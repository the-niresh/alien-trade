# WebSocket (Beta) Overview

:::tip[Beta]
WebSocket API is currently in **beta**. This feature is excluded from the Service Level Agreement (SLA).

**API Plan Availability:** Available on **Startup** and above (Startup, Standard, Professional, and Enterprise). Access consumes your monthly credits - up to **10 concurrent connections**, each supporting up to **100 subscriptions**, at **0.1 credit per subscription**. For higher limits, contact us about Enterprise plans.
:::

CoinMarketCap WebSocket API provides real-time market data streaming via persistent WebSocket connections. Two categories of channels are available:

| Category | Channels | Description | Update Trigger |
|----------|---------|-------------|---------------|
| **Market Data** | Crypto Latest Price | CEX spot price, market cap, volume, and price changes | ~5s (top 500 by rank); ~15s (all the other cryptocurrencies) |
| **On-Chain Data** | On-chain channels | Real-time DEX token/pool data: prices, swaps, liquidity, kline, metrics, holders | Event-driven (pushed on each on-chain event or metric update) |

- **Protocol**: WebSocket (WSS)
- **Data format**: JSON text frames
- **Methods**: `subscribe`, `unsubscribe`, `unsubscribe_all`, `ping` (lowercase)
- **Authentication**: `X-CMC_PRO_API_KEY` header

## Endpoint

All WebSocket channels (CEX and DEX) share the same endpoint:

```
wss://pro-stream.coinmarketcap.com/v1
```

## Authentication

All connections require a valid CoinMarketCap API key:

```javascript
// Header (server-side clients, recommended)
const ws = new WebSocket('wss://pro-stream.coinmarketcap.com/v1', {
  headers: { 'X-CMC_PRO_API_KEY': 'your-api-key' }
});
```

---

## Channel Index

| Channel | Category | Subscribe params | Trigger |
|---------|----------|----------------|---------|
| [`market@crypto_latest_price`](/api/documentation/pro-api-websocket/cryptocurrency#latest-price) | Market Data | `crypto_ids` | ~5s (top 500 by rank); ~15s (all the other cryptocurrencies) |
| [`onchain@token_agg_event`](/api/documentation/pro-api-websocket/token#aggregated-token-price-push) | On-Chain | `platform_id`, `address` | Per swap |
| [`onchain@transaction`](/api/documentation/pro-api-websocket/token#transaction-push) | On-Chain | `platform_id`, `address` | Per swap |
| [`onchain@liquidity_event`](/api/documentation/pro-api-websocket/token#liquidity-event-push) | On-Chain | `platform_id`, `address` | Per liquidity tx |
| [`onchain@kline`](/api/documentation/pro-api-websocket/token#kline-push) | On-Chain | `platform_id`, `address`, `interval` | Per interval close |
| [`onchain@token_metric`](/api/documentation/pro-api-websocket/token#token-rolling-metrics-push) | On-Chain | `platform_id`, `address` | Per metric update |
| [`onchain@pool_metric`](/api/documentation/pro-api-websocket/token#pool-rolling-metric-push) | On-Chain | `platform_id`, **`pool_address`** | Per metric update |
| [`onchain@unique_trader`](/api/documentation/pro-api-websocket/token#unique-trader-push) | On-Chain | `platform_id`, `address`, `interval` | Per interval close |
| [`onchain@holders_metrics`](/api/documentation/pro-api-websocket/token#holder-metrics-push) | On-Chain | `platform_id`, `address` | Per holder update |
| [`onchain@holder_wallet_update`](/api/documentation/pro-api-websocket/token#holder-field-change-push) | On-Chain | `platform_id`, **`wallet_address`** | Per wallet update |

On-chain subscribe params require numeric **`platform_id`** (e.g. `14` for BSC, `16` for Solana). Data payloads use short key **`pid`** for the same ID. 
> For `platform_id`, refer to the DEX API [/v1/dex/platform/list](/api/documentation/pro-api-reference/platform#get-platform-list) endpoint.

---

## Market Data

Subscribe with channel `market@crypto_latest_price` and **`crypto_ids`** (required).

**Plan:** Startup and above.

| Push interval | Fields | Scope |
|---------------|--------|--------|
| ~5s (top 500 by rank); ~15s (all the other cryptocurrencies) | 14 fields (`cid`, `p`, `vu`, `mc`, `cs`, multi-window `p*`, `fdv24h`, etc.) | Subscribed `crypto_ids` |

- [Latest Price](/api/documentation/pro-api-websocket/cryptocurrency#latest-price)

### Try it live

<WsPlayground />

### Common Cryptocurrency IDs

| ID | Name | Symbol |
|----|------|--------|
| 1 | Bitcoin | BTC |
| 1027 | Ethereum | ETH |
| 1839 | BNB | BNB |
| 5426 | Solana | SOL |
| 2010 | Cardano | ADA |
| 52 | XRP | XRP |
| 74 | Dogecoin | DOGE |
| 6636 | Polkadot | DOT |
| 3408 | USDC | USDC |
| 825 | Tether | USDT |

For a complete list of cryptocurrency IDs, refer to the [/v1/cryptocurrency/map](/pro-api-reference/cryptocurrency#coinmarketcap-id-map) endpoint or [download the CSV](https://s3.coinmarketcap.com/generated/core/crypto/idmaps.csv).

---

## On-Chain Data

DEX WebSocket streams real-time on-chain events: aggregated prices, swaps, liquidity, kline, rolling token/pool metrics, unique traders, and holder analytics.

Supported chains include **Ethereum**, **BSC**, **Solana**, **Base**, and other EVM-compatible chains.

### Channels

See the [WebSockets Reference](/api/documentation/pro-api-websocket/token) for per-channel schemas and field definitions.

- **Aggregated Token Price** - `onchain@token_agg_event`  
  Params: `platform_id`, `address`  
  Data: `ap`, `p`, `lu`, `pid`, `a`, `ts`

- **Transaction** - `onchain@transaction`  
  Params: `platform_id`, `address`  
  Full swap payload; platform in data is `pid` (number). Dedupe duplicate pushes with `tx` + `lgid`.

- **Liquidity Event** - `onchain@liquidity_event`  
  Params: `platform_id`, `address`  
  `tp`: `add` \| `remove` \| `migrate`

- **Kline** - `onchain@kline`  
  Params: `platform_id`, `address`, `interval`  
  OHLCV in `data`: `o`, `h`, `l`, `c`, `vu`, `ot` (epoch ms)

- **Token Metric** - `onchain@token_metric`  
  Params: `platform_id`, `address`  
  Rolling windows in `sts[]` with `win`, `bc`/`sc`, `vu`, `pc` (0–100 scale), etc.

- **Pool Metric** - `onchain@pool_metric`  
  Params: `platform_id`, **`pool_address`**  
  Windows `5m`, `1h`, `4h`, `24h`, `7d` as objects (`bvn`, `bvu`, `svn`, `svu`, `ut`, `but`, `sut`)

- **Unique Trader** - `onchain@unique_trader`  
  Params: `platform_id`, `address`, `interval` (up to `1d`)  
  Data: `ut`, `ot`

- **Holder Metrics** - `onchain@holders_metrics`  
  Params: `platform_id`, `address`  
  Route by string **`tp`**: `tag_distribution`, `holder_count`, `top_share`, `tag_pnl`, `tag_balance`

- **Holder Wallet Update** - `onchain@holder_wallet_update`  
  Params: `platform_id`, **`wallet_address`**  
  Route by **`tp`**: `token_balance`, `native_balance`, `pnl_stats`, `last_active`, `position_time`

### Try it live (Aggregated Token Price)

<WsPlayground mode="dex" />

### Chain Coverage

`onchain@token_agg_event`, `onchain@transaction`, `onchain@liquidity_event`, `onchain@kline`, `onchain@token_metric`, `onchain@pool_metric`, and `onchain@unique_trader` are supported on all chains.

`onchain@holders_metrics` and `onchain@holder_wallet_update` support EVM chains (Ethereum, BSC, Base, Polygon, Arbitrum, Optimism, Avalanche, Celo, zkSync Era, Scroll, Linea, Berachain, Sonic, Monad, Plasma), Solana, and Tron20 only.

---

## Common Reference

### Message envelope

All server messages use `type` for dispatch:

| `type` | Description |
|--------|-------------|
| `ack` | Response to `subscribe` / `unsubscribe` / `unsubscribe_all` |
| `data` | Channel push |
| `error` | Error (optional `id` echo) |
| `pong` | Response to `ping` |

**Data push** (all channels):

```json
{
  "type": "data",
  "channel": "market@crypto_latest_price",
  "params": { "crypto_ids": 1 },
  "data": { "cid": 1, "p": 81187.93, "vu": 29932025976.79, "mc": 1626089237758.01, "cs": 20028706, "p24h": 0.534 },
  "ts": 1778663880111
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"data"` for pushes |
| `channel` | string | Channel name (e.g. `onchain@kline`) |
| `params` | object | Subscription identity - echoes subscribe params (scalar `address` in pushes) |
| `data` | object | Channel-specific payload |
| `ts` | number | Server timestamp (epoch **ms**) |

Data pushes always include `channel` + `params` (never rely on client `id` for routing). Optional request `id` is echoed only on `ack` / `error`.

**ACK** (example):

```json
{
  "type": "ack",
  "id": 1,
  "code": 0,
  "msg": "ok",
  "channel": "market@crypto_latest_price",
  "sub_count": 1,
  "sub_limit": 100
}
```

Duplicate subscribe (same `channel` + normalized `params`) returns `code: 0` with `"duplicate": true` and does not increase `sub_count`.

### Keep-alive

Use the `ping_interval_ms` from the welcome message (typically **10s**). Send:

```json
{ "id": 1, "method": "ping" }
```

Response:

```json
{ "type": "pong", "id": 1, "code": 0, "ts": 1778659200000 }
```

Idle connections may be closed after prolonged inactivity if neither pings nor data are flowing.

### Subscription commands

**Subscribe**

```json
{
  "id": 1,
  "method": "subscribe",
  "channel": "market@crypto_latest_price",
  "params": { "crypto_ids": [1, 1027] }
}
```

**Unsubscribe** (specific subscription - same `channel` + `params` as subscribe)

```json
{
  "id": 2,
  "method": "unsubscribe",
  "channel": "onchain@kline",
  "params": { "platform_id": 14, "address": ["0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"], "interval": "1m" }
}
```

**Unsubscribe entire channel** (omit `params`)

```json
{ "id": 3, "method": "unsubscribe", "channel": "onchain@kline" }
```

**Unsubscribe all**

```json
{ "id": 4, "method": "unsubscribe_all" }
```

### Quick Start (JavaScript)

```javascript
const ws = new WebSocket('wss://pro-stream.coinmarketcap.com/v1', {
  headers: { 'X-CMC_PRO_API_KEY': 'your-api-key' }
});

ws.onopen = () => {
  ws.send(JSON.stringify({
    id: 1,
    method: 'subscribe',
    channel: 'market@crypto_latest_price',
    params: { crypto_ids: [1, 1027] }
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'data' && msg.channel === 'market@crypto_latest_price') {
    const { cid, p, p24h } = msg.data;
    console.log(`#${cid}: $${p} (${p24h}% 24h) @ ${msg.ts}`);
  }
};

ws.onclose = (event) => {
  console.log(`Disconnected (code: ${event.code}). Implement reconnection logic here.`);
};
```

### Quick Start (Python)

```python
import asyncio
import json
import websockets

async def subscribe():
    uri = "wss://pro-stream.coinmarketcap.com/v1"
    headers = {"X-CMC_PRO_API_KEY": "your-api-key"}

    async with websockets.connect(uri, extra_headers=headers) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "subscribe",
            "channel": "market@crypto_latest_price",
            "params": {"crypto_ids": [1, 1027]},
        }))

        async for raw in ws:
            message = json.loads(raw)
            if message.get("type") != "data":
                continue
            d = message["data"]
            print(f"[{message['channel']}] #{d['cid']}: "
                  f"${d['p']:.2f} ({d['p24h']:+.4f}% 24h)")

asyncio.run(subscribe())
```

## Errors

When a request fails validation, authentication, plan limits, or subscription limits, the server responds with `type: "error"`. The WebSocket envelope adds `type` and optional `id` (echoed from your request); error details live in a **`status`** object that matches the Pro API REST format. Handle failures with `response.status` - read `error_code`, `category`, `error_message`, and optional `error_detail`.

```json
{
  "type": "error",
  "id": 1,
  "status": {
    "timestamp": "2026-05-21T01:57:09.125Z",
    "error_code": "2401",
    "category": "PROTOCOL",
    "error_message": "Missing required param for channel.",
    "error_detail": "Param 'crypto_ids' is required for channel 'market@crypto_latest_price'."
  }
}
```

### Error codes

| Code | Category | Type | `error_message` |
|------|----------|------|-----------------|
| 1001 | AUTH | Authentication | This API Key is invalid. |
| 1002 | AUTH | Authentication | API key missing. |
| 1003 | AUTH | Authentication | Your API Key must be activated. |
| 1004 | AUTH | Authentication | Your API Key subscription plan has expired. |
| 1006 | AUTH | Plan | Your plan does not support this endpoint. |
| 1007 | AUTH | Authentication | This API Key has been disabled. Please contact support. |
| 1010 | AUTH | Credits | Monthly credit limit exceeded. |
| 2201 | PROTOCOL | Request format (22xx) | Invalid request format. |
| 2202 | PROTOCOL | Request format (22xx) | Unknown method. |
| 2203 | PROTOCOL | Request format (22xx) | Message length is not right. |
| 2204 | PROTOCOL | Request format (22xx) | Missing required field. |
| 2301 | PROTOCOL | Subscription / channel (23xx) | Channel does not exist. |
| 2302 | PROTOCOL | Subscription / channel (23xx) | Channel not available on your plan. |
| 2303 | PROTOCOL | Subscription / channel (23xx) | Subscription limit reached. |
| 2304 | PROTOCOL | Subscription / channel (23xx) | Connection limit reached. |
| 2401 | PROTOCOL | Param validation (24xx) | Missing required param for channel. |
| 2402 | PROTOCOL | Param validation (24xx) | Invalid param for channel. |
| 5001 | SERVER | Internal | Internal server error. |

`error_detail` provides context when present (which field, allowed values, current/max limits, etc.).

### WebSocket close codes

Some auth and connection-limit failures close the socket **without** a JSON body. Handle these in `ws.onclose` via the WebSocket close frame code:

| Close code | Reason | When |
|------------|--------|------|
| 1000 | Normal close | Client or server graceful disconnect |
| 1001 | Write idle timeout | Server disconnects inactive connection |
| 1011 | Send failure | Server could not push message |
| 1012 | Frame sink cancellation | Internal stream error |
| 1013 | Close topic signal | Channel shutdown |
| 1014 | Unknown close reason | Unexpected disconnection |
| 4004 | Connection limit | Too many connections for API key (maps to error code 2304) |
| 4100 | API key invalid | Auth failed on connect (maps to error code 1001) |
| 4101 | API key disabled | Auth failed on connect (maps to error code 1007) |
| 4102 | Plan not support WS | Requires Startup and above plan (maps to error code 1006) |

## Best Practices

- **Authentication**: Provide your API key in the header during the handshake.
- **Reconnection**: Reconnect with exponential backoff.
- **Routing**: Branch on `msg.type`; for data, use `channel` + `params` to match subscriptions.
- **Null handling**: Numeric fields may be `null` when unavailable.
- **Timestamps**: All times are epoch **milliseconds** (`ts`, `ot`, `lat`, `spot`, `spct`, etc.).
- **Percentages**: Use **0–100** scale (`2.33` = 2.33%) for `p24h`, `pc`, `devp`, `hp`, holder share fields: `t10p`, `t50p`, `t100p`, etc.
- **Platform in data**: On-chain payloads use `pid` (number), not `platform_id`.
- **Deduping**: Transaction and liquidity events may push twice (token0 and token1 subscriptions). Dedupe with `tx` + `lgid` (or `tx` + `iix` on Solana).
- **Holder routing**: For `onchain@holders_metrics` and `onchain@holder_wallet_update`, check string **`tp`** before reading type-specific fields.
- **Excluded swaps**: `ex: true` means excluded from aggregates; see `txtp` for reason. Filter `ex: false` for price/volume UI if needed.
- **Transaction direction**: `tp` is `buy` or `sell` relative to the pair; use `qi` / `tii` for token-level direction.
- **Bandwidth**: Subscribe only to needed channels and intervals; avoid `1s`/`5s` kline unless required.
- **Precision**: Use decimal types for prices and large USD values in production code.
