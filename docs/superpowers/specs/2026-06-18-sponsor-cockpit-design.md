# Sponsor Cockpit — Design Spec

**Date:** 2026-06-18  
**Branch:** `AT-2-awake-sprint-productization`  
**Status:** Pre-implementation (awaiting plan confirmation)

---

## Goal

Turn the cockpit into a polished operator console that surfaces the full TWAK / CMC / BNB SDK sponsor surface as auditable controls, wires the autonomous agent to use the safe ones, and looks "man-made" (Trenchers-class) not AI-generated. Maps to win-gate via three $2k special prizes + stronger Track-1 demo.

---

## 1. Control Bus Architecture

All operator actions flow through exactly one of three transports. Every control in the system is classified at design time.

| Transport | What it does | Examples |
|---|---|---|
| **Policy** | Writes a Convex `config` or `agent_control` field. Agent reads reactively each cycle. | Kill switch, strategy, equity floor, rug-check gate on/off, x402 budget cap |
| **Read** | UI → Convex action → FastAPI `GET /twak/*` or `/cmc/*` → TWAK/CMC → cached result. No signing. | `wallet portfolio`, `twak price`, `twak risk`, `twak trending`, CMC F&G |
| **Imperative** | UI writes to `agent_commands` queue (token-gated + confirm dialog) → agent worker drains queue → runs signed TWAK command → writes `status` + `result` + `audit` row. | Manual swap, DCA setup, limit order, alert create, erc20 approve/revoke, x402 request |

**Invariant:** The scored path (deterministic `/core` → `twak swap`) is never touched by any operator control except the kill switch and strategy selector.

---

## 2. `SponsorControl` Registry

Single typed config object. Every control in the system is defined once here. The Controls UI, the Docs view, and the landing-page showcase all render FROM this registry.

```typescript
// web/src/lib/sponsorRegistry.ts

export type ScoringImpact = "scored" | "neutral" | "operator";
export type Transport    = "policy" | "read" | "imperative";
export type Sponsor      = "TWAK" | "CMC" | "BNB_SDK" | "agent";

export interface SponsorControl {
  id: string;
  label: string;
  description: string;        // shown in Docs view + control tooltip
  sponsor: Sponsor;
  transport: Transport;
  scoringImpact: ScoringImpact;
  confirmRequired?: boolean;  // imperative commands show confirm dialog
  commandType?: string;       // for imperative: maps to agent_commands.command_type
  readEndpoint?: string;      // for read: FastAPI path
  configKey?: string;         // for policy: Convex config field name
}
```

Scoring-impact visual key in the Controls UI:
- `scored` — green badge "SCORED PATH" — autonomous, counts toward Track-1 PnL
- `neutral` — grey badge — read-only, no signing, no PnL effect
- `operator` — amber badge "OPERATOR" — TWAK-signed, auditable, off scored path

---

## 3. `agent_commands` Table

New Convex table. Operator queues commands from the cockpit; the agent command worker drains them.

```typescript
agent_commands: defineTable({
  command_type: v.string(),     // "manual_swap" | "automate_add" | "automate_pause" |
                                // "automate_resume" | "automate_delete" |
                                // "alert_create" | "alert_delete" |
                                // "erc20_approve" | "erc20_revoke" | "x402_request"
  params: v.string(),           // JSON params specific to command_type
  status: v.union(
    v.literal("queued"),
    v.literal("running"),
    v.literal("done"),
    v.literal("failed"),
  ),
  result:       v.optional(v.string()),   // JSON result on success
  error:        v.optional(v.string()),   // error message on failure
  audit_id:     v.optional(v.id("audit")),
  queued_by:    v.string(),               // "user" always
  queued_at_ms: v.number(),
  updated_at_ms: v.number(),
})
  .index("by_status", ["status"])
  .index("by_queued_at", ["queued_at_ms"])
```

Security: the `enqueueCommand` mutation calls `assertControlToken(args.control_token)` before inserting.

---

## 4. Schema Additions (all in Task 1)

**`copilot_messages` additions:**
- `thread_id: v.optional(v.id("copilot_threads"))` — null = legacy flat thread
- `partial_content: v.optional(v.string())` — streaming in-flight tokens
- `is_streaming: v.optional(v.boolean())` — true while agent is writing tokens

**New `copilot_threads` table:**
```typescript
copilot_threads: defineTable({
  title:          v.string(),
  created_ms:     v.number(),
  last_active_ms: v.number(),
})
  .index("by_last_active", ["last_active_ms"])
```

---

## 5. New Screens

| Screen | View key | Data sources |
|---|---|---|
| **Portfolio** | `portfolio` | Convex action → `/twak/portfolio` → `wallet_state` fallback |
| **Decision Pipeline** | `pipeline` | Convex `decisions` + `signals` + `agent_events` + `risk_state` |
| **Docs** | `docs` | `SponsorControl` registry (static) |
| **Landing** | pre-pairing public route | Static + registry excerpt |

**Reworked:**
- `Controls` — split into two sections: *Autonomous (Scored)* / *Manual Operator Tools*. Each control renders from the registry with its description, sponsor badge, and scoring-impact tag.

---

## 6. Decision Pipeline View

Shows the deterministic `/core` pipeline as a live stage-card sequence. Data is already in Convex — no new tables needed.

Stages:
1. **Market Data** — latest bar OHLCV from `price_ticks`, timestamps, latency
2. **Signal Analysis** — `signals` table: momentum, derivatives, sentiment, flow scores
3. **Regime Detection** — `decisions.regime` — TREND / CHOP / HIGH_VOL / CRASH badge
4. **Risk Check** — `risk_state` circuit breaker + `decisions.risk_verdict`
5. **Execution** — latest `trades` entry: side, size, fill price, tx hash, gas

Each stage shows a status badge (running / pass / block / stale), key values, and the latency since the last cycle. This is the "glass cockpit" that makes the deterministic system VISIBLE.

---

## 7. Co-Pilot Streaming

Agent server writes partial tokens to the message doc as they arrive:

```
1. UI sends question → Convex addMessage (role=user)
2. Convex action calls POST /copilot on agent server
3. Agent writes assistant row immediately: {is_streaming: true, partial_content: ""}
4. As tokens arrive from LLM, agent calls Convex updatePartialContent mutation
5. UI reactive query shows partial_content while is_streaming=true
6. Agent finalises: {is_streaming: false, content: full_text}
```

No new dependencies. Works even when Second Brain is off (fallback response still streams by batching into one "chunk").

---

## 8. Rug-Check Gate

Pre-trade hook in `agent/executor.py`. Calls `TwakCli.risk(asset_id)` before every `swap_execute`. If `risk.is_rug` is true OR `risk.risk_score > RUG_RISK_THRESHOLD` (configurable env var, default 75), the swap is blocked and an audit row is written. Operator can disable via the `rug_check_enabled` policy control (Convex config field).

---

## 9. x402 Micropayments

The `/skill/signal_score` endpoint is already gated via `X402Provider`. This task extends x402 coverage to the CMC data calls the agent makes each cycle (`BinanceClient.fetch_recent_bars` currently calls a free CMC endpoint). When `X402_ENABLED=1` and budget cap > 0, the agent uses `TwakCli.x402_request()` to pay the CMC x402 endpoint with a per-call micropayment capped by `x402_budget_usd` (policy control). This demonstrates CMC + TWAK x402 depth together.

---

## 10. Landing Page

Pre-pairing public route. Renders:
- Hero: "ALIEN·TRADE — Autonomous BSC Trading Agent" with terminal-style description
- Capability showcase: all sponsor controls from registry, grouped by sponsor, with scoring-impact tags
- "Connect Agent" CTA → triggers pairing wizard
- Social proof: live stats pulled from public Convex queries (equity, trades today) if agent is online

Routing: if no token AND hash does not contain `#t=`, show LandingView. Existing QR deep-link (`#t=...`) skips landing and goes to pairing as before.

---

## 11. Visual Direction

True-black operator console. References: Trenchers (depth, hierarchy, pro density).

- Background: `#000000` (not `#050508`)  
- Surface: `#0a0a0a`  
- Panel: `#111111` with `1px` `#1a1a1a` border  
- Alien-green accent: stays `oklch(68% 0.22 145)` but used with more restraint — only on active state, not everywhere  
- Typography: tighter leading, denser stat grids (4 cols instead of 3)  
- No colour washing everywhere — let black breathe

Changes: update CSS custom properties in `web/src/globals.css`. Do NOT change the alien-green identity, only make black blacker and reduce green wash.

---

## Scoring Safety Guarantee

No feature in this plan touches the scored path. The scored path is:
1. `/core` deterministic Python (signal computation + regime + risk + order sizing)
2. `TwakCli.swap_execute()` via the existing `agent/executor.py`

The rug-check gate only BLOCKS a swap — it never CAUSES one. Every other new feature is read-only, advisory, or queued-and-signed-manually. The `agent_commands` worker runs AFTER the main decision cycle to avoid any timing interaction.
