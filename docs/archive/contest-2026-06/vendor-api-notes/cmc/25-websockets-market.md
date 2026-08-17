Cryptocurrency

CEX spot quotes via market@crypto_latest_price. Subscribe with crypto_ids (14 fields; ~5s for top 500 by rank, ~15s for other subscribed IDs). Plan: Startup and above.
Latest Price
WSS
wss://pro-stream.coinmarketcap.com
/v1

Subscribe with crypto_ids. Pushes 14 fields ~5s for top 500 by rank, ~15s for all other cryptocurrencies. Plan: Startup and above.

Channel: market@crypto_latest_price

Request example

Code
{
  "id": 1,
  "method": "subscribe",
  "channel": "market@crypto_latest_price",
  "params": {
    "crypto_ids": [
      1,
      1027,
      1839
    ]
  }
}

Latest Price › query Parameters
crypto_ids
​integer[] · required

CoinMarketCap cryptocurrency IDs.
Latest Price › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Latest Price › Responses
200

Streaming data push (type: data).
type
​string · enum · required

Message type (envelope): welcome / ack / data / error / pong
Enum values:
data
channel
​string · required

Channel identifier
params
​object · required

Subscribe params echo (envelope)
​required

Payload data (envelope)
ts
​integer · int64 · required

Server timestamp (epoch ms)
Example Responses
{
  "type": "data",
  "channel": "market@crypto_latest_price",
  "params": {
    "crypto_ids": 1
  },
  "data": {
    "cid": 1,
    "p": 81187.93284788371,
    "vu": 29932025976.79,
    "mc": 1626089237758.01,
    "cs": 20028706,
    "p24h": 0.534347439686,
    "p7d": -0.769630510488,
    "p30d": 14.825850522161,
    "p60d": 14.895817222241,
    "p3m": 20.814087592967,
    "p1y": -21.146722852984,
    "pytd": -8.280487978902,
    "pall": 131301167.42003132,
    "fdv24h": 0.534347439686
  },
  "ts": 1778663880111
}
json
application/json
