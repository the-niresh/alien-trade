"""Equity Floor Guard — guardrail unit tests + loop integration."""
from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from risk.guardrails import check_equity_floor, EquityFloorCheck


# ── check_equity_floor ────────────────────────────────────────────────────────

def test_floor_zero_is_noop():
    r = check_equity_floor(10.0, 0)
    assert not r.halt and not r.warn

def test_below_floor_halts():
    r = check_equity_floor(49.0, 50.0)
    assert r.halt and not r.warn
    assert "49.00" in r.reason and "50.00" in r.reason

def test_at_floor_halts():
    r = check_equity_floor(50.0, 50.0)
    assert r.halt

def test_warn_at_120_pct():
    r = check_equity_floor(59.0, 50.0)   # 59 <= 50*1.20=60
    assert not r.halt and r.warn

def test_no_warn_above_120_pct():
    r = check_equity_floor(61.0, 50.0)   # 61 > 60
    assert not r.halt and not r.warn

def test_floor_negative_is_noop():
    r = check_equity_floor(1.0, -10.0)
    assert not r.halt and not r.warn


# ── loop integration ──────────────────────────────────────────────────────────

def _make_loop(equity_floor=50.0, equity=45.0, is_halted=False):
    """Build a minimal DecisionLoop mock with a bridge that returns given values."""
    from agent.loop import DecisionLoop
    bridge = MagicMock()
    bridge.get_equity_floor.return_value = equity_floor
    bridge.is_halted.return_value = is_halted
    bridge.enabled = False
    ledger = MagicMock()
    ledger.mark.return_value = equity
    ledger.cash = equity
    ledger.open_exposure.return_value = 0.0
    ledger.daily_loss_usd.return_value = 0.0
    ledger.drawdown_pct.return_value = 0.0
    ledger.peak_equity = equity
    ledger.consecutive_losses = 0
    ledger.roll_day = MagicMock()
    loop = object.__new__(DecisionLoop)
    loop.bridge = bridge
    loop.ledger = ledger
    loop.symbol = "ETH"
    loop.mode = "paper"
    loop.enforce_activity_floor = False
    loop._activity_day = -1
    loop._trades_today = 0
    loop.max_consecutive_losses = 5
    loop._cycles_total = 0
    loop._blocks_fired = 0
    loop._kill_switch_activations = 0
    loop._circuit_breaker_activations = 0
    loop._peak_exposure_pct = 0.0
    loop._was_halted = False
    loop._was_circuit = False
    loop.notifier = None
    loop._halted_by_floor = False
    loop._daily_pnl_start = equity
    loop._daily_max_dd = 0.0
    loop._stale_sources = set()
    # sustained-failure watchdog state (set in real __init__; this fixture bypasses it)
    loop._first_exec_failure_ms = None
    loop._sustained_warn_sent = False
    return loop, bridge


def _bar():
    return SimpleNamespace(timestamp=1_000_000, open=100.0, close=100.0, high=101.0, low=99.0,
                           volume=1000.0, social_score=0.0, funding_rate=0.0,
                           open_interest=0.0, net_flow_usd=0.0)


def test_floor_halt_sets_halted_and_returns_early():
    loop, bridge = _make_loop(equity_floor=50.0, equity=45.0)
    halted = loop._check_equity_floor(_bar(), "cyc-1")
    assert halted is True
    bridge.set_halted.assert_called_once_with(True)


def test_floor_warn_does_not_halt():
    loop, bridge = _make_loop(equity_floor=50.0, equity=58.0)  # 58 <= 60
    halted = loop._check_equity_floor(_bar(), "cyc-2")
    assert halted is False
    bridge.set_halted.assert_not_called()


def test_floor_zero_skips_bridge_call():
    loop, bridge = _make_loop(equity_floor=0.0, equity=5.0)
    halted = loop._check_equity_floor(_bar(), "cyc-3")
    assert halted is False
    bridge.set_halted.assert_not_called()


def test_floor_above_equity_returns_halted_cycle():
    """_check_equity_floor returning True causes run_cycle to return halted result."""
    loop, bridge = _make_loop(equity_floor=50.0, equity=40.0)
    bar = _bar()
    fake_bd = {"target": 0.0, "momentum": 0.0, "derivatives": 0.0,
               "sentiment": 0.0, "flow": 0.0, "composite": 0.0}
    with patch.object(loop, "_finalise") as mock_fin, \
         patch.object(loop, "_sync_trading_mode"), \
         patch("agent.loop.detect_regime", return_value=SimpleNamespace(value="chop")), \
         patch("agent.loop.score_breakdown", return_value=fake_bd):
        loop.ledger.roll_day = MagicMock()
        loop.params = MagicMock()
        loop.base_position_usd = 100.0
        loop.run_cycle([bar])
    mock_fin.assert_called_once()
    _, kwargs = mock_fin.call_args
    assert kwargs.get("halted") is True
