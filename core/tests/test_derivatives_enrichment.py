"""Derivatives enrichment - unit tests for funding rate + OI merge (offline, no network)."""
from __future__ import annotations
import polars as pl
import pytest


def _merge_derivatives_fn():
    from data.binance_client import _merge_derivatives
    return _merge_derivatives


def _df(n: int = 10, start_ms: int = 0, step_ms: int = 3_600_000) -> pl.DataFrame:
    """Minimal OHLCV-shaped dataframe with stubbed S2 fields."""
    ts = [start_ms + i * step_ms for i in range(n)]
    return pl.DataFrame({
        "timestamp_ms":  ts,
        "open":          [100.0] * n,
        "high":          [110.0] * n,
        "low":           [90.0]  * n,
        "close":         [105.0] * n,
        "volume":        [1000.0] * n,
        "funding_rate":  [0.0] * n,
        "open_interest": [0.0] * n,
        "social_score":  [0.0] * n,
        "net_flow":      [0.0] * n,
    })


# ── forward-fill funding rate ─────────────────────────────────────────────────

def test_funding_rate_forward_filled():
    df = _df(n=9, start_ms=0, step_ms=3_600_000)   # hourly bars 0h-8h
    # Funding rate settled at t=0 (rate 0.0001) and t=28800000 (8h, rate -0.0002)
    funding = [
        {"fundingTime": 0,          "fundingRate": 0.0001},
        {"fundingTime": 28_800_000, "fundingRate": -0.0002},
    ]
    result = _merge_derivatives_fn()(df, funding, [])
    rates = result["funding_rate"].to_list()
    # Bars 0-7 (t=0h to t=7h) should carry the first settlement rate 0.0001
    assert all(abs(r - 0.0001) < 1e-9 for r in rates[:8]), rates[:8]
    # Bar 8 (t=8h = 28800000) gets the second settlement rate
    assert abs(rates[8] - (-0.0002)) < 1e-9, rates[8]


def test_funding_rate_no_data_stays_zero():
    df = _df(n=5)
    result = _merge_derivatives_fn()(df, [], [])
    assert result["funding_rate"].to_list() == [0.0] * 5


def test_funding_rate_before_first_settlement_is_zero():
    df = _df(n=3, start_ms=0, step_ms=3_600_000)
    # Settlement is at t=7200000 (bar index 2); bars 0 and 1 have no settlement yet
    funding = [{"fundingTime": 7_200_000, "fundingRate": 0.0005}]
    result = _merge_derivatives_fn()(df, funding, [])
    rates = result["funding_rate"].to_list()
    assert rates[0] == 0.0  # no settlement yet
    assert rates[1] == 0.0
    assert abs(rates[2] - 0.0005) < 1e-9


# ── open interest alignment ───────────────────────────────────────────────────

def test_oi_aligned_to_nearest_hourly():
    step = 3_600_000
    df = _df(n=4, start_ms=0, step_ms=step)
    oi = [
        {"timestamp": 0,        "sumOpenInterest": 100_000.0},
        {"timestamp": step,     "sumOpenInterest": 110_000.0},
        {"timestamp": step * 2, "sumOpenInterest": 120_000.0},
        {"timestamp": step * 3, "sumOpenInterest": 130_000.0},
    ]
    result = _merge_derivatives_fn()(df, [], oi)
    vals = result["open_interest"].to_list()
    assert vals == [100_000.0, 110_000.0, 120_000.0, 130_000.0]


def test_oi_skips_stale_snapshot_beyond_1h():
    step = 3_600_000
    df = _df(n=3, start_ms=2 * step, step_ms=step)  # bars at 2h, 3h, 4h
    # OI snapshot only at t=0h - more than 1h away from bar at t=2h
    oi = [{"timestamp": 0, "sumOpenInterest": 99_000.0}]
    result = _merge_derivatives_fn()(df, [], oi)
    vals = result["open_interest"].to_list()
    assert vals == [0.0, 0.0, 0.0]   # too stale, not applied


def test_oi_uses_most_recent_snapshot_before_bar():
    step = 3_600_000
    df = _df(n=2, start_ms=step, step_ms=step)  # bars at 1h, 2h
    oi = [
        {"timestamp": 0,    "sumOpenInterest": 50_000.0},
        {"timestamp": step, "sumOpenInterest": 60_000.0},
    ]
    result = _merge_derivatives_fn()(df, [], oi)
    vals = result["open_interest"].to_list()
    # Bar at 1h matches snapshot at 1h exactly
    # Bar at 2h: most recent snapshot at 1h (within 1h)
    assert abs(vals[0] - 60_000.0) < 1e-9
    assert abs(vals[1] - 60_000.0) < 1e-9


# ── both signals combined ─────────────────────────────────────────────────────

def test_both_signals_merged_independently():
    step = 3_600_000
    df = _df(n=3, start_ms=0, step_ms=step)
    funding = [{"fundingTime": 0, "fundingRate": 0.0003}]
    oi = [
        {"timestamp": 0,    "sumOpenInterest": 200_000.0},
        {"timestamp": step, "sumOpenInterest": 210_000.0},
    ]
    result = _merge_derivatives_fn()(df, funding, oi)
    assert all(abs(r - 0.0003) < 1e-9 for r in result["funding_rate"].to_list())
    assert result["open_interest"].to_list()[0] == 200_000.0
    assert result["open_interest"].to_list()[1] == 210_000.0


def test_empty_both_returns_unchanged_df():
    df = _df(n=4)
    result = _merge_derivatives_fn()(df, [], [])
    assert result["funding_rate"].to_list() == [0.0] * 4
    assert result["open_interest"].to_list() == [0.0] * 4


def test_schema_preserved_after_merge():
    df = _df(n=3)
    funding = [{"fundingTime": 0, "fundingRate": 0.001}]
    result = _merge_derivatives_fn()(df, funding, [])
    expected_cols = {"timestamp_ms", "open", "high", "low", "close", "volume",
                     "funding_rate", "open_interest", "social_score", "net_flow"}
    assert set(result.columns) == expected_cols
