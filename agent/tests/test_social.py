"""
Offline tests for the social ingestion layer: parse -> normalize -> score, plus
adapter registry + credential-gating. No network (pure functions + gated stubs).
"""
from __future__ import annotations

import time

from agent.social.ingest import ingest
from agent.social.normalize import detect_symbols, normalize
from agent.social.schema import SocialPost, SourceSpec
from agent.social.score import post_polarity, score_symbol
from agent.social.sources import available_platforms, get_source, registered_platforms
from agent.social.sources.rss import parse_feed

_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>BNB breakout</title><description>BNB looks bullish, strong breakout, moon</description>
    <link>https://x/1</link><guid>g1</guid><pubDate>Wed, 10 Jun 2026 12:00:00 +0000</pubDate></item>
  <item><title>ETH weakness</title><description>ETH dump, bearish breakdown, weak</description>
    <link>https://x/2</link><guid>g2</guid><pubDate>Wed, 10 Jun 2026 13:00:00 +0000</pubDate></item>
</channel></rss>"""

_ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>BTC rally</title><summary>BTC bullish, support holding</summary>
    <link href="https://x/3"/><id>a3</id><updated>2026-06-10T14:00:00Z</updated></entry>
</feed>"""


def test_parse_rss_and_atom():
    rss = parse_feed(_RSS, handle="Feed", weight=1.0)
    assert len(rss) == 2
    assert rss[0].id == "rss:g1" and rss[0].platform == "rss"
    assert rss[0].ts_ms > 0
    atom = parse_feed(_ATOM, handle="Feed", weight=1.0)
    assert len(atom) == 1 and atom[0].id == "rss:a3" and atom[0].ts_ms > 0


def test_parse_garbage_is_empty():
    assert parse_feed("not xml at all", handle="x") == []


def test_detect_symbols():
    assert detect_symbols("$BNB to the moon", ["BNB", "ETH"]) == ["BNB"]
    assert detect_symbols("ETH looks weak today", ["ETH"]) == ["ETH"]
    assert detect_symbols("nothing here", ["BNB"]) == []


def test_normalize_dedupe_and_tag():
    posts = parse_feed(_RSS, handle="Feed") + parse_feed(_RSS, handle="Feed")  # duplicates
    out = normalize(posts, universe=["BNB", "ETH"])
    assert len(out) == 2  # deduped by id
    assert out[0].ts_ms >= out[1].ts_ms  # newest first
    tagged = {s for p in out for s in p.symbols}
    assert "BNB" in tagged and "ETH" in tagged


def test_post_polarity_direction():
    assert post_polarity("bullish breakout moon strong") > 0
    assert post_polarity("bearish dump crash weak") < 0
    assert post_polarity("the cat sat on the mat") == 0.0


def test_score_bounds_and_determinism():
    now = int(time.time() * 1000)
    posts = [
        SocialPost(id="t:1", platform="rss", author="a", text="BNB bullish breakout moon",
                   ts_ms=now, symbols=["BNB"], weight=1.0),
        SocialPost(id="t:2", platform="rss", author="b", text="BNB strong, accumulate",
                   ts_ms=now, symbols=["BNB"], weight=2.0),
    ]
    r1 = score_symbol(posts, "BNB", now_ms=now)
    r2 = score_symbol(posts, "BNB", now_ms=now)
    assert r1 == r2                      # deterministic
    assert -1.0 <= r1.score <= 1.0
    assert 0.0 <= r1.confidence <= 1.0
    assert r1.score > 0 and r1.n_posts == 2


def test_score_no_posts_is_neutral():
    r = score_symbol([], "BNB", now_ms=123)
    assert r.score == 0.0 and r.confidence == 0.0 and r.n_posts == 0


def test_registry_has_all_platforms():
    plats = registered_platforms()
    for p in ("rss", "farcaster", "telegram", "twitter"):
        assert p in plats
    avail = available_platforms()
    assert avail["rss"] is True          # no creds needed
    # credential-gated adapters are unavailable in a bare test env
    assert avail["telegram"] is False and avail["twitter"] is False


def test_ingest_skips_unconfigured_sources_gracefully():
    # Only credential-gated platforms -> no network, all skipped, run still completes.
    specs = [
        SourceSpec(platform="twitter", handle="someone", enabled=True),
        SourceSpec(platform="telegram", handle="somechan", enabled=True),
    ]
    res = ingest(["BNB"], specs)
    assert res.posts == []
    assert "twitter" in res.skipped and "telegram" in res.skipped
    assert res.readings["BNB"].n_posts == 0
