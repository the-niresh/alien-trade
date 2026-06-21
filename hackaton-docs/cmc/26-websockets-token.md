Token

DEX on-chain channels. Subscribe with platform_id. Data payloads use numeric pid; discriminate holder channels with string tp.
Aggregated Token Price and Liquidity
WSS
wss://pro-stream.coinmarketcap.com
/v1

Aggregated (ap) and single-pool (p) USD prices plus liquidity lu.

Channel: onchain@token_agg_event

Request example

Code
{
  "id": 7,
  "method": "subscribe",
  "channel": "onchain@token_agg_event",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ]
  }
}

Aggregated Token Price and Liquidity › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required
Aggregated Token Price and Liquidity › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Aggregated Token Price and Liquidity › Responses
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
  "channel": "onchain@token_agg_event",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
  },
  "data": {
    "pid": 14,
    "a": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "ap": 0.9998026294970268,
    "p": 0.9997425990337028,
    "lu": 112769637.58815227,
    "ts": 1778659194000
  },
  "ts": 1778663880111
}
json
application/json
Kline
WSS
wss://pro-stream.coinmarketcap.com
/v1

OHLCV candle updates. data uses object keys o, h, l, c, vu, ot (not the legacy u array).

Channel: onchain@kline

Request example

Code
{
  "id": 2,
  "method": "subscribe",
  "channel": "onchain@kline",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ],
    "interval": "1m"
  }
}

Kline › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required

Token contract addresses.
interval
​enum · required

Candle interval for onchain@kline subscribe param
Enum values:
1s
5s
30s
1m
3m
5m
15m
30m
Kline › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Kline › Responses
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
  "channel": "onchain@kline",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "interval": "1m"
  },
  "data": {
    "o": 0.9995980459860556,
    "h": 0.999729701705,
    "l": 0.999529767125,
    "c": 0.999677480145,
    "vu": 3237.47055005272,
    "ot": 1778649420000
  },
  "ts": 1778663880111
}
json
application/json
Unique Trader
WSS
wss://pro-stream.coinmarketcap.com
/v1

Distinct trader count per candle interval (intervals up to 1d).

Channel: onchain@unique_trader

Request example

Code
{
  "id": 3,
  "method": "subscribe",
  "channel": "onchain@unique_trader",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ],
    "interval": "1m"
  }
}

Unique Trader › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required
interval
​enum · required

Candle interval for onchain@unique_trader (up to 1d)
Enum values:
1s
5s
30s
1m
3m
5m
15m
30m
Unique Trader › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Unique Trader › Responses
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
  "channel": "onchain@unique_trader",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "interval": "1m"
  },
  "data": {
    "ut": 6,
    "ot": 1778659140000
  },
  "ts": 1778663880111
}
json
application/json
Transaction
WSS
wss://pro-stream.coinmarketcap.com
/v1

Full swap payload. data.pid is the platform ID (number). Same swap may appear on both token0 and token1 channels — dedupe by tx + lgid.

Channel: onchain@transaction

Request example

Code
{
  "id": 4,
  "method": "subscribe",
  "channel": "onchain@transaction",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ]
  }
}

Transaction › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required
Transaction › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Transaction › Responses
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
  "channel": "onchain@transaction",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
  },
  "data": {
    "pid": 14,
    "f": "0xdb1d10011ad0ff90774d0c6bb92e5c5c8b4461f7",
    "bh": 98011237,
    "tp": "sell",
    "pa": "0x2f4a644cd20eb9f45fa166dbb87068697fe8e6e3",
    "t0a": "0x5feccd17c393caf1001d18164236a37e731fcb9d",
    "t1a": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "t0s": "USDC",
    "t1s": "WBNB",
    "vu": 167.11650988683866,
    "q": 0.2876839934391258,
    "t0pu": 0.28760994330122636,
    "t1pu": 0.9997425990337028,
    "tx": "0xade908a367c85915a89719ddce9e95a864bd2c9691bb28c6d6b86d907181f7aa",
    "ts": 1778659192000,
    "ma": "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df",
    "ba": "0x55d398326f99059ff775485246999027b3197955",
    "a0": 8.581676894301156,
    "a1": 0.9999663716704877,
    "qi": 0,
    "tii": 0,
    "lgid": 59,
    "ex": false,
    "txtp": 0
  },
  "ts": 1778663880111
}
json
application/json
Liquidity Event
WSS
wss://pro-stream.coinmarketcap.com
/v1

Add / remove / migrate liquidity. May push twice per event (token0 and token1).

Channel: onchain@liquidity_event

Request example

Code
{
  "id": 5,
  "method": "subscribe",
  "channel": "onchain@liquidity_event",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ]
  }
}

Liquidity Event › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required
Liquidity Event › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Liquidity Event › Responses
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
  "channel": "onchain@liquidity_event",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
  },
  "data": {
    "pid": 14,
    "f": "0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865",
    "ts": 1778659195000,
    "tp": "add",
    "t0s": "USDC",
    "t1s": "MAT",
    "t0a": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "t1a": "0xfe2dd2d57a05f89438f3aec94e",
    "a0": 0,
    "a1": 293.8158004758334,
    "vu": 49.84709760712249,
    "ma": "0x7cc5a95f6e688a917c899084b5cfd389de730fdf",
    "tx": "0xcf859eb0b1c563ea69255eb4ea8a134002948e7e7e9913f441896c518a4dfaeb",
    "lgid": 12
  },
  "ts": 1778663880111
}
json
application/json
Token Rolling Metrics
WSS
wss://pro-stream.coinmarketcap.com
/v1

Rolling windows in sts[] with win (1m, 5m, 1h, 4h, 24h). pc is 0–100 scale (e.g. -0.01 = -0.01%).

Channel: onchain@token_metric

Request example

Code
{
  "id": 6,
  "method": "subscribe",
  "channel": "onchain@token_metric",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ]
  }
}

Token Rolling Metrics › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required
Token Rolling Metrics › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Token Rolling Metrics › Responses
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
  "channel": "onchain@token_metric",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
  },
  "data": {
    "pid": 14,
    "a": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "p": 0.9997425990337028,
    "mc": null,
    "lu": null,
    "sts": [
      {
        "win": "4h",
        "vn": 6615525.086132893,
        "vu": 6613627.176252886,
        "pc": -0.01,
        "txs": 28864,
        "bc": 12692,
        "sc": 16172,
        "bvu": 3234904.850668452,
        "svu": 3378722.325584434,
        "bvn": null,
        "svn": null,
        "ut": 6211,
        "but": 3695,
        "sut": 4142,
        "h": 1.0003681078349795,
        "l": 0.9994
      }
    ]
  },
  "ts": 1778663880111
}
json
application/json
Pool Rolling Metric
WSS
wss://pro-stream.coinmarketcap.com
/v1

Subscribe with pool_address. Each window (5m, 1h, 4h, 24h) is an object with bvn, bvu, svn, svu, ut, but, sut.

Channel: onchain@pool_metric

Request example

Code
{
  "id": 10,
  "method": "subscribe",
  "channel": "onchain@pool_metric",
  "params": {
    "platform_id": 16,
    "pool_address": [
      "DJpdHs4wbm1XqRruM1NPHnSfpnSztUEeFW3bcaDEeg7H"
    ]
  }
}

Pool Rolling Metric › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
pool_address
​string[] · required

Pool / LP contract addresses.
Pool Rolling Metric › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Pool Rolling Metric › Responses
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
  "channel": "onchain@pool_metric",
  "params": {
    "platform_id": 16,
    "pool_address": "DJpdHs4wbm1XqRruM1NPHnSfpnSztUEeFW3bcaDEeg7H"
  },
  "data": {
    "pid": 16,
    "pa": "DJpdHs4wbm1XqRruM1NPHnSfpnSztUEeFW3bcaDEeg7H",
    "5m": {
      "bvn": 0,
      "bvu": 0,
      "svn": 0,
      "svu": 0,
      "ut": 11,
      "but": 2,
      "sut": 10
    },
    "1h": {
      "bvn": 123.45,
      "bvu": 500,
      "svn": 87.65,
      "svu": 400,
      "ut": 53,
      "but": 21,
      "sut": 38
    },
    "4h": {
      "bvn": 1234.56,
      "bvu": 5000,
      "svn": 987.65,
      "svu": 4000,
      "ut": 200,
      "but": 80,
      "sut": 120
    },
    "24h": {
      "bvn": 12345.67,
      "bvu": 50000,
      "svn": 9876.54,
      "svu": 40000,
      "ut": 1000,
      "but": 400,
      "sut": 600
    }
  },
  "ts": 1778663880111
}
json
application/json
Holder Metrics
WSS
wss://pro-stream.coinmarketcap.com
/v1

Discriminate by string tp: tag_distribution, holder_count, top_share, tag_pnl, tag_balance.

Channel: onchain@holders_metrics

Request example

Code
{
  "id": 8,
  "method": "subscribe",
  "channel": "onchain@holders_metrics",
  "params": {
    "platform_id": 14,
    "address": [
      "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
    ]
  }
}

Holder Metrics › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
address
​string[] · required
Holder Metrics › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Holder Metrics › Responses
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
  "channel": "onchain@holders_metrics",
  "params": {
    "platform_id": 14,
    "address": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
  },
  "data": {
    "pid": 14,
    "a": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "tp": "tag_distribution",
    "ts": 1778659184000,
    "devp": 12,
    "khc": 221,
    "whc": 2518,
    "bdhc": 3897,
    "shc": 102,
    "bhc": 45,
    "smhc": 2
  },
  "ts": 1778663880111
}
json
application/json
Holder Wallet Update
WSS
wss://pro-stream.coinmarketcap.com
/v1

Subscribe with wallet_address (not token address).

Channel: onchain@holder_wallet_update

Request example

Code
{
  "id": 9,
  "method": "subscribe",
  "channel": "onchain@holder_wallet_update",
  "params": {
    "platform_id": 16,
    "wallet_address": [
      "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN"
    ]
  }
}

Holder Wallet Update › query Parameters
platform_id
​required

Platform ID (e.g. 14 for BSC, 16 for Solana).

Platform / chain ID (numeric, e.g. 14 = BSC, 16 = Solana)
wallet_address
​string[] · required

Wallet addresses to watch.
Holder Wallet Update › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Holder Wallet Update › Responses
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
  "channel": "onchain@holder_wallet_update",
  "params": {
    "platform_id": 16,
    "wallet_address": "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN"
  },
  "data": {
    "pid": 16,
    "wa": "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
    "tp": "token_balance",
    "a": "GYQQfZTnTokenMintAddress",
    "b": 37151378.807477,
    "hp": 3.715,
    "bh": 416995858,
    "ts": 1778659191803
  },
  "ts": 1778663880111
}
json
application/json
