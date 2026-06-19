# Multi-Agent Fleet + Cockpit Enhancements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-agent spawning via Co-Pilot, fleet view in sidebar + AgentsView, keyboard shortcuts (`Ctrl+K` / `Ctrl+Tab` / `Ctrl+Enter`), and interactive Pipeline controls (force-run + risk threshold edit).

**Architecture:** A new `spawned_agents` Convex table stores user-named agents linked to copilot threads. The CoPilotDrawer gains structured quick-action chips and a spawn state machine. The SideNav gets a live "My Agents" section. PipelineView gets a force-run button and inline-editable risk thresholds via existing Convex mutations.

**Tech Stack:** React + TypeScript, Convex (real-time backend), shadcn/ui, Tailwind CSS, lucide-react

## Global Constraints

- All Convex client mutations must wrap args with `withToken(args)` from `@/lib/control`
- No test framework — verify with `cd web && bunx tsc --noEmit` then browser smoke-test
- Do not touch `core/` Python, `agent/`, or any trade execution path
- Follow existing patterns: `useQuery` / `useMutation` from `convex/react`, shadcn Sheet/Button/Input
- Bun, not npm/npx
- All files under `web/src/` import Convex API as `import { api } from "../../../convex/_generated/api"` (adjust relative depth per file location)

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `convex/schema.ts` | Add `spawned_agents` table |
| Create | `convex/spawnedAgents.ts` | CRUD queries + mutations for spawned agents |
| Modify | `web/src/App.tsx` | Add `Ctrl+K` global keyboard shortcut; pass `openCopilotInSpawnMode` |
| Modify | `web/src/components/CoPilotDrawer.tsx` | Quick-action chips, spawn state machine, `initialThreadId` prop |
| Modify | `web/src/components/SideNav.tsx` | "My Agents" collapsible section |
| Modify | `web/src/views/AgentsView.tsx` | "Your Agents" second section |
| Modify | `web/src/views/PipelineView.tsx` | Force-run button + inline risk threshold edit |
| Modify | `web/src/components/AppShell.tsx` | Thread `openCopilotInSpawnMode` prop down to SideNav |

---

## Task 1: Convex — `spawned_agents` table + CRUD

**Files:**
- Modify: `convex/schema.ts` (after the `copilot_threads` table, ~line 361)
- Create: `convex/spawnedAgents.ts`

**Interfaces:**
- Produces: `api.spawnedAgents.list`, `api.spawnedAgents.create`, `api.spawnedAgents.setStatus`
- These are consumed by Tasks 3, 5, 6

- [ ] **Step 1: Add `spawned_agents` table to `convex/schema.ts`**

Open `convex/schema.ts`. After the `copilot_threads` block (around line 361), add:

```typescript
  spawned_agents: defineTable({
    name:              v.string(),
    task_summary:      v.string(),
    thread_id:         v.optional(v.id("copilot_threads")),
    status:            v.union(v.literal("active"), v.literal("idle"), v.literal("archived")),
    created_at:        v.number(),
    last_activity_ms:  v.optional(v.number()),
  })
    .index("by_status",  ["status"])
    .index("by_created", ["created_at"]),
```

- [ ] **Step 2: Create `convex/spawnedAgents.ts`**

```typescript
import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const list = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("spawned_agents")
      .withIndex("by_created")
      .order("desc")
      .filter((q) => q.neq(q.field("status"), "archived"))
      .collect();
  },
});

export const create = mutation({
  args: {
    name:         v.string(),
    task_summary: v.string(),
    thread_id:    v.optional(v.id("copilot_threads")),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("spawned_agents", {
      name:             args.name,
      task_summary:     args.task_summary,
      thread_id:        args.thread_id,
      status:           "active",
      created_at:       Date.now(),
      last_activity_ms: Date.now(),
    });
  },
});

export const setStatus = mutation({
  args: {
    id:     v.id("spawned_agents"),
    status: v.union(v.literal("active"), v.literal("idle"), v.literal("archived")),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { status: args.status });
  },
});

export const updateActivity = mutation({
  args: { id: v.id("spawned_agents") },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { last_activity_ms: Date.now() });
  },
});
```

- [ ] **Step 3: Type-check**

```bash
cd /root/claude/projects/alien-trade && bunx convex dev --once 2>&1 | tail -20
```

Expected: no errors, `spawned_agents` table appears in Convex dashboard.

- [ ] **Step 4: Commit**

```bash
git add convex/schema.ts convex/spawnedAgents.ts
git commit -m "feat(convex): spawned_agents table + CRUD mutations"
```

---

## Task 2: Keyboard shortcuts — `Ctrl+K`, `Ctrl+Tab`, `Ctrl+Enter` + hover hints

**Files:**
- Modify: `web/src/App.tsx`
- Modify: `web/src/components/CoPilotDrawer.tsx`
- Modify: `web/src/components/SideNav.tsx`

**Interfaces:**
- Consumes: `setCopilotOpen` already in App.tsx state
- Produces: `onCopilotThreadCycle` callback prop on CoPilotDrawer (cycles to next/prev thread)

- [ ] **Step 1: Add `Ctrl+K` global shortcut in `App.tsx`**

In `App.tsx`, find the existing `useEffect` blocks (around line 207). Add a new one after them:

```typescript
// Global keyboard shortcuts
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key === "k") {
      e.preventDefault();
      setCopilotOpen((o) => !o);
    }
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, []);
```

- [ ] **Step 2: Add `Ctrl+Tab` thread-cycling in `App.tsx`**

Add a `copilotCycleRef` so App can tell the drawer to cycle threads. Replace the above effect with:

```typescript
const copilotCycleRef = useRef<((dir: 1 | -1) => void) | null>(null);

useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key === "k") { e.preventDefault(); setCopilotOpen((o) => !o); return; }
    if (copilotOpen && mod && e.key === "Tab") {
      e.preventDefault();
      copilotCycleRef.current?.(e.shiftKey ? -1 : 1);
    }
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, [copilotOpen]);
```

Then pass `onCycleThread` to CoPilotDrawer in the JSX:

```tsx
<CoPilotDrawer
  isOpen={copilotOpen}
  onClose={() => { setCopilotOpen(false); setCopilotPrefill(""); }}
  prefill={copilotPrefill}
  onRegisterCycle={(fn) => { copilotCycleRef.current = fn; }}
/>
```

- [ ] **Step 3: Accept `onRegisterCycle` in `CoPilotDrawer.tsx`**

In `CoPilotDrawer.tsx`, update the Props type:

```typescript
type Props = {
  isOpen: boolean;
  onClose: () => void;
  prefill?: string;
  initialThreadId?: Id<"copilot_threads">;
  onRegisterCycle?: (fn: (dir: 1 | -1) => void) => void;
};
```

Inside the component, register the cycle function using `useEffect`:

```typescript
// Register Ctrl+Tab thread cycling with parent
useEffect(() => {
  if (!onRegisterCycle) return;
  onRegisterCycle((dir) => {
    const all = [null, ...(threads as ThreadDoc[]).map((t) => t._id as Id<"copilot_threads">)];
    const current = all.indexOf(activeThreadId);
    const next = (current + dir + all.length) % all.length;
    setActiveThreadId(all[next]);
  });
}, [onRegisterCycle, threads, activeThreadId]);
```

- [ ] **Step 4: Add `Ctrl+Enter` to send in `CoPilotDrawer.tsx`**

Find the input `onKeyDown` handler (around line 343):

```typescript
onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
```

Change to:

```typescript
onKeyDown={(e) => {
  if (e.key === "Enter" && (!e.shiftKey || e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    send();
  }
}}
```

Also update the placeholder text on the same input:

```typescript
placeholder="Ask the agent… (⌃↵ to send)"
```

- [ ] **Step 5: Add `⌃K` hint to Co-Pilot tooltip in `SideNav.tsx`**

Find the Co-Pilot `TooltipContent` (around line 122):

```tsx
<TooltipContent side="right">Co-Pilot</TooltipContent>
```

Change to:

```tsx
<TooltipContent side="right">
  <span className="flex items-center gap-2">
    Co-Pilot
    <kbd className="font-mono text-[10px] bg-elevated border border-border rounded px-1 py-0.5">⌃K</kbd>
  </span>
</TooltipContent>
```

- [ ] **Step 6: Type-check**

```bash
cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step 7: Browser smoke-test**

Open app → press `Ctrl+K` → Co-Pilot opens. Press again → closes. With Co-Pilot open, press `Ctrl+Tab` → cycles to next thread. Hover Co-Pilot icon in sidebar → tooltip shows `⌃K`. Input shows `⌃↵ to send` hint.

- [ ] **Step 8: Commit**

```bash
git add web/src/App.tsx web/src/components/CoPilotDrawer.tsx web/src/components/SideNav.tsx
git commit -m "feat(shortcuts): Ctrl+K toggle copilot, Ctrl+Tab cycle threads, Ctrl+Enter send"
```

---

## Task 3: CoPilotDrawer — quick-action chip redesign + spawn state machine

**Files:**
- Modify: `web/src/components/CoPilotDrawer.tsx`

**Interfaces:**
- Consumes: `api.spawnedAgents.create` (from Task 1), `api.copilot.createThread` (already exists)
- Produces: new spawned agent record; `initialThreadId` prop (consumed by Tasks 5, 6)

- [ ] **Step 1: Add spawn state + `useMutation` for `spawnedAgents.create`**

At the top of `CoPilotDrawer`, add to the imports:

```typescript
import type { Id } from "../../../convex/_generated/dataModel";
```

(Already imported — verify it's there. If yes, skip.)

Add to the Props type (merge with Task 2's change):

```typescript
  initialThreadId?: Id<"copilot_threads">;
```

Inside the component function, after the existing state declarations, add:

```typescript
type SpawnStep = "idle" | "awaiting_task" | "awaiting_name";
const [spawnStep, setSpawnStep]           = useState<SpawnStep>("idle");
const [spawnTaskSummary, setSpawnTask]    = useState("");

const createAgent = useMutation(api.spawnedAgents.create);
```

- [ ] **Step 2: Apply `initialThreadId` prop**

Find where `activeThreadId` is initialised (around line 89):

```typescript
const [activeThreadId, setActiveThreadId] = useState<Id<"copilot_threads"> | null>(null);
```

Change to:

```typescript
const [activeThreadId, setActiveThreadId] = useState<Id<"copilot_threads"> | null>(
  initialThreadId ?? null
);
```

Add a `useEffect` to sync if prop changes:

```typescript
useEffect(() => {
  if (initialThreadId) setActiveThreadId(initialThreadId);
}, [initialThreadId]);
```

- [ ] **Step 3: Replace `SUGGESTION_CARDS` with new quick-action chips**

Delete the entire `SUGGESTION_CARDS` const at the top of the file and replace with:

```typescript
const QUICK_ACTIONS = [
  { id: "spawn",       emoji: "🤖", label: "Spawn a new agent",   sub: "Set up a new focused co-pilot" },
  { id: "configure",   emoji: "⚙️", label: "Configure strategy",   sub: "Tune risk params or strategy" },
  { id: "performance", emoji: "📊", label: "Check performance",    sub: "Ask about PnL, drawdown, trades" },
  { id: "custom",      emoji: "➕", label: "Type my own…",         sub: null },
] as const;
type QuickActionId = typeof QUICK_ACTIONS[number]["id"];
```

- [ ] **Step 4: Replace chip rendering in the component JSX**

Find the block that renders `SUGGESTION_CARDS` (around line 317–333). Replace it entirely:

```tsx
{msgs.length === 0 && !pendingAction && spawnStep === "idle" && (
  <div className="space-y-1.5 mb-2">
    {QUICK_ACTIONS.map((card) => (
      <button
        key={card.id}
        onClick={() => handleQuickAction(card.id)}
        className="w-full text-left border border-border/60 rounded-xl px-3 py-2.5 hover:bg-elevated/70 hover:border-border transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-[16px]">{card.emoji}</span>
          <div>
            <p className="font-mono text-[12px] text-text font-bold">{card.label}</p>
            {card.sub && <p className="font-mono text-[10px] text-muted-fg mt-0.5">{card.sub}</p>}
          </div>
        </div>
      </button>
    ))}
  </div>
)}
```

- [ ] **Step 5: Add `handleQuickAction` and the spawn-aware `send()` intercept**

Add the handler function inside the component, before `return`:

```typescript
const handleQuickAction = (id: QuickActionId) => {
  if (id === "spawn") {
    // Start spawn flow — inject a Co-Pilot message asking for the task
    addMessage(withToken({
      role: "assistant",
      content: "Sure! What should this agent focus on? Describe its job in one or two sentences.",
      sources_json: "[]",
      thread_id: activeThreadId ?? undefined,
    }));
    setSpawnStep("awaiting_task");
  } else if (id === "custom") {
    inputRef.current?.focus();
  } else {
    const prefills: Record<string, string> = {
      configure:   "Help me configure the strategy and risk parameters.",
      performance: "How is the agent performing? Show me PnL and drawdown.",
    };
    setQuestion(prefills[id] ?? "");
    inputRef.current?.focus();
  }
};
```

- [ ] **Step 6: Intercept spawn messages inside `send()`**

At the top of the existing `send` function (around line 162), add spawn interception before the normal `ask()` path:

```typescript
const send = async (q = question) => {
  const text = q.trim();
  if (!text || loading) return;
  setQuestion("");

  // ── Spawn state machine ────────────────────────────────────
  if (spawnStep === "awaiting_task") {
    setSpawnTask(text);
    await addMessage(withToken({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
    await addMessage(withToken({
      role: "assistant",
      content: "Got it. What should I call this agent?",
      sources_json: "[]",
      thread_id: activeThreadId ?? undefined,
    }));
    setSpawnStep("awaiting_name");
    return;
  }

  if (spawnStep === "awaiting_name") {
    const name = text;
    await addMessage(withToken({ role: "user", content: name, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
    // Create the agent record
    const agentId = await createAgent(withToken({
      name,
      task_summary: spawnTaskSummary,
      thread_id: activeThreadId ?? undefined,
    }));
    await addMessage(withToken({
      role: "assistant",
      content: `✅ **${name}** is live. I'll work on: "${spawnTaskSummary}". You can find this agent in the Agents tab and your sidebar.`,
      sources_json: "[]",
      thread_id: activeThreadId ?? undefined,
    }));
    setSpawnStep("idle");
    setSpawnTask("");
    console.log("Spawned agent:", agentId);
    return;
  }
  // ── End spawn state machine ────────────────────────────────

  setLoading(true);
  // ... rest of existing send() unchanged
```

Note: `createAgent` needs `withToken`. Add `withToken` import if not already there (it's already imported in the file at line 9).

Also add `withToken` to the `createAgent` call — the mutation is authenticated. Since `spawnedAgents.create` doesn't validate the control token server-side in our Task 1 implementation, this is safe either way, but wrap it for consistency: `createAgent(withToken({ name, task_summary: spawnTaskSummary, thread_id: activeThreadId ?? undefined }))`.

- [ ] **Step 7: Type-check**

```bash
cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step 8: Browser smoke-test**

Open Co-Pilot (new thread) → see 4 chip buttons. Click "🤖 Spawn a new agent" → Co-Pilot says "What should this agent focus on?". Type a task → Co-Pilot asks for a name. Type a name → Co-Pilot confirms. Check Convex dashboard → row in `spawned_agents` table.

- [ ] **Step 9: Commit**

```bash
git add web/src/components/CoPilotDrawer.tsx
git commit -m "feat(copilot): quick-action chips + multi-agent spawn state machine"
```

---

## Task 4: Sidebar — "My Agents" section in `SideNav.tsx`

**Files:**
- Modify: `web/src/components/SideNav.tsx`
- Modify: `web/src/components/AppShell.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- Consumes: `api.spawnedAgents.list` (Task 1), `onAgentOpen(threadId)` callback from App
- Produces: clicking an agent row → opens CoPilotDrawer on that thread (via `onAgentOpen`)

- [ ] **Step 1: Add `onAgentOpen` + `onSpawnAgent` props to `SideNav`**

In `SideNav.tsx`, update the Props type (around line 30):

```typescript
type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
  onTour: () => void;
  onAgentOpen?: (threadId: string) => void;
  onSpawnAgent?: () => void;
};
```

Update the function signature to destructure them:

```typescript
export function SideNav({ active, onSelect, onCopilot, onTour, onAgentOpen, onSpawnAgent }: Props) {
```

- [ ] **Step 2: Query spawned agents inside SideNav**

After the existing `events` query (around line 34), add:

```typescript
const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
```

Add the import at the top of the file:

```typescript
import { Cpu } from "lucide-react"; // already likely imported — just verify
```

- [ ] **Step 3: Add "My Agents" section between nav items and the spacer**

Find the `<div className="flex-1" />` spacer (around line 97). Insert the My Agents block just before it:

```tsx
{/* My Agents section */}
{spawnedAgents.length > 0 && (
  <>
    <div className="w-full px-2 py-1">
      <div className="h-px bg-border/50 w-full" />
    </div>
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="w-full px-1">
          <span className="block font-mono text-[8px] tracking-[0.18em] uppercase text-muted-fg/50 text-center px-1 pb-0.5">
            agents
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent side="right">Your spawned agents</TooltipContent>
    </Tooltip>
    {spawnedAgents.slice(0, 5).map((agent) => (
      <Tooltip key={agent._id}>
        <TooltipTrigger asChild>
          <button
            onClick={() => onAgentOpen?.(agent.thread_id ?? "")}
            className="relative w-10 h-8 rounded-[8px] flex items-center justify-center transition-colors cursor-pointer text-muted-fg hover:bg-elevated hover:text-text group"
            aria-label={agent.name}
          >
            <span
              className={cn(
                "w-2 h-2 rounded-full flex-shrink-0",
                agent.status === "active" ? "bg-green" : "bg-muted-fg/30"
              )}
              style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}}
            />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">
          <span className="font-mono text-[11px]">{agent.name}</span>
          <span className="block font-mono text-[10px] text-muted-fg truncate max-w-[160px]">
            {agent.task_summary}
          </span>
        </TooltipContent>
      </Tooltip>
    ))}
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={() => onSpawnAgent?.()}
          className="w-10 h-7 rounded-[8px] flex items-center justify-center text-muted-fg/40 hover:text-muted-fg hover:bg-elevated transition-colors cursor-pointer text-[16px]"
          aria-label="Spawn agent"
        >
          +
        </button>
      </TooltipTrigger>
      <TooltipContent side="right">Spawn a new agent</TooltipContent>
    </Tooltip>
  </>
)}

<div className="flex-1" />
```

- [ ] **Step 4: Thread `onAgentOpen` + `onSpawnAgent` through `AppShell`**

In `AppShell.tsx`, add to Props type:

```typescript
  onAgentOpen?: (threadId: string) => void;
  onSpawnAgent?: () => void;
```

Destructure them and pass to `SideNav`:

```tsx
<SideNav
  active={activeView}
  onSelect={onViewChange}
  onCopilot={onCopilot}
  onTour={onTour}
  onAgentOpen={onAgentOpen}
  onSpawnAgent={onSpawnAgent}
/>
```

- [ ] **Step 5: Wire in `App.tsx`**

In `App.tsx`, add `copilotThreadId` state:

```typescript
const [copilotThreadId, setCopilotThreadId] = useState<string | undefined>(undefined);
```

Pass to AppShell:

```tsx
<AppShell
  ...existing props...
  onAgentOpen={(threadId) => {
    setCopilotThreadId(threadId);
    setCopilotOpen(true);
  }}
  onSpawnAgent={() => {
    setCopilotThreadId(undefined);
    setCopilotOpen(true);
  }}
>
```

Pass `initialThreadId` to CoPilotDrawer:

```tsx
<CoPilotDrawer
  isOpen={copilotOpen}
  onClose={() => { setCopilotOpen(false); setCopilotPrefill(""); setCopilotThreadId(undefined); }}
  prefill={copilotPrefill}
  initialThreadId={copilotThreadId as Id<"copilot_threads"> | undefined}
  onRegisterCycle={(fn) => { copilotCycleRef.current = fn; }}
/>
```

Add the import for `Id` at the top of App.tsx:

```typescript
import type { Id } from "../../convex/_generated/dataModel";
```

- [ ] **Step 6: Type-check**

```bash
cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step 7: Browser smoke-test**

Spawn an agent (from Task 3). Reload → a green dot appears in the SideNav below the nav items. Hover → tooltip shows name + task. Click → CoPilotDrawer opens on that agent's thread. Click "+" dot → CoPilotDrawer opens in spawn mode with chips.

- [ ] **Step 8: Commit**

```bash
git add web/src/components/SideNav.tsx web/src/components/AppShell.tsx web/src/App.tsx
git commit -m "feat(sidebar): My Agents section with live dots + spawn shortcut"
```

---

## Task 5: AgentsView — "Your Agents" fleet section

**Files:**
- Modify: `web/src/views/AgentsView.tsx`

**Interfaces:**
- Consumes: `api.spawnedAgents.list` (Task 1)
- Consumes: `onAgentOpen(threadId)` — needs to be added to AgentsView Props and wired in App.tsx

- [ ] **Step 1: Update AgentsView Props and add query**

In `AgentsView.tsx`, update the Props type:

```typescript
type Props = {
  onAgentClick: (name: string) => void;
  onAgentOpen?: (threadId: string) => void;
};
```

Inside the component, add the spawned agents query after the existing `roster` query:

```typescript
const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
```

Add the import:

```typescript
import { api } from "../../../convex/_generated/api";
// api is already imported — just add spawnedAgents usage
```

- [ ] **Step 2: Add "Your Agents" section to the JSX**

After the closing `</div>` of the existing agent grid (around line 37), add:

```tsx
{/* Your Agents — user-spawned fleet */}
<div className="mt-8">
  <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-3 flex items-center gap-2">
    <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
    Your Agents
  </div>

  {spawnedAgents.length === 0 ? (
    <div className="panel p-6 text-center">
      <p className="font-mono text-[13px] text-muted-fg mb-1">No agents yet.</p>
      <p className="font-mono text-[11px] text-muted-fg/60">
        Open the Co-Pilot and say what job you need done.
      </p>
    </div>
  ) : (
    <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
      {spawnedAgents.map((agent) => {
        const timeAgo = agent.last_activity_ms
          ? Math.round((Date.now() - agent.last_activity_ms) / 60000)
          : null;
        return (
          <div
            key={agent._id}
            className="panel p-4 flex flex-col gap-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5",
                    agent.status === "active" ? "bg-green" : "bg-muted-fg/30"
                  )}
                  style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}}
                />
                <span className="font-display text-[14px] font-bold text-text">{agent.name}</span>
              </div>
              <span className={cn(
                "font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest flex-shrink-0",
                agent.status === "active"
                  ? "bg-green/12 text-green border-green/25"
                  : "bg-muted-fg/8 text-muted-fg border-muted-fg/20"
              )}>
                {agent.status}
              </span>
            </div>

            <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed line-clamp-2">
              {agent.task_summary}
            </p>

            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-muted-fg/50">
                {timeAgo != null ? `${timeAgo}m ago` : "just now"}
              </span>
              <button
                onClick={() => onAgentOpen?.(agent.thread_id ?? "")}
                className="font-mono text-[11px] text-purple hover:text-purple/80 transition-colors cursor-pointer flex items-center gap-1"
              >
                Open Chat →
              </button>
            </div>
          </div>
        );
      })}
    </div>
  )}
</div>
```

Add `cn` import at the top (verify it's already there):

```typescript
import { cn } from "@/lib/utils";
```

- [ ] **Step 3: Wire `onAgentOpen` in `App.tsx`**

Find where `AgentsView` is rendered in `App.tsx` (around line 286):

```tsx
case "agents": return <AgentsView onAgentClick={onAgentClick} />;
```

Change to:

```tsx
case "agents": return (
  <AgentsView
    onAgentClick={onAgentClick}
    onAgentOpen={(threadId) => {
      setCopilotThreadId(threadId);
      setCopilotOpen(true);
    }}
  />
);
```

- [ ] **Step 4: Type-check**

```bash
cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step 5: Browser smoke-test**

Navigate to Agents tab → see "System Agents" section (existing cards) + "Your Agents" section below. If no agents yet: empty state message. After spawning one (Task 3): card appears with name, task, status dot, "Open Chat →" button. Clicking it opens CoPilotDrawer on that conversation.

- [ ] **Step 6: Commit**

```bash
git add web/src/views/AgentsView.tsx web/src/App.tsx
git commit -m "feat(agents): Your Agents fleet section with live cards"
```

---

## Task 6: Pipeline — Force-run button + inline risk threshold edit

**Files:**
- Modify: `web/src/views/PipelineView.tsx`

**Interfaces:**
- Consumes: `api.agentCommands.enqueue` (already exists in Convex), `api.config.updateLimits` (already exists, used in CoPilotDrawer)
- Consumes: `withToken` from `@/lib/control`

- [ ] **Step 1: Add mutations to `PipelineView`**

At the top of `PipelineView.tsx`, add imports:

```typescript
import { useMutation } from "convex/react";
import { withToken } from "@/lib/control";
import { useState } from "react";
import { Play, Pencil, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
```

Inside the component, add mutations after the existing queries:

```typescript
const enqueueCommand = useMutation(api.agentCommands.enqueue);
const updateLimits   = useMutation(api.config.updateLimits);
```

Also add local edit state:

```typescript
const [editingField, setEditingField]     = useState<string | null>(null);
const [editValue, setEditValue]           = useState("");
const [forceRunning, setForceRunning]     = useState(false);
```

- [ ] **Step 2: Add "Run now" button in the Pipeline header**

Find the header `<div className="mb-2">` block (around line 87). Add the button inline with the title:

```tsx
<div className="flex items-center justify-between mb-2">
  <div>
    <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
      <span className="h-[2px] w-4 bg-cyan rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--cyan)" }} />
      Deterministic Pipeline
    </div>
    <div className="flex items-baseline gap-3">
      <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Decision Pipeline</h1>
      {ageMs != null && (
        <span className="font-mono text-[11px] text-muted-fg">last cycle {ageSec}s ago</span>
      )}
    </div>
  </div>
  <Button
    size="sm"
    variant="outline"
    disabled={forceRunning}
    onClick={async () => {
      setForceRunning(true);
      await enqueueCommand(withToken({
        command_type: "force_cycle",
        params: "{}",
      }));
      setTimeout(() => setForceRunning(false), 3000);
    }}
    className="flex items-center gap-1.5 font-mono text-[11px] border-cyan/30 text-cyan hover:bg-cyan/10 cursor-pointer"
  >
    <Play className="w-3 h-3" />
    {forceRunning ? "Queued…" : "Run now"}
  </Button>
</div>
```

Replace the old header `<div className="mb-2">` with this new flex wrapper (keep the content, just wrap it).

- [ ] **Step 3: Make Stage 4 risk fields inline-editable**

Find the Stage 4 block (around line 144). Replace the `rows` prop with an inline implementation using editable fields. Replace the entire Stage 4 call:

```tsx
{/* Stage 4 — Risk Check (inline editable) */}
<div className="flex gap-4 items-start">
  <div className="flex flex-col items-center gap-1 flex-shrink-0">
    <div className="w-7 h-7 rounded-full border border-border flex items-center justify-center font-mono text-[11px] text-muted-fg">4</div>
    <div className="w-px flex-1 bg-border min-h-[24px]" />
  </div>
  <div className="panel flex-1 mb-3 p-3">
    <div className="flex items-center justify-between mb-2">
      <span className="font-display text-[13px] font-bold text-text">Risk Check</span>
      <StageBadge status={riskState?.circuit_breaker_active ? "block" : riskState ? "pass" : "stale"} />
    </div>
    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
      {/* Editable: Drawdown */}
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[11px] text-muted-fg">Drawdown</span>
        {editingField === "drawdown" ? (
          <form onSubmit={async (e) => {
            e.preventDefault();
            const val = parseFloat(editValue);
            if (!isNaN(val)) await updateLimits(withToken({ max_drawdown_pct: val / 100 }));
            setEditingField(null);
          }} className="flex items-center gap-1">
            <Input
              autoFocus
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => setEditingField(null)}
              className="w-16 h-5 text-[11px] font-mono px-1 py-0 bg-bg border-green/50 text-text"
            />
            <span className="font-mono text-[10px] text-muted-fg">%</span>
            <button type="submit" className="text-green cursor-pointer"><Check className="w-3 h-3" /></button>
          </form>
        ) : (
          <button
            className="flex items-center gap-1 group cursor-pointer"
            onClick={() => { setEditingField("drawdown"); setEditValue(riskState ? (riskState.current_drawdown_pct * 100).toFixed(1) : ""); }}
          >
            <span className="font-mono text-[12px] text-text tabular-nums">
              {riskState ? `${(riskState.current_drawdown_pct * 100).toFixed(1)}%` : "—"}
            </span>
            <Pencil className="w-2.5 h-2.5 text-muted-fg/0 group-hover:text-muted-fg/60 transition-colors" />
          </button>
        )}
      </div>

      {/* Editable: Daily loss */}
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[11px] text-muted-fg">Daily loss</span>
        {editingField === "daily_loss" ? (
          <form onSubmit={async (e) => {
            e.preventDefault();
            const val = parseFloat(editValue);
            if (!isNaN(val)) await updateLimits(withToken({ max_daily_loss_usd: val }));
            setEditingField(null);
          }} className="flex items-center gap-1">
            <span className="font-mono text-[10px] text-muted-fg">$</span>
            <Input
              autoFocus
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => setEditingField(null)}
              className="w-16 h-5 text-[11px] font-mono px-1 py-0 bg-bg border-green/50 text-text"
            />
            <button type="submit" className="text-green cursor-pointer"><Check className="w-3 h-3" /></button>
          </form>
        ) : (
          <button
            className="flex items-center gap-1 group cursor-pointer"
            onClick={() => { setEditingField("daily_loss"); setEditValue(riskState ? riskState.daily_loss_usd.toFixed(2) : ""); }}
          >
            <span className="font-mono text-[12px] text-text tabular-nums">
              {riskState ? usd(riskState.daily_loss_usd) : "—"}
            </span>
            <Pencil className="w-2.5 h-2.5 text-muted-fg/0 group-hover:text-muted-fg/60 transition-colors" />
          </button>
        )}
      </div>

      {/* Read-only: Exposure */}
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[11px] text-muted-fg">Exposure</span>
        <span className="font-mono text-[12px] text-text tabular-nums">{riskState ? usd(riskState.open_exposure_usd) : "—"}</span>
      </div>

      {/* Read-only: Circuit breaker */}
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[11px] text-muted-fg">Breaker</span>
        <span className={cn("font-mono text-[12px] tabular-nums", riskState?.circuit_breaker_active ? "text-red" : "text-muted-fg")}>
          {riskState?.circuit_breaker_active ? "ACTIVE" : "off"}
        </span>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Verify `updateLimits` mutation exists and accepts these fields**

```bash
grep -n "max_drawdown_pct\|max_daily_loss_usd\|updateLimits" /root/claude/projects/alien-trade/convex/config.ts | head -20
```

If `updateLimits` does not accept those field names, check the actual field names and adjust the mutation calls in Step 3 to match.

- [ ] **Step 5: Type-check**

```bash
cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step 6: Browser smoke-test**

Open Pipeline view → "Run now" button visible in header. Click it → button shows "Queued…" for 3s → check Convex dashboard for a new `agent_commands` row with `command_type: "force_cycle"`. Hover over Drawdown or Daily loss values → pencil icon appears. Click → inline input. Type new value → press Enter → value saves (verify in Convex config table).

- [ ] **Step 7: Commit**

```bash
git add web/src/views/PipelineView.tsx
git commit -m "feat(pipeline): force-run button + inline risk threshold edit"
```

---

## Self-Review Checklist

### Spec coverage

| Spec section | Task |
|---|---|
| A — spawned_agents schema | Task 1 |
| A — list/create/setStatus | Task 1 |
| A — Spawn flow (chip → task → name → agent) | Task 3 |
| A — Sidebar My Agents section | Task 4 |
| A — AgentsView Your Agents section | Task 5 |
| A — initialThreadId prop | Tasks 3, 4 |
| B — Ctrl+K toggle | Task 2 |
| B — Ctrl+Tab cycle threads | Task 2 |
| B — Ctrl+Enter send | Task 2 |
| B — ⌃K hover hint | Task 2 |
| C — Force-run button (Layer 1) | Task 6 |
| C — Risk threshold inline edit (Layer 2) | Task 6 |
| C — Layer 3 signal sliders | Deferred (post-freeze per spec) |
| D — Watchlist workstream G | Separate plan (not in scope here) |
| E — Mobile reachability | No change needed (already done) |

All spec requirements covered or intentionally deferred.

### Type consistency

- `api.spawnedAgents.create` called with `{ name, task_summary, thread_id }` — matches Task 1 mutation args ✅
- `api.spawnedAgents.list` returns array with `{ _id, name, task_summary, thread_id, status, last_activity_ms }` — used correctly in Tasks 4 and 5 ✅
- `onAgentOpen(threadId: string)` — consistent across AppShell, SideNav, AgentsView, App ✅
- `copilotCycleRef` registered by CoPilotDrawer, invoked in App — types align ✅
- `enqueueCommand` called with `{ command_type, params }` — matches schema (Task 6 Step 4 has a verification step in case field names differ) ✅
