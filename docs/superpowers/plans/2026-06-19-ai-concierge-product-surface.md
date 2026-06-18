# AI Concierge Product Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the autonomous product surface around the existing trading agent — entry point CTA, action-taking chat concierge with HITL, trackers view, deposit/withdraw panels, post-trade tour, and logo fix.

**Architecture:** All agent actions go through Convex token-gated mutations (never directly from the LLM). The concierge maps language → `ProposedAction` types via a deterministic grammar in `concierge.ts`; the agent's `/copilot` endpoint optionally returns a structured action too. HITL confirmation cards render in the message stream; confirming calls the matching mutation. The `core` loop reads config changes each cycle — that's the "acts next time without asking" memory.

**Tech Stack:** React + TypeScript + Convex + `driver.js` v1 + `zod` (already in web deps) + `qrcode` (already imported in App.tsx) + `twak transfer` CLI (for withdraw backend)

## Global Constraints

- **LLM stays OFF the buy/sell hot path.** The concierge NEVER decides a trade. It only mutates config / commands / feedback.
- **All writes are token-gated.** `withToken(...)` on client, `assertControlToken` on server.
- **HITL required** for every action except read-only answers and deposit_info.
- **Double confirm** for `withdraw` — shows destination address verbatim before executing.
- Package manager: `bun` — never `npm` or `npx`.
- Build check: `cd /root/claude/projects/alien-trade/web && bun run build` — must pass zero TS errors.
- Python tests: `cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest` from repo root.
- Working directory for all commands: `/root/claude/projects/alien-trade`.
- Do NOT rebuild existing Convex APIs: `config.setAutopilot`, `config.setStrategy`, `config.updateLimits`, `config.setHalted`, `agentControl.set`, `agentCommands.enqueue`, `feedback.record`.
- Every new file under 400 lines; extract helpers if a view grows.

---

### Task 1: Logo Fix (Unit 8)

**Files:**
- Modify: `web/src/components/LiveHeader.tsx:42` — logo img sizing

**Interfaces:**
- No new interfaces; pure CSS fix.

- [ ] **Step 1: Read the current logo block in LiveHeader.tsx**

Open `web/src/components/LiveHeader.tsx`. Find the brand mark `<div data-tour="brand">` block (around line 40). The current logo img is:
```tsx
<img src="/logo.png" alt="Alien-Trade" className="logo-blend w-7 h-7" />
```
The issue: `object-cover` + `border-radius: 50%` (from `.logo-blend`) clips the alien face. The logo is 2048×2048 so it fits a circle, but the `w-7 h-7` (28px) box is too small and the `object-cover` crops it.

- [ ] **Step 2: Fix the logo wrapper to use object-contain and a slightly larger box**

Replace:
```tsx
<div className="relative flex-shrink-0">
  <img
    src="/logo.png"
    alt="Alien-Trade"
    className="logo-blend w-7 h-7"
  />
  {/* Status pulse overlaid at bottom-right of logo */}
  <span className={cn(
    "absolute bottom-0 right-0 w-2 h-2 rounded-full border border-[#050508]",
    halted ? "bg-red" : "bg-green animate-pulse",
  )} />
</div>
```

With:
```tsx
<div className="relative flex-shrink-0">
  <img
    src="/logo.png"
    alt="Alien-Trade"
    className="w-8 h-8 rounded-full object-contain"
    style={{ mixBlendMode: "screen" }}
  />
  <span className={cn(
    "absolute bottom-0 right-0 w-2 h-2 rounded-full border-[1.5px] border-[#050508]",
    halted ? "bg-red" : "bg-green animate-pulse",
  )} />
</div>
```

- [ ] **Step 3: Also fix logo in App.tsx PairingScreen (welcome step)**

In `App.tsx`, the pairing wizard welcome step has:
```tsx
<img src="/logo.png" alt="Alien-Trade" className="logo-blend w-20 h-20" />
```
Replace with:
```tsx
<img
  src="/logo.png"
  alt="Alien-Trade"
  className="w-20 h-20 rounded-full object-contain"
  style={{ mixBlendMode: "screen" }}
/>
```

- [ ] **Step 4: Fix logo in LandingView.tsx**

In `web/src/views/LandingView.tsx`, find:
```tsx
<img src="/logo.png" alt="Alien-Trade" className="logo-blend w-28 h-28 mb-6" />
```
Replace with:
```tsx
<img
  src="/logo.png"
  alt="Alien-Trade"
  className="w-32 h-32 rounded-full object-contain mb-6"
  style={{ mixBlendMode: "screen" }}
/>
```

- [ ] **Step 5: Build and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```
Expected: clean build.

```bash
cd /root/claude/projects/alien-trade
git add web/src/components/LiveHeader.tsx web/src/App.tsx web/src/views/LandingView.tsx
git commit -m "fix(logo): object-contain + explicit mixBlendMode — full alien face visible in navbar"
```

---

### Task 2: Wallet address in Convex + StartTradingCTA (Unit 1 + §7)

**Files:**
- Modify: `convex/walletState.ts` — add `address` field to upsert + get
- Modify: `convex/schema.ts` — add `address` to `wallet_state` table
- Create: `web/src/components/StartTradingCTA.tsx`
- Modify: `web/src/views/OverviewView.tsx` — add CTA above stats grid

**Interfaces:**
- `api.walletState.get` now returns `address?: string` in addition to existing fields
- `StartTradingCTA` props: `{ onStart: () => void }` — calls copilot open

- [ ] **Step 1: Add `address` to wallet_state schema**

Open `convex/schema.ts`. Find the `wallet_state` table definition and add `address`:
```typescript
wallet_state: defineTable({
  address:   v.optional(v.string()),   // add this line
  usdt:      v.number(),
  eth:       v.number(),
  bnb:       v.number(),
  bnb_usd:   v.number(),
  total_usd: v.number(),
  updated_ms: v.number(),
}),
```

- [ ] **Step 2: Add `address` to walletState upsert mutation**

Open `convex/walletState.ts`. In the `upsert` mutation, add `address: v.optional(v.string())` to args, and include it in both `patch` and `insert` calls:

```typescript
export const upsert = mutation({
  args: {
    address:   v.optional(v.string()),
    usdt:      v.number(),
    eth:       v.number(),
    bnb:       v.number(),
    bnb_usd:   v.number(),
    total_usd: v.number(),
    updated_ms: v.number(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const existing = await ctx.db.query("wallet_state").first();
    if (existing) {
      await ctx.db.patch(existing._id, args);
    } else {
      await ctx.db.insert("wallet_state", args);
    }
    return null;
  },
});
```

Also update the `get` query return type to include `address`:
```typescript
export const get = query({
  args: {},
  returns: v.union(v.null(), v.object({
    _id: v.id("wallet_state"),
    _creationTime: v.number(),
    address:   v.optional(v.string()),
    usdt:      v.number(),
    eth:       v.number(),
    bnb:       v.number(),
    bnb_usd:   v.number(),
    total_usd: v.number(),
    updated_ms: v.number(),
  })),
  handler: async (ctx) => {
    return await ctx.db.query("wallet_state").first();
  },
});
```

- [ ] **Step 3: Update agent to write address on each cycle**

Open `agent/convex_bridge.py`. Find the `upsert_wallet_state` method (or the equivalent call that writes wallet_state). Add `address` to the args:

```python
def upsert_wallet_state(self, usdt: float, eth: float, bnb: float,
                         bnb_usd: float, total_usd: float, address: str = "") -> None:
    import os
    addr = address or os.environ.get("WALLET_ADDRESS", "")
    self._call("mutation", "walletState:upsert", {
        "address": addr,
        "usdt": usdt,
        "eth": eth,
        "bnb": bnb,
        "bnb_usd": bnb_usd,
        "total_usd": total_usd,
        "updated_ms": int(time.time() * 1000),
    })
```

Search `convex_bridge.py` for the existing wallet state upsert call signature and update it to match.

- [ ] **Step 4: Create StartTradingCTA component**

Create `web/src/components/StartTradingCTA.tsx`:

```tsx
import { motion } from "framer-motion";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = { onStart: () => void };

export function StartTradingCTA({ onStart }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="panel rounded-2xl border border-border p-6 flex flex-col items-center gap-4 text-center"
      style={{ background: "radial-gradient(ellipse at 50% 0%, rgba(52,255,174,0.06) 0%, transparent 70%)" }}
    >
      <div className="w-12 h-12 rounded-2xl bg-green/10 border border-green/20 flex items-center justify-center"
        style={{ boxShadow: "0 0 24px rgba(52,255,174,0.15)" }}>
        <Bot className="w-6 h-6 text-green" />
      </div>
      <div>
        <h2 className="font-display text-[18px] font-bold text-text mb-1">
          Autonomous AI Trading Agent
        </h2>
        <p className="font-mono text-[12px] text-muted-fg max-w-xs leading-relaxed">
          Your agent is live and watching the market. Configure strategy, set risk limits, and track trades — all through the Co-Pilot.
        </p>
      </div>
      <Button
        onClick={onStart}
        className="bg-green text-[#04140c] font-bold px-6 py-2.5 h-auto hover:bg-green/80 cursor-pointer flex items-center gap-2"
      >
        <Bot className="w-4 h-4" />
        Start Trading with AI
      </Button>
    </motion.div>
  );
}
```

- [ ] **Step 5: Wire StartTradingCTA into OverviewView**

Open `web/src/views/OverviewView.tsx`. Add the import:
```typescript
import { StartTradingCTA } from "../components/StartTradingCTA";
```

Update the `Props` type:
```typescript
type Props = { onAgentClick: (name: string) => void; onCopilot: () => void };
```

Add the CTA at the top of the returned JSX, after alert banners and before the stats grid:
```tsx
{/* Start Trading CTA — always visible as the primary entry point */}
<StartTradingCTA onStart={onCopilot} />
```

- [ ] **Step 6: Pass onCopilot from App.tsx**

In `web/src/App.tsx`, the `OverviewView` render in `renderView()` is:
```typescript
case "overview": return <OverviewView onAgentClick={onAgentClick} />;
```
Change to:
```typescript
case "overview": return <OverviewView onAgentClick={onAgentClick} onCopilot={() => setCopilotOpen(true)} />;
```

- [ ] **Step 7: Build and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```

```bash
cd /root/claude/projects/alien-trade
git add convex/schema.ts convex/walletState.ts agent/convex_bridge.py \
  web/src/components/StartTradingCTA.tsx web/src/views/OverviewView.tsx web/src/App.tsx
git commit -m "feat(cta): StartTradingCTA on Overview + wallet address in Convex walletState"
```

---

### Task 3: concierge.ts — pure intent grammar + ProposedAction types (Unit 2 core)

**Files:**
- Create: `web/src/lib/concierge.ts`
- Create: `web/src/lib/concierge.test.ts`

**Interfaces:**
- Produces:
  ```typescript
  type ProposedAction = SetStrategyAction | UpdateLimitsAction | SetAutopilotAction |
    HaltAction | ResumeAction | MarkSetupAction | WithdrawAction | DepositInfoAction;
  function parseIntent(text: string): ProposedAction | null;
  function dispatchAction(action: ProposedAction, mutations: ConciergeDispatchers): Promise<void>;
  ```

- [ ] **Step 1: Create concierge.ts**

Create `web/src/lib/concierge.ts`:

```typescript
import { withToken } from "./control";

// ── Types ─────────────────────────────────────────────────────────────────────

export type ProposedAction =
  | { type: "set_strategy";   params: { strategy_name: string };                                         summary: string }
  | { type: "update_limits";  params: { max_position_usd?: number; daily_loss_limit_usd?: number; max_drawdown_pct?: number; equity_floor?: number }; summary: string }
  | { type: "set_autopilot";  params: { enabled: boolean; profit_target_pct?: number; protect_principal?: boolean; trailing_giveback_pct?: number }; summary: string }
  | { type: "halt";           params: Record<string, never>;                                             summary: string }
  | { type: "resume";         params: Record<string, never>;                                             summary: string }
  | { type: "mark_setup";     params: { setup_key: string; cycle_id: string; symbol: string; label: "good" | "bad"; note?: string }; summary: string }
  | { type: "withdraw";       params: { to_address: string; amount: number; token: string };              summary: string }
  | { type: "deposit_info";   params: Record<string, never>;                                             summary: string };

export type ConciergeDispatchers = {
  setStrategy:   (args: { strategy_name: string; control_token?: string }) => Promise<void>;
  updateLimits:  (args: { max_position_usd?: number; daily_loss_limit_usd?: number; max_drawdown_pct?: number; equity_floor?: number; control_token?: string }) => Promise<void>;
  setAutopilot:  (args: { autopilot: { enabled: boolean; profit_target_pct?: number; protect_principal?: boolean; trailing_giveback_pct?: number }; control_token?: string }) => Promise<void>;
  setHalted:     (args: { halted: boolean; control_token?: string }) => Promise<void>;
  setControl:    (args: { trading_halted: boolean; updated_by: string; control_token?: string }) => Promise<void>;
  recordFeedback:(args: { setup_key: string; cycle_id: string; symbol: string; label: "good" | "bad"; note?: string; control_token?: string }) => Promise<void>;
  enqueueCommand:(args: { command_type: string; params: string; queued_by?: string; control_token: string }) => Promise<unknown>;
  onDepositInfo: () => void;
};

// ── Suggestion card builders (deterministic — no LLM needed) ─────────────────

export function suggestionConservative(): ProposedAction {
  return {
    type: "set_strategy",
    params: { strategy_name: "defensive" },
    summary: "Switch strategy to defensive (low risk, small positions, strict stop-loss).",
  };
}

export function suggestionAdjustRisk(max_position_usd: number, equity_floor: number): ProposedAction {
  return {
    type: "update_limits",
    params: { max_position_usd, equity_floor },
    summary: `Set max position to $${max_position_usd} and equity floor to $${equity_floor}.`,
  };
}

export function suggestionTakeProfit(profit_target_pct: number): ProposedAction {
  return {
    type: "set_autopilot",
    params: { enabled: true, profit_target_pct, protect_principal: true },
    summary: `Enable autopilot: take profit at ${(profit_target_pct * 100).toFixed(0)}%, protect principal.`,
  };
}

// ── Deterministic intent grammar ─────────────────────────────────────────────

export function parseIntent(text: string): ProposedAction | null {
  const t = text.toLowerCase().trim();

  // halt / resume
  if (/\b(halt|stop|pause)\b/.test(t) && !/resume|restart/.test(t)) {
    return { type: "halt", params: {}, summary: "Halt all trading immediately." };
  }
  if (/\b(resume|restart|unpause|continue)\b/.test(t)) {
    return { type: "resume", params: {}, summary: "Resume trading." };
  }

  // strategy keywords
  const strategyMap: Record<string, string> = {
    conservative: "defensive", defensive: "defensive",
    aggressive: "momentum",   momentum: "momentum",
    balanced: "balanced",     contrarian: "contrarian",
  };
  for (const [kw, strat] of Object.entries(strategyMap)) {
    if (t.includes(kw)) {
      return {
        type: "set_strategy",
        params: { strategy_name: strat },
        summary: `Switch strategy to ${strat}.`,
      };
    }
  }

  // size / position
  const sizeMatch = t.match(/\bsize\b.*?\$?(\d+(?:\.\d+)?)/);
  if (sizeMatch) {
    const n = parseFloat(sizeMatch[1]);
    return {
      type: "update_limits",
      params: { max_position_usd: n },
      summary: `Set max position size to $${n}.`,
    };
  }

  // take profit
  const tpMatch = t.match(/\btake\s+profit\b|profit\s+target.*?(\d+(?:\.\d+)?)%/);
  if (tpMatch) {
    const pct = tpMatch[1] ? parseFloat(tpMatch[1]) / 100 : 0.05;
    return {
      type: "set_autopilot",
      params: { enabled: true, profit_target_pct: pct, protect_principal: true },
      summary: `Enable autopilot profit-take at ${(pct * 100).toFixed(0)}%.`,
    };
  }

  // withdraw
  const withdrawMatch = t.match(/withdraw\s+(\d+(?:\.\d+)?)\s*(usdt|eth|bnb)\s+to\s+(0x[0-9a-f]{40})/i);
  if (withdrawMatch) {
    const [, amtStr, token, to_address] = withdrawMatch;
    return {
      type: "withdraw",
      params: { to_address, amount: parseFloat(amtStr), token: token.toUpperCase() },
      summary: `Withdraw ${amtStr} ${token.toUpperCase()} to ${to_address.slice(0, 6)}...${to_address.slice(-4)}.`,
    };
  }

  // deposit
  if (/\bdeposit\b/.test(t)) {
    return { type: "deposit_info", params: {}, summary: "Show deposit address and on-ramp." };
  }

  return null; // read-only — no proposed action
}

// ── Action dispatcher ─────────────────────────────────────────────────────────

export async function dispatchAction(action: ProposedAction, d: ConciergeDispatchers): Promise<void> {
  switch (action.type) {
    case "set_strategy":
      await d.setStrategy(withToken({ strategy_name: action.params.strategy_name }));
      break;
    case "update_limits":
      await d.updateLimits(withToken(action.params));
      break;
    case "set_autopilot":
      await d.setAutopilot(withToken({ autopilot: action.params }));
      break;
    case "halt":
      await d.setHalted(withToken({ halted: true }));
      await d.setControl(withToken({ trading_halted: true, updated_by: "copilot" }));
      break;
    case "resume":
      await d.setHalted(withToken({ halted: false }));
      await d.setControl(withToken({ trading_halted: false, updated_by: "copilot" }));
      break;
    case "mark_setup":
      await d.recordFeedback(withToken(action.params));
      break;
    case "withdraw": {
      const p = action.params;
      await d.enqueueCommand(withToken({
        command_type: "withdraw",
        params: JSON.stringify({ to_address: p.to_address, amount: p.amount, token: p.token }),
        queued_by: "copilot",
      }));
      break;
    }
    case "deposit_info":
      d.onDepositInfo();
      break;
  }
}
```

- [ ] **Step 2: Write unit tests for concierge.ts**

Create `web/src/lib/concierge.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { parseIntent, dispatchAction, type ProposedAction } from "./concierge";

// ── parseIntent ───────────────────────────────────────────────────────────────
describe("parseIntent", () => {
  it("returns halt for 'halt trading'", () => {
    expect(parseIntent("halt trading")).toMatchObject({ type: "halt" });
  });

  it("returns resume for 'resume now'", () => {
    expect(parseIntent("resume now")).toMatchObject({ type: "resume" });
  });

  it("returns set_strategy defensive for 'go conservative'", () => {
    expect(parseIntent("go conservative")).toMatchObject({ type: "set_strategy", params: { strategy_name: "defensive" } });
  });

  it("returns set_strategy momentum for 'aggressive mode'", () => {
    expect(parseIntent("aggressive mode")).toMatchObject({ type: "set_strategy", params: { strategy_name: "momentum" } });
  });

  it("returns update_limits for 'set size to $8'", () => {
    expect(parseIntent("set size to $8")).toMatchObject({ type: "update_limits", params: { max_position_usd: 8 } });
  });

  it("returns set_autopilot for 'take profit'", () => {
    const a = parseIntent("take profit");
    expect(a?.type).toBe("set_autopilot");
  });

  it("returns set_autopilot with pct for 'profit target 10%'", () => {
    const a = parseIntent("profit target 10%") as Extract<ProposedAction, { type: "set_autopilot" }>;
    expect(a.params.profit_target_pct).toBeCloseTo(0.1);
  });

  it("returns withdraw for full withdraw command", () => {
    const a = parseIntent("withdraw 5 USDT to 0xabcdef1234567890abcdef1234567890abcdef12") as Extract<ProposedAction, { type: "withdraw" }>;
    expect(a.type).toBe("withdraw");
    expect(a.params.amount).toBe(5);
    expect(a.params.token).toBe("USDT");
  });

  it("returns deposit_info for 'deposit'", () => {
    expect(parseIntent("I want to deposit")).toMatchObject({ type: "deposit_info" });
  });

  it("returns null for unknown text", () => {
    expect(parseIntent("what is the current price?")).toBeNull();
    expect(parseIntent("hello")).toBeNull();
  });
});

// ── dispatchAction ────────────────────────────────────────────────────────────
describe("dispatchAction", () => {
  function makeDispatchers() {
    return {
      setStrategy:    vi.fn().mockResolvedValue(undefined),
      updateLimits:   vi.fn().mockResolvedValue(undefined),
      setAutopilot:   vi.fn().mockResolvedValue(undefined),
      setHalted:      vi.fn().mockResolvedValue(undefined),
      setControl:     vi.fn().mockResolvedValue(undefined),
      recordFeedback: vi.fn().mockResolvedValue(undefined),
      enqueueCommand: vi.fn().mockResolvedValue("cmd-id"),
      onDepositInfo:  vi.fn(),
    };
  }

  it("calls setStrategy for set_strategy action", async () => {
    const d = makeDispatchers();
    await dispatchAction({ type: "set_strategy", params: { strategy_name: "defensive" }, summary: "" }, d);
    expect(d.setStrategy).toHaveBeenCalledWith(expect.objectContaining({ strategy_name: "defensive" }));
  });

  it("calls both setHalted and setControl for halt action", async () => {
    const d = makeDispatchers();
    await dispatchAction({ type: "halt", params: {}, summary: "" }, d);
    expect(d.setHalted).toHaveBeenCalledWith(expect.objectContaining({ halted: true }));
    expect(d.setControl).toHaveBeenCalledWith(expect.objectContaining({ trading_halted: true }));
  });

  it("enqueues withdraw command with JSON params", async () => {
    const d = makeDispatchers();
    await dispatchAction({
      type: "withdraw",
      params: { to_address: "0xabc", amount: 5, token: "USDT" },
      summary: "",
    }, d);
    expect(d.enqueueCommand).toHaveBeenCalledWith(expect.objectContaining({ command_type: "withdraw" }));
    const call = d.enqueueCommand.mock.calls[0][0];
    const parsed = JSON.parse(call.params);
    expect(parsed.to_address).toBe("0xabc");
    expect(parsed.amount).toBe(5);
  });

  it("calls onDepositInfo for deposit_info action", async () => {
    const d = makeDispatchers();
    await dispatchAction({ type: "deposit_info", params: {}, summary: "" }, d);
    expect(d.onDepositInfo).toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd /root/claude/projects/alien-trade/web && bun run test --run lib/concierge.test.ts 2>&1 | tail -15
```

Expected: all tests pass. If Vitest is not configured, check `web/vitest.config.ts` — it should already exist.

- [ ] **Step 4: Build check and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```

```bash
cd /root/claude/projects/alien-trade
git add web/src/lib/concierge.ts web/src/lib/concierge.test.ts
git commit -m "feat(concierge): pure intent grammar + ProposedAction types + dispatch router (11 tests)"
```

---

### Task 4: Action confirmation cards + suggestion chips in CoPilotDrawer (Units 2+3)

**Files:**
- Modify: `web/src/components/CoPilotDrawer.tsx` — action card rendering, confirm/cancel flow, updated suggestion chips, agent action response wiring

**Interfaces:**
- Consumes: `parseIntent`, `dispatchAction`, `ProposedAction` from `./lib/concierge`
- Consumes: `suggestionConservative`, `suggestionAdjustRisk`, `suggestionTakeProfit` from `./lib/concierge`

- [ ] **Step 1: Read current CoPilotDrawer.tsx**

Read the full file at `web/src/components/CoPilotDrawer.tsx`. Note:
- `CHIPS` constant (the 4 Q&A chips on empty state)
- `send()` function (calls `ask` action)
- Message rendering in the messages map

- [ ] **Step 2: Add imports and concierge integration**

At the top of `CoPilotDrawer.tsx`, add:
```typescript
import { parseIntent, dispatchAction, type ProposedAction, suggestionConservative, suggestionAdjustRisk, suggestionTakeProfit } from "@/lib/concierge";
import { useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Check, X as XIcon } from "lucide-react";
```

(Note: `X` is already imported — use `XIcon` alias only if there's a conflict. Check existing imports and alias accordingly.)

- [ ] **Step 3: Replace CHIPS with action suggestion cards**

Find the `CHIPS` constant and replace:
```typescript
const SUGGESTION_CARDS = [
  { label: "🛡️ Start a conservative run", action: () => suggestionConservative() },
  { label: "🎚️ Adjust risk & size",        action: () => suggestionAdjustRisk(4, 4) },
  { label: "💰 Take profit at 5%",          action: () => suggestionTakeProfit(0.05) },
  { label: "➕ Type my own…",               action: null },
] as const;
```

- [ ] **Step 4: Add pendingAction state**

In the component body, add state:
```typescript
const [pendingAction, setPendingAction] = useState<ProposedAction | null>(null);
const [actionLoading, setActionLoading] = useState(false);
const [withdrawConfirmStep, setWithdrawConfirmStep] = useState(false);
```

- [ ] **Step 5: Add Convex mutation hooks for dispatching**

After existing mutation hooks, add:
```typescript
const setStrategy    = useMutation(api.config.setStrategy);
const updateLimits   = useMutation(api.config.updateLimits);
const setAutopilot   = useMutation(api.config.setAutopilot);
const setHalted      = useMutation(api.config.setHalted);
const setControl     = useMutation(api.agentControl.set);
const recordFeedback = useMutation(api.feedback.record);
const enqueueCommand = useMutation(api.agentCommands.enqueue);
```

- [ ] **Step 6: Add confirmAction handler**

```typescript
const confirmAction = async () => {
  if (!pendingAction || actionLoading) return;
  if (pendingAction.type === "withdraw" && !withdrawConfirmStep) {
    setWithdrawConfirmStep(true);
    return;
  }
  setActionLoading(true);
  try {
    await dispatchAction(pendingAction, {
      setStrategy,
      updateLimits,
      setAutopilot,
      setHalted,
      setControl: (a) => setControl(a as Parameters<typeof setControl>[0]),
      recordFeedback,
      enqueueCommand,
      onDepositInfo: () => { setPendingAction(null); /* DepositView handled separately */ },
    });
    await addMessage(withToken({ role: "assistant", content: `✅ Done: ${pendingAction.summary}`, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
    setPendingAction(null);
    setWithdrawConfirmStep(false);
  } catch (e) {
    await addMessage(withToken({ role: "assistant", content: `❌ Action failed: ${String(e)}`, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
  } finally {
    setActionLoading(false);
  }
};
```

- [ ] **Step 7: Add ActionConfirmCard component (inline, above export)**

```tsx
function ActionConfirmCard({
  action, onConfirm, onCancel, loading, withdrawStep,
}: {
  action: ProposedAction;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
  withdrawStep: boolean;
}) {
  const isWithdraw = action.type === "withdraw";
  const destAddress = isWithdraw ? (action as Extract<ProposedAction, { type: "withdraw" }>).params.to_address : null;

  return (
    <div className="rounded-xl border border-yellow/30 bg-yellow/5 px-4 py-3 space-y-2.5">
      <div className="flex items-start gap-2">
        <span className="text-yellow text-[11px] font-mono font-bold uppercase tracking-widest mt-0.5">Action</span>
        <p className="font-mono text-[12px] text-text leading-relaxed flex-1">
          {withdrawStep && destAddress
            ? <>Sending to: <span className="text-yellow font-bold break-all">{destAddress}</span><br />Confirm address is correct.</>
            : action.summary}
        </p>
      </div>
      <div className="flex gap-2">
        <button onClick={onConfirm} disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 bg-green/15 border border-green/30 text-green font-mono text-[11px] font-bold rounded-lg py-1.5 hover:bg-green/25 transition-colors cursor-pointer disabled:opacity-50">
          <Check className="w-3.5 h-3.5" />
          {loading ? "Executing…" : withdrawStep ? "Yes, send it" : "Confirm"}
        </button>
        <button onClick={onCancel} disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 bg-elevated border border-border text-muted-fg font-mono text-[11px] rounded-lg py-1.5 hover:text-text transition-colors cursor-pointer disabled:opacity-50">
          <XIcon className="w-3.5 h-3.5" />
          Cancel
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Wire suggestion cards in the chips area**

Find the area where chips are currently rendered (the `msgs.length === 0` block). Replace with:

```tsx
{msgs.length === 0 && !pendingAction && (
  <div className="space-y-1.5">
    {SUGGESTION_CARDS.map((card) => (
      <button key={card.label}
        onClick={() => {
          if (card.action === null) {
            // focus input
          } else {
            const proposed = card.action();
            setPendingAction(proposed);
          }
        }}
        className="w-full text-left font-mono text-[11px] text-text/80 border border-border/60 rounded-lg px-3 py-2 hover:bg-elevated/70 hover:border-border transition-colors cursor-pointer">
        {card.label}
      </button>
    ))}
  </div>
)}
```

- [ ] **Step 9: Render pending action card + wire send() to parse intent**

In the messages area, just before `<div ref={bottomRef} />`, add:
```tsx
{pendingAction && (
  <ActionConfirmCard
    action={pendingAction}
    onConfirm={confirmAction}
    onCancel={() => { setPendingAction(null); setWithdrawConfirmStep(false); }}
    loading={actionLoading}
    withdrawStep={withdrawConfirmStep}
  />
)}
```

In the `send()` function, after `setQuestion("")`, add intent parsing for free text:
```typescript
const intent = parseIntent(text);
if (intent && intent.type !== "deposit_info") {
  await addMessage(withToken({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
  setPendingAction(intent);
  setLoading(false);
  return;
}
```
(This goes BEFORE the `startStream` / `ask` call block, so recognized commands show a confirm card instead of going to the LLM.)

- [ ] **Step 10: Build check and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```

```bash
cd /root/claude/projects/alien-trade
git add web/src/components/CoPilotDrawer.tsx
git commit -m "feat(concierge): action confirmation cards + suggestion chips in CoPilotDrawer — HITL for all state-changing actions"
```

---

### Task 5: Agent /copilot endpoint optional action response (Unit 2 agent)

**Files:**
- Modify: `agent/server.py` — extend `/copilot` POST to optionally return `action: ProposedAction | null`

**Interfaces:**
- `/copilot` response gains optional `action` field: `{ answer: str, sources: list, action: dict | None }`
- Client in `CoPilotDrawer.tsx` already handles `action` being absent (falls back to grammar)

- [ ] **Step 1: Find the /copilot endpoint in server.py**

```bash
grep -n "copilot\|/copilot" /root/claude/projects/alien-trade/agent/server.py | head -10
```

- [ ] **Step 2: Extend /copilot to parse action intent from LLM answer**

Open `agent/server.py`. Find the `/copilot` endpoint handler. After computing the `answer` string, add an action extraction step:

```python
@app.post("/copilot")
async def copilot_endpoint(req: Request):
    body = await req.json()
    question = body.get("question", "")
    
    # ... existing answer generation ...
    answer = ...  # existing logic
    sources = ...  # existing logic
    
    # Try to extract a structured action from the LLM answer
    action = _extract_action(question, answer)
    
    return {"answer": answer, "sources": sources, "action": action}


_ACTION_VERBS = {
    "halt": {"type": "halt", "params": {}, "summary": "Halt all trading."},
    "resume": {"type": "resume", "params": {}, "summary": "Resume trading."},
    "stop trading": {"type": "halt", "params": {}, "summary": "Halt all trading."},
}

def _extract_action(question: str, answer: str) -> dict | None:
    """Lightweight server-side action extraction. Client grammar is the primary path."""
    q = question.lower()
    for trigger, action in _ACTION_VERBS.items():
        if trigger in q:
            return action
    return None
```

Note: The client-side `parseIntent` is the primary and most reliable path. This server-side extraction is a supplementary signal.

- [ ] **Step 3: Update CoPilotDrawer to consume action from ask response**

In `web/src/components/CoPilotDrawer.tsx`, the `ask` call currently is:
```typescript
const res = await ask(withToken({ question: text }));
await finaliseStream(withToken({ id: streamId, content: res.answer, sources_json: JSON.stringify(res.sources) }));
```

After the `ask` call, check if the response contains an action:
```typescript
const res = await ask(withToken({ question: text }));
await finaliseStream(withToken({ id: streamId, content: res.answer, sources_json: JSON.stringify(res.sources) }));
// If agent returned a structured action, surface the confirm card
if (res.action && !pendingAction) {
  setPendingAction(res.action as ProposedAction);
}
```

- [ ] **Step 4: Commit**

```bash
cd /root/claude/projects/alien-trade
git add agent/server.py web/src/components/CoPilotDrawer.tsx
git commit -m "feat(concierge): /copilot endpoint returns optional action; client wires to confirm card"
```

---

### Task 6: TrackersView (Unit 4)

**Files:**
- Create: `web/src/views/TrackersView.tsx`
- Modify: `web/src/components/SideNav.tsx` — add "trackers" to View union + nav item
- Modify: `web/src/components/BottomNav.tsx` — add trackers tab
- Modify: `web/src/App.tsx` — add `case "trackers"`

**Interfaces:**
- Consumes: `api.positions.open` (existing), `api.agentCommands.list` (existing), `api.decisions.recent` (existing)
- No new Convex APIs needed.

- [ ] **Step 1: Create TrackersView.tsx**

Create `web/src/views/TrackersView.tsx`:

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { RegimeBadge } from "../components/RegimeBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, ts } from "../lib/formatters";
import { Activity, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  queued:  "text-yellow border-yellow/30 bg-yellow/8",
  running: "text-cyan border-cyan/30 bg-cyan/8",
  done:    "text-green border-green/30 bg-green/8",
  failed:  "text-red border-red/30 bg-red/8",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  queued:  <Clock className="w-3 h-3" />,
  running: <Loader2 className="w-3 h-3 animate-spin" />,
  done:    <CheckCircle2 className="w-3 h-3" />,
  failed:  <XCircle className="w-3 h-3" />,
};

export function TrackersView() {
  const positions = useQuery(api.positions.open) ?? [];
  const commands  = useQuery(api.agentCommands.list, { limit: 20 }) ?? [];
  const decisions = useQuery(api.decisions.recent, { limit: 1 }) ?? [];

  const ongoing = commands.filter((c: Record<string, string>) => c.status === "running");
  const pending = commands.filter((c: Record<string, string>) => c.status === "queued");
  const recent  = commands.filter((c: Record<string, string>) => c.status === "done" || c.status === "failed").slice(0, 5);
  const nextDecision = decisions[0];

  return (
    <div className="max-w-[900px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-cyan rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--cyan)" }} />
          Live Agent Activity
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Trackers</h1>
      </div>

      {/* Ongoing — open positions */}
      <Panel label="Ongoing Trades" tick="green" action={
        <span className="font-mono text-[10px] text-muted-fg">{positions.length} open</span>
      }>
        {positions.length === 0 ? (
          <div className="flex items-center gap-3 py-3">
            <Activity className="w-4 h-4 text-muted-fg" />
            <p className="font-mono text-[12px] text-muted-fg">No active trades — agent is watching the market.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {positions.map((p: Record<string, number|string>) => {
              const pnlPos = (p.unrealized_pnl_usd as number) >= 0;
              return (
                <div key={p._id as string} className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5">
                  <span className="font-mono font-bold text-cyan text-[13px] w-14">{p.symbol as string}</span>
                  <span className="font-mono text-[11px] text-muted-fg">{(p.quantity as number).toFixed(6)}</span>
                  <span className="font-mono text-[11px] text-muted-fg ml-1">@ {usd(p.avg_entry_price as number)}</span>
                  <span className={cn("ml-auto font-mono text-[12px] font-bold", pnlPos ? "text-green" : "text-red")}>
                    {pnlPos ? "+" : ""}{usd(p.unrealized_pnl_usd as number)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* Next planned action */}
      {nextDecision && (
        <Panel label="Next Decision" tick="cyan">
          <div className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5">
            <span className="font-mono font-bold text-cyan text-[13px] w-14">{nextDecision.symbol}</span>
            <RegimeBadge regime={nextDecision.regime} />
            <span className={cn(
              "ml-auto font-mono text-[10px] font-bold tracking-[0.16em] uppercase px-2 py-1 rounded border",
              nextDecision.risk_verdict === "allow"
                ? "text-green border-green/30 bg-green/10"
                : "text-red border-red/30 bg-red/10",
            )}>{nextDecision.risk_verdict}</span>
          </div>
        </Panel>
      )}

      {/* Pending commands */}
      {(ongoing.length > 0 || pending.length > 0) && (
        <Panel label="Pending Commands" tick="yellow" action={
          <span className="font-mono text-[10px] text-muted-fg">{ongoing.length + pending.length} queued</span>
        }>
          <div className="space-y-2">
            {[...ongoing, ...pending].map((c: Record<string, string>) => (
              <div key={c._id} className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5">
                <span className={cn("flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded border", STATUS_STYLE[c.status])}>
                  {STATUS_ICON[c.status]}
                  {c.status}
                </span>
                <span className="font-mono text-[12px] text-text">{c.command_type}</span>
                <span className="font-mono text-[10px] text-muted-fg ml-auto">{ts(parseInt(c.queued_at_ms))}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* Recent command history */}
      {recent.length > 0 && (
        <Panel label="Command History" tick="cyan">
          <div className="space-y-2">
            {recent.map((c: Record<string, string>) => (
              <div key={c._id} className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5">
                <span className={cn("flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded border", STATUS_STYLE[c.status])}>
                  {STATUS_ICON[c.status]}
                  {c.status}
                </span>
                <span className="font-mono text-[12px] text-text">{c.command_type}</span>
                {c.error && <span className="font-mono text-[10px] text-red truncate max-w-[200px]">{c.error}</span>}
                <span className="font-mono text-[10px] text-muted-fg ml-auto">{ts(parseInt(c.queued_at_ms))}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add "trackers" to SideNav View union and nav items**

Open `web/src/components/SideNav.tsx`. Add `"trackers"` to the `View` type union:
```typescript
export type View = "overview" | "trackers" | "chart" | "positions" | "agents" | "controls" | "pipeline" | "portfolio" | "logs" | "notifications" | "docs";
```

Add to `NAV_ITEMS` array (after `"overview"`, before `"chart"`):
```typescript
{ view: "trackers", icon: Activity, label: "Trackers" },
```
(`Activity` is already imported from lucide-react.)

- [ ] **Step 3: Add trackers to BottomNav**

Open `web/src/components/BottomNav.tsx`. Replace `"positions"` with `"trackers"` in the TABS array (keep 5 total):
```typescript
const TABS = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "trackers",  icon: Activity,        label: "Trackers" },
  { view: "chart",     icon: LineChart,       label: "Chart" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
];
```
Add `Activity` and `LineChart` to lucide imports as needed.

- [ ] **Step 4: Add case "trackers" in App.tsx**

In `web/src/App.tsx`, add the import:
```typescript
import { TrackersView } from "./views/TrackersView";
```

In `renderView()`, add before `case "agents"`:
```typescript
case "trackers": return <TrackersView />;
```

- [ ] **Step 5: Build and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```

```bash
cd /root/claude/projects/alien-trade
git add web/src/views/TrackersView.tsx web/src/components/SideNav.tsx web/src/components/BottomNav.tsx web/src/App.tsx
git commit -m "feat(trackers): TrackersView — ongoing positions, pending commands, next decision"
```

---

### Task 7: Post-trade tour + DepositView (Units 7 + 5)

**Files:**
- Modify: `web/src/lib/tour.ts` — add `startPostTradeTour()`
- Modify: `web/src/App.tsx` — auto-trigger post-trade tour on 0→1 trades; add DepositView
- Create: `web/src/views/DepositView.tsx`
- Modify: `web/src/components/SideNav.tsx` — add "deposit" view
- Modify: `web/src/components/LiveHeader.tsx` — wire Deposit button to view

**Interfaces:**
- `startPostTradeTour(): void` exported from `tour.ts`
- `api.walletState.get` returns `address?: string` (added in Task 2)

- [ ] **Step 1: Add startPostTradeTour to tour.ts**

Open `web/src/lib/tour.ts`. After `startTour()`, add:

```typescript
const POST_TOUR_KEY = "alien-trade:posttrade-tour-seen-v1";

export function hasPostTradeTourBeenSeen(): boolean {
  return localStorage.getItem(POST_TOUR_KEY) === "1";
}

export function startPostTradeTour(): void {
  const driverObj = driver({
    showProgress: true,
    progressText: "{{current}} / {{total}}",
    animate: true,
    overlayOpacity: 0.65,
    popoverClass: "alien-tour-popover",
    onDestroyed: () => localStorage.setItem(POST_TOUR_KEY, "1"),
    steps: [
      {
        element: '[data-tour="nav-trackers"]',
        popover: {
          title: "First trade logged",
          description: "Your agent made its first trade. The Trackers view shows all ongoing positions and queued commands.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-portfolio"]',
        popover: {
          title: "Check your portfolio",
          description: "Portfolio shows your TWAK wallet balance — USDT, ETH, BNB, and total value after the trade.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-chart"]',
        popover: {
          title: "See the entry on the chart",
          description: "The chart marks your buy with a green ▲ and sell with a red ▼.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-copilot"]',
        popover: {
          title: "Withdraw or take profit",
          description: "Ask the Co-Pilot: \"withdraw 2 USDT to 0x...\" or \"take profit at 5%\" to set up autopilot.",
          side: "right",
        },
      },
    ],
  });
  driverObj.drive();
}
```

Also add `data-tour="nav-trackers"` to the Trackers button in `SideNav.tsx` (it's dynamic via `data-tour={`nav-${item.view}`}` already — verify it renders as `data-tour="nav-trackers"`).

- [ ] **Step 2: Auto-trigger post-trade tour in App.tsx**

Open `web/src/App.tsx`. Import:
```typescript
import { startPostTradeTour, hasPostTradeTourBeenSeen } from "./lib/tour";
```

Add a trades query after the existing `events` query:
```typescript
const trades = useQuery(api.trades.recent, { limit: 1 });
```

Add a useRef and useEffect for 0→1 trades transition:
```typescript
const tradeCountRef = useRef<number | null>(null);
useEffect(() => {
  if (trades === undefined) return;
  const count = trades.length;
  if (tradeCountRef.current === 0 && count === 1 && !hasPostTradeTourBeenSeen()) {
    setTimeout(startPostTradeTour, 800);
  }
  tradeCountRef.current = count;
}, [trades]);
```

- [ ] **Step 3: Create DepositView.tsx**

Create `web/src/views/DepositView.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Copy, Check, ExternalLink } from "lucide-react";
import QRCode from "qrcode";

type Tab = "deposit" | "buy";

export function DepositView() {
  const wallet  = useQuery(api.walletState.get);
  const address = wallet?.address ?? "";
  const [tab, setTab]       = useState<Tab>("deposit");
  const [copied, setCopied] = useState(false);
  const canvasRef           = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (tab === "deposit" && address && canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, address, {
        width: 180,
        color: { dark: "#000000", light: "#ffffff" },
        errorCorrectionLevel: "M",
      }).catch(() => {/* ignore */});
    }
  }, [tab, address]);

  const copy = () => {
    if (!address) return;
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-[520px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          TWAK Self-Custody · BSC
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Fund Wallet</h1>
      </div>

      {/* Tab selector */}
      <div className="flex gap-1 p-1 bg-elevated rounded-xl border border-border">
        {(["deposit", "buy"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={cn(
              "flex-1 font-mono text-[12px] font-bold py-1.5 rounded-lg transition-colors cursor-pointer capitalize",
              tab === t ? "bg-bg text-text border border-border shadow-sm" : "text-muted-fg hover:text-text",
            )}>
            {t === "deposit" ? "Deposit" : "Buy Crypto"}
          </button>
        ))}
      </div>

      {tab === "deposit" && (
        <Panel label="BSC Deposit Address" tick="green">
          {!address ? (
            <p className="font-mono text-[12px] text-muted-fg py-4 text-center">
              Address loads after first agent cycle…
            </p>
          ) : (
            <div className="space-y-4">
              <p className="font-mono text-[11px] text-muted-fg">
                Send USDT (BEP-20) or BNB directly to this address. <span className="text-yellow font-bold">BSC chain only — do not send from Ethereum mainnet.</span>
              </p>
              <div className="flex justify-center">
                <canvas ref={canvasRef} className="rounded-xl" />
              </div>
              <div className="bg-bg border border-border rounded-lg px-3 py-2 flex items-center gap-2">
                <span className="font-mono text-[11px] text-text truncate flex-1">{address}</span>
                <button onClick={copy}
                  className="flex-shrink-0 text-muted-fg hover:text-green transition-colors cursor-pointer">
                  {copied ? <Check className="w-4 h-4 text-green" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <Button onClick={copy} className="w-full bg-green text-[#04140c] font-bold hover:bg-green/80 cursor-pointer flex items-center gap-2">
                {copied ? <><Check className="w-4 h-4" /> Copied!</> : <><Copy className="w-4 h-4" /> Copy Address</>}
              </Button>
              <div className="font-mono text-[10px] text-muted-fg space-y-1">
                <div className="flex items-center justify-between">
                  <span>USDT (BEP-20)</span><span className="text-text">Trading capital</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>BNB</span><span className="text-yellow">Gas — keep ≥ 0.005</span>
                </div>
              </div>
            </div>
          )}
        </Panel>
      )}

      {tab === "buy" && (
        <Panel label="Buy Crypto with Card" tick="cyan">
          <div className="space-y-4 py-2">
            <p className="font-mono text-[12px] text-muted-fg leading-relaxed">
              Purchase USDT or BNB directly to your self-custody wallet using a credit card or bank transfer via Onramper.
            </p>
            <div className="bg-elevated border border-border rounded-xl p-4 space-y-2">
              <p className="font-mono text-[11px] text-muted-fg">Your wallet address:</p>
              <p className="font-mono text-[12px] text-text break-all">{address || "Loading…"}</p>
            </div>
            <Button
              className="w-full bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer flex items-center gap-2"
              onClick={() => window.open(`https://onramper.com/?wallets=BSC:${address}&defaultCrypto=USDT_BSC`, "_blank", "noopener,noreferrer")}
              disabled={!address}
            >
              <ExternalLink className="w-4 h-4" />
              Buy via Onramper →
            </Button>
            <p className="font-mono text-[10px] text-muted-fg text-center">
              Onramper supports 150+ payment methods in 180+ countries. KYC may be required.
            </p>
          </div>
        </Panel>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Add "deposit" to SideNav, BottomNav, App**

In `web/src/components/SideNav.tsx`, add `"deposit"` to the `View` union and add a nav item. Import `Wallet2` from lucide (or use `ArrowDownToLine`):
```typescript
export type View = "overview" | "trackers" | "deposit" | "chart" | "positions" | "agents" | "controls" | "pipeline" | "portfolio" | "logs" | "notifications" | "docs";
```
Add to NAV_ITEMS (after "portfolio"):
```typescript
{ view: "deposit", icon: ArrowDownToLine, label: "Deposit" },
```

In `web/src/App.tsx`, add the import and case:
```typescript
import { DepositView } from "./views/DepositView";
// in renderView():
case "deposit": return <DepositView />;
```

- [ ] **Step 5: Wire the "Deposit" button in LiveHeader to the deposit view**

Open `web/src/components/LiveHeader.tsx`. The existing code may show a static "Deposit" badge/button. Find it and add an `onClick` to navigate to the deposit view by accepting `onDeposit?: () => void` prop.

Check if `LiveHeader` has a `Deposit` button. If not, add one. Update `LiveHeader` props:
```typescript
type Props = { halted: boolean; mode?: string; onKillToggle: () => void; selectedSymbol?: string; onSymbolChange?: (s: string) => void; onDeposit?: () => void };
```

Wire it in `App.tsx` AppShell → LiveHeader — or pass `onDeposit` directly to `LiveHeader` via `AppShell`. Since `AppShell` wraps `LiveHeader`, add `onDeposit` through the chain.

Simpler: in `LiveHeader.tsx`, after the symbol selector, add a deposit button:
```tsx
{onDeposit && (
  <button onClick={onDeposit} data-tour="deposit-btn"
    className="hidden sm:flex items-center gap-1.5 font-mono text-[10px] font-bold text-cyan border border-cyan/25 bg-cyan/8 rounded-lg px-2.5 py-1 hover:bg-cyan/15 transition-colors cursor-pointer">
    ↓ Deposit
  </button>
)}
```

Pass through AppShell and wire from App.tsx: `onDeposit={() => setView("deposit")}`.

- [ ] **Step 6: Build and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```

```bash
cd /root/claude/projects/alien-trade
git add web/src/lib/tour.ts web/src/App.tsx web/src/views/DepositView.tsx \
  web/src/components/SideNav.tsx web/src/components/LiveHeader.tsx \
  web/src/components/AppShell.tsx
git commit -m "feat(deposit+tour): DepositView (QR + Onramper), post-trade tour on first fill"
```

---

### Task 8: WithdrawView + backend command worker handler (Unit 6)

**Files:**
- Create: `web/src/views/WithdrawView.tsx` — form + HITL double-confirm
- Modify: `web/src/components/SideNav.tsx` — add "withdraw" view
- Modify: `web/src/App.tsx` — add case "withdraw"
- Modify: `agent/command_worker.py` — add "withdraw" command handler
- Create: `agent/tests/test_command_worker_withdraw.py` — tests

**Interfaces:**
- `agentCommands.enqueue({ command_type: "withdraw", params: JSON.stringify({ to_address, amount, token }) })`
- `twak transfer --to <addr> --amount <n> --token <contract_or_symbol> --chain bsc --json`

- [ ] **Step 1: Write backend tests first**

Create `agent/tests/test_command_worker_withdraw.py`:

```python
import json
from unittest.mock import MagicMock, patch
from agent.command_worker import _dispatch


def _make_twak(tx_hash="0xabc"):
    twak = MagicMock()
    twak.available = True
    twak.transfer = MagicMock(return_value={"hash": tx_hash, "explorer": "https://bscscan.com/tx/0xabc"})
    return twak


def test_withdraw_usdt_dispatches_transfer():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        result = _dispatch("withdraw", {"to_address": "0xDEAD", "amount": 5.0, "token": "USDT"})
    twak.transfer.assert_called_once_with("0xDEAD", 5.0, "USDT", chain="bsc")
    assert result["tx_hash"] == "0xabc"


def test_withdraw_bnb_native_transfer():
    twak = _make_twak("0xdef")
    with patch("agent.command_worker.TwakCli", return_value=twak):
        result = _dispatch("withdraw", {"to_address": "0xBEEF", "amount": 0.005, "token": "BNB"})
    twak.transfer.assert_called_once_with("0xBEEF", 0.005, "BNB", chain="bsc")
    assert result["tx_hash"] == "0xdef"


def test_withdraw_missing_to_address_raises():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        try:
            _dispatch("withdraw", {"amount": 5.0, "token": "USDT"})
            assert False, "should raise"
        except (ValueError, KeyError):
            pass  # expected


def test_withdraw_zero_amount_raises():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        try:
            _dispatch("withdraw", {"to_address": "0xABC", "amount": 0, "token": "USDT"})
            assert False, "should raise"
        except ValueError:
            pass


def test_withdraw_invalid_address_raises():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        try:
            _dispatch("withdraw", {"to_address": "notanaddress", "amount": 1.0, "token": "USDT"})
            assert False, "should raise"
        except ValueError:
            pass
```

- [ ] **Step 2: Run tests — they should FAIL**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_command_worker_withdraw.py -v 2>&1 | tail -15
```

Expected: FAIL with `KeyError` or similar (withdraw case doesn't exist yet).

- [ ] **Step 3: Add TwakCli.transfer method**

Open `agent/twak_cli.py`. After `swap_execute`, add:

```python
def transfer(self, to_address: str, amount: float, token: str, *, chain: Optional[str] = None) -> dict:
    """Transfer tokens to another address via `twak transfer`."""
    args = [
        "transfer",
        "--to", to_address,
        "--amount", str(amount),
        "--chain", chain or self.chain,
        "--json",
    ]
    # BNB (native coin): no --token flag
    # ERC-20 tokens: pass symbol; twak resolves contract address
    if token.upper() != "BNB":
        args += ["--token", token]
    return self._run(*args)
```

- [ ] **Step 4: Add withdraw handler in command_worker.py**

Open `agent/command_worker.py`. In the `_dispatch` function, before the `raise ValueError(f"unknown command_type")` line, add:

```python
if cmd_type == "withdraw":
    to_addr = params.get("to_address", "")
    amount  = float(params.get("amount", 0))
    token   = params.get("token", "USDT")
    # Validate before calling TWAK
    if not re.match(r"^0x[0-9a-fA-F]{40}$", to_addr):
        raise ValueError(f"invalid BSC address: {to_addr!r}")
    if amount <= 0:
        raise ValueError(f"amount must be > 0, got {amount}")
    result = twak.transfer(to_addr, amount, token, chain="bsc")
    tx_hash = result.get("hash") or result.get("txHash") or ""
    return {"tx_hash": tx_hash, "explorer": result.get("explorer", ""), "amount": amount, "token": token, "to": to_addr}
```

Also add `import re` at the top of the file if not already present.

- [ ] **Step 5: Run tests — they should PASS**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_command_worker_withdraw.py -v 2>&1 | tail -10
```

Expected: all 5 tests pass.

- [ ] **Step 6: Create WithdrawView.tsx**

Create `web/src/views/WithdrawView.tsx`:

```tsx
import { useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";
import { AlertTriangle, ArrowUpFromLine, Check } from "lucide-react";
import { usd } from "../lib/formatters";

type Token = "USDT" | "ETH" | "BNB";
type Step = "form" | "confirm" | "done";

const TOKEN_MAX: Record<Token, (w: Record<string, number>) => number> = {
  USDT: (w) => Math.max(0, w.usdt - 0.5),  // keep $0.50 buffer
  ETH:  (w) => w.eth,
  BNB:  (w) => Math.max(0, w.bnb - 0.005), // keep gas buffer
};

export function WithdrawView() {
  const wallet  = useQuery(api.walletState.get);
  const enqueue = useMutation(api.agentCommands.enqueue);

  const [token, setToken]       = useState<Token>("USDT");
  const [amount, setAmount]     = useState("");
  const [toAddr, setToAddr]     = useState("");
  const [step, setStep]         = useState<Step>("form");
  const [loading, setLoading]   = useState(false);
  const [txResult, setTxResult] = useState<string>("");
  const [error, setError]       = useState("");

  const maxAmount = wallet ? TOKEN_MAX[token](wallet as unknown as Record<string, number>) : 0;
  const addrValid = /^0x[0-9a-fA-F]{40}$/.test(toAddr.trim());
  const amtNum    = parseFloat(amount) || 0;
  const amtValid  = amtNum > 0 && amtNum <= maxAmount;

  const submit = () => {
    if (!addrValid || !amtValid) return;
    setStep("confirm");
    setError("");
  };

  const confirm = async () => {
    setLoading(true);
    try {
      await enqueue(withToken({
        command_type: "withdraw",
        params: JSON.stringify({ to_address: toAddr.trim(), amount: amtNum, token }),
        queued_by: "user",
      }));
      setStep("done");
    } catch (e) {
      setError(`Failed: ${String(e)}`);
      setStep("form");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[520px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-purple rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--purple)" }} />
          TWAK Self-Custody · BSC
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Withdraw</h1>
      </div>

      {step === "done" ? (
        <Panel label="Withdrawal Queued" tick="green">
          <div className="flex flex-col items-center gap-3 py-6">
            <div className="w-12 h-12 rounded-full bg-green/15 border border-green/30 flex items-center justify-center">
              <Check className="w-6 h-6 text-green" />
            </div>
            <p className="font-mono text-[13px] text-text text-center">
              Withdrawal queued. The agent will execute it in the next command cycle.
            </p>
            <p className="font-mono text-[11px] text-muted-fg text-center">
              Check the Trackers view to see its status.
            </p>
            <Button variant="outline" className="border-border text-muted-fg mt-2 cursor-pointer"
              onClick={() => { setStep("form"); setAmount(""); setToAddr(""); }}>
              New withdrawal
            </Button>
          </div>
        </Panel>
      ) : step === "confirm" ? (
        <Panel label="Confirm Withdrawal" tick="yellow">
          <div className="space-y-4">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow/8 border border-yellow/25">
              <AlertTriangle className="w-4 h-4 text-yellow flex-shrink-0 mt-0.5" />
              <p className="font-mono text-[11px] text-text leading-relaxed">
                Sending <span className="font-bold text-yellow">{amtNum} {token}</span> to:
              </p>
            </div>
            <div className="bg-bg border border-border rounded-lg px-3 py-2.5">
              <p className="font-mono text-[12px] text-text break-all">{toAddr.trim()}</p>
            </div>
            <p className="font-mono text-[10px] text-muted-fg">Verify the address above. Blockchain transactions are irreversible.</p>
            {error && <p className="font-mono text-[11px] text-red">{error}</p>}
            <div className="flex gap-2">
              <Button onClick={confirm} disabled={loading}
                className="flex-1 bg-yellow text-[#0d0900] font-bold hover:bg-yellow/80 cursor-pointer disabled:opacity-50 flex items-center gap-2">
                <ArrowUpFromLine className="w-4 h-4" />
                {loading ? "Queuing…" : "Yes, withdraw"}
              </Button>
              <Button variant="outline" onClick={() => setStep("form")} disabled={loading}
                className="flex-1 border-border text-muted-fg hover:text-text cursor-pointer">
                Cancel
              </Button>
            </div>
          </div>
        </Panel>
      ) : (
        <Panel label="Withdrawal Form" tick="purple">
          <div className="space-y-4">
            {/* Token selector */}
            <div>
              <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">Token</label>
              <div className="flex gap-2">
                {(["USDT", "ETH", "BNB"] as Token[]).map((t) => (
                  <button key={t} onClick={() => setToken(t)}
                    className={cn(
                      "flex-1 font-mono text-[12px] font-bold py-1.5 rounded-lg border transition-colors cursor-pointer",
                      token === t ? "bg-purple/15 border-purple/40 text-purple" : "border-border text-muted-fg hover:text-text",
                    )}>{t}</button>
                ))}
              </div>
            </div>
            {/* Balance display */}
            {wallet && (
              <p className="font-mono text-[11px] text-muted-fg">
                Available: <span className="text-text font-bold">{maxAmount.toFixed(6)} {token}</span>
                {token === "USDT" && <span className="text-muted-fg"> (keeping $0.50 buffer)</span>}
                {token === "BNB" && <span className="text-yellow"> (keeping 0.005 for gas)</span>}
              </p>
            )}
            {/* Amount */}
            <div>
              <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">Amount</label>
              <div className="flex gap-2">
                <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-purple" />
                <Button variant="outline" className="border-border text-muted-fg cursor-pointer text-[11px] font-mono"
                  onClick={() => setAmount(maxAmount.toFixed(6))}>Max</Button>
              </div>
            </div>
            {/* Destination */}
            <div>
              <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">Destination Address (BSC)</label>
              <Input value={toAddr} onChange={(e) => setToAddr(e.target.value)}
                placeholder="0x..."
                className={cn("bg-bg border-border text-text font-mono text-[12px] focus-visible:ring-purple",
                  toAddr && !addrValid ? "border-red/50" : "")} />
              {toAddr && !addrValid && (
                <p className="font-mono text-[10px] text-red mt-1">Invalid BSC address (must be 0x + 40 hex chars)</p>
              )}
            </div>
            {error && <p className="font-mono text-[11px] text-red">{error}</p>}
            <Button onClick={submit} disabled={!addrValid || !amtValid}
              className="w-full bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer disabled:opacity-50 flex items-center gap-2">
              <ArrowUpFromLine className="w-4 h-4" />
              Review Withdrawal
            </Button>
          </div>
        </Panel>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Add "withdraw" to SideNav, App**

In `web/src/components/SideNav.tsx`, add `"withdraw"` to View union. Add nav item (import `ArrowUpFromLine` from lucide):
```typescript
{ view: "withdraw", icon: ArrowUpFromLine, label: "Withdraw" },
```

In `web/src/App.tsx`:
```typescript
import { WithdrawView } from "./views/WithdrawView";
// in renderView():
case "withdraw": return <WithdrawView />;
```

- [ ] **Step 8: Run all tests and build**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_command_worker_withdraw.py -v 2>&1 | tail -8
cd web && bun run build 2>&1 | tail -5
```

- [ ] **Step 9: Commit**

```bash
cd /root/claude/projects/alien-trade
git add agent/twak_cli.py agent/command_worker.py \
  agent/tests/test_command_worker_withdraw.py \
  web/src/views/WithdrawView.tsx web/src/components/SideNav.tsx web/src/App.tsx
git commit -m "feat(withdraw): WithdrawView double-confirm + backend twak transfer handler (5 tests)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Unit 8 (logo) → Task 1
- ✅ Unit 1 (StartTradingCTA) → Task 2
- ✅ §7 (wallet address in Convex) → Task 2
- ✅ Unit 2 (concierge pure logic + dispatch) → Task 3
- ✅ Unit 2 (HITL action cards in drawer) → Task 4
- ✅ Unit 3 (suggestion cards) → Task 4
- ✅ Unit 2 agent (/copilot optional action) → Task 5
- ✅ Unit 4 (TrackersView) → Task 6
- ✅ Unit 7 (post-trade tour) → Task 7
- ✅ Unit 5 (DepositView Deposit+Buy tabs) → Task 7
- ✅ Unit 6 (WithdrawView + backend handler) → Task 8

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:**
- `ProposedAction` union defined once in `concierge.ts` (Task 3), consumed in `CoPilotDrawer.tsx` (Task 4) and `WithdrawView.tsx` (Task 8).
- `ConciergeDispatchers` interface in `concierge.ts` matches exact Convex mutation signatures confirmed from the codebase.
- `View` union updated in Task 6 (trackers), Task 7 (deposit), Task 8 (withdraw) — each task adds its own value; no conflicts.
- `wallet.address` added to schema + upsert in Task 2; consumed in Task 7 (DepositView) — consistent field name `address`.
