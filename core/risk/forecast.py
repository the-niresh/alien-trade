"""
Option-B forecast bridge - the math side (STEP 8.4).

The only influence the Researcher's forecast may have on a trade is a confidence
float in [0, 1] that SHRINKS size (multiplier ≤ 1.0 - the one-way valve). The
clamp + time-decay math lives here so sim and live apply the exact same arithmetic.

Invariants tested in test_forecast_bridge.py:
  1. Multiplier is always ≤ 1.0 - can never enlarge a position.
  2. Stale (age ≥ ttl_ms) forecast decays to NEUTRAL (1.0) - can't silently throttle.
  3. FLOOR prevents the multiplier from dropping below FORECAST_FLOOR.
"""
from __future__ import annotations

FORECAST_FLOOR: float = 0.5    # minimum multiplier; shrink at most 50%
NEUTRAL: float = 1.0           # "no opinion" - result when there is no forecast


def decay_confidence(confidence: float, age_ms: int, ttl_ms: int) -> float:
    """Linear decay from `confidence` toward NEUTRAL as the forecast ages.
    At age >= ttl_ms the result is exactly NEUTRAL - a stale forecast is
    equivalent to no forecast. age_ms=0 returns confidence unchanged."""
    if ttl_ms <= 0 or age_ms <= 0:
        return float(confidence)
    if age_ms >= ttl_ms:
        return NEUTRAL
    t = age_ms / ttl_ms      # 0.0 → 1.0
    return float(confidence) + (NEUTRAL - float(confidence)) * t


def apply_forecast_multiplier(size_usd: float, confidence: float) -> float:
    """Shrink-only: multiply size by the clamped confidence.
    Clamps to [FORECAST_FLOOR, NEUTRAL] so multiplier ∈ [0.5, 1.0].
    Never returns a value > size_usd."""
    mult = max(FORECAST_FLOOR, min(NEUTRAL, float(confidence)))
    return size_usd * mult


def brier_score(buckets: list[tuple[float, float]]) -> float:
    """Calibration quality for the forecast confidence.

    Given a list of (confidence, realized_win_rate) bucket pairs, returns the
    mean squared error between predicted confidence and observed win rate.
    Lower is better; 0.0 is perfect calibration; 0.25 is the uninformed baseline
    (constant 0.5 prediction on a balanced outcome).

    Dreamer logs this nightly after collecting enough fills per bucket.
    """
    if not buckets:
        return 0.25  # uninformed baseline - no data yet
    return sum((conf - wr) ** 2 for conf, wr in buckets) / len(buckets)


def confidence_from_regime(regime: str) -> float:
    """Deterministic confidence from regime for a long-only spot strategy.
    Downtrends and high-vol shrink size; uptrends leave it at neutral."""
    return {
        "trend_up":   1.00,   # no shrink
        "trend_down": 0.55,   # long-only in a downtrend is high-risk
        "chop":       0.75,   # uncertain; moderate shrink
        "high_vol":   0.65,   # elevated vol; defensive shrink
    }.get(regime, 0.85)       # unknown regime → cautious but not extreme
