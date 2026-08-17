Deprecated
Deprecated (V1) Endpoints

These endpoints have been replaced by their V2/V3 versions and are no longer actively supported. We strongly recommend migrating to the latest versions.

    /v1/cryptocurrency/info - Metadata v1
    /v1/tools/price-conversion - Price Conversion v1
    /v1/cryptocurrency/market-pairs/latest - Market Pairs Latest v1
    /v1/cryptocurrency/ohlcv/historical - OHLCV Historical v1
    /v1/cryptocurrency/ohlcv/latest - OHLCV Latest v1
    /v1/cryptocurrency/price-performance-stats/latest - Price Performance Stats v1
    /v1/cryptocurrency/quotes/historical - Quotes Historical v1
    /v1/cryptocurrency/quotes/latest - Quotes Latest v1
    /v1/partners/flipside-crypto/fcas/listings/latest - FCAS Listings Latest
    /v1/partners/flipside-crypto/fcas/quotes/latest - FCAS Quotes Latest

Legacy cryptocurrency quotes (V2)

Prefer /v3/cryptocurrency/quotes/latest and /v3/cryptocurrency/quotes/historical.

    /v2/cryptocurrency/quotes/latest - Quotes Latest v2
    /v2/cryptocurrency/quotes/historical - Quotes Historical v2

Legacy ERC-8056 UI multiplier endpoints

    /v1/cryptocurrency/multiplier - Cryptocurrency Multiplier
    /v2/dex/multiplier - Get Token Multiplier

Cryptocurrency Multiplier
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/multiplier

Returns a paginated list of cryptocurrencies that has a ERC-8056 UI multiplier.

Filtering and pagination

    Use crypto_id, crypto_slug, symbol, or token_address to look up specific cryptocurrencies. These four filters are mutually exclusive, pass only one per request. Omit all four to page through every cryptocurrency that currently has a UI multiplier, sorted by ascending CoinMarketCap ID.
    total_size is the total number of results before pagination.
    start and limit paginate the list (1-based start, default start=1, limit=100). has_more is true when start + limit has not yet reached total_size.

No credit is needed when querying this endpoint.

Cache / Update frequency: Refreshed whenever multiplier changes are applied. CMC equivalent pages: Cryptocurrency detail pages that display adjusted supply or price using the UI multiplier.
Cryptocurrency Multiplier › query Parameters
crypto_id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: 1,1027. Mutually exclusive with crypto_slug, symbol, and token_address.
crypto_slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

One or more comma-separated cryptocurrency slugs. Example: bitcoin,ethereum. Mutually exclusive with crypto_id, symbol, and token_address.
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

One or more comma-separated cryptocurrency symbols. Example: BTC,ETH. Symbols are uppercased server-side. When multiple assets share a symbol, the lowest CoinMarketCap ID is used. Mutually exclusive with crypto_id, crypto_slug, and token_address.
token_address
​string

One or more comma-separated contract addresses. Mutually exclusive with crypto_id, crypto_slug, and symbol.
skip_invalid
​boolean

Pass true to skip invalid crypto_id, crypto_slug, symbol, or token_address values and return only resolvable matches. When false (default), the request fails with 400 if any lookup value is invalid.
Default: false
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list. Non-positive values fall back to the default of 1.
Default: 1
limit
​integer · min: 1 · max: 2000

Optionally specify the number of results to return. Use this parameter and the "start" parameter for pagination. Non-positive values fall back to the default of 100.
Default: 100
Cryptocurrency Multiplier › Responses

Successful
Cryptocurrency_Multiplier_-_Response_Model
​Cryptocurrency_Multiplier_-_Data_object · required

Paginated multiplier results.
​API_Status_Object · required

Standardized status object for API calls.
GET/v1/cryptocurrency/multiplier
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/multiplier
Example Responses
{
  "status": {
    "timestamp": "2026-05-11T07:30:00.123Z",
    "error_code": 0,
    "error_message": null,
    "elapsed": 12,
    "credit_count": 0,
    "notice": null
  },
  "data": {
    "total_size": 2,
    "has_more": false,
    "items": [
      {
        "crypto_id": 1,
        "crypto_slug": "bitcoin",
        "name": "Bitcoin",
        "symbol": "BTC",
        "multiplier": 1,
        "effective_at": "2026-05-10T10:30:00Z",
        "token_address": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
        "platform_id": 14
      },
      {
        "crypto_id": 1027,
        "crypto_slug": "ethereum",
        "name": "Ethereum",
        "symbol": "ETH",
        "multiplier": 1,
        "effective_at": "2026-05-10T13:30:00Z"
      }
    ]
  }
}
json
application/json
Metadata v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/info

Returns all static metadata available for one or more cryptocurrencies. This information includes details like logo, description, official website URL, social links, and links to a cryptocurrency's technical documentation.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Static data is updated only as needed, every 30 seconds.
Plan credit use: 1 call credit per 100 cryptocurrencies returned (rounded up).
CMC equivalent pages: Cryptocurrency detail page metadata like coinmarketcap.com/currencies/bitcoin/.
Metadata v1 (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,2"
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "slug" or "symbol" is required for this request. Please note that starting in the v2 endpoint, due to the fact that a symbol is not unique, if you request by symbol each data response will contain an array of objects containing all of the coins that use each requested symbol. The v1 endpoint will still return a single object, the highest ranked coin using that symbol.
address
​string

Alternatively pass in a contract address. Example: "0xc40af1e4fecfa05ce6bab79dcd8b373d2e436c4e"
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if any invalid cryptocurrencies are requested or a cryptocurrency does not have matching records in the requested timeframe. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: false
aux
​string · pattern: ^(urls|logo|descript…

Optionally specify a comma-separated list of supplemental data fields to return. Pass urls,logo,description,tags,platform,date_added,notice,status to include all auxiliary fields.
Default: urls,logo,description,tags,platform,date_added,notice
Metadata v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Metadata v1 (deprecated) › Responses

Successful
Cryptocurrencies_Info_-_Response_Model
​Cryptocurrency_Info_-_Results_map · required

Results of your query returned as an object map.
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/info
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/info \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "urls": {
        "website": [
          "https://bitcoin.org/"
        ],
        "technical_doc": [
          "https://bitcoin.org/bitcoin.pdf"
        ],
        "twitter": [],
        "reddit": [
          "https://reddit.com/r/bitcoin"
        ],
        "message_board": [
          "https://bitcointalk.org"
        ],
        "announcement": [],
        "chat": [],
        "explorer": [
          "https://blockchain.coinmarketcap.com/chain/bitcoin",
          "https://blockchain.info/",
          "https://live.blockcypher.com/btc/"
        ],
        "source_code": [
          "https://github.com/bitcoin/"
        ]
      },
      "logo": "https://s2.coinmarketcap.com/static/img/coins/64x64/1.png",
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "slug": "bitcoin",
      "description": "Bitcoin (BTC) is a consensus network that enables a new payment system and a completely digital currency. Powered by its users, it is a peer to peer payment network that requires no central authority to operate. On October 31st, 2008, an individual or group of individuals operating under the pseudonym \"Satoshi Nakamoto\" published the Bitcoin Whitepaper and described it as: \"a purely peer-to-peer version of electronic cash would allow online payments to be sent directly from one party to another without going through a financial institution.\"",
      "date_added": "2013-04-28T00:00:00.000Z",
      "date_launched": "2013-04-28T00:00:00.000Z",
      "tags": [
        "mineable"
      ],
      "platform": null,
      "category": "coin"
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Price Conversion v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/tools/price-conversion

Convert an amount of one cryptocurrency or fiat currency into one or more different currencies utilizing the latest market rate for each currency. You may optionally pass a historical timestamp as time to convert values based on historical rates (as your API plan supports).

Technical Notes

    Latest market rate conversions are accurate to 1 minute of specificity. Historical conversions are accurate to 1 minute of specificity outside of non-USD fiat conversions which have 5 minute specificity.
    You may reference a current list of all supported cryptocurrencies via the cryptocurrency/map endpoint. This endpoint also returns the supported date ranges for historical conversions via the first_historical_data and last_historical_data properties.
    Conversions are supported in 93 different fiat currencies and 4 precious metals as outlined here. Historical fiat conversions are supported as far back as 2013-04-28.
    A last_updated timestamp is included for both your source currency and each conversion currency. This is the timestamp of the closest market rate record referenced for each currency during the conversion.

This endpoint is available on the following API plans:

    Basic (Latest market price conversions)
    Hobbyist (Latest market price conversions + 1 month historical)
    Startup (Latest market price conversions + 1 month historical)
    Standard (Latest market price conversions + 3 months historical)
    Professional (Latest market price conversions + 12 months historical)
    Enterprise (Latest market price conversions + up to 6 years historical)

Cache / Update frequency: Every 60 seconds for the lastest cryptocurrency and fiat currency rates.
Plan credit use: 1 call credit per call and 1 call credit per convert option beyond the first.
CMC equivalent pages: Our cryptocurrency conversion page at coinmarketcap.com/converter/.
Price Conversion v1 (deprecated) › query Parameters
amount
​number · min: 1e-8 · max: 1000000000000 · required

An amount of currency to convert. Example: 10.43
id
​string · pattern: ^\d*$

The CoinMarketCap currency ID of the base cryptocurrency or fiat to convert from. Example: "1"
symbol
​string · pattern: ^[0-9A-Za-z$@\-]*$

Alternatively the currency symbol of the base cryptocurrency or fiat to convert from. Example: "BTC". One "id" or "symbol" is required. Please note that starting in the v2 endpoint, due to the fact that a symbol is not unique, if you request by symbol each quote response will contain an array of objects containing all of the coins that use each requested symbol. The v1 endpoint will still return a single object, the highest ranked coin using that symbol.
time
​string

Optional timestamp (Unix or ISO 8601) to reference historical pricing during conversion. If not passed, the current time will be used. If passed, we'll reference the closest historic values available for this conversion.
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Pass up to 120 comma-separated fiat or cryptocurrency symbols to convert the source amount to.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Price Conversion v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Price Conversion v1 (deprecated) › Responses

Successful
Tools_Price_Conversion_-_Response_Model
​Tools_Price_Conversion_-_Results_Object · required

Results object for your API call.
​API_Status_Object

Standardized status object for API calls.
GET/v1/tools/price-conversion
curl --request GET \
  --url 'https://pro-api.coinmarketcap.com/v1/tools/price-conversion?amount=%3Cnumber%3E' \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "symbol": "BTC",
    "id": 1,
    "name": "Bitcoin",
    "amount": 50,
    "last_updated": "2018-06-06T08:04:36.000Z",
    "quote": {
      "USD": {
        "price": 284656.08465608465,
        "last_updated": "2018-06-06T06:00:00.000Z"
      }
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Market Pairs Latest v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/market-pairs/latest

Lists all active market pairs that CoinMarketCap tracks for a given cryptocurrency or fiat currency. All markets with this currency as the pair base or pair quote will be returned. The latest price and volume information is returned for each market. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 1 minute.
Plan credit use: 1 call credit per 100 market pairs returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Our active cryptocurrency markets pages like coinmarketcap.com/currencies/bitcoin/#markets.
Market Pairs Latest v1 (deprecated) › query Parameters
id
​string

A cryptocurrency or fiat currency by CoinMarketCap ID to list market pairs for. Example: "1"
slug
​string · pattern: ^[0-9a-z-]*$

Alternatively pass a cryptocurrency by slug. Example: "bitcoin"
symbol
​string · pattern: ^[0-9A-Za-z$@\-]*$

Alternatively pass a cryptocurrency by symbol. Fiat currencies are not supported by this field. Example: "BTC". A single cryptocurrency "id", "slug", or "symbol" is required.
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 5000

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 100
sort_dir
​string · enum

Optionally specify the sort direction of markets returned.
Enum values:
asc
desc
Default: desc
sort
​string · enum

Optionally specify the sort order of markets returned. By default we return a strict sort on 24 hour reported volume. Pass cmc_rank to return a CMC methodology based sort where markets with excluded volumes are returned last.
Enum values:
volume_24h_strict
cmc_rank
cmc_rank_advanced
effective_liquidity
market_score
market_reputation
Default: volume_24h_strict
aux
​string · pattern: ^(num_market_pairs|c…

Optionally specify a comma-separated list of supplemental data fields to return. Pass num_market_pairs,category,fee_type,market_url,currency_name,currency_slug,price_quote,notice,cmc_rank,effective_liquidity,market_score,market_reputation to include all auxiliary fields.
Default: num_market_pairs,category,fee_type
matched_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally include one or more fiat or cryptocurrency IDs to filter market pairs by. For example ?id=1&matched_id=2781 would only return BTC markets that matched: "BTC/USD" or "USD/BTC". This parameter cannot be used when matched_symbol is used.
matched_symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally include one or more fiat or cryptocurrency symbols to filter market pairs by. For example ?symbol=BTC&matched_symbol=USD would only return BTC markets that matched: "BTC/USD" or "USD/BTC". This parameter cannot be used when matched_id is used.
category
​string · enum

The category of trading this market falls under. Spot markets are the most common but options include derivatives and OTC.
Enum values:
all
spot
derivatives
otc
perpetual
Default: all
fee_type
​string · enum

The fee type the exchange enforces for this market.
Enum values:
all
percentage
no-fees
transactional-mining
unknown
Default: all
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Market Pairs Latest v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Market Pairs Latest v1 (deprecated) › Responses

Successful
Cryptocurrency_Market_Pairs_Latest_-_Response_Model
​Cryptocurrency_Market_Pairs_Latest_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/market-pairs/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/market-pairs/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "id": 1,
    "name": "Bitcoin",
    "symbol": "BTC",
    "num_market_pairs": 7526,
    "market_pairs": [
      {
        "exchange": {
          "id": 157,
          "name": "BitMEX",
          "slug": "bitmex"
        },
        "market_id": 4902,
        "market_pair": "BTC/USD",
        "category": "derivatives",
        "fee_type": "no-fees",
        "market_pair_base": {
          "currency_id": 1,
          "currency_symbol": "BTC",
          "exchange_symbol": "XBT",
          "currency_type": "cryptocurrency"
        },
        "market_pair_quote": {
          "currency_id": 2781,
          "currency_symbol": "USD",
          "exchange_symbol": "USD",
          "currency_type": "fiat"
        },
        "quote": {
          "exchange_reported": {
            "price": 7839,
            "volume_24h_base": 434215.85308502,
            "volume_24h_quote": 3403818072.33347,
            "last_updated": "2019-05-24T02:39:00.000Z"
          },
          "USD": {
            "price": 7839,
            "volume_24h": 3403818072.33347,
            "last_updated": "2019-05-24T02:39:00.000Z"
          }
        }
      },
      {
        "exchange": {
          "id": 108,
          "name": "Negocie Coins",
          "slug": "negocie-coins"
        },
        "market_id": 3377,
        "market_pair": "BTC/BRL",
        "category": "spot",
        "fee_type": "percentage",
        "market_pair_base": {
          "currency_id": 1,
          "currency_symbol": "BTC",
          "exchange_symbol": "BTC",
          "currency_type": "cryptocurrency"
        },
        "market_pair_quote": {
          "currency_id": 2783,
          "currency_symbol": "BRL",
          "exchange_symbol": "BRL",
          "currency_type": "fiat"
        },
        "quote": {
          "exchange_reported": {
            "price": 33002.11,
            "volume_24h_base": 336699.03559957,
            "volume_24h_quote": 11111778609.7509,
            "last_updated": "2019-05-24T02:39:00.000Z"
          },
          "USD": {
            "price": 8165.02539531659,
            "volume_24h": 2749156176.2491,
            "last_updated": "2019-05-24T02:39:00.000Z"
          }
        }
      }
    ]
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
OHLCV Historical v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/ohlcv/historical

Returns historical OHLCV (Open, High, Low, Close, Volume) data along with market cap for any cryptocurrency using time interval parameters. Currently daily and hourly OHLCV periods are supported. Volume is not currently supported for hourly OHLCV intervals before 2020-09-22.

Technical Notes

    Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time for this "time_period".
    One OHLCV quote will be returned for every "time_period" between your "time_start" (exclusive) and "time_end" (inclusive).
    If a "time_start" is not supplied, the "time_period" will be calculated in reverse from "time_end" using the "count" parameter which defaults to 10 results.
    If "time_end" is not supplied, it defaults to the current time.
    If you don't need every "time_period" between your dates you may adjust the frequency that "time_period" is sampled using the "interval" parameter. For example with "time_period" set to "daily" you may set "interval" to "2d" to get the daily OHLCV for every other day. You could set "interval" to "monthly" to get the first daily OHLCV for each month, or set it to "yearly" to get the daily OHLCV value against the same date every year.

Implementation Tips

    If querying for a specific OHLCV date your "time_start" should specify a timestamp of 1 interval prior as "time_start" is an exclusive time parameter (as opposed to "time_end" which is inclusive to the search). This means that when you pass a "time_start" results will be returned for the next complete "time_period". For example, if you are querying for a daily OHLCV datapoint for 2018-11-30 your "time_start" should be "2018-11-29".
    If only specifying a "count" parameter to return latest OHLCV periods, your "count" should be 1 number higher than the number of results you expect to receive. "Count" defines the number of "time_period" intervals queried, not the number of results to return, and this includes the currently active time period which is incomplete when working backwards from current time. For example, if you want the last daily OHLCV value available simply pass "count=2" to skip the incomplete active time period.
    This endpoint supports requesting multiple cryptocurrencies in the same call. Please note the API response will be wrapped in an additional object in this case.

Interval Options

There are 2 types of time interval formats that may be used for "time_period" and "interval" parameters. For "time_period" these return aggregate OHLCV data from the beginning to end of each interval period. Apply these time intervals to "interval" to adjust how frequently "time_period" is sampled.

The first are calendar year and time constants in UTC time:
"hourly" - Hour intervals in UTC.
"daily" - Calendar day intervals for each UTC day.
"weekly" - Calendar week intervals for each calendar week.
"monthly" - Calendar month intervals for each calendar month.
"yearly" - Calendar year intervals for each calendar year.

The second are relative time intervals.
"h": Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h".
"d": Time periods that repeat every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d".

Please note that "time_period" currently supports the "daily" and "hourly" options. "interval" supports all interval options.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup (1 month)
    Standard (3 months)
    Professional (12 months)
    Enterprise (Up to 6 years)

Cache / Update frequency: Latest Daily OHLCV record is available ~5 to ~10 minutes after each midnight UTC. The latest hourly OHLCV record is available 5 minutes after each UTC hour.
Plan credit use: 1 call credit per 100 OHLCV data points returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Our historical cryptocurrency data pages like coinmarketcap.com/currencies/bitcoin/historical-data/.
OHLCV Historical v1 (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,1027"
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "slug" or "symbol" is required for this request.
time_period
​string · enum

Time period to return OHLCV data for. The default is "daily". If hourly, the open will be 01:00 and the close will be 01:59. If daily, the open will be 00:00:00 for the day and close will be 23:59:99 for the same day. See the main endpoint description for details.
Enum values:
daily
hourly
Default: daily
time_start
​string

Timestamp (Unix or ISO 8601) to start returning OHLCV time periods for. Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time.
time_end
​string

Timestamp (Unix or ISO 8601) to stop returning OHLCV time periods for (inclusive). Optional, if not passed we'll default to the current time. Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time.
count
​number · min: 1 · max: 10000

Optionally limit the number of time periods to return results for. The default is 10 items. The current query limit is 10000 items.
Default: 10
interval
​string · enum

Optionally adjust the interval that "time_period" is sampled. For example with interval=monthly&time_period=daily you will see a daily OHLCV record for January, February, March and so on. See main endpoint description for available options.
Enum values:
hourly
daily
weekly
monthly
yearly
1h
2h
3h
Default: daily
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 fiat currencies or cryptocurrencies.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if any invalid cryptocurrencies are requested or a cryptocurrency does not have matching records in the requested timeframe. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
OHLCV Historical v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
OHLCV Historical v1 (deprecated) › Responses

Successful
Cryptocurrency_OHLCV_Historical_-_Response_Model
​Cryptocurrency_OHLCV_Historical_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/ohlcv/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "id": 1,
    "name": "Bitcoin",
    "symbol": "BTC",
    "quotes": [
      {
        "time_open": "2019-01-02T00:00:00.000Z",
        "time_close": "2019-01-02T23:59:59.999Z",
        "time_high": "2019-01-02T03:53:00.000Z",
        "time_low": "2019-01-02T02:43:00.000Z",
        "quote": {
          "USD": {
            "open": 3849.21640853,
            "high": 3947.9812729,
            "low": 3817.40949569,
            "close": 3943.40933686,
            "volume": 5244856835.70851,
            "market_cap": 68849856731.6738,
            "timestamp": "2019-01-02T23:59:59.999Z"
          }
        }
      },
      {
        "time_open": "2019-01-03T00:00:00.000Z",
        "time_close": "2019-01-03T23:59:59.999Z",
        "time_high": "2019-01-02T03:53:00.000Z",
        "time_low": "2019-01-02T02:43:00.000Z",
        "quote": {
          "USD": {
            "open": 3931.04863841,
            "high": 3935.68513083,
            "low": 3826.22287069,
            "close": 3836.74131867,
            "volume": 4530215218.84018,
            "market_cap": 66994920902.7202,
            "timestamp": "2019-01-03T23:59:59.999Z"
          }
        }
      }
    ]
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
OHLCV Latest v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/ohlcv/latest

Returns the latest OHLCV (Open, High, Low, Close, Volume) market values for one or more cryptocurrencies for the current UTC day. Since the current UTC day is still active these values are updated frequently. You can find the final calculated OHLCV values for the last completed UTC day along with all historic days using /cryptocurrency/ohlcv/historical.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 10 minutes. Additional OHLCV intervals and 1 minute updates will be available in the future.
Plan credit use: 1 call credit per 100 OHLCV values returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: No equivalent, this data is only available via API.
OHLCV Latest v1 (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "symbol" is required.
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if any invalid cryptocurrencies are requested or a cryptocurrency does not have matching records in the requested timeframe. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
OHLCV Latest v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
OHLCV Latest v1 (deprecated) › Responses

Successful
Cryptocurrency_OHLCV_Latest_-_Response_Model
​Cryptocurrency_OHLCV_Latest_-_Cryptocurrency_Results_map · required

A map of cryptocurrency objects by ID or symbol (as passed in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/ohlcv/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "last_updated": "2018-09-10T18:54:00.000Z",
      "time_open": "2018-09-10T00:00:00.000Z",
      "time_close": "2019-08-30T23:59:59.999Z",
      "time_high": "2018-09-10T00:00:00.000Z",
      "time_low": "2018-09-10T00:00:00.000Z",
      "quote": {
        "USD": {
          "open": 6301.57,
          "high": 6374.98,
          "low": 6292.76,
          "close": 6308.76,
          "volume": 3786450000,
          "last_updated": "2018-09-10T18:54:00.000Z"
        }
      }
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Price Performance Stats v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/price-performance-stats/latest

Returns price performance statistics for one or more cryptocurrencies including launch price ROI and all-time high / all-time low. Stats are returned for an all_time period by default. UTC yesterday and a number of rolling time periods may be requested using the time_period parameter. Utilize the convert parameter to translate values into multiple fiats or cryptocurrencies using historical rates.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Plan credit use: 1 call credit per 100 cryptocurrencies returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: The statistics module displayed on cryptocurrency pages like Bitcoin.

NOTE: You may also use /cryptocurrency/ohlcv/historical for traditional OHLCV data at historical daily and hourly intervals. You may also use /v1/cryptocurrency/ohlcv/latest for OHLCV data for the current UTC day.
Price Performance Stats v1 (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "slug" or "symbol" is required for this request.
time_period
​string · pattern: ^(all_time|yesterday…

Specify one or more comma-delimited time periods to return stats for. all_time is the default. Pass all_time,yesterday,24h,7d,30d,90d,365d to return all supported time periods. All rolling periods have a rolling close time of the current request time. For example 24h would have a close time of now and an open time of 24 hours before now. Please note: yesterday is a UTC period and currently does not currently support high and low timestamps.
Default: all_time
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
Price Performance Stats v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Price Performance Stats v1 (deprecated) › Responses

Successful
Cryptocurrency_Price_Performance_Stats_Latest_-_Response_Model
​Cryptocurrency_Price_Performance_Stats_Latest_-_Cryptocurrency_Results_map · required

An object map of cryptocurrency objects by ID, slug, or symbol (as used in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/price-performance-stats/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/price-performance-stats/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "slug": "bitcoin",
      "last_updated": "2019-08-22T01:51:32.000Z",
      "periods": {
        "USD": {
          "open_timestamp": "2013-04-28T00:00:00.000Z",
          "high_timestamp": "2017-12-17T12:19:14.000Z",
          "low_timestamp": "2013-07-05T18:56:01.000Z",
          "close_timestamp": "2019-08-22T01:52:18.613Z",
          "quote": {
            "USD": {
              "open": 135.3000030517578,
              "open_timestamp": "2013-04-28T00:00:00.000Z",
              "high": 20088.99609375,
              "high_timestamp": "2017-12-17T12:19:14.000Z",
              "low": 65.5260009765625,
              "low_timestamp": "2013-07-05T18:56:01.000Z",
              "close": 65.5260009765625,
              "close_timestamp": "2019-08-22T01:52:18.618Z",
              "percent_change": 7223.718930042746,
              "price_change": 9773.691932798241
            }
          }
        }
      }
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Quotes Historical v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/quotes/historical

Returns an interval of historic market quotes for any cryptocurrency based on time and interval parameters.

Technical Notes

    A historic quote for every "interval" period between your "time_start" and "time_end" will be returned.
    If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end".
    If "time_end" is not supplied, it defaults to the current time.
    At each "interval" period, the historic quote that is closest in time to the requested time will be returned.
    If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped.

Implementation Tips

    Want to get the last quote of each UTC day? Don't use "interval=daily" as that returns the first quote. Instead use "interval=24h" to repeat a specific timestamp search every 24 hours and pass ex. "time_start=2019-01-04T23:59:00.000Z" to query for the last record of each UTC day.
    This endpoint supports requesting multiple cryptocurrencies in the same call. Please note the API response will be wrapped in an additional object in this case.

Interval Options
There are 2 types of time interval formats that may be used for "interval".

The first are calendar year and time constants in UTC time:
"hourly" - Get the first quote available at the beginning of each calendar hour.
"daily" - Get the first quote available at the beginning of each calendar day.
"weekly" - Get the first quote available at the beginning of each calendar week.
"monthly" - Get the first quote available at the beginning of each calendar month.
"yearly" - Get the first quote available at the beginning of each calendar year.

The second are relative time intervals.
"m": Get the first quote available every "m" minutes (60 second intervals). Supported minutes are: "5m", "10m", "15m", "30m", "45m".
"h": Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h".
"d": Get the first quote available every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d".

This endpoint is available on the following API plans:

    Basic
    Hobbyist (1 month)
    Startup (1 month)
    Standard (3 month)
    Professional (12 months)
    Enterprise (Up to 6 years)

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 call credit per 100 historical data points returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Our historical cryptocurrency charts like coinmarketcap.com/currencies/bitcoin/#charts.
Quotes Historical v1 (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,2"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "symbol" is required for this request.
time_start
​string

Timestamp (Unix or ISO 8601) to start returning quotes for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end".
time_end
​string

Timestamp (Unix or ISO 8601) to stop returning quotes for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time.
count
​number · min: 1 · max: 10000

The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 10 items. The current query limit is 10000.
Default: 10
interval
​string · enum

Interval of time to return data points for. See details in endpoint description.
Enum values:
yearly
monthly
weekly
daily
hourly
5m
10m
15m
Default: 5m
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies.
convert_id
​string · pattern: (^\d+(?:,\d+)*$|(\d,…

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
aux
​string · pattern: ^(price|volume|marke…

Optionally specify a comma-separated list of supplemental data fields to return. Pass price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat,search_interval to include all auxiliary fields.
Default: price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
Quotes Historical v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Historical v1 (deprecated) › Responses

Successful
Cryptocurrency_Quotes_Historical_-_Response_Model
​Cryptocurrency_Quotes_Historical_-_Results_map · required

Results of your query returned as an object map.
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/quotes/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "is_active": 1,
      "is_fiat": 0,
      "quotes": [
        {
          "timestamp": "2018-06-22T00:00:00.000Z",
          "quote": {
            "USD": {
              "price": 6242.48,
              "volume_24h": 4894120000,
              "market_cap": 107057808682,
              "last_updated": "2018-06-22T00:04:16.000Z",
              "volume_24hr": 4894120000,
              "timestamp": "2018-06-22T00:04:16.000Z"
            }
          }
        }
      ]
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Quotes Latest v1 (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/cryptocurrency/quotes/latest

Returns the latest market quote for 1 or more cryptocurrencies. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Plan credit use: 1 call credit per 100 cryptocurrencies returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Latest market data pages for specific cryptocurrencies like coinmarketcap.com/currencies/bitcoin/.

NOTE: Use this endpoint to request the latest quote for specific cryptocurrencies. If you need to request all cryptocurrencies use /v1/cryptocurrency/listings/latest which is optimized for that purpose. The response data between these endpoints is otherwise the same.
Quotes Latest v1 (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "slug" or "symbol" is required for this request.
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: (^\d+(?:,\d+)*$|(\d,…

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
aux
​string · pattern: ^(num_market_pairs|c…

Optionally specify a comma-separated list of supplemental data fields to return. Pass num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,market_cap_by_total_supply,volume_24h_reported,volume_7d,volume_7d_reported,volume_30d,volume_30d_reported,is_active,is_fiat to include all auxiliary fields.
Default: num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,is_active,is_fiat
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
Quotes Latest v1 (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Latest v1 (deprecated) › Responses

Successful
Cryptocurrency_Quotes_Latest_-_Response_Model
​Cryptocurrency_Quotes_Latest_-_Cryptocurrency_Results_map · required

A map of cryptocurrency objects by ID, symbol, or slug (as used in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v1/cryptocurrency/quotes/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "slug": "bitcoin",
      "is_active": 1,
      "is_fiat": 0,
      "circulating_supply": 17199862,
      "total_supply": 17199862,
      "max_supply": 21000000,
      "date_added": "2013-04-28T00:00:00.000Z",
      "num_market_pairs": 331,
      "cmc_rank": 1,
      "last_updated": "2018-08-09T21:56:28.000Z",
      "tags": [
        "mineable"
      ],
      "platform": null,
      "self_reported_circulating_supply": null,
      "self_reported_market_cap": null,
      "minted_market_cap": 1802955697670.94,
      "quote": {
        "USD": {
          "price": 6602.60701122,
          "volume_24h": 4314444687.5194,
          "volume_change_24h": -0.152774,
          "percent_change_1h": 0.988615,
          "percent_change_24h": 4.37185,
          "percent_change_7d": -12.1352,
          "percent_change_30d": -12.1352,
          "market_cap": 852164659250.2758,
          "market_cap_dominance": 51,
          "fully_diluted_market_cap": 952835089431.14,
          "last_updated": "2018-08-09T21:56:28.000Z"
        }
      }
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Quotes Historical v2
GET
https://pro-api.coinmarketcap.com
/v2/cryptocurrency/quotes/historical

Returns an interval of historic market quotes for any cryptocurrency based on time and interval parameters.

Please note: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found the deprecated section.

Technical Notes

    A historic quote for every "interval" period between your "time_start" and "time_end" will be returned.
    If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end".
    If "time_end" is not supplied, it defaults to the current time.
    At each "interval" period, the historic quote that is closest in time to the requested time will be returned.
    If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped.

Implementation Tips

    Want to get the last quote of each UTC day? Don't use "interval=daily" as that returns the first quote. Instead use "interval=24h" to repeat a specific timestamp search every 24 hours and pass ex. "time_start=2019-01-04T23:59:00.000Z" to query for the last record of each UTC day.
    This endpoint supports requesting multiple cryptocurrencies in the same call. Please note the API response will be wrapped in an additional object in this case.

Interval Options
There are 2 types of time interval formats that may be used for "interval".

The first are calendar year and time constants in UTC time:
"hourly" - Get the first quote available at the beginning of each calendar hour.
"daily" - Get the first quote available at the beginning of each calendar day.
"weekly" - Get the first quote available at the beginning of each calendar week.
"monthly" - Get the first quote available at the beginning of each calendar month.
"yearly" - Get the first quote available at the beginning of each calendar year.

The second are relative time intervals.
"m": Get the first quote available every "m" minutes (60 second intervals). Supported minutes are: "5m", "10m", "15m", "30m", "45m".
"h": Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h".
"d": Get the first quote available every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d".

This endpoint is available on the following API plans:

    Basic
    Hobbyist (1 month)
    Startup (1 month)
    Standard (3 month)
    Professional (12 months)
    Enterprise (Up to 6 years)

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 call credit per 100 historical data points returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Our historical cryptocurrency charts like coinmarketcap.com/currencies/bitcoin/#charts.
Quotes Historical v2 › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,2"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "symbol" is required for this request.
time_start
​string

Timestamp (Unix or ISO 8601) to start returning quotes for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end".
time_end
​string

Timestamp (Unix or ISO 8601) to stop returning quotes for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time.
count
​number · min: 1 · max: 10000

The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 10 items. The current query limit is 10000.
Default: 10
interval
​string · enum

Interval of time to return data points for. See details in endpoint description.
Enum values:
yearly
monthly
weekly
daily
hourly
5m
10m
15m
Default: 5m
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies.
convert_id
​string · pattern: (^\d+(?:,\d+)*$|(\d,…

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
aux
​string · pattern: ^(price|volume|marke…

Optionally specify a comma-separated list of supplemental data fields to return. Pass price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat,search_interval to include all auxiliary fields.
Default: price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
Quotes Historical v2 › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Historical v2 › Responses

Successful
Cryptocurrency_Quotes_Historical_-_Response_Model
​Cryptocurrency_Quotes_Historical_-_Results_map · required

Results of your query returned as an object map.
​API_Status_Object

Standardized status object for API calls.
GET/v2/cryptocurrency/quotes/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "is_active": 1,
      "is_fiat": 0,
      "quotes": [
        {
          "timestamp": "2018-06-22T00:00:00.000Z",
          "quote": {
            "USD": {
              "price": 6242.48,
              "volume_24h": 4894120000,
              "market_cap": 107057808682,
              "last_updated": "2018-06-22T00:04:16.000Z",
              "volume_24hr": 4894120000,
              "timestamp": "2018-06-22T00:04:16.000Z"
            }
          }
        }
      ]
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Quotes Latest v2
GET
https://pro-api.coinmarketcap.com
/v2/cryptocurrency/quotes/latest

Returns the latest market quote for 1 or more cryptocurrencies. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

Please note: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found the deprecated section.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Plan credit use: 1 call credit per 100 cryptocurrencies returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Latest market data pages for specific cryptocurrencies like coinmarketcap.com/currencies/bitcoin/.

NOTE: Use this endpoint to request the latest quote for specific cryptocurrencies. If you need to request all cryptocurrencies use /v1/cryptocurrency/listings/latest which is optimized for that purpose. The response data between these endpoints is otherwise the same.
Quotes Latest v2 › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "slug" or "symbol" is required for this request.
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: (^\d+(?:,\d+)*$|(\d,…

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
aux
​string · pattern: ^(num_market_pairs|c…

Optionally specify a comma-separated list of supplemental data fields to return. Pass num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,market_cap_by_total_supply,volume_24h_reported,volume_7d,volume_7d_reported,volume_30d,volume_30d_reported,is_active,is_fiat to include all auxiliary fields.
Default: num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,is_active,is_fiat
skip_invalid
​boolean

Pass true to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned.
Default: true
Quotes Latest v2 › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Latest v2 › Responses

Successful
Cryptocurrency_Quotes_Latest_-_Response_Model
​Cryptocurrency_Quotes_Latest_-_Cryptocurrency_Results_map · required

A map of cryptocurrency objects by ID, symbol, or slug (as used in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v2/cryptocurrency/quotes/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "slug": "bitcoin",
      "is_active": 1,
      "is_fiat": 0,
      "circulating_supply": 17199862,
      "total_supply": 17199862,
      "max_supply": 21000000,
      "date_added": "2013-04-28T00:00:00.000Z",
      "num_market_pairs": 331,
      "cmc_rank": 1,
      "last_updated": "2018-08-09T21:56:28.000Z",
      "tags": [
        "mineable"
      ],
      "platform": null,
      "self_reported_circulating_supply": null,
      "self_reported_market_cap": null,
      "minted_market_cap": 1802955697670.94,
      "quote": {
        "USD": {
          "price": 6602.60701122,
          "volume_24h": 4314444687.5194,
          "volume_change_24h": -0.152774,
          "percent_change_1h": 0.988615,
          "percent_change_24h": 4.37185,
          "percent_change_7d": -12.1352,
          "percent_change_30d": -12.1352,
          "market_cap": 852164659250.2758,
          "market_cap_dominance": 51,
          "fully_diluted_market_cap": 952835089431.14,
          "last_updated": "2018-08-09T21:56:28.000Z"
        }
      }
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
FCAS Listings Latest (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/partners/flipside-crypto/fcas/listings/latest

Returns a paginated list of FCAS scores for all cryptocurrencies currently supported by FCAS. FCAS ratings are on a 0-1000 point scale with a corresponding letter grade and is updated once a day at UTC midnight.

FCAS stands for Fundamental Crypto Asset Score, a single, consistently comparable value for measuring cryptocurrency project health. FCAS measures User Activity, Developer Behavior and Market Maturity and is provided by FlipSide Crypto. Find out more about FCAS methodology. Users interested in FCAS historical data including sub-component scoring may inquire through our CSV Data Delivery request form.

Disclaimer: Ratings that are calculated by third party organizations and are not influenced or endorsed by CoinMarketCap in any way.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Once a day at UTC midnight.
Plan credit use: 1 call credit per 100 FCAS scores returned (rounded up).
CMC equivalent pages: The FCAS ratings available under our cryptocurrency ratings tab like coinmarketcap.com/currencies/bitcoin/#ratings.

NOTE: Use this endpoint to request the latest FCAS score for all supported cryptocurrencies at the same time. If you require FCAS for only specific cryptocurrencies use /v1/partners/flipside-crypto/fcas/quotes/latest which is optimized for that purpose. The response data between these endpoints is otherwise the same.
FCAS Listings Latest (deprecated) › query Parameters
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 5000

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 100
aux
​string · pattern: ^(point_change_24h|p…

Optionally specify a comma-separated list of supplemental data fields to return. Pass point_change_24h,percent_change_24h to include all auxiliary fields.
Default: point_change_24h,percent_change_24h
FCAS Listings Latest (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
FCAS Listings Latest (deprecated) › Responses

Successful
FCAS_Listings_Latest_-_Response_Model
​FCAS_Listings_Latest_-_Cryptocurrency_object[] · required

Array of cryptocurrency objects matching the list options.
​API_Status_Object

Standardized status object for API calls.
GET/v1/partners/flipside-crypto/fcas/listings/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/partners/flipside-crypto/fcas/listings/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "id": 1027,
      "name": "Ethereum",
      "symbol": "ETH",
      "slug": "ethereum",
      "score": 971,
      "grade": "S",
      "last_updated": "2021-05-05T00:00:00Z"
    },
    {
      "id": 2010,
      "name": "Cardano",
      "symbol": "ADA",
      "slug": "cardano",
      "score": 961,
      "grade": "S",
      "last_updated": "2021-05-05T00:00:00Z"
    }
  ],
  "status": {
    "timestamp": "2018-06-02T22:51:28.209Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1
  }
}
json
application/json
FCAS Quotes Latest (deprecated)
GET
https://pro-api.coinmarketcap.com
/v1/partners/flipside-crypto/fcas/quotes/latest

Returns the latest FCAS score for 1 or more cryptocurrencies. FCAS ratings are on a 0-1000 point scale with a corresponding letter grade and is updated once a day at UTC midnight.

FCAS stands for Fundamental Crypto Asset Score, a single, consistently comparable value for measuring cryptocurrency project health. FCAS measures User Activity, Developer Behavior and Market Maturity and is provided by FlipSide Crypto. Find out more about FCAS methodology. Users interested in FCAS historical data including sub-component scoring may inquire through our CSV Data Delivery request form.

Disclaimer: Ratings that are calculated by third party organizations and are not influenced or endorsed by CoinMarketCap in any way.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Once a day at UTC midnight.
Plan credit use: 1 call credit per 100 FCAS scores returned (rounded up).
CMC equivalent pages: The FCAS ratings available under our cryptocurrency ratings tab like coinmarketcap.com/currencies/bitcoin/#ratings.

NOTE: Use this endpoint to request the latest FCAS score for specific cryptocurrencies. If you require FCAS for all supported cryptocurrencies use /v1/partners/flipside-crypto/fcas/listings/latest which is optimized for that purpose. The response data between these endpoints is otherwise the same.
FCAS Quotes Latest (deprecated) › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" or "slug" or "symbol" is required for this request.
aux
​string · pattern: ^(point_change_24h|p…

Optionally specify a comma-separated list of supplemental data fields to return. Pass point_change_24h,percent_change_24h to include all auxiliary fields.
Default: point_change_24h,percent_change_24h
FCAS Quotes Latest (deprecated) › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
FCAS Quotes Latest (deprecated) › Responses

Successful
FCAS_Quote_Latest_-_Response_Model
​FCAS_Quote_Latest_-_Cryptocurrency_Results_map · required

A map of cryptocurrency objects by ID or symbol (as used in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v1/partners/flipside-crypto/fcas/quotes/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/partners/flipside-crypto/fcas/quotes/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "name": "Bitcoin",
      "symbol": "BTC",
      "slug": "bitcoin",
      "score": 894,
      "grade": "A",
      "percent_change_24h": 0.56,
      "point_change_24h": 5,
      "last_updated": "2019-08-08T00:00:00Z"
    }
  },
  "status": {
    "timestamp": "2026-03-05T22:43:48.471Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1,
    "notice": ""
  }
}
json
application/json
Get token multiplier
GET
https://pro-api.coinmarketcap.com
/v2/dex/multiplier

Returns a paginated list of tokens that has a ERC-8056 UI multiplier.

You may filter by platform or platform_id (if both are provided, platform_id takes precedence). When querying a specific token via token_address, you must also provide at least one of platform or platform_id.

Pagination is controlled by start (1-based index) and limit (default 100, max 2000).

No credit is needed when querying this endpoint.
Get token multiplier › query Parameters
platform
​string

Platform name. If both platform and platform_id are provided, platform_id takes precedence.
platform_id
​integer · min: 1

Platform id. If both platform and platform_id are provided, platform_id takes precedence.
token_address
​string

Token address. If provided, at least one of platform or platform_id is required.
start
​integer · min: 1

Pagination start (1-based index). Default: 1.
Default: 1
limit
​integer · min: 1 · max: 2000

Number of results per page. Default: 100.
Default: 100
Get token multiplier › Responses

Successful
Dex_Multiplier_-_Response_Model
​Dex_Multiplier_-_Data_Object · required

Paginated ERC-8056 multiplier results.
​API_Status_Object · required

Standardized status object for API calls.
GET/v2/dex/multiplier
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v2/dex/multiplier
Example Responses
{
  "data": {
    "total_size": 2,
    "items": [
      {
        "platform_id": 14,
        "platform": "bsc",
        "token_address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "Dogecoin",
        "symbol": "DOGE",
        "multiplier": 0.01,
        "effective_at": "2026-05-19T10:30:00Z"
      },
      {
        "platform_id": 14,
        "platform": "bsc",
        "token_address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "Zest Protocol",
        "symbol": "ZEST",
        "multiplier": 0.01,
        "effective_at": "2026-05-19T10:30:00Z"
      }
    ],
    "has_more": false
  },
  "status": {
    "timestamp": "2026-05-19T10:59:42.581Z",
    "error_code": 0,
    "error_message": null,
    "elapsed": 83,
    "credit_count": 0,
    "notice": null
  }
}
json
application/json
Trades Latest
GET
https://pro-api.coinmarketcap.com
/v4/dex/pairs/trade/latest

Returns up to the latest 100 trades for 1 spot pair. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.
Trades Latest › query Parameters
contract_address
​string

One or more comma-separated contract addresses.
network_id
​string

One CoinMarketCap cryptocurrency network id.
network_slug
​string

Alternatively, one network names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens).
aux
​string

Default:"" Valid values: "transaction_hash" "blockchain_explorer_link" Optionally specify a comma-separated list of supplemental data fields to return.
convert_id
​string

Optionally calculate market quotes in up to 30 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency IDs. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found in our API document. Each conversion is returned in its own "trade" object.
skip_invalid
​string

Pass true to relax request validation rules. When requesting records on multiple spot pairs an error is returned if no match is found for 1 or more requested spot pairs. If set to true, invalid lookups will be skipped allowing valid spot pairs to still be returned.
Default: true
reverse_order
​string

Pass true to invert the order of a spot pair. For example, a trading pair is set up as Token B/Token A in the contract and is commonly referred to as Token A/Token B. Using reverse_order would change the order to reflect the true Token B/Token A pairing as it exists in the pool.
Default: false
Trades Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Trades Latest › Responses
200

OK
​DexPairsTradeDTO[]
DexPairsTradeDTO
​DexTransactionDTO[]

A map of market quotes in different currency conversions. The default map included is USD.
contract_address
​string

The unique contract address for this spot pair.
name
​string

The name of this spot pair.
base_asset_id
​string

The id of this base asset in the spot pair.
base_asset_ucid
​string

The ucid of this base asset in the spot pair.
base_asset_name
​string

The name of this base asset in the spot pair.
base_asset_symbol
​string

The symbol of this base asset in the spot pair.
base_asset_contract_address
​string

The contract addres of this base asset in the spot pair.
quote_asset_id
​string

The id of this quote asset in the spot pair.
quote_asset_ucid
​string

The ucid of this quote asset in the spot pair.
quote_asset_name
​string

The name of this quote asset in the spot pair.
quote_asset_symbol
​string

The symbol of this quote asset in the spot pair.
quote_asset_contract_address
​string

The contract addresss of this quote asset in the spot pair.
dex_id
​string

The id of this dex the spot pair is on.
dex_slug
​string

The name of this dex the spot pair is on.
network_id
​string

The id of the network the spot pair is on.
network_slug
​string

The slug of the network the spot pair is on.
last_updated
​string · date-time

Timestamp (ISO 8601) of the last time this record was updated.
created_at
​string · date-time

Timestamp (ISO 8601) when we started tracking this asset.
num_transactions_24h
​integer · int64

Number of transactions in past 24 hours
holders
​integer · int64

Number of holders of the asset
24h_no_of_buys
​integer · int64

Number of asset buys in the past 24 hours
24h_no_of_sells
​integer · int64

Number of asset sells in the past 24 hours
pool_created
​string · date-time

When the pool of the asset was created
buy_tax
​number · bigdecimal

Buy tax on the asset
sell_tax
​number · bigdecimal

Sell tax on the asset
​SecurityScanResult[]

Security scan by Go+.

All infomation and data relating to contract detection are based on public third party information. CoinMarketCap does not confirm or verify the accuracy or timeliness of such information and data.

CoinMarketCap shall have no responsibility or liability for the accuracy of data, nor have the duty to review, confirm, verify or otherwise perform any inquiry or investigation as to the completeness, accuracy, sufficiency, integrity, reliability or timeliness of any such information or data provided.

Only returned if passed in aux.
pool_base_asset
​number · bigdecimal

Base asset in the pool
pool_quote_asset
​number · bigdecimal

Quote asset in the pool
percent_pooled_base_asset
​number · bigdecimal

Percentage of the base asset in the pool
24h_volume_quote_asset
​number · bigdecimal

24 hours volume of the quote asset
total_supply_quote_asset
​number · bigdecimal

Total supply of the quote asset
total_supply_base_asset
​number · bigdecimal

Total supply of the quote asset
date_launched
​string · date-time

Timestamp (ISO 8601) of the launch date for this exchange.
GET/v4/dex/pairs/trade/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v4/dex/pairs/trade/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
[
  {
    "trades": [
      {
        "date": "2024-08-25T15:00:00Z",
        "type": "type",
        "quote": [
          {
            "price": 0,
            "total": 0,
            "convert_id": "convert_id",
            "price_by_quote_asset": 0,
            "amount_base_asset": 0,
            "amount_quote_asset": 0
          }
        ],
        "transaction_hash": "transaction_hash",
        "blockchain_explorer_link": "blockchain_explorer_link"
      }
    ],
    "contract_address": "contract_address",
    "name": "name",
    "base_asset_id": "base_asset_id",
    "base_asset_ucid": "base_asset_ucid",
    "base_asset_name": "base_asset_name",
    "base_asset_symbol": "base_asset_symbol",
    "base_asset_contract_address": "base_asset_contract_address",
    "quote_asset_id": "quote_asset_id",
    "quote_asset_ucid": "quote_asset_ucid",
    "quote_asset_name": "quote_asset_name",
    "quote_asset_symbol": "quote_asset_symbol",
    "quote_asset_contract_address": "quote_asset_contract_address",
    "dex_id": "dex_id",
    "dex_slug": "dex_slug",
    "network_id": "network_id",
    "network_slug": "network_slug",
    "last_updated": "2024-08-25T15:00:00Z",
    "created_at": "2024-08-25T15:00:00Z",
    "num_transactions_24h": 0,
    "holders": 0,
    "24h_no_of_buys": 0,
    "24h_no_of_sells": 0,
    "pool_created": "2024-08-25T15:00:00Z",
    "buy_tax": 0,
    "sell_tax": 0,
    "security_scan": [
      {
        "third_party": {
          "open_source": true,
          "proxy": true,
          "mintable": true,
          "can_take_back_ownership": true,
          "owner_change_balance": true,
          "hidden_owner": true,
          "self_destruct": true,
          "external_call": true,
          "cannot_buy": true,
          "cannot_sell_all": true,
          "slippage_modifiable": true,
          "honeypot": true,
          "transfer_pausable": true,
          "blacklisted": true,
          "whitelisted": true,
          "in_dex": true,
          "anti_whale": true,
          "anti_whale_modifiable": true,
          "trading_cool_down": true,
          "personal_slippage_modifiable": true,
          "trust_list": true,
          "true_token": true,
          "airdrop_scam": true
        },
        "aggregated": {
          "contract_verified": true,
          "honeypot": true
        }
      }
    ],
    "pool_base_asset": 0,
    "pool_quote_asset": 0,
    "percent_pooled_base_asset": 0,
    "24h_volume_quote_asset": 0,
    "total_supply_quote_asset": 0,
    "total_supply_base_asset": 0,
    "date_launched": "2024-08-25T15:00:00Z"
  }
]
json
application/json
OHLCV Latest
GET
https://pro-api.coinmarketcap.com
/v4/dex/pairs/ohlcv/latest

Returns the latest OHLCV (Open, High, Low, Close, Volume) market values for one or more spot pairs for the current UTC day. Since the current UTC day is still active these values are updated frequently. You can find the final calculated OHLCV values for the last completed UTC day along with all historic days using /dex/pairs/ohlcv/historical.
OHLCV Latest › query Parameters
contract_address
​string

One or more comma-separated contract addresses.
network_id
​string

One or more CoinMarketCap cryptocurrency network ids
network_slug
​string

Alternatively, one network names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens).
aux
​string

Default:"" Valid values: "pool_created" "percent_pooled_base_asset" "num_transactions_24h" "pool_base_asset" "pool_quote_asset" "24h_volume_quote_asset" "total_supply_quote_asset" "total_supply_base_asset" "holders" "buy_tax" "sell_tax" "security_scan" "24h_no_of_buys" "24h_no_of_sells" "24h_buy_volume" "24h_sell_volume" Optionally specify a comma-separated list of supplemental data fields to return.
convert_id
​string

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
skip_invalid
​string

Pass true to relax request validation rules. When requesting records on multiple spot pairs an error is returned if no match is found for 1 or more requested spot pairs. If set to true, invalid lookups will be skipped allowing valid spot pairs to still be returned.
reverse_order
​string

Pass true to invert the order of a spot pair. For example, a trading pair is set up as Token B/Token A in the contract and is commonly referred to as Token A/Token B. Using reverse_order would change the order to reflect the true Token B/Token A pairing as it exists in the pool.
OHLCV Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
OHLCV Latest › Responses
200

OK
​DexPairsOhlcvDTO[]
DexPairsOhlcvDTO
​DexOhlcvQuote[]

A map of market quotes in different currency conversions. The default map included is USD.
contract_address
​string

The unique contract address for this spot pair.
name
​string

The name of this spot pair.
base_asset_id
​string

The id of this base asset in the spot pair.
base_asset_ucid
​string

The ucid of this base asset in the spot pair.
base_asset_name
​string

The name of this base asset in the spot pair.
base_asset_symbol
​string

The symbol of this base asset in the spot pair.
base_asset_contract_address
​string

The contract addres of this base asset in the spot pair.
quote_asset_id
​string

The id of this quote asset in the spot pair.
quote_asset_ucid
​string

The ucid of this quote asset in the spot pair.
quote_asset_name
​string

The name of this quote asset in the spot pair.
quote_asset_symbol
​string

The symbol of this quote asset in the spot pair.
quote_asset_contract_address
​string

The contract addresss of this quote asset in the spot pair.
dex_id
​string

The id of this dex the spot pair is on.
dex_slug
​string

The name of this dex the spot pair is on.
network_id
​string

The id of the network the spot pair is on.
network_slug
​string

The slug of the network the spot pair is on.
last_updated
​string · date-time

Timestamp (ISO 8601) of the last time this record was updated.
created_at
​string · date-time

Timestamp (ISO 8601) when we started tracking this asset.
num_transactions_24h
​integer · int64

Number of transactions in past 24 hours
holders
​integer · int64

Number of holders of the asset
24h_no_of_buys
​integer · int64

Number of asset buys in the past 24 hours
24h_no_of_sells
​integer · int64

Number of asset sells in the past 24 hours
pool_created
​string · date-time

When the pool of the asset was created
buy_tax
​number · bigdecimal

Buy tax on the asset
sell_tax
​number · bigdecimal

Sell tax on the asset
​SecurityScanResult[]

Security scan by Go+.

All infomation and data relating to contract detection are based on public third party information. CoinMarketCap does not confirm or verify the accuracy or timeliness of such information and data.

CoinMarketCap shall have no responsibility or liability for the accuracy of data, nor have the duty to review, confirm, verify or otherwise perform any inquiry or investigation as to the completeness, accuracy, sufficiency, integrity, reliability or timeliness of any such information or data provided.

Only returned if passed in aux.
pool_base_asset
​number · bigdecimal

Base asset in the pool
pool_quote_asset
​number · bigdecimal

Quote asset in the pool
percent_pooled_base_asset
​number · bigdecimal

Percentage of the base asset in the pool
24h_volume_quote_asset
​number · bigdecimal

24 hours volume of the quote asset
total_supply_quote_asset
​number · bigdecimal

Total supply of the quote asset
total_supply_base_asset
​number · bigdecimal

Total supply of the quote asset
date_launched
​string · date-time

Timestamp (ISO 8601) of the launch date for this exchange.
time_open
​string

Timestamp (ISO 8601) of the start of this OHLCV period.
time_close
​string

Timestamp (ISO 8601) of the end of this OHLCV period. Always null as the current day is incomplete. See last_updated for the last UTC time included in the current OHLCV calculation.
GET/v4/dex/pairs/ohlcv/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v4/dex/pairs/ohlcv/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
[
  {
    "quote": [
      {
        "open": 0,
        "high": 0,
        "low": 0,
        "close": 0,
        "volume": 0,
        "convert_id": "convert_id",
        "last_updated": "last_updated",
        "24h_buy_volume": 0,
        "24h_sell_volume": 0
      }
    ],
    "contract_address": "contract_address",
    "name": "name",
    "base_asset_id": "base_asset_id",
    "base_asset_ucid": "base_asset_ucid",
    "base_asset_name": "base_asset_name",
    "base_asset_symbol": "base_asset_symbol",
    "base_asset_contract_address": "base_asset_contract_address",
    "quote_asset_id": "quote_asset_id",
    "quote_asset_ucid": "quote_asset_ucid",
    "quote_asset_name": "quote_asset_name",
    "quote_asset_symbol": "quote_asset_symbol",
    "quote_asset_contract_address": "quote_asset_contract_address",
    "dex_id": "dex_id",
    "dex_slug": "dex_slug",
    "network_id": "network_id",
    "network_slug": "network_slug",
    "last_updated": "2024-08-25T15:00:00Z",
    "created_at": "2024-08-25T15:00:00Z",
    "num_transactions_24h": 0,
    "holders": 0,
    "24h_no_of_buys": 0,
    "24h_no_of_sells": 0,
    "pool_created": "2024-08-25T15:00:00Z",
    "buy_tax": 0,
    "sell_tax": 0,
    "security_scan": [
      {
        "third_party": {
          "open_source": true,
          "proxy": true,
          "mintable": true,
          "can_take_back_ownership": true,
          "owner_change_balance": true,
          "hidden_owner": true,
          "self_destruct": true,
          "external_call": true,
          "cannot_buy": true,
          "cannot_sell_all": true,
          "slippage_modifiable": true,
          "honeypot": true,
          "transfer_pausable": true,
          "blacklisted": true,
          "whitelisted": true,
          "in_dex": true,
          "anti_whale": true,
          "anti_whale_modifiable": true,
          "trading_cool_down": true,
          "personal_slippage_modifiable": true,
          "trust_list": true,
          "true_token": true,
          "airdrop_scam": true
        },
        "aggregated": {
          "contract_verified": true,
          "honeypot": true
        }
      }
    ],
    "pool_base_asset": 0,
    "pool_quote_asset": 0,
    "percent_pooled_base_asset": 0,
    "24h_volume_quote_asset": 0,
    "total_supply_quote_asset": 0,
    "total_supply_base_asset": 0,
    "date_launched": "2024-08-25T15:00:00Z",
    "time_open": "time_open",
    "time_close": "time_close"
  }
]
json
application/json
OHLCV Historical
GET
https://pro-api.coinmarketcap.com
/v4/dex/pairs/ohlcv/historical

Returns historical OHLCV (Open, High, Low, Close, Volume) data along with market cap for any spot pairs using time interval parameters.
OHLCV Historical › query Parameters
contract_address
​string

One contract address. Example:"0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640". If network/dex/base asset/quote asset information is passed, contract address cannot be passed. Note: contract_address is case sensitive for all non-EVM chains and not case sensitive for all EVM chains. EVM chains contract address addresses begin with 0x, and are followed by 40 alphanumeric characters(numerals and letters)
network_id
​string

One or more CoinMarketCap cryptocurrency network ids
network_slug
​string

Alternatively, one network names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens).
time_period
​string

Default:"daily" Valid values: "daily" "hourly" "1m" "5m" "15m" "4h" Time period to return OHLCV data for. If hourly, the open will be 01:00 and the close will be 01:59. If daily, the open will be 00:00:00 for the day and close will be 23:59:99 for the same day. See the main endpoint description for details.
Default: daily
time_start
​string

Timestamp (Unix or ISO 8601) to start returning OHLCV time periods for. Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time.
time_end
​string

Timestamp (Unix or ISO 8601) to stop returning OHLCV time periods for (inclusive). Optional, if not passed we'll default to the current time. Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time.
count
​string

Optionally limit the number of time periods to return results for. The default is 10 items. The current query limit is 500 items.
Default: 10
interval
​string

Default:"daily" Valid values: "1m" "5m" "15m" "30m" "1h" "4h" "8h" "12h" "daily" "weekly" "monthly" Optionally adjust the interval that "time_period" is sampled. For example with interval=monthly&time_period=daily you will see a daily OHLCV record for January, February, March and so on. See main endpoint description for available options.
Default: daily
aux
​string

Default:"" Valid values: "pool_created" "percent_pooled_base_asset" "num_transactions_24h" "pool_base_asset" "pool_quote_asset" "24h_volume_quote_asset" "total_supply_quote_asset" "total_supply_base_asset" "holders" "buy_tax" "sell_tax" "security_scan" "24h_no_of_buys" "24h_no_of_sells" "24h_buy_volume" "24h_sell_volume" Optionally specify a comma-separated list of supplemental data fields to return.
convert_id
​string

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
skip_invalid
​string

Pass true to relax request validation rules. When requesting records on multiple spot pairs an error is returned if no match is found for 1 or more requested spot pairs. If set to true, invalid lookups will be skipped allowing valid spot pairs to still be returned.
reverse_order
​string

Pass true to invert the order of a spot pair. For example, a trading pair is set up as Token B/Token A in the contract and is commonly referred to as Token A/Token B. Using reverse_order would change the order to reflect the true Token B/Token A pairing as it exists in the pool.
OHLCV Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
OHLCV Historical › Responses
200

OK
​DexPairsOhlcvHistoricalDTO[]
DEX pairs OHLCV historical data
DexPairsOhlcvHistoricalDTO
​DexPairsOhlcvHistoricalQuotes[]

Collection of historical OHLCV quotes for the DEX pair
contract_address
​string

The unique contract address for this spot pair.
name
​string

The name of this spot pair.
base_asset_id
​string

The id of this base asset in the spot pair.
base_asset_ucid
​string

The ucid of this base asset in the spot pair.
base_asset_name
​string

The name of this base asset in the spot pair.
base_asset_symbol
​string

The symbol of this base asset in the spot pair.
base_asset_contract_address
​string

The contract addres of this base asset in the spot pair.
quote_asset_id
​string

The id of this quote asset in the spot pair.
quote_asset_ucid
​string

The ucid of this quote asset in the spot pair.
quote_asset_name
​string

The name of this quote asset in the spot pair.
quote_asset_symbol
​string

The symbol of this quote asset in the spot pair.
quote_asset_contract_address
​string

The contract addresss of this quote asset in the spot pair.
dex_id
​string

The id of this dex the spot pair is on.
dex_slug
​string

The name of this dex the spot pair is on.
network_id
​string

The id of the network the spot pair is on.
network_slug
​string

The slug of the network the spot pair is on.
last_updated
​string · date-time

Timestamp (ISO 8601) of the last time this record was updated.
created_at
​string · date-time

Timestamp (ISO 8601) when we started tracking this asset.
num_transactions_24h
​integer · int64

Number of transactions in past 24 hours
holders
​integer · int64

Number of holders of the asset
24h_no_of_buys
​integer · int64

Number of asset buys in the past 24 hours
24h_no_of_sells
​integer · int64

Number of asset sells in the past 24 hours
pool_created
​string · date-time

When the pool of the asset was created
buy_tax
​number · bigdecimal

Buy tax on the asset
sell_tax
​number · bigdecimal

Sell tax on the asset
​SecurityScanResult[]

Security scan by Go+.

All infomation and data relating to contract detection are based on public third party information. CoinMarketCap does not confirm or verify the accuracy or timeliness of such information and data.

CoinMarketCap shall have no responsibility or liability for the accuracy of data, nor have the duty to review, confirm, verify or otherwise perform any inquiry or investigation as to the completeness, accuracy, sufficiency, integrity, reliability or timeliness of any such information or data provided.

Only returned if passed in aux.
pool_base_asset
​number · bigdecimal

Base asset in the pool
pool_quote_asset
​number · bigdecimal

Quote asset in the pool
percent_pooled_base_asset
​number · bigdecimal

Percentage of the base asset in the pool
24h_volume_quote_asset
​number · bigdecimal

24 hours volume of the quote asset
total_supply_quote_asset
​number · bigdecimal

Total supply of the quote asset
total_supply_base_asset
​number · bigdecimal

Total supply of the quote asset
date_launched
​string · date-time

Timestamp (ISO 8601) of the launch date for this exchange.
GET/v4/dex/pairs/ohlcv/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v4/dex/pairs/ohlcv/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
[
  {
    "quotes": [
      {
        "quote": [
          {
            "open": 0,
            "high": 0,
            "low": 0,
            "close": 0,
            "volume": 0,
            "convert_id": "convert_id",
            "last_updated": "last_updated",
            "24h_buy_volume": 0,
            "24h_sell_volume": 0
          }
        ],
        "time_open": "2024-08-25T15:00:00Z",
        "time_close": "2024-08-25T15:00:00Z"
      }
    ],
    "contract_address": "contract_address",
    "name": "name",
    "base_asset_id": "base_asset_id",
    "base_asset_ucid": "base_asset_ucid",
    "base_asset_name": "base_asset_name",
    "base_asset_symbol": "base_asset_symbol",
    "base_asset_contract_address": "base_asset_contract_address",
    "quote_asset_id": "quote_asset_id",
    "quote_asset_ucid": "quote_asset_ucid",
    "quote_asset_name": "quote_asset_name",
    "quote_asset_symbol": "quote_asset_symbol",
    "quote_asset_contract_address": "quote_asset_contract_address",
    "dex_id": "dex_id",
    "dex_slug": "dex_slug",
    "network_id": "network_id",
    "network_slug": "network_slug",
    "last_updated": "2024-08-25T15:00:00Z",
    "created_at": "2024-08-25T15:00:00Z",
    "num_transactions_24h": 0,
    "holders": 0,
    "24h_no_of_buys": 0,
    "24h_no_of_sells": 0,
    "pool_created": "2024-08-25T15:00:00Z",
    "buy_tax": 0,
    "sell_tax": 0,
    "security_scan": [
      {
        "third_party": {
          "open_source": true,
          "proxy": true,
          "mintable": true,
          "can_take_back_ownership": true,
          "owner_change_balance": true,
          "hidden_owner": true,
          "self_destruct": true,
          "external_call": true,
          "cannot_buy": true,
          "cannot_sell_all": true,
          "slippage_modifiable": true,
          "honeypot": true,
          "transfer_pausable": true,
          "blacklisted": true,
          "whitelisted": true,
          "in_dex": true,
          "anti_whale": true,
          "anti_whale_modifiable": true,
          "trading_cool_down": true,
          "personal_slippage_modifiable": true,
          "trust_list": true,
          "true_token": true,
          "airdrop_scam": true
        },
        "aggregated": {
          "contract_verified": true,
          "honeypot": true
        }
      }
    ],
    "pool_base_asset": 0,
    "pool_quote_asset": 0,
    "percent_pooled_base_asset": 0,
    "24h_volume_quote_asset": 0,
    "total_supply_quote_asset": 0,
    "total_supply_base_asset": 0,
    "date_launched": "2024-08-25T15:00:00Z"
  }
]
json
application/json
CoinMarketCap ID Map
GET
https://pro-api.coinmarketcap.com
/v4/dex/networks/list

Returns a list of all networks to unique CoinMarketCap ids.Per our Best Practices we recommend utilizing CMC ID instead of network symbols to securely identify networks with our other endpoints and in your own application logic. Each network returned includes typical identifiers such as name, symbol, and token_address for flexible mapping to id.
CoinMarketCap ID Map › query Parameters
start
​string

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​string

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 50
sort
​string

Default:"id" Valid values: "id" "name" What field to sort the list of networks by.
Default: id
sort_dir
​string

Default:"desc" Valid values: "desc" "asc" The direction in which to order networks against the specified sort.
Default: desc
aux
​string

Default:"" Valid values: "alternativeName" "cryptocurrencyId" "cryptocurrenySlug" "wrappedTokenId" "wrappedTokenSlug" "tokenExplorerUrl" "poolExplorerUrl" "transactionHashUrl" Optionally specify a comma-separated list of supplemental data fields to return.
CoinMarketCap ID Map › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CoinMarketCap ID Map › Responses
200

OK
​NetworkInfoDTO[]
NetworkInfoDTO
id
​integer · int32

The unique CoinMarketCap ID for this network.
name
​string

The name of this network.
alternativeName
​string

The alternate name for this network.
cryptocurrencyId
​string

The unique CoinMarketCap identifier for the cryptocurrency associated with this network.
cryptocurrencySlug
​string

The slug(URL-friendly name) for the associated cryptocurrency
wrappedTokenId
​string

The unique identifier for the wrapped token on this network.
wrappedTokenSlug
​string

The slug(URL-friendly name) for the wrapped token on this network.
tokenExplorerUrl
​string

The URL for exploring tokens on this network.
poolExplorerUrl
​string

The URL for exploring liquidity pools on this network.
transactionHashUrl
​string

The URL for exploring transaction hashes on this network.
network_slug
​string

The slug of the network the spot pair is on.
GET/v4/dex/networks/list
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v4/dex/networks/list \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
[
  {
    "id": 0,
    "name": "name",
    "alternativeName": "alternativeName",
    "cryptocurrencyId": "cryptocurrencyId",
    "cryptocurrencySlug": "cryptocurrencySlug",
    "wrappedTokenId": "wrappedTokenId",
    "wrappedTokenSlug": "wrappedTokenSlug",
    "tokenExplorerUrl": "tokenExplorerUrl",
    "poolExplorerUrl": "poolExplorerUrl",
    "transactionHashUrl": "transactionHashUrl",
    "network_slug": "network_slug"
  }
]
json
application/json
DEX Listings Latest
GET
https://pro-api.coinmarketcap.com
/v4/dex/listings/quotes

Returns a paginated list of all decentralised cryptocurrency exchanges including the latest aggregate market data for each exchange. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.
DEX Listings Latest › query Parameters
start
​string

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​string

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 50
sort
​string

Default:"volume_24h" Valid values: "name" "volume_24h" "market_share" "num_markets" What field to sort the list of exchanges by.
Default: volume_24h
sort_dir
​string

Default:"desc" Valid values: "desc" "asc" The direction in which to order exchanges against the specified sort.
Default: desc
type
​string

Default:"all" Valid values: "all" "orderbook" "swap" "aggregator" The category for this exchange.
Default: all
aux
​string

Default:"" Valid values: "date_launched" Optionally specify a comma-separated list of supplemental data fields to return.
convert_id
​string

Optionally calculate market quotes in up to 30 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency IDs. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found in our API document. Each conversion is returned in its own "quote" object.
DEX Listings Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
DEX Listings Latest › Responses
200

OK
​DexInfoDTO[]
DexInfoDTO
id
​integer · int32

The unique CoinMarketCap ID for this exchange.
name
​string

The name of this exchange.
slug
​string

The web URL friendly shorthand version of this exchange name.
logo
​string

Link to a CoinMarketCap hosted logo png for this exchange. 64px is default size returned. Replace "64x64" in the image path with these alternative sizes: 16, 32, 64, 128, 200
status
​string

Current status of the DEX. Can be "active" or "inactive".
description
​string

A CoinMarketCap supplied brief description of this DEX pair. This field will return null if a description is not available.
notice
​string

A Markdown formatted message outlining a condition that is impacting the availability of the exchange's market data or the secure use of the exchange, otherwise null. This may include a maintenance event on the exchange's end or CoinMarketCap's end, an alert about reported issues with withdrawls from this exchange, or another condition that may be impacting the exchange and it's markets. If present, this notice is also displayed in an alert banner at the top of the exchange's page on coinmarketcap.com.
​DexUrls

An object containing various resource URLs for this exchange.
type
​string

The type of DEX this exchange is, such as, Orderbook, Swap, and Aggregator.
​DexInfoQuote[]

A map of market quotes in different currency conversions. The default map included is USD.
date_launched
​string · date-time

Timestamp (ISO 8601) of the date this exchange launched. This field is only returned if requested through the aux request parameter.
num_market_pairs
​string

The number of trading pairs actively tracked on this exchange.
last_updated
​string

Timestamp (ISO 8601) of the last time this record was updated.
market_share
​number · bigdecimal

Percentage of DEX market share based on volume.
GET/v4/dex/listings/quotes
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v4/dex/listings/quotes \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
[
  {
    "id": 0,
    "name": "name",
    "slug": "slug",
    "logo": "logo",
    "status": "status",
    "description": "description",
    "notice": "notice",
    "urls": {
      "website": [
        "string"
      ],
      "blog": [
        "string"
      ],
      "chat": [
        "string"
      ],
      "fee": [
        "string"
      ],
      "twitter": [
        "string"
      ]
    },
    "type": "type",
    "quote": [
      {
        "convert_id": "convert_id",
        "market_type": "market_type",
        "last_updated": "2024-08-25T15:00:00Z",
        "volume_24h": 0,
        "percent_change_volume_24h": 0,
        "num_transactions_24h": 0
      }
    ],
    "date_launched": "2024-08-25T15:00:00Z",
    "num_market_pairs": "num_market_pairs",
    "last_updated": "last_updated",
    "market_share": 0
  }
]
json
application/json
DEX Metadata
GET
https://pro-api.coinmarketcap.com
/v4/dex/listings/info

Returns all static metadata for one or more decentralised exchanges. This information includes details like launch date, logo, official website URL, social links, and market fee documentation URL.
DEX Metadata › query Parameters
id
​string

One or more comma-separated CoinMarketCap cryptocurrency exchange ids.
aux
​string

Default:"" Valid values: "urls" "logo" "description" "date_launched" "notice" Optionally specify a comma-separated list of supplemental data fields to return.
Default:
DEX Metadata › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
DEX Metadata › Responses
200

OK
​DexCommonInfoDTO[]
DexCommonInfoDTO
id
​integer · int32

The unique CoinMarketCap ID for this exchange.
name
​string

The name of this exchange.
slug
​string

The web URL friendly shorthand version of this exchange name.
logo
​string

Link to a CoinMarketCap hosted logo png for this exchange. 64px is default size returned. Replace "64x64" in the image path with these alternative sizes: 16, 32, 64, 128, 200
status
​string

Current status of the DEX. Can be "active" or "inactive".
description
​string

A CoinMarketCap supplied brief description of this DEX pair. This field will return null if a description is not available.
notice
​string

A Markdown formatted message outlining a condition that is impacting the availability of the exchange's market data or the secure use of the exchange, otherwise null. This may include a maintenance event on the exchange's end or CoinMarketCap's end, an alert about reported issues with withdrawls from this exchange, or another condition that may be impacting the exchange and it's markets. If present, this notice is also displayed in an alert banner at the top of the exchange's page on coinmarketcap.com.
​DexUrls

An object containing various resource URLs for this exchange.
date_launched
​string · date-time

Timestamp (ISO 8601) of the date this exchange launched. This field is only returned if requested through the aux request parameter.
GET/v4/dex/listings/info
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v4/dex/listings/info \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
[
  {
    "id": 0,
    "name": "name",
    "slug": "slug",
    "logo": "logo",
    "status": "status",
    "description": "description",
    "notice": "notice",
    "urls": {
      "website": [
        "string"
      ],
      "blog": [
        "string"
      ],
      "chat": [
        "string"
      ],
      "fee": [
        "string"
      ],
      "twitter": [
        "string"
      ]
    },
    "date_launched": "2024-08-25T15:00:00Z"
  }
]
json
application/json
