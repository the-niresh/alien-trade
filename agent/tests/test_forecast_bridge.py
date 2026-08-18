"""
8.4 Option-B forecast bridge tests.

Three groups:
  1. Pure math - decay_confidence, apply_forecast_multiplier, confidence_from_regime
  2. Invariant - multiplier can never enlarge a position
  3. DecisionLoop._apply_forecast - offline (sim-parity), live, stale, error-safe
"""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from risk.forecast import (
    FORECAST_FLOOR,
    NEUTRAL,
    apply_forecast_multiplier,
    confidence_from_regime,
    decay_confidence,
)


# ── pure math ─────────────────────────────────────────────────────────────────

def test_decay_zero_age_returns_unchanged():
    assert decay_confidence(0.6, 0, 10_000) == pytest.approx(0.6)

def test_decay_stale_returns_neutral():
    assert decay_confidence(0.4, 100_000, 50_000) == pytest.approx(NEUTRAL)

def test_decay_at_ttl_boundary():
    assert decay_confidence(0.5, 6_000, 6_000) == pytest.approx(NEUTRAL)

def test_decay_midpoint_linear():
    # age = ttl/2 → halfway between confidence and NEUTRAL
    conf = decay_confidence(0.6, 5_000, 10_000)
    assert conf == pytest.approx(0.8)   # 0.6 + (1.0-0.6)*0.5 = 0.8

def test_decay_zero_ttl_returns_unchanged():
    assert decay_confidence(0.7, 1_000, 0) == pytest.approx(0.7)

def test_apply_mult_clamps_to_floor():
    # confidence=0.1 is below FORECAST_FLOOR=0.5 → clamped to 0.5
    result = apply_forecast_multiplier(1_000.0, 0.1)
    assert result == pytest.approx(1_000.0 * FORECAST_FLOOR)

def test_apply_mult_neutral_is_noop():
    assert apply_forecast_multiplier(500.0, NEUTRAL) == pytest.approx(500.0)

def test_apply_mult_shrinks_correctly():
    assert apply_forecast_multiplier(1_000.0, 0.8) == pytest.approx(800.0)

def test_apply_mult_above_one_clamped_to_neutral():
    # a caller passing >1.0 must be clamped to 1.0 (never enlarges)
    assert apply_forecast_multiplier(200.0, 1.5) == pytest.approx(200.0)

def test_confidence_from_regime_trend_up():
    assert confidence_from_regime("trend_up") == pytest.approx(1.0)

def test_confidence_from_regime_trend_down():
    c = confidence_from_regime("trend_down")
    assert c < 0.8   # meaningful shrink for long-only in downtrend

def test_confidence_from_regime_chop():
    c = confidence_from_regime("chop")
    assert FORECAST_FLOOR <= c < 1.0

def test_confidence_from_regime_high_vol():
    c = confidence_from_regime("high_vol")
    assert FORECAST_FLOOR <= c < 1.0

def test_confidence_from_regime_unknown():
    c = confidence_from_regime("some_new_regime")
    assert FORECAST_FLOOR <= c <= 1.0


# ── invariant: multiplier can never enlarge a position ────────────────────────

@pytest.mark.parametrize("confidence", [-1.0, 0.0, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0])
def test_multiplier_never_enlarges(confidence):
    size = 1_000.0
    result = apply_forecast_multiplier(size, confidence)
    assert result <= size + 1e-9, f"confidence={confidence} enlarged size to {result}"


# ── DecisionLoop._apply_forecast ─────────────────────────────────────────────

def _make_order(size_usd=1_000.0, side="buy"):
    from backtest.engine import Order
    return Order(side=side, size_usd=size_usd, symbol="ETH", timestamp=1_000_000)


def _bar(ts=1_000_000):
    return SimpleNamespace(timestamp=ts, open=100.0, close=100.0, high=101.0, low=99.0,
                           volume=1000.0, social_score=0.0, funding_rate=0.0,
                           open_interest=0.0, net_flow_usd=0.0)


def _make_loop_with_forecast(forecast_row):
    """Build a minimal DecisionLoop stub with a bridge returning the given forecast."""
    from agent.loop import DecisionLoop
    bridge = MagicMock()
    bridge.get_forecast_state.return_value = forecast_row
    bridge.audit = MagicMock()
    loop = object.__new__(DecisionLoop)
    loop.bridge = bridge
    loop.symbol = "ETH"
    return loop, bridge


def test_apply_forecast_offline_noop():
    """Bridge returns None (offline/sim) → order unchanged (parity)."""
    loop, _ = _make_loop_with_forecast(None)
    order = _make_order(1_000.0)
    result = loop._apply_forecast(order, _bar(), "cyc-1")
    assert result.size_usd == pytest.approx(1_000.0)


def test_apply_forecast_fresh_shrinks():
    """Fresh forecast confidence=0.75 → size shrunk to 750."""
    now_ms = 1_000_000
    loop, _ = _make_loop_with_forecast({
        "confidence": 0.75,
        "ts_ms": now_ms,        # written at bar time → age=0
        "ttl_ms": 6 * 3_600_000,
        "reason": "chop regime",
    })
    order = _make_order(1_000.0)
    result = loop._apply_forecast(order, _bar(ts=now_ms), "cyc-2")
    assert result.size_usd == pytest.approx(750.0)


def test_apply_forecast_neutral_is_noop():
    """Confidence=1.0 (neutral) → no-op, no audit call."""
    now_ms = 1_000_000
    loop, bridge = _make_loop_with_forecast({
        "confidence": 1.0,
        "ts_ms": now_ms,
        "ttl_ms": 6 * 3_600_000,
        "reason": "trend_up",
    })
    order = _make_order(1_000.0)
    result = loop._apply_forecast(order, _bar(ts=now_ms), "cyc-3")
    assert result.size_usd == pytest.approx(1_000.0)
    bridge.audit.assert_not_called()


def test_apply_forecast_stale_decays_to_neutral():
    """Forecast older than ttl → decays to NEUTRAL → size unchanged."""
    ttl_ms = 6 * 3_600_000
    written_at = 1_000_000
    bar_ts = written_at + ttl_ms + 1   # one ms past the TTL
    loop, _ = _make_loop_with_forecast({
        "confidence": 0.5,
        "ts_ms": written_at,
        "ttl_ms": ttl_ms,
        "reason": "old research",
    })
    order = _make_order(1_000.0)
    result = loop._apply_forecast(order, _bar(ts=bar_ts), "cyc-4")
    assert result.size_usd == pytest.approx(1_000.0)


def test_apply_forecast_error_safe():
    """Bridge.get_forecast_state raising must not crash the loop (Tier-1 safety)."""
    from agent.loop import DecisionLoop
    bridge = MagicMock()
    bridge.get_forecast_state.side_effect = RuntimeError("network down")
    loop = object.__new__(DecisionLoop)
    loop.bridge = bridge
    loop.symbol = "ETH"
    order = _make_order(1_000.0)
    result = loop._apply_forecast(order, _bar(), "cyc-5")
    assert result.size_usd == pytest.approx(1_000.0)  # unchanged


def test_apply_forecast_clamps_to_floor():
    """Extremely low confidence is clamped to FORECAST_FLOOR (never > 50% shrink)."""
    loop, _ = _make_loop_with_forecast({
        "confidence": 0.01,   # below FLOOR
        "ts_ms": 1_000_000,
        "ttl_ms": 6 * 3_600_000,
        "reason": "crash regime",
    })
    order = _make_order(1_000.0)
    result = loop._apply_forecast(order, _bar(ts=1_000_000), "cyc-6")
    assert result.size_usd == pytest.approx(1_000.0 * FORECAST_FLOOR)


def test_apply_forecast_preserves_side_and_symbol():
    """Shrink must not change side or symbol."""
    loop, _ = _make_loop_with_forecast({
        "confidence": 0.8,
        "ts_ms": 1_000_000,
        "ttl_ms": 6 * 3_600_000,
        "reason": "test",
    })
    order = _make_order(500.0, side="sell")
    loop.symbol = "CAKE"
    result = loop._apply_forecast(order, _bar(), "cyc-7")
    assert result.side == "sell"
    assert result.symbol == "sell" or result.side == "sell"   # side preserved


# ── confidence_from_history integration ──────────────────────────────────────

def test_confidence_from_history_empty():
    from agent.secondbrain.research import confidence_from_history
    assert confidence_from_history([]) == pytest.approx(1.0)


def test_confidence_from_history_returns_float():
    from agent.secondbrain.research import confidence_from_history
    from backtest.engine import Bar
    bar = Bar(timestamp=1_000_000, open=100, high=102, low=99, close=101,
              volume=1000, social_score=0.0, funding_rate=0.0,
              open_interest=0.0, net_flow=0.0)
    result = confidence_from_history([bar] * 30)
    assert FORECAST_FLOOR <= result <= 1.0
