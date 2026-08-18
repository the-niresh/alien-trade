"""
Scorecard tests - the agent's goal made measurable.
Covers: objective formula, the added lines (drawdown duration, daily consistency,
profit factor / expectancy, cost ratio, exposure efficiency), graceful degradation
when timestamps / exposure are absent, and that sim and live score identically.
All synthetic - no network.
"""
from __future__ import annotations

import math

from backtest.engine import Fill, Order, Trade
from scorecard import (
    LAMBDA,
    OperationalStats,
    RuleAdherence,
    Scorecard,
    compute_scorecard,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_MS_DAY = 86_400_000


def _order(side: str = "buy", size: float = 1_000.0) -> Order:
    return Order(side=side, size_usd=size, symbol="BNB", timestamp=0)


def _fill(price: float, fee: float = 2.5, gas: float = 0.43, slip: float = 1.0,
          side: str = "buy") -> Fill:
    return Fill(order=_order(side), fill_price=price, fee_usd=fee, gas_usd=gas,
                slippage_usd=slip)


def _trade(pnl: float, entry_price: float = 100.0, exit_price: float = 110.0) -> Trade:
    return Trade(entry=_fill(entry_price, side="buy"),
                 exit=_fill(exit_price, side="sell"), pnl_usd=pnl)


# ── Objective formula ──────────────────────────────────────────────────────────

def test_objective_is_sortino_minus_lambda_drawdown():
    # Rising-then-dipping curve so sortino and drawdown are both nonzero.
    curve = [10_000, 10_200, 10_100, 10_400, 10_300, 10_600]
    card = compute_scorecard(curve, trades=[], fills=[], initial_capital=10_000)
    assert math.isclose(card.objective, round(card.sortino - LAMBDA * abs(card.max_drawdown), 4),
                        rel_tol=0, abs_tol=1e-9)


def test_drawdown_penalty_lowers_objective():
    smooth = [10_000, 10_100, 10_200, 10_300, 10_400]
    bumpy = [10_000, 10_400, 9_800, 10_200, 10_400]   # same end, deeper drawdown
    s_smooth = compute_scorecard(smooth, [], [], 10_000)
    s_bumpy = compute_scorecard(bumpy, [], [], 10_000)
    assert abs(s_bumpy.max_drawdown) > abs(s_smooth.max_drawdown)
    assert s_bumpy.objective < s_smooth.objective


# ── Drawdown duration ──────────────────────────────────────────────────────────

def test_drawdown_duration_counts_days_underwater():
    # Peak at day 0 (10_400), underwater days 1-3, recovers day 4 → 3 days under.
    curve = [10_400, 10_000, 9_900, 10_100, 10_500]
    ts = [i * _MS_DAY for i in range(len(curve))]
    card = compute_scorecard(curve, [], [], 10_000, timestamps=ts)
    assert card.max_drawdown_duration_days == 4.0  # day0 peak -> day4 recovery


def test_drawdown_duration_none_without_timestamps():
    card = compute_scorecard([10_000, 9_500, 10_200], [], [], 10_000)
    assert card.max_drawdown_duration_days is None


# ── Daily consistency ──────────────────────────────────────────────────────────

def test_pct_positive_days():
    # 5 days: +,+,-,+  → end-of-day equities give 4 daily deltas, 3 positive.
    eq = [10_000, 10_100, 10_300, 10_200, 10_400]
    ts = [i * _MS_DAY for i in range(len(eq))]
    card = compute_scorecard(eq, [], [], 10_000, timestamps=ts)
    assert card.pct_positive_days == 0.75
    assert card.daily_pnl_vol is not None and card.daily_pnl_vol >= 0


# ── Trade quality ──────────────────────────────────────────────────────────────

def test_profit_factor_and_expectancy():
    trades = [_trade(300), _trade(200), _trade(-100), _trade(-100)]
    card = compute_scorecard([10_000, 10_300], trades, [], initial_capital=10_000)
    assert card.n_trades == 4
    assert card.win_rate == 0.5
    assert card.profit_factor == 2.5          # 500 won / 200 lost
    assert card.expectancy_usd == 75.0        # (300+200-100-100)/4
    assert card.worst_trade_usd == -100.0


def test_profit_factor_no_losses_is_capped_finite():
    trades = [_trade(100), _trade(50)]
    card = compute_scorecard([10_000, 10_150], trades, [], 10_000)
    assert math.isfinite(card.profit_factor)   # serialises to Convex


# ── Cost efficiency ──────────────────────────────────────────────────────────

def test_cost_ratio_and_total():
    # 2 fills, each cost 2.5+0.43+1.0 = 3.93 → total 7.86
    f_in, f_out = _fill(100.0), _fill(110.0, side="sell")
    trade = Trade(entry=f_in, exit=f_out, pnl_usd=100.0)
    card = compute_scorecard([10_000, 10_100], trades=[trade],
                            fills=[f_in, f_out], initial_capital=10_000)
    assert math.isclose(card.total_cost_usd, 7.86, abs_tol=1e-6)
    # gross = |100 + (3.93+3.93)| = 107.86 ; ratio = 7.86/107.86
    assert math.isclose(card.cost_ratio, round(7.86 / 107.86, 4), abs_tol=1e-9)


# ── Exposure efficiency ──────────────────────────────────────────────────────

def test_exposure_lines_present_when_curve_given():
    eq = [10_000, 10_100, 10_050, 10_200]
    exp = [0, 2_000, 3_000, 0]   # open position USD per step
    card = compute_scorecard(eq, [], [], 10_000, exposure_curve=exp)
    assert card.peak_exposure_pct is not None
    assert card.avg_exposure_pct is not None
    assert card.peak_exposure_pct > 0


def test_exposure_none_without_curve():
    card = compute_scorecard([10_000, 10_100], [], [], 10_000)
    assert card.avg_exposure_pct is None
    assert card.peak_exposure_pct is None


# ── Passthrough facts: operational + rule adherence ───────────────────────────

def test_operational_and_adherence_passthrough():
    ops = OperationalStats(cycles_total=100, cycles_unattended=100, uptime_pct=0.99,
                           n_recoveries=1)
    rules = RuleAdherence(violations=0, blocks_fired=3, kill_switch_activations=1,
                          max_open_exposure_pct=0.28)
    card = compute_scorecard([10_000, 10_100], [], [], 10_000,
                            operational=ops, rule_adherence=rules)
    assert card.operational["cycles_unattended"] == 100
    assert card.rule_adherence["clean"] is True
    assert card.rule_adherence["blocks_fired"] == 3


def test_rule_adherence_dirty_when_violation():
    rules = RuleAdherence(violations=1)
    assert rules.clean is False
    card = compute_scorecard([10_000, 10_100], [], [], 10_000, rule_adherence=rules)
    assert card.rule_adherence["clean"] is False


# ── Degenerate input ──────────────────────────────────────────────────────────

def test_short_curve_returns_zeroed_card_not_crash():
    card = compute_scorecard([10_000], [], [], 10_000)
    assert isinstance(card, Scorecard)
    assert card.objective == 0.0
    assert card.n_trades == 0


# ── Convex row shape ──────────────────────────────────────────────────────────

def test_convex_row_is_flat_and_serialisable():
    import json
    trades = [_trade(300), _trade(-100)]
    card = compute_scorecard([10_000, 10_300, 10_200], trades, [], 10_000)
    row = card.as_convex_row()
    # nested facts JSON-encoded, scalar lines flat
    assert isinstance(row["operational"], str)
    assert isinstance(row["rule_adherence"], str)
    assert isinstance(row["objective"], float)
    json.dumps(row)  # must be fully serialisable
    assert json.loads(row["rule_adherence"])["clean"] is True


# ── Sim == live (locked decision #2) ──────────────────────────────────────────

def test_same_inputs_score_identically():
    """The whole reason this lives in /core: identical shapes → identical score,
    whether they came from a sim BacktestResult or a live window's real fills."""
    eq = [10_000, 10_200, 9_900, 10_400]
    trades = [_trade(200), _trade(-100), _trade(300)]
    a = compute_scorecard(eq, trades, [], 10_000)
    b = compute_scorecard(list(eq), list(trades), [], 10_000)
    assert a.as_dict() == b.as_dict()
