"""
8.2 Social S3 bridge tests.

Groups:
  1. _inject_sentiment — offline noop, injects score, zero-score noop, error-safe
  2. Parity invariant — bridge None (sim) → history unchanged
  3. Loop integration — score_breakdown sees injected social_score
"""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backtest.engine import Bar


def _bar(ts=1_000_000, social_score=0.0):
    return Bar(timestamp=ts, open=100.0, high=102.0, low=99.0, close=101.0,
               volume=1000.0, social_score=social_score, funding_rate=0.0,
               open_interest=0.0, net_flow=0.0)


def _make_loop(sentiment_row):
    from agent.loop import DecisionLoop
    bridge = MagicMock()
    bridge.get_sentiment_state.return_value = sentiment_row
    loop = object.__new__(DecisionLoop)
    loop.bridge = bridge
    loop.symbol = "ETH"
    return loop, bridge


# ── _inject_sentiment ─────────────────────────────────────────────────────────

def test_inject_offline_noop():
    """bridge returns None (offline/sim) → history unchanged."""
    loop, _ = _make_loop(None)
    history = [_bar()]
    result = loop._inject_sentiment(history, history[-1])
    assert result is history   # same object, untouched


def test_inject_stamps_score():
    """Fresh reading with score=0.6 → last bar social_score = 0.6."""
    loop, _ = _make_loop({"score": 0.6, "confidence": 0.8})
    history = [_bar(), _bar()]
    result = loop._inject_sentiment(history, history[-1])
    assert result[-1].social_score == pytest.approx(0.6)
    # original bar not mutated
    assert history[-1].social_score == pytest.approx(0.0)


def test_inject_zero_score_noop():
    """score=0.0 → no injection (avoids pointless copy)."""
    loop, _ = _make_loop({"score": 0.0, "confidence": 0.9})
    history = [_bar()]
    result = loop._inject_sentiment(history, history[-1])
    assert result is history


def test_inject_preserves_history_prefix():
    """Only the last bar is replaced; earlier bars are untouched."""
    loop, _ = _make_loop({"score": -0.5, "confidence": 0.7})
    b1, b2, b3 = _bar(ts=1), _bar(ts=2), _bar(ts=3)
    result = loop._inject_sentiment([b1, b2, b3], b3)
    assert result[0] is b1
    assert result[1] is b2
    assert result[2].social_score == pytest.approx(-0.5)
    assert len(result) == 3


def test_inject_negative_score():
    """Bearish scores (negative) are injected correctly."""
    loop, _ = _make_loop({"score": -0.8, "confidence": 0.5})
    history = [_bar()]
    result = loop._inject_sentiment(history, history[-1])
    assert result[-1].social_score == pytest.approx(-0.8)


def test_inject_error_safe():
    """bridge.get_sentiment_state raising → history unchanged (never crashes cycle)."""
    from agent.loop import DecisionLoop
    bridge = MagicMock()
    bridge.get_sentiment_state.side_effect = RuntimeError("network")
    loop = object.__new__(DecisionLoop)
    loop.bridge = bridge
    loop.symbol = "ETH"
    history = [_bar()]
    result = loop._inject_sentiment(history, history[-1])
    assert result is history


# ── parity invariant ──────────────────────────────────────────────────────────

def test_parity_sim_social_score_zero():
    """When bridge is offline (sim), injected history keeps social_score=0.0
    — identical to what the backtest sees from historical parquet data."""
    loop, _ = _make_loop(None)
    history = [_bar(social_score=0.0)] * 5
    result = loop._inject_sentiment(history, history[-1])
    assert all(b.social_score == 0.0 for b in result)


# ── score_breakdown sees injected score ───────────────────────────────────────

def test_score_breakdown_reads_injected_score():
    """After injection, score_breakdown receives a bar with non-zero social_score."""
    from strategy.combined import StrategyParams, score_breakdown
    loop, _ = _make_loop({"score": 0.7, "confidence": 0.9})
    history = [_bar()] * 30
    augmented = loop._inject_sentiment(history, history[-1])
    # The last bar must carry the injected score
    assert augmented[-1].social_score == pytest.approx(0.7)
    # score_breakdown must run without error on augmented history
    bd = score_breakdown(augmented, StrategyParams())
    assert "sentiment" in bd
