"""Autopilot wired into the DecisionLoop — bank/ratchet/block-entry/parity (offline)."""
from __future__ import annotations

from backtest.costs import BSCCostModel
from backtest.engine import Bar, Order
from strategy.combined import StrategyParams

from agent.convex_bridge import ConvexBridge
from agent.executor import PaperExecutor
from agent.feed import ReplayFeed
from agent.loop import DecisionLoop
from risk.autopilot import AutopilotConfig


class _Bridge(ConvexBridge):
    """Offline bridge that captures audit kinds; everything else no-ops."""
    def __init__(self):
        super().__init__(url="")
        self.audits: list[tuple] = []

    def is_halted(self):
        return False

    def get_equity_floor(self):
        return 0.0

    def audit(self, event_type, cycle_id, payload, severity="info"):
        self.audits.append((event_type, payload))

    def kinds(self):
        return [a[0] for a in self.audits]


def _bar(ts, price):
    return Bar(timestamp=ts, open=price, high=price * 1.01, low=price * 0.99,
               close=price, volume=1.0)


class _Strategy:
    """Buys once (when first called), then holds (returns None)."""
    def __init__(self, size):
        self.size = size
        self.fired = False

    def __call__(self, history):
        if self.fired:
            return None
        self.fired = True
        bar = history[-1]
        return Order(side="buy", size_usd=self.size, symbol="ETH", timestamp=bar.timestamp)


def _loop(bridge, strategy, autopilot, capital=100.0):
    return DecisionLoop(
        feed=ReplayFeed([]), strategy=strategy,
        executor=PaperExecutor(cost_model=BSCCostModel()), bridge=bridge,
        params=StrategyParams(symbol="ETH"), symbol="ETH", mode="paper",
        initial_capital=capital, autopilot_config=autopilot,
    )


# ── Parity: disabled autopilot changes nothing ────────────────────────────────

def test_disabled_autopilot_no_intervention():
    bridge = _Bridge()
    loop = _loop(bridge, _Strategy(90.0), autopilot=None)
    loop.run_cycle([_bar(0, 100.0)])           # buy fills
    loop.run_cycle([_bar(3_600_000, 130.0)])   # big gain, but autopilot off
    assert "autopilot" not in bridge.kinds()
    assert loop._block_entry is False


# ── Profit-lock + capital ratchet ─────────────────────────────────────────────

def test_bank_on_profit_target_and_ratchet():
    bridge = _Bridge()
    cfg = AutopilotConfig(enabled=True, profit_target_pct=0.10, protect_principal=True)
    loop = _loop(bridge, _Strategy(95.0), cfg)
    loop.run_cycle([_bar(0, 100.0)])                 # buy ~95 of 100 capital
    floor_before = loop._autopilot_state.protected_floor
    res = loop.run_cycle([_bar(3_600_000, 140.0)])   # +40% on the position -> bank
    assert "autopilot" in bridge.kinds()
    assert "autopilot" in res.reason
    assert loop._autopilot_state.protected_floor > floor_before
    # After banking the floor is at/above the gained equity -> no capital to redeploy.
    assert loop.ledger.open_exposure(140.0) < 1e-3   # position was flattened


def test_deployable_cap_blocks_buy_above_floor():
    bridge = _Bridge()
    cfg = AutopilotConfig(enabled=True)
    loop = _loop(bridge, _Strategy(50.0), cfg, capital=100.0)
    # Pin a protected floor above equity -> a fresh buy has no deployable capital.
    from risk.autopilot import AutopilotState
    loop._autopilot_state = AutopilotState(protected_floor=200.0)
    res = loop.run_cycle([_bar(0, 100.0)])
    assert loop.ledger.open_exposure(100.0) < 1e-3   # buy was blocked
    assert any(p.get("action") == "block_buy" for k, p in bridge.audits if k == "autopilot")


# ── Recycle gate / cooldown ───────────────────────────────────────────────────

def test_block_entry_suppresses_buy():
    bridge = _Bridge()
    # Impossible confidence threshold -> recycle gate always blocks a fresh entry.
    cfg = AutopilotConfig(enabled=True, min_recycle_confidence=2.0)
    loop = _loop(bridge, _Strategy(50.0), cfg)
    res = loop.run_cycle([_bar(0, 100.0)])
    assert loop._block_entry is True
    assert "recycle gate" in res.reason
    assert loop.ledger.open_exposure(100.0) < 1e-3   # nothing bought


# ── Daily profit target ───────────────────────────────────────────────────────

def test_daily_target_halts_for_day():
    bridge = _Bridge()
    cfg = AutopilotConfig(enabled=True, daily_profit_target_pct=0.05)
    loop = _loop(bridge, _Strategy(0.0), cfg, capital=100.0)
    # Seed the day anchor below current equity so the daily gain clears the target.
    from risk.autopilot import AutopilotState
    loop._autopilot_state = AutopilotState(day_start_equity=90.0, day_key="1970-01-01")
    res = loop.run_cycle([_bar(0, 100.0)])           # +11% on the day -> halt
    assert "autopilot" in res.reason
    assert loop._autopilot_state.halted_for_day is True
