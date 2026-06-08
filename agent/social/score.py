"""
Deterministic sentiment scoring — the OFF-hot-path reducer.

Posts -> a bounded `SentimentReading` per symbol. Deterministic by design: a
lexicon mapping, weighted by source trust and recency decay. No LLM, no network,
fully reproducible (so it can later feed signal S3 with sim/live parity). An LLM
enrichment pass can refine this asynchronously, but the NUMBER that crosses into
the decision is always this deterministic one.

The reading can only INFORM sizing inside risk caps (shrink-or-confirm), never
enlarge it — same discipline as the Option-B forecast bridge.
"""
from __future__ import annotations

import math

from agent.social.schema import SentimentReading, SocialPost

_BULLISH = {
    "bull", "bullish", "long", "buy", "buying", "breakout", "moon", "pump",
    "accumulate", "accumulating", "rally", "surge", "support", "rip", "send",
    "up", "uptrend", "green", "ath", "strong", "strength", "bounce", "rebound",
}
_BEARISH = {
    "bear", "bearish", "short", "sell", "selling", "dump", "crash", "rug",
    "breakdown", "weak", "weakness", "down", "downtrend", "red", "capitulation",
    "rejection", "resistance", "fakeout", "exit", "liquidated", "rekt", "fade",
}

_WORD = __import__("re").compile(r"[a-zA-Z]+")
_HALF_LIFE_H_DEFAULT = 12.0
_VOLUME_FULL = 5  # n posts at/above which volume confidence saturates


def post_polarity(text: str) -> float:
    """Lexicon polarity of one post in [-1, 1]; 0 if no signal words."""
    words = [w.lower() for w in _WORD.findall(text)]
    b = sum(1 for w in words if w in _BULLISH)
    s = sum(1 for w in words if w in _BEARISH)
    if b == 0 and s == 0:
        return 0.0
    return (b - s) / (b + s)


def _recency_weight(age_ms: int, half_life_h: float) -> float:
    if age_ms <= 0:
        return 1.0
    age_h = age_ms / 3_600_000.0
    return 0.5 ** (age_h / max(half_life_h, 0.1))


def score_symbol(
    posts: list[SocialPost],
    symbol: str,
    *,
    now_ms: int,
    half_life_h: float = _HALF_LIFE_H_DEFAULT,
) -> SentimentReading:
    """Aggregate posts mentioning `symbol` into one bounded reading."""
    relevant = [p for p in posts if symbol.upper() in (p.symbols or [])]
    if not relevant:
        return SentimentReading(symbol=symbol, score=0.0, confidence=0.0, n_posts=0, ts_ms=now_ms)

    num = den = 0.0
    abs_den = 0.0
    contributing: list[tuple[float, str]] = []  # (abs effective weight, id)
    for p in relevant:
        pol = post_polarity(p.text)
        w = max(p.weight, 0.0) * _recency_weight(now_ms - p.ts_ms if p.ts_ms else 0, half_life_h)
        num += w * pol
        den += w
        abs_den += w * abs(pol)
        contributing.append((w * abs(pol), p.id))

    score = (num / den) if den else 0.0
    score = max(-1.0, min(1.0, score))

    # Confidence = volume saturation * directional agreement.
    volume = 1.0 - math.exp(-len(relevant) / _VOLUME_FULL)
    agreement = (abs(num) / abs_den) if abs_den else 0.0   # 1.0 = posts all agree in direction
    confidence = max(0.0, min(1.0, volume * agreement))

    contributing.sort(reverse=True)
    top_ids = [pid for _, pid in contributing[:3]]
    return SentimentReading(
        symbol=symbol, score=score, confidence=confidence,
        n_posts=len(relevant), ts_ms=now_ms, top_post_ids=top_ids,
    )


def score_all(
    posts: list[SocialPost],
    symbols: list[str],
    *,
    now_ms: int,
    half_life_h: float = _HALF_LIFE_H_DEFAULT,
) -> dict[str, SentimentReading]:
    return {s: score_symbol(posts, s, now_ms=now_ms, half_life_h=half_life_h) for s in symbols}
