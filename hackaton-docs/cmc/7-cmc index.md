CMC Index
CoinMarketCap market indices. This category includes 4 endpoints:

    /v3/index/cmc100-latest - CoinMarketCap 100 Index Latest
    /v3/index/cmc100-historical - CoinMarketCap 100 Index Historical
    /v3/index/cmc20-latest - CoinMarketCap 20 Index Latest
    /v3/index/cmc20-historical - CoinMarketCap 20 Index Historical

CoinMarketCap 100 Index Historical
GET
https://pro-api.coinmarketcap.com
/v3/index/cmc100-historical

Returns an interval of historic CoinMarketCap 100 Index values based on the interval parameter.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 API call credit per request no matter query size.
CMC equivalent pages: Our CoinMarketCap 100 Index on https://coinmarketcap.com/charts/cmc100/.
CoinMarketCap 100 Index Historical › query Parameters
time_start
​string

Timestamp (Unix or ISO 8601) to start returning CoinMarketCap 100 Index data for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end".
time_end
​string

Timestamp (Unix or ISO 8601) to stop returning CoinMarketCap 100 Index data for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time.
count
​string

The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 5 items. If "time_start" and "time_end" are supplied, the query limit is 10 and the count starts from "time_start".
interval
​string

Optionally adjust the interval of data returned.Valid values:"5m","15m","daily".
CoinMarketCap 100 Index Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CoinMarketCap 100 Index Historical › Responses

Succeeded response
ApiResponseOfIndexHistoricalResponseDTO
​IndexHistoricalDTO[]
​ProApiResponseStatus
GET/v3/index/cmc100-historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v3/index/cmc100-historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "constituents": [
        {
          "id": 0,
          "name": "name",
          "symbol": "symbol",
          "url": "url",
          "weight": 0
        }
      ],
      "update_time": "update_time",
      "value": 0
    }
  ],
  "status": {
    "credit_count": 0,
    "elapsed": 0,
    "error_code": "error_code",
    "error_message": "error_message",
    "notice": "notice",
    "timestamp": "2024-08-25T15:00:00Z",
    "total_count": 0
  }
}
json
application/json
CoinMarketCap 100 Index Latest
GET
https://pro-api.coinmarketcap.com
/v3/index/cmc100-latest

Returns the lastest CoinMarketCap 100 Index value, constituents, and constituent weights.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 call credit per API call.
CMC equivalent pages: Our CoinMarketCap 100 Index on https://coinmarketcap.com/charts/cmc100/.
CoinMarketCap 100 Index Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CoinMarketCap 100 Index Latest › Responses

Succeeded response
ApiResponseOfIndexLatestResponseDTO
​IndexLatestDTO · required

The latest CoinMarketCap 100 Index value is returned in this object.
​ProApiResponseStatus
GET/v3/index/cmc100-latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v3/index/cmc100-latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "constituents": [
      {
        "id": 0,
        "name": "name",
        "symbol": "symbol",
        "url": "url",
        "weight": 0
      }
    ],
    "last_update": "2024-08-25",
    "next_update": "next_update",
    "value": 0,
    "value_24h_percentage_change": 0
  },
  "status": {
    "credit_count": 0,
    "elapsed": 0,
    "error_code": "error_code",
    "error_message": "error_message",
    "notice": "notice",
    "timestamp": "2024-08-25T15:00:00Z",
    "total_count": 0
  }
}
json
application/json
CoinMarketCap 20 Index Historical
GET
https://pro-api.coinmarketcap.com
/v3/index/cmc20-historical

Returns an interval of historic CoinMarketCap 20 Index values based on the interval parameter.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 API call credit per request no matter query size.
CMC equivalent pages: Our CoinMarketCap 20 Index on https://coinmarketcap.com/charts/cmc20/.
CoinMarketCap 20 Index Historical › query Parameters
time_start
​string

Timestamp (Unix or ISO 8601) to start returning CoinMarketCap 20 Index data for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end".
time_end
​string

Timestamp (Unix or ISO 8601) to stop returning CoinMarketCap 20 Index data for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time.
count
​string

The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 5 items. If "time_start" and "time_end" are supplied, the query limit is 10 and the count starts from "time_start".
interval
​string

Optionally adjust the interval of data returned.Valid values:"5m","15m","daily".
CoinMarketCap 20 Index Historical › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CoinMarketCap 20 Index Historical › Responses

Succeeded response
ApiResponseOfCMC20IndexHistoricalResponseDTO
​CMC20IndexHistoricalDTO[]
​ProApiResponseStatus
GET/v3/index/cmc20-historical
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v3/index/cmc20-historical \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "constituents": [
        {
          "id": 0,
          "name": "name",
          "symbol": "symbol",
          "url": "url",
          "weight": 0,
          "priceUsd": 0,
          "units": 0
        }
      ],
      "update_time": "update_time",
      "value": 0
    }
  ],
  "status": {
    "credit_count": 0,
    "elapsed": 0,
    "error_code": "error_code",
    "error_message": "error_message",
    "notice": "notice",
    "timestamp": "2024-08-25T15:00:00Z",
    "total_count": 0
  }
}
json
application/json
CoinMarketCap 20 Index Latest
GET
https://pro-api.coinmarketcap.com
/v3/index/cmc20-latest

Returns the lastest CoinMarketCap 20 Index value, constituents, and constituent weights.

This endpoint is available on the following API plans:

    Basic
    Startup
    Hobbyist
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 5 minutes.
Plan credit use: 1 call credit per API call.
CMC equivalent pages: Our CoinMarketCap 20 Index on https://coinmarketcap.com/charts/cmc20/.
CoinMarketCap 20 Index Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
CoinMarketCap 20 Index Latest › Responses

Succeeded response
ApiResponseOfCMC20IndexLatestResponseDTO
​CMC20IndexLatestDTO · required

The latest CoinMarketCap 20 Index value is returned in this object.
​ProApiResponseStatus
GET/v3/index/cmc20-latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v3/index/cmc20-latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "constituents": [
      {
        "id": 0,
        "name": "name",
        "symbol": "symbol",
        "url": "url",
        "weight": 0,
        "priceUsd": 0,
        "units": 0
      }
    ],
    "last_update": "2024-08-25",
    "next_update": "next_update",
    "value": 0,
    "value_24h_percentage_change": 0
  },
  "status": {
    "credit_count": 0,
    "elapsed": 0,
    "error_code": "error_code",
    "error_message": "error_message",
    "notice": "notice",
    "timestamp": "2024-08-25T15:00:00Z",
    "total_count": 0
  }
}
json
application/json
