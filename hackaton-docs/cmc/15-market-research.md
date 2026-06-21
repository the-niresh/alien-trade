Crypto Research

GitHub repo: coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap

Perform comprehensive due diligence on any cryptocurrency by systematically gathering and analyzing data from multiple CMC MCP tools.
Prerequisites

Before starting research, verify the CMC MCP tools are available. If tools fail or return connection errors, set up the MCP connection:

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
Research Workflow
Step 1: Identify the Token

Call search_cryptos with the token name/symbol to get the CMC ID.
Step 2: Basic Information

Call get_crypto_info to get:

    Project description and category
    Launch date
    Website, social links, documentation
    Tags (DeFi, Layer 1, Meme coin, etc.)

Step 3: Market Data

Call get_crypto_quotes_latest to get:

    Current price and market cap
    24h, 7d, 30d, 90d, 1y price changes
    Trading volume and volume change
    Circulating supply vs max supply
    Market cap rank

Step 4: Holder Analysis

Call get_crypto_metrics to get:

    Address distribution by holding value ($0-1k, $1k-100k, $100k+)
    Whale concentration (% held by top holders)
    Holder behavior (traders vs cruisers vs long-term holders)

Step 5: Technical Analysis

Call get_crypto_technical_analysis to get:

    Moving averages (7d, 30d, 200d SMA/EMA)
    RSI (oversold < 30, overbought > 70)
    MACD signal
    Fibonacci levels and pivot points

Step 6: Recent News

Call get_crypto_latest_news with limit 5-10 to get recent headlines and sentiment.
Step 7: Deep Dive (if needed)

Call search_crypto_info to answer specific questions about the token's technology, use case, or mechanics.
Analysis Framework
Fundamentals

    What problem does it solve?
    Is there a working product?
    How does it compare to competitors?
    Is the use case sustainable?

Tokenomics

    What % of max supply is circulating?
    Is there inflation or deflation?
    Are there large unlocks coming?
    How concentrated is ownership?

Market Position

    Market cap rank and trajectory
    Volume relative to market cap (healthy turnover?)
    Price trend (accumulation or distribution?)

Risk Assessment

Red Flags:

    Extreme whale concentration (>10% held by few addresses)
    Low holder count relative to market cap
    Declining holder numbers
    Negative news sentiment
    Price down >80% from ATH with no recovery
    Very low trading volume

Green Flags:

    Growing holder base
    High % of long-term holders
    Healthy distribution across address sizes
    Active development and news flow
    Strong community engagement

Report Structure

Code
## [Token Name] Research Report

### Overview
- Category: [DeFi/Layer 1/Meme/etc.]
- Launched: [Date]
- Rank: #XX by market cap

### Market Data
- Price: $X.XX
- Market Cap: $X.XX B
- 24h Volume: $X.XX M
- Performance: 24h X.X% | 7d X.X% | 30d X.X% | 1y X.X%

### Supply
- Circulating: X.XX M (XX% of max)
- Max Supply: X.XX M

### Holder Analysis
- Total Addresses: X.XX M
- Whale Concentration: X.X%
- Long-term Holders: XX%
- Holder Trend: Growing/Stable/Declining

### Technical Outlook
- RSI: XX (oversold/neutral/overbought)
- Trend: Above/Below 200d MA
- Key Support: $X.XX
- Key Resistance: $X.XX

### Recent News
- [Headline 1]
- [Headline 2]

### Green Flags
- [List positive indicators]

### Red Flags
- [List concerns]

### Summary
[2-3 sentence synthesis of the research findings]

Required Tools
Tool	Report Section
search_cryptos	Token identification
get_crypto_info	Overview
get_crypto_quotes_latest	Market Data, Supply
get_crypto_metrics	Holder Analysis
get_crypto_technical_analysis	Technical Outlook
get_crypto_latest_news	Recent News
search_crypto_info	Deep Dive

This is research data, not financial advice. Always present both positive and negative findings.
