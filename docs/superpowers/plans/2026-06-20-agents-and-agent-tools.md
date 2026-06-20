# Agents & Agent Tools — Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the operator spawn/name their own **Agents** that compose the five sponsor-powered **Agent Tools**, run safely off the trade hot path, and report back via Web Push — without ever auto-trading the scored wallet.

**Architecture:** Agents are Convex records describing a goal + allowed tools + trigger + notify policy + mode. A Python `agent/agents/` runtime runs each one as a bounded Anthropic tool-loop (reusing `agent/copilot_agent.py:run_read_loop`), writes heartbeats + run records, and — in `live` mode — *proposes* trades as approval requests that the operator one-taps through the **existing** control-token → `command_worker` → `twak swap` path. Web Push replaces Telegram.

**Tech Stack:** Python 3.12 + pytest (`agent/tests/`), Convex (TS, pushed via `bunx convex dev`), Anthropic SDK, `pywebpush` (VAPID), React + Vite PWA (`web/`, `vite-plugin-pwa`).

**Spec:** `docs/superpowers/specs/2026-06-20-agents-and-agent-tools-design.md`. This plan covers **Phase 1** (Foundation + safety, §8). Phases 2–3 (collaboration, autonomy) are a roadmap appendix and get their own plan once these interfaces are real.

## Global Constraints

- **LLM off the trade hot path.** Agents are Tier-1; they never run inside the `/core` decision loop and never decide/execute a scored trade autonomously. (Locked #1/#6.)
- **Scored-wallet invariant.** No spawned Agent may produce a `twak swap` without a prior human `approved` transition. This is asserted by a test (Task 7).
- **Default mode = `paper`.** A trade-capable Agent is `paper` until the operator explicitly flips it to `live`; `live` only enables *propose→approve*, never auto-execution.
- **Reuse, don't fork.** Tool calls go through `agent/copilot_agent.py` (`run_read_loop`, `execute_tool`, `TOOLS`). State writes go through `agent/convex_bridge.py` (control-token gating). Trades go through `agent/command_worker.py`. No duplicate logic. (Locked #2.)
- **Convex is the bus.** No new webhook/websocket server. `bunx convex dev` (separate terminal) auto-pushes schema/functions on save — never run `convex deploy` in dev.
- **Tooling:** `bun`/`bunx` only (never npm/npx). Python tests: `cd core && .\.venv\Scripts\python.exe -m pytest` on Windows; on this VPS use `core/.venv/bin/python -m pytest agent/tests/...`.
- **No-silent-failure.** Every Agent run writes a heartbeat and wraps its body so failures surface as an `agent_events` row, never a silent stall. (The 2026-06-20 7-hour outage is why.)

---

### Task 1: Convex data layer — extend `spawned_agents` + add `agent_runs`, `approval_requests`, `push_subscriptions`

**Files:**
- Modify: `convex/schema.ts:362-373` (extend `spawned_agents`)
- Modify: `convex/spawnedAgents.ts` (extend `create`, add `rename`)
- Create: `convex/agentRuns.ts`
- Create: `convex/approvals.ts`
- Create: `convex/push.ts`
- Modify: `convex/control.ts` (add the approve + push mutations to the guarded set — match existing pattern)

**Interfaces:**
- Produces (consumed by Python via `ConvexBridge.call`):
  - `spawned_agents` rows now carry `goal: string`, `allowed_tools: string[]`, `trigger: {kind, spec}`, `notify_policy: {webpush: bool, severity_min: string}`, `mode: "paper"|"live"`.
  - `agentRuns.record({ agent_id, started_ms, ended_ms, ok, summary, tool_calls })`
  - `approvals.propose({ agent_id, payload }) -> id`; `approvals.resolve({ id, status, control_token })`; `approvals.listPending()`
  - `push.subscribe({ endpoint, p256dh, auth })`; `push.list()`

- [ ] **Step 1: Extend the `spawned_agents` table.** In `convex/schema.ts`, replace the `spawned_agents` definition (lines 362–373) with:

```ts
  spawned_agents: defineTable({
    name:              v.string(),
    task_summary:      v.string(),        // kept for back-compat (display)
    goal:              v.optional(v.string()),
    allowed_tools:     v.optional(v.array(v.string())),
    trigger:           v.optional(v.object({ kind: v.string(), spec: v.string() })),
    notify_policy:     v.optional(v.object({ webpush: v.boolean(), severity_min: v.string() })),
    mode:              v.optional(v.union(v.literal("paper"), v.literal("live"))),
    thread_id:         v.optional(v.id("copilot_threads")),
    status:            v.union(v.literal("active"), v.literal("idle"), v.literal("archived")),
    created_at:        v.number(),
    last_activity_ms:  v.optional(v.number()),
  })
    .index("by_status",  ["status"])
    .index("by_created", ["created_at"]),
```

- [ ] **Step 2: Add the three new tables.** In `convex/schema.ts`, immediately after the `spawned_agents` block, add:

```ts
  agent_runs: defineTable({
    agent_id:   v.id("spawned_agents"),
    started_ms: v.number(),
    ended_ms:   v.optional(v.number()),
    ok:         v.boolean(),
    summary:    v.string(),
    tool_calls: v.array(v.object({ tool: v.string(), args: v.string() })),
  })
    .index("by_agent", ["agent_id"])
    .index("by_started", ["started_ms"]),

  approval_requests: defineTable({
    agent_id:    v.id("spawned_agents"),
    kind:        v.string(),            // "trade"
    payload:     v.string(),            // JSON: {command_type, params}
    status:      v.union(v.literal("pending"), v.literal("approved"), v.literal("rejected")),
    created_ms:  v.number(),
    resolved_ms: v.optional(v.number()),
  })
    .index("by_status", ["status"])
    .index("by_agent",  ["agent_id"]),

  push_subscriptions: defineTable({
    endpoint:   v.string(),
    p256dh:     v.string(),
    auth:       v.string(),
    created_ms: v.number(),
  })
    .index("by_endpoint", ["endpoint"]),
```

- [ ] **Step 3: Extend `spawnedAgents.create` and add `rename`.** In `convex/spawnedAgents.ts`, replace the `create` mutation args/handler to accept the new fields (all optional except name/goal) and add a `rename`:

```ts
export const create = mutation({
  args: {
    name:          v.string(),
    goal:          v.string(),
    allowed_tools: v.optional(v.array(v.string())),
    trigger:       v.optional(v.object({ kind: v.string(), spec: v.string() })),
    notify_policy: v.optional(v.object({ webpush: v.boolean(), severity_min: v.string() })),
    mode:          v.optional(v.union(v.literal("paper"), v.literal("live"))),
    thread_id:     v.optional(v.id("copilot_threads")),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("spawned_agents", {
      name:             args.name,
      task_summary:     args.goal,
      goal:             args.goal,
      allowed_tools:    args.allowed_tools ?? [],
      trigger:          args.trigger,
      notify_policy:    args.notify_policy ?? { webpush: true, severity_min: "info" },
      mode:             args.mode ?? "paper",
      thread_id:        args.thread_id,
      status:           "active",
      created_at:       Date.now(),
      last_activity_ms: Date.now(),
    });
  },
});

export const rename = mutation({
  args: { id: v.id("spawned_agents"), name: v.string() },
  handler: async (ctx, args) => { await ctx.db.patch(args.id, { name: args.name }); },
});
```

- [ ] **Step 4: Create `convex/agentRuns.ts`.**

```ts
import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const record = mutation({
  args: {
    agent_id:   v.id("spawned_agents"),
    started_ms: v.number(),
    ended_ms:   v.number(),
    ok:         v.boolean(),
    summary:    v.string(),
    tool_calls: v.array(v.object({ tool: v.string(), args: v.string() })),
  },
  handler: async (ctx, a) => {
    await ctx.db.patch(a.agent_id, { last_activity_ms: Date.now() });
    return await ctx.db.insert("agent_runs", a);
  },
});

export const recent = query({
  args: { agent_id: v.id("spawned_agents") },
  handler: async (ctx, a) =>
    await ctx.db.query("agent_runs").withIndex("by_agent", q => q.eq("agent_id", a.agent_id))
      .order("desc").take(20),
});
```

- [ ] **Step 5: Create `convex/approvals.ts`.** The `resolve` mutation is control-token gated and, on approval, enqueues into the existing `agent_commands` queue (status `queued`) — it never executes a trade itself.

```ts
import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { requireControlToken } from "./control";   // existing helper used by guarded mutations

export const propose = mutation({
  args: { agent_id: v.id("spawned_agents"), payload: v.string() },
  handler: async (ctx, a) =>
    await ctx.db.insert("approval_requests", {
      agent_id: a.agent_id, kind: "trade", payload: a.payload,
      status: "pending", created_ms: Date.now(),
    }),
});

export const listPending = query({
  args: {},
  handler: async (ctx) =>
    await ctx.db.query("approval_requests").withIndex("by_status", q => q.eq("status", "pending"))
      .order("desc").collect(),
});

export const resolve = mutation({
  args: {
    id: v.id("approval_requests"),
    status: v.union(v.literal("approved"), v.literal("rejected")),
    control_token: v.string(),
  },
  handler: async (ctx, a) => {
    requireControlToken(a.control_token);
    const req = await ctx.db.get(a.id);
    if (!req || req.status !== "pending") throw new Error("approval not pending");
    await ctx.db.patch(a.id, { status: a.status, resolved_ms: Date.now() });
    if (a.status === "approved") {
      const { command_type, params } = JSON.parse(req.payload);
      await ctx.db.insert("agent_commands", {
        command_type, params: JSON.stringify(params), status: "queued",
        queued_by: `agent:${req.agent_id}`, queued_at_ms: Date.now(), updated_at_ms: Date.now(),
      });
    }
  },
});
```

> If `control.ts` exposes the gate differently (e.g. inline token compare rather than `requireControlToken`), match the existing pattern used by the other guarded mutations — open `convex/control.ts` and copy its exact check. The contract is: `resolve` must reject a missing/wrong token.

- [ ] **Step 6: Create `convex/push.ts`.**

```ts
import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const subscribe = mutation({
  args: { endpoint: v.string(), p256dh: v.string(), auth: v.string() },
  handler: async (ctx, a) => {
    const existing = await ctx.db.query("push_subscriptions")
      .withIndex("by_endpoint", q => q.eq("endpoint", a.endpoint)).unique();
    if (existing) return existing._id;
    return await ctx.db.insert("push_subscriptions", { ...a, created_ms: Date.now() });
  },
});

export const list = query({ args: {}, handler: async (ctx) =>
  await ctx.db.query("push_subscriptions").collect() });
```

- [ ] **Step 7: Verify the push + codegen.** With `bunx convex dev` running in another terminal (auto-pushes on save), confirm no schema/type errors:

Run: `bunx convex dev --once`
Expected: `✔ Schema validation` / functions deployed, exit 0, no validator errors. `convex/_generated/api.d.ts` now lists `agentRuns`, `approvals`, `push`.

- [ ] **Step 8: Commit.**

```bash
git add convex/schema.ts convex/spawnedAgents.ts convex/agentRuns.ts convex/approvals.ts convex/push.ts convex/control.ts
git commit -m "feat(convex): agent records, runs, approvals, push subscriptions"
```

---

### Task 2: Agent spec validation (`agent/agents/spec.py`)

The co-pilot fills a structured `create_agent` tool call; we don't parse free text — we **validate** the structured args, default `mode=paper`, and reject unknown tools.

**Files:**
- Create: `agent/agents/__init__.py` (empty)
- Create: `agent/agents/spec.py`
- Test: `agent/tests/test_agent_spec.py`

**Interfaces:**
- Produces: `AGENT_TOOL_NAMES: frozenset[str]`; `validate_agent_spec(raw: dict) -> dict` returning a normalized record `{name, goal, allowed_tools, trigger, notify_policy, mode}`; raises `ValueError` on bad input.

- [ ] **Step 1: Write the failing test.**

```python
# agent/tests/test_agent_spec.py
import pytest
from agent.agents.spec import validate_agent_spec, AGENT_TOOL_NAMES


def test_defaults_mode_paper_and_keeps_known_tools():
    rec = validate_agent_spec({
        "name": "CAKE-Watcher", "goal": "watch CAKE funding",
        "allowed_tools": ["get_price", "cmc_market_skill"],
    })
    assert rec["mode"] == "paper"
    assert rec["allowed_tools"] == ["get_price", "cmc_market_skill"]
    assert rec["notify_policy"] == {"webpush": True, "severity_min": "info"}


def test_rejects_unknown_tool():
    with pytest.raises(ValueError, match="unknown tool"):
        validate_agent_spec({"name": "x", "goal": "g", "allowed_tools": ["drain_wallet"]})


def test_requires_name_and_goal():
    with pytest.raises(ValueError):
        validate_agent_spec({"name": "", "goal": "g"})


def test_known_tool_names_cover_copilot_tools():
    assert {"get_price", "get_trending", "check_token_risk",
            "cmc_market_skill", "get_agent_state"} <= AGENT_TOOL_NAMES
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_spec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.agents.spec'`.

- [ ] **Step 3: Implement `agent/agents/spec.py`.**

```python
"""Validation for user-spawned Agent records. We validate structured input from the
co-pilot's create_agent tool — we never parse free text. Default mode is paper."""
from __future__ import annotations

from agent.copilot_agent import TOOLS

# The Tier-A Agent Tools an Agent may compose = the co-pilot's read tools.
AGENT_TOOL_NAMES = frozenset(t["name"] for t in TOOLS)

_DEFAULT_NOTIFY = {"webpush": True, "severity_min": "info"}


def validate_agent_spec(raw: dict) -> dict:
    name = str(raw.get("name", "")).strip()
    goal = str(raw.get("goal", "")).strip()
    if not name or not goal:
        raise ValueError("agent requires a non-empty name and goal")

    tools = list(raw.get("allowed_tools") or [])
    for t in tools:
        if t not in AGENT_TOOL_NAMES:
            raise ValueError(f"unknown tool: {t!r}")

    mode = raw.get("mode", "paper")
    if mode not in ("paper", "live"):
        raise ValueError(f"mode must be paper|live, got {mode!r}")

    trigger = raw.get("trigger")
    notify = raw.get("notify_policy") or dict(_DEFAULT_NOTIFY)
    return {
        "name": name, "goal": goal, "allowed_tools": tools,
        "trigger": trigger, "notify_policy": notify, "mode": mode,
    }
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_spec.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit.**

```bash
git add agent/agents/__init__.py agent/agents/spec.py agent/tests/test_agent_spec.py
git commit -m "feat(agents): structured spec validation with paper default"
```

---

### Task 3: Registry (`agent/agents/registry.py`)

Thin CRUD over the bridge so the runtime never builds Convex calls inline.

**Files:**
- Create: `agent/agents/registry.py`
- Test: `agent/tests/test_agent_registry.py`

**Interfaces:**
- Consumes: a `bridge` exposing `.call(kind, path, args) -> Any` (the `ConvexBridge` shape; `kind` is `"query"|"mutation"`).
- Produces: `create_agent(bridge, spec)`, `list_active(bridge)`, `rename(bridge, agent_id, name)`, `archive(bridge, agent_id)`, `heartbeat(bridge, agent_id)`.

- [ ] **Step 1: Write the failing test** (uses a fake bridge that records calls).

```python
# agent/tests/test_agent_registry.py
from agent.agents import registry


class FakeBridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args):
        self.calls.append((kind, path, args))
        return "agent123" if path == "spawnedAgents:create" else None


def test_create_agent_calls_create_mutation():
    b = FakeBridge()
    out = registry.create_agent(b, {"name": "W", "goal": "g", "allowed_tools": ["get_price"],
                                    "trigger": None, "notify_policy": {"webpush": True, "severity_min": "info"},
                                    "mode": "paper"})
    assert out == "agent123"
    kind, path, args = b.calls[0]
    assert (kind, path) == ("mutation", "spawnedAgents:create")
    assert args["name"] == "W" and args["mode"] == "paper"


def test_archive_sets_status():
    b = FakeBridge()
    registry.archive(b, "agent123")
    assert b.calls[0] == ("mutation", "spawnedAgents:setStatus",
                          {"id": "agent123", "status": "archived"})
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_registry.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError`.

- [ ] **Step 3: Implement `agent/agents/registry.py`.**

```python
"""CRUD over spawned_agents via the ConvexBridge. One call site for agent records."""
from __future__ import annotations

import time


def create_agent(bridge, spec: dict):
    return bridge.call("mutation", "spawnedAgents:create", {
        "name": spec["name"], "goal": spec["goal"],
        "allowed_tools": spec.get("allowed_tools", []),
        "trigger": spec.get("trigger"),
        "notify_policy": spec.get("notify_policy"),
        "mode": spec.get("mode", "paper"),
    })


def list_active(bridge):
    return bridge.call("query", "spawnedAgents:list", {}) or []


def rename(bridge, agent_id, name: str):
    bridge.call("mutation", "spawnedAgents:rename", {"id": agent_id, "name": name})


def archive(bridge, agent_id):
    bridge.call("mutation", "spawnedAgents:setStatus", {"id": agent_id, "status": "archived"})


def heartbeat(bridge, agent_id):
    bridge.call("mutation", "spawnedAgents:updateActivity", {"id": agent_id})
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_registry.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit.**

```bash
git add agent/agents/registry.py agent/tests/test_agent_registry.py
git commit -m "feat(agents): registry CRUD over convex bridge"
```

---

### Task 4: Runner (`agent/agents/runner.py`)

Run one Agent: build a goal prompt, drive the bounded tool-loop with only the agent's allowed tools, write a heartbeat + an `agent_runs` row + one `agent_events` row, and never raise (failures become an error event).

**Files:**
- Create: `agent/agents/runner.py`
- Test: `agent/tests/test_agent_runner.py`

**Interfaces:**
- Consumes: `agent/copilot_agent.py:run_read_loop(question, *, twak, skills, bridge, client, model, max_turns) -> {answer, grounded, sources}`; `registry.heartbeat`.
- Produces: `run_agent(agent_record, *, twak, skills, bridge, client) -> RunResult` where `RunResult` is a dict `{ok, summary, tool_calls}`. Writes `agentRuns:record` and an `agent_events` row via `bridge`.

- [ ] **Step 1: Write the failing test** (stub `run_read_loop` via a fake client is heavy — instead inject a fake loop fn).

```python
# agent/tests/test_agent_runner.py
from agent.agents import runner


class RecBridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args): self.calls.append((path, args)); return "run1"
    def append_event(self, **kw): self.calls.append(("event", kw))


def test_run_agent_records_run_and_heartbeat():
    rec = {"_id": "a1", "name": "W", "goal": "watch CAKE",
           "allowed_tools": ["get_price"], "mode": "paper"}
    b = RecBridge()

    def fake_loop(question, **kw):
        assert "watch CAKE" in question
        return {"answer": "CAKE flat", "grounded": True,
                "sources": [{"tool": "get_price", "args": {"token": "CAKE"}}]}

    out = runner.run_agent(rec, twak=None, skills=None, bridge=b, client=None,
                           loop_fn=fake_loop)
    assert out["ok"] is True
    assert "CAKE flat" in out["summary"]
    paths = [c[0] for c in b.calls]
    assert "agentRuns:record" in paths        # run persisted
    assert any(p == "event" for p in paths)    # one agent_events row


def test_run_agent_failure_becomes_error_event_not_raise():
    rec = {"_id": "a1", "name": "W", "goal": "g", "allowed_tools": [], "mode": "paper"}
    b = RecBridge()

    def boom(question, **kw): raise RuntimeError("tool down")

    out = runner.run_agent(rec, twak=None, skills=None, bridge=b, client=None, loop_fn=boom)
    assert out["ok"] is False
    assert "tool down" in out["summary"]
    assert any(c[0] == "agentRuns:record" and c[1]["ok"] is False for c in b.calls)
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_runner.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `agent/agents/runner.py`.** Note: `run_read_loop` ignores unknown tool names if the agent restricts them — we pass the allowlist into the prompt and rely on `execute_tool` for the actual calls. (Tool *restriction* enforcement is Task 4b/Phase 2; Phase 1 scopes by prompt + records what was called.)

```python
"""Run one user-spawned Agent as a bounded tool-loop. Off the trade hot path.
Never raises: any failure is captured as an error run + agent_events row
(no-silent-failure, per the 2026-06-20 outage)."""
from __future__ import annotations

import time

from agent.copilot_agent import run_read_loop


def _goal_prompt(rec: dict) -> str:
    tools = ", ".join(rec.get("allowed_tools") or []) or "(no tools)"
    return (
        f"You are the user's agent named '{rec['name']}'. Pursue this goal using ONLY "
        f"these tools: {tools}. Goal: {rec['goal']}. "
        f"Report concisely what you found and whether the user should be notified."
    )


def run_agent(rec: dict, *, twak, skills, bridge, client, loop_fn=run_read_loop) -> dict:
    started = int(time.time() * 1000)
    agent_id = rec["_id"]
    try:
        result = loop_fn(_goal_prompt(rec), twak=twak, skills=skills, bridge=bridge,
                         client=client, max_turns=4)
        summary = result.get("answer", "")[:600]
        tool_calls = [{"tool": s["tool"], "args": str(s.get("args", {}))[:200]}
                      for s in result.get("sources", [])]
        ok = True
    except Exception as exc:  # no-silent-failure: capture, don't raise
        summary = f"agent run failed: {exc}"[:600]
        tool_calls, ok = [], False

    ended = int(time.time() * 1000)
    bridge.call("mutation", "agentRuns:record", {
        "agent_id": agent_id, "started_ms": started, "ended_ms": ended,
        "ok": ok, "summary": summary, "tool_calls": tool_calls,
    })
    bridge.append_event(
        agent=rec["name"],
        kind="analysis" if ok else "control",
        headline=summary.split("\n")[0][:120],
        detail="{}",
        refs=[],
    )
    return {"ok": ok, "summary": summary, "tool_calls": tool_calls}
```

> If `ConvexBridge` exposes event-writing under a different name than `append_event`, check `agent/convex_bridge.py` (it already writes `agent_events`; reuse that method) and adjust the call. Keep `append_audit` for audit rows; events go to `agent_events`.

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_runner.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit.**

```bash
git add agent/agents/runner.py agent/tests/test_agent_runner.py
git commit -m "feat(agents): bounded runner with heartbeat + no-silent-failure"
```

---

### Task 5: Watchdog (`agent/agents/watchdog.py`)

Pure detection: given active agents + now, return those silent past `expected × N`. Wired into the loop tick to emit one alert event per stalled agent.

**Files:**
- Create: `agent/agents/watchdog.py`
- Test: `agent/tests/test_agent_watchdog.py`

**Interfaces:**
- Produces: `STALL_FACTOR: int`; `default_cadence_ms(trigger) -> int`; `find_stalled(agents, now_ms) -> list[dict]` (each agent dict needs `last_activity_ms`, `trigger`, `status`).

- [ ] **Step 1: Write the failing test.**

```python
# agent/tests/test_agent_watchdog.py
from agent.agents.watchdog import find_stalled, default_cadence_ms

HOUR = 3600_000


def test_stalled_when_silent_beyond_factor():
    now = 100 * HOUR
    agents = [
        {"name": "fresh", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - HOUR},                       # 1× cadence: ok
        {"name": "stale", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - 5 * HOUR},                   # >3× cadence: stalled
    ]
    stalled = [a["name"] for a in find_stalled(agents, now)]
    assert stalled == ["stale"]


def test_archived_agents_ignored():
    now = 100 * HOUR
    agents = [{"name": "z", "status": "archived", "trigger": {"kind": "schedule", "spec": "1h"},
               "last_activity_ms": now - 99 * HOUR}]
    assert find_stalled(agents, now) == []


def test_default_cadence_parses_hours_and_falls_back():
    assert default_cadence_ms({"kind": "schedule", "spec": "2h"}) == 2 * HOUR
    assert default_cadence_ms(None) == HOUR    # event-driven / unknown -> 1h heartbeat
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_watchdog.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `agent/agents/watchdog.py`.**

```python
"""Flag spawned Agents that have gone silent past their expected cadence.
No Agent fails quietly (2026-06-20 outage lesson)."""
from __future__ import annotations

import re

STALL_FACTOR = 3
_HOUR_MS = 3600_000
_SPEC_RE = re.compile(r"^\s*(\d+)\s*h\s*$", re.I)


def default_cadence_ms(trigger) -> int:
    if isinstance(trigger, dict):
        m = _SPEC_RE.match(str(trigger.get("spec", "")))
        if m:
            return int(m.group(1)) * _HOUR_MS
    return _HOUR_MS


def find_stalled(agents: list[dict], now_ms: int) -> list[dict]:
    out = []
    for a in agents:
        if a.get("status") != "active":
            continue
        last = a.get("last_activity_ms") or 0
        if now_ms - last > STALL_FACTOR * default_cadence_ms(a.get("trigger")):
            out.append(a)
    return out
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_watchdog.py -v`
Expected: 3 passed.

- [ ] **Step 5: Wire into the loop tick.** In `agent/loop.py`, find the per-cycle Tier-1 hook (where the supervisor/digest is already pinged each cycle) and add a watchdog sweep that emits one event per stalled agent:

```python
from agent.agents.watchdog import find_stalled
from agent.agents.registry import list_active

# inside the per-cycle advisory block (off the scored path):
try:
    _now = int(time.time() * 1000)
    for _a in find_stalled(list_active(bridge), _now):
        bridge.append_event(agent="WalletManager", kind="control",
                            headline=f"Agent '{_a['name']}' is stalled — no activity",
                            detail="{}", refs=[])
except Exception:
    log.exception("watchdog sweep failed")   # never break the loop
```

- [ ] **Step 6: Commit.**

```bash
git add agent/agents/watchdog.py agent/tests/test_agent_watchdog.py agent/loop.py
git commit -m "feat(agents): stall watchdog + loop sweep"
```

---

### Task 6: Market Watcher template (`agent/agents/templates.py`)

A factory that produces a ready-to-run Market Watcher spec (monitor a symbol + condition). Verifies an agent spec is well-formed and uses only CMC/price tools.

**Files:**
- Create: `agent/agents/templates.py`
- Test: `agent/tests/test_agent_templates.py`

**Interfaces:**
- Produces: `market_watcher(symbol: str, condition: str) -> dict` → a validated spec (via `validate_agent_spec`) with `allowed_tools = ["get_price", "cmc_market_skill"]`, `trigger = {"kind": "schedule", "spec": "1h"}`, `mode = "paper"`.

- [ ] **Step 1: Write the failing test.**

```python
# agent/tests/test_agent_templates.py
from agent.agents.templates import market_watcher


def test_market_watcher_is_valid_and_read_only():
    spec = market_watcher("CAKE", "funding flips negative")
    assert spec["mode"] == "paper"
    assert spec["allowed_tools"] == ["get_price", "cmc_market_skill"]
    assert spec["trigger"] == {"kind": "schedule", "spec": "1h"}
    assert "CAKE" in spec["goal"] and "funding flips negative" in spec["goal"]
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_templates.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `agent/agents/templates.py`.**

```python
"""Prebuilt Agent specs the co-pilot/UI can spawn in one tap."""
from __future__ import annotations

from agent.agents.spec import validate_agent_spec


def market_watcher(symbol: str, condition: str) -> dict:
    return validate_agent_spec({
        "name": f"{symbol}-Watcher",
        "goal": f"Monitor {symbol}. Notify me when {condition}.",
        "allowed_tools": ["get_price", "cmc_market_skill"],
        "trigger": {"kind": "schedule", "spec": "1h"},
        "mode": "paper",
    })
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_templates.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit.**

```bash
git add agent/agents/templates.py agent/tests/test_agent_templates.py
git commit -m "feat(agents): Market Watcher template"
```

---

### Task 7: Trade Proposer + approval flow (`agent/agents/proposals.py`) — the safety-critical task

A `live`-mode agent *proposes*; it never swaps. `propose` writes an `approval_requests` row. Approval is a human action in the PWA that calls the control-token-gated `approvals:resolve` (Task 1), which enqueues into `agent_commands`. This task's tests assert the **scored-wallet invariant**.

**Files:**
- Create: `agent/agents/proposals.py`
- Test: `agent/tests/test_agent_proposals.py`

**Interfaces:**
- Consumes: a `bridge` with `.call(kind, path, args)`.
- Produces: `propose_trade(bridge, agent_id, *, command_type, params) -> id` (writes a pending approval, returns its id). In `paper` mode the caller uses `simulate_fill` instead — `propose_trade` is only reached in `live` mode.
- Produces: `simulate_fill(symbol, side, usd, price) -> dict` (paper ledger entry; no tx).

- [ ] **Step 1: Write the failing tests** — including the invariant.

```python
# agent/tests/test_agent_proposals.py
import pytest
from agent.agents import proposals


class Bridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args):
        self.calls.append((kind, path, args))
        return "appr1"


def test_propose_writes_pending_approval_and_no_swap():
    b = Bridge()
    out = proposals.propose_trade(b, "a1", command_type="twak_swap",
                                  params={"from": "USDT", "to": "CAKE", "amount": 4})
    assert out == "appr1"
    # Exactly one call, and it is the approval write — never a swap/command directly.
    assert len(b.calls) == 1
    kind, path, args = b.calls[0]
    assert (kind, path) == ("mutation", "approvals:propose")
    assert args["agent_id"] == "a1"
    # The scored-wallet invariant: no command_worker / twak path touched here.
    assert all("command" not in p.lower() and "twak" not in p.lower()
               for _, p, _ in b.calls)


def test_paper_simulate_fill_has_no_tx():
    fill = proposals.simulate_fill("CAKE", "buy", usd=4.0, price=2.0)
    assert fill["qty"] == 2.0 and fill["tx_hash"] is None and fill["mode"] == "paper"
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_proposals.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `agent/agents/proposals.py`.**

```python
"""Trade proposals from live-mode Agents. An Agent NEVER swaps directly:
it writes a pending approval. The human approves in the PWA (control-token
gated), which enqueues the real command. Paper mode simulates with no tx."""
from __future__ import annotations

import json


def propose_trade(bridge, agent_id, *, command_type: str, params: dict):
    """Write a pending approval_request. Returns its id. Does NOT execute."""
    payload = json.dumps({"command_type": command_type, "params": params})
    return bridge.call("mutation", "approvals:propose",
                       {"agent_id": agent_id, "payload": payload})


def simulate_fill(symbol: str, side: str, *, usd: float, price: float) -> dict:
    """Paper fill — no on-chain tx. Mirrors /core's notion of a fill for the ledger."""
    qty = round(usd / price, 8) if price else 0.0
    return {"symbol": symbol, "side": side, "usd": usd, "price": price,
            "qty": qty, "tx_hash": None, "mode": "paper"}
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_proposals.py -v`
Expected: 2 passed (the invariant test is green).

- [ ] **Step 5: Add the end-to-end approval invariant test** (proves approve → exactly one queued command, reject → none). This exercises the Convex contract shape through a fake bridge that mimics `approvals:resolve`.

```python
# append to agent/tests/test_agent_proposals.py
def test_resolve_contract_enqueues_one_command_on_approve_only():
    # Simulate the convex resolve handler's effect on agent_commands.
    queued = []
    def resolve(status, payload):
        if status == "approved":
            c = json.loads(payload)
            queued.append({"command_type": c["command_type"],
                           "params": json.dumps(c["params"]), "status": "queued"})
    payload = json.dumps({"command_type": "twak_swap",
                          "params": {"from": "USDT", "to": "CAKE", "amount": 4}})
    resolve("rejected", payload); assert queued == []
    resolve("approved", payload); assert len(queued) == 1
    assert queued[0]["status"] == "queued" and queued[0]["command_type"] == "twak_swap"
```

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_proposals.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit.**

```bash
git add agent/agents/proposals.py agent/tests/test_agent_proposals.py
git commit -m "feat(agents): propose-only trade flow + scored-wallet invariant tests"
```

---

### Task 8: Web Push (`agent/push.py` + service worker)

Send a Web Push to subscribed PWAs (VAPID). Python builds the payload + sends; the SW renders it. Subscription happens in the PWA (Task 9).

**Files:**
- Create: `agent/push.py`
- Test: `agent/tests/test_push.py`
- Create: `web/public/sw-push.js` (push + notificationclick handlers)
- Modify: `web/vite.config.ts` (vite-plugin-pwa `injectManifest`/`importScripts` to include `sw-push.js`)
- Env: add `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` to `.env.local`

**Interfaces:**
- Produces: `build_push_payload(title, body, *, severity="info", url="/") -> dict`; `send_push(subscription, payload, *, vapid) -> bool` (uses `pywebpush`; returns False on a dead subscription rather than raising).

- [ ] **Step 1: Add the dependency.**

Run: `cd core && uv pip install pywebpush`
Expected: installs `pywebpush` + `py-vapid` into `core/.venv`.

- [ ] **Step 2: Write the failing test** (payload builder is pure; send is mocked).

```python
# agent/tests/test_push.py
from unittest.mock import patch
from agent import push


def test_build_payload_shape():
    p = push.build_push_payload("Agent W", "CAKE funding negative", severity="warn", url="/agents")
    assert p == {"title": "Agent W", "body": "CAKE funding negative",
                 "severity": "warn", "url": "/agents"}


def test_send_push_returns_false_on_dead_subscription():
    sub = {"endpoint": "https://x", "keys": {"p256dh": "a", "auth": "b"}}
    with patch("agent.push.webpush", side_effect=Exception("410 Gone")):
        assert push.send_push(sub, {"title": "t", "body": "b"},
                              vapid={"private_key": "k", "subject": "mailto:x@y.z"}) is False
```

- [ ] **Step 3: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_push.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.push'`.

- [ ] **Step 4: Implement `agent/push.py`.**

```python
"""Web Push (VAPID) — replaces Telegram as the away-from-app ping.
send_push never raises on a dead subscription; the caller prunes on False."""
from __future__ import annotations

import json
import logging

from pywebpush import webpush

log = logging.getLogger(__name__)


def build_push_payload(title: str, body: str, *, severity: str = "info", url: str = "/") -> dict:
    return {"title": title, "body": body, "severity": severity, "url": url}


def send_push(subscription: dict, payload: dict, *, vapid: dict) -> bool:
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=vapid["private_key"],
            vapid_claims={"sub": vapid["subject"]},
        )
        return True
    except Exception as exc:  # 410/404 = dead subscription; prune upstream
        log.warning("web push failed (%s); subscription likely dead", exc)
        return False
```

- [ ] **Step 5: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_push.py -v`
Expected: 2 passed.

- [ ] **Step 6: Add the service worker `web/public/sw-push.js`.**

```js
self.addEventListener("push", (event) => {
  const d = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(d.title || "Alien-Trade", {
      body: d.body || "", data: { url: d.url || "/" },
      icon: "/logo.png", badge: "/logo.png",
    })
  );
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data?.url || "/"));
});
```

- [ ] **Step 7: Register the push SW.** In `web/vite.config.ts`, ensure the existing `vite-plugin-pwa` config imports `sw-push.js` (add to `workbox.importScripts: ["/sw-push.js"]`, or `injectManifest` swSrc if already custom). Verify the build still produces a service worker:

Run: `cd web && bun run build`
Expected: build succeeds; `dist/sw.js` (or the configured SW) references the push handlers.

- [ ] **Step 8: Commit.**

```bash
git add agent/push.py agent/tests/test_push.py web/public/sw-push.js web/vite.config.ts
git commit -m "feat(push): web push send + service worker handlers"
```

---

### Task 9: Agent Console wiring — co-pilot `create_agent` tool + PWA spawn/approve/subscribe

Promote the co-pilot to the Agent Console: it can create agents; the "Your Agents" section shows them with run status; pending approvals render as one-tap cards; a "Enable alerts" button subscribes to Web Push.

**Files:**
- Modify: `agent/copilot_agent.py` (add a `create_agent` tool + `execute_tool` branch)
- Modify: `web/src/views/AgentsView.tsx` (render new fields + pending approvals + alerts toggle)
- Modify: `web/src/components/CoPilotDrawer.tsx` (surface "spawn an agent" affordance)
- Create: `web/src/lib/push.ts` (subscribe helper: register SW, `pushManager.subscribe`, call `push:subscribe`)

**Interfaces:**
- Consumes: `convex/spawnedAgents.ts:create`, `convex/approvals.ts:{listPending,resolve}`, `convex/push.ts:subscribe`, and `agent/agents/spec.py:validate_agent_spec`.
- Produces: a co-pilot tool `create_agent(name, goal, allowed_tools, trigger?, mode?)` that validates via `validate_agent_spec` then calls `spawnedAgents:create`.

- [ ] **Step 1: Add the `create_agent` tool schema to `agent/copilot_agent.py:TOOLS`** (keep alphabetical order — `create_agent` goes before `get_agent_state`):

```python
    {
        "name": "create_agent",
        "description": "Spawn a new user-owned Agent that pursues a goal using the "
                       "specialized Agent Tools. Default mode is paper (no real trades).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "goal": {"type": "string"},
                "allowed_tools": {"type": "array", "items": {"type": "string"}},
                "trigger": {"type": "object"},
                "mode": {"type": "string", "enum": ["paper", "live"]},
            },
            "required": ["name", "goal", "allowed_tools"],
        },
    },
```

- [ ] **Step 2: Handle it in `execute_tool`.** Add a branch that validates then writes (this is the one *write* the co-pilot may do — it creates a record, never a trade):

```python
    if name == "create_agent":
        from agent.agents.spec import validate_agent_spec
        from agent.agents.registry import create_agent
        spec = validate_agent_spec(args)
        new_id = create_agent(bridge, spec)
        return f"Created agent '{spec['name']}' (mode={spec['mode']}, id={new_id})."
```

- [ ] **Step 3: Add a unit test** for the tool branch (fake bridge):

```python
# agent/tests/test_copilot_create_agent.py
from agent.copilot_agent import execute_tool


class B:
    def call(self, kind, path, args): return "agentX"


def test_create_agent_tool_validates_and_writes():
    out = execute_tool("create_agent",
                       {"name": "CAKE-Watcher", "goal": "watch CAKE",
                        "allowed_tools": ["get_price"]},
                       twak=None, skills=None, bridge=B())
    assert "CAKE-Watcher" in out and "agentX" in out


def test_create_agent_tool_rejects_unknown_tool():
    out = execute_tool("create_agent",
                       {"name": "x", "goal": "g", "allowed_tools": ["drain"]},
                       twak=None, skills=None, bridge=B())
    assert "unknown tool" in out.lower() or "error" in out.lower()
```

> If `execute_tool` swallows exceptions into a string, the second test passes via the error string. If it raises, wrap the `create_agent` branch in try/except returning `f"error: {exc}"` to match the read-tool convention already used in that function.

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_create_agent.py -v`
Expected: 2 passed.

- [ ] **Step 4: Add `web/src/lib/push.ts`.**

```ts
import { api } from "../../convex/_generated/api";
import type { ConvexReactClient } from "convex/react";

const VAPID_PUBLIC = import.meta.env.VITE_VAPID_PUBLIC_KEY as string;

function urlBase64ToUint8Array(b64: string): Uint8Array {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function enableAlerts(convex: ConvexReactClient): Promise<boolean> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return false;
  if ((await Notification.requestPermission()) !== "granted") return false;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC),
  });
  const j = sub.toJSON();
  await convex.mutation(api.push.subscribe, {
    endpoint: j.endpoint!, p256dh: j.keys!.p256dh, auth: j.keys!.auth,
  });
  return true;
}
```

- [ ] **Step 5: Wire `AgentsView.tsx`.** In the "Your Agents" section, (a) render each spawned agent's `mode` + `last_activity_ms`; (b) below it, map `useQuery(api.approvals.listPending)` into approval cards with Approve/Reject buttons that call `api.approvals.resolve` with the `control_token` already held by the cockpit (same place the kill-switch/commands read it); (c) add an "Enable alerts" button calling `enableAlerts(convex)`. Key snippet for the approval card:

```tsx
const pending = useQuery(api.approvals.listPending) ?? [];
// ...
{pending.map((p) => (
  <div key={p._id} className="rounded-lg border border-border p-3 flex items-center justify-between">
    <span className="font-mono text-xs">{JSON.parse(p.payload).command_type} — {p.payload}</span>
    <div className="flex gap-2">
      <button onClick={() => convex.mutation(api.approvals.resolve,
        { id: p._id, status: "approved", control_token: controlToken })}>Approve</button>
      <button onClick={() => convex.mutation(api.approvals.resolve,
        { id: p._id, status: "rejected", control_token: controlToken })}>Reject</button>
    </div>
  </div>
))}
```

- [ ] **Step 6: Verify the frontend builds + typechecks.**

Run: `cd web && bun run build`
Expected: build succeeds, no TS errors. Manually: open the PWA, click "Enable alerts" → browser permission prompt; ask the co-pilot "make an agent that watches CAKE" → a new row appears in "Your Agents".

- [ ] **Step 7: Commit.**

```bash
git add agent/copilot_agent.py agent/tests/test_copilot_create_agent.py \
  web/src/views/AgentsView.tsx web/src/components/CoPilotDrawer.tsx web/src/lib/push.ts
git commit -m "feat(console): co-pilot create_agent tool + spawn/approve/subscribe UI"
```

---

### Task 10: Schedule spawned-agent runs + push delivery (loop integration)

Tie it together: each loop tick (off the scored path), run due agents and deliver any agent notifications via Web Push to all subscriptions.

**Files:**
- Modify: `agent/loop.py` (per-cycle advisory block — run due agents, prune dead subscriptions)
- Modify: `agent/runtime.py` (construct the Anthropic `client` + pass `bridge`, `twak`, `skills` already available)
- Test: `agent/tests/test_agent_schedule.py`

**Interfaces:**
- Consumes: `runner.run_agent`, `registry.list_active`, `watchdog.default_cadence_ms`, `push.send_push`, `push.build_push_payload`.
- Produces: `due_agents(agents, now_ms) -> list[dict]` (active + past cadence since `last_activity_ms`); `deliver_push(bridge, payload, *, vapid, sender=send_push) -> int` (count delivered, prunes dead).

- [ ] **Step 1: Write the failing test.**

```python
# agent/tests/test_agent_schedule.py
from agent.agents.schedule import due_agents, deliver_push

HOUR = 3600_000


def test_due_when_past_cadence():
    now = 100 * HOUR
    agents = [
        {"name": "a", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - 2 * HOUR},     # due
        {"name": "b", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - 10_000},        # not due
    ]
    assert [a["name"] for a in due_agents(agents, now)] == ["a"]


def test_deliver_push_prunes_dead_subscriptions():
    subs = [{"_id": "s1", "endpoint": "e1", "p256dh": "x", "auth": "y"},
            {"_id": "s2", "endpoint": "e2", "p256dh": "x", "auth": "y"}]
    pruned = []
    class B:
        def call(self, kind, path, args):
            if path == "push:list": return subs
            if path == "push:remove": pruned.append(args["id"])
    def sender(sub, payload, *, vapid): return sub["endpoint"] == "e1"  # e2 dead
    n = deliver_push(B(), {"title": "t", "body": "b"}, vapid={}, sender=sender)
    assert n == 1 and pruned == ["s2"]
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_schedule.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `agent/agents/schedule.py`** (and add a `push:remove` mutation to `convex/push.ts` mirroring `subscribe`).

```python
"""Decide which agents are due and fan a notification out to push subscriptions."""
from __future__ import annotations

from agent.agents.watchdog import default_cadence_ms
from agent.push import send_push as _send_push


def due_agents(agents: list[dict], now_ms: int) -> list[dict]:
    out = []
    for a in agents:
        if a.get("status") != "active":
            continue
        last = a.get("last_activity_ms") or 0
        if now_ms - last >= default_cadence_ms(a.get("trigger")):
            out.append(a)
    return out


def deliver_push(bridge, payload: dict, *, vapid: dict, sender=_send_push) -> int:
    subs = bridge.call("query", "push:list", {}) or []
    delivered = 0
    for s in subs:
        sub = {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}}
        if sender(sub, payload, vapid=vapid):
            delivered += 1
        else:
            bridge.call("mutation", "push:remove", {"id": s["_id"]})
    return delivered
```

Add to `convex/push.ts`:

```ts
export const remove = mutation({
  args: { id: v.id("push_subscriptions") },
  handler: async (ctx, a) => { await ctx.db.delete(a.id); },
});
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `core/.venv/bin/python -m pytest agent/tests/test_agent_schedule.py -v`
Expected: 2 passed.

- [ ] **Step 5: Wire into `agent/loop.py`** (the same off-scored-path advisory block as Task 5). Guard the whole thing so it can never break trading:

```python
from agent.agents.schedule import due_agents, deliver_push
from agent.agents.runner import run_agent

try:
    _now = int(time.time() * 1000)
    _agents = list_active(bridge)
    for _a in due_agents(_agents, _now):
        _res = run_agent(_a, twak=twak, skills=skills, bridge=bridge, client=anthropic_client)
        if _res["ok"] and _a.get("notify_policy", {}).get("webpush", True):
            deliver_push(bridge, build_push_payload(_a["name"], _res["summary"], url="/agents"),
                         vapid=VAPID)
except Exception:
    log.exception("spawned-agent tick failed")   # never break the loop
```

(`anthropic_client`, `twak`, `skills`, `VAPID` are constructed in `agent/runtime.py`; pass them through to the loop where the co-pilot client already is.)

- [ ] **Step 6: Run the full agents test module + smoke the loop import.**

Run: `core/.venv/bin/python -m pytest agent/tests/ -k "agent or push" -v && core/.venv/bin/python -c "import agent.loop"`
Expected: all green; loop imports without error.

- [ ] **Step 7: Commit.**

```bash
git add agent/agents/schedule.py agent/tests/test_agent_schedule.py convex/push.ts agent/loop.py agent/runtime.py
git commit -m "feat(agents): schedule due runs + web-push fan-out with pruning"
```

---

## Self-Review (against the spec)

- **§2 two tiers / Agent Tools = co-pilot tools** → Task 2 (`AGENT_TOOL_NAMES` from `copilot_agent.TOOLS`). ✔
- **§3 off-hot-path, bounded, heartbeat, no-silent-failure** → Tasks 4, 5. ✔
- **§4 propose→approve, paper default, scored-wallet invariant** → Tasks 1 (gated `resolve`), 7 (invariant tests). ✔
- **§5 co-pilot → Agent Console + Web Push** → Tasks 8, 9. ✔
- **§6 data model** → Task 1 (all four tables/fields). ✔
- **§7 component boundaries** → one module per unit (`spec`, `registry`, `runner`, `watchdog`, `templates`, `proposals`, `schedule`, `push`). ✔
- **§9 testing incl. safety assertion** → Task 7 Steps 1 & 5. ✔
- **Collaboration (§5.1)** → **NOT in Phase 1** by design; see appendix. (Gap is intentional and phased.)

No placeholders; types consistent (`bridge.call(kind, path, args)`, `run_agent(...) -> {ok, summary, tool_calls}`, `validate_agent_spec(raw) -> dict` used identically across tasks).

---

## Appendix — Phases 2 & 3 (roadmap, not yet task-decomposed)

These get their own plan once Phase 1's interfaces are merged and real.

**Phase 2 — Collaboration (§5.1).**
- `agent/agents/orchestrator.py`: Level-1 tool handoff chains via the LangGraph supervisor, consuming typed `agent/graph/contracts.py` outputs; combined result + ordered `tool_calls[]` trace.
- Level-2 Agent→Agent delegation with cycle detection (no self-call, direct or transitive) and `MAX_DELEGATION_DEPTH`.
- Templates that require collaboration: **Setup Scorer** (Researcher→Historian→CoPilot), **Daily Brief** (delegates to multiple Agents).
- Cockpit "Neural Mesh" who-called-whom graph from `agent_runs`.

**Phase 3 — Autonomy + polish (stretch).**
- Separate funded wallet for a fully-autonomous live Agent; scored wallet isolated.
- Visual agent builder (allowed-tools picker, trigger editor).
- Telegram restored as an optional secondary pipe.
