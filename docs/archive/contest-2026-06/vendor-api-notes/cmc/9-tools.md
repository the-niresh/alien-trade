Tools
Utility endpoints. This category includes 4 endpoints:

    /v2/tools/price-conversion - Price Conversion v2
    /v1/fiat/map - CoinMarketCap ID Map (Fiat)
    /v1/key/info - Key Info
    /v1/tools/postman - Postman Conversion v1

Fiat ID Map
GET
https://pro-api.coinmarketcap.com
/v1/fiat/map

Returns a mapping of all supported fiat currencies to unique CoinMarketCap ids. Per our Best Practices we recommend utilizing CMC ID instead of currency symbols to securely identify assets with our other endpoints and in your own application logic.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Mapping data is updated only as needed, every 30 seconds.
Plan credit use: 1 API call credit per request no matter query size.
CMC equivalent pages: No equivalent, this data is only available via API.
Fiat ID Map › query Parameters
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 5000

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
sort
​string · enum

What field to sort the list by.
Enum values:
name
id
Default: id
include_metals
​boolean

Pass true to include precious metals.
Default: false
Fiat ID Map › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Fiat ID Map › Responses

Successful
Fiat_Map_-_Response_Model
​Fiat_Map_-_Fiat_Object[] · required

Array of fiat object results.
​API_Status_Object

Standardized status object for API calls.
GET/v1/fiat/map
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/fiat/map \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "id": 2781,
      "name": "United States Dollar",
      "sign": "$",
      "symbol": "USD"
    },
    {
      "id": 2787,
      "name": "Chinese Yuan",
      "sign": "¥",
      "symbol": "CNY"
    },
    {
      "id": 2781,
      "name": "South Korean Won",
      "sign": "₩",
      "symbol": "KRW"
    }
  ],
  "status": {
    "timestamp": "2020-01-07T22:51:28.209Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 3,
    "credit_count": 1
  }
}
json
application/json
Key Info
GET
https://pro-api.coinmarketcap.com
/v1/key/info

Returns API key details and usage stats. This endpoint can be used to programmatically monitor your key usage compared to the rate limit and daily/monthly credit limits available to your API plan. You may use the Developer Portal's account dashboard as an alternative to this endpoint.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: No cache, this endpoint updates as requests are made with your key.
Plan credit use: No API credit cost. Requests to this endpoint do contribute to your minute based rate limit however.
CMC equivalent pages: Our Developer Portal dashboard for your API Key at pro.coinmarketcap.com/account.
Key Info › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Key Info › Responses

Successful
Account_Info_-_Response_Model
​Account_Info_-_Response_Object · required

Details about your API key are returned in this object.
​API_Status_Object

Standardized status object for API calls.
GET/v1/key/info
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/key/info \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "plan": {
      "credit_limit_monthly": 120000,
      "credit_limit_monthly_reset": "In 3 days, 19 hours, 56 minutes",
      "credit_limit_monthly_reset_timestamp": "2019-09-01T00:00:00.000Z",
      "rate_limit_minute": 60
    },
    "usage": {
      "current_minute": {
        "requests_made": 1,
        "requests_left": 59
      },
      "current_day": {
        "credits_used": 1,
        "credits_left": 3999
      },
      "current_month": {
        "credits_used": 1,
        "credits_left": 119999
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
Postman Conversion v1
GET
https://pro-api.coinmarketcap.com
/v1/tools/postman

Convert APIs into postman format. You can reference the operation from this article.

This endpoint is available on the following API plans:

    Free
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Technical Notes

    Set the env variables in the postman: {{baseUrl}}, {{API_KEY}}

Postman Conversion v1 › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Postman Conversion v1 › Responses

Bad Request
Bad Request
HTTP_Status_400_Error_Object
​status
GET/v1/tools/postman
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/tools/postman \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "status": {
    "timestamp": "2018-06-02T22:51:28.209Z",
    "error_code": 400,
    "error_message": "Invalid value for \\\"id\\\"",
    "elapsed": 10,
    "credit_count": 0
  }
}
json
application/json
Price Conversion v2
GET
https://pro-api.coinmarketcap.com
/v2/tools/price-conversion

Convert an amount of one cryptocurrency or fiat currency into one or more different currencies utilizing the latest market rate for each currency. You may optionally pass a historical timestamp as time to convert values based on historical rates (as your API plan supports).

Please note: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found the deprecated section.

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
Price Conversion v2 › query Parameters
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
Price Conversion v2 › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Price Conversion v2 › Responses

Successful
Tools_Price_Conversion_-_Response_Model
​Tools_Price_Conversion_-_Results_Object · required

Results object for your API call.
​API_Status_Object

Standardized status object for API calls.
GET/v2/tools/price-conversion
curl --request GET \
  --url 'https://pro-api.coinmarketcap.com/v2/tools/price-conversion?amount=%3Cnumber%3E' \
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
