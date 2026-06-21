# DEX API

GitHub repo: [coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap](https://github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap)

On-chain token data APIs for decentralized exchanges like Uniswap, PancakeSwap, and Raydium.

## Authentication

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/dex/platform/list" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

Get your API key at [https://pro.coinmarketcap.com/login](https://pro.coinmarketcap.com/login)

**Base URL:** `https://pro-api.coinmarketcap.com`

## POST vs GET Endpoints

Many DEX endpoints use POST for complex queries with body parameters:
- **GET** endpoints pass parameters as query strings
- **POST** endpoints pass parameters in JSON body with `Content-Type: application/json`

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| /v1/dex/token | GET | Token details by platform/address |
| /v1/dex/token/price | GET | Latest DEX price for a token |
| /v1/dex/token/price/batch | POST | Batch token prices |
| /v1/dex/token/pools | GET | Liquidity pools for a token |
| /v1/dex/token-liquidity/query | GET | Token liquidity over time |
| /v1/dex/tokens/batch-query | POST | Batch token metadata |
| /v1/dex/tokens/transactions | GET | Recent DEX transactions |
| /v1/dex/tokens/trending/list | POST | Trending DEX tokens |
| /v4/dex/pairs/quotes/latest | GET | Latest DEX pair quotes |
| /v4/dex/spot-pairs/latest | GET | DEX spot pairs listing |
| /v1/dex/platform/list | GET | List supported DEX platforms |
| /v1/dex/platform/detail | GET | Platform details |
| /v1/dex/search | GET | Search DEX tokens/pairs |
| /v1/dex/gainer-loser/list | POST | Top DEX gainers/losers |
| /v1/dex/liquidity-change/list | GET | Tokens with liquidity changes |
| /v1/dex/meme/list | POST | Meme tokens on DEX |
| /v1/dex/new/list | POST | Newly discovered DEX tokens |
| /v1/dex/security/detail | GET | Token security/risk signals |

## Common Workflows

### Get DEX Token Information

1. Search for token: `/v1/dex/search?keyword=PEPE`
2. Get token details: `/v1/dex/token?network_slug=ethereum&contract_address=0x...`
3. Check security risks: `/v1/dex/security/detail?network_slug=ethereum&contract_address=0x...`

### Analyze Token Liquidity

1. Get token pools: `/v1/dex/token/pools?network_slug=ethereum&contract_address=0x...`
2. Get liquidity history: `/v1/dex/token-liquidity/query?network_slug=ethereum&contract_address=0x...`

### Find Trending Tokens

1. Get trending tokens: POST `/v1/dex/tokens/trending/list` with filters
2. Get gainers/losers: POST `/v1/dex/gainer-loser/list`
3. Find new tokens: POST `/v1/dex/new/list`

## Key Parameters

Most DEX endpoints require:
- `network_slug` or `platform_crypto_id`: Identifies the blockchain (ethereum, solana, bsc)
- `contract_address`: The token's on-chain contract address

Use `/v1/dex/platform/list` to get valid network slugs and platform IDs.

## Common Use Cases

1. Get DEX token price by contract address
2. Find a token's contract address by name
3. Get prices for multiple tokens at once
4. Check token security before trading
5. Find liquidity pools for a token
6. Find trending DEX tokens
7. Find today's biggest DEX gainers
8. Find newly launched tokens
9. Detect potential rug pulls (liquidity removal)
10. Get recent trades for a token
11. Get supported networks and DEXs
12. Get meme coins
