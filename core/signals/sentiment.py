"""
S3 — Social / Sentiment signal.
Rate-of-change of CMC social attention score, not the absolute level.
Spike in social volume + improving sentiment precedes retail flow.
Euphoric extreme (very high score, still rising fast) = blow-off → fade.
Output: float in [-1, +1].
Returns 0.0 when CMC social data is absent (all zeros).
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar


def s3_sentiment(history: list[Bar], period: int = 7) -> float:
    """
    Social attention momentum score in [-1, 1].
    Positive when attention is accelerating constructively.
    Negative on euphoric blow-off tops or sharply declining attention.
    Returns 0.0 when social_score is all zeros (CMC not yet wired).
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
            return -0.6   # blow-off top — contrarian

    # Normal: accelerating attention = bullish; collapsing attention = bearish
    # 50% increase over period → full bullish signal
    return float(np.clip(roc * 2.0, -1.0, 1.0))
