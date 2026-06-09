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
from typing import Callable, Optional

from backtest.engine import Bar, Fill, Order, StrategyFn, Trade
from backtest.regime import detect_regime
from scorecard import OperationalStats, RuleAdherence, compute_scorecard
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
        executor_factory: Optional[Callable[[str], Executor]] = None,
        enforce_activity_floor: bool = False,
        activity_deadline_hour: int = 23,
        activity_trade_usd: float = 15.0,
    ):
        self.feed = feed
        self.strategy = strategy            # the SAME risk-wrapped /core strategy
        self.executor = executor
        self.bridge = bridge
        self.params = params
        self.symbol = symbol
        self.mode = mode
        # Live mode toggle (the UI writes config.trading_mode). When a factory is
        # supplied, the loop swaps its executor to match the toggle each cycle —
        # but only while FLAT (an open position must close under the mode it was
        # opened in). None → mode is fixed at the boot value (no live switching).
        self.executor_factory = executor_factory
        self._pending_mode: Optional[str] = None   # desired mode deferred until flat
        self._exposure_epsilon = 1e-6
        self.base_position_usd = base_position_usd
        self.max_consecutive_losses = max_consecutive_losses
        self.brain = mistake_avoidance or AllowAll()
        # Hermes write-side (post-trade reflection). None = disabled (Step 5 default).
        self.reflection_writer = reflection_writer
        self.ledger = LedgerState(initial_capital=initial_capital)

        # ── Live scorecard accumulators (docs/GOAL.md) ──────────────────────
        # The same shapes core/scorecard.py scores in sim, built up cycle-by-cycle
        # from real fills so the live objective is computed identically. Trades are
        # paired exactly as backtest.engine does (single entry fill → close on sell),
        # which holds because live fills reproduce the sim's fills (parity invariant).
        self._initial_capital = initial_capital
        self._equity_curve: list[float] = []
        self._equity_ts: list[int] = []
        self._exposure_curve: list[float] = []
        self._fills: list[Fill] = []
        self._trades: list[Trade] = []
        self._entry_fill: Optional[Fill] = None
        # Passthrough facts the curve can't reveal (autonomy + rule adherence).
        self._cycles_total = 0
        self._blocks_fired = 0
        self._kill_switch_activations = 0
        self._circuit_breaker_activations = 0
        self._peak_exposure_pct = 0.0
        self._was_halted = False
        self._was_circuit = False

        # ── Activity floor (competition qualification) ──────────────────────
        # Track 1 requires >= 1 trade per calendar day (7 over the window). A quiet
        # regime that emits no signal must not disqualify us, so when enabled the
        # loop forces ONE minimal compliance swap late in the day if nothing has
        # traded yet. OFF by default: it would diverge a paper run from the sim
        # (the backtest has no such forced trade), so it's enabled only for the
        # live competition window — never during parity/rehearsal.
        self.enforce_activity_floor = enforce_activity_floor
        self.activity_deadline_hour = activity_deadline_hour
        self.activity_trade_usd = activity_trade_usd
        self._activity_day = -1
        self._trades_today = 0

    # ── one cycle ────────────────────────────────────────────────────────────

    def run_cycle(self, history: list[Bar]) -> CycleResult:
        bar = history[-1]
        cycle_id = f"{self.symbol}-{bar.timestamp}"
        self.ledger.roll_day(bar.timestamp, bar.open)

        # Reset the per-day trade counter on a calendar-day rollover (activity floor).
        day = bar.timestamp // 86_400_000
        if day != self._activity_day:
            self._activity_day = day
            self._trades_today = 0

        # ── Live trading-mode toggle: align the executor with the UI ─────────
        self._sync_trading_mode(bar, cycle_id)

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

        # ── Activity floor: guarantee >= 1 trade this calendar day ───────────
        self._maybe_compliance_trade(bar, cycle_id)

        return self._finalise(
            cycle_id, bar, regime.value, verdict, reason, order, execution,
            target_usd, final_size, trade_id, breakdown, signals, halted=False,
        )

    # ── live mode toggle ─────────────────────────────────────────────────────

    def _sync_trading_mode(self, bar: Bar, cycle_id: str) -> None:
        """Read the UI's trading-mode toggle and swap the executor to match — but
        only while flat. Switching paper↔mainnet moves real funds, so a position
        opened under one mode must close under that same mode; while a position is
        open the switch is DEFERRED (audited once) and applied the first flat cycle.
        Offline / no factory / unseeded config → no-op (mode stays at boot value)."""
        if self.executor_factory is None:
            return
        desired = self.bridge.get_trading_mode()
        if not desired or desired == self.mode:
            self._pending_mode = None
            return

        open_exposure = self.ledger.open_exposure(bar.close)
        if open_exposure > self._exposure_epsilon:
            # Position open — defer. Audit only when the deferred target changes,
            # so a long-held position doesn't spam the audit log every cycle.
            if self._pending_mode != desired:
                self._pending_mode = desired
                self.bridge.audit("mode_switch_deferred", cycle_id, {
                    "from": self.mode, "to": desired,
                    "open_exposure_usd": round(open_exposure, 2),
                    "reason": "position open — switch applies once flat",
                }, "warn")
            return

        # Flat → safe to switch. Rebuild the executor for the new mode.
        try:
            new_executor = self.executor_factory(desired)
        except Exception as e:  # noqa: BLE001 — a bad rebuild must not crash the cycle
            self.bridge.audit("error", cycle_id, {
                "error": str(e), "error_type": type(e).__name__,
                "reason": f"executor rebuild for mode {desired!r} failed; staying on {self.mode!r}",
            }, "error")
            return
        previous = self.mode
        self.executor = new_executor
        self.mode = desired
        self._pending_mode = None
        self.bridge.audit("mode_switch", cycle_id,
                          {"from": previous, "to": desired}, "info")

    # ── activity floor ─────────────────────────────────────────────────────────

    def _maybe_compliance_trade(self, bar: Bar, cycle_id: str) -> None:
        """Force ONE minimal swap late in the day if nothing has traded yet, so we
        meet Track 1's >= 1-trade/day qualification. Safe by construction: it TRIMS
        an open position when we hold one (a sell can never breach an exposure cap)
        and otherwise opens a tiny position. Never fires when disabled, when a trade
        already happened today, or before the deadline hour. Routed through the same
        executor as every other trade, so it's a real `twak swap` that counts."""
        if not self.enforce_activity_floor or self._trades_today > 0:
            return
        hour = (bar.timestamp // 3_600_000) % 24
        if hour < self.activity_deadline_hour:
            return   # still early in the day — give the strategy room to trade

        price = bar.close
        held_usd = self.ledger.open_exposure(price)
        if held_usd > self.activity_trade_usd:
            side, size = "sell", self.activity_trade_usd      # trim — always safe
        elif held_usd > 0.0:
            side, size = "sell", held_usd                     # close the dust
        else:
            side, size = "buy", self.activity_trade_usd       # flat → open tiny
        if size <= 0.0:
            return

        order = Order(side=side, size_usd=size, symbol=self.symbol, timestamp=bar.timestamp)
        execution = self.executor.execute(order, bar, idempotency_key=f"{cycle_id}-activity")
        self.bridge.audit("activity_floor", cycle_id, {
            "side": side, "size_usd": round(size, 2), "hour": hour,
            "reason": "no trade yet today — forcing minimal compliance swap",
        }, "info")
        self._handle_execution(execution, bar, cycle_id)

    # ── execution → ledger → trade/ledger rows ──────────────────────────────

    def _handle_execution(self, execution: ExecutionReport, bar: Bar, cycle_id: str,
                          regime: str = "", breakdown: Optional[dict] = None):
        if execution.is_fill and execution.fill is not None:
            realized = self.ledger.apply(execution.fill)
            self._trades_today += 1   # counts toward the >= 1 trade/day floor
            # Accumulate for the live scorecard, pairing trades like the backtest.
            self._fills.append(execution.fill)
            if execution.fill.order.side == "buy":
                if self._entry_fill is None:
                    self._entry_fill = execution.fill
            elif self._entry_fill is not None:
                self._trades.append(
                    Trade(entry=self._entry_fill, exit=execution.fill, pnl_usd=realized))
                self._entry_fill = None
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
            # A guardrail correctly blocked a trade — this is the system working,
            # not a rule violation (scorecard rule-adherence counts it as such).
            self._blocks_fired += 1
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

        # ── Accumulate the scorecard series + push the live objective ────────
        open_exp = self.ledger.open_exposure(bar.close)
        self._cycles_total += 1
        self._equity_curve.append(equity)
        self._equity_ts.append(bar.timestamp)
        self._exposure_curve.append(open_exp)
        if equity > 0:
            self._peak_exposure_pct = max(self._peak_exposure_pct, open_exp / equity)
        if halted and not self._was_halted:        # rising edge only
            self._kill_switch_activations += 1
        self._was_halted = halted
        if circuit and not self._was_circuit:
            self._circuit_breaker_activations += 1
        self._was_circuit = circuit
        self._push_scorecard()

        return CycleResult(
            cycle_id=cycle_id, timestamp_ms=bar.timestamp, halted=halted,
            regime=regime, verdict=verdict, reason=reason, order=order,
            execution=execution, equity=equity, drawdown_pct=drawdown,
            breakdown=breakdown,
        )

    # ── live scorecard ────────────────────────────────────────────────────────

    def build_scorecard(self):
        """Score the run so far against the agent's goal (docs/GOAL.md). Same
        core/scorecard.py the backtest uses — sim and live score identically."""
        ops = OperationalStats(cycles_total=self._cycles_total)
        rules = RuleAdherence(
            violations=0,   # a breach can't reach execution — guardrails block first
            blocks_fired=self._blocks_fired,
            kill_switch_activations=self._kill_switch_activations,
            circuit_breaker_activations=self._circuit_breaker_activations,
            max_open_exposure_pct=self._peak_exposure_pct,
        )
        return compute_scorecard(
            self._equity_curve, self._trades, self._fills, self._initial_capital,
            timestamps=self._equity_ts, exposure_curve=self._exposure_curve,
            operational=ops, rule_adherence=rules,
        )

    def _push_scorecard(self) -> None:
        """Upsert the live scorecard. Pure telemetry — a failure here must never
        crash a trading cycle, so it's fully guarded."""
        try:
            self.bridge.update_scorecard(**self.build_scorecard().as_convex_row())
        except Exception:  # noqa: BLE001 — scorecard is observability, not the trade
            pass

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
