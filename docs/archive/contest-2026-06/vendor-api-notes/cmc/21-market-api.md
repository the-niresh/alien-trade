# Market API

GitHub repo: [coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap](https://github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap)

Market-wide cryptocurrency data including global metrics, sentiment indicators, market indices, community activity, news content, charting data, and utility endpoints.

## Authentication

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

Get your API key at [https://pro.coinmarketcap.com/login](https://pro.coinmarketcap.com/login)

**Base URL:** `https://pro-api.coinmarketcap.com`

## API Overview

### Global Metrics

| Endpoint | Description |
|----------|-------------|
| GET /v1/global-metrics/quotes/historical | Historical global market metrics |
| GET /v1/global-metrics/quotes/latest | Latest total market cap, BTC dominance |

### Fear and Greed Index

| Endpoint | Description |
|----------|-------------|
| GET /v3/fear-and-greed/historical | Historical fear/greed values |
| GET /v3/fear-and-greed/latest | Current market sentiment score |

### Market Indices

| Endpoint | Description |
|----------|-------------|
| GET /v3/index/cmc100-historical | CMC100 index history |
| GET /v3/index/cmc100-latest | CMC100 current value |
| GET /v3/index/cmc20-historical | CMC20 index history |
| GET /v3/index/cmc20-latest | CMC20 current value |

### Community

| Endpoint | Description |
|----------|-------------|
| GET /v1/community/trending/token | Trending tokens by community activity |
| GET /v1/community/trending/topic | Trending discussion topics |

### Content

| Endpoint | Description |
|----------|-------------|
| GET /v1/content/latest | Latest news and Alexandria articles |
| GET /v1/content/posts/comments | Comments on a specific post |
| GET /v1/content/posts/latest | Latest community posts |
| GET /v1/content/posts/top | Top ranked community posts |

### K-Line Charts

| Endpoint | Description |
|----------|-------------|
| GET /v1/k-line/candles | OHLCV candlestick data |
| GET /v1/k-line/points | Time series price/market cap points |

### Tools

| Endpoint | Description |
|----------|-------------|
| GET /v1/fiat/map | Map fiat currencies to CMC IDs |
| GET /v1/key/info | API key usage and plan details |
| GET /v2/tools/price-conversion | Convert between currencies |

## Common Workflows

### Get Market Sentiment Overview

1. Fetch fear/greed index: `/v3/fear-and-greed/latest`
2. Get global metrics: `/v1/global-metrics/quotes/latest`
3. Combine for sentiment analysis with market cap context

### Track Market Index Performance

1. Get current CMC100 value: `/v3/index/cmc100-latest`
2. Fetch historical data: `/v3/index/cmc100-historical`
3. Compare performance over time

### Monitor Community Activity

1. Check trending tokens: `/v1/community/trending/token`
2. Review trending topics: `/v1/community/trending/topic`
3. Read latest posts: `/v1/content/posts/top`

### Build Price Charts

1. Fetch OHLCV candles: `/v1/k-line/candles`
2. Use interval parameter for timeframe (1h, 4h, 1d)
3. Plot candlestick chart with returned data

## Common Use Cases

1. Get current market sentiment (Fear & Greed)
2. Get total crypto market cap
3. Get BTC dominance
4. Track market cap history
5. Track Fear & Greed history
6. Get CMC100 index performance
7. Compare CMC100 vs CMC20
8. Get OHLCV candlestick data for charts
9. Get community trending tokens
10. Get trending discussion topics
11. Get latest crypto news
12. Convert currency amounts
13. Check API usage and limits

## Tips

- Use `/v1/key/info` to check your plan limits before heavy usage
- Cache global metrics data as it updates every few minutes
- Fear/greed index updates daily, no need for frequent polling
- K-line data supports multiple intervals for different chart timeframes
- Community trending data refreshes periodically throughout the day
