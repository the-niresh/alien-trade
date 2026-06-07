"""
S4 — On-chain flow signal.
Net outflow from exchanges (accumulation) = bullish precursor.
Net inflow (distribution / sell pressure) = bearish.
Score is the z-score of current net_flow vs recent history, sign-flipped
so negative flow (outflow) → positive signal.
Output: float in [-1, +1].
Returns 0.0 when CMC on-chain data is absent (all zeros).
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar


def s4_onchain(history: list[Bar], lookback: int = 14) -> float:
    """
    On-chain net flow z-score signal in [-1, 1].
    Positive = net outflow (accumulation = smart money buying off exchange).
    Negative = net inflow (distribution = selling pressure building).
    Returns 0.0 when net_flow is all zeros (CMC not yet wired).
    """
    if len(history) < lookback + 1:
        return 0.0

    flows = [b.net_flow for b in history[-lookback:]]
    if all(f == 0.0 for f in flows):
        return 0.0   # graceful degradation

    arr = np.array(flows, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std())

    if std < 1e-8:
        return 0.0   # no variation in flow — uninformative

    # z-score: how unusual is today's flow relative to recent history?
    z = (arr[-1] - mean) / std

    # Sign flip: outflow (negative net_flow) = bullish
    # ±2σ = full signal; beyond that clips to ±1
    return float(np.clip(-z / 2.0, -1.0, 1.0))
