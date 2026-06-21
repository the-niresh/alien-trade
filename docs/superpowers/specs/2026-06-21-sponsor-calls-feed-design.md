# Sponsor-Calls Dynamic Feed — Design

**Date:** 2026-06-21
**Branch:** AT-2-awake-sprint-productization
**Status:** Approved (brainstorm) → ready for implementation plan

> **Win-gate:** A live, judge-legible record of every CMC / TWAK / BNB-SDK call —
> with x402 micropayment spend and on-chain tx links — directly serves the three
> $2k special prizes (CMC / TWAK / BNB depth of usage). **Yes.**
>
> **Freeze note:** Today (Jun 21) is the feature freeze. This design is additive:
> a *new isolated* Convex table + agent-layer fire-and-forget emits + a UI rewrite.
> It does **not** touch the deterministic trade math, existing tables, or existing
> validators, so it cannot break the running live agent.

---

## 1. Goal

Replace the static Intelligence tab with a **dynamic dashboard** that shows, in
real time, every call the agent makes to a sponsor layer (CMC, TWAK, BNB-SDK):
which sponsor, which endpoint, status, latency, x402 cost, and tx hash. Notable
calls also surface in the Notification panel.

## 2. Decisions (locked in brainstorm)

1. **Storage:** dedicated `sponsor_calls` Convex table (typed columns for cheap
   per-sponsor aggregation).
2. **Coverage:** all three sponsors — CMC + TWAK + BNB-SDK.
3. **Presentation:** fully replace the static Intelligence view with a live
   telemetry dashboard.
4. **Notifications:** notable calls only (swaps, x402 payments, errors) fan out to
   the Notification panel via `agent_events`.

## 3. Architecture

A module-level **telemetry recorder** decouples the sponsor clients from Convex.
Clients call `record_sponsor_call(...)`, which is a **no-op until a sink is
registered** (so sim runs and unit tests stay silent). At runtime startup the sink
is `bridge.emit_sponsor_call`. The recorder is **non-blocking** (a daemon thread
drains a queue), so the trade path never waits on a Convex write and never sees an
exception from telemetry.

```
TwakCli._run ─┐
copilot cmc  ─┼─► record_sponsor_call() ─► queue ─► daemon ─► bridge.emit_sponsor_call()
Onchain exec ─┘                                              └─► sponsorCalls:append (Convex)
                                                                   ├─► sponsor_calls row
                                                                   └─► agent_events row (notable only)
IntelligenceView ◄── sponsorCalls.summary + sponsorCalls.recent (reactive)
NotificationPanel ◄── agentEvents.recent (already wired)
```

## 4. Data model — `sponsor_calls` table (new, additive)

Add to `convex/schema.ts`:

```ts
sponsor_calls: defineTable({
  sponsor:    v.union(v.literal("CMC"), v.literal("TWAK"), v.literal("BNB_SDK")),
  kind:       v.string(),   // data|swap|balance|compete|payment|price|risk|trending|search|skill|sign
  endpoint:   v.string(),   // human label: "swap execute", "wallet balance", url path, skill name
  status:     v.union(v.literal("ok"), v.literal("error")),
  latency_ms: v.number(),
  cost_usd:   v.optional(v.number()),   // x402 micropayment (CMC)
  tx_hash:    v.optional(v.string()),
  cycle_id:   v.optional(v.string()),
  detail:     v.string(),               // JSON blob (args summary / error)
  ts_ms:      v.number(),
})
  .index("by_ts", ["ts_ms"])
  .index("by_sponsor", ["sponsor"]),
```

No existing table or validator is modified.

## 5. Telemetry recorder + sink

### 5.1 `agent/sponsor_telemetry.py` (new)

```python
# Module-level, fire-and-forget sponsor-call recorder. No-op until a sink is set.
SponsorCall = dataclass(sponsor, kind, endpoint, status, latency_ms,
                        cost_usd=None, tx_hash=None, cycle_id=None, detail="{}", ts_ms=...)

def set_sink(fn): ...          # registered once at runtime startup
def record_sponsor_call(...):  # build SponsorCall, enqueue; never raises
```

- Internally: a `queue.Queue` + a single daemon thread that pops calls and forwards
  to the sink. If no sink is registered, `record_sponsor_call` returns immediately.
- The daemon wraps the sink in `try/except` — a telemetry failure is swallowed.
- `latency_ms` is measured by the caller (the instrumentation wrapper times the call).

### 5.2 Bridge — `agent/convex_bridge.py`

- Add `"sponsorCalls:append"` to the `_GUARDED_MUTATIONS` allowlist.
- Add `emit_sponsor_call(call) -> Optional[str]` → `self._call("mutation",
  "sponsorCalls:append", call.as_row())` (control token attached automatically by
  the existing `_call` guard logic).

### 5.3 Registration — `agent/runtime.py`

In `main()` (after `build_bridge`):

```python
from agent import sponsor_telemetry
sponsor_telemetry.set_sink(bridge.emit_sponsor_call)
```

`TwakCli` and the other clients stay decoupled — they only call the module-level
`record_sponsor_call`, which is inert until this line runs.

## 6. Instrumentation points (all in `agent/`, freeze-safe)

### 6.1 `TwakCli._run` (the chokepoint) — TWAK + CMC-x402

`x402_request` calls `self._run("x402", "request", url, ...)`, so a single wrap on
`_run` captures both. In `_run`:

1. Record `t0 = time.monotonic()` before the subprocess call.
2. After it returns (or raises), compute `latency_ms`.
3. Classify by `args[0]`:
   - `"x402"` → `sponsor="CMC"`, `kind="data"`; best-effort parse `cost_usd` and
     `tx_hash` from the response JSON.
   - otherwise → `sponsor="TWAK"`; `kind` = mapped from `args[0]`
     (`swap`→"swap"/"price"/"quote" per `args[1]`, `wallet`→"balance"/"address",
     `compete`→"compete", `risk`→"risk", `trending`→"trending", `search`→"search").
   - `endpoint` = `" ".join(args[0:2])`.
4. `status="ok"` on success, `"error"` on exception (then re-raise the original
   exception so behavior is unchanged).
5. Call `record_sponsor_call(...)`. This wrapping must never alter `_run`'s return
   value or swallow its exceptions.

### 6.2 `agent/copilot_agent.py` — CMC MCP skill

In the `cmc_market_skill` tool handler: wrap the call, record
`sponsor="CMC", kind="skill", endpoint=<skill unique_name>`. Off the trade path.

### 6.3 `OnchainExecutor.execute` (`agent/executor.py`) — BNB-SDK

Wrap the broadcast in `execute()`: record `sponsor="BNB_SDK", kind="sign",
endpoint="onchain execute", tx_hash=<broadcast result>`. Dev/testnet-only per the
scoring ruling, included per the "all three" decision.

### 6.4 Left untouched

`core/data/cmc_client.py` (honor freeze; not on the live path). Logged as an
out-of-scope honesty follow-up if direct-CMC usage grows.

## 7. Convex functions — `convex/sponsorCalls.ts` (new)

### 7.1 `append` (mutation, token-gated)

- `assertControlToken` (mirror `agentEvents:append`).
- Insert the `sponsor_calls` row.
- **Notable fan-out:** if `kind ∈ {"swap","payment"}`, or `cost_usd > 0` (any paid
  x402 call), or `status === "error"`, also insert an `agent_events` row:
  - `agent = sponsor`, `kind = "action"`,
  - `headline` templated (e.g. `"TWAK swap executed"`, `"CMC x402 payment $0.01"`,
    `"BNB_SDK call failed"`),
  - `detail` = the same JSON, `refs = [tx_hash]` when present.
  This is how notable sponsor calls reach the Notification panel — no extra agent
  round trip.
- **Retention:** after insert, if the table exceeds ~500 rows, delete the oldest
  beyond 500 (reuse the existing prune pattern used elsewhere).

### 7.2 `recent` (query)

`args: { limit?: number }` → newest-first slice of `sponsor_calls` (default 50).

### 7.3 `summary` (query)

No args → scan the last ~500 rows, aggregate per sponsor:
`{ sponsor, calls, errors, cost_usd_total, last_ts }` for CMC / TWAK / BNB_SDK
(zero-filled when a sponsor has no calls yet).

## 8. Intelligence dashboard rewrite — `web/src/views/IntelligenceView.tsx`

Full replace of the static SponsorCards / ON-OFF-ARMED pills with a live dashboard:

- **Summary row (top):** three cards from `sponsorCalls.summary`:
  - CMC — calls · `$` spent via x402 · errors
  - TWAK — swaps signed · total calls
  - BNB_SDK — calls
  Each keeps a one-line descriptor for judge context (descriptor, not a fake status).
- **Live feed (below):** from `sponsorCalls.recent` — each row: sponsor badge, kind,
  endpoint, status (green ok / red error), latency, cost (when present), and a
  BscScan tx link when `tx_hash` is present.
- **Empty state:** "No sponsor calls yet — agent idle." until rows arrive.
- Styling matches the existing cockpit idiom (`font-mono` labels, `panel` cards,
  `cn(...)`, sponsor colors).

The `SponsorCard` component may be retained for the descriptor framing or replaced;
the static ON/OFF/ARMED status logic is removed.

## 9. Failure isolation & freeze-safety

- Recorder is fire-and-forget on a daemon queue: zero added latency on the trade
  path, never raises into `_run` / `execute` (same principle as "LLM off the hot
  path", locked decision #1).
- Only new symbols are added (table, functions, emits, recorder). Existing trade
  logic and schema are unchanged.

## 10. Testing

- **pytest** (`agent/tests/`):
  - `record_sponsor_call` is a no-op when no sink is registered.
  - With a sink registered, a recorded call reaches the sink (drain the queue).
  - When the sink raises, `record_sponsor_call` / the daemon never propagate it.
  - `_run` classification: `args[0]=="x402"` → `sponsor="CMC"`; other commands →
    `sponsor="TWAK"` with correct `kind`/`endpoint`; a raising subprocess records
    `status="error"` and still re-raises.
- **Convex/web:** `tsc` typecheck passes; the `append` notable-fan-out inserts an
  `agent_events` row for `swap`/`payment`/`error` (and not for routine `data`
  reads); manual screenshot of the Intelligence dashboard with live rows + an
  empty state.

## 11. Out of scope

- Logging non-sponsor external calls (Binance / alternative.me) — honesty
  follow-up, not v1.
- Historical backfill of past sponsor calls.
- Per-user telemetry; rerouting the core daily feed to CMC.
