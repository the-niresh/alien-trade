# Social Ingestion Layer - "bring your own KOL list"

The user curates a watchlist of traders/channels; the agent watches them so the
user doesn't have to ("makes them lazy"). Posts across multiple platforms are
ingested through swappable adapters, normalised, and reduced - **off the trade
hot path** - into a bounded, deterministic sentiment feature that feeds signal
**S3** (which was stubbed at 0.0). Raw posts also fuel the Second Brain
researcher + co-pilot.

Why it's a differentiator: most teams use CMC's single social score. We ingest
*raw posts from the user's own chosen KOLs* across channels, score them
deterministically, and **cross-check against CMC hard data** (funding/OI/flow) so
a tweet alone never moves size. Personalised + multi-channel + risk-disciplined.

---

## Where it lives

```
agent/social/
  schema.py            SocialPost · SourceSpec · SentimentReading  (contracts-first)
  normalize.py         dedupe · time-filter · symbol detection
  score.py             deterministic lexicon scorer -> SentimentReading
  ingest.py            orchestrator + CLI (load watchlist -> fan-out -> score)
  watchlist.example.json
  sources/
    base.py            SocialSource protocol + registry (@register)
    rss.py             RSS/Atom  - NO creds (works today)
    farcaster.py       Warpcast public API - NO creds (works today)
    telegram.py        Telethon - credential-gated
    twitter.py         twscrape - credential-gated, ToS-risk, BURNER account
```

## Data flow (mirrors the Option-B forecast bridge)

```
user watchlist (Convex social_sources, user-writable)
  -> fan out across enabled adapters (failure-isolated: one source down != run down)
  -> SocialPost[] -> normalize (dedupe, tag symbols)
  -> [OFF hot path] deterministic lexicon score -> SentimentReading{score[-1,1], confidence[0,1]}
       |- Convex social_posts  (the UI feed / "agent activity")
       |- Convex sentiment_state  (the bounded number signal S3 reads, point-in-time)
       \- Second Brain (raw posts -> researcher digests + co-pilot citations)
```

**Locked-decision compliance:** the LLM is *not* in this path - scoring is a
deterministic lexicon (reproducible, sim/live-parity safe). Any LLM enrichment is
async and never produces the number that crosses into the decision. The sentiment
reading can only inform sizing *within* risk caps (shrink-or-confirm), like the
forecast bridge - never enlarge a position.

## Adapters & status

| Platform | Adapter | Creds? | Status |
|----------|---------|--------|--------|
| RSS/Atom | `rss.py` | none | ✅ live (tested + real pull) |
| Farcaster | `farcaster.py` | none | ✅ live (Warpcast public API) |
| Telegram | `telegram.py` | api_id/api_hash/session | 🔌 built, switch on with creds |
| X/Twitter | `twitter.py` | burner account (twscrape) | 🔌 built, switch on with creds |

Adding a channel later = write an adapter + `@register("name")`. Nothing else
changes.

## Run

```bash
core/.venv/Scripts/python.exe -m pytest agent/tests/test_social.py -q
core/.venv/Scripts/python.exe -m agent.social.ingest --once
core/.venv/Scripts/python.exe -m agent.social.ingest --once --json
core/.venv/Scripts/python.exe -m agent.social.ingest --once --watchlist my.json
```

First live run pulled 30 RSS + 8 Farcaster posts with zero credentials; Telegram
and X were cleanly skipped as "not configured".

## Enabling the gated channels (operator, optional)

**Telegram** (legit, recommended): free `api_id`/`api_hash` from
`https://my.telegram.org`; `uv pip install --python core/.venv/Scripts/python.exe
telethon`; generate a `StringSession` once; set `TELEGRAM_API_ID`,
`TELEGRAM_API_HASH`, `TELEGRAM_SESSION` in `.env.local`.

**X/Twitter** (ToS-risk, use a BURNER): `uv pip install --python … twscrape`; add
+ login a burner X account into twscrape's db; set `X_ACCOUNTS_READY=1`. Treated
as one swappable adapter on purpose - it can break/ban without affecting the rest.

## Next steps (not yet wired)

1. Convex `social.ts` mutations/queries (write `social_posts`/`sentiment_state`,
   user CRUD on `social_sources`) so the PWA hosts the watchlist + feed.
2. Schedule ingest via Trigger.dev (every N min, off hot path).
3. Bridge `sentiment_state` -> core signal S3 with point-in-time discipline
   (same care as the forecast bridge; covered by a parity test).
4. Optional LLM enrichment (claim extraction, manipulation/pump detection) via
   the Second Brain - async, never on the number that reaches the core.

See `AGENT_TEAM_PLAN.md` (§9 patterns, failure matrix) and `STRATEGY.md` (S3).
