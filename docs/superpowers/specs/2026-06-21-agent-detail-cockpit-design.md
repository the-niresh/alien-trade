# Agent Detail Cockpit + Chat-First Create — Design

**Date:** 2026-06-21
**Branch:** AT-2-awake-sprint-productization
**Status:** Approved (brainstorm) → ready for implementation plan

> **Freeze note:** Today (Jun 21) is the feature-freeze deadline. This design is
> deliberately **web-only** (React + Convex reads/existing mutations). It makes
> **zero changes to `core/` or the agent hot path**. The Configure tab writes only
> through *existing* token-gated config mutations.

---

## 1. Goal

Clicking any agent in the Agents tab opens a full-page detail cockpit with five
sections — **Dashboard, Trades, Scanning, Live Positions, Configure** — mirroring
the `docs/screenshots/start a trade *.png` layout (left sub-nav + section outlet).

The **+ New** button opens a fresh co-pilot chat thread pre-seeded with a guided
agent-creation template (chat-first create), replacing the current inline form.

Win-gate mapping: this is **productization depth** (a polished, honest cockpit that
shows the real risk-adjusted engine) — it protects the Track-1 score story and the
TWAK/CMC self-custody narrative for judging. Every Configure knob maps to the
drawdown-first objective. SOL-specific knobs and decorative controls are omitted.

## 2. Architecture decisions (locked in brainstorm)

1. **Data scope:** Real data for the **primary** live trader; honest lighter data
   for **spawned** assistant agents. No spawned agent ever displays PnL it didn't earn.
2. **Configure:** Winning knobs only, wired live to existing config mutations.
   No schema changes, no core changes.
3. **Presentation:** Full-page detail view with a left sub-nav + back button.
4. **Create flow:** Chat-first. Remove the inline `AgentBuilderPanel`.
5. **Primary card:** A pinned, distinct "Alien-Trade · contrarian" card at the top
   of the grid opens the real-data detail view.

## 3. Agent kinds

A discriminator drives every section's data source:

```ts
type AgentKind = "primary" | "spawned";
```

- **primary** — the single deterministic live trader (`alien-trade.service`,
  contrarian). Backed by the global Convex singletons (scorecard, trades,
  decisions, signals, positions, config). There is exactly one.
- **spawned** — rows in `spawned_agents`. Backed by `agent_runs` (tool-call
  traces) and `approval_requests`. They propose trades (approval-gated) and run
  tools on a schedule; they hold no positions and have no PnL of their own.

## 4. Components / files (all under `web/src/`)

```
views/AgentsView.tsx                       # rework: grid + pinned primary card +
                                           #   chat-first create; remove inline form
views/agent-detail/AgentDetailView.tsx     # shell: header + left sub-nav + outlet
views/agent-detail/DashboardSection.tsx
views/agent-detail/TradesSection.tsx
views/agent-detail/ScanningSection.tsx
views/agent-detail/LivePositionsSection.tsx
views/agent-detail/ConfigureSection.tsx
```

Each section is a small, focused file that takes `{ kind, agent }` and renders the
correct source. Reuse existing components rather than re-implement:
`EquityChart`, `RealizedPnlChart`, `Sparkline`, `StatCard`, `RegimeBadge`,
`SignalScores`, `PositionCard`, `RecentTrades`, `FearGreedGauge`.

### Detail shell (`AgentDetailView`)
- Header: agent name, status dot, mode badge, kill/pause control (primary only),
  **← Back** to grid.
- Left sub-nav: Dashboard · Trades · Scanning · Live Positions · Configure
  (local `section` state; default Dashboard).
- Co-pilot stays the existing `CoPilotDrawer` (Ctrl+K / button) — **not** a docked
  right panel — for consistency with the rest of the app. An "Open Chat" affordance
  in the header opens the drawer on this agent's thread (spawned) or a general
  thread (primary).

## 5. Section data sources

| Section | Primary (real) | Spawned (honest-light) |
|---|---|---|
| **Dashboard** | `scorecard.get` (Realized PnL, Open Exposure, Win Rate, Trades, Max Drawdown, Sortino) + equity sparkline + latest `decisions.latest` narrative ("AI Insights") | run stats from `agentRuns.recent`: # runs, last ok/fail, avg tools/run, last activity |
| **Trades** | `trades.recent` table | `approvals.listPending` filtered to this agent + note: "assistant agents propose, don't execute" |
| **Scanning** | `decisions.recent` + `SignalScores` (what it evaluates each cycle) | `agent_runs` tool-call traces (expanded chain view) |
| **Live Positions** | `positions.open` via `PositionCard` | empty state: "Assistant agents hold no positions." |
| **Configure** | live risk knobs (§6) | goal / allowed_tools / trigger / mode / notify editor (needs new `spawnedAgents.update` mutation — see §6.1) |

## 6. Configure — winning knobs (primary), wired live

All through **existing** token-gated mutations (`withToken`):

| Knob | Field | Mutation |
|---|---|---|
| Per-trade size (USD) | `max_position_usd` | `config.updateLimits` |
| Daily loss limit (USD) | `daily_loss_limit_usd` | `config.updateLimits` |
| Max drawdown % | `max_drawdown_pct` | `config.updateLimits` |
| Equity floor (USD) | `equity_floor` | `config.updateLimits` |
| Token allowlist | `token_allowlist` | `config.updateLimits` |
| Strategy | `strategy_name` | `config.setStrategy` |
| Trading mode | `trading_mode` | `config.setTradingMode` |
| Autopilot profit-lock (optional) | `autopilot` | `config.setAutopilot` |

UX: an **"Unsaved"** indicator + Save button (like `configure.md`). Save is
token-gated; a missing/invalid token shows a toast (reuse existing pattern).
Disable Save while in flight.

### 6.1 Spawned-agent Configure (new Convex mutation)

Editing a spawned agent's goal / allowed_tools / trigger / mode / notify_policy
needs a single new mutation `spawnedAgents.update` (patches the row by id).
This is a **Convex function only** — not `core/`, not the trading hot path — so it
stays within the freeze boundary. Reuse `rename` / `setStatus` for those fields.

**Omitted (win-gate "no" / freeze-safe):**
- Every SOL-specific gate: bonding-curve %, dev holding, dev-dump tripwire, Jito
  tip, mint checks, holder/wallet wash gates. Irrelevant to BSC spot-long-only.
- Live slippage / max-open-exposure knobs. These are enforced by
  `core/risk/guardrails.py` (`max_slippage_pct`, `max_open_exposure_pct`) but are
  **not** in the Convex `config` table. Making them tunable would require a schema
  + bridge + core read change on freeze day — out of scope. (May appear as a
  read-only "enforced by risk engine" line if it adds clarity, but no inert knobs.)

## 7. + New — chat-first create

1. Remove `AgentBuilderPanel` from `AgentsView`.
2. **+ New** → `copilot.createThread({ title: "New agent" })`.
3. Set that thread as the active co-pilot thread, set a guided **creation-template
   prefill** (name → goal → tools → cadence → mode), and open `CoPilotDrawer`.
4. The co-pilot's existing spawn/create path performs the actual
   `spawned_agents` insert. (Implementation step verifies the create_agent path;
   if the co-pilot cannot yet insert, the template gathers the spec and calls the
   existing spawn action — no new backend surface beyond what exists.)

The template is a single seed message that frames the conversation, e.g.:

> "Let's create a new agent. Tell me: (1) a short name, (2) the goal in one line,
> (3) which tools it may use, (4) how often it runs, (5) paper or live. I'll set it
> up and spawn it for you."

## 8. Error handling

- Token-gated writes reuse `withToken`; invalid/missing token → toast, no silent
  failure.
- Save buttons disabled while saving; "Unsaved" badge clears on success.
- Empty states for spawned Trades (no pending approvals) and Live Positions.
- Detail view wrapped by the existing `ErrorBoundary` / `ViewError` already around
  `renderView` in `App.tsx` (detail renders inside `AgentsView`, so it inherits it).

## 9. Testing

- `web` has no unit-test harness configured. Verify with:
  - `tsc` typecheck (no type errors).
  - Production build succeeds.
  - **Manual screenshot from the operator** (per project preference: do not spin up
    a headless browser for UI verification — ask for a screenshot).
- Manual click-path: grid → primary card → each of the 5 sections; grid → spawned
  card → each section; **+ New** → chat thread opens with the template; Configure
  Save with and without a valid token.

## 10. Out of scope

- Independent PnL/positions/trades for spawned agents (they don't trade).
- All SOL-specific sniper gates.
- Any change to `core/`, the agent runtime, or the Convex schema.
- Live slippage / max-open-exposure knobs.
- URL deep-linking per section (local state only; can be added later).
