"""
Live scorecard wiring — the loop accumulates the same shapes core/scorecard.py
scores in sim and pushes the objective to Convex each cycle. Pins: a scorecard is
upserted every cycle, trades are paired from real fills, and the live objective
equals what compute_scorecard() produces from the loop's own series.
"""
from __future__ import annotations

import numpy as np

from backtest.costs import BSCCostModel
from risk.engine import make_risk_strategy
from risk.guardrails import RiskConfig
from scorecard import compute_scorecard
from strategy.combined import StrategyParams, make_strategy

from backtest.engine import Bar
from agent.convex_bridge import ConvexBridge
from agent.executor import PaperExecutor
from agent.feed import ReplayFeed
from agent.loop import DecisionLoop


def _bars(n: int, start: float = 300.0, trend: float = 1.004, vol: float = 0.012, seed: int = 42):
    rng = np.random.default_rng(seed)
    bars, price = [], start
    for i in range(n):
        price *= trend * (1 + rng.normal(0, vol))
        bars.append(Bar(
            timestamp=1_700_000_000_000 + i * 86_400_000,
            open=price * 0.999, high=price * 1.01,
            low=price * 0.99, close=price, volume=5_000_000.0,
        ))
    return bars


def _run_loop():
    bars = _bars(150)
    params = StrategyParams(s1_fast=5, s1_slow=21, entry_threshold=0.10,
                            position_size_usd=1_000.0)
    risk = RiskConfig()
    strat = make_risk_strategy(make_strategy(params), risk, initial_capital=10_000.0)
    bridge = ConvexBridge(url="")   # offline → writes captured in _offline_log
    loop = DecisionLoop(
        feed=ReplayFeed(bars), strategy=strat,
        executor=PaperExecutor(cost_model=BSCCostModel()), bridge=bridge,
        params=params, symbol="BNB", mode="paper", initial_capital=10_000.0,
        base_position_usd=risk.base_position_usd,
    )
    results = loop.run()
    return loop, results, bridge


def test_scorecard_pushed_every_cycle():
    loop, results, bridge = _run_loop()
    pushes = sum(1 for e in bridge._offline_log if e["path"] == "scorecard:update")
    assert pushes == len(results)  # one upsert per finalised cycle


def test_trades_paired_from_real_fills():
    loop, results, _ = _run_loop()
    card = loop.build_scorecard()
    # The loop pairs a Trade on each sell that closes an entry; at least one round-trip.
    assert card.n_trades == len(loop._trades)
    assert card.n_trades > 0


def test_live_objective_matches_compute_from_series():
    loop, _, _ = _run_loop()
    card = loop.build_scorecard()
    # Re-derive straight from the loop's accumulated series — must be identical.
    ref = compute_scorecard(
        loop._equity_curve, loop._trades, loop._fills, loop._initial_capital,
        timestamps=loop._equity_ts, exposure_curve=loop._exposure_curve,
    )
    assert card.objective == ref.objective
    assert card.sortino == ref.sortino
    assert card.max_drawdown == ref.max_drawdown


def test_convex_row_serialises_and_carries_facts():
    import json
    loop, _, _ = _run_loop()
    row = loop.build_scorecard().as_convex_row()
    json.dumps(row)  # fully serialisable for the HTTP mutation
    assert row["rule_adherence_clean"] is True          # no violations in paper
    # exposure lines populated because the loop supplies an exposure curve
    assert row["peak_exposure_pct"] is not None
    assert json.loads(row["operational"])["cycles_total"] > 0
