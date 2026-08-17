# Design — Level-1 Agent Prompt + Token-Efficient Market/Trade Monitor

Status: APPROVED (office-hours, 2026-06-22) · Mode: hackathon/live · Build target: live judging window
Owner: Nire · Implements against locked decisions #1 (LLM off hot path) and #6 (failure = log, never halt)

---

## 1. Problem

Two gaps surfaced while polishing the agent cockpit for live judging:

1. **Spawned (level-1) agents have a weak goal prompt.** `agent/agents/runner.py::_goal_prompt`
   tells the agent it's an "orchestrator" with a tool list, but never says *what each tool is
   for*, that it is a **specialized researcher**, or that it must hand up a **fast, decisive**
   synthesis. Level-1 gathers; the decision layer decides quick.
2. **No market/trade monitor.** Operators can't say "watch CAKE, ping me if it drops." The
   existing `market_watcher` template runs the full LLM loop every cadence just to look —
   token-wasteful and only checks at 1h/4h, missing fast moves.

Hard constraint (operator's words): **token-efficient** and **flawless live for judges.**

---

## 2. Premise (agreed)

A monitor must NOT be an LLM that wakes each cycle to ask "did it trigger yet?" — that burns
tokens every tick and puts an LLM on a polling path (violates locked decision #1). Correct shape:
**deterministic watch + LLM only when it actually fires.** Steady-state token cost = 0. One short
LLM call happens only on the edge, to explain *why it matters*. Deterministic = it works every
time on stage.

---

## 3. Decision — Approach A: Deterministic watch + explain-on-fire

A watch is a row `{kind, target, op, threshold, last_state}`:
- `kind`: `price | regime | pnl | drawdown`
- `op`: `lt | gt | crosses`
- example: `{price, CAKE, lt, 2.40}`

A cheap **Python checker** runs each tick against data already in hand (price / regime /
PnL / drawdown) — **no LLM**. Edge-trigger logic (condition newly true vs `last_state`):

```
tick → check each watch (deterministic)
  not fired      → 0 tokens, update last_state
  EDGE FIRE      → Convex event  (agent_events)
                 → Telegram alert (agent/notify.py)
                 → ONE co-pilot line: "why this matters" (run_read_loop, 1 short call)
```

Surfaces in the cockpit as a **Watches panel**, and becomes the real engine behind the
`market_watcher` template (replacing its LLM-poll loop).

Rejected:
- **B (+`set_watch` co-pilot tool):** conversational creation is a great demo, but more tool
  surface to wire + verify before judges. Keep as a thin follow-on once A is solid.
- **C (prompt + cadence only):** cheapest, but checks only at 1h/4h and burns an LLM call
  every tick. Fails the token-efficient + flawless bar.

---

## 4. Data source / latency (push, not poll)

Today both feeds are HTTP request/response:
- Market price: Binance REST (`core/data/binance_client.py`).
- On-chain: JSON-RPC over HTTP in `core/exec/bnb.py` (`eth_call`, `eth_estimateGas`).

For the checker, feed it **push streams** so it reacts in seconds, not at the next hourly poll:

| Surface | Lowest-latency source | Notes |
|---|---|---|
| Market price | **Binance WS** `wss://stream.binance.com/ws/<sym>@miniTicker` (or `@kline_1s`) | ms push; NOT JSON-RPC. Engine already uses Binance, so this is the natural feed. Subscribe once, hold latest price in memory. |
| On-chain fills / position change | **JSON-RPC `eth_subscribe`** over `wss://` BSC RPC — `logs` on the wallet Transfer / pair Swap, or `newHeads` | The literal "JRPC method to reduce latency." Push on ~1 block (sub-3s) vs polling a receipt. |
| Execution simulate-before-send | **JSON-RPC batch** (`[eth_call, eth_estimateGas]` in one array) | One round trip instead of two per trade. |
| Any RPC call | **`BNB_RPC_URL` env override** → dedicated endpoint | Zero-code latency win over the public node. |

**Caveat (keep the risk story intact):** all latency work serves the **monitor/alerts** and
**execution confirmation** only. The scored trade engine stays deterministic + hourly by design
(locked decision #6). Lower data latency must NOT make it trade faster.

Persistent WS = one always-on asyncio task with reconnect/backoff. Public BSC WS is flaky/rate-
limited — prefer a dedicated endpoint. The `eth_call` simulate path stays HTTP (request/response
fits it).

---

## 5. Level-1 prompt rewrite (`_goal_prompt`)

Replace the current orchestrator prompt with a specialized-researcher framing that names each
tool's job and demands a fast, decisive hand-up:

```
You are '{name}', a specialized research agent in the Alien-Trade mesh.
Your tools and what each is for:
  - get_wallet        live self-custody holdings + USD values
  - get_price         live USD spot price for one token
  - get_trending      ranked BNB-chain movers
  - check_token_risk  rug / contract safety for one token
  - cmc_market_skill  deep market data (OHLCV, funding/OI, sentiment, on-chain flow)
  - get_agent_state   the main trader's PnL / drawdown / regime / last decisions
You are specialized at research with these tools: call them as many times and in whatever
combination it takes to ground your answer in live data — never guess when a tool can tell you.
Your mandate: {goal}.
Work the mandate, then hand up a fast, decisive synthesis:
  (1) what you found (grounded in tool output),
  (2) your call in one line — act / wait / avoid, or the specific alert,
  (3) whether the operator should be notified now.
Be token-frugal: stop calling tools the moment you can answer. No padding.
```

This makes level-1 = gather-with-specialized-tools, and the synthesis = the quick decision the
operator (level-2) consumes.

---

## 6. Build order

1. `_goal_prompt` rewrite (lowest risk, no new surface). Verify spawned-agent tests still pass.
2. `watches` Convex table + `create/list/cancel/setState` functions; reuse `assertControlToken`.
3. Python deterministic checker (`agent/watches.py`) — pure function `evaluate(watch, snapshot)`;
   unit-tested with table-driven edge cases (not-fired / edge-fire / already-fired).
4. Wire checker into the existing loop tick; on fire → Convex event + `notify.py` Telegram + one
   `run_read_loop` explain call.
5. Cockpit Watches panel (read `watches`, add/cancel).
6. Latency upgrade (optional, after the above is green): Binance WS price task + `eth_subscribe`
   on-chain fill stream feeding the checker.

## 7. Verification (flawless-for-judges bar)

- Unit: checker fires exactly on the edge, never twice, never on noise.
- Integration: create watch → force condition → see Convex event + Telegram alert + one-line why.
- Token audit: idle watches over N ticks = 0 LLM calls (assert in test via a mock client).
- Live: demo a price watch tripping on stage, alert lands on phone in seconds.

## 8. The assignment (next real action)

Before building the WS latency layer, **pick the RPC endpoint**: confirm `BNB_RPC_URL` points at a
dedicated low-latency BSC node (not the public default), and confirm it exposes a `wss://`
subscription endpoint. That one fact decides whether the on-chain `eth_subscribe` path is even
available for the live window — verify it before writing the subscription task.
