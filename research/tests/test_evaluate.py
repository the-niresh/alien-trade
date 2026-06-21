"""Tests for the thesis evaluation harness (research/evaluate.py).

This is the keystone that turns a distilled thesis card's `proposed_rule` (DSL) into a
per-asset out-of-sample scorecard over the eligible universe, using the SHARED /core
engine + the real BSC cost model (locked decision #2: no separate sim path). All tests
are offline/deterministic — bars are injected, never fetched.
"""
from __future__ import annotations

import numpy as np
import pytest

from backtest.engine import Bar
from research.evaluate import (
    AssetResult,
    ThesisEval,
    _positions,
    evaluate_on_bars,
    evaluate_thesis,
    format_ledger_row,
    objective,
    rule_to_strategy,
)

_HOUR_MS = 3_600_000


def _bars(prices: list[float], vol: float = 1000.0) -> list[Bar]:
    t0 = 1_600_000_000_000
    return [
        Bar(timestamp=t0 + i * _HOUR_MS, open=p, high=p * 1.001, low=p * 0.999,
            close=p, volume=vol)
        for i, p in enumerate(prices)
    ]


def test_objective_is_the_rubric_formula():
    # objective = sortino - 2*|maxDD|  (locked decision #6)
    assert objective(1.0, -0.1) == pytest.approx(0.8)
    assert objective(0.0, 0.0) == 0.0
    assert objective(-0.2, -0.05) == pytest.approx(-0.3)


def test_always_false_rule_never_enters_and_scores_like_cash():
    bars = _bars([100, 101, 102, 103, 104] * 40)
    rule = {"entry": "close<0", "exit": "close>0"}  # entry can never be true
    res = evaluate_on_bars(rule, bars, asset="TEST")
    assert isinstance(res, AssetResult)
    assert res.n_fills == 0
    assert res.total_return == 0.0
    assert res.objective == 0.0  # flat-in-cash is the 0.0 bar every thesis must beat


def test_buy_and_hold_on_uptrend_makes_money():
    prices = list(np.linspace(100.0, 200.0, 400))
    bars = _bars(prices)
    rule = {"entry": "close>0", "exit": "close<0"}  # always in
    res = evaluate_on_bars(rule, bars, asset="TEST")
    assert res.n_fills >= 1
    assert res.total_return > 0.0


def test_positions_are_causal_no_lookahead():
    # Position at bar i must depend ONLY on bars[0..i]. Recomputing on a prefix must
    # yield the identical positions for that prefix (the anti-lookahead guarantee).
    prices = list(np.linspace(100, 200, 50)) + list(np.linspace(200, 110, 50))
    bars = _bars(prices)
    rule = {"entry": "close>ema10", "exit": "close<ema10"}
    full = list(_positions(rule, bars))
    for k in (20, 40, 70, 90):
        prefix = list(_positions(rule, bars[:k]))
        assert prefix == full[:k], f"lookahead at prefix length {k}"


def test_evaluate_thesis_falsified_does_not_touch_holdout():
    bars = {a: _bars(list(np.linspace(100, 200, 400)))
            for a in ("ETH", "CAKE", "UNI", "LINK", "AAVE")}
    rule = {"entry": "close>0", "exit": "close<0"}
    ev = evaluate_thesis(rule, bars_by_asset=bars, threshold=1e9, min_beat=4)
    assert isinstance(ev, ThesisEval)
    assert ev.n_assets == 5
    assert ev.verdict == "FALSIFIED"
    assert ev.n_beat == 0
    assert ev.holdout is None          # untouched until a thesis survives the gate
    assert ev.deflated_sharpe is None


def test_evaluate_thesis_validated_runs_holdout_once():
    bars = {a: _bars(list(np.linspace(100, 200, 400)))
            for a in ("ETH", "CAKE", "UNI", "LINK", "AAVE")}
    rule = {"entry": "close>0", "exit": "close<0"}
    ev = evaluate_thesis(rule, bars_by_asset=bars, threshold=-1e9, min_beat=4,
                         n_trials=10)
    assert ev.verdict == "VALIDATED"
    assert ev.n_beat == 5
    assert ev.holdout is not None       # survivor -> the reserved tail is scored once
    assert "objective" in ev.holdout
    assert ev.deflated_sharpe is not None
    assert 0.0 <= ev.deflated_sharpe <= 1.0


def test_format_ledger_row_is_one_markdown_table_line():
    bars = {a: _bars(list(np.linspace(100, 200, 400)))
            for a in ("ETH", "CAKE", "UNI", "LINK", "AAVE")}
    rule = {"entry": "close>0", "exit": "close<0"}
    ev = evaluate_thesis(rule, bars_by_asset=bars, threshold=1e9, min_beat=4)
    row = format_ledger_row("T-099", "always-in test", "unit-test", ev)
    assert row.startswith("| T-099 ")
    assert "FALSIFIED" in row
    assert row.count("|") >= 8        # a full pipe-delimited table row
    assert "\n" not in row.strip()    # exactly one line


def test_per_asset_results_carry_full_scorecard_fields():
    bars = _bars(list(np.linspace(100, 130, 300)))
    rule = {"entry": "close>0", "exit": "close<0"}
    res = evaluate_on_bars(rule, bars, asset="ETH")
    # objective must equal the rubric formula applied to this card's own sortino/maxDD
    assert res.objective == pytest.approx(objective(res.sortino, res.max_drawdown),
                                          abs=1e-4)
