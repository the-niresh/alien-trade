"""
Derivatives signal: funding rate (contrarian) + open interest (confirmatory).
Output: float in [-1, +1].
Returns 0.0 gracefully when derivatives data is absent (all zeros).

Edge: positioning data front-runs liquidations.  Most backtest-only teams miss this.
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar

# Funding rate thresholds (8-hour rates from CMC perp data)
_FUNDING_LONG_EXTREME  =  0.0005   # +0.05%/8h → very crowded longs → contrarian bearish
_FUNDING_SHORT_EXTREME = -0.0002   # -0.02%/8h → crowded shorts → contrarian bullish


# ── Public API ────────────────────────────────────────────────────────────────

def derivatives_signal(
    history: list[Bar],
    lookback: int = 7,
) -> float:
    """
    Combined derivatives score in [-1, 1].
    Component 1 (60%): funding rate — contrarian on extremes.
    Component 2 (40%): OI trend vs price trend — confirmatory / divergence flag.
    Returns 0.0 when funding_rate and open_interest are all zero (data not yet available).
    """
    if len(history) < lookback + 1:
        return 0.0

    window = history[-lookback:]
    funding_rates = [b.funding_rate for b in window]
    ois = [b.open_interest for b in window]

    # Graceful degradation: return neutral when CMC data is absent
    has_funding = any(f != 0.0 for f in funding_rates)
    has_oi = any(oi != 0.0 for oi in ois)
    if not has_funding and not has_oi:
        return 0.0

    fsig = _funding_signal(funding_rates) if has_funding else 0.0
    oisig = _oi_signal(window, ois) if has_oi else 0.0

    return float(np.clip(0.6 * fsig + 0.4 * oisig, -1.0, 1.0))


def funding_signal(history: list[Bar], lookback: int = 7) -> float:
    """Isolated funding-rate signal for attribution."""
    if len(history) < lookback + 1:
        return 0.0
    rates = [b.funding_rate for b in history[-lookback:]]
    return _funding_signal(rates) if any(r != 0.0 for r in rates) else 0.0


def oi_signal(history: list[Bar], lookback: int = 7) -> float:
    """Isolated OI-vs-price signal for attribution."""
    if len(history) < lookback + 1:
        return 0.0
    window = history[-lookback:]
    ois = [b.open_interest for b in window]
    return _oi_signal(window, ois) if any(oi != 0.0 for oi in ois) else 0.0


# ── Private helpers ───────────────────────────────────────────────────────────

def _funding_signal(rates: list[float]) -> float:
    """
    Contrarian: extreme positive funding → bearish; extreme negative → bullish.
    Linear interpolation between thresholds; clips at ±1.
    """
    avg = float(np.mean(rates))
    if avg >= _FUNDING_LONG_EXTREME:
        # Normalize: exactly at threshold = -1, double = still capped at -1
        return float(np.clip(-avg / _FUNDING_LONG_EXTREME, -1.0, 0.0))
    if avg <= _FUNDING_SHORT_EXTREME:
        return float(np.clip(-avg / abs(_FUNDING_SHORT_EXTREME), 0.0, 1.0))
    # Linear in the neutral zone
    return float(-avg / _FUNDING_LONG_EXTREME)


def _oi_signal(window: list[Bar], ois: list[float]) -> float:
    """
    OI vs price co-movement signal.
    Rising OI + rising price  → trend has conviction → follow direction of price.
    Rising OI + falling price → short-squeeze risk    → slight bullish bias.
    Falling OI               → trend may be exhausting → fade direction.
    """
    if ois[0] <= 0 or ois[-1] <= 0:
        return 0.0

    oi_change = (ois[-1] - ois[0]) / ois[0]
    price_start = window[0].close
    price_end = window[-1].close
    if price_start <= 0:
        return 0.0
    price_change = (price_end - price_start) / price_start

    # OI and price in same direction = conviction
    if np.sign(oi_change) == np.sign(price_change) and abs(oi_change) > 0.01:
        # Scale: 10% price move with OI confirmation = ±1
        return float(np.clip(price_change * 10.0, -1.0, 1.0))
    # OI rising vs flat/falling price = potential squeeze
    if oi_change > 0.05 and price_change < 0.01:
        return 0.3
    # OI falling = trend exhaustion; lean opposite
    if oi_change < -0.05:
        return float(np.clip(-price_change * 5.0, -0.5, 0.5))
    return 0.0
