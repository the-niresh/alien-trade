Derivatives
Endpoints for derivatives market data (perpetuals and futures). This category includes 3 endpoints:

    /v5/exchange/derivatives/list - List derivatives exchanges
    /v5/exchange/derivatives/market-pairs/list/latest - Derivative market pairs by exchange
    /v5/cryptocurrency/derivatives/market-pairs/list/latest - Derivative market pairs by cryptocurrency

List derivatives exchanges
GET
https://pro-api.coinmarketcap.com
/v5/exchange/derivatives/list

Returns the list of derivatives exchanges CoinMarketCap tracks, sorted by 24-hour derivative volume in descending order by default. Only exchanges with active derivative trading (open interest or derivative volume > 0) are returned.

This endpoint is available on the following API plans:

    Free
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Plan credit use: 1 call credit per 100 exchanges returned (rounded up) and 1 additional call credit per convert option beyond the first.
List derivatives exchanges › query Parameters
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

Optionally specify the field used to sort the list of exchanges. Options: name, volume_24h, volume_24h_adjusted, exchange_score.
Enum values:
name
volume_24h
volume_24h_adjusted
exchange_score
Default: volume_24h
sort_dir
​string · enum

Optionally specify the sort direction. Options: asc, desc.
Enum values:
asc
desc
Default: desc
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in multiple currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own quote object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
List derivatives exchanges › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
List derivatives exchanges › Responses

Successful
Derivatives_Exchanges_List_-_Response_Model
​Derivatives_Exchanges_List_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v5/exchange/derivatives/list
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v5/exchange/derivatives/list \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "exchanges": [
      {
        "exchange_id": 270,
        "exchange_name": "Binance",
        "exchange_slug": "binance",
        "num_market_pairs": 645,
        "fiats": [],
        "traffic_score": 1000,
        "rank": 1,
        "exchange_score": 7.82345678,
        "liquidity_score": 9.8028,
        "last_updated": "2026-04-21T10:30:00.000Z",
        "quotes": [
          {
            "convert_id": 2781,
            "convert_symbol": "USD",
            "open_interest": 23306624960.78,
            "open_interest_usd": 23306624960.78,
            "derivative_volume": 62828618628.85901,
            "derivative_volume_usd": 62828618628.85901,
            "maker_fees": 0.04,
            "taker_fees": 0.04,
            "last_updated": "2026-04-21T10:30:00.000Z"
          }
        ]
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
Derivative market pairs by exchange
GET
https://pro-api.coinmarketcap.com
/v5/exchange/derivatives/market-pairs/list/latest

Returns all active derivative market pairs that CoinMarketCap tracks for a given exchange.

This endpoint is available on the following API plans:

    Free
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Derivative market pairs by exchange › query Parameters
exchange_id
​integer

A CoinMarketCap exchange ID. Example: "270"
exchange_slug
​string · pattern: ^[0-9a-z-]+$

Alternatively pass an exchange "slug" (URL friendly all lowercase shorthand version of name with spaces replaced with hyphens). Example: "binance". One "exchange_id" or "exchange_slug" is required.
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

Optionally specify the field used to sort market pairs. Options: volume_24h_strict, cmc_rank, cmc_rank_advanced, effective_liquidity.
Enum values:
volume_24h_strict
cmc_rank
cmc_rank_advanced
effective_liquidity
Default: volume_24h_strict
sort_dir
​string · enum

Optionally specify the sort direction. Options: asc, desc.
Enum values:
asc
desc
Default: desc
category
​string · enum

The derivative category of trading this market falls under. Options: all, perpetual, futures.
Enum values:
all
perpetual
futures
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
matched_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally include one or more comma-delimited fiat or cryptocurrency IDs to filter market pairs by. For example ?matched_id=2781 would only return derivative markets matched against USD for the requested exchange. This parameter cannot be used when matched_symbol is used.
matched_symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally include one or more comma-delimited fiat or cryptocurrency symbols to filter market pairs by. For example ?matched_symbol=USD would only return derivative markets matched against USD for the requested exchange. This parameter cannot be used when matched_id is used.
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in multiple currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own quote object.
Default: USD
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Derivative market pairs by exchange › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Derivative market pairs by exchange › Responses

Successful
Derivatives_Market_Pairs_List_Latest_-_Response_Model
​Derivatives_Market_Pairs_List_Latest_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v5/exchange/derivatives/market-pairs/list/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v5/exchange/derivatives/market-pairs/list/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "exchange_id": 270,
    "exchange_name": "Binance",
    "exchange_slug": "binance",
    "num_market_pairs": 2045,
    "volume_24h": 69306677552.93349,
    "market_pairs": [
      {
        "market_id": 47150,
        "market_pair": "BTC/USDT",
        "category": "perpetual",
        "fee_type": "percentage",
        "outlier_detected": false,
        "exclusions": null,
        "market_pair_base": {
          "exchange_symbol": "BTC",
          "symbol": "BTC",
          "crypto_id": 1,
          "currency_type": "cryptocurrency"
        },
        "market_pair_quote": {
          "exchange_symbol": "USDT",
          "symbol": "USDT",
          "crypto_id": 825,
          "currency_type": "cryptocurrency"
        },
        "exchange_reported_quotes": [
          {
            "crypto_id": 2781,
            "symbol": "USD",
            "price": 80521.2,
            "volume_24h_base": 184589.83976729,
            "volume_24h_quote": 14863395405.87,
            "open_interest": 5000000,
            "index_price": 80498.5,
            "index_basis": 0.0023,
            "funding_rate": 0.0001,
            "last_updated": "2026-05-15T06:54:18.743Z",
            "volume_percentage": 21.441131937316662
          }
        ],
        "quotes": [
          {
            "crypto_id": 2781,
            "symbol": "USD",
            "price": 80504.01770192,
            "volume_24h": 14860136175.4951,
            "open_interest": 5000000,
            "last_updated": "2026-05-15T06:54:18.743Z"
          }
        ]
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
Derivative market pairs by cryptocurrency
GET
https://pro-api.coinmarketcap.com
/v5/cryptocurrency/derivatives/market-pairs/list/latest

Returns all active derivative market pairs that CoinMarketCap tracks for a given cryptocurrency, across exchanges.

This endpoint is available on the following API plans:

    Free
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 60 seconds.
Derivative market pairs by cryptocurrency › query Parameters
crypto_id
​integer

A CoinMarketCap cryptocurrency ID. Example: "1"
crypto_slug
​string · pattern: ^[0-9a-z-]+$

Alternatively pass a cryptocurrency "slug" (URL friendly all lowercase shorthand version of name with spaces replaced with hyphens). Example: "bitcoin".
crypto_symbol
​string · pattern: ^[0-9A-Za-z$@\-]+$

Alternatively pass a cryptocurrency symbol. Example: "BTC". One "crypto_id", "crypto_slug", or "crypto_symbol" is required.
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

Optionally specify the sort direction. Options: asc, desc.
Enum values:
asc
desc
Default: desc
sort
​string · enum

Optionally specify the field used to sort market pairs. Options: volume_24h_strict, cmc_rank, cmc_rank_advanced, effective_liquidity.
Enum values:
volume_24h_strict
cmc_rank
cmc_rank_advanced
effective_liquidity
Default: volume_24h_strict
category
​string · enum

The derivative category of trading this market falls under. Options: all, perpetual, futures.
Enum values:
all
perpetual
futures
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
matched_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally include one or more comma-delimited fiat or cryptocurrency IDs to filter market pairs by. For example ?matched_id=2781 would only return derivative markets matched against USD for the requested exchange. This parameter cannot be used when matched_symbol is used.
matched_symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally include one or more comma-delimited fiat or cryptocurrency symbols to filter market pairs by. For example ?matched_symbol=USD would only return derivative markets matched against USD for the requested exchange. This parameter cannot be used when matched_id is used.
center_type
​string · enum

Optionally filter by exchange center type. Options: all, cex, dex.
Enum values:
all
cex
dex
Default: all
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in multiple currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own quote object.
Default: USD
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Derivative market pairs by cryptocurrency › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Derivative market pairs by cryptocurrency › Responses

Successful
Derivatives_Crypto_Market_Pairs_List_Latest_-_Response_Model
​Derivatives_Crypto_Market_Pairs_List_Latest_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v5/cryptocurrency/derivatives/market-pairs/list/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v5/cryptocurrency/derivatives/market-pairs/list/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "crypto_id": 1,
    "crypto_name": "Bitcoin",
    "symbol": "BTC",
    "num_market_pairs": 5,
    "market_pairs": [
      {
        "market_id": 79477,
        "market_pair": "BTC/USDT",
        "category": "perpetual",
        "fee_type": "percentage",
        "outlier_detected": false,
        "exclusions": null,
        "exchange": {
          "exchange_id": 270,
          "exchange_name": "Binance",
          "exchange_slug": "binance"
        },
        "market_pair_base": {
          "crypto_id": 1,
          "symbol": "BTC",
          "exchange_symbol": "BTC",
          "currency_type": "cryptocurrency"
        },
        "market_pair_quote": {
          "crypto_id": 825,
          "symbol": "USDT",
          "exchange_symbol": "USDT",
          "currency_type": "cryptocurrency"
        },
        "exchange_reported_quotes": [
          {
            "crypto_id": 2781,
            "symbol": "USD",
            "price": 80496.6,
            "volume_24h_base": 686357.90331837,
            "volume_24h_quote": 55249477600.25728,
            "open_interest": 5000000,
            "index_price": 80498.5,
            "index_basis": 0.0023,
            "funding_rate": 0.0001,
            "last_updated": "2026-05-15T06:36:15.586Z"
          }
        ],
        "quotes": [
          {
            "crypto_id": 2781,
            "symbol": "USD",
            "price": 80470.69372308,
            "volume_24h": 55231696622.35106,
            "open_interest": 5000000,
            "last_updated": "2026-05-15T06:36:15.586Z"
          }
        ]
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
