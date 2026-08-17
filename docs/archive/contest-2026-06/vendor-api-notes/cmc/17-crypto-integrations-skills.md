# Cryptocurrency API

GitHub repo: [coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap](https://github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap)

REST API endpoints for retrieving price data, market listings, historical quotes, trending coins, and token metadata.

## Authentication

All requests require an API key in the header.

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

Get your API key at [https://pro.coinmarketcap.com/login](https://pro.coinmarketcap.com/login)

**Base URL:** `https://pro-api.coinmarketcap.com`

## API Overview

| Endpoint | Description |
|----------|-------------|
| GET /v1/cryptocurrency/categories | List all categories with market metrics |
| GET /v1/cryptocurrency/category | Single category details |
| GET /v1/cryptocurrency/listings/historical | Historical listings snapshot |
| GET /v1/cryptocurrency/listings/latest | Current listings with market data |
| GET /v1/cryptocurrency/listings/new | Newly added cryptocurrencies |
| GET /v1/cryptocurrency/map | Map names/symbols to CMC IDs |
| GET /v1/cryptocurrency/trending/gainers-losers | Top gainers and losers |
| GET /v1/cryptocurrency/trending/latest | Currently trending coins |
| GET /v1/cryptocurrency/trending/most-visited | Most visited on CMC |
| GET /v2/cryptocurrency/info | Static metadata (logo, description, URLs) |
| GET /v2/cryptocurrency/market-pairs/latest | Trading pairs for a coin |
| GET /v2/cryptocurrency/ohlcv/historical | Historical OHLCV candles |
| GET /v2/cryptocurrency/ohlcv/latest | Latest OHLCV data |
| GET /v2/cryptocurrency/price-performance-stats/latest | Price performance stats |
| GET /v2/cryptocurrency/quotes/latest | Latest price quotes |
| GET /v3/cryptocurrency/quotes/historical | Historical price quotes |

## Common Workflows

### Get Token Price by Symbol

```bash
# Step 1: Get CMC ID for ETH
curl -X GET "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map?symbol=ETH" \
  -H "X-CMC_PRO_API_KEY: your-api-key"

# Step 2: Get price quote (using id=1027 for ETH)
curl -X GET "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?id=1027" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

### Get Top 100 Coins by Market Cap

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit=100&sort=market_cap" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

### Get Historical Price Data

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/historical?id=1&time_start=2024-01-01&time_end=2024-01-31&interval=daily" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

### Get Token Metadata

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v2/cryptocurrency/info?id=1,1027" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

## Common Use Cases

1. Get current price of a token
2. Find a token's CMC ID from symbol or name
3. Get a token by contract address
4. Get top 100 coins by market cap
5. Find coins in a price range
6. Get historical price at a specific date
7. Build a price chart (OHLCV data)
8. Find where a coin trades
9. Get all-time high and distance from ATH
10. Find today's biggest gainers
11. Discover newly listed coins
12. Get all tokens in a category (e.g., DeFi)

## Error Handling

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 403 | Forbidden (endpoint not available on your plan) |
| 429 | Rate limit exceeded |
| 500 | Server error |

## Response Format

```json
{
  "status": {
    "timestamp": "2024-01-15T12:00:00.000Z",
    "error_code": 0,
    "error_message": null,
    "credit_count": 1
  },
  "data": { ... }
}
```
