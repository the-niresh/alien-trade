"""
Crash-state recovery (AgentForge Lesson 11: persistence + recovery).

Convex is the durable event log (append-only trades/decisions/ledger). On a
restart the in-memory state is gone - this module rebuilds it from Convex so a
restart mid-position is safe:

  1. Idempotency  - re-seed the executor's seen-set from already-executed cycles,
                    so replaying a cycle after a crash returns DUPLICATE, never a
                    second broadcast. (This is the critical no-double-trade guard.)
  2. Ledger       - replay closed trades through a fresh LedgerState to restore
                    cash/units/peak-equity/drawdown/cumulative-costs/loss-streak.
  3. Risk engine  - replay the same trades through the RiskEngine's internal
                    tracker so sizing, daily-loss, and the circuit breaker resume.

On-chain balance is the ultimate truth; `expected_units` is returned so the
caller can alert on drift between reconstructed and real position.
"""
from __future__ import annotations

from dataclasses import dataclass

from backtest.engine import Fill, Order
from risk.engine import RiskEngine

from agent.ledger import LedgerState


@dataclass
class RecoveryReport:
    recovered: bool
    n_trades: int
    n_seen_cycles: int
    expected_units: float
    realized_pnl: float
    peak_equity: float
    note: str = ""


def recover(loop) -> RecoveryReport:
    """Rebuild `loop` state from its Convex bridge. No-op when offline/empty."""
    bridge = loop.bridge
    if not getattr(bridge, "enabled", False):
        return RecoveryReport(False, 0, 0, 0.0, 0.0, 0.0, "convex offline - nothing to recover")

    trades_desc = bridge.recent_trades(limit=500)
    decisions = bridge.recent_decisions(limit=500)
    if not trades_desc and not decisions:
        return RecoveryReport(False, 0, 0, 0.0, 0.0, 0.0, "no prior state in convex")

    trades = list(reversed(trades_desc))   # ascending for replay

    # 1. Idempotency: every cycle that already produced a trade is off-limits.
    executed_cycles = [d["cycle_id"] for d in decisions if d.get("trade_id")]
    for cid in executed_cycles:
        loop.executor.mark_seen(cid)

    # 2. Ledger: replay trades into a fresh ledger.
    led = LedgerState(initial_capital=loop.ledger.initial_capital)
    for t in trades:
        order = Order(side=t["side"], size_usd=float(t["size_usd"]),
                      symbol=t["symbol"], timestamp=int(t.get("timestamp_ms", 0)))
        led.apply(Fill(order=order, fill_price=float(t["fill_price"]),
                       fee_usd=float(t.get("fee_usd", 0.0)),
                       gas_usd=float(t.get("gas_usd", 0.0)),
                       slippage_usd=float(t.get("slippage_usd", 0.0))))
    # Peak equity is driven by per-bar marks (not just trades), so restore it
    # from the durable ledger row; the running peak re-establishes on next mark.
    latest = bridge.latest_ledger()
    if latest and latest.get("peak_equity_usd"):
        led.peak_equity = max(led.peak_equity, float(latest["peak_equity_usd"]))
    loop.ledger = led

    # 3. Risk engine: replay through its internal tracker.
    if isinstance(loop.strategy, RiskEngine):
        loop.strategy.restore(trades, initial_capital=led.initial_capital)

    return RecoveryReport(
        recovered=True,
        n_trades=len(trades),
        n_seen_cycles=len(executed_cycles),
        expected_units=led.units,
        realized_pnl=led.realized_pnl_total,
        peak_equity=led.peak_equity,
        note="state rebuilt from convex event log",
    )
