# Agent Detail Cockpit + Chat-First Create — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clicking an agent opens a full-page detail cockpit (Dashboard / Trades / Scanning / Live Positions / Configure), and "+ New" opens a chat-first agent-creation flow.

**Architecture:** Web-only. `AgentsView` holds a `selectedAgentId` and swaps the grid for a new `AgentDetailView` (left sub-nav + section outlet). Each section reads global Convex singletons for the **primary** live trader and lighter `spawned_agents` data for spawned agents. Configure writes only through *existing* token-gated config mutations; the one new backend symbol is a Convex `spawnedAgents.update` mutation. No `core/` or hot-path changes.

**Tech Stack:** React 19 + Vite + TypeScript, Convex (reactive queries), Tailwind + shadcn/ui, `framer-motion`, `sonner` toasts.

## Global Constraints

- **Freeze-safe (Jun 21 freeze):** no edits to `core/`, the agent runtime, or `convex/schema.ts`. Only `web/src/**` and one new mutation in `convex/spawnedAgents.ts`.
- **Package manager:** `bun`, never `npm`/`npx`. Run web commands from `web/`.
- **Honesty rule:** spawned agents NEVER display PnL/positions/trades they didn't earn. Empty states instead.
- **Win gate:** Configure exposes only score-relevant knobs (drawdown-first). No SOL-specific gates, no inert decorative controls.
- **Token-gated writes:** every config/agent mutation call is wrapped with `withToken(...)` from `@/lib/control`; on failure show a `sonner` `toast.error`.
- **Styling idiom:** `font-mono` for labels (`text-[10px] uppercase tracking-widest text-muted-fg`), `panel` class for cards, `cn(...)` for conditional classes, colors via `text-green` / `text-purple` / `text-red` / `text-muted-fg`. Match existing `AgentsView.tsx`.
- **Verification approach:** `web` UI is verified by `bun run typecheck` (tsc) + `bun run build` (final task) + a **manual screenshot from the operator** (do not spin up a headless browser). The one pure-logic helper gets a vitest unit test.

---

### Task 1: `spawnedAgents.update` Convex mutation

**Files:**
- Modify: `convex/spawnedAgents.ts` (add after `rename`)

**Interfaces:**
- Produces: `api.spawnedAgents.update({ id, goal?, allowed_tools?, trigger?, mode?, notify_policy? })`

- [ ] **Step 1: Add the mutation**

In `convex/spawnedAgents.ts`, after the `rename` mutation, add:

```ts
export const update = mutation({
  args: {
    id:            v.id("spawned_agents"),
    goal:          v.optional(v.string()),
    allowed_tools: v.optional(v.array(v.string())),
    trigger:       v.optional(v.object({ kind: v.string(), spec: v.string() })),
    mode:          v.optional(v.union(v.literal("paper"), v.literal("live"))),
    notify_policy: v.optional(v.object({ webpush: v.boolean(), severity_min: v.string() })),
  },
  handler: async (ctx, args) => {
    const { id, ...rest } = args;
    const patch: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(rest)) {
      if (val !== undefined) patch[k] = val;
    }
    // keep task_summary (display field) in sync with goal
    if (rest.goal !== undefined) patch.task_summary = rest.goal;
    patch.last_activity_ms = Date.now();
    await ctx.db.patch(id, patch);
  },
});
```

- [ ] **Step 2: Verify codegen + types**

With `bunx convex dev` running in another terminal (it auto-pushes on save), confirm no schema/validator error in its output. Then:

Run: `cd web && bun run typecheck`
Expected: PASS (no errors). `api.spawnedAgents.update` is now generated.

- [ ] **Step 3: Commit**

```bash
git add convex/spawnedAgents.ts
git commit -m "feat(convex): spawnedAgents.update mutation for agent config editing"
```

---

### Task 2: Agent-kind model + detail shell

**Files:**
- Create: `web/src/views/agent-detail/types.ts`
- Create: `web/src/views/agent-detail/types.test.ts`
- Create: `web/src/views/agent-detail/AgentDetailView.tsx`

**Interfaces:**
- Produces:
  - `type AgentKind = "primary" | "spawned"`
  - `type DetailAgent = { kind: AgentKind; id?: Id<"spawned_agents">; name: string; status: string; mode?: string; goal?: string; thread_id?: string; allowed_tools?: string[]; trigger?: { kind: string; spec: string } }`
  - `type DetailSection = "dashboard" | "trades" | "scanning" | "positions" | "configure"`
  - `function sectionLabel(s: DetailSection): string`
  - `<AgentDetailView agent={DetailAgent} onBack={() => void} onOpenChat={() => void} />`

- [ ] **Step 1: Write the failing test for `sectionLabel`**

`web/src/views/agent-detail/types.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { sectionLabel, SECTION_ORDER } from "./types";

describe("sectionLabel", () => {
  it("maps each section to a human label", () => {
    expect(sectionLabel("dashboard")).toBe("Dashboard");
    expect(sectionLabel("positions")).toBe("Live Positions");
    expect(sectionLabel("configure")).toBe("Configure");
  });
  it("SECTION_ORDER lists all five sections in nav order", () => {
    expect(SECTION_ORDER).toEqual(["dashboard", "trades", "scanning", "positions", "configure"]);
  });
});
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd web && bun run test -- types.test`
Expected: FAIL ("Cannot find module './types'").

- [ ] **Step 3: Create `types.ts`**

`web/src/views/agent-detail/types.ts`:

```ts
import type { Id } from "../../../../convex/_generated/dataModel";

export type AgentKind = "primary" | "spawned";

export type DetailAgent = {
  kind: AgentKind;
  id?: Id<"spawned_agents">;        // undefined for the primary trader
  name: string;
  status: string;
  mode?: string;
  goal?: string;
  thread_id?: string;
  allowed_tools?: string[];
  trigger?: { kind: string; spec: string };
};

export type DetailSection = "dashboard" | "trades" | "scanning" | "positions" | "configure";

export const SECTION_ORDER: DetailSection[] = [
  "dashboard", "trades", "scanning", "positions", "configure",
];

export function sectionLabel(s: DetailSection): string {
  switch (s) {
    case "dashboard": return "Dashboard";
    case "trades":    return "Trades";
    case "scanning":  return "Scanning";
    case "positions": return "Live Positions";
    case "configure": return "Configure";
  }
}
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `cd web && bun run test -- types.test`
Expected: PASS.

- [ ] **Step 5: Create the shell with placeholder sections**

`web/src/views/agent-detail/AgentDetailView.tsx`:

```tsx
import { useState } from "react";
import { cn } from "@/lib/utils";
import { SECTION_ORDER, sectionLabel, type DetailAgent, type DetailSection } from "./types";
import { DashboardSection } from "./DashboardSection";
import { TradesSection } from "./TradesSection";
import { ScanningSection } from "./ScanningSection";
import { LivePositionsSection } from "./LivePositionsSection";
import { ConfigureSection } from "./ConfigureSection";

type Props = {
  agent: DetailAgent;
  onBack: () => void;
  onOpenChat: () => void;
};

export function AgentDetailView({ agent, onBack, onOpenChat }: Props) {
  const [section, setSection] = useState<DetailSection>("dashboard");

  return (
    <div className="max-w-[1180px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="font-mono text-[11px] text-muted-fg hover:text-text border border-border/40 rounded px-2 py-1 transition-colors"
          >← Agents</button>
          <span className={cn(
            "w-2.5 h-2.5 rounded-full flex-shrink-0",
            agent.status === "active" ? "bg-green" : "bg-muted-fg/30",
          )} style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}} />
          <h1 className="font-display text-[20px] font-bold text-text truncate">{agent.name}</h1>
          {agent.kind === "primary" && (
            <span className="font-mono text-[9px] text-green border border-green/30 bg-green/10 rounded px-1.5 py-0.5 uppercase tracking-widest">Live trader</span>
          )}
          {agent.mode && (
            <span className="font-mono text-[9px] text-muted-fg border border-border/40 rounded px-1.5 py-0.5 uppercase tracking-widest">{agent.mode}</span>
          )}
        </div>
        <button
          onClick={onOpenChat}
          className="font-mono text-[11px] text-purple border border-purple/30 rounded px-3 py-1 hover:bg-purple/10 transition-colors flex-shrink-0"
        >Open Chat →</button>
      </div>

      <div className="flex gap-5 max-md:flex-col">
        {/* Left sub-nav */}
        <nav className="flex md:flex-col gap-1 md:w-[160px] flex-shrink-0 max-md:flex-wrap">
          {SECTION_ORDER.map((s) => (
            <button
              key={s}
              onClick={() => setSection(s)}
              className={cn(
                "font-mono text-[11px] text-left rounded px-3 py-2 transition-colors uppercase tracking-widest",
                section === s
                  ? "bg-green/12 text-green border border-green/25"
                  : "text-muted-fg border border-transparent hover:text-text hover:border-border/40",
              )}
            >{sectionLabel(s)}</button>
          ))}
        </nav>

        {/* Section outlet */}
        <div className="flex-1 min-w-0">
          {section === "dashboard" && <DashboardSection agent={agent} />}
          {section === "trades"    && <TradesSection agent={agent} />}
          {section === "scanning"  && <ScanningSection agent={agent} />}
          {section === "positions" && <LivePositionsSection agent={agent} />}
          {section === "configure" && <ConfigureSection agent={agent} />}
        </div>
      </div>
    </div>
  );
}
```

> NOTE: The five section imports don't exist yet — they are created in Tasks 4–7. To keep this task independently type-checkable, create five **stub** files now; each task replaces its stub.

- [ ] **Step 6: Create five stub section files**

Create each of these (replaced in later tasks):

`web/src/views/agent-detail/DashboardSection.tsx`,
`TradesSection.tsx`, `ScanningSection.tsx`, `LivePositionsSection.tsx`, `ConfigureSection.tsx`

Each with this body (swap the component name + label):

```tsx
import type { DetailAgent } from "./types";

export function DashboardSection({ agent }: { agent: DetailAgent }) {
  return <div className="panel p-6 font-mono text-[12px] text-muted-fg">Dashboard — {agent.name}</div>;
}
```

(For the others use `TradesSection`/`ScanningSection`/`LivePositionsSection`/`ConfigureSection` and labels "Trades"/"Scanning"/"Live Positions"/"Configure".)

- [ ] **Step 7: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add web/src/views/agent-detail
git commit -m "feat(web): agent detail shell + kind model + section stubs"
```

---

### Task 3: AgentsView rework — primary card, grid → detail, remove inline form

**Files:**
- Modify: `web/src/views/AgentsView.tsx`
- Modify: `web/src/App.tsx` (pass `onNewAgent`; primary scorecard for the card)

**Interfaces:**
- Consumes: `AgentDetailView` (Task 2), `api.scorecard.get`, `api.spawnedAgents.list`, `api.agentRuns.latestAllAgents`
- Produces: `<AgentsView onAgentOpen={(threadId)=>void} onNewAgent={()=>void} />`

- [ ] **Step 1: Rework `AgentsView.tsx`**

Replace the whole file with:

```tsx
import { useQuery } from "convex/react";
import { useState } from "react";
import { api } from "../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import { AgentDetailView } from "./agent-detail/AgentDetailView";
import type { DetailAgent } from "./agent-detail/types";
import type { Id } from "../../../convex/_generated/dataModel";

type ToolCall = { tool: string; args?: string };

type Props = {
  onAgentOpen?: (threadId: string) => void;   // opens co-pilot drawer on a thread
  onNewAgent?: () => void;                     // opens chat-first create
};

const PRIMARY: DetailAgent = {
  kind: "primary",
  name: "Alien-Trade",
  status: "active",
  goal: "Autonomous BSC spot trader — contrarian, drawdown-first.",
};

export function AgentsView({ onAgentOpen, onNewAgent }: Props) {
  const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
  const latestRuns = useQuery(api.agentRuns.latestAllAgents) ?? [];
  const scorecard = useQuery(api.scorecard.get);
  const config = useQuery(api.config.get);
  const [selected, setSelected] = useState<DetailAgent | null>(null);

  const latestRunMap = new Map(
    latestRuns.map((r: { agent_id: string; tool_calls: ToolCall[] }) => [r.agent_id, r]),
  );

  if (selected) {
    return (
      <AgentDetailView
        agent={selected}
        onBack={() => setSelected(null)}
        onOpenChat={() => onAgentOpen?.(selected.thread_id ?? "")}
      />
    );
  }

  const primary: DetailAgent = {
    ...PRIMARY,
    status: config?.halted ? "idle" : "active",
    mode: config?.trading_mode,
  };
  const pnl = scorecard?.net_pnl_usd ?? null;

  return (
    <div className="max-w-[1180px] mx-auto">
      <div className="mb-6">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Agents
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Your Agents</h1>
      </div>

      <div className="flex items-center justify-end mb-3">
        <button
          onClick={() => onNewAgent?.()}
          className="font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest transition-colors text-muted-fg border-muted-fg/20 hover:border-muted-fg/40"
        >+ New</button>
      </div>

      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        {/* Pinned primary card */}
        <button
          onClick={() => setSelected(primary)}
          className="panel p-4 flex flex-col gap-3 text-left border border-green/25 hover:border-green/50 transition-colors"
          style={{ boxShadow: "0 0 20px rgba(var(--green-rgb,52,211,153),0.06)" }}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5 bg-green" style={{ boxShadow: "0 0 6px var(--green)" }} />
              <span className="font-display text-[14px] font-bold text-text">Alien-Trade</span>
            </div>
            <span className="font-mono text-[9px] text-green border border-green/30 bg-green/10 rounded px-1.5 py-0.5 uppercase tracking-widest flex-shrink-0">Live trader</span>
          </div>
          <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed">{PRIMARY.goal}</p>
          <div className="flex items-center justify-between border-t border-border/30 pt-2">
            <span className="font-mono text-[10px] text-muted-fg/50 uppercase tracking-widest">Net PnL</span>
            <span className={cn("font-mono text-[13px] font-bold",
              pnl == null ? "text-muted-fg" : pnl >= 0 ? "text-green" : "text-red")}>
              {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`}
            </span>
          </div>
        </button>

        {/* Spawned agent cards */}
        {spawnedAgents.map((agent) => {
          const run = latestRunMap.get(agent._id);
          const calls: ToolCall[] = run?.tool_calls ?? [];
          const detail: DetailAgent = {
            kind: "spawned",
            id: agent._id as Id<"spawned_agents">,
            name: agent.name,
            status: agent.status,
            mode: agent.mode,
            goal: agent.goal ?? agent.task_summary,
            thread_id: agent.thread_id ?? undefined,
            allowed_tools: agent.allowed_tools ?? [],
            trigger: agent.trigger ?? undefined,
          };
          return (
            <button
              key={agent._id}
              onClick={() => setSelected(detail)}
              className="panel p-4 flex flex-col gap-3 text-left hover:border-border/60 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={cn("w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5",
                    agent.status === "active" ? "bg-green" : "bg-muted-fg/30")}
                    style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}} />
                  <span className="font-display text-[14px] font-bold text-text">{agent.name}</span>
                </div>
                <span className={cn("font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest flex-shrink-0",
                  agent.status === "active" ? "bg-green/12 text-green border-green/25" : "bg-muted-fg/8 text-muted-fg border-muted-fg/20")}>
                  {agent.status}
                </span>
              </div>
              <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed line-clamp-2">{agent.task_summary}</p>
              {calls.length > 0 && (
                <div className="flex items-center gap-0.5 flex-wrap border-t border-border/30 pt-2">
                  <span className="font-mono text-[9px] text-muted-fg/50 uppercase tracking-widest mr-1">Chain</span>
                  {calls.map((tc, i) => (
                    <span key={i} className="font-mono text-[9px] rounded px-1.5 py-0.5 border bg-purple/10 text-purple border-purple/20">{tc.tool}</span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire `onNewAgent` in `App.tsx`**

In `App.tsx`, the `AgentsView` case currently passes only `onAgentOpen`. Update it to:

```tsx
      case "agents":        return (
        <AgentsView
          onAgentOpen={(threadId) => {
            setCopilotThreadId(threadId as Id<"copilot_threads"> | undefined);
            setCopilotOpen(true);
          }}
          onNewAgent={() => {
            setCopilotThreadId(undefined);
            setCopilotStartSpawn(true);
            setCopilotOpen(true);
          }}
        />
      );
```

Add the state near the other copilot state (around the `copilotThreadId` declaration):

```tsx
  const [copilotStartSpawn, setCopilotStartSpawn] = useState(false);
```

And reset it in the drawer's `onClose` (updated fully in Task 8 — for now just add `setCopilotStartSpawn(false);` to the existing `onClose` handler of `CoPilotDrawer`).

- [ ] **Step 3: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS. (`copilotStartSpawn` is set but not yet read by the drawer — that's Task 8. No type error.)

- [ ] **Step 4: Manual screenshot check**

Ask the operator for a screenshot of the Agents tab. Verify: pinned green "Alien-Trade" card with Net PnL, spawned cards below, clicking the primary card opens the detail shell with the five-item left sub-nav and "← Agents" back button.

- [ ] **Step 5: Commit**

```bash
git add web/src/views/AgentsView.tsx web/src/App.tsx
git commit -m "feat(web): agents grid with pinned primary card + click-into detail"
```

---

### Task 4: DashboardSection

**Files:**
- Modify (replace stub): `web/src/views/agent-detail/DashboardSection.tsx`

**Interfaces:**
- Consumes: `api.scorecard.get`, `api.decisions.latest`, `api.agentRuns.recent`

- [ ] **Step 1: Implement**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "green" | "red" | "muted" }) {
  return (
    <div className="panel p-3 flex flex-col gap-1">
      <span className="font-mono text-[9px] text-muted-fg/60 uppercase tracking-widest">{label}</span>
      <span className={cn("font-mono text-[16px] font-bold",
        tone === "green" ? "text-green" : tone === "red" ? "text-red" : "text-text")}>{value}</span>
    </div>
  );
}

export function DashboardSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryDashboard />;
  return <SpawnedDashboard agent={agent} />;
}

function PrimaryDashboard() {
  const sc = useQuery(api.scorecard.get);
  const decision = useQuery(api.decisions.latest);
  const pnl = sc?.net_pnl_usd ?? null;
  const dd = sc?.max_drawdown ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-2">
        <Stat label="Realized PnL" value={pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`} tone={pnl == null ? "muted" : pnl >= 0 ? "green" : "red"} />
        <Stat label="Win Rate" value={sc?.win_rate == null ? "—" : `${(sc.win_rate * 100).toFixed(0)}%`} />
        <Stat label="Trades" value={sc?.n_trades?.toString() ?? "—"} />
        <Stat label="Max Drawdown" value={dd == null ? "—" : `${(dd * 100).toFixed(1)}%`} tone={dd ? "red" : "muted"} />
        <Stat label="Sortino" value={sc?.sortino?.toFixed(2) ?? "—"} />
        <Stat label="Profit Factor" value={sc?.profit_factor?.toFixed(2) ?? "—"} />
      </div>

      <div className="panel p-4">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-2">AI Insights</div>
        {decision ? (
          <div className="flex flex-col gap-1.5">
            <p className="font-mono text-[12px] text-text leading-relaxed">
              Regime <span className="text-purple">{decision.regime}</span> on {decision.symbol} ·
              verdict <span className={cn(decision.risk_verdict === "block" ? "text-red" : decision.risk_verdict === "reduce" ? "text-yellow" : "text-green")}>{decision.risk_verdict}</span>
            </p>
            {decision.risk_reason && <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed">{decision.risk_reason}</p>}
            <p className="font-mono text-[10px] text-muted-fg/50">target ${decision.target_position_usd.toFixed(0)} → final ${decision.final_size_usd.toFixed(0)}</p>
          </div>
        ) : (
          <p className="font-mono text-[11px] text-muted-fg/60">No decisions recorded yet.</p>
        )}
      </div>
    </div>
  );
}

function SpawnedDashboard({ agent }: { agent: DetailAgent }) {
  const runs = useQuery(api.agentRuns.recent, agent.id ? { agent_id: agent.id } : "skip") ?? [];
  const lastRun = runs[0];
  const okCount = runs.filter((r) => r.ok).length;
  const avgTools = runs.length ? (runs.reduce((s, r) => s + r.tool_calls.length, 0) / runs.length) : 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-2">
        <Stat label="Runs" value={runs.length.toString()} />
        <Stat label="OK / Total" value={`${okCount}/${runs.length}`} tone={runs.length && okCount === runs.length ? "green" : "muted"} />
        <Stat label="Avg Tools/Run" value={avgTools.toFixed(1)} />
      </div>
      <div className="panel p-4">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-2">Goal</div>
        <p className="font-mono text-[12px] text-text leading-relaxed">{agent.goal ?? "—"}</p>
        {lastRun && <p className="font-mono text-[11px] text-muted-fg/70 mt-2">Last run: {lastRun.ok ? "✅" : "⚠️"} {lastRun.summary}</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 3: Screenshot check**

Ask operator for screenshots of the primary Dashboard (real metrics) and a spawned agent's Dashboard (run stats). Confirm spawned shows NO PnL.

- [ ] **Step 4: Commit**

```bash
git add web/src/views/agent-detail/DashboardSection.tsx
git commit -m "feat(web): agent dashboard section (primary scorecard / spawned run stats)"
```

---

### Task 5: TradesSection + LivePositionsSection

**Files:**
- Modify (replace stubs): `web/src/views/agent-detail/TradesSection.tsx`, `web/src/views/agent-detail/LivePositionsSection.tsx`

**Interfaces:**
- Consumes: `api.trades.recent`, `api.positions.open`, `api.approvals.listPending`

- [ ] **Step 1: Implement `TradesSection.tsx`**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

export function TradesSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryTrades />;
  return <SpawnedApprovals agent={agent} />;
}

function PrimaryTrades() {
  const trades = useQuery(api.trades.recent, { limit: 30 }) ?? [];
  if (trades.length === 0) return <Empty text="No trades yet." />;
  return (
    <div className="panel p-0 overflow-hidden">
      <table className="w-full font-mono text-[11px]">
        <thead>
          <tr className="text-muted-fg/60 uppercase tracking-widest text-[9px] border-b border-border/30">
            <th className="text-left px-3 py-2">Side</th>
            <th className="text-left px-3 py-2">Symbol</th>
            <th className="text-right px-3 py-2">Size</th>
            <th className="text-right px-3 py-2">Fill</th>
            <th className="text-right px-3 py-2">Gas</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t._id} className="border-b border-border/15">
              <td className={cn("px-3 py-2 uppercase", t.side === "buy" ? "text-green" : "text-red")}>{t.side}</td>
              <td className="px-3 py-2 text-text">{t.symbol}</td>
              <td className="px-3 py-2 text-right text-text">${t.size_usd.toFixed(2)}</td>
              <td className="px-3 py-2 text-right text-muted-fg">${t.fill_price.toFixed(4)}</td>
              <td className="px-3 py-2 text-right text-muted-fg/70">${t.gas_usd.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SpawnedApprovals({ agent }: { agent: DetailAgent }) {
  const pending = useQuery(api.approvals.listPending) ?? [];
  const mine = pending.filter((p) => p.agent_id === agent.id);
  return (
    <div className="flex flex-col gap-3">
      <p className="font-mono text-[10px] text-muted-fg/60 uppercase tracking-widest">Assistant agents propose trades — they don't execute directly.</p>
      {mine.length === 0 ? <Empty text="No pending trade proposals." /> : mine.map((p) => (
        <div key={p._id} className="panel p-3 font-mono text-[11px] text-text">{p.kind}: {p.payload}</div>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">{text}</div>;
}
```

- [ ] **Step 2: Implement `LivePositionsSection.tsx`**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

export function LivePositionsSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind !== "primary") {
    return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">Assistant agents hold no positions.</div>;
  }
  return <PrimaryPositions />;
}

function PrimaryPositions() {
  const positions = useQuery(api.positions.open) ?? [];
  if (positions.length === 0) return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">Flat — no open positions.</div>;
  return (
    <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
      {positions.map((p) => (
        <div key={p._id} className="panel p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-display text-[14px] font-bold text-text">{p.symbol}</span>
            <span className={cn("font-mono text-[12px] font-bold", p.unrealized_pnl_usd >= 0 ? "text-green" : "text-red")}>
              {p.unrealized_pnl_usd >= 0 ? "+" : ""}${p.unrealized_pnl_usd.toFixed(2)}
            </span>
          </div>
          <div className="font-mono text-[10px] text-muted-fg/70 flex justify-between">
            <span>{p.quantity.toFixed(4)} @ ${p.avg_entry_price.toFixed(4)}</span>
            <span>now ${p.current_price.toFixed(4)}</span>
          </div>
          <div className="font-mono text-[10px] text-muted-fg/50">value ${p.current_value_usd.toFixed(2)}</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src/views/agent-detail/TradesSection.tsx web/src/views/agent-detail/LivePositionsSection.tsx
git commit -m "feat(web): trades + live positions sections"
```

---

### Task 6: ScanningSection

**Files:**
- Modify (replace stub): `web/src/views/agent-detail/ScanningSection.tsx`

**Interfaces:**
- Consumes: `api.decisions.recent`, `api.agentRuns.recent`

- [ ] **Step 1: Implement**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

export function ScanningSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryScanning />;
  return <SpawnedScanning agent={agent} />;
}

function PrimaryScanning() {
  const decisions = useQuery(api.decisions.recent, { limit: 20 }) ?? [];
  if (decisions.length === 0) return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">No cycles recorded yet.</div>;
  return (
    <div className="flex flex-col gap-2">
      {decisions.map((d) => (
        <div key={d._id} className="panel p-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-mono text-[11px] text-text">{d.symbol}</span>
            <span className="font-mono text-[9px] text-purple border border-purple/20 bg-purple/10 rounded px-1.5 py-0.5 uppercase">{d.regime}</span>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {d.signals.momentum != null && <Sig label="mom" v={d.signals.momentum} />}
            {d.signals.sentiment != null && <Sig label="sent" v={d.signals.sentiment} />}
            <span className={cn("font-mono text-[10px] uppercase",
              d.risk_verdict === "block" ? "text-red" : d.risk_verdict === "reduce" ? "text-yellow" : "text-green")}>{d.risk_verdict}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Sig({ label, v }: { label: string; v: number }) {
  return <span className="font-mono text-[9px] text-muted-fg">{label} <span className={v >= 0 ? "text-green" : "text-red"}>{v.toFixed(2)}</span></span>;
}

function SpawnedScanning({ agent }: { agent: DetailAgent }) {
  const runs = useQuery(api.agentRuns.recent, agent.id ? { agent_id: agent.id } : "skip") ?? [];
  if (runs.length === 0) return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">No runs yet.</div>;
  return (
    <div className="flex flex-col gap-2">
      {runs.map((r) => (
        <div key={r._id} className="panel p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-text">{r.ok ? "✅" : "⚠️"} {r.summary}</span>
            <span className="font-mono text-[9px] text-muted-fg/50">{new Date(r.started_ms).toLocaleTimeString()}</span>
          </div>
          {r.tool_calls.length > 0 && (
            <div className="flex items-center gap-0.5 flex-wrap">
              {r.tool_calls.map((tc, i) => (
                <span key={i} className="font-mono text-[9px] rounded px-1.5 py-0.5 border bg-purple/10 text-purple border-purple/20">{tc.tool}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add web/src/views/agent-detail/ScanningSection.tsx
git commit -m "feat(web): scanning section (primary decisions / spawned run traces)"
```

---

### Task 7: ConfigureSection

**Files:**
- Modify (replace stub): `web/src/views/agent-detail/ConfigureSection.tsx`

**Interfaces:**
- Consumes: `api.config.get`, `api.config.updateLimits`, `api.config.setStrategy`, `api.config.setTradingMode`, `api.spawnedAgents.update` (Task 1), `withToken` from `@/lib/control`, `toast` from `sonner`

- [ ] **Step 1: Implement**

```tsx
import { useQuery, useMutation } from "convex/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "../../../../convex/_generated/api";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

const STRATEGIES = ["momentum", "contrarian", "balanced", "defensive"];
const MODES = ["paper", "testnet", "mainnet"] as const;

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">{label}</label>
      {hint && <span className="font-mono text-[10px] text-muted-fg/50">{hint}</span>}
      {children}
    </div>
  );
}

const inputCls = "font-mono text-[12px] bg-surface border border-border/40 rounded px-3 py-2 text-text focus:outline-none focus:border-green/50";

export function ConfigureSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryConfigure />;
  return <SpawnedConfigure agent={agent} />;
}

function PrimaryConfigure() {
  const config = useQuery(api.config.get);
  const updateLimits = useMutation(api.config.updateLimits);
  const setStrategy = useMutation(api.config.setStrategy);
  const setTradingMode = useMutation(api.config.setTradingMode);

  const [maxPos, setMaxPos] = useState("");
  const [dailyLoss, setDailyLoss] = useState("");
  const [maxDd, setMaxDd] = useState("");
  const [floor, setFloor] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!config || dirty) return;
    setMaxPos(String(config.max_position_usd));
    setDailyLoss(String(config.daily_loss_limit_usd));
    setMaxDd(String((config.max_drawdown_pct * 100).toFixed(1)));
    setFloor(String(config.equity_floor ?? 0));
  }, [config, dirty]);

  async function save() {
    setSaving(true);
    try {
      await updateLimits(withToken({
        max_position_usd: Number(maxPos),
        daily_loss_limit_usd: Number(dailyLoss),
        max_drawdown_pct: Number(maxDd) / 100,
        equity_floor: Number(floor),
      }));
      toast.success("Risk limits updated");
      setDirty(false);
    } catch (e) {
      toast.error(`Save failed — ${String(e).includes("token") ? "pair the cockpit first" : "check token"}`);
    } finally {
      setSaving(false);
    }
  }

  const onEdit = (setter: (v: string) => void) => (v: string) => { setter(v); setDirty(true); };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Risk limits — drawdown-first</span>
        {dirty && <span className="font-mono text-[10px] text-yellow">Unsaved</span>}
      </div>

      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <Field label="Per-trade size (USD)" hint="Max USD per position.">
          <input className={inputCls} value={maxPos} onChange={(e) => onEdit(setMaxPos)(e.target.value)} inputMode="decimal" />
        </Field>
        <Field label="Daily loss limit (USD)" hint="Halt for the day past this loss.">
          <input className={inputCls} value={dailyLoss} onChange={(e) => onEdit(setDailyLoss)(e.target.value)} inputMode="decimal" />
        </Field>
        <Field label="Max drawdown %" hint="Circuit-breaker depth.">
          <input className={inputCls} value={maxDd} onChange={(e) => onEdit(setMaxDd)(e.target.value)} inputMode="decimal" />
        </Field>
        <Field label="Equity floor (USD)" hint="Halt if portfolio drops below. 0 = off.">
          <input className={inputCls} value={floor} onChange={(e) => onEdit(setFloor)(e.target.value)} inputMode="decimal" />
        </Field>
      </div>

      <Field label="Strategy">
        <div className="flex gap-1.5 flex-wrap">
          {STRATEGIES.map((s) => (
            <button key={s} disabled={saving}
              onClick={async () => {
                try { await setStrategy(withToken({ strategy_name: s })); toast.success(`Strategy → ${s}`); }
                catch { toast.error("Pair the cockpit to change strategy"); }
              }}
              className={cn("font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                config?.strategy_name === s ? "bg-green/15 text-green border-green/30" : "text-muted-fg border-border/30 hover:border-border/60")}>
              {s}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Trading mode">
        <div className="flex gap-1.5">
          {MODES.map((m) => (
            <button key={m} disabled={saving}
              onClick={async () => {
                try { await setTradingMode(withToken({ trading_mode: m })); toast.success(`Mode → ${m}`); }
                catch { toast.error("Pair the cockpit to change mode"); }
              }}
              className={cn("font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                config?.trading_mode === m ? "bg-purple/15 text-purple border-purple/30" : "text-muted-fg border-border/30 hover:border-border/60")}>
              {m}
            </button>
          ))}
        </div>
      </Field>

      <button onClick={save} disabled={saving || !dirty}
        className="font-mono text-[12px] bg-green/20 text-green border border-green/30 rounded px-4 py-2.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest self-start">
        {saving ? "Saving…" : "Save risk limits"}
      </button>
    </div>
  );
}

function SpawnedConfigure({ agent }: { agent: DetailAgent }) {
  const update = useMutation(api.spawnedAgents.update);
  const [goal, setGoal] = useState(agent.goal ?? "");
  const [spec, setSpec] = useState(agent.trigger?.spec ?? "4h");
  const [mode, setMode] = useState<"paper" | "live">(agent.mode === "live" ? "live" : "paper");
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!agent.id) return;
    setSaving(true);
    try {
      await update({ id: agent.id, goal, trigger: { kind: "schedule", spec }, mode });
      toast.success("Agent updated");
    } catch (e) {
      toast.error(`Save failed — ${String(e)}`);
    } finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col gap-4">
      <Field label="Goal">
        <textarea className={cn(inputCls, "resize-none")} rows={2} value={goal} onChange={(e) => setGoal(e.target.value)} />
      </Field>
      <Field label="Run cadence">
        <select className={inputCls} value={spec} onChange={(e) => setSpec(e.target.value)}>
          <option value="1h">Every hour</option>
          <option value="4h">Every 4 hours</option>
          <option value="24h">Daily</option>
        </select>
      </Field>
      <Field label="Mode">
        <div className="flex gap-1.5">
          {(["paper", "live"] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={cn("font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                mode === m ? "bg-purple/15 text-purple border-purple/30" : "text-muted-fg border-border/30 hover:border-border/60")}>{m}</button>
          ))}
        </div>
      </Field>
      <button onClick={save} disabled={saving}
        className="font-mono text-[12px] bg-green/20 text-green border border-green/30 rounded px-4 py-2.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest self-start">
        {saving ? "Saving…" : "Save agent"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 3: Manual check (token-gated)**

Ask operator to screenshot the primary Configure tab. Verify: editing a field shows "Unsaved", Save with a valid token shows success toast, Save without pairing shows the error toast. Spawned Configure shows goal/cadence/mode editor.

- [ ] **Step 4: Commit**

```bash
git add web/src/views/agent-detail/ConfigureSection.tsx
git commit -m "feat(web): configure section — live risk knobs + spawned agent editor"
```

---

### Task 8: Chat-first create — "+ New" auto-starts the spawn flow

**Files:**
- Modify: `web/src/components/CoPilotDrawer.tsx` (add `startSpawn` prop + auto-trigger)
- Modify: `web/src/App.tsx` (pass `startSpawn`, reset on close)

**Interfaces:**
- Consumes: existing spawn state machine (`handleQuickAction("spawn")`), `api.copilot.createThread`
- Produces: `<CoPilotDrawer startSpawn={boolean} ... />`

- [ ] **Step 1: Add the `startSpawn` prop to `CoPilotDrawer`**

In the `Props` type (around line 54), add:

```tsx
  startSpawn?: boolean;
```

Destructure it in the component signature (around line 322):

```tsx
export function CoPilotDrawer({
  isOpen,
  onClose,
  prefill = "",
  initialThreadId,
  startSpawn = false,
}: Props) {
```

- [ ] **Step 2: Auto-trigger the spawn flow on open**

Add this effect after the existing prefill-sync effect (around line 470). It creates a fresh thread, then kicks the existing spawn quick-action once per open:

```tsx
  // "+ New" entry point — open a fresh thread and auto-start the guided spawn flow.
  const [spawnKicked, setSpawnKicked] = useState(false);
  useEffect(() => {
    if (!isOpen) { setSpawnKicked(false); return; }
    if (!startSpawn || spawnKicked) return;
    setSpawnKicked(true);
    void (async () => {
      const id = await createThread(withToken({ title: "New agent" }));
      setActiveThreadId(id);
      handleQuickAction("spawn");
    })();
  }, [isOpen, startSpawn, spawnKicked]);
```

> NOTE: `handleQuickAction` and `createThread` are already defined above this point in the component. If ESLint flags exhaustive-deps, leave the deps as written — re-running on `handleQuickAction` identity change would double-fire; the `spawnKicked` guard is the intended gate.

- [ ] **Step 3: Pass and reset `startSpawn` from `App.tsx`**

Update the `CoPilotDrawer` usage in `App.tsx`:

```tsx
      <CoPilotDrawer
        isOpen={copilotOpen}
        onClose={() => { setCopilotOpen(false); setCopilotPrefill(""); setCopilotThreadId(undefined); setCopilotStartSpawn(false); }}
        prefill={copilotPrefill}
        initialThreadId={copilotThreadId as Id<"copilot_threads"> | undefined}
        startSpawn={copilotStartSpawn}
      />
```

(The `copilotStartSpawn` state was added in Task 3.)

- [ ] **Step 4: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 5: Manual check**

Ask operator: from the Agents tab, click **+ New**. Confirm the co-pilot drawer opens on a fresh "New agent" thread and immediately asks "What should this agent focus on?" — answering the two prompts (task, then name) creates a new spawned agent that then appears in the grid.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/CoPilotDrawer.tsx web/src/App.tsx
git commit -m "feat(web): + New opens chat-first guided agent creation"
```

---

### Task 9: Final build verification

- [ ] **Step 1: Full typecheck + production build**

Run: `cd web && bun run typecheck && bun run build`
Expected: both PASS (no type errors, build emits `dist/`).

- [ ] **Step 2: Final screenshot pass**

Ask the operator for screenshots of: Agents grid (primary + spawned), primary detail across all 5 sections, a spawned detail across all 5 sections, and the + New chat flow. Confirm no fake numbers on spawned agents.

- [ ] **Step 3: Commit any build-driven fixes (if needed)**

```bash
git add -A && git commit -m "chore(web): build verification for agent detail cockpit"
```

---

## Self-Review

**Spec coverage:**
- §3 five sections → Tasks 4–7 ✓ · §4 files → Tasks 2–7 ✓ · §5 data sources → Tasks 4–7 ✓ · §6 winning knobs → Task 7 ✓ · §6.1 `spawnedAgents.update` → Task 1 ✓ · §7 chat-first create → Tasks 3 + 8 ✓ · §2 primary card → Task 3 ✓ · §8 error handling (toasts/empty states) → Tasks 5,7 ✓ · §9 testing (typecheck/build/screenshot) → Tasks 9 + per-task ✓.
- Omitted-by-design (SOL gates, slippage/max-open live knobs, spawned PnL) — correctly absent.

**Placeholder scan:** No TBD/TODO; every code step has full code. The five stubs in Task 2 are explicitly temporary and each is replaced by a named later task.

**Type consistency:** `DetailAgent`/`DetailSection`/`AgentKind`/`SECTION_ORDER`/`sectionLabel` defined in Task 2, consumed identically in Tasks 2–7. `agent.id` typed `Id<"spawned_agents">` and guarded with `"skip"` before every spawned query. `spawnedAgents.update` args in Task 1 match the call in Task 7. `copilotStartSpawn` added in Task 3, consumed in Task 8. Query signatures (`trades.recent`/`positions.open`/`decisions.recent`/`decisions.latest`/`agentRuns.recent`/`approvals.listPending`/`scorecard.get`) match `convex/` exactly.
