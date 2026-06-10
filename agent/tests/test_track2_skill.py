"""Tests for the Track-2 CMC Skill (signal_score endpoint)."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from agent.skills.track2 import (
    ELIGIBLE_SYMBOLS,
    DEFAULT_LOOKBACK,
    MIN_LOOKBACK,
    MAX_LOOKBACK,
    SKILL_UNIQUE_NAME,
    SignalScoreResult,
    SignalScoreSkill,
    _verdict,
    _strength,
    _utc_now,
)


# ── helper ──────────────────────────────────────────────────────────────────

def _mock_bars(n: int = 80):
    """Build a minimal list of mock Bar objects with non-zero OHLCV."""
    from backtest.engine import Bar
    bars = []
    for i in range(n):
        bars.append(Bar(
            timestamp=float(1_700_000_000_000 + i * 86_400_000),
            open=100.0 + i * 0.1,
            high=101.0 + i * 0.1,
            low=99.0 + i * 0.1,
            close=100.5 + i * 0.1,
            volume=1_000_000.0,
            funding_rate=0.0001,
            open_interest=500_000.0,
            social_score=0.0,
            net_flow=0.0,
        ))
    return bars


# ── unit tests: helpers ────────────────────────────────────────────────────

def test_verdict_buy():
    assert _verdict(0.40, 0.30, -0.10) == "buy"

def test_verdict_sell():
    assert _verdict(-0.15, 0.30, -0.10) == "sell"

def test_verdict_hold_neutral():
    assert _verdict(0.10, 0.30, -0.10) == "hold"

def test_verdict_hold_exact_entry():
    # composite == entry_threshold → NOT a buy (strict >)
    assert _verdict(0.30, 0.30, -0.10) == "hold"

def test_strength_strong():
    assert _strength(0.65) == "strong"
    assert _strength(1.0) == "strong"

def test_strength_moderate():
    assert _strength(0.30) == "moderate"
    assert _strength(0.59) == "moderate"

def test_strength_weak():
    assert _strength(0.0) == "weak"
    assert _strength(0.29) == "weak"

def test_utc_now_is_iso():
    ts = _utc_now()
    dt = datetime.datetime.fromisoformat(ts)
    assert dt.tzinfo is not None


# ── unit tests: SignalScoreResult ─────────────────────────────────────────

def test_result_as_dict_no_error():
    r = SignalScoreResult(
        symbol="ETH", timestamp="2026-06-10T00:00:00+00:00",
        regime="trend", regime_gate=1.0,
        momentum_score=0.42, derivatives_score=0.18,
        sentiment_score=0.0, flow_score=0.0,
        composite_score=0.34, verdict="buy",
        signal_strength="moderate", bars_used=60,
    )
    d = r.as_dict()
    assert "error" not in d
    assert d["verdict"] == "buy"
    assert d["symbol"] == "ETH"

def test_result_as_dict_with_error():
    r = SignalScoreResult(
        symbol="BAD", timestamp="2026-06-10T00:00:00+00:00",
        regime="unknown", regime_gate=0.0,
        momentum_score=0.0, derivatives_score=0.0,
        sentiment_score=0.0, flow_score=0.0,
        composite_score=0.0, verdict="hold",
        signal_strength="weak", bars_used=0,
        error="Symbol not eligible",
    )
    d = r.as_dict()
    assert d["error"] == "Symbol not eligible"


# ── unit tests: SignalScoreSkill ──────────────────────────────────────────

def test_invalid_symbol_returns_error():
    skill = SignalScoreSkill()
    result = skill.compute("INVALID_TOKEN", 60)
    assert result.error is not None
    assert result.verdict == "hold"
    assert result.bars_used == 0

def test_lookback_clamped_to_min():
    """Lookback below MIN is silently clamped."""
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(80)):
        with patch("strategy.combined.score_breakdown", return_value={
            "regime": "trend", "gate": 1.0,
            "momentum": 0.4, "derivatives": 0.2,
            "sentiment": 0.0, "flow": 0.0,
            "raw": 0.33, "target": 0.33,
        }):
            skill = SignalScoreSkill()
            result = skill.compute("ETH", lookback_bars=5)   # below MIN_LOOKBACK=30
            # clamped to 30; bars available = 80 → slice last 30
            assert result.bars_used == 30
            assert result.error is None

def test_lookback_clamped_to_max():
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(260)):
        with patch("strategy.combined.score_breakdown", return_value={
            "regime": "chop", "gate": 0.5,
            "momentum": 0.1, "derivatives": -0.05,
            "sentiment": 0.0, "flow": 0.0,
            "raw": 0.047, "target": 0.023,
        }):
            skill = SignalScoreSkill()
            result = skill.compute("ETH", lookback_bars=999)   # above MAX=200
            assert result.bars_used == 200
            assert result.error is None

def test_data_fetch_failure_returns_error():
    with patch("data.binance_client.BinanceClient.fetch_recent_bars",
               side_effect=ConnectionError("network unavailable")):
        skill = SignalScoreSkill()
        result = skill.compute("ETH", 60)
    assert result.error is not None
    assert "network unavailable" in result.error
    assert result.verdict == "hold"

def test_insufficient_bars_returns_error():
    with patch("data.binance_client.BinanceClient.fetch_recent_bars",
               return_value=_mock_bars(10)):   # < MIN_LOOKBACK
        skill = SignalScoreSkill()
        result = skill.compute("ETH", 60)
    assert result.error is not None
    assert "Insufficient" in result.error

def test_score_computation_failure_returns_error():
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(80)):
        with patch("strategy.combined.score_breakdown", side_effect=RuntimeError("signal crash")):
            skill = SignalScoreSkill()
            result = skill.compute("ETH", 60)
    assert result.error is not None
    assert "signal crash" in result.error

@pytest.mark.parametrize("symbol", list(ELIGIBLE_SYMBOLS))
def test_all_eligible_symbols_accepted(symbol):
    """Every symbol in the allowlist should pass validation (not return an error
    on the symbol check itself)."""
    bd = {
        "regime": "chop", "gate": 0.5,
        "momentum": 0.05, "derivatives": -0.02,
        "sentiment": 0.0, "flow": 0.0,
        "raw": 0.025, "target": 0.012,
    }
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(80)):
        with patch("strategy.combined.score_breakdown", return_value=bd):
            skill = SignalScoreSkill()
            result = skill.compute(symbol, 60)
    assert result.symbol == symbol
    # Error field should not mention "not eligible"
    assert result.error is None or "not eligible" not in result.error

def test_buy_verdict_on_strong_positive():
    bd = {
        "regime": "trend", "gate": 1.0,
        "momentum": 0.80, "derivatives": 0.40,
        "sentiment": 0.0, "flow": 0.0,
        "raw": 0.66, "target": 0.66,
    }
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(80)):
        with patch("strategy.combined.score_breakdown", return_value=bd):
            skill = SignalScoreSkill()
            result = skill.compute("ETH", 60)
    assert result.verdict == "buy"
    assert result.signal_strength == "strong"

def test_sell_verdict_on_crash_regime():
    bd = {
        "regime": "crash", "gate": 0.0,
        "momentum": -0.50, "derivatives": -0.30,
        "sentiment": 0.0, "flow": 0.0,
        "raw": -0.43, "target": 0.0,   # gate=0 zeroes out composite
    }
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(80)):
        with patch("strategy.combined.score_breakdown", return_value=bd):
            skill = SignalScoreSkill()
            result = skill.compute("ETH", 60)
    assert result.regime == "crash"
    assert result.regime_gate == 0.0
    # composite=0.0 → hold (between -0.10 and 0.30)
    assert result.verdict == "hold"

def test_output_schema_keys():
    """Result dict must contain all required output fields."""
    bd = {
        "regime": "trend", "gate": 1.0,
        "momentum": 0.35, "derivatives": 0.15,
        "sentiment": 0.0, "flow": 0.0,
        "raw": 0.28, "target": 0.28,
    }
    required_keys = {
        "symbol", "timestamp", "regime", "regime_gate",
        "momentum_score", "derivatives_score", "sentiment_score", "flow_score",
        "composite_score", "verdict", "signal_strength", "bars_used",
    }
    with patch("data.binance_client.BinanceClient.fetch_recent_bars", return_value=_mock_bars(80)):
        with patch("strategy.combined.score_breakdown", return_value=bd):
            skill = SignalScoreSkill()
            d = skill.compute("ETH", 60).as_dict()
    assert required_keys.issubset(d.keys())


# ── skill identity ─────────────────────────────────────────────────────────

def test_skill_unique_name():
    assert SKILL_UNIQUE_NAME == "alien_trade_multi_signal_score"

def test_manifest_json_loadable():
    import json
    from pathlib import Path
    manifest_path = Path(__file__).parent.parent / "skills" / "skill_manifest.json"
    assert manifest_path.exists(), "skill_manifest.json not found"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["unique_name"] == SKILL_UNIQUE_NAME
    assert "input_schema" in manifest
    assert "output_schema" in manifest
    assert "ETH" in manifest["input_schema"]["properties"]["symbol"]["enum"]
