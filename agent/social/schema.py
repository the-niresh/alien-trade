"""
Social-layer contracts. Defined first (contracts-first, AGENT_TEAM_PLAN §9.2) so
every adapter, the normaliser, the scorer, and the Convex sink agree on shape.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

# Platforms v1 ships an adapter for. RSS + Farcaster need no credentials;
# Telegram + Twitter(X) are gated on credentials and switch on when configured.
PLATFORMS = ("rss", "farcaster", "telegram", "twitter")


@dataclass
class SourceSpec:
    """One entry in the user's watchlist: who to watch, on which platform."""
    platform: str                 # one of PLATFORMS
    handle: str                   # RSS feed URL | Farcaster/X username | Telegram channel
    weight: float = 1.0           # user trust weight (a trusted KOL counts more)
    enabled: bool = True
    label: str = ""               # display name for the UI

    def key(self) -> str:
        return f"{self.platform}:{self.handle.lower()}"


@dataclass
class SocialPost:
    """One normalised post from any platform."""
    id: str                       # stable dedupe key: "<platform>:<native_id>"
    platform: str
    author: str                   # handle/channel the post came from
    text: str
    ts_ms: int                    # post time (epoch ms); 0 if unknown
    url: str = ""
    author_display: str = ""
    lang: str = ""
    symbols: list[str] = field(default_factory=list)  # detected tickers, e.g. ["BNB"]
    weight: float = 1.0           # inherited from the SourceSpec that produced it
    raw: dict = field(default_factory=dict)


@dataclass
class SentimentReading:
    """
    The OFF-hot-path output: a bounded, timestamped sentiment feature per symbol.
    This is the seam into the deterministic core (signal S3) - exactly like the
    Option-B forecast bridge: an LLM/lexicon produces a number, the number (not
    prose) crosses into the decision, clamped and decayed. The core reads it
    point-in-time; it can only inform sizing within risk caps.
    """
    symbol: str
    score: float                  # in [-1, 1]: -1 max bearish, +1 max bullish
    confidence: float             # in [0, 1]: volume * directional agreement
    n_posts: int
    ts_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    top_post_ids: list[str] = field(default_factory=list)  # for citation in the channel

    def as_row(self) -> dict:
        """Shape written to the Convex `sentiment_state` table."""
        return {
            "symbol": self.symbol,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "n_posts": self.n_posts,
            "ts_ms": self.ts_ms,
            "top_post_ids": self.top_post_ids,
        }
