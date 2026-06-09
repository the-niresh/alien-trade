"""
Combined strategy: S1 + S2 (+ optional S3/S4) with regime gating and rebalance band.

Decision flow per bar:
  1. detect_regime(history)              → regime gate multiplier
  2. compute S1, S2, (S3, S4) scores    → each in [-1, 1]
  3. weighted sum + gate                 → target in [-1, 1] * gate
  4. compare target to current position  → enter / exit / hold

Rebalance band prevents constant churning on noise (saves gas + slippage).
Spot-long-only: perp shorts were dropped from the scored path (only `twak swap`
transactions count toward competition PnL — see reference-hackathon-rules).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from backtest.engine import Bar, Order, StrategyFn
from backtest.regime import Regime, detect_regime
from signals.momentum import s1_momentum
from signals.derivatives import s2_derivatives
from signals.sentiment import s3_sentiment
from signals.onchain import s4_onchain


# ── Regime gates ──────────────────────────────────────────────────────────────

REGIME_GATES: dict[Regime, float] = {
    Regime.TREND:    1.0,   # full conviction
    Regime.CHOP:     0.5,   # half size — chop kills momentum strategies
    Regime.HIGH_VOL: 0.3,   # size down hard — vol-target principle
    Regime.CRASH:    0.0,   # sit out — no entry, force exit if in
}


# ── Strategy parameters ───────────────────────────────────────────────────────

@dataclass
class StrategyParams:
    # S1 — momentum / trend
    s1_fast: int = 8
    s1_slow: int = 21
    s1_roc: int = 10
    # Signal weights (each ≥ 0; sum should be ≤ 1)
    w_s1: float = 0.65
    w_s2: float = 0.35
    w_s3: float = 0.0    # enabled when CMC social data improves OOS Sortino
    w_s4: float = 0.0    # enabled when CMC flow data improves OOS Sortino
    # Entry / exit thresholds (applied to gated composite score)
    entry_threshold: float = 0.30
    exit_threshold: float = -0.10
    # Rebalance band: skip trade if |target - current| < band (cuts churn)
    rebalance_band: float = 0.15
    # Position sizing
    position_size_usd: float = 1_000.0
    # Traded symbol — must be a competition-eligible BEP-20 (see docs/GOAL.md /
    # reference). BNB/BTC/BTCB are NOT eligible; ETH is the liquid default.
    symbol: str = "ETH"


# ── Strategy factory ──────────────────────────────────────────────────────────

def make_strategy(params: StrategyParams) -> StrategyFn:
    """
    Returns a stateful StrategyFn closure for use with run_backtest / run_walk_forward.
    Each call to make_strategy() produces an independent instance with fresh state.
    """
    in_position: list[bool] = [False]   # mutable cell — survives bar-by-bar calls

    def strategy(history: list[Bar]) -> Optional[Order]:
        if len(history) < params.s1_slow + 5:
            return None

        bar = history[-1]

        # ── Regime gate ───────────────────────────────────────────────────────
        regime = detect_regime(history)
        gate = REGIME_GATES.get(regime, 1.0)

        # Force exit on crash regardless of signal
        if regime == Regime.CRASH and in_position[0]:
            in_position[0] = False
            return Order(
                side="sell",
                size_usd=params.position_size_usd,
                symbol=params.symbol,
                timestamp=bar.timestamp,
            )

        # ── Signal scores ─────────────────────────────────────────────────────
        s1 = s1_momentum(history, params.s1_fast, params.s1_slow, params.s1_roc)
        s2 = s2_derivatives(history)
        s3 = s3_sentiment(history) if params.w_s3 > 0.0 else 0.0
        s4 = s4_onchain(history) if params.w_s4 > 0.0 else 0.0

        raw = (params.w_s1 * s1
               + params.w_s2 * s2
               + params.w_s3 * s3
               + params.w_s4 * s4)
        target = float(np.clip(raw, -1.0, 1.0)) * gate

        # ── Rebalance band ────────────────────────────────────────────────────
        current = 1.0 if in_position[0] else 0.0
        if abs(target - current) < params.rebalance_band:
            return None   # within band — don't trade

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
    s1 = s1_momentum(history, params.s1_fast, params.s1_slow, params.s1_roc)
    s2 = s2_derivatives(history)
    s3 = s3_sentiment(history) if params.w_s3 > 0.0 else 0.0
    s4 = s4_onchain(history)   if params.w_s4 > 0.0 else 0.0
    raw = params.w_s1 * s1 + params.w_s2 * s2 + params.w_s3 * s3 + params.w_s4 * s4
    return {
        "regime": regime.value,
        "gate": gate,
        "s1": round(s1, 4),
        "s2": round(s2, 4),
        "s3": round(s3, 4),
        "s4": round(s4, 4),
        "raw": round(raw, 4),
        "target": round(float(np.clip(raw, -1.0, 1.0)) * gate, 4),
    }
