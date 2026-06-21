Statistics Latest
GET
https://pro-api.coinmarketcap.com
/v1/blockchain/statistics/latest

Returns the latest blockchain statistics data for 1 or more blockchains. Bitcoin, Litecoin, and Ethereum are currently supported. Additional blockchains will be made available on a regular basis.

This endpoint is available on the following API plans:

    Basic
    Hobbyist
    Startup
    Standard
    Professional
    Enterprise

Cache / Update frequency: Every 15 seconds.
Plan credit use: 1 call credit per request.
CMC equivalent pages: Our blockchain explorer pages like blockchain.coinmarketcap.com/.
Statistics Latest › query Parameters
id
​string · pattern: ^\d+(?:,\d+)*$

One or more comma-separated cryptocurrency CoinMarketCap IDs to return blockchain data for. Pass 1,2,1027 to request all currently supported blockchains.
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Alternatively pass one or more comma-separated cryptocurrency symbols. Pass BTC,LTC,ETH to request all currently supported blockchains.
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Alternatively pass a comma-separated list of cryptocurrency slugs. Pass bitcoin,litecoin,ethereum to request all currently supported blockchains.
Statistics Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Statistics Latest › Responses

Successful
Blockchain_Statistics_Latest_-_Response_Model
​Blockchain_Statistics_Latest_-_Results_map · required

A map of blockchain objects by ID, symbol, or slug (as used in query parameters).
​API_Status_Object

Standardized status object for API calls.
GET/v1/blockchain/statistics/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/blockchain/statistics/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "1": {
      "id": 1,
      "slug": "bitcoin",
      "symbol": "BTC",
      "block_reward_static": 12.5,
      "consensus_mechanism": "proof-of-work",
      "difficulty": "11890594958796",
      "hashrate_24h": "85116194130018810000",
      "pending_transactions": 1177,
      "reduction_rate": "50%",
      "total_blocks": 595165,
      "total_transactions": "455738994",
      "tps_24h": 3.808090277777778,
      "first_block_timestamp": "2009-01-09T02:54:25.000Z"
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
