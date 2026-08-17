Global Metrics
Endpoints for global aggregate market data. This category includes 6 endpoints:

    /v1/global-metrics/quotes/latest - Quotes Latest
    /v1/global-metrics/quotes/historical - Quotes Historical
    /v3/fear-and-greed/latest - CMC Crypto Fear and Greed Latest
    /v3/fear-and-greed/historical - CMC Crypto Fear and Greed Historical
    /v1/altcoin-season-index/latest - Altcoin Season Index Latest
    /v1/altcoin-season-index/historical - Altcoin Season Index Historical

CMC Crypto Fear and Greed Historical
GET
https://pro-api.coinmarketcap.com
/v3/fear-and-greed/historical

Returns a paginated list of all CMC Crypto Fear and Greed values at 12am UTC time.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 15 seconds.
Plan credit use: 1 API call credit per request no matter query size.
CMC equivalent pages: Our CMC Crypto Fear and Greed Index card on https://coinmarketcap.com/charts/.
CMC Crypto Fear and Greed Historical › query Parameters
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 500

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 50
CMC Crypto Fear and Greed Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CMC Crypto Fear and Greed Historical › Responses

Successful
Fear_and_Greed_Historical_-_Response_Model
​Fear_and_Greed_Historical_-_Fear_and_Greed_object[] · required

Fear and Greed Historical.
​API_Status_Object

Standardized status object for API calls.
GET/v3/fear-and-greed/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "timestamp": "1726617600",
      "value": 38,
      "value_classification": "Fear"
    },
    {
      "timestamp": "1726531200",
      "value": 34,
      "value_classification": "Fear"
    },
    {
      "timestamp": "1726444800",
      "value": 36,
      "value_classification": "Fear"
    },
    {
      "timestamp": "1726358400",
      "value": 38,
      "value_classification": "Fear"
    },
    {
      "timestamp": "1726272000",
      "value": 38,
      "value_classification": "Fear"
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
CMC Crypto Fear and Greed Latest
GET
https://pro-api.coinmarketcap.com
/v3/fear-and-greed/latest

Returns the lastest CMC Crypto Fear and Greed value.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 15 minutes.
Plan credit use: 1 call credit per request.
CMC equivalent pages: Our CMC Crypto Fear and Greed Index card on https://coinmarketcap.com/charts/.
CMC Crypto Fear and Greed Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CMC Crypto Fear and Greed Latest › Responses

Successful
Fear_and_Greed_Latest_-_Response_Model
​Fear_and_Greed_Latest_-_Response_Object · required

The latest CMC Fear and Greed value.
​API_Status_Object

Standardized status object for API calls.
GET/v3/fear-and-greed/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "value": 40,
    "value_classification": "Neutral",
    "update_time": "2024-09-19T02:54:56.017Z"
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
/v1/global-metrics/quotes/historical

Returns an interval of historical global cryptocurrency market metrics based on time and interval parameters.

Technical Notes

    A historic quote for every "interval" period between your "time_start" and "time_end" will be returned.
    If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end".
    If "time_end" is not supplied, it defaults to the current time.
    At each "interval" period, the historic quote that is closest in time to the requested time will be returned.
    If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped.

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
Plan credit use: 1 call credit per 100 historical data points returned (rounded up).
CMC equivalent pages: Our Total Market Capitalization global chart coinmarketcap.com/charts/.
Quotes Historical › query Parameters
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
Default: 1d
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
aux
​string · pattern: ^(btc_dominance|eth_…

Optionally specify a comma-separated list of supplemental data fields to return. Pass btc_dominance,eth_dominance,active_cryptocurrencies,active_exchanges,active_market_pairs,total_volume_24h,total_volume_24h_reported,altcoin_market_cap,altcoin_volume_24h,altcoin_volume_24h_reported,search_interval to include all auxiliary fields.
Default: btc_dominance,eth_dominance,active_cryptocurrencies,active_exchanges,active_market_pairs,total_volume_24h,total_volume_24h_reported,altcoin_market_cap,altcoin_volume_24h,altcoin_volume_24h_reported
Quotes Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Historical › Responses

Successful
Global_Metrics_Quotes_Historic_-_Response_Model
​Global_Metrics_Quotes_Historic_-_Results_object · required

Results of your query returned as an object.
​API_Status_Object

Standardized status object for API calls.
GET/v1/global-metrics/quotes/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "quotes": [
      {
        "timestamp": "2018-07-31T00:02:00.000Z",
        "eth_dominance": 16.099,
        "btc_dominance": 47.9949,
        "active_cryptocurrencies": 2500,
        "active_exchanges": 600,
        "active_market_pairs": 1000,
        "quote": {
          "USD": {
            "total_market_cap": 292863223827.394,
            "total_volume_24h": 17692152629.7864,
            "total_volume_24h_reported": 375179000000,
            "altcoin_market_cap": 187589500000,
            "altcoin_volume_24h": 375179000000,
            "altcoin_volume_24h_reported": 375179000000,
            "timestamp": "2018-07-31T00:02:00.000Z"
          }
        }
      },
      {
        "timestamp": "2018-08-01T00:02:00.000Z",
        "eth_dominance": 16.099,
        "btc_dominance": 48.0585,
        "active_cryptocurrencies": 2500,
        "active_exchanges": 600,
        "active_market_pairs": 1000,
        "quote": {
          "USD": {
            "total_market_cap": 277770824530.303,
            "total_volume_24h": 15398085549.0344,
            "total_volume_24h_reported": 375179000000,
            "altcoin_market_cap": 187589500000,
            "altcoin_volume_24h": 375179000000,
            "altcoin_volume_24h_reported": 375179000000,
            "timestamp": "2018-07-31T00:02:00.000Z"
          }
        }
      },
      {
        "timestamp": "2018-08-02T00:02:00.000Z",
        "eth_dominance": 16.099,
        "btc_dominance": 48.041,
        "active_cryptocurrencies": 2500,
        "active_exchanges": 600,
        "active_market_pairs": 1000,
        "quote": {
          "USD": {
            "total_market_cap": 273078776005.223,
            "total_volume_24h": 14300071695.0547,
            "total_volume_24h_reported": 375179000000,
            "altcoin_market_cap": 187589500000,
            "altcoin_volume_24h": 375179000000,
            "altcoin_volume_24h_reported": 375179000000,
            "timestamp": "2018-07-31T00:02:00.000Z"
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
Quotes Latest
GET
https://pro-api.coinmarketcap.com
/v1/global-metrics/quotes/latest

Returns the latest global cryptocurrency market metrics. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 5 minute.
Plan credit use: 1 call credit per call and 1 call credit per convert option beyond the first.
CMC equivalent pages: The latest aggregate global market stats ticker across all CMC pages like coinmarketcap.com.
Quotes Latest › query Parameters
convert
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found here. Each conversion is returned in its own "quote" object.
convert_id
​string · pattern: ^\d+(?:,\d+)*$

Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to convert outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when convert is used.
Quotes Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Quotes Latest › Responses

Successful
Global_Metrics_Quotes_Latest_-_Response_Model
​Global_Metrics_Quotes_Latest_-_Results_Object · required

Results object for your API call.
​API_Status_Object

Standardized status object for API calls.
GET/v1/global-metrics/quotes/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "btc_dominance": 67.0057,
    "eth_dominance": 9.02205,
    "active_cryptocurrencies": 2941,
    "total_cryptocurrencies": 4637,
    "active_market_pairs": 21209,
    "active_exchanges": 445,
    "total_exchanges": 677,
    "last_updated": "2019-05-16T18:47:00.000Z",
    "quote": {
      "USD": {
        "total_market_cap": 250284668020.67,
        "total_volume_24h": 16903498628.86,
        "total_volume_24h_reported": 16903498628.86,
        "altcoin_volume_24h": 11883384723.14,
        "altcoin_volume_24h_reported": 11883384723.14,
        "altcoin_market_cap": 119597549931.01,
        "last_updated": "2018-06-02T23:46:14.000Z"
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
Altcoin Season Index Latest
GET
https://pro-api.coinmarketcap.com
/v1/altcoin-season-index/latest

Returns the latest Altcoin Season Index snapshot with yearly high/low statistics. Index scale 0-100; values above 75 suggest altcoin season, below 25 suggest Bitcoin season.

Cache / Update frequency: Every 15 minutes. Plan credit use: 1 API call credit per request.
Altcoin Season Index Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Altcoin Season Index Latest › Responses

Successful
Altcoin_Season_Index_Latest_-_Response_Model
​Altcoin_Season_Index_Latest_-_Response_Object · required

Altcoin Season Index latest snapshot.
​API_Status_Object

Standardized status object for API calls.
GET/v1/altcoin-season-index/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/altcoin-season-index/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "altcoin_index": 0,
    "altcoin_marketcap": 0,
    "snapshot_time": "snapshot_time",
    "yearly_high": 0,
    "yearly_high_date": "yearly_high_date",
    "yearly_low": 0,
    "yearly_low_date": "yearly_low_date"
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
Altcoin Season Index Historical
GET
https://pro-api.coinmarketcap.com
/v1/altcoin-season-index/historical

Returns historical Altcoin Season Index data for a specified timeframe (7d, 30d, or 90d). Data points are sorted by timestamp (oldest first).

Cache / Update frequency: Every 15 minutes. Plan credit use: 1 API call credit per request.
Altcoin Season Index Historical › query Parameters
timeframe
​string · enum

Timeframe for historical data. Valid values are 7d, 30d, and 90d. Default is 7d.
Enum values:
7d
30d
90d
Default: 7d
Altcoin Season Index Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Altcoin Season Index Historical › Responses

Successful
Altcoin_Season_Index_Historical_-_Response_Model
​Altcoin_Season_Index_Historical_-_Response_Object · required

Altcoin Season Index historical series for a timeframe.
​API_Status_Object

Standardized status object for API calls.
GET/v1/altcoin-season-index/historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/altcoin-season-index/historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "timeframe": "timeframe",
    "points": [
      {
        "timestamp": "timestamp",
        "altcoin_index": 0,
        "altcoin_marketcap": 0
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
