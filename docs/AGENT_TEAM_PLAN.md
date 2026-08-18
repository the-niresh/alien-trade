# Agent Team Plan — Alien-Trade

> How many agents we have, what each one is, how they form a team, and who is the
> single point of contact for the user. Grounded in the code that already exists
> (`agent/`, `core/`, `agent/secondbrain/`) and the project's locked architectural decisions.

---

## 0. The one rule that shapes everything

Two locked architectural decisions (#1 and #6) govern this whole design:

1. **The LLM is OFF the trade hot path.** The buy/sell + size decision is
   deterministic Python in `/core`. No LLM picks an order. Ever.
2. **The supervisor/agents are for the Second-Brain (advisory/learning) layer only.**
   None of the LLM agents make the buy/sell decision.

So "a team of agents" here does **not** mean "a swarm of LLMs voting on trades."
It means **one orchestrator coordinating a set of specialists**, where the
specialists split into two tiers:

```
                          ┌─────────────────────────────┐
   USER  ───────────────► │   ORCHESTRATOR (the POC)    │  ◄── single point of contact
                          │   LangGraph supervisor       │
                          └──────────────┬──────────────┘
                                         │ routes / schedules / explains
            ┌────────────────────────────┼────────────────────────────┐
            ▼                            ▼                             ▼
   ── TIER 1: ADVISORY (LLM, off hot path, async) ──────────────────────────────
   History Checker     Future Predictor       (+ Reflection, Co-pilot)
   (Hermes memory)     (AutoResearch)
            │                            │
            │ writes memory / digests    │ writes digests
            ▼                            ▼
   ── TIER 0: DECISION (deterministic Python, the hot path) ─────────────────────
   Pattern Recognizer ──► Risk Manager ──► Trade Handler
   (regime + signals)     (hard caps)      (sim→sign→send→confirm)
                                                  │
                                                  ▼
                                            on-chain fill (TWAK)
```

Tier 0 is where money moves; it is deterministic, testable, and identical in sim
and live (locked decision #2). Tier 1 makes Tier 0 *smarter over time* without
ever touching the decision math — it feeds memory and research that Tier 0 reads
through a narrow, deterministic seam (`agent/brain.py`).

**"Specialized kings, not just specialists":** every agent below gets its own
mission, its own tool belt, its own slice of memory, its own success metric, and
an explicit *contract* of what it must never do. None of them is a thin wrapper.

---

## 1. The roster — 7 agents

| # | Your name        | Our agent              | Tier | Lives in (code)                         | LLM? |
|---|------------------|------------------------|------|-----------------------------------------|------|
| 1 | Orchestrator     | **Supervisor**         | —    | `agent/graph/` (to build)               | yes (routing/chat) |
| 2 | History checker  | **Historian** (Hermes) | 1    | `agent/secondbrain/avoidance.py` + `reflection.py` | yes (lesson synth, off path) |
| 3 | Pattern recognizer | **Strategist**       | 0    | `core/backtest/regime.py` + `core/strategy/` | no (deterministic) |
| 4 | Future predictor | **Researcher** (AutoResearch) | 1 | `agent/secondbrain/research.py`         | yes |
| 5 | Risk manager     | **Risk Officer**       | 0    | `core/risk/` (RiskEngine)               | no (deterministic) |
| 6 | Trade handler    | **Executor**           | 0    | `agent/loop.py` + `agent/executor.py`   | no (deterministic) |
| 7 | (implicit)       | **Reflector + Co-pilot** | 1  | `agent/secondbrain/reflection.py` + `copilot.py` | yes |

Count: **7 named roles** (Orchestrator + 6 specialists). The Reflector/Co-pilot
pair is bundled with the Historian as the "learning + chat" surface, so you can
also count it as **5 distinct specialists under 1 orchestrator** — same team,
different granularity.

Most of this already exists. The missing piece is the **orchestrator graph**
(`agent/graph/` is currently empty) that turns these modules into an explicit,
single-POC team.

---

## 2. Each agent as a "specialized king"

Each spec: **Mission → Inputs → Tools → Outputs → Memory → Autonomy → Success
metric → NEVER.**

### 1. Orchestrator (Supervisor) — the single POC

- **Mission:** the only thing the user talks to. Owns the conversation, routes
  every request to the right specialist, schedules the async agents, and merges
  their outputs into one coherent answer or action. Nothing reaches the user
  except through here.
- **Inputs:** user messages (co-pilot chat), system events (cycle done, position
  closed, kill-switch), schedule ticks.
- **Tools:** the other 6 agents (as graph nodes / tool calls), Convex live state,
  the CMC MCP server, the co-pilot retriever.
- **Outputs:** user-facing answers; dispatch commands to sub-agents; halt/resume.
- **Memory:** conversation state + pointers into the Second Brain (does not store
  its own facts; it routes to whoever owns them).
- **Autonomy:** decides *who* runs and *when* (e.g. "spawn Researcher every N
  hours", "on position close, run Reflector"). It does **not** decide trades.
- **Success metric:** every user question answered with cited sources; every
  async agent fired on schedule; zero direct user contact with sub-agents.
- **NEVER:** size or place a trade; override a risk cap; answer about money
  without grounding in Convex/Vector.
- **Build home:** `agent/graph/supervisor.py` (LangGraph `StateGraph`). The hot
  path (`agent/loop.py`) runs underneath it, not inside it.

### 2. Historian (History Checker / Hermes) — Tier 1

- **Mission:** institutional memory. Two halves of one loop:
  - **Write (post-trade):** compress every closed trade into a one-line lesson
    `{signals, regime, outcome, lesson}` and store it (Vector + Convex).
  - **Read (pre-trade):** "have we lost on this exact setup before?" → returns a
    verdict that can **block or shrink** an order.
- **Inputs:** closed-trade record (write); current `{regime, dominant signal,
  side}` setup key (read).
- **Tools:** Upstash Vector (semantic recall by setup key), Convex `reflections`
  + `audit`, cheapest LLM tier for lesson synthesis (falls back to rule-based
  offline).
- **Outputs:** `AvoidanceVerdict{block, size_penalty, reason}` consumed by the
  hot path through `agent/brain.py`.
- **Memory:** owns `kind="reflection"` and `kind="institutional"` (the 2-year
  pre-load) namespaces.
- **Autonomy:** self-decides what lesson to record and how to phrase the setup
  fingerprint so write and read land in the same vector neighborhood.
- **Success metric:** repeat-mistake rate trends down; verdicts demonstrably
  avoid setups that previously lost (measure on walk-forward).
- **NEVER:** invent a trade; the *only* way it touches the hot path is the
  block/shrink verdict — it can veto/reduce, it cannot create or enlarge.
- **Status:** built (`avoidance.py`, `reflection.py`); seam is `brain.py`.

### 3. Strategist (Pattern Recognizer) — Tier 0, deterministic

- **Mission:** read the market's current *shape* — detect regime (trend / chop /
  high-vol) and compute the orthogonal signal stack (S1 momentum, S2
  derivatives, S3 sentiment, S4 flow) into a single deterministic score.
- **Inputs:** point-in-time OHLCV + funding/OI + social + flow (same data sim and
  live both see).
- **Tools:** `core/backtest/regime.py`, `core/signals/`, `core/strategy/combined.py`.
- **Outputs:** `{regime, signal breakdown, combined score}` → handed to the Risk
  Officer.
- **Memory:** stateless per bar (uses only point-in-time history — that's the
  sim/live parity guarantee). An LLM *narrative* may describe the regime **after**
  detection, but the detection itself is pure math.
- **Autonomy:** none beyond the math — determinism is the feature.
- **Success metric:** out-of-sample Sortino − λ·max-drawdown (locked objective #6);
  signals stay orthogonal; ≤3 signals (anti-overfit).
- **NEVER:** call an LLM inside the score computation; use look-ahead data; exceed
  3 signals without an OOS Sortino improvement.
- **Status:** built in `/core`.

### 4. Researcher (Future Predictor / AutoResearch) — Tier 1

- **Mission:** Karpathy AutoResearch loop. Self-directs: inspects the market,
  decides what it *doesn't understand* (regime anomalies, social spikes,
  OI/price divergence), gathers data, synthesizes a "market research digest",
  and stores it for the Strategist's narrative and the Co-pilot to read.
- **Inputs:** live CMC quotes + recent bars + on-chain flow (via CMC MCP).
- **Tools:** CMC MCP server, Upstash Vector, LLM (digest synthesis).
- **Outputs:** `ResearchDigest{question, findings, tags}` → `kind="research"`.
- **Memory:** owns the `kind="research"` namespace.
- **Autonomy:** **highest of any agent** — it picks its own research questions
  every N hours, unsupervised. This is the "king" of curiosity.
- **Success metric:** digests that later prove predictive (tagged + scored
  against subsequent regime/outcome); coverage of anomalies before they bite.
- **NEVER (important):** size, time, or place a trade. It *forecasts and
  explains*; it is **advisory only**. See the open question in §6 — if you want
  its forecast to actually nudge sizing, that is a deliberate change to locked
  decision #1 and must be explicitly approved.
- **Status:** built (`research.py`); needs CMC MCP wired as a live tool +
  scheduling under the supervisor.

### 5. Risk Officer (Risk Manager) — Tier 0, deterministic

- **Mission:** the hard guardrail. Takes the Strategist's intended order and
  enforces caps: position size, max exposure, leverage ceiling (≤2x,
  regime-gated), daily-loss limit, drawdown kill-switch.
- **Inputs:** intended order + live ledger state (PnL, drawdown, open exposure).
- **Tools:** `core/risk/` RiskEngine; reads `agent/ledger.py`.
- **Outputs:** a risk-clamped order (or a flat/halt) → handed to the Trade Handler.
- **Memory:** current risk state (exposure, daily loss) in Convex `risk_state`.
- **Autonomy:** none — caps are fixed config, deliberately not "smart". An LLM
  may *explain* a clamp to the user (via Orchestrator) but cannot soften it.
- **Success metric:** drawdown stays under the configured ceiling across the live
  window; zero cap breaches in the audit log.
- **NEVER:** let any agent (including the Historian's verdict) *increase* size or
  leverage; the Historian can only shrink, the Risk Officer can only clamp down.
- **Status:** built in `/core`; wrapped around the strategy via `make_strategy` +
  `RiskEngine` (the same wrap sim and live use).

### 6. Trade Handler (Executor) — Tier 0, deterministic

- **Mission:** turn an approved order into a confirmed on-chain fill, safely and
  idempotently. The "simulate → sign → send → confirm → reconcile" specialist.
- **Inputs:** risk-clamped order + Historian verdict.
- **Tools:** `agent/executor.py` (`TwakSwapExecutor` self-custody live /
  `PaperExecutor` sim), `twak_cli.py` (signing on-device, keys never in code),
  BNB SDK path, Convex bridge, ledger reconciler.
- **Outputs:** `ExecutionReport` (real fill price + real gas) → ledger + Convex
  decision/trade/audit rows. On-chain receipt is the source of truth.
- **Memory:** idempotency set + ledger, rebuildable from the Convex event log on
  crash (`recovery.py`).
- **Autonomy:** none on *what* to trade; full ownership of *how* to execute
  (slippage cap, simulate-before-send, retry/dead-letter, dedupe).
- **Success metric:** zero double-trades, zero unconfirmed sends, fills within
  the slippage cap, every cycle writes exactly one decision row.
- **NEVER:** place an order that didn't pass Risk Officer + Historian; hold a raw
  key; send without a simulate step.
- **Status:** built (`loop.py`, `executor.py`, `twak_cli.py`, `recovery.py`).

### 7. Reflector + Co-pilot — Tier 1 (the learning + chat surface)

- **Reflector:** the write trigger for the Historian — fires on position close,
  produces the lesson. (Same module family; listed separately because it's
  *event-driven* where the Historian's read side is *pre-trade*.)
- **Co-pilot:** grounded Q&A. Answers "why this trade?", "what regime are we
  in?", "what did 2 years teach us about this setup?" using **only** retrieved
  memory + live Convex state, with citations. This is the mouth of the
  Orchestrator to the user.
- **NEVER:** answer ungrounded; touch the hot path.
- **Status:** built (`reflection.py`, `copilot.py`).

---

## 3. How they work as a team (the protocol)

Two shared buses, no direct agent-to-agent coupling:

- **Convex** = the live state + audit bus. Decisions, trades, ledger, risk_state,
  reflections, kill-switch. "If it's not in Convex, it didn't happen."
- **Upstash Vector** = the long-term memory bus. Three namespaces: `reflection`,
  `institutional`, `research`. Agents write/read by *setup key*, never by direct
  call.

This means agents are **decoupled**: the Historian doesn't call the Researcher;
they both write Vector, and the Strategist/Co-pilot read it. The Orchestrator is
the only component that calls agents directly.

### One live cycle (the hot path, deterministic)

```
feed → kill-switch check
     → Strategist (regime + signals + score)
     → Risk Officer (clamp to caps)
     → Historian.read (block / shrink?)        ← only veto/reduce allowed
     → Trade Handler (simulate → sign → send → confirm)
     → ledger reconcile → Convex rows
     → on close: Reflector → Historian.write (lesson → Vector + Convex)
```

This is exactly `agent/loop.py` today. The team additions are around it, not
inside it.

### The async/advisory layer (off the hot path)

```
Orchestrator schedule tick (every N hours)
     → Researcher: identify unknowns → CMC MCP fetch → digest → Vector(research)

User question
     → Orchestrator → Co-pilot: retrieve(reflection+institutional+research)
                              + live Convex state → grounded answer w/ citations
```

---

## 4. What exists vs what to build

| Piece | Status | Work to do |
|-------|--------|-----------|
| Tier-0 hot path (Strategist, Risk Officer, Trade Handler) | ✅ built | none — it's the proven `/core` + `loop.py` |
| Historian (read+write), Reflector, Co-pilot, Researcher | ✅ built | none for logic; needs wiring under supervisor |
| Mistake-avoidance seam (`brain.py`) | ✅ built | swap `AllowAll` for the Vector-backed Historian in live |
| 2-year institutional pre-load | spec'd | run the ingestion once before go-live |
| **Orchestrator graph** (`agent/graph/`) | ❌ empty | **build this** — see below |
| CMC MCP as a live LangGraph tool | partial | wire MCP into Researcher + Co-pilot |

### The one real build: `agent/graph/supervisor.py`

A LangGraph `StateGraph` that:
1. Exposes a **single entry** the user/PWA talks to (chat + commands).
2. Has nodes: `co_pilot`, `researcher`, `reflector`, `historian` (advisory only).
3. **Does not** wrap the hot path — the hot path stays in `loop.py` and runs
   on its own cadence (Trigger.dev). The supervisor *observes* it via Convex and
   *reacts* (e.g. on `position_closed` event → run Reflector).
4. Routing rules: user question → co_pilot; schedule tick → researcher; trade
   close event → reflector → historian.write.

This is the only net-new component. Everything else is assembly.

---

## 5. Build order (fits existing phases)

1. **Scaffold `agent/graph/supervisor.py`** — LangGraph StateGraph, nodes wired
   to the existing secondbrain modules. Single chat entry. (Phase 6.)
2. **Flip `brain.py`** from `AllowAll` to the Vector-backed Historian in the live
   loop. (Phase 6.)
3. **Wire CMC MCP** as a tool for Researcher + Co-pilot. (Phase 6.)
4. **Schedule the Researcher** via Trigger.dev under the supervisor (every N hrs).
5. **Run the 2-year pre-load** once, populate `kind="institutional"`. (Phase 7.)
6. **Paper rehearsal** with the full team live end-to-end. (Phase 7.)

Run each piece once and verify it's alive before stacking the next (per project
convention).

---

## 6. LOCKED: Option B — the deterministic forecast bridge

**Decision (confirmed):** the Researcher's forecast gets *teeth*, but only
through a deterministic, bounded, audited bridge. No LLM ever enters the order
math; the forecast can **only shrink** size, never enlarge it. Same shape as the
Historian's veto — a one-way safety valve.

### How it works

1. **Researcher** produces, alongside each digest, a single deterministic number:
   `forecast_confidence ∈ [0, 1]` for the current setup (e.g. "0.3 = I expect a
   regime flip against this trade soon"). The *number* is what crosses the
   boundary — the prose stays in the digest, off the hot path.
2. The number is written to a small Convex row (`forecast_state`) with a
   **timestamp and a decay**: a forecast older than `TTL` decays back to neutral
   (1.0 = no opinion), so a stale prediction can never silently throttle trading.
3. The **Risk Officer** reads it as a bounded multiplier on size:
   `size *= clamp(forecast_confidence, FLOOR, 1.0)` — `FLOOR` (e.g. 0.5) caps how
   much a forecast can shrink a position. It can **never** push the factor above
   1.0. Pure arithmetic, fully testable, identical in sim and live.

### Why this is safe (the invariants it keeps)

- **Locked #1 holds:** no LLM in the decision. A *deterministic float* crosses the
  line, clamped on both ends.
- **Locked #2 holds:** sim and live both apply the same multiplier from the same
  `forecast_state` → parity tests still pass fill-for-fill.
- **Locked #6 (drawdown-first) holds:** the only thing a forecast can do is
  *de-risk*. The worst a bad forecast does is make us trade smaller. It can never
  cause a bigger loss than the deterministic core already allows.
- **Auditable:** every shrink writes the confidence, the decayed value, and the
  resulting factor to the audit log → the Activity Channel can show *"Researcher
  forecast 0.30 → size cut to 50%."*

### Build notes

- Lives in `core/risk/` (the multiplier) + a `forecast_state` Convex table.
- The Researcher's confidence extraction must itself be deterministic given its
  inputs (rule-based mapping from digest tags / signal divergence), so the bridge
  number is reproducible — the LLM prose is decoration, not the source of the
  number where it matters for parity. (If we ever let the LLM emit the float
  directly, it must be snapshotted to `forecast_state` so sim/live replay the
  exact same value.)

---

## 7. The Agent Activity Channel — the "glass cockpit"

**Decision:** the user gets a live, low-latency channel showing what the agents
are doing — the chatter, the history they pulled, the analyzed list, the verdicts.
This is both the headline marketing surface ("watch a team of specialist agents
reason in real time") **and**, conveniently, our audit trail rendered for humans.
Two birds: the thing that sells the demo is the same thing that proves the agent
is honest.

> **Relationship to `FRONTEND_PLAN.md` (read this — the two docs split here):**
> This section owns the **backend data contracts** (`agent_events`,
> `forecast_state`, `agent_control`). `FRONTEND_PLAN.md` owns the **rendering** —
> the animated roster/orbit (§3), the read-only log console (§2), the co-pilot
> chat (§5), and the build sequence (§12). Don't redefine the UI here or the data
> shapes there. Two reconciliations from the earlier FRONTEND_PLAN draft:
> - **Tables:** `agent_events` (this doc) is the single append-only write — the
>   chat timeline + audit. FRONTEND_PLAN's `agent_activity` becomes a *derived*
>   "latest row per agent" view for the roster cards; no separate hand-written
>   status writes (one write path, no drift).
> - **Controls:** FRONTEND_PLAN's per-agent pause + kill switch are the same
>   surface as `agent_control` below — per-agent pause is the finer-grained form
>   of "Pause Agents". Risk-cap sliders / mode toggle stay on `config` (FRONTEND
>   §2), separate from the stop controls.

### What it is (and isn't)

- It **is** a real-time, append-only stream of structured **trace events**, one
  per meaningful agent action, rendered as a readable timeline / "conversation".
- It **is not** literal LLM-to-LLM chat. Our agents are decoupled through buses
  (Convex + Vector) by design — that's what makes them independently testable.
  The "conversation" is *narrated from real events*, so it's truthful, not theater.
  It reads like a conversation because each event is phrased in the agent's voice.

### Shape

A Convex table `agent_events` (reactive → the PWA subscribes, sub-second updates
for free, no websocket infra — locked decision: Convex is the real-time bus):

```
agent_events {
  cycle_id        // ties the whole team's actions to one decision
  ts              // ordering
  agent           // "Strategist" | "Risk Officer" | "Historian" | "Researcher" | ...
  kind            // "observation" | "analysis" | "verdict" | "action" | "handoff"
  headline        // one-line, agent's voice: "Historian: 3 past losses on this setup → shrink 30%"
  detail          // structured payload (the analyzed list, the history hits, the numbers)
  refs            // links to reflections / digests / on-chain receipt
}
```

Every agent emits to this table through one tiny helper (`emit_event`). Example
of one cycle as the user would see it:

```
Strategist   observation  Regime = TREND_UP. S1 +0.62, S2 −0.10, S4 +0.31 → score +0.71
Researcher   analysis     Forecast confidence 0.40 (OI/price divergence building)
Historian    analysis     Checked 142 past setups → 3 losses on TREND_UP+S1-dominant
Historian    verdict      Shrink 30% (prior losses on this exact setup)
Risk Officer verdict      Size 1.2 BNB → 0.84 (forecast 0.40 + historian 0.70, caps OK)
Trade Handler action      Simulated 0.84 BNB swap, slippage 0.12% → signed via TWAK → filled
Reflector    handoff      Position opened; will reflect on close
```

That timeline is the demo. It's also the audit log.

### Rendering: a read-only agent chat

The channel is rendered in the PWA as a **chat interface** — each `agent_events`
row is a bubble in the agent's voice, grouped by `cycle_id` into "conversations".
The user has **read-only access**: they watch the team think, but cannot inject
messages into the agent stream.

Two surfaces, kept distinct (don't confuse them):

| Surface | Direction | What it is |
|---------|-----------|-----------|
| **Agent Channel** (this) | read-only | the team's real-time chatter / trace, grouped by cycle |
| **Co-pilot** (§2.7) | two-way | the user's own chat — ask "why this trade?"; grounded answers |

So the user *observes* the agents here and *talks* to the Co-pilot there. The
agent chatter is never something the user (or a prompt-injection) can write into —
that keeps the trace truthful and un-spoofable.

### User controls: three graduated stops (the only thing the user can write)

The channel shows stop controls. **Critical distinction — stopping the talking
agents is NOT the same as stopping trading**, so they are separate controls with
separate blast radius:

| Control | Stops | Effect on trading | Confirm? |
|---------|-------|-------------------|----------|
| **Stop response** (per-message ✕) | one in-flight agent action (like a chat "stop generating") | none | no |
| **Pause Agents** | the whole Tier-1 advisory team (Researcher, Dreamer, supervisor narration) | **none** — Tier-0 keeps trading deterministically; forecast decays to neutral per the failure matrix (§9.3) | no |
| **🛑 Kill Switch / Stop Trading** | the Tier-0 hot path — halts the trade loop | **stops all trading** (existing `/halt`) | **yes** (typed confirm) |

Design intent: the everyday button is **Pause Agents** — quiet the team without
touching positions. The **Kill Switch** is the big red, safety-critical control
(reuses the existing `agent/server.py /halt` + kill-switch), gated behind a
confirm so a curious tap can't flatten the book.

(FRONTEND_PLAN §2 also exposes **per-agent** pause/resume — the per-agent form of
"Pause Agents"; it lives in the same `agent_control` doc via `paused_agents[]`.)

**Mechanism (Convex bus, locked decision #5):** a single user-writable doc
`agent_control { stop_response_id?, agents_paused: bool, paused_agents: string[],
trading_halted: bool, updated_by, ts }`. The PWA is the *only* writer; the
supervisor and the DecisionLoop are reactive *readers*:

- supervisor checks `agents_paused` / `stop_response_id` at each node boundary →
  cooperative cancel (no orphaned LLM calls);
- the loop already reads the kill-switch each cycle → `trading_halted` maps onto it.

Every control action also writes an `agent_events` row — *"User paused the
agents"*, *"User triggered the kill switch"* — so the channel shows who stopped
what and when (auditable, and it reads naturally in the chat). Matching
**Resume** actions flip the flags back; trading resume stays confirm-gated.

### Latency stance (deferred, but designed-in)

- **Hot path stays lean:** agents emit *lightweight structured events* (no LLM
  call to write a trace). The human-readable `headline` is template-rendered from
  the structured fields — cheap, deterministic, zero added latency to the trade.
- Any "prettier" LLM narration is an **off-path** enrichment, applied after the
  fact, never blocking a decision.
- Convex reactive queries already give sub-second push to the PWA, so v1 is
  "low-latency enough" without extra work. We tune (batching, edge, partial
  hydration) **after** it works end-to-end — per your call.

---

## 8. Build order (updated)

0. **Contracts-first** (§9.2): `agent/graph/contracts.py` — every inter-agent
   payload + the failure matrix (§9.3) defined before any wiring.
1. **Convex schema:** add `agent_events` + `forecast_state` + `agent_control`
   (the single user-writable control doc) tables.
2. **`emit_event` helper** in `agent/` — every agent writes its trace through it.
3. **Option-B bridge** in `core/risk/` — the bounded forecast multiplier + tests
   (assert it can only shrink, never enlarge; assert decay-to-neutral; assert
   sim/live parity still holds).
4. **Researcher confidence output** — deterministic float + `forecast_state` write;
   fan-out across symbols (§9.1); self-eval gate (§9.5).
5. **Scaffold `agent/graph/supervisor.py`** — LangGraph StateGraph. **Start with 2
   nodes** (Co-pilot + Historian), prove graph + channel, then grow (§9.6).
6. **Flip `brain.py`** to the Vector-backed Historian (emits its verdict events,
   honors the failure matrix: defaults to `AllowAll` on error).
7. **PWA Activity Channel view** — read-only chat rendering of `agent_events`
   (grouped by `cycle_id`) + the three stop controls writing `agent_control`
   (Stop response / Pause Agents / Kill Switch, the last confirm-gated). Supervisor
   + loop read `agent_control` reactively for cooperative cancel.
8. **Dreamer** nightly job (§9.4) via Trigger.dev — consolidate memory + score
   prior forecasts.
9. **2-year pre-load (fan-out) + paper rehearsal** with the full team + channel live.

Free discipline to do now (no extra build): contracts-first (0), failure matrix
(§9.3), incremental supervisor (5). Additive features (lock design, build as time
allows): fan-out (§9.1), Dreamer (8), self-eval (§9.5).

(Latency optimization is explicitly *after* step 9.)

---

## 9. Multi-agent build principles (locked — from `harness/multi agents.pdf`)

The harness blog ("How to build multiple AI agents work together", Akash) was
reviewed and **validates this architecture** (specialist team, narrow roles,
off-path learning, parallelism). Five concrete upgrades are locked from it.

### 9.1 Name the patterns — and fan-out where it pays

The blog: every system is *pipeline* (ordered), *fan-out* (one job split into
parallel chunks), or *specialist team* (domains collaborate on one deliverable);
real systems combine them. Ours:

- **Hot path = pipeline:** Strategist → Risk Officer → Historian → Trade Handler.
  Ordered by necessity; deterministic; microseconds, not LLM latency.
- **Advisory layer = specialist team:** Historian / Researcher / Reflector /
  Co-pilot collaborate only through the buses (Convex + Vector), never direct calls.
- **Research + 2-yr preload = fan-out:** the Researcher analyzes many
  symbols/anomalies in parallel; the preload walks many periods in parallel.
  **Adopt:** parallelize these instead of looping one at a time.

### 9.2 Contracts-first (the single most important rule)

Blog: *"standardize output formats before building anything; if A outputs text and
B expects JSON the handoff silently fails and every downstream agent produces
garbage."* **Lock:** before the supervisor is wired, define every inter-agent
payload in one central, versioned place (`agent/graph/contracts.py`) — reusing the
existing typed dataclasses (`AvoidanceVerdict`, `ResearchDigest`, the
`agent_events` row, the new `forecast_state`). No agent emits an ad-hoc shape.

### 9.3 Explicit failure matrix (most important for trading)

Blog: define failure behavior explicitly — *"log the failure and continue with
historical data; do not halt the whole pipeline."* **Lock — the governing rule:
a Tier-1 (learning/advisory) agent failing must NEVER halt or distort a trade.**

| Agent | On failure | Effect on hot path |
|-------|-----------|--------------------|
| Researcher / CMC MCP | log to channel; `forecast_state` decays to neutral (1.0) | none — trades at full deterministic size |
| Historian read | log; verdict defaults to `AllowAll` (no veto) | none — core decision stands |
| Reflector / Dreamer | log; queue lesson for retry | none — off-path |
| Co-pilot | log; tell user "context unavailable" | none |
| Convex bridge | buffer locally; reconcile on reconnect (`recovery.py`) | none — ledger is source of truth |
| **Strategist / Risk Officer / Trade Handler (Tier 0)** | **halt that cycle, write audit, flip kill-switch if needed** | this is the only tier allowed to stop trading |

Every failure is a visible `agent_events` row, never a silent swallow.

### 9.4 The Dreamer — nightly consolidation ("dreaming")

Blog: a background process between sessions reviews past work, extracts patterns,
updates memory automatically (Harvey: **6x task completion, no new model**).
Today we reflect *per trade*; **add** a nightly **Dreamer** pass (a batch mode of
the Hermes/Reflector family, scheduled via Trigger.dev) that:

- reviews the whole day's trades + digests + outcomes together,
- extracts higher-order patterns a single-trade reflection can't see,
- dedupes/compresses memory and **scores yesterday's forecasts vs. what actually
  happened** (closes the Option-B feedback loop),
- writes a "nightly digest" to the channel.

Not a new decision-maker — same off-path learning family, batch cadence. Demo
hook: *"it dreams overnight and wakes up smarter."*

### 9.5 Output rubric / self-eval on Tier-1 agents

Blog: agents evaluate their own output against a rubric and iterate until it
passes, or **flag failure with a reason rather than silently delivering garbage.**
**Add** a lightweight self-check to each LLM agent (off-path, so no hot-path cost):

- Researcher: "is this digest specific + actionable?" else retry once, else tag low-confidence.
- Co-pilot: "is every claim grounded in a retrieved source?" else say so plainly.
- Reflector: "is the lesson one concrete, reusable rule?" else regenerate.

### 9.6 Discipline (start small, watch, grow)

- **Start the supervisor with 2 nodes, not 7.** Our agents are mostly pre-built
  and individually tested, but the *new orchestration* gets wired incrementally:
  Co-pilot + Historian first, prove the graph + channel, then add Researcher, then
  the Dreamer. (Build order §8 already reflects this.)
- **Monitor via the channel:** `agent_events` doubles as observability — track
  per-agent failure rate and which handoffs produce downstream errors.
- **Cost model:** keep LLM agents tier-routed + cached; only the deterministic
  pipeline is sequential, every LLM agent runs parallel/async off-path.

---

## 10. TL;DR

## 7. TL;DR

- **7 agents:** Orchestrator + Historian, Strategist, Researcher, Risk Officer,
  Trade Handler, Reflector/Co-pilot.
- **Orchestrator is the single POC** — the user only ever talks to it; everyone
  else is a level-2 specialist it coordinates.
- **Two tiers:** the trade decision (Strategist → Risk Officer → Trade Handler)
  is deterministic Python and stays that way; the LLM agents (Historian,
  Researcher, Reflector, Co-pilot) make it smarter over time without touching the
  decision.
- **Forecast has teeth (Option B):** the Researcher's prediction crosses into the
  decision only as a deterministic, decaying, clamped multiplier that can **only
  shrink** size — never an LLM in the math, never a bigger loss.
- **Glass cockpit:** a reactive `agent_events` channel streams the team's
  reasoning to the PWA as a **read-only agent chat** (the user watches, but talks
  to the Co-pilot separately) — the marketing headline *and* the audit log, same
  data. Latency tuning deferred until it works end-to-end.
- **Graduated stops:** three controls written via `agent_control` — *Stop
  response* (one action), *Pause Agents* (quiet the Tier-1 team, trading
  untouched), and the confirm-gated *Kill Switch* (halts trading). Pausing the
  agents ≠ stopping trading — separate buttons, separate blast radius.
- **Blog-validated (§9):** named patterns (pipeline + specialist-team + fan-out),
  contracts-first, an explicit failure matrix (Tier-1 failure never halts a trade),
  a nightly **Dreamer** consolidation pass, and Tier-1 self-eval rubrics.
- **~85% already built** — the new pieces are the supervisor graph
  (`agent/graph/`), the Option-B bridge (`core/risk/`), and the Activity Channel
  (`agent_events` + PWA view). The rest is assembly + the 2-year pre-load.
