# Coin Research

GitHub repo: [coinmarketcap-official/CoinMarketCap-CLI](https://github.com/coinmarketcap-official/CoinMarketCap-CLI)

Quick, structured single-coin research using the `cmc` CLI. Covers the main research dimensions in one pass without a multi-model debate.

## When to Use

- User says "research BTC", "look at SOL", "tell me about ETH", or "coin overview"
- User wants a quick asset profile before deciding whether to run a deeper analysis workflow
- User asks "what's happening with X" for a specific crypto asset

## When Not to Use

- Full investment analysis with bull/bear debate
- Market-wide scan with no specific coin
- Stock analysis

## Research Pipeline

```text
Step 1: Identity Resolution
    ↓
Step 2: Price + Fundamentals + Chain Stats
    ↓
Step 3: Historical Price Action
    ↓
Step 4: Market Structure
    ↓
Step 5: Market Context
    ↓
Step 6: News & Sentiment
    ↓
Synthesis: Structured Research Report
```

## Execution

### Step 1: Identity Resolution

```bash
# If user gives a symbol/name, resolve to CMC ID first
cmc resolve --symbol BTC -o json

# If ambiguous, search
cmc search bitcoin -o json
```

Extract `cmc_id`, `slug`, `name`, `symbol`, and `rank`.

### Step 2: Price + Fundamentals + Chain Stats

```bash
# Single enriched call — gets quotes + info + blockchain stats
cmc price --id <cmc_id> --with-info --with-chain-stats -o json
```

Extract from quotes: price, market_cap, volume_24h, percent_change_24h/7d/30d.
Extract from info: description, tags, and URLs such as website, explorer, github, and twitter.
Extract from chain_stats: consensus_mechanism, hashrate, tps_24h, total_transactions.

### Step 3: Historical Price Action

```bash
# 7-day hourly candles
cmc history --id <cmc_id> --days 7 --ohlc --interval hourly -o json

# 30-day daily candles
cmc history --id <cmc_id> --days 30 --ohlc -o json
```

Analyze trend direction, volatility, support/resistance levels, and volume patterns.

### Step 4: Market Structure

```bash
# Top trading pairs across spot + derivatives
cmc pairs <slug> --category all --limit 20 -o json
```

Analyze liquidity distribution, exchange concentration, and spot vs derivatives ratio.

### Step 5: Market Context

```bash
# Global metrics
cmc metrics -o json

# Top movers
cmc top-gainers-losers --time-period 24h --limit 20 -o json
```

Analyze asset performance vs market, BTC dominance trend, and sector rotation signals.

### Step 6: News & Sentiment

```bash
# Latest news
cmc news --limit 10 -o json

# Community trending
cmc trending --limit 10 -o json
```

Analyze catalyst events, narrative alignment, and social momentum.

## Output Format

Present findings as a structured report:

```markdown
# <Name> (<Symbol>) Research Report

## Overview
- **Rank**: #X | **Price**: $X | **Market Cap**: $X
- **24h Change**: X% | **7d**: X% | **30d**: X%
- **Volume 24h**: $X | **Vol/MCap Ratio**: X%

## Fundamentals
- **Description**: (1-2 sentences from info)
- **Tags/Sectors**: [list]
- **Chain Stats**: consensus, hashrate/TPS, transaction activity
- **Key Links**: website, explorer, github, twitter

## Price Action (7d / 30d)
- **Short-term trend**: (up/down/sideways + key levels)
- **Medium-term trend**: (up/down/sideways + key levels)
- **Volatility**: (high/medium/low relative to recent history)

## Market Structure
- **Top exchanges**: (by volume)
- **Liquidity**: (spot vs derivatives split)
- **Pair concentration**: (how distributed)

## Market Context
- **BTC Dominance**: X% (trend)
- **Total Market Cap**: $X (trend)
- **Asset vs Market**: outperforming / underperforming / in-line
- **Sector momentum**: (relevant sector trends)

## News & Sentiment
- **Key headlines**: (top 3 relevant)
- **Social trending**: (is asset trending? community signals)
- **Catalyst watch**: (upcoming events if any)

## Quick Assessment
- **Strengths**: (2-3 bullet points)
- **Risks**: (2-3 bullet points)
- **Next step**: "Run a deeper analysis workflow for a full investment view"
```

## Data Gaps

The following dimensions are not available via cmc-cli as a single first-class call:
- Technical indicators such as RSI, MACD, and Bollinger bands
- Fear & Greed Index
- Trending narratives
- Community topics
- Price performance stats beyond the fetched history window
- Category or sector classification

## Tips

- Always use `--id` over `--symbol` after resolution for determinism
- Use `-o json` for all data fetching, `-o table` only for final human display
- Run Steps 2-6 in parallel where possible after Step 1
- If an enrichment flag fails, fall back gracefully and keep the report moving
- Keep the synthesis concise
