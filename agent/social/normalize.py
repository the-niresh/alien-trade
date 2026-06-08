"""
Normalise a raw post stream: dedupe, drop empties, time-filter, sort newest-first,
and tag detected symbols. Pure functions — unit-testable, no network.
"""
from __future__ import annotations

import re

from agent.social.schema import SocialPost

# $TICKER cashtags, and bare uppercase tickers when they match the universe.
_CASHTAG = re.compile(r"\$([A-Za-z]{2,6})\b")


def detect_symbols(text: str, universe: list[str]) -> list[str]:
    """Return universe symbols mentioned in `text` (cashtag or whole-word)."""
    found: set[str] = set()
    upper = {s.upper() for s in universe}
    for m in _CASHTAG.finditer(text):
        sym = m.group(1).upper()
        if sym in upper:
            found.add(sym)
    for sym in upper:
        if re.search(rf"\b{re.escape(sym)}\b", text, flags=re.IGNORECASE):
            found.add(sym)
    return sorted(found)


def normalize(
    posts: list[SocialPost],
    *,
    universe: list[str] | None = None,
    since_ms: int = 0,
    drop_empty: bool = True,
) -> list[SocialPost]:
    universe = universe or []
    seen: set[str] = set()
    out: list[SocialPost] = []
    for p in posts:
        if not p.id or p.id in seen:
            continue
        if drop_empty and not p.text.strip():
            continue
        if since_ms and p.ts_ms and p.ts_ms < since_ms:
            continue
        seen.add(p.id)
        if universe:
            p.symbols = detect_symbols(p.text, universe)
        out.append(p)
    out.sort(key=lambda p: p.ts_ms, reverse=True)
    return out
