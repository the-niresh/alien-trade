Community
Endpoints for community data. This category includes 2 endpoints:

    /v1/community/trending/topic - Community Trending Topics
    /v1/community/trending/token - Community Trending Tokens

Community Trending Tokens
GET
https://pro-api.coinmarketcap.com
/v1/community/trending/token

Returns the latest trending tokens from the CMC Community.

This endpoint is available on the following API plans:

    Standard
    Professional
    Enterprise

Cache / Update frequency: One Minute Plan credit use: 0 credit
Community Trending Tokens › query Parameters
limit
​integer · min: 1 · max: 5

Optionally specify the number of results to return.
Default: 5
Community Trending Tokens › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Community Trending Tokens › Responses

Successful
Community_Trending_Token_-_Response_Model
​Community_Trending_Token_-Results-Object[] · required

Cntent objects.
GET/v1/community/trending/token
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/community/trending/token \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "id": 7102,
      "name": "Linear Finance",
      "symbol": "LINA",
      "slug": "linear",
      "cmc_rank": 461,
      "rank": 1
    },
    {
      "id": 26265,
      "name": "NiHao",
      "symbol": "NIHAO",
      "slug": "nihao",
      "cmc_rank": 5000,
      "rank": 2
    },
    {
      "id": 22538,
      "name": "T-mac DAO",
      "symbol": "TMG",
      "slug": "t-mac-dao",
      "cmc_rank": 4802,
      "rank": 3
    },
    {
      "id": 2398,
      "name": "SelfKey",
      "symbol": "KEY",
      "slug": "selfkey",
      "cmc_rank": 753,
      "rank": 4
    },
    {
      "id": 3437,
      "name": "ABBC Coin",
      "symbol": "ABBC",
      "slug": "abbc-coin",
      "cmc_rank": 178,
      "rank": 5
    }
  ]
}
json
application/json
Community Trending Topics
GET
https://pro-api.coinmarketcap.com
/v1/community/trending/topic

Returns the latest trending topics from the CMC Community.

This endpoint is available on the following API plans:

    Standard
    Professional
    Enterprise

Cache / Update frequency: One Minute Plan credit use: 0 credit
Community Trending Topics › query Parameters
limit
​integer · min: 1 · max: 5

Optionally specify the number of results to return.
Default: 5
Community Trending Topics › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Community Trending Topics › Responses

Successful
Community_Trending_Topic_-_Response_Model
​Community_Trending_Topic_-_Results · required

Cntent objects.
GET/v1/community/trending/topic
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/community/trending/topic \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "rank": 1,
    "topic": "Tether"
  },
  "status": {
    "timestamp": "2022-09-08T16:08:52.641Z",
    "error_code": "0",
    "error_message": "SUCCESS",
    "elapsed": "0",
    "credit_count": 0
  }
}
json
application/json
