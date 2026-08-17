# CMC Agent Hub — 12-Tool Coverage Map (L1 sponsor depth)

> AWAKE_SPRINT §3.5 (L1). Maps the CoinMarketCap Agent Hub **Data MCP (12 tools)** to
> our four-signal strategy + the two CMC Marketplace skills we publish. The goal: show
> deep, deliberate use of the data layer (one of the three stackable $2k prizes), and
> name the gaps we close for the thesis factory.

## Coverage table

| # | CMC Agent Hub MCP tool (data category) | Our use | Where (file) | Status |
|---|----------------------------------------|---------|--------------|--------|
| 1 | **Latest quotes** (price) | Live mark price each cycle | `core/data/cmc_client.py` | ✅ used |
| 2 | **OHLCV historical** | Backtest + walk-forward corpus | `core/data/cmc_client.py`, `core/data/corpus/market.py` | ✅ used |
| 3 | **OHLCV latest** (intraday) | 1h live bars on the hot path | `core/data/cmc_client.py` | ✅ used |
| 4 | **Derivatives — funding rate** | S2 contrarian-on-extremes | `core/signals/derivatives.py` | ✅ used |
| 5 | **Derivatives — open interest** | S2 trend confirm/deny | `core/signals/derivatives.py` | ✅ used |
| 6 | **On-chain exchange flow** | S4 net-outflow accumulation | `core/signals/onchain.py` | ✅ used |
| 7 | **Whale / large-txn flow** | S4 confirmation | `core/signals/onchain.py` | ◑ partial (flow yes, whale-tag pending) |
| 8 | **Social sentiment** | S3 rate-of-change of attention | `core/signals/sentiment.py`, `core/data/sentiment_history.py` | ✅ used |
| 9 | **KOL / influencer signal** | S3 enrich + **wisdom-corpus source** | `core/data/corpus/wisdom.py` (allowlist) | ◑ wired as corpus source |
| 10 | **News feed** | Event intel + **corpus distillation source** | Researcher fan-out → `research/distill.py` | ◑ wired as corpus source |
| 11 | **Global metrics** (dominance, total mcap) | Regime context | regime detector input | ○ planned |
| 12 | **Listings / market pairs** | Eligible-token universe sanity | `risk/guardrails.py` allowlist | ○ planned |

Legend: ✅ on the hot path · ◑ wired (corpus/enrichment) · ○ planned/low-priority.

**Score:** 8/12 in active use, 2 newly wired as corpus sources (news + KOL — the §3.5
gap-closure), 2 planned (global metrics, listings) as low-marginal-value context.

## Gap closure done this sprint (news + KOL → the thesis factory)

The two highest-value missing tools were **news** and **KOL** — not for the trade hot
path (LLM stays off it, locked decision #1), but as **wisdom-corpus sources** feeding
distillation:

- `core/data/corpus/wisdom.py::SOURCE_ALLOWLIST` — KOL channels are an explicit, frozen,
  curated set (nothing self-expanding); `distill_ready()` wraps their text as untrusted
  data before it reaches the LLM.
- News headlines feed the same `research/distill.py` boundary → structured `ThesisCard`s
  → walk-forward tested → logged in the thesis ledger.

This keeps the CMC data layer doing what it's best at (breadth of signal) while our
deterministic `/core` owns every trade decision.

## Marketplace skills we publish back

1. **`alien_trade_multi_signal_score`** — the four-signal score (Track-2). `POST /skill/signal_score`.
2. **`alien_trade_thesis_check`** — falsification-as-a-service over the thesis ledger.
   `POST /skill/thesis_check`. Both manifests at `GET /skill/manifests`.

## x402 micropayment provenance

Every CMC data call from the runtime is metered via TWAK-native x402 at $0.01/call
(`agent/server.py` x402 provider). The cross-layer "cent that became a trade" trace
(`docs/CROSS_LAYER_TRACE.md`) follows one such cent end-to-end.
