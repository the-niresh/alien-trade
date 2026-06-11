"""Strategy Registry — named presets over one engine (offline)."""
from __future__ import annotations

import pytest

from strategy.combined import StrategyParams, make_strategy
from strategy.registry import (
    DEFAULT_STRATEGY, RISK_PROFILES, STRATEGIES,
    get_risk_profile, get_strategy_params, list_strategies,
)


def test_all_strategies_build_valid_params():
    for name in STRATEGIES:
        p = get_strategy_params(name, symbol="UNI")
        assert isinstance(p, StrategyParams)
        assert p.symbol == "UNI"
        # weights are non-negative and sum to ~1.0 (anti-overfit: a real allocation)
        total = p.w_momentum + p.w_derivatives + p.w_sentiment
        assert 0.95 <= total <= 1.05
        # each preset must produce a usable strategy closure
        assert callable(make_strategy(p))


def test_contrarian_is_fear_led():
    p = get_strategy_params("contrarian")
    assert p.w_sentiment > p.w_momentum   # F&G is the backbone, momentum only filters


def test_momentum_has_no_sentiment():
    p = get_strategy_params("momentum")
    assert p.w_sentiment == 0.0


def test_defensive_is_high_conviction():
    d = get_strategy_params("defensive")
    m = get_strategy_params("momentum")
    assert d.entry_threshold > m.entry_threshold   # rarer entries
    assert d.rebalance_band >= m.rebalance_band     # lower turnover


def test_unknown_strategy_falls_back_not_raises():
    p = get_strategy_params("does-not-exist")
    assert p == get_strategy_params(DEFAULT_STRATEGY)


def test_case_insensitive():
    assert get_strategy_params("CONTRARIAN").w_sentiment == get_strategy_params("contrarian").w_sentiment


def test_risk_profiles_ordered():
    c = get_risk_profile("conservative")
    b = get_risk_profile("balanced")
    a = get_risk_profile("aggressive")
    assert c.max_position_pct < b.max_position_pct < a.max_position_pct
    assert c.target_vol_ann < b.target_vol_ann < a.target_vol_ann


def test_unknown_risk_profile_falls_back():
    assert get_risk_profile("nope").name == "balanced"


def test_list_strategies_payload():
    rows = list_strategies()
    assert len(rows) == len(STRATEGIES)
    assert all({"name", "label", "blurb"} <= set(r) for r in rows)
