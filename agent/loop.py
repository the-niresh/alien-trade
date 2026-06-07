"""
DecisionLoop — the live trading heart.

Per cycle, identical in shape to one bar of the backtest:
    feed → kill-switch check → SAME /core risk-wrapped strategy → mistake-avoidance
    → executor (simulate→sign→send→confirm) → reconcile ledger → write Convex rows.

The strategy callable IS the sim's strategy (RiskEngine-wrapped core). Because
the loop hands it the same point-in-time history the sim does, the live decision
is provably the sim's decision — that's the sim/live parity invariant.

Every cycle writes exactly one decision row (idempotent on cycle_id) so the audit
trail is complete: "if it's not in Convex, it didn't happen."
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from backtest.engine import Bar, Order, StrategyFn
from backtest.regime import detect_regime
from strategy.combined import StrategyParams, score_breakdown

from agent.brain import AllowAll, MistakeAvoidance
from agent.convex_bridge import ConvexBridge
from agent.executor import DUPLICATE, FAILED, REJECTED, Executor, ExecutionReport
from agent.ledger import LedgerState


@dataclass
class CycleResult:
    cycle_id: str
    timestamp_ms: int
    halted: bool
    regime: str
    verdict: str                       # allow | reduce | block
    reason: str
    order: Optional[Order]
    execution: Optional[ExecutionReport]
    equity: float
    drawdown_pct: float
    breakdown: dict = field(default_factory=dict)


class DecisionLoop:
    def __init__(
        self,
        *,
        feed,
        strategy: StrategyFn,
        executor: Executor,
        bridge: ConvexBridge,
        params: StrategyParams,
        symbol: str = "BNB",
        mode: str = "paper",
        initial_capital: float = 10_000.0,
        base_position_usd: float = 1_000.0,
        max_consecutive_losses: int = 5,
        mistake_avoidance: Optional[MistakeAvoidance] = None,
        reflection_writer: Optional[object] = None,
    ):
        self.feed = feed
        self.strategy = strategy            # the SAME risk-wrapped /core strategy
        self.executor = executor
        self.bridge = bridge
        self.params = params
        self.symbol = symbol
        self.mode = mode
        self.base_position_usd = base_position_usd
        self.max_consecutive_losses = max_consecutive_losses
        self.brain = mistake_avoidance or AllowAll()
        # Hermes write-side (post-trade reflection). None = disabled (Step 5 default).
        self.reflection_writer = reflection_writer
        self.ledger = LedgerState(initial_capital=initial_capital)

    # ── one cycle ────────────────────────────────────────────────────────────

    def run_cycle(self, history: list[Bar]) -> CycleResult:
        bar = history[-1]
        cycle_id = f"{self.symbol}-{bar.timestamp}"
        self.ledger.roll_day(bar.timestamp, bar.open)

        regime = detect_regime(history)
        breakdown = score_breakdown(history, self.params)
        signals = _signals_obj(breakdown)
        target_usd = breakdown["target"] * self.base_position_usd

        # ── Kill switch: halt within one cycle ──────────────────────────────
        if self.bridge.is_halted():
            self.bridge.audit("kill_switch", cycle_id,
                              {"symbol": self.symbol, "regime": regime.value}, "warn")
            return self._finalise(
                cycle_id, bar, regime.value, "block", "kill switch active",
                None, None, target_usd, 0.0, None, breakdown, signals, halted=True,
            )

        # ── Decision (same code as the sim) ─────────────────────────────────
        order = self.strategy(history)

        verdict, reason, execution, trade_id, final_size = "block", "no signal / risk veto", None, None, 0.0

        if order is not None:
            ma = self.brain.check(history, order, regime.value)
            if ma.block:
                verdict, reason = "block", f"mistake-avoidance: {ma.reason}"
                self.bridge.audit("risk_veto", cycle_id, {"reason": ma.reason}, "warn")
            else:
                exec_order = order
                # Hermes soft veto: shrink the order on a historically-bad setup.
                if ma.size_penalty > 0.0:
                    exec_order = Order(
                        side=order.side, size_usd=order.size_usd * (1.0 - ma.size_penalty),
                        symbol=order.symbol, timestamp=order.timestamp,
                    )
                    self.bridge.audit("risk_veto", cycle_id,
                                      {"reason": ma.reason, "size_penalty": ma.size_penalty}, "warn")
                final_size = exec_order.size_usd
                execution = self.executor.execute(exec_order, bar, idempotency_key=cycle_id)
                verdict, reason, trade_id = self._handle_execution(
                    execution, bar, cycle_id, regime.value, breakdown)

        return self._finalise(
            cycle_id, bar, regime.value, verdict, reason, order, execution,
            target_usd, final_size, trade_id, breakdown, signals, halted=False,
        )

    # ── execution → ledger → trade/ledger rows ──────────────────────────────

    def _handle_execution(self, execution: ExecutionReport, bar: Bar, cycle_id: str,
                          regime: str = "", breakdown: Optional[dict] = None):
        if execution.is_fill and execution.fill is not None:
            realized = self.ledger.apply(execution.fill)
            trade_id = self.bridge.record_trade(
                symbol=execution.order.symbol,
                side=execution.order.side,
                size_usd=execution.order.size_usd,
                fill_price=execution.fill.fill_price,
                fee_usd=execution.fill.fee_usd,
                gas_usd=execution.fill.gas_usd,
                slippage_usd=execution.fill.slippage_usd,
                mode=self.mode,
                tx_hash=execution.tx_hash,
                timestamp_ms=bar.timestamp,
            )
            if trade_id:
                self.bridge.append_ledger(
                    trade_id=trade_id,
                    realized_pnl_usd=realized,
                    cumulative_pnl_usd=self.ledger.cumulative_pnl(bar.close),
                    cumulative_fees_usd=self.ledger.cumulative_fees,
                    cumulative_gas_usd=self.ledger.cumulative_gas,
                    peak_equity_usd=self.ledger.peak_equity,
                    current_drawdown_pct=self.ledger.drawdown_pct(bar.close),
                    timestamp_ms=bar.timestamp,
                )
            self.bridge.audit("trade", cycle_id,
                             {"side": execution.order.side, "size_usd": execution.order.size_usd,
                              "fill_price": execution.fill.fill_price, "tx_hash": execution.tx_hash,
                              "realized_pnl": realized}, "info")
            # Hermes write-side: a sell closes/reduces a position → reflect on the
            # realized outcome. (Buys open positions — no outcome to learn yet.)
            if (self.reflection_writer is not None
                    and execution.order.side == "sell" and breakdown is not None):
                self.reflection_writer.reflect(
                    cycle_id=cycle_id, trade_id=trade_id, timestamp_ms=bar.timestamp,
                    regime=regime, side=execution.order.side, signals=breakdown,
                    realized_pnl=realized,
                )
            return "allow", execution.reason, trade_id

        if execution.status == DUPLICATE:
            return "block", execution.reason, None
        if execution.status == REJECTED:
            self.bridge.audit("risk_veto", cycle_id, {"reason": execution.reason}, "warn")
            return "block", execution.reason, None
        if execution.status == FAILED:
            self.bridge.audit("error", cycle_id, {"reason": execution.reason}, "error")
            return "block", execution.reason, None
        return "reduce", execution.reason, None

    # ── finalise: decision row + risk_state every cycle ─────────────────────

    def _finalise(self, cycle_id, bar, regime, verdict, reason, order, execution,
                  target_usd, final_size, trade_id, breakdown, signals, halted):
        equity = self.ledger.mark(bar.close)
        drawdown = self.ledger.drawdown_pct(bar.close)
        circuit = self.ledger.consecutive_losses >= self.max_consecutive_losses

        self.bridge.record_decision(
            cycle_id=cycle_id, symbol=self.symbol, timestamp_ms=bar.timestamp,
            regime=regime, signals=signals, target_position_usd=target_usd,
            risk_verdict=verdict, risk_reason=reason, final_size_usd=final_size,
            trade_id=trade_id,
        )
        self.bridge.update_risk_state(
            daily_loss_usd=self.ledger.daily_loss_usd(bar.close),
            open_exposure_usd=self.ledger.open_exposure(bar.close),
            current_drawdown_pct=drawdown,
            peak_equity_usd=self.ledger.peak_equity,
            circuit_breaker_active=circuit,
        )
        return CycleResult(
            cycle_id=cycle_id, timestamp_ms=bar.timestamp, halted=halted,
            regime=regime, verdict=verdict, reason=reason, order=order,
            execution=execution, equity=equity, drawdown_pct=drawdown,
            breakdown=breakdown,
        )

    # ── drivers ─────────────────────────────────────────────────────────────

    def run(self, max_cycles: Optional[int] = None) -> list[CycleResult]:
        """Drive the feed to exhaustion (replay) or for max_cycles. No sleeps."""
        results: list[CycleResult] = []
        n = 0
        while max_cycles is None or n < max_cycles:
            history = self.feed.next()
            if history is None:
                break
            results.append(self.run_cycle(history))
            n += 1
        return results

    def run_forever(self, cycle_seconds: int) -> None:
        """Live driver: one cycle, sleep to cadence, repeat. Ctrl-C to stop.

        Each cycle is wrapped so an unanticipated exception is logged (structured,
        keyed by trace) and audited to Convex, then the loop CONTINUES — a testnet
        shadow-run must survive the surprises it exists to surface, not die on the
        first one."""
        from agent.observability import jlog
        while True:
            try:
                history = self.feed.next()
                if history:
                    res = self.run_cycle(history)
                    jlog("cycle", trace=res.cycle_id, regime=res.regime,
                         verdict=res.verdict, equity=round(res.equity, 2),
                         drawdown=round(res.drawdown_pct, 4),
                         filled=bool(res.execution and res.execution.is_fill),
                         halted=res.halted, reason=res.reason)
            except Exception as e:  # noqa: BLE001 — shadow-run resilience
                jlog("cycle_error", level="error",
                     error=str(e), error_type=type(e).__name__)
                try:
                    self.bridge.audit("error", None,
                                      {"error": str(e), "error_type": type(e).__name__}, "error")
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(cycle_seconds)


# ── helpers ────────────────────────────────────────────────────────────────

def _signals_obj(breakdown: dict) -> dict:
    """Map score_breakdown → the Convex decisions.signals object shape."""
    return {
        "s1_momentum": breakdown.get("s1"),
        "s2_funding": breakdown.get("s2"),
        "s3_sentiment": breakdown.get("s3"),
        "s4_flow": breakdown.get("s4"),
    }
