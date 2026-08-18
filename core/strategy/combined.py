"""
Combined strategy: momentum + derivatives (+ optional sentiment/flow) with regime
gating and rebalance band.

Decision flow per bar:
  1. detect_regime(history)                    → regime gate multiplier
  2. compute momentum, derivatives, sentiment, flow scores  → each in [-1, 1]
  3. weighted sum + gate                        → target in [-1, 1] * gate
  4. compare target to current position         → enter / exit / hold

Rebalance band prevents constant churning on noise (saves gas + slippage).
Spot-long-only. Perp shorts were dropped deliberately: every position is a
`twak swap` on PancakeSwap, so the agent can never take on funding-rate or
liquidation risk it has no model for.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from backtest.engine import Bar, Order, StrategyFn
from backtest.regime import Regime, detect_regime
from signals.momentum import momentum_signal, ema_value
from signals.derivatives import derivatives_signal
from signals.sentiment import fear_greed_signal
from signals.onchain import flow_signal


# ── Regime gates ──────────────────────────────────────────────────────────────

REGIME_GATES: dict[Regime, float] = {
    Regime.TREND:    1.0,   # full conviction
    Regime.CHOP:     0.5,   # half size - chop kills momentum strategies
    Regime.HIGH_VOL: 0.3,   # size down hard - vol-target principle
    Regime.CRASH:    0.0,   # sit out - no entry, force exit if in
}


# ── Strategy parameters ───────────────────────────────────────────────────────

@dataclass
class StrategyParams:
    # Momentum signal (EMA cross + ROC)
    ema_fast: int = 8
    ema_slow: int = 21
    roc_period: int = 10
    # Signal weights (each ≥ 0; sum should be ≤ 1)
    w_momentum:    float = 0.65
    w_derivatives: float = 0.35
    w_sentiment:   float = 0.0   # enabled when social data improves OOS Sortino
    w_flow:        float = 0.0   # enabled when on-chain flow data improves OOS Sortino
    # Entry / exit thresholds (applied to gated composite score)
    entry_threshold: float = 0.30
    exit_threshold:  float = -0.10
    # Long-term trend filter (cash-default gate): only hold long while price is
    # above this EMA of close. On 1h bars, 100 ≈ ~4 days. NOT swept by the
    # optimizer - a single principled knob keeps overfit risk low (locked #7).
    trend_filter_period: int = 100
    # Entry quality: require the trend EMA itself to be RISING over this lookback
    # before opening a new long (cuts failed breakouts above a flat/rolling EMA).
    # Asymmetric - the exit only needs price back below the EMA, so we don't churn
    # on a momentarily flat slope. 12 bars ≈ half a day on 1h. Not optimizer-swept.
    trend_slope_lookback: int = 12
    # Rebalance band: skip trade if |target - current| < band (cuts churn)
    rebalance_band: float = 0.15
    # Per-strategy CHOP gate override. Default None = use REGIME_GATES[CHOP]=0.5.
    # Contrarian sets this to 0.8 because it is DESIGNED for sideways/choppy markets
    # and the generic 0.5 gate directly fights its edge.
    chop_gate: float | None = None
    # When True, skip the rising-EMA trend filter on entry. Contrarian buys fear in
    # flat/down markets - requiring a rising EMA would block every entry it is meant
    # to make.  Momentum/balanced leave this False (trend filter protects their edge).
    bypass_trend_filter: bool = False
    # Position sizing
    position_size_usd: float = 1_000.0
    # Traded symbol - must be in risk.guardrails.TOKEN_ALLOWLIST (the tested set).
    # BNB/BTC/BTCB are never traded; ETH is the liquid default.
    symbol: str = "ETH"


# ── Strategy factory ──────────────────────────────────────────────────────────

def make_strategy(params: StrategyParams) -> StrategyFn:
    """
    Returns a stateful StrategyFn closure for use with run_backtest / run_walk_forward.
    Each call to make_strategy() produces an independent instance with fresh state.
    """
    in_position: list[bool] = [False]   # mutable cell - survives bar-by-bar calls

    def strategy(history: list[Bar]) -> Optional[Order]:
        # Need enough history for the slow EMA, the long trend filter, and the EMA
        # slope lookback used by the rising-trend entry filter.
        warmup = max(params.ema_slow + 5,
                     params.trend_filter_period + params.trend_slope_lookback + 1)
        if len(history) < warmup:
            return None

        bar = history[-1]

        # ── Regime gate ───────────────────────────────────────────────────────
        regime = detect_regime(history)
        gate = REGIME_GATES.get(regime, 1.0)
        if regime == Regime.CHOP and params.chop_gate is not None:
            gate = params.chop_gate

        # ── Trend-filter regime gate (cash is the default) ────────────────────
        # Only hold long while price is above the long EMA. Below it, capital sits
        # in USDT - which contributes zero drawdown. This is the core of the
        # drawdown-first redesign: a long-only book that refuses to fight a
        # downtrend, rather than buying every dip and getting chopped.
        ema_long = ema_value(history, params.trend_filter_period)
        ema_prev = ema_value(history[:-params.trend_slope_lookback],
                             params.trend_filter_period)
        above_trend  = (ema_long == ema_long) and bar.close > ema_long       # NaN-safe
        trend_rising = (ema_prev == ema_prev) and ema_long > ema_prev        # NaN-safe

        # Asymmetric gate: ENTER only when price is above a RISING trend line
        # (kills failed breakouts above a flat/rolling EMA); HOLD as long as price
        # stays above the EMA (lenient exit → no churn on a momentarily flat slope).
        can_enter = above_trend and trend_rising
        can_hold  = above_trend

        # Force exit to cash when price breaks the trend or on a crash.
        if in_position[0] and (not can_hold or regime == Regime.CRASH):
            in_position[0] = False
            return Order(
                side="sell",
                size_usd=params.position_size_usd,
                symbol=params.symbol,
                timestamp=bar.timestamp,
            )

        # No new longs unless price is above a confirmed *rising* trend (cash-default).
        # Contrarian bypasses this: it buys fear in flat/down markets where the trend
        # filter would block every entry it is designed to make.
        if not can_enter and not params.bypass_trend_filter:
            return None

        # ── Signal scores ─────────────────────────────────────────────────────
        mom  = momentum_signal(history, params.ema_fast, params.ema_slow, params.roc_period)
        deriv = derivatives_signal(history)
        sent = fear_greed_signal(history) if params.w_sentiment > 0.0 else 0.0
        flow = flow_signal(history)      if params.w_flow > 0.0 else 0.0

        raw = (params.w_momentum    * mom
               + params.w_derivatives * deriv
               + params.w_sentiment   * sent
               + params.w_flow        * flow)
        target = float(np.clip(raw, -1.0, 1.0)) * gate

        # ── Rebalance band ────────────────────────────────────────────────────
        current = 1.0 if in_position[0] else 0.0
        if abs(target - current) < params.rebalance_band:
            return None   # within band - don't trade

        # ── Entry / exit ──────────────────────────────────────────────────────
        if not in_position[0] and target > params.entry_threshold:
            in_position[0] = True
            return Order(
                side="buy",
                size_usd=params.position_size_usd,
                symbol=params.symbol,
                timestamp=bar.timestamp,
            )
        if in_position[0] and target < params.exit_threshold:
            in_position[0] = False
            return Order(
                side="sell",
                size_usd=params.position_size_usd,
                symbol=params.symbol,
                timestamp=bar.timestamp,
            )
        return None

    return strategy


# ── Signal attribution helper ─────────────────────────────────────────────────

def score_breakdown(history: list[Bar], params: StrategyParams) -> dict:
    """Return per-signal scores + composite for a given history slice."""
    regime = detect_regime(history)
    gate = REGIME_GATES.get(regime, 1.0)
    if regime == Regime.CHOP and params.chop_gate is not None:
        gate = params.chop_gate
    mom   = momentum_signal(history, params.ema_fast, params.ema_slow, params.roc_period)
    deriv = derivatives_signal(history)
    sent  = fear_greed_signal(history) if params.w_sentiment > 0.0 else 0.0
    onchain = flow_signal(history)     if params.w_flow > 0.0 else 0.0
    raw = (params.w_momentum    * mom
           + params.w_derivatives * deriv
           + params.w_sentiment   * sent
           + params.w_flow        * onchain)
    return {
        "regime":      regime.value,
        "gate":        gate,
        "momentum":    round(mom,     4),
        "derivatives": round(deriv,   4),
        "sentiment":   round(sent,    4),
        "flow":        round(onchain, 4),
        "raw":         round(raw,     4),
        "target":      round(float(np.clip(raw, -1.0, 1.0)) * gate, 4),
    }
