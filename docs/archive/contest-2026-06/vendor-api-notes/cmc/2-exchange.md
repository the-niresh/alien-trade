Exchange
Endpoints for cryptocurrency exchanges. This category includes 7 endpoints:

    /v1/exchange/map - CoinMarketCap ID Map
    /v1/exchange/info - Metadata
    /v1/exchange/listings/latest - Exchange Listings Latest
    /v1/exchange/quotes/latest - Quotes Latest
    /v1/exchange/quotes/historical - Quotes Historical
    /v1/exchange/market-pairs/latest - Market Pairs Latest
    /v1/exchange/assets - Exchange Assets

Exchange Assets
GET
https://pro-api.coinmarketcap.com
/v1/exchange/assets

Returns the exchange assets in the form of token holdings. This information includes details like wallet address, cryptocurrency, blockchain platform, balance, and etc.

    Only wallets containing at least 100,000 USD in balance are shown
    Balances from wallets might be delayed

** Disclaimer: All information and data relating to the holdings in the third-party wallet addresses are provided by the third parties to CoinMarketCap, and CoinMarketCap does not confirm or verify the accuracy or timeliness of such information and data. The information and data are provided "as is" without warranty of any kind. CoinMarketCap shall have no responsibility or liability for these third parties’ information and data or have the duty to review, confirm, verify or otherwise perform any inquiry or investigation as to the completeness, accuracy, sufficiency, integrity, reliability or timeliness of any such information or data provided.

This endpoint is available on the following API plans:

    Free
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Balance data is updated statically based on the source. Price data is updated every 5 minutes.
Plan credit use: 1 credit.
CMC equivalent pages: Exchange detail page like coinmarketcap.com/exchanges/binance/
Exchange Assets › query Parameters
id
​string · pattern: ^\d*$

A CoinMarketCap exchange ID. Example: 270
Exchange Assets › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Exchange Assets › Responses

Successful
Exchange_Assets_-_Response_Model
​Exchange_Assets_Wallets_-_Response_Model[]
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/assets
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/assets \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "status": {
    "timestamp": "2022-11-24T08:23:22.028Z",
    "error_code": 0,
    "error_message": null,
    "elapsed": 1828,
    "credit_count": 0,
    "notice": null
  },
  "data": [
    {
      "wallet_address": "0x5a52e96bacdabb82fd05763e25335261b270efcb",
      "balance": 45000000,
      "platform": {
        "crypto_id": 1027,
        "symbol": "ETH",
        "name": "Ethereum"
      },
      "currency": {
        "crypto_id": 5117,
        "price_usd": 0.10241799413549,
        "symbol": "OGN",
        "name": "Origin Protocol"
      }
    },
    {
      "wallet_address": "0xf977814e90da44bfa03b6295a0616a897441acec",
      "balance": 400000000,
      "platform": {
        "crypto_id": 1027,
        "symbol": "ETH",
        "name": "Ethereum"
      },
      "currency": {
        "crypto_id": 5824,
        "price_usd": 0.00251174724338,
        "symbol": "SLP",
        "name": "Smooth Love Potion"
      }
    },
    {
      "wallet_address": "0x5a52e96bacdabb82fd05763e25335261b270efcb",
      "balance": 5588175,
      "platform": {
        "crypto_id": 1027,
        "symbol": "ETH",
        "name": "Ethereum"
      },
      "currency": {
        "crypto_id": 3928,
        "price_usd": 0.04813245442357,
        "symbol": "IDEX",
        "name": "IDEX"
      }
    },
    {
      "wallet_address": "0x5a52e96bacdabb82fd05763e25335261b270efcb",
      "balance": 125000,
      "platform": {
        "crypto_id": 1027,
        "symbol": "ETH",
        "name": "Ethereum"
      },
      "currency": {
        "crypto_id": 1552,
        "price_usd": 20.46545919550142,
        "symbol": "MLN",
        "name": "Enzyme"
      }
    },
    {
      "wallet_address": "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
      "balance": 27241191.98,
      "platform": {
        "crypto_id": 1027,
        "symbol": "ETH",
        "name": "Ethereum"
      },
      "currency": {
        "crypto_id": 14806,
        "price_usd": 0.02390427295165,
        "symbol": "PEOPLE",
        "name": "ConstitutionDAO"
      }
    }
  ]
}
json
application/json
Metadata
GET
https://pro-api.coinmarketcap.com
/v1/exchange/info

Returns all static metadata for one or more exchanges. This information includes details like launch date, logo, official website URL, social links, and market fee documentation URL.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Static data is updated only as needed, every 30 seconds.
Plan credit use: 1 call credit per 100 exchanges returned (rounded up).
CMC equivalent pages: Exchange detail page metadata like coinmarketcap.com/exchanges/binance/.
Metadata › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap cryptocurrency exchange ids. Example: "1,2"
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively, one or more comma-separated exchange names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens). Example: "binance,gdax". At least one "id" or "slug" is required.
aux
​string · pattern: ^(urls|logo|descript…

Optionally specify a comma-separated list of supplemental data fields to return. Pass urls,logo,description,date_launched,notice,status to include all auxiliary fields.
Default: urls,logo,description,date_launched,notice
Metadata › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Metadata › Responses

Successful
Exchanges_Info_-_Response_Model
​Exchanges_Info_-_Results_map · required

Results of your query returned as an object map.
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/info
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/info \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 270,
      "name": "Binance",
      "slug": "binance",
      "logo": "https://s2.coinmarketcap.com/static/img/exchanges/64x64/270.png",
      "description": "Launched in Jul-2017, Binance is a centralized exchange based in Malta.",
      "date_launched": "2017-07-14T00:00:00.000Z",
      "notice": "",
      "countries": [],
      "fiats": [
        "AED",
        "USD"
      ],
      "tags": null,
      "type": "",
      "maker_fee": 0.02,
      "taker_fee": 0.04,
      "weekly_visits": 5123451,
      "spot_volume_usd": 66926283498.60113,
      "spot_volume_last_updated": "2021-05-06T01:20:15.451Z",
      "urls": {
        "website": [
          "https://www.binance.com/"
        ],
        "twitter": [
          "https://twitter.com/binance"
        ],
        "blog": [],
        "chat": [
          "https://t.me/binanceexchange"
        ],
        "fee": [
          "https://www.binance.com/fees.html"
        ]
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
CoinMarketCap ID Map
GET
https://pro-api.coinmarketcap.com
/v1/exchange/map

Returns a paginated list of all active cryptocurrency exchanges by CoinMarketCap ID. We recommend using this convenience endpoint to lookup and utilize our unique exchange id across all endpoints as typical exchange identifiers may change over time. As a convenience you may pass a comma-separated list of exchanges by slug to filter this list to only those you require or the aux parameter to slim down the payload.

By default this endpoint returns exchanges that have at least 1 actively tracked market. You may receive a map of all inactive cryptocurrencies by passing listing_status=inactive. You may also receive a map of registered exchanges that are listed but do not yet meet methodology requirements to have tracked markets available via listing_status=untracked. Please review (3) Listing Tiers in our methodology documentation for additional details on listing states.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Mapping data is updated only as needed, every 30 seconds.
Plan credit use: 1 call credit per call.
CMC equivalent pages: No equivalent, this data is only available via API.
CoinMarketCap ID Map › query Parameters
listing_status
​string · pattern: ^(active|inactive|un…

Only active exchanges are returned by default. Pass inactive to get a list of exchanges that are no longer active. Pass untracked to get a list of exchanges that are registered but do not currently meet methodology requirements to have active markets tracked. You may pass one or more comma-separated values.
Default: active
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Optionally pass a comma-separated list of exchange slugs (lowercase URL friendly shorthand name with spaces replaced with dashes) to return CoinMarketCap IDs for. If this option is passed, other options will be ignored.
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 5000

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
sort
​string · enum

What field to sort the list of exchanges by.
Enum values:
volume_24h
id
Default: id
aux
​string · pattern: ^(first_historical_d…

Optionally specify a comma-separated list of supplemental data fields to return. Pass first_historical_data,last_historical_data,is_active,status to include all auxiliary fields.
Default: first_historical_data,last_historical_data,is_active
crypto_id
​string · pattern: ^\d*$

Optionally include one fiat or cryptocurrency IDs to filter market pairs by. For example ?crypto_id=1 would only return exchanges that have BTC.
CoinMarketCap ID Map › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CoinMarketCap ID Map › Responses

Successful
Exchange_Map_-_Response_Model
​Exchange_Map_-_Exchange_Object[] · required

Array of exchange object results.
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/map
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/map \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "id": 270,
      "name": "Binance",
      "slug": "binance",
      "is_active": 1,
      "status": "active",
      "first_historical_data": "2018-04-26T00:45:00.000Z",
      "last_historical_data": "2019-06-02T21:25:00.000Z"
    }
  ],
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
Exchange Listings Latest
GET
https://pro-api.coinmarketcap.com
/v1/exchange/listings/latest

Returns a paginated list of all cryptocurrency exchanges including the latest aggregate market data for each exchange. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 1 minute. Plan credit use: 1 call credit per 100 exchanges returned (rounded up) and 1 call credit per convert option beyond the first. CMC equivalent pages: Our latest exchange listing and ranking pages like coinmarketcap.com/rankings/exchanges/.

NOTE: Use this endpoint if you need a sorted and paginated list of exchanges. If you want to query for market data on a few specific exchanges use /v1/exchange/quotes/latest which is optimized for that purpose. The response data between these endpoints is otherwise the same.

“exchange_score" will be deprecated on 4 November 2024.

After this date, the "exchange_score" field return null from these endpoints. We encourage users to review and update their implementations accordingly to avoid any disruptions.
Exchange Listings Latest › query Parameters
category
​string · enum

The category for this exchange.
Enum values:
all
spot
derivatives
dex
lending
Default: all
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 5000

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 100
sort
​string · enum

What field to sort the list of exchanges by.
Enum values:
name
volume_24h
volume_24h_adjusted
exchange_score
Default: volume_24h
sort_dir
​string · enum

The direction in which to order exchanges against the specified sort.
Enum values:
asc
desc
market_type
​string · enum

The type of exchange markets to include in rankings. This field is deprecated. Please use "all" for accurate sorting.
Enum values:
fees
no_fees
all
Default: all
aux
​string · pattern: ^(num_market_pairs|t…

Optionally specify a comma-separated list of supplemental data fields to return. Pass num_market_pairs,traffic_score,rank,exchange_score,effective_liquidity_24h,date_launched,fiats to include all auxiliary fields.
Default: num_market_pairs,traffic_score,rank,exchange_score,effective_liquidity_24h
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Exchange Listings Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Exchange Listings Latest › Responses

Successful
Exchange_Listings_Latest_-_Response_Model
​Exchange_Listings_Latest_-_Exchange_object[] · required

Array of exchange objects matching the list options.
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/listings/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/listings/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "id": 270,
      "name": "Binance",
      "slug": "binance",
      "num_market_pairs": 1214,
      "fiats": [
        "AED",
        "USD"
      ],
      "traffic_score": 1000,
      "rank": 1,
      "exchange_score": 9.8,
      "liquidity_score": 9.8028,
      "last_updated": "2018-11-08T22:18:00.000Z",
      "quote": {
        "USD": {
          "volume_24h": 769291636.239632,
          "volume_24h_adjusted": 769291636.239632,
          "volume_7d": 3666423776,
          "volume_30d": 21338299776,
          "percent_change_volume_24h": -11.6153,
          "percent_change_volume_7d": 67.2055,
          "percent_change_volume_30d": 0.00169339,
          "effective_liquidity_24h": 629.9774,
          "derivative_volume_usd": 62828618628.85901,
          "spot_volume_usd": 39682580614.8572,
          "last_updated": "2018-11-08T22:18:00.000Z"
        }
      }
    },
    {
      "id": 294,
      "name": "OKEx",
      "slug": "okex",
      "num_market_pairs": 385,
      "fiats": [
        "AED",
        "USD"
      ],
      "traffic_score": 845.1565,
      "rank": 1,
      "exchange_score": 8.5,
      "liquidity_score": 9.8028,
      "last_updated": "2018-11-08T22:18:00.000Z",
      "quote": {
        "USD": {
          "volume_24h": 677439315.721563,
          "volume_24h_adjusted": 677439315.721563,
          "volume_7d": 3506137120,
          "volume_30d": 14418225072,
          "percent_change_volume_24h": -13.9256,
          "percent_change_volume_7d": 60.0461,
          "percent_change_volume_30d": 67.2225,
          "effective_liquidity_24h": 629.9774,
          "derivative_volume_usd": 62828618628.85901,
          "spot_volume_usd": 39682580614.8572,
          "last_updated": "2018-11-08T22:18:00.000Z"
        }
      }
    }
  ],
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
Market Pairs Latest
GET
https://pro-api.coinmarketcap.com
/v1/exchange/market-pairs/latest

Returns all active market pairs that CoinMarketCap tracks for a given exchange. The latest price and volume information is returned for each market. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.'

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Plan credit use: 1 call credit per 100 market pairs returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: Our exchange level active markets pages like coinmarketcap.com/exchanges/binance/.
Market Pairs Latest › query Parameters
id
​string · pattern: ^\d*$

A CoinMarketCap exchange ID. Example: "1"
slug
​string · pattern: ^[0-9a-z-]*$

Alternatively pass an exchange "slug" (URL friendly all lowercase shorthand version of name with spaces replaced with hyphens). Example: "binance". One "id" or "slug" is required.
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 5000

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 100
aux
​string · pattern: ^(num_market_pairs|c…

Optionally specify a comma-separated list of supplemental data fields to return. Pass num_market_pairs,category,fee_type,market_url,currency_name,currency_slug,price_quote,effective_liquidity,market_score,market_reputation to include all auxiliary fields.
Default: num_market_pairs,category,fee_type
matched_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally include one or more comma-delimited fiat or cryptocurrency IDs to filter market pairs by. For example ?matched_id=2781 would only return BTC markets that matched: "BTC/USD" or "USD/BTC" for the requested exchange. This parameter cannot be used when matched_symbol is used.
matched_symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally include one or more comma-delimited fiat or cryptocurrency symbols to filter market pairs by. For example ?matched_symbol=USD would only return BTC markets that matched: "BTC/USD" or "USD/BTC" for the requested exchange. This parameter cannot be used when matched_id is used.
category
​string · enum

The category of trading this market falls under. Spot markets are the most common but options include derivatives and OTC.
Enum values:
all
spot
derivatives
otc
futures
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
Market Pairs Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Market Pairs Latest › Responses

Successful
Exchange_Market_Pairs_Latest_-_Response_Model
​Exchange_Market_Pairs_Latest_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/market-pairs/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/market-pairs/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "id": 270,
    "name": "Binance",
    "slug": "binance",
    "num_market_pairs": 473,
    "volume_24h": 769291636.239632,
    "market_pairs": [
      {
        "market_id": 9933,
        "market_pair": "BTC/USDT",
        "category": "spot",
        "fee_type": "percentage",
        "outlier_detected": 0,
        "exclusions": null,
        "market_pair_base": {
          "currency_id": 1,
          "currency_symbol": "BTC",
          "exchange_symbol": "BTC",
          "currency_type": "cryptocurrency"
        },
        "market_pair_quote": {
          "currency_id": 825,
          "currency_symbol": "USDT",
          "exchange_symbol": "USDT",
          "currency_type": "cryptocurrency"
        },
        "quote": {
          "exchange_reported": {
            "price": 7901.83,
            "volume_24h_base": 47251.3345550653,
            "volume_24h_quote": 373372012.927251,
            "volume_percentage": 19.4346563602467,
            "last_updated": "2019-05-24T01:40:10.000Z"
          },
          "USD": {
            "price": 7933.66233493434,
            "volume_24h": 374876133.234903,
            "depth_negative_two": 40654.68019906,
            "depth_positive_two": 17352.9964811,
            "last_updated": "2019-05-24T01:40:10.000Z"
          }
        }
      },
      {
        "market_id": 36329,
        "market_pair": "MATIC/BTC",
        "category": "spot",
        "fee_type": "percentage",
        "outlier_detected": 0,
        "exclusions": null,
        "market_pair_base": {
          "currency_id": 3890,
          "currency_symbol": "MATIC",
          "exchange_symbol": "MATIC",
          "currency_type": "cryptocurrency"
        },
        "market_pair_quote": {
          "currency_id": 1,
          "currency_symbol": "BTC",
          "exchange_symbol": "BTC",
          "currency_type": "cryptocurrency"
        },
        "quote": {
          "exchange_reported": {
            "price": 0.0000034,
            "volume_24h_base": 8773968381.05,
            "volume_24h_quote": 29831.49249557,
            "volume_percentage": 19.4346563602467,
            "last_updated": "2019-05-24T01:41:16.000Z"
          },
          "USD": {
            "price": 0.0269295015799739,
            "volume_24h": 236278595.380127,
            "depth_negative_two": 40654.68019906,
            "depth_positive_two": 17352.9964811,
            "last_updated": "2019-05-24T01:41:16.000Z"
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
Quotes Historical
GET
https://pro-api.coinmarketcap.com
/v1/exchange/quotes/historical

Returns an interval of historic quotes for any exchange based on time and interval parameters.

Technical Notes

    A historic quote for every "interval" period between your "time_start" and "time_end" will be returned.
    If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end".
    If "time_end" is not supplied, it defaults to the current time.
    At each "interval" period, the historic quote that is closest in time to the requested time will be returned.
    If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped.
    This endpoint supports requesting multiple exchanges in the same call. Please note the API response will be wrapped in an additional object in this case.

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
    Professional (Up to 12 months)
    Enterprise (Up to 6 years)

Note: You may use the /exchange/map endpoint to receive a list of earliest historical dates that may be fetched for each exchange as first_historical_data. This timestamp will either be the date CoinMarketCap first started tracking the exchange or 2018-04-26T00:45:00.000Z, the earliest date this type of historical data is available for.

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 call credit per 100 historical data points returned (rounded up) and 1 call credit per convert option beyond the first.
CMC equivalent pages: No equivalent, this data is only available via API outside of our volume sparkline charts in coinmarketcap.com/rankings/exchanges/.
Quotes Historical › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated exchange CoinMarketCap ids. Example: "24,270"
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively, one or more comma-separated exchange names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens). Example: "binance,kraken". At least one "id" or "slug" is required.
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
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Quotes Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Historical › Responses

Successful
Exchange_Historical_Quotes_-_Response_Model
​Exchange_Historical_Quotes_-_Results_map · required

Results of your query returned as an object map.
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/quotes/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/quotes/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 270,
      "name": "Binance",
      "slug": "binance",
      "quotes": [
        {
          "timestamp": "2018-06-03T00:00:00.000Z",
          "quote": {
            "USD": {
              "volume_24h": 1632390000,
              "timestamp": "2018-06-03T00:00:00.000Z"
            }
          },
          "num_market_pairs": 338
        },
        {
          "timestamp": "2018-06-10T00:00:00.000Z",
          "quote": {
            "USD": {
              "volume_24h": 1034720000,
              "timestamp": "2018-06-10T00:00:00.000Z"
            }
          },
          "num_market_pairs": 349
        },
        {
          "timestamp": "2018-06-17T00:00:00.000Z",
          "quote": {
            "USD": {
              "volume_24h": 883885000,
              "timestamp": "2018-06-17T00:00:00.000Z"
            }
          },
          "num_market_pairs": 357
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
Quotes Latest
GET
https://pro-api.coinmarketcap.com
/v1/exchange/quotes/latest

Returns the latest aggregate market data for 1 or more exchanges. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds. Plan credit use: 1 call credit per 100 exchanges returned (rounded up) and 1 call credit per convert option beyond the first. CMC equivalent pages: Latest market data summary for specific exchanges like coinmarketcap.com/rankings/exchanges/.

NOTE: “exchange_score" will be deprecated on 4 November 2024.

After this date, the "exchange_score" field return null from these endpoints. We encourage users to review and update their implementations accordingly to avoid any disruptions.
Quotes Latest › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated CoinMarketCap exchange IDs. Example: "1,2"
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively, pass a comma-separated list of exchange "slugs" (URL friendly all lowercase shorthand version of name with spaces replaced with hyphens). Example: "binance,gdax". At least one "id" or "slug" is required.
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
aux
​string · pattern: ^(num_market_pairs|t…

Optionally specify a comma-separated list of supplemental data fields to return. Pass num_market_pairs,traffic_score,rank,exchange_score,liquidity_score,effective_liquidity_24h to include all auxiliary fields.
Default: num_market_pairs,traffic_score,rank,exchange_score,liquidity_score,effective_liquidity_24h
Quotes Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Latest › Responses

Successful
Exchange_Quotes_Latest_-_Response_Model
​Exchange_Quotes_Latest_-_Exchange_Results_map · required

A map of exchange objects by ID or slugs (as used in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v1/exchange/quotes/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/exchange/quotes/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 270,
      "name": "Binance",
      "slug": "binance",
      "num_coins": 132,
      "num_market_pairs": 385,
      "last_updated": "2018-11-08T22:11:00.000Z",
      "traffic_score": 1000,
      "rank": 1,
      "exchange_score": 9.8,
      "liquidity_score": 9.8028,
      "quote": {
        "USD": {
          "volume_24h": 768478308.529847,
          "volume_24h_adjusted": 768478308.529847,
          "volume_7d": 3666423776,
          "volume_30d": 21338299776,
          "percent_change_volume_24h": -11.8232,
          "percent_change_volume_7d": 67.0306,
          "percent_change_volume_30d": -0.0821558,
          "effective_liquidity_24h": 629.9774,
          "last_updated": "2018-11-08T22:18:00.000Z"
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
