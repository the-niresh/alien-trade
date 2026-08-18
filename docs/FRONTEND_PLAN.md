# Alien-Trade - Frontend Plan (ideation, Jun 8 2026)

Companion to `STEPS.md`. Captures the frontend direction agreed in the Jun 8
session. Build starts after the wallets are funded. Local-only (no public
deploy); Convex cloud stays the backend bus (Option A).

> **Backend contracts live in `AGENT_TEAM_PLAN.md` (§7).** This doc owns
> *rendering*; that doc owns the *data shapes* the UI reads. Reconciliations:
> the agent chatter renders from the append-only **`agent_events`** stream
> (the roster's `agent_activity` is a *derived* "latest per agent" view, not a
> second write path); the kill switch + per-agent pause write the
> **`agent_control`** doc (`paused_agents[]` / `agents_paused` / `trading_halted`);
> the agent chat panel is **read-only** (the user watches the team; the co-pilot
> in §5 is the only two-way surface).

---

## 1. Connection model - the browser never talks to the agent's port

```
Browser (localhost:5173, Vite PWA)
   │  ConvexReactClient(VITE_CONVEX_URL)   ← subscribes, live push
   ▼
Convex cloud (festive-newt-1)              ← the ONLY seam (locked decision #5)
   ▲
   │  HTTP writes (agent/convex_bridge.py)
Agent (terminal / localhost:8000 FastAPI)
```

- The Vite port only serves the static UI; **all live data flows through Convex cloud**, not the agent's port.
- Bring-up locally: set `web/.env.local` → `VITE_CONVEX_URL=https://festive-newt-1.convex.cloud`, then `cd web && npm install && npm run dev`. Run the agent in another terminal (writes Convex). Phone on same Wi-Fi installs the PWA via the terminal QR (`agent/qr.py`, vite `host:true`).
- **Option A confirmed:** local now; the subscription/sync future just swaps the QR target to a hosted URL - no rewrite. (Option B - offline-local store + cloud sync - was rejected: it forces SQLite+IndexedDB+sync adapter and re-introduces the agent↔browser bridge Convex gives for free.)

## 2. Controlling the agent from the UI (all via Convex flags the agent obeys)

Control = write a Convex row the agent reads at the top of each cycle. No terminal socket.

- **Kill switch** (exists) - prominent, confirm-gated, unmistakable state.
- **Risk caps as live sliders** - max position / daily-loss / slippage / max-exposure / consecutive-losses → write `config`, applies next cycle (show that hint). Needs `config.setCaps` mutation.
- **Mode toggle** paper / testnet / mainnet - mainnet behind a double-confirm.
- **Trigger buttons** - "Run research now", "Run one cycle", "Reconcile", "Explain last decision".
- **Per-agent pause/resume** - disable research/reflection sub-agents individually.
- **Live log console pane** - stream the structured `jlog` JSON (`agent/observability.py`) into a read-only terminal widget. This is the literal "watch the terminal from the UI" and reads as serious ops software.

## 3. Agent selector + roster (animated - the demo centerpiece)

One component does double duty: pick who you're talking to + show what each agent is doing. Agents = the supervisor sub-agents (Core decision · Reflection/Hermes · Research/Karpathy · Co-pilot).

- **Orbiting hub:** agent glyphs gently orbit a central supervisor node; the active one breaks orbit and docks into the prompt input as a pill. It's the architecture, animated.
- **Motion = state, not decoration:** idle = slow breathing pulse; running = rotating ring/waveform; just-finished = pop + checkmark. Status is readable from movement.
- **Routing animation:** on send, prompt text flies to the chosen agent's glyph → it "thinks" (shimmer) → answer **streams token-by-token** back (terminal typewriter).
- **Identity system:** each agent a distinct color + sigil, consistent across orbit, roster cards, chat bubbles. Core gets a different *shape* (it's the deterministic rules engine, not an LLM).
- Tech: **Framer Motion**; `@`-mention parsing in the input; respect `prefers-reduced-motion`.
- Backend: the roster reads a **derived "latest per agent"** view over the
  `agent_events` stream (see `AGENT_TEAM_PLAN.md` §7) - `{agent, status,
  last_run_ms, summary}` per agent - *not* a separate hand-written table, so the
  chat timeline and the roster never drift. Extends cleanly to multiple trading
  agents later (multi-wallet).

## 4. Polish system

- Animated count-up on PnL; sparklines that draw in; spring physics (not linear); skeleton shimmers.
- A persistent subtle **heartbeat** that ticks each cycle - app feels alive even when idle.
- Mission-control dark theme (`#0b0f17` set); glass cards; faint grid; accent **glows green on a win**.
- Optional ambient **sound** (off by default, toggle): chime on win, tick on decision.
- Premium = restraint: negative space, one accent, crisp type, real-time everything, zero jank, considered empty/loading/error states.

## 5. Prompt input + co-pilot

- Chat box → the co-pilot (`agent/secondbrain/copilot.py`, already built, grounded in the Second Brain).
- Flow: input → Convex **action** `copilot.ask` → proxies to agent (or Anthropic) → `{answer, sources}` → render. Persist the thread in a `copilot_messages` Convex table (syncs across devices - Option A).
- **GUARDRAIL (load-bearing):** the prompt is an *ask / explain / trigger* channel, NOT a *command-the-trade* channel. It can answer "why did we skip that?", run research, or nudge caps - it must **never** route into the signal/trade path. Trades stay deterministic in `/core` (locked decision #1). Protects Track-1 integrity.

## 6. Testnet wins feed (nearly free - data already exists)

- `reflections` already labels `win`/`loss` and has a `byOutcome` query; `trades` has `mode`; `ledger` has realized PnL.
- "Testnet wins" feed = reflections where `outcome_label == "win"` (filter testnet) → card shows setup + realized PnL + the lesson Hermes wrote. Doubles as judge/social proof.
- Add `mode` to the reflection row for a clean filter.

## 7. UX psychology (notes)

- **Lazy = low friction:** glanceable single-color status (calm/attention/danger); PWA push only on events that matter (kill, drawdown breach, big win); one-tap actions; safe defaults; set-and-forget + kill switch.
- **Happy / dopamine:** surface **loss-avoidance** ("Skipped a setup we lost on twice") - loss aversion lands harder than wins; agent narrates in plain language ("Sitting out - chop regime, protecting capital"); wins feed with restrained confetti; streaks ("3 green days").
- **Secure (and true):** self-custody badge ("Keys never leave your device - Trust Wallet"); drawdown as the hero metric; "every decision logged" + audit stream; "simulated before every trade · blocked N risky trades" counters.

## 8. Backend glue still needed (all small, all through Convex)

- `copilot.ask` action + `copilot_messages` table.
- `agent_events` append-only stream (+ `emit_event` helper) + a "latest per agent" query for the roster; heartbeat ticks as `agent_events` rows. (Schema in `AGENT_TEAM_PLAN.md` §7.)
- `agent_control` doc (kill switch / pause-all / per-agent pause / stop-response) - the single user-writable control surface.
- `mode` field on `reflections` + a wins query.
- `ledger.history` query (equity/drawdown chart).
- `config.setCaps` mutation (risk-cap sliders).
- Everything else (co-pilot, reflections, research digests, telemetry) already exists - UI just surfaces it.

## 9. Stack

shadcn/ui + Tailwind + Framer Motion + recharts (charts) + vite-plugin-pwa (configured). Current `web/` is a single plain-CSS component - upgrade to the above. Web + mobile only (PWA = the mobile app; Capacitor wrapper later if native is ever truly needed). **No desktop app.**

## 10. Judge-impress demo moments (spend polish here)

1. Kill switch from phone → agent halts within one cycle (control + safety, live).
2. Co-pilot: "Why did you skip that pump?" → grounded answer citing the exact past loss (proof it learns; CMC + Hermes).
3. Drawdown line flat while PnL climbs (risk-adjusted).
4. "$X saved vs naive Opus" telemetry (efficiency flex).
5. Self-custody + audit trail on screen (TWAK/BNB prize hooks).

## 11. Out of scope / deferred (decisions)

- **Browser extension - NO** (now and future). It wouldn't change how it connects (still via Convex), adds store/MV3/security cost for zero capability the PWA lacks, and needing a passkey→Convex→browser sync of all account/trade details doesn't make traders lazy - it's just another process. Park it.
- **Multitenant SaaS / per-user agents - NO** for the hackathon. One agent per user; multiple wallets *maybe* later.
- **Desktop app - NO.** Web + mobile (PWA) only.
- **Option B (offline-local backend) - deferred.** Convex cloud stays the bus.

## 12. Suggested build sequence (post-funding)

1. Tailwind/shadcn shell + theme + layout.
2. Prompt → co-pilot (Convex `copilot.ask` action + `copilot_messages`) + **animated agent roster/selector** (the centerpiece).
3. Testnet-wins feed + equity/drawdown chart (`ledger.history`).
4. Risk-cap sliders (`config.setCaps`) + mode toggle + live log console.
5. Polish pass: count-ups, heartbeat, win animation, push notifications, reduced-motion.
