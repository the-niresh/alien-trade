"""
Social / Sentiment signal.
Rate-of-change of CMC social attention score, not the absolute level.
Spike in social volume + improving sentiment precedes retail flow.
Euphoric extreme (very high score, still rising fast) = blow-off → fade.
Output: float in [-1, +1].
Returns 0.0 when CMC social data is absent (all zeros).
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar


def sentiment_signal(history: list[Bar], period: int = 7) -> float:
    """
    Social attention momentum score in [-1, 1].
    Positive when attention is accelerating constructively.
    Negative on euphoric blow-off tops or sharply declining attention.
    Returns 0.0 when social_score is all zeros (social data not yet available).
    """
    if len(history) < period + 1:
        return 0.0

    scores = [b.social_score for b in history[-(period + 1):]]
    if all(s == 0.0 for s in scores):
        return 0.0   # graceful degradation

    baseline = scores[0]
    if baseline <= 0:
        return 0.0

    current = scores[-1]
    roc = (current - baseline) / baseline

    # Euphoria detection: score is very high AND rising sharply → fade signal
    window_scores = [b.social_score for b in history[-max(period * 3, 21):]]
    if len(window_scores) >= 5:
        p90 = float(np.percentile(window_scores, 90))
        if current > p90 and roc > 0.4:
            return -0.6   # blow-off top - contrarian

    # Normal: accelerating attention = bullish; collapsing attention = bearish
    # 50% increase over period → full bullish signal
    return float(np.clip(roc * 2.0, -1.0, 1.0))


# ── Fear & Greed Index (free historical S3 - contrarian level) ────────────────

_FG_NEUTRAL = 50.0   # F&G midpoint
_FG_SPAN = 40.0      # value 10 -> +1.0 (buy fear), value 90 -> -1.0 (fade greed)
_FG_DEADZONE = 10.0  # |value - 50| <= 10 -> no edge (sentiment is unremarkable)


def fear_greed_signal(history: list[Bar], smooth: int = 3) -> float:
    """Contrarian market-sentiment signal from the Fear & Greed Index in [-1, 1].

    social_score here carries the raw F&G value in [0, 100] (see
    data/sentiment_history.py). Classic contrarian edge: extreme fear precedes
    bounces (bullish), extreme greed precedes pullbacks (bearish). A deadzone
    around neutral keeps the signal quiet when sentiment is unremarkable, so it
    only speaks at the extremes where the index actually carries information.

    Returns 0.0 when F&G data is absent (all zeros) - graceful degradation,
    identical to sentiment_signal so sim/live parity holds with no feed.
    """
    if not history:
        return 0.0
    scores = [b.social_score for b in history[-max(smooth, 1):]]
    if all(s == 0.0 for s in scores):
        return 0.0

    nonzero = [s for s in scores if s > 0.0]
    if not nonzero:
        return 0.0
    current = float(np.mean(nonzero))  # short average smooths the daily step

    deviation = current - _FG_NEUTRAL
    if abs(deviation) <= _FG_DEADZONE:
        return 0.0
    # Contrarian: positive deviation (greed) -> negative signal, and vice versa.
    return float(np.clip(-deviation / _FG_SPAN, -1.0, 1.0))
