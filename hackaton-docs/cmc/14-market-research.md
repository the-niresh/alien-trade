Market Report

GitHub repo: coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap

Generate a comprehensive crypto market report by systematically pulling data from multiple CMC MCP tools.
Prerequisites

Before generating a report, verify the CMC MCP tools are available. If tools fail or return connection errors, set up the MCP connection:

Code
{
  "mcpServers": {
    "cmc-mcp": {
      "url": "https://mcp.coinmarketcap.com/mcp",
      "headers": {
        "X-CMC-MCP-API-KEY": "your-api-key"
      }
    }
  }
}

Get your API key from https://pro.coinmarketcap.com/login
Report Workflow
Step 1: Global Market Health

Call get_global_metrics_latest to get:

    Total crypto market cap and 24h/7d/30d changes
    Fear & Greed Index (current value and trend)
    Altcoin Season Index
    BTC and ETH dominance
    Total volume
    ETF flows (BTC and ETH)

Step 2: Market Technical Analysis

Call get_crypto_marketcap_technical_analysis to get:

    Total market cap RSI
    MACD signals
    Key support/resistance levels (Fibonacci, pivot points)

Step 3: Leverage and Derivatives

Call get_global_crypto_derivatives_metrics to get:

    Total open interest and changes
    Funding rates (positive = longs paying shorts)
    BTC liquidations (long vs short bias)
    Futures vs perpetuals breakdown

Step 4: Trending Narratives

Call trending_crypto_narratives to get:

    Top trending themes/sectors
    Market cap and performance of each narrative
    Top coins within each narrative

Step 5: Upcoming Catalysts

Call get_upcoming_macro_events to get:

    Fed meetings and rate decisions
    Regulatory deadlines
    Major protocol upgrades

Step 6: BTC and ETH Quick Check

Call get_crypto_quotes_latest with id="1,1027" to get current BTC and ETH prices and changes as anchors for the report.
Report Structure

Code
## Market Snapshot
- Total market cap: $X.XX T (24h: +X.X%)
- Fear & Greed: XX (Extreme Fear/Fear/Neutral/Greed/Extreme Greed)
- BTC Dominance: XX% | ETH Dominance: XX%
- Altcoin Season Index: XX

## BTC & ETH
- BTC: $XX,XXX (24h: X.X%, 7d: X.X%)
- ETH: $X,XXX (24h: X.X%, 7d: X.X%)

## Market Technicals
- RSI: XX (oversold/neutral/overbought)
- MACD: bullish/bearish
- Key levels: support at $X.XX T, resistance at $X.XX T

## Leverage & Sentiment
- Open Interest: $XXX B (24h: X.X%)
- Funding Rate: X.XXX% (longs/shorts paying)
- 24h Liquidations: $XXX M (XX% longs, XX% shorts)

## Trending Narratives
1. Narrative Name - $XX B market cap, +XX% (7d)
2. ...

## Upcoming Catalysts
- Date: Event description
- ...

Adapting the Report

    Quick summary: Focus on Market Snapshot and BTC/ETH sections only
    Full report: Include all sections
    Specific focus: Expand the requested section with more detail

Required Tools
Tool	Report Section
get_global_metrics_latest	Market Snapshot
get_crypto_marketcap_technical_analysis	Market Technicals
get_global_crypto_derivatives_metrics	Leverage & Sentiment
trending_crypto_narratives	Trending Narratives
get_upcoming_macro_events	Upcoming Catalysts
get_crypto_quotes_latest	BTC & ETH
