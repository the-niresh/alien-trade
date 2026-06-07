"""
RiskEngine: wraps any StrategyFn and enforces all risk rules before an order reaches execution.

Responsibilities (in order):
  1. Track daily P&L via internal position accounting → daily-loss kill switch
  2. Run all hard guardrails (check_guardrails)
  3. Volatility-targeted position sizing (shrinks in turbulence)
  4. Kelly sizing cap from recent trade history
  5. Mistake-avoidance stub → wired to Upstash Vector in Step 6

The engine is itself a StrategyFn so it drops straight into run_backtest and run_walk_forward.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from backtest.engine import Bar, Order, StrategyFn
from risk.guardrails import RiskConfig, GuardrailResult, check_guardrails, check_max_exposure
from risk.sizing import compute_position_size


# ── Internal position tracker ─────────────────────────────────────────────────

@dataclass
class _PosTracker:
    """
    Lightweight position accounting for daily P&L.
    Does NOT replicate the backtest engine's cost model — costs are tracked there.
    Used only for daily-loss threshold computation.
    """
    cash: float
    units: float = 0.0
    avg_entry: float = 0.0
    consecutive_losses: int = 0
    current_day: int = -1
    day_start_equity: float = 0.0
    recent_pnls: list = field(default_factory=list)   # last N closed-trade PnLs

    def equity(self, price: float) -> float:
        return self.cash + self.units * price

    def new_day(self, equity: float) -> None:
        self.day_start_equity = equity

    def daily_loss_pct(self, current_equity: float) -> float:
        if self.day_start_equity <= 0:
            return 0.0
        loss = self.day_start_equity - current_equity
        return max(loss / self.day_start_equity, 0.0)

    def apply_buy(self, size_usd: float, price: float) -> None:
        units = size_usd / price if price > 0 else 0.0
        if self.units == 0:
            self.avg_entry = price
        elif units > 0:
            total = self.units + units
            self.avg_entry = (self.avg_entry * self.units + price * units) / total
        self.units += units
        self.cash -= size_usd

    def apply_sell(self, size_usd: float, price: float) -> None:
        units = min(size_usd / price if price > 0 else 0.0, self.units)
        pnl = (price - self.avg_entry) * units
        self.cash += size_usd
        self.units = max(self.units - units, 0.0)
        self.recent_pnls.append(pnl)
        if len(self.recent_pnls) > 20:
            self.recent_pnls.pop(0)
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0


# ── Risk engine ───────────────────────────────────────────────────────────────

class RiskEngine:
    """
    Callable StrategyFn wrapper.  Usage:

        raw_strategy = make_strategy(params)
        safe_strategy = RiskEngine(raw_strategy, RiskConfig(), initial_capital=10_000)
        result = run_backtest(bars, safe_strategy, cost_model=BSCCostModel())
    """

    def __init__(
        self,
        inner_strategy: StrategyFn,
        config: RiskConfig,
        initial_capital: float = 10_000.0,
    ) -> None:
        self._strategy = inner_strategy
        self._config = config
        self._pos = _PosTracker(cash=initial_capital, day_start_equity=initial_capital)

    # StrategyFn interface
    def __call__(self, history: list[Bar]) -> Optional[Order]:
        bar = history[-1]
        price = bar.close

        # ── Daily bookkeeping ─────────────────────────────────────────────────
        day = bar.timestamp // 86_400_000
        if day != self._pos.current_day:
            self._pos.current_day = day
            self._pos.new_day(self._pos.equity(bar.open))

        current_equity = self._pos.equity(price)
        daily_loss_pct = self._pos.daily_loss_pct(current_equity)

        # ── Guardrails (pre-signal check — fail fast) ─────────────────────────
        pre_check = check_guardrails(
            symbol="BNB",                        # placeholder — real symbol from order below
            size_usd=self._config.base_position_usd,
            daily_loss_pct=daily_loss_pct,
            consecutive_losses=self._pos.consecutive_losses,
            capital=current_equity,
            config=self._config,
        )
        # Only block on daily-loss / circuit-breaker at this stage
        if not pre_check.allowed and (
            "daily-loss" in pre_check.reason or "circuit breaker" in pre_check.reason
        ):
            return None

        # ── Inner strategy signal ─────────────────────────────────────────────
        order = self._strategy(history)
        if order is None:
            return None

        # ── Volatility-targeted sizing ────────────────────────────────────────
        sized_usd = compute_position_size(
            history=history,
            base_size_usd=self._config.base_position_usd,
            capital=current_equity,
            recent_pnls=self._pos.recent_pnls,
            max_pct=self._config.max_position_pct,
            target_vol=self._config.target_vol_ann,
        )
        sized_usd = min(sized_usd, self._config.max_trade_usd)

        # ── Full guardrail check on final sized order ─────────────────────────
        check = check_guardrails(
            symbol=order.symbol,
            size_usd=sized_usd,
            daily_loss_pct=daily_loss_pct,
            consecutive_losses=self._pos.consecutive_losses,
            capital=current_equity,
            config=self._config,
        )
        if not check.allowed:
            return None

        if sized_usd < 10.0:
            return None

        # ── Max-exposure invariant: a buy may never push CUMULATIVE open
        #    exposure past the cap (a sequence of legal buys can't pile over).
        #    Sells reduce exposure, so they're never gated here. ───────────────
        if order.side == "buy":
            exposure = check_max_exposure(
                open_exposure_usd=self._pos.units * price,
                new_size_usd=sized_usd,
                equity=current_equity,
                config=self._config,
            )
            if not exposure.allowed:
                return None

        # ── Mistake-avoidance: the live Hermes read path runs in the agent loop
        #    (agent/secondbrain/avoidance.py), off the /core hot path. ─────────

        # ── Update internal tracker + emit order ──────────────────────────────
        if order.side == "buy":
            self._pos.apply_buy(sized_usd, price)
        else:
            self._pos.apply_sell(sized_usd, price)

        return Order(
            side=order.side,
            size_usd=sized_usd,
            symbol=order.symbol,
            timestamp=order.timestamp,
        )

    def restore(self, trades: list, initial_capital: float | None = None) -> None:
        """
        Rebuild internal position accounting after a crash/restart by replaying
        closed trades (the on-chain ledger is the source of truth). `trades` is a
        list of dicts/objects with side, size_usd, fill_price in time order.
        Restores cash, units, avg_entry, recent_pnls, and consecutive_losses so
        sizing + daily-loss + circuit-breaker resume correctly. Idempotent per call.
        """
        cap = initial_capital if initial_capital is not None else self._pos.cash
        self._pos = _PosTracker(cash=cap, day_start_equity=cap)
        for t in trades:
            side = t["side"] if isinstance(t, dict) else t.side
            size = float(t["size_usd"] if isinstance(t, dict) else t.size_usd)
            price = float(t["fill_price"] if isinstance(t, dict) else t.fill_price)
            if side == "buy":
                self._pos.apply_buy(size, price)
            else:
                self._pos.apply_sell(size, price)

    @property
    def risk_state_snapshot(self) -> dict:
        """Read-only state for logging / Convex audit rows."""
        return {
            "consecutive_losses": self._pos.consecutive_losses,
            "daily_loss_pct": self._pos.daily_loss_pct(
                self._pos.equity(self._pos.avg_entry or 1.0)
            ),
            "open_units": self._pos.units,
            "cash": self._pos.cash,
        }


# ── Convenience factory ───────────────────────────────────────────────────────

def make_risk_strategy(
    inner: StrategyFn,
    config: RiskConfig | None = None,
    initial_capital: float = 10_000.0,
) -> RiskEngine:
    """Wrap a StrategyFn with the full risk engine. Drop-in replacement."""
    return RiskEngine(inner, config or RiskConfig(), initial_capital)
