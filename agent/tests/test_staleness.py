"""
8.11 — Degraded-mode observability: DecisionLoop._check_staleness emits RiskGuard
observation events when forecast or sentiment signals go stale, and clears them on
recovery.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


def _bar(ts_ms: int = 1_000_000):
    return SimpleNamespace(
        timestamp=ts_ms, open=100.0, close=100.0, high=101.0, low=99.0,
        volume=1000.0, social_score=0.0, funding_rate=0.0,
        open_interest=0.0, net_flow=0.0,
    )


def _make_loop(forecast_ts=None, sentiment_ts=None):
    """Minimal DecisionLoop with controllable bridge signal timestamps."""
    from agent.loop import DecisionLoop
    bridge = MagicMock()
    bridge.enabled = False
    bridge.emit_event = MagicMock()

    now_ms = 10_000_000
    bar = _bar(ts_ms=now_ms)

    # Forecast: stale if > 4h old
    if forecast_ts is not None:
        bridge.get_forecast_state.return_value = {"confidence": 0.9, "ts_ms": forecast_ts}
    else:
        bridge.get_forecast_state.return_value = None

    # Sentiment: stale if > 2h old
    if sentiment_ts is not None:
        bridge.get_sentiment_state.return_value = {"score": 0.3, "ts_ms": sentiment_ts}
    else:
        bridge.get_sentiment_state.return_value = None

    loop = object.__new__(DecisionLoop)
    loop.bridge = bridge
    loop.symbol = "ETH"
    loop.notifier = None
    loop._stale_sources = set()
    return loop, bridge, bar


# ── forecast staleness ────────────────────────────────────────────────────────

def test_fresh_forecast_emits_no_event():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(forecast_ts=now_ms - 1 * 3_600_000)  # 1h old
    loop._check_staleness(bar, "cyc-1")
    bridge.emit_event.assert_not_called()


def test_stale_forecast_emits_riskguard_event():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(forecast_ts=now_ms - 5 * 3_600_000)  # 5h old > 4h
    loop._check_staleness(bar, "cyc-1")
    bridge.emit_event.assert_called_once()
    evt = bridge.emit_event.call_args[0][0]
    assert evt.agent == "RiskGuard"
    assert "forecast" in evt.headline.lower()
    assert evt.headline.startswith("STALE")


def test_stale_forecast_recorded_in_stale_sources():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(forecast_ts=now_ms - 5 * 3_600_000)
    loop._check_staleness(bar, "cyc-1")
    assert "forecast" in loop._stale_sources


# ── sentiment staleness ───────────────────────────────────────────────────────

def test_fresh_sentiment_emits_no_event():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(sentiment_ts=now_ms - 1 * 3_600_000)  # 1h old
    loop._check_staleness(bar, "cyc-2")
    bridge.emit_event.assert_not_called()


def test_stale_sentiment_emits_riskguard_event():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(sentiment_ts=now_ms - 3 * 3_600_000)  # 3h old > 2h
    loop._check_staleness(bar, "cyc-2")
    bridge.emit_event.assert_called_once()
    evt = bridge.emit_event.call_args[0][0]
    assert "sentiment" in evt.headline.lower()
    assert evt.headline.startswith("STALE")


# ── deduplication ─────────────────────────────────────────────────────────────

def test_stale_event_emitted_only_once_per_transition():
    """Second call with still-stale data should not re-emit (already in stale_sources)."""
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(forecast_ts=now_ms - 5 * 3_600_000)
    loop._check_staleness(bar, "cyc-1")  # first detection → emit
    loop._check_staleness(bar, "cyc-2")  # still stale → no new emit
    assert bridge.emit_event.call_count == 1


def test_recovery_emits_recovered_event():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(forecast_ts=now_ms - 5 * 3_600_000)
    loop._check_staleness(bar, "cyc-1")          # goes stale
    assert bridge.emit_event.call_count == 1

    # Now the forecast is fresh (recent timestamp)
    loop.bridge.get_forecast_state.return_value = {
        "confidence": 0.9, "ts_ms": now_ms - 1 * 3_600_000,
    }
    loop._check_staleness(bar, "cyc-2")          # recovers
    assert bridge.emit_event.call_count == 2
    recovery_evt = bridge.emit_event.call_args[0][0]
    assert recovery_evt.headline.startswith("RECOVERED")
    assert "forecast" in recovery_evt.headline
    assert "forecast" not in loop._stale_sources  # cleared


# ── no signal data (offline / None) ──────────────────────────────────────────

def test_no_forecast_state_does_not_emit():
    """None from bridge means signal is absent, not stale — don't alarm."""
    loop, bridge, bar = _make_loop(forecast_ts=None)
    loop._check_staleness(bar, "cyc-3")
    bridge.emit_event.assert_not_called()


def test_bridge_exception_is_swallowed():
    """A buggy bridge must not crash a cycle."""
    loop, bridge, bar = _make_loop()
    bridge.get_forecast_state.side_effect = RuntimeError("convex down")
    bridge.get_sentiment_state.side_effect = RuntimeError("convex down")
    loop._check_staleness(bar, "cyc-4")  # must not raise
    bridge.emit_event.assert_not_called()


# ── both signals stale at once ────────────────────────────────────────────────

def test_both_stale_emits_two_events():
    now_ms = 10_000_000
    loop, bridge, bar = _make_loop(
        forecast_ts=now_ms - 5 * 3_600_000,
        sentiment_ts=now_ms - 3 * 3_600_000,
    )
    loop._check_staleness(bar, "cyc-5")
    assert bridge.emit_event.call_count == 2
    headlines = {bridge.emit_event.call_args_list[i][0][0].headline for i in range(2)}
    assert any("forecast" in h for h in headlines)
    assert any("sentiment" in h for h in headlines)
