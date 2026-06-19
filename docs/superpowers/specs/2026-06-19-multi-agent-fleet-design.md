# Multi-Agent Fleet + Cockpit Enhancements — Design Spec
**Date:** 2026-06-19  
**Status:** Draft — pending user approval  
**Scope:** 6 feature areas discussed in the 2026-06-19 review session

---

## 1. Context

The cockpit currently has a single CoPilotDrawer (one chat panel, named threads), a fixed AgentsView showing 4 system agents, a static PipelineView, and a mobile BottomNav with 4 tabs + More sheet. This spec covers:

| Area | What changes |
|------|-------------|
| A — Multi-agent fleet | Spawn named agents from chat; fleet view in Agents tab + sidebar |
| B — Keyboard shortcuts | `Ctrl+K` opens/closes Co-Pilot; `Ctrl+Tab` cycles threads; `Ctrl+Enter` sends |
| C — Pipeline interactivity | Signal weight sliders, force-run button, threshold overrides |
| D — Watchlist workstream | New Workstream G added to roadmap |
| E — Mobile reachability | Document current state; no code change needed |

---

## 2. Area A — Multi-Agent Fleet

### 2.1 Concept

A user can spawn as many named AI agents as they want. Each agent is a focused co-pilot with a specific task (e.g. "ETH Risk Monitor", "CAKE Researcher"). Agents live persistently in Convex and appear in:
- A **"My Agents"** collapsible section at the bottom of the sidebar
- A **"Your Agents"** section in the AgentsView (below the existing system agent cards)

The CoPilotDrawer is the spawn point. It is also the agent's chat surface — opening an agent from its card lands directly in that agent's conversation thread.

### 2.2 Spawn Flow

```
User opens Co-Pilot (new thread)
  → Empty state shows 4 structured quick-action chips:
      🤖 Spawn a new agent      — Set up a new focused agent
      ⚙️ Configure strategy      — Tune risk params, strategy name
      📊 Check performance       — Ask about PnL, drawdown, trades
      ➕ Type my own…            — Free-text input, no chip
  → User picks "Spawn a new agent"
  → Co-Pilot: "What should this agent focus on? Describe its job."
  → User types task (e.g. "Watch ETH for volatility spikes above 8%")
  → Co-Pilot: "Got it. What should I call this agent?"
  → User types name (e.g. "ETH Risk Monitor")
  → Co-Pilot creates the agent record in Convex
  → Agent card appears in sidebar "My Agents" list + AgentsView "Your Agents" section
  → Co-Pilot: "ETH Risk Monitor is live. I'll alert you when conditions match."
```

**Non-blocking:** free-text messages that don't go through the chip flow do NOT auto-trigger naming. Naming only happens when the user explicitly picks "Spawn a new agent."

### 2.3 Convex Schema — new table

```typescript
// convex/schema.ts — add to defineSchema
spawned_agents: defineTable({
  name: v.string(),                     // user-given name, e.g. "ETH Risk Monitor"
  task_summary: v.string(),             // what the agent was told to do
  thread_id: v.optional(v.id("copilot_threads")),  // linked conversation
  status: v.union(v.literal("active"), v.literal("idle"), v.literal("archived")),
  created_at: v.number(),               // Date.now()
  last_activity_ms: v.optional(v.number()),
})
.index("by_status", ["status"])
.index("by_created", ["created_at"])
```

### 2.4 Convex Functions — new file `convex/spawnedAgents.ts`

```typescript
// Queries
export const list = query(...)          // list all non-archived, newest first
export const get = query(...)           // single agent by id

// Mutations  
export const create = mutation(...)     // name + task_summary + thread_id → insert
export const setStatus = mutation(...)  // active / idle / archived
export const updateActivity = mutation(...)  // bump last_activity_ms
```

### 2.5 CoPilotDrawer changes

**Quick-action chips (empty thread state):**
Replace the current 4 suggestion cards (conservative run / adjust risk / take profit / type own) with:

```
┌──────────────────────────────────────────┐
│ 🤖 Spawn a new agent                     │
│    Set up a new focused co-pilot         │
├──────────────────────────────────────────┤
│ ⚙️  Configure strategy                   │
│    Tune risk params or strategy          │
├──────────────────────────────────────────┤
│ 📊 Check performance                     │
│    Ask about PnL, drawdown, trades       │
├──────────────────────────────────────────┤
│ ➕ Type my own…                          │
└──────────────────────────────────────────┘
```

**Spawn conversation state machine** (local React state in CoPilotDrawer):
```
idle → awaiting_task → awaiting_name → creating → done
```
- `awaiting_task`: co-pilot asks for the job description; user's next message is captured as `task_summary`
- `awaiting_name`: co-pilot asks for a name; user's next message is captured as `name`
- `creating`: mutation fires, agent record created, chip UI resets

The state machine runs inside the existing `send()` path — it intercepts messages during spawn flow and skips the normal `ask()` action call.

**New prop:** `initialThreadId?: Id<"copilot_threads">` — if passed, the drawer opens directly on that thread. Used when clicking "Open Chat" from an agent card.

### 2.6 Sidebar changes — `SideNav.tsx`

Add a "My Agents" section between the nav items and the footer buttons:

```
[existing NAV_ITEMS...]
────────────────── (divider)
MY AGENTS  (section label)
  ● ETH Risk Monitor   (green dot = active)
  ○ CAKE Researcher    (dim dot = idle)
  + Spawn agent        (opens Co-Pilot in spawn mode)
────────────────── 
[Tour] [Co-Pilot] [Theme]  (existing footer)
```

- Each agent row: colored status dot + truncated name (max 14 chars) + click → opens CoPilotDrawer on that agent's `thread_id`
- "Spawn agent" row → opens CoPilotDrawer with spawn chip pre-selected
- Section is collapsible (chevron) if > 5 agents
- Reads from `api.spawnedAgents.list`; empty = section hidden

### 2.7 AgentsView redesign

**Two sections:**

**Section 1 — System Agents** (unchanged, existing AGENT_DEFS cards)  
Label: `SYSTEM · Neural Mesh`

**Section 2 — Your Agents** (new)  
Label: `YOUR AGENTS`

Each spawned agent card:
```
┌──────────────────────────────────────────┐
│ ⬡  ETH Risk Monitor            ● active  │
│    "Watch ETH for volatility…"           │
│    Spawned 2h ago                        │
│                          [Open Chat →]   │
└──────────────────────────────────────────┘
```

Empty state: "No agents yet. Open the Co-Pilot and say what job you need done."

---

## 3. Area B — Keyboard Shortcuts

### 3.1 Shortcut map

| Action | Shortcut | Notes |
|--------|----------|-------|
| Toggle Co-Pilot open/close | `Ctrl+K` (Win/Linux) / `Cmd+K` (Mac) | De-facto AI chat shortcut (Copilot, Linear, Raycast) |
| Cycle co-pilot threads (next) | `Ctrl+Tab` | Only active when Co-Pilot is open |
| Cycle co-pilot threads (prev) | `Ctrl+Shift+Tab` | Only active when Co-Pilot is open |
| Send message | `Ctrl+Enter` | In addition to existing `Enter` |

### 3.2 Implementation

Global `keydown` listener in `App.tsx` `useEffect`:
```typescript
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key === "k") { e.preventDefault(); setCopilotOpen(o => !o); }
    if (copilotOpen && mod && e.key === "Tab") {
      e.preventDefault();
      // cycle thread — emit event CoPilotDrawer listens to
    }
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, [copilotOpen]);
```

`Ctrl+Enter` in CoPilotDrawer input — already handles `Enter`; add check for `e.ctrlKey`.

### 3.3 Hover hints

**Co-Pilot button in SideNav** — tooltip currently reads "Co-Pilot". Change to:
```
Co-Pilot  ⌃K
```
(Append shortcut badge to TooltipContent)

**Co-Pilot button in BottomNav More sheet** — same tooltip addition.

**Input field placeholder** — change from `"Ask the agent…"` to `"Ask the agent… (⌃↵ to send)"`.

---

## 4. Area C — Pipeline Interactivity

### 4.1 Current state

PipelineView is read-only. All 5 stages auto-update from Convex live data. Nothing is clickable or adjustable.

### 4.2 What becomes interactive

Three interaction layers, from lowest to highest impact:

**Layer 1 — Force run (safe, immediate value)**  
A "Run now" button in the Pipeline header that enqueues an `agent_command` of type `force_cycle` via `convex/agentCommands.ts`. The agent picks it up on its next poll.

**Layer 2 — Risk threshold override (medium impact)**  
Stage 4 (Risk Check) gets inline editable fields for:
- Max drawdown % (currently from `core/config.py` via Convex config)
- Daily loss cap USD
Both write to `convex/config.ts` via the existing `updateLimits` mutation (already used in CoPilotDrawer).  
Fields show as plain text by default; click → becomes an input; blur/Enter → saves + shows confirmation flash.

**Layer 3 — Signal weight sliders (high complexity, post-freeze)**  
Stage 2 (Signal Analysis) would get sliders for momentum/derivatives/sentiment/flow weights. Deferred — requires a `signal_weights` Convex config field and the Python agent to read it. Not in scope before Jun 21 freeze.

### 4.3 Scope for freeze (Jun 21)

- ✅ Layer 1: Force-run button  
- ✅ Layer 2: Risk threshold inline edit  
- ❌ Layer 3: Signal weight sliders (post-freeze)

### 4.4 UX detail

Stage cards get a subtle `hover:border-border` state to signal they're interactive when Layer 2 is active. The edit icon (pencil) appears on hover next to editable values only. Non-editable rows stay as-is.

---

## 5. Area D — Watchlist Workstream (Roadmap Addition)

### 5.1 Win-gate

**YES** — A watchlist of tokens with price alerts is directly useful for:
- S3 sentiment monitoring (track tokens the agent is eligible to trade)
- Judge demo: shows the cockpit is a complete trading tool, not just a single-ticker viewer
- Stackable with Workstream D (KOL tracker) — tracked tokens can feed the same alert pipeline

### 5.2 Workstream G definition

**Goal:** A watchlist view where the user adds tokens (from the eligible set: ETH/CAKE/UNI/LINK/AAVE + any others), sets price alert thresholds, and sees live price + % change. Alerts fire as toast notifications and Telegram messages.

**Files:**
- New Convex table: `watchlist` `{ symbol, alert_above_usd, alert_below_usd, added_at, user_note? }`
- New query: `convex/watchlist.ts → list`, `add`, `remove`, `setAlerts`
- New view: `web/src/views/WatchlistView.tsx` — token rows with live price (from `priceTicks`), % change, alert badge, edit/remove
- Nav: Add `watchlist` to `View` type + nav items (More section on mobile, sidebar on desktop)
- Alert trigger: in `convex/priceTicks.ts` mutation — after inserting a tick, check watchlist thresholds and emit an `agentEvent` if crossed

**Priority:** P2 (after A and B, before freeze if time allows)

**Detailed plan:** `2026-06-19-watchlist-workstream.md` (to be written separately)

---

## 6. Area E — Mobile Reachability (Documentation)

### 6.1 Current state (no change needed)

The BottomNav already has 4 primary tabs + "More" button:

| Tab slot | View |
|----------|------|
| 1 | Overview |
| 2 | Trackers |
| 3 | Chart |
| 4 | Portfolio |
| 5 (More) | Opens bottom sheet |

The "More" bottom sheet has two sections:
- **Main**: Intelligence, Controls (overflow primary)
- **Tools**: Deposit, Withdraw, Positions, Agents, Pipeline, Logs, Alerts, Docs

**All views are reachable on mobile.** The "More" pattern was implemented in Workstream C of the prior sprint. No code change required for this area.

---

## 7. Implementation Sequence (pre-freeze, Jun 21)

| Order | Item | Files | Effort |
|-------|------|-------|--------|
| 1 | Keyboard shortcuts (`Ctrl+K`, `Ctrl+Tab`, `Ctrl+Enter`) + hover hints | `App.tsx`, `CoPilotDrawer.tsx`, `SideNav.tsx` | Small |
| 2 | Convex schema + `spawnedAgents.ts` functions | `convex/schema.ts`, `convex/spawnedAgents.ts` | Small |
| 3 | CoPilotDrawer quick-action chip redesign + spawn state machine | `CoPilotDrawer.tsx` | Medium |
| 4 | Sidebar "My Agents" section | `SideNav.tsx` | Small |
| 5 | AgentsView "Your Agents" section | `AgentsView.tsx` | Small |
| 6 | Pipeline Layer 1 (force-run button) | `PipelineView.tsx`, `convex/agentCommands.ts` | Small |
| 7 | Pipeline Layer 2 (risk threshold inline edit) | `PipelineView.tsx`, `convex/config.ts` | Medium |
| 8 | Watchlist (Workstream G, if time) | new files | Medium |

---

## 8. What This Does NOT Change

- The Python trading core (`core/`) — zero changes
- The deterministic trade decision path — agents are UI/chat only
- The existing thread model in CoPilotDrawer — threads still exist; spawned agents simply have a named agent record linked to a thread
- The system agent cards (Historian/Researcher/Reflector) — unchanged, still shown in AgentsView section 1
- The registered competition wallet or any live trading parameters

---

## 9. Open Questions

| # | Question | Default if not answered |
|---|----------|------------------------|
| 1 | Should archived agents be deletable from the UI, or just hidden? | Hidden (archived, not deleted) |
| 2 | Can a spawned agent have more than one thread? | No — 1 agent : 1 thread |
| 3 | Should "Spawn agent" in the sidebar skip the chip UI and go straight to the spawn flow? | Yes — pre-select the spawn chip |
