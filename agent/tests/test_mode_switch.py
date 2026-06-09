"""
Live trading-mode toggle — the UI writes config.trading_mode and the loop swaps
its executor to match, but only while FLAT (a position opened under one mode must
close under that same mode). These tests pin the guard: flat switches, open
positions defer, deferral applies on the first flat cycle, and offline / no-factory
runs never switch.
"""
from __future__ import annotations

from backtest.engine import Bar
from strategy.combined import StrategyParams

from agent.convex_bridge import ConvexBridge
from agent.feed import ReplayFeed
from agent.loop import DecisionLoop


# ── fixtures ──────────────────────────────────────────────────────────────────

class _ModeBridge(ConvexBridge):
    """Offline bridge with a settable trading mode + captured audits."""
    def __init__(self, mode=None):
        super().__init__(url="")
        self._mode = mode
        self.audits: list[tuple] = []

    def get_trading_mode(self):
        return self._mode

    def is_halted(self):
        return False

    def audit(self, event_type, cycle_id, payload, severity="info"):
        self.audits.append((event_type, payload, severity))

    def kinds(self):
        return [a[0] for a in self.audits]


class _Exec:
    """Marker executor — the swap only stores it; _sync never calls execute()."""
    def __init__(self, tag):
        self.tag = tag


def _loop(bridge, *, factory=None, mode="paper"):
    return DecisionLoop(
        feed=ReplayFeed([]), strategy=lambda h: None,
        executor=_Exec("paper"), bridge=bridge,
        params=StrategyParams(), symbol="BNB", mode=mode,
        initial_capital=10_000.0, executor_factory=factory,
    )


_BAR = Bar(timestamp=1_700_000_000_000, open=100.0, high=101.0, low=99.0,
           close=100.0, volume=1.0)


# ── tests ───────────────────────────────────────────────────────────────────

def test_no_factory_never_switches():
    loop = _loop(_ModeBridge("mainnet"), factory=None, mode="paper")
    loop._sync_trading_mode(_BAR, "c1")
    assert loop.mode == "paper"  # boot mode is fixed without a factory


def test_offline_mode_is_noop():
    # get_trading_mode() -> None (unseeded / offline) keeps the boot mode.
    loop = _loop(_ModeBridge(None), factory=lambda m: _Exec(m), mode="paper")
    loop._sync_trading_mode(_BAR, "c1")
    assert loop.mode == "paper"
    assert loop.bridge.kinds() == []


def test_same_mode_is_noop():
    bridge = _ModeBridge("paper")
    loop = _loop(bridge, factory=lambda m: _Exec(m), mode="paper")
    loop._sync_trading_mode(_BAR, "c1")
    assert loop.mode == "paper"
    assert bridge.kinds() == []


def test_flat_switches_and_rebuilds_executor():
    bridge = _ModeBridge("mainnet")
    loop = _loop(bridge, factory=lambda m: _Exec(m), mode="paper")  # flat: units == 0
    loop._sync_trading_mode(_BAR, "c1")
    assert loop.mode == "mainnet"
    assert loop.executor.tag == "mainnet"
    assert "mode_switch" in bridge.kinds()
    assert loop._pending_mode is None


def test_open_position_defers_switch():
    bridge = _ModeBridge("mainnet")
    loop = _loop(bridge, factory=lambda m: _Exec(m), mode="paper")
    loop.ledger.units = 5.0  # open position → exposure 5 * 100 = $500
    loop._sync_trading_mode(_BAR, "c1")
    assert loop.mode == "paper"            # NOT switched while a position is open
    assert loop.executor.tag == "paper"
    assert loop._pending_mode == "mainnet"
    assert "mode_switch_deferred" in bridge.kinds()
    assert "mode_switch" not in bridge.kinds()


def test_deferred_switch_applies_once_flat():
    bridge = _ModeBridge("mainnet")
    loop = _loop(bridge, factory=lambda m: _Exec(m), mode="paper")
    loop.ledger.units = 5.0
    loop._sync_trading_mode(_BAR, "c1")    # deferred
    assert loop.mode == "paper"
    loop.ledger.units = 0.0                # position closed
    loop._sync_trading_mode(_BAR, "c2")    # now applies
    assert loop.mode == "mainnet"
    assert loop.executor.tag == "mainnet"
    assert loop._pending_mode is None


def test_deferral_audited_only_once_while_held():
    bridge = _ModeBridge("mainnet")
    loop = _loop(bridge, factory=lambda m: _Exec(m), mode="paper")
    loop.ledger.units = 5.0
    loop._sync_trading_mode(_BAR, "c1")
    loop._sync_trading_mode(_BAR, "c2")
    loop._sync_trading_mode(_BAR, "c3")
    # A long-held position must not spam the audit log every cycle.
    assert sum(1 for k in bridge.kinds() if k == "mode_switch_deferred") == 1


def test_failed_rebuild_keeps_current_mode_and_audits_error():
    def _boom(_m):
        raise RuntimeError("executor build failed")

    bridge = _ModeBridge("mainnet")
    loop = _loop(bridge, factory=_boom, mode="paper")  # flat
    loop._sync_trading_mode(_BAR, "c1")
    assert loop.mode == "paper"            # stayed put — never trade on a broken executor
    assert "error" in bridge.kinds()
