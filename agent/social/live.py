"""
Live social ingest → Convex sentiment_state, for the KOL auto-trade path.

One pass: load the watchlist (Convex social_sources if present, else the JSON
file), fan out across adapters (existing ingest()), then write one sentiment_state
row per ELIGIBLE symbol so the loop's _inject_sentiment (S3) and _apply_kol_signal
overlay can read it. Eligible-only: an ineligible token can never reach execution,
so we don't even persist its reading into the trade path.

Failure-isolated (§9.3): never raises — social is advisory/off the hot path.
"""
from __future__ import annotations

from pathlib import Path

from agent.social.ingest import ingest, load_watchlist
from agent.social.schema import SentimentReading, SourceSpec
from risk.guardrails import TOKEN_ALLOWLIST

_DEFAULT_WATCHLIST = Path(__file__).resolve().parent / "watchlist.example.json"

_ELIGIBLE_SYMBOLS = [s.upper() for s in TOKEN_ALLOWLIST]


def _load_sources_from_bridge(bridge) -> tuple[list[str], list[SourceSpec]] | None:
    """Fetch watchlist from Convex social_sources. Returns None if unavailable or empty."""
    try:
        rows = bridge.get_social_sources()
    except Exception:  # noqa: BLE001
        return None
    if not rows:
        return None
    # Derive symbol list from enabled Twitter handles (best-effort mapping via handle name)
    # The actual symbol attribution happens inside ingest/score; we pass all eligible symbols.
    symbols = list(_ELIGIBLE_SYMBOLS)
    specs = [
        SourceSpec(
            platform=r["platform"],
            handle=r["handle"],
            weight=float(r.get("weight", 1.0)),
            enabled=bool(r.get("enabled", True)),
            label=r.get("label", r["handle"]),
        )
        for r in rows
    ]
    return symbols, specs


def run_live_ingest(
    bridge,
    *,
    watchlist_path: str | None = None,
    limit: int = 50,
) -> dict[str, SentimentReading]:
    """
    Ingest and write sentiment state for eligible symbols only.

    Source priority:
      1. Convex social_sources (user-curated via the cockpit UI)
      2. watchlist_path JSON override (if provided)
      3. watchlist.example.json fallback

    Args:
        bridge: ConvexBridge instance (read social_sources + write sentiment_state).
        watchlist_path: Optional path to watchlist JSON — skips Convex when set.
        limit: Max posts per source (passed to ingest()).

    Returns:
        Dictionary of {symbol: SentimentReading} for all ingested symbols.
        On error (ingest or write), returns {} (failure-isolated).
    """
    try:
        # Bridge-first unless an explicit path was given
        loaded = None
        if watchlist_path is None:
            loaded = _load_sources_from_bridge(bridge)

        if loaded is not None:
            symbols, specs = loaded
        else:
            path = Path(watchlist_path) if watchlist_path else _DEFAULT_WATCHLIST
            symbols, specs = load_watchlist(path)

        symbols = [s for s in symbols if s.upper() in TOKEN_ALLOWLIST]
        if not symbols:
            return {}
        result = ingest(symbols, specs, limit=limit)
    except Exception:  # noqa: BLE001 — ingest must never crash the caller
        return {}

    for sym, reading in result.readings.items():
        if sym.upper() not in TOKEN_ALLOWLIST:
            continue
        try:
            bridge.set_sentiment_state(reading)
        except Exception:  # noqa: BLE001 — a bad write must not sink the pass
            pass
    return result.readings
