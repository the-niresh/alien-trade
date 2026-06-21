# Which CoinMarketCap API Endpoint Should I Use?

> For the complete CoinMarketCap API documentation index, see [llms.txt](https://pro.coinmarketcap.com/llms.txt). For a single-file dump of all documentation, see [llms-full.txt](https://pro.coinmarketcap.com/llms-full.txt).

Use this page when you know what you want to build, but you are not yet sure which part of the API to start with. The task chooser below points you to the right API family first. The full category tables remain below if you prefer to browse the API by section.

## Start with your goal

| If you want to...                                          | Start here                                                                                                                                                                           | Typical endpoint patterns                                         |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| Get the latest prices for assets you already know          | [Cryptocurrency](/pro-api-reference/cryptocurrency)                                                                                                                                  | `quotes/latest`, `price-performance-stats/latest`                 |
| Get a ranked list of top assets by market cap              | [Cryptocurrency](/pro-api-reference/cryptocurrency)                                                                                                                                  | `listings/latest`, `trending/*`                                   |
| Fetch historical prices or candlestick data                | [Cryptocurrency](/pro-api-reference/cryptocurrency) and [OHLCV](/pro-api-reference/ohlcv)                                                                                            | `quotes/historical`, `ohlcv/historical`                           |
| Look up metadata, IDs, logos, or mappings                  | [Cryptocurrency](/pro-api-reference/cryptocurrency), [Exchange](/pro-api-reference/exchange), and [Tools](/pro-api-reference/tools)                                                  | `info`, `map`, `price-conversion`                                 |
| Analyze centralized exchanges and market pairs             | [Exchange](/pro-api-reference/exchange)                                                                                                                                              | `info`, `listings/latest`, `market-pairs/latest`, `assets`        |
| Work with DEX tokens, pairs, and on-chain trading activity | [Token](/pro-api-reference/token), [Platform](/pro-api-reference/platform), and [OHLCV](/pro-api-reference/ohlcv)                                                                    | token lookup, pair quotes, pool/liquidity data, OHLCV             |
| Understand the broader market and sentiment                | [Global Metrics](/pro-api-reference/global-metrics), [CMC Index](/pro-api-reference/cmc-index), [Content](/pro-api-reference/content), and [Community](/pro-api-reference/community) | market cap, dominance, indices, headlines, trending topics        |
| Convert prices or export a Postman helper                  | [Tools](/pro-api-reference/tools)                                                                                                                                                    | `price-conversion`, `postman`                                     |

## Quick rules that save time

- Use `listings` endpoints when you want sorted, paginated lists.
- Use `quotes`, `info`, and `market-pairs` endpoints when you already know which assets or exchanges you care about.
- Use `*/latest` for current market data and `*/historical` for time-series data.
- Use `*/info` for descriptive metadata and `*/map` for stable identifiers.
- Use CoinMarketCap IDs when possible; they are more stable than symbols.
- Use the guides for [authentication](/guides/authentication), [response format and IDs](/guides/standards-and-conventions), and [rate limits and troubleshooting](/guides/errors-and-rate-limits).

---

## Browse all API families

The CoinMarketCap API reference is organized into four groups: market data, DEX data, utilities, and legacy endpoints.

### Market Data

Core centralized market data for cryptocurrency prices, exchange volumes, global metrics, news, and community trends.

| Category                                            | Use it for                                                                                          |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| [Cryptocurrency](/pro-api-reference/cryptocurrency) | Quotes, listings, OHLCV, market pairs, trending, categories, airdrops, and price performance stats. |
| [Exchange](/pro-api-reference/exchange)             | Exchange metadata, rankings, volume quotes, market pairs, and proof-of-reserves assets.             |
| [Derivatives](/pro-api-reference/derivatives)       | Perpetual and futures market pairs by exchange, with open interest, index price, and funding rate.  |
| [Global Metrics](/pro-api-reference/global-metrics) | Aggregate market cap, BTC/ETH dominance, total market volume, and historical market-wide views.     |
| [Content](/pro-api-reference/content)               | News headlines, Alexandria content, community posts, and post comments.                             |
| [Community](/pro-api-reference/community)           | Trending topics and trending tokens driven by community activity.                                   |
| [CMC Index](/pro-api-reference/cmc-index)           | CoinMarketCap indices such as CMC 100 and CMC 20.                                                   |

---

### DEX Data

On-chain DEX trading data across hundreds of decentralized exchanges on Ethereum, Solana, BNB Chain, and more.

| Category                                | Use it for                                                                                                                                                                   |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Token](/pro-api-reference/token)       | Token lookup, batch queries, price, liquidity, pools, transactions, trending lists, new tokens, meme tokens, gainers/losers, and security analysis.                         |
| [Platform](/pro-api-reference/platform) | Supported blockchain networks and DEX platform details.                                                                                                                      |
| [Holder](/pro-api-reference/holder)     | Token holder analytics and distribution data.                                                                                                                                |
| [OHLCV](/pro-api-reference/ohlcv)       | Candlestick data and OHLCV price history for DEX pairs.                                                                                                                      |
| [Others](/pro-api-reference/others)     | Additional DEX endpoints including trade data and blockchain statistics.                                                                                                     |

---

### Utilities

| Category                          | Use it for                                                                         |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| [Tools](/pro-api-reference/tools) | Fiat ID maps, API key usage info, price conversion, and Postman collection export. |

---

### Legacy

| Category                                    | Description                                                                                                                             |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [Deprecated](/pro-api-reference/deprecated) | Legacy endpoints retained for backward compatibility. Includes ERC-8056 UI multiplier endpoints, older quote versions, and other archived surfaces. |
