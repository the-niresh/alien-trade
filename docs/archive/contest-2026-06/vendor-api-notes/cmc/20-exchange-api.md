# Exchange API

GitHub repo: [coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap](https://github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap)

APIs for centralized cryptocurrency exchanges (Binance, Coinbase, Kraken, etc.) including metadata, trading volumes, market pairs, and asset holdings.

## Authentication

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/exchange/map" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

Get your API key at [https://pro.coinmarketcap.com/login](https://pro.coinmarketcap.com/login)

**Base URL:** `https://pro-api.coinmarketcap.com`

## API Overview

| Endpoint | Description |
|----------|-------------|
| GET /v1/exchange/map | Map exchange names to CMC IDs |
| GET /v1/exchange/info | Exchange metadata (logo, URLs, description) |
| GET /v1/exchange/listings/latest | List all exchanges with market data |
| GET /v1/exchange/quotes/latest | Latest exchange volume and metrics |
| GET /v1/exchange/quotes/historical | Historical exchange volume data |
| GET /v1/exchange/market-pairs/latest | Trading pairs on an exchange |
| GET /v1/exchange/assets | Assets held by an exchange |

## Common Workflows

### Get Exchange Information

1. Call `/v1/exchange/map` with `slug=binance` to get the exchange ID
2. Call `/v1/exchange/info` with the ID to get full metadata

### Compare Exchange Volumes

1. Call `/v1/exchange/listings/latest` to get all exchanges ranked by volume
2. Use `sort=volume_24h` and `sort_dir=desc` for descending order

### Analyze Trading Pairs

1. Get the exchange ID from `/v1/exchange/map`
2. Call `/v1/exchange/market-pairs/latest` with that ID
3. Filter by `category=spot` or `category=derivatives`

### Track Volume History

1. Get the exchange ID from `/v1/exchange/map`
2. Call `/v1/exchange/quotes/historical` with date range parameters

## Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | CMC exchange ID (comma-separated for multiple) |
| slug | string | Exchange slug (e.g., "binance") |
| convert | string | Currency for price conversion (default: USD) |
| aux | string | Additional fields to include in response |

## Common Use Cases

1. Get exchange information by name
2. Find an exchange's CMC ID
3. Get top exchanges by volume
4. Get only spot or derivatives exchanges
5. Get current volume for a specific exchange
6. Compare volume across multiple exchanges
7. Get historical volume for an exchange
8. Get all trading pairs on an exchange
9. Find BTC pairs on an exchange
10. Get perpetual/futures pairs on an exchange
11. Check exchange reserves (proof-of-reserves)
12. Find exchanges that list a specific coin
