"""
Cross-sectional rotation backtester (long-only, one asset at a time).

Where per-asset trend-following on a hostile universe only reaches ~flat, relative
strength is the real long-only edge: hold whichever eligible asset is *strongest*
right now, and sit in USDT (zero drawdown) when none qualify.

Reuses the single-asset engine's Bar / cost model / fill accounting (`_apply_fill`)
and the same scorecard, so a rotation result is directly comparable to the per-symbol
runs in retune.py. Same anti-overfit discipline: principled fixed knobs, no sweep.

Eligibility per asset is the v2 cash-default gate (price above a *rising* EMA100 +
positive momentum); the score used for ranking is the momentum composite. A switch
band stops the book thrashing between near-tied leaders.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from backtest.engine import Bar, Order, Fill, BacktestResult, _apply_fill, _compute_metrics
from backtest.costs import BSCCostModel
from signals.momentum import momentum_signal, ema_value


@dataclass
class RotationParams:
    # Momentum scoring (same as the single-asset strategy)
    ema_fast: int = 8
    ema_slow: int = 21
    roc_period: int = 10
    # Cash-default trend filter + rising-trend entry (mirrors strategy/combined.py)
    trend_filter_period: int = 100
    trend_slope_lookback: int = 12
    entry_threshold: float = 0.30
    # Only switch leaders when the challenger beats the incumbent's score by this
    # margin — kills churn between near-tied assets.
    switch_margin: float = 0.10
    # Rebalance cadence: only *enter from cash* or *switch leaders* every N bars
    # (24 ≈ daily on 1h). Exit-to-cash on loss of eligibility is allowed every bar
    # (risk control is responsive; rotation is slow). This is the anti-churn knob.
    rebalance_every: int = 24
    # Fraction of available cash deployed into the chosen asset (buffer for costs).
    deploy_fraction: float = 0.95
    # Don't open a position with less than this much cash (avoids fixed-gas drag
    # dominating a shrunk account).
    min_trade_usd: float = 100.0


def _eval_symbol(history: list[Bar], p: RotationParams) -> tuple[bool, float]:
    """(eligible, score) for one asset at the current bar. Eligible = price above a
    rising EMA(trend_filter_period) AND momentum over entry_threshold. Score = momentum."""
    if len(history) < p.trend_filter_period + p.trend_slope_lookback + 1:
        return False, 0.0
    bar = history[-1]
    ema_long = ema_value(history, p.trend_filter_period)
    ema_prev = ema_value(history[: -p.trend_slope_lookback], p.trend_filter_period)
    above  = (ema_long == ema_long) and bar.close > ema_long          # NaN-safe
    rising = (ema_prev == ema_prev) and ema_long > ema_prev           # NaN-safe
    mom = momentum_signal(history, p.ema_fast, p.ema_slow, p.roc_period)
    return (above and rising and mom > p.entry_threshold), mom


def run_rotation_backtest(
    bars_by_symbol: dict[str, list[Bar]],
    params: RotationParams = RotationParams(),
    cost_model=None,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    """Event-driven rotation over a common timestamp grid. Holds at most one asset.
    Point-in-time: each symbol's signal sees only its bars up to the current step."""
    cost_model = cost_model or BSCCostModel()
    symbols = list(bars_by_symbol)

    # Align on the intersection of timestamps so every symbol is comparable per step.
    idx = {s: {b.timestamp: b for b in bars_by_symbol[s]} for s in symbols}
    common = sorted(set.intersection(*[set(m) for m in idx.values()])) if symbols else []
    aligned = {s: [idx[s][t] for t in common] for s in symbols}

    result = BacktestResult()
    cash = initial_capital
    held: Optional[str] = None
    position_units = 0.0
    entry_fill: Optional[Fill] = None
    total_volume = 0.0
    warmup = params.trend_filter_period + params.trend_slope_lookback + 1

    def _fill(side: str, size_usd: float, sym: str, bar: Bar, ts: int):
        nonlocal cash, position_units, entry_fill, total_volume
        if size_usd <= 0:
            return
        order = Order(side=side, size_usd=size_usd, symbol=sym, timestamp=ts)
        fee, gas, slip = cost_model(order, bar)
        slip_pct = slip / size_usd if size_usd > 0 else 0.0
        fill_price = bar.close * (1 + slip_pct if side == "buy" else 1 - slip_pct)
        cash, position_units, entry_fill = _apply_fill(
            order, fill_price, bar, cash, position_units, entry_fill,
            cost_model, result, precomputed=(fee, gas, slip),
        )
        total_volume += size_usd

    for i, ts in enumerate(common):
        if i < warmup:
            result.equity_curve.append(cash)
            continue

        # Rank eligible assets by momentum score (relative strength).
        scores = {}
        for s in symbols:
            elig, sc = _eval_symbol(aligned[s][: i + 1], params)
            if elig:
                scores[s] = sc
        best = max(scores, key=scores.get) if scores else None
        can_trade = (i % params.rebalance_every == 0)   # slow rotation cadence

        # Decide the target. Ride the winner: stay in the held asset as long as it
        # remains eligible, and only rotate when ITS OWN trend filter forces an exit
        # to cash. We never switch peer-to-peer on a momentum edge — that flip-flop
        # is what churned the book to death. Re-entry from cash is cadence-gated.
        if held is not None:
            target = held if scores.get(held) is not None else None  # exit only on trend break
        else:
            target = best if can_trade else None  # enter strongest from cash, on cadence

        # Execute: exit the old leader, enter the new one.
        if held is not None and held != target:
            bar_h = aligned[held][i]
            _fill("sell", position_units * bar_h.close, held, bar_h, ts)
            held = None
        if held is None and target is not None and cash >= params.min_trade_usd:
            bar_t = aligned[target][i]
            _fill("buy", cash * params.deploy_fraction, target, bar_t, ts)
            held = target

        held_close = aligned[held][i].close if held else 0.0
        result.equity_curve.append(cash + position_units * held_close)

    avg_equity = float(np.mean(result.equity_curve)) if result.equity_curve else initial_capital
    result.metrics = _compute_metrics(
        result.equity_curve, initial_capital, result.trades,
        total_volume, avg_equity, n_fills=len(result.fills),
    )
    return result
