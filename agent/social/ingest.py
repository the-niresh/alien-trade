"""
Ingest orchestrator + CLI - the "agent watches your list for you" loop.

  load watchlist -> fan out across platform adapters -> normalise -> score
  -> emit summary (and, when wired, write Convex social_posts + sentiment_state).

Failure-isolated (§9.3): a platform that's unavailable or errors is skipped with
a note; the run always completes on whatever sources did work.

Run:
  core/.venv/Scripts/python.exe -m agent.social.ingest --once
  core/.venv/Scripts/python.exe -m agent.social.ingest --once --json
  core/.venv/Scripts/python.exe -m agent.social.ingest --once --watchlist path/to.json
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from agent.social.normalize import normalize
from agent.social.schema import SentimentReading, SocialPost, SourceSpec
from agent.social.score import score_all
from agent.social.sources import NotConfigured, available_platforms, get_source

_DEFAULT_WATCHLIST = Path(__file__).resolve().parent / "watchlist.example.json"


@dataclass
class IngestResult:
    posts: list[SocialPost]
    readings: dict[str, SentimentReading]
    skipped: dict[str, str] = field(default_factory=dict)   # platform -> reason
    counts: dict[str, int] = field(default_factory=dict)    # platform -> n posts


def load_watchlist(path: Path) -> tuple[list[str], list[SourceSpec]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    symbols = [s.upper() for s in data.get("symbols", [])]
    specs = [
        SourceSpec(
            platform=s["platform"], handle=s["handle"],
            weight=float(s.get("weight", 1.0)), enabled=bool(s.get("enabled", True)),
            label=s.get("label", ""),
        )
        for s in data.get("sources", [])
    ]
    return symbols, specs


def ingest(symbols: list[str], specs: list[SourceSpec], *, since_ms: int = 0, limit: int = 50) -> IngestResult:
    by_platform: dict[str, list[SourceSpec]] = {}
    for spec in specs:
        if spec.enabled:
            by_platform.setdefault(spec.platform, []).append(spec)

    raw: list[SocialPost] = []
    skipped: dict[str, str] = {}
    counts: dict[str, int] = {}
    for platform, plat_specs in by_platform.items():
        try:
            source = get_source(platform)
        except KeyError:
            skipped[platform] = "no adapter registered"
            continue
        if not source.available():
            skipped[platform] = "not configured (deps/credentials missing)"
            continue
        try:
            got = source.fetch(plat_specs, since_ms=since_ms, limit=limit)
            raw.extend(got)
            counts[platform] = len(got)
        except NotConfigured as exc:
            skipped[platform] = str(exc)
        except Exception as exc:  # never fatal - one source can't sink the run
            skipped[platform] = f"error: {exc}"

    now_ms = int(time.time() * 1000)
    posts = normalize(raw, universe=symbols, since_ms=since_ms)
    readings = score_all(posts, symbols, now_ms=now_ms)
    return IngestResult(posts=posts, readings=readings, skipped=skipped, counts=counts)


def _print_summary(res: IngestResult) -> None:
    print(f"[social] ingested {len(res.posts)} posts across {len(res.counts)} live source(s)")
    for platform, n in sorted(res.counts.items()):
        print(f"  - {platform:10s} {n} posts")
    for platform, reason in sorted(res.skipped.items()):
        print(f"  - {platform:10s} SKIPPED: {reason}")
    print("[social] sentiment readings (deterministic, off hot path):")
    for sym, r in sorted(res.readings.items()):
        bar = "bullish" if r.score > 0.05 else "bearish" if r.score < -0.05 else "neutral"
        print(f"  {sym:6s} score={r.score:+.3f} conf={r.confidence:.2f} "
              f"n={r.n_posts:3d} -> {bar}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Social ingest (RSS/Farcaster/Telegram/X)")
    ap.add_argument("--once", action="store_true", help="run a single ingest pass")
    ap.add_argument("--watchlist", default=str(_DEFAULT_WATCHLIST))
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    symbols, specs = load_watchlist(Path(args.watchlist))
    if not args.json:
        print(f"[social] watchlist: {len(specs)} sources, symbols={symbols}")
        print(f"[social] adapters available: {available_platforms()}")
    res = ingest(symbols, specs, limit=args.limit)

    if args.json:
        print(json.dumps({
            "readings": {s: r.as_row() for s, r in res.readings.items()},
            "counts": res.counts,
            "skipped": res.skipped,
            "posts": [{"id": p.id, "platform": p.platform, "author": p.author,
                       "ts_ms": p.ts_ms, "symbols": p.symbols, "text": p.text[:200]}
                      for p in res.posts[:50]],
        }, indent=2))
    else:
        _print_summary(res)


if __name__ == "__main__":
    main()
