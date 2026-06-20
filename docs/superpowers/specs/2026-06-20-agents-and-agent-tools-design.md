# Agents & Agent Tools — Design Spec

**Date:** 2026-06-20
**Status:** Approved (brainstorm) → ready for plan
**Freeze:** Jun 21, 2026 · **Live window:** Jun 22–28, 2026
**Author:** Nire + Claude

---

## 1. Problem & intent

Alien-Trade today ships five fixed internal roles — **CoPilot, Historian, Researcher,
Reflector, WalletManager** (`web/src/components/AgentCard.tsx:AGENT_DEFS`,
`agent/graph/supervisor.py`). They are presented to the user as an "Agent Team" but
they are really *capabilities*, not agents the user controls.

We want the user to **spawn, name, and rename their own agents** that pursue a goal —
watch a market, research, propose a strategy, recognise a pattern in history, and report
back — and to make the **sponsor-layer composition explicit** for hackathon judging.

The seam (confirmed with the operator):

- **Agent Tools** (Tier A) — the five specialized, *sponsor-powered* building blocks.
- **Agents** (Tier B) — user-spawned, user-named, possibly many. An Agent has no powers
  of its own; it can only call Agent Tools. That constraint is what makes it both **safe**
  and **the judging pitch**: *"every agent our user builds is composed from our
  sponsor-powered capability layer."*

**Operator directive (2026-06-20): build this fully, not a trimmed slice — and the
specialized Agent Tools must collaborate with each other** (multi-agent handoffs), not just
sit as independent tools. Collaboration is specified in §5.1 and the scope is re-cut as a
**phased full build** (§8): Phase 1 lands by freeze for safety; Phases 2–3 land through the
Jun 29–Jul 5 judging window (legitimate — the freeze governs the *trading* path, which is the
done deterministic `/core`; the cockpit/demo keeps improving).

### Win-gate justification
This does **not** directly raise Track 1 PnL (one wallet, deterministic `/core`). It is a
**maybe → build, scoped** item: its value is (a) demonstrable **sponsor depth** feeding the
three $2k specials (CMC / TWAK / BNB-SDK), and (b) the product/demo narrative. It is only a
"yes" if it **cannot endanger the scored wallet** — see §4.

---

## 2. The two tiers

```
┌─ AGENTS (Tier B) ─ user-spawned · user-named · multiple ─────────────┐
│  e.g. "Watch CAKE, ping me when funding flips negative"              │
│  record = { name, goal, allowed_tools[], trigger, notify_policy,    │
│             mode: paper|live, status }                              │
│        │ may ONLY call ▼                                            │
├─ AGENT TOOLS (Tier A) ─ 5 specialized · sponsor-powered ─────────────┤
│  Researcher          → CMC Agent Hub        (data + market skills)  │
│  Historian/Reflector → Upstash Vector       (Hermes memory)         │
│  WalletManager + exec→ TWAK + BNB SDK        (signing / fills)       │
│  CoPilot             → Claude               (reasoning / chat)      │
└──────────────────────────────────────────────────────────────────────┘
   The deterministic /core trading loop is a SEPARATE process — untouched.
```

**Agent Tools** are the existing read-capabilities, surfaced as a stable tool list.
The co-pilot already exposes most of them in `agent/copilot_agent.py:TOOLS`
(`get_price`, `get_trending`, `check_token_risk`, `cmc_market_skill`, `get_agent_state`).
The Agent runtime reuses that exact loop and tool set — no duplicate logic (locked #2).

---

## 3. Where Agents run & how they execute

- An Agent runs as a **bounded Anthropic tool-loop** (the same loop as
  `agent/copilot_agent.py`, routed through the LangGraph supervisor), **off the trade hot
  path** — the Tier-1 advisory rule (locked #1/#6). It is **never** executed inside the
  deterministic `/core` loop process.
- **Trigger:** schedule (cron-like cadence) or event (a loop tick / Convex event). Reuse the
  existing Trigger.dev / loop tick rather than a new scheduler.
- **Budget & dedupe:** each run is capped by `MAX_HOPS` (already in
  `agent/graph/supervisor.py`) and dedupe-guarded per (agent_id, window), mirroring the
  Researcher's 90-min symbol dedupe.
- **No silent failure** (the 7-hour outage from the 2026-06-20 session is the cautionary
  tale): every Agent run
  1. writes a **heartbeat** (`last_activity_ms`, already on `spawned_agents`),
  2. wraps its body in the existing `_emit_failure` pattern (supervisor §8.14),
  3. is covered by a **watchdog** that flags any Agent silent past `expected_cadence × N`.
  The watchdog reuses the WalletManager guardrail style (`agent/wallet_manager.py`).

---

## 4. Execution — the only path that touches real money

```
Agent (mode = live) → PROPOSE trade
   → write an Approval Request row to Convex            (NOT a trade)
   → Web Push: "Agent 'CAKE-Watcher' wants to buy $4 CAKE — approve?"
   → operator taps Approve in the PWA
   → control-token → agent_commands → command_worker → twak swap
        (the EXISTING gated path — agent/command_worker.py + control token)

Agent (mode = paper) → sim fill against /core, NO on-chain tx,
   → logged to the agent's own paper ledger / agent_runs
```

**Invariant (hard):** the scored competition wallet's autonomy is never delegated to an LLM
agent. A user-Agent at most *asks*; the human (or the deterministic core) acts. This preserves
locked decision #1 and the drawdown-first score. Default mode for any trade-capable Agent is
**paper**; flipping to **live** only enables the *propose→approve* path, never auto-execution.

---

## 5. Co-pilot → Agent Console + Web Push

- The co-pilot is **promoted, not removed.** It becomes the **Agent Console** inside the PWA:
  the operator spawns agents in natural language ("make an agent that…"); the co-pilot turns
  that into an Agent record (name + allowed_tools + trigger + notify_policy); every Agent's
  updates stream into the same chat/feed.
- **Web Push replaces Telegram** (banned in India; was only ever one transport). Flow:
  Agent emits update → Convex → service-worker Web Push to the installed PWA **and** the
  in-app `web/src/views/NotificationsView.tsx` feed (the source of truth). The PWA already has
  `vite-plugin-pwa`; we add a push subscription + a VAPID-keyed send. Telegram (`agent/notify.py`)
  remains an **optional** extra pipe, not a dependency.

---

## 5.1 Specialized Agent collaboration (the depth play)

An Agent rarely wants one tool — it wants a **team that hands off**. Collaboration happens at
two levels, both orchestrated by the existing **LangGraph supervisor** (`agent/graph/supervisor.py`),
never by ad-hoc glue:

**Level 1 — tools collaborate inside one Agent run (handoff chain).**
The supervisor routes a goal through multiple Tier-A tools, each consuming the previous one's
typed output via the contracts in `agent/graph/contracts.py` (locked: standardized shapes,
`tier_of()`/`is_tier0()`). Canonical chains:

```
"is this a setup we should take?"
   Researcher (CMC: regime, funding/OI, social)
      → Historian (Upstash: have we lost on this setup before?)   [AvoidanceVerdict]
      → CoPilot  (Claude: synthesize a one-paragraph call)
      → [if live] Trade Proposer → approval request

"learn from what just happened"
   Reflector (post-trade lesson) → Historian (store + index)      [Reflection]
```

Each hop emits exactly one `AgentEvent` to the Activity Channel, capped by `MAX_HOPS`, wrapped
in `_emit_failure`. A failing Tier-1 tool degrades the chain (skips that input) but **never**
halts trading (failure matrix §9.3). The chain produces **one combined result + one visible
trace** the operator can expand in the cockpit (the existing "Neural Mesh" surface in
`web/src/views/AgentsView.tsx`).

**Level 2 — Agents consult Agents (delegation).**
A user Agent may name another Agent in its `allowed_tools` as a sub-agent (e.g. a "Daily Brief"
Agent that consults the "CAKE-Watcher" and "Macro-Researcher" Agents and merges their findings).
Delegation is one bounded hop, dedupe-guarded, and **cycle-protected** (an Agent cannot, directly
or transitively, call itself). Depth is capped (`MAX_DELEGATION_DEPTH`, small) so a fan-out can't
explode token spend.

**Collaboration is observable.** Every handoff and delegation writes to `agent_runs.tool_calls[]`
and emits an `AgentEvent`, so the cockpit shows *who called whom* — the multi-agent story is
demoed live, not just claimed.

## 6. Data model (Convex)

Extend the existing `spawned_agents` table (`convex/spawnedAgents.ts`) — additive only:

| field             | type                                   | notes |
|-------------------|----------------------------------------|-------|
| `name`            | string                                 | existing — user-renamable |
| `task_summary`    | string                                 | existing → repurpose as `goal` display |
| `goal`            | string                                 | the natural-language mandate |
| `allowed_tools`   | string[]                               | Agent-Tool names, and/or other agent ids for Level-2 delegation (§5.1) |
| `trigger`         | `{ kind: "schedule"\|"event", spec }`  | cadence or event key |
| `notify_policy`   | `{ webpush: bool, severity_min }`      | when to ping |
| `mode`            | `"paper"\|"live"`                      | default `paper` |
| `status`          | `"active"\|"idle"\|"archived"`         | existing |
| `last_activity_ms`| number                                 | existing — heartbeat |

New tables:
- `agent_runs` — `{ agent_id, started_ms, ended_ms, ok, summary, tool_calls[], emitted[] }`
- `approval_requests` — `{ agent_id, kind:"trade", payload, status:"pending"|"approved"|"rejected", created_ms, resolved_ms }`
- `push_subscriptions` — `{ endpoint, keys, created_ms }` (Web Push)

---

## 7. Component boundaries (isolation)

| Unit | Does | Depends on |
|------|------|-----------|
| `agent/agents/runner.py` | run one Agent: build tool-loop, cap hops, heartbeat, emit run record | copilot tool-loop, supervisor, ConvexBridge |
| `agent/agents/orchestrator.py` | Level-1 tool handoff chains + Level-2 delegation, cycle/depth guards (§5.1) | supervisor, contracts, registry |
| `agent/agents/registry.py` | CRUD over `spawned_agents` from the runtime side | ConvexBridge |
| `agent/agents/watchdog.py` | flag silent / stalled Agents | `spawned_agents`, notify |
| `agent/push.py` | Web Push send (VAPID) | `push_subscriptions` |
| `convex/spawnedAgents.ts` (+`agentRuns.ts`,`approvals.ts`,`push.ts`) | reactive state for PWA | schema |
| co-pilot NL→record | parse "make an agent…" into a record | `copilot_agent.py` |
| PWA: Agent Console + builder | spawn/name/rename/approve UI | `AgentsView.tsx`, `CoPilotDrawer.tsx`, service worker |

Each is independently testable: the runner can be driven with a stub Convex; push can be
unit-tested against a fake subscription; the NL→record parse is a pure function over a string.

---

## 8. Scope — phased full build

The operator wants the **full** feature, including collaboration. We phase it so the
safety-critical pieces are correct by freeze and the depth lands through judging.

**Phase 1 — Foundation + safety (by Jun 21 freeze).**
1. Schema extension + `agent_runs`, `approval_requests`, `push_subscriptions`.
2. `agent/agents/` runtime: `runner.py` (bounded loop, heartbeat), `registry.py` (CRUD),
   `watchdog.py` (no-silent-failure).
3. Spawn/name/rename/archive via co-pilot (NL → Agent record), building on existing
   `convex/spawnedAgents.ts` create/list/setStatus.
4. **Template A — Market Watcher** end-to-end (monitor symbol + pattern → notify).
5. **Template B — Trade Proposer**: propose→approve through the existing control-token →
   `command_worker` → `twak swap` path; **paper by default**.
6. Web Push (VAPID subscribe + send) + Agent Console wiring of co-pilot.

**Phase 2 — Collaboration (post-freeze, before/within judging).**
7. Supervisor orchestration of **Level-1 tool handoff chains** (§5.1) with combined result +
   visible trace.
8. **Level-2 Agent→Agent delegation** with cycle + depth guards.
9. Two more templates that *require* collaboration: **Setup Scorer** (Researcher→Historian→CoPilot)
   and **Daily Brief** (delegates to multiple Agents).
10. Cockpit "Neural Mesh" upgrade: live who-called-whom graph from `agent_runs`.

**Phase 3 — Autonomy + polish (stretch, judging window).**
11. Separate funded wallet option for a fully-autonomous live Agent (scored wallet stays isolated).
12. Visual agent builder (allowed-tools picker, trigger editor).
13. Telegram restored as an optional secondary pipe.

---

## 9. Testing

- **Unit:** NL→Agent-record parse; watchdog silence detection; push payload build; approval
  state machine (pending→approved→command emitted).
- **Integration:** Market Watcher run against a stubbed CMC tool → emits one notification;
  Trade Proposer live-mode → writes an `approval_requests` row and **no** tx; approve →
  exactly one `agent_commands` row through the control-token gate.
- **Collaboration:** a Level-1 chain (Researcher→Historian→CoPilot) over stubbed tools produces
  one combined result + an ordered `tool_calls[]` trace; a degraded tool (raises) skips its input
  and the chain still completes. Level-2 delegation rejects a cycle (A→B→A) and stops at
  `MAX_DELEGATION_DEPTH`.
- **Safety assertion (must pass):** in no test path does a spawned Agent write a `twak swap`
  without a prior human `approved` transition. This is the scored-wallet invariant (§4).

---

## 10. Locked-decision compliance

- LLM off the hot path ✔ (Agents are Tier-1, propose-only).
- Sim/live share `/core` ✔ (paper mode runs `/core`, no fork).
- Convex is the bus ✔ (no new webhook server; Web Push send is a Convex-triggered call).
- Control-token gate ✔ (every real trade still passes through it).
- No raw keys ✔ (execution still via TWAK).
