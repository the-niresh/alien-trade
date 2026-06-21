# Convert Crypto (Deposit Section) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a **Convert** tab to the Fund Wallet (Deposit) screen — a swap widget modelled on `docs/screenshots/convert.png` (a "Converting" card → flip button → "Gaining" card → live rate → Confirm) that converts one held token into another via a real `twak swap`. Primary use: turn surplus **BNB** (gas token) into **USDT** trading capital.

**Architecture:** UI matches the reference exchange widget: amount entered in **token units**, with a live USD subtext and a `1 X = Y Z` spot-rate line. Spot prices come from the existing agent endpoint `GET /twak/price` via a new Convex action `twak.convertQuote` (same fetch-the-agent pattern as the existing `twak.getPortfolio`). On Confirm, the UI computes USD size (`amount × fromPrice`) and enqueues an `agent_command` (`command_type: "convert"`) through `agentCommands.enqueue` with the cockpit control token — exactly the path the Withdraw flow already uses. `command_worker._dispatch` runs it off the scored path: **simulate-before-send** (`twak swap --quote-only`), abort on >5% price impact, else `twak swap`. No new Convex tables, no new agent endpoints (the price endpoint and the `agent_commands`/`/twak/drain` cycle already exist).

**Tech Stack:** React 19 + Vite + shadcn/ui (`Select`, `Input`, `Button`) + Tailwind (web), Convex (action + queue + control token), Python `twak` CLI wrapper (`agent/twak_cli.py`), pytest.

## Global Constraints

- **Only `twak swap` counts toward PnL.** Convert uses `TwakCli.swap_execute()` (a real `twak swap`). Do NOT route through perps or the raw BNB-SDK signer.
- **Every state-changing Convex mutation requires the control token.** Use `withToken(...)` from `web/src/lib/control.ts` — never call `agentCommands.enqueue` without it. (Queries and the `convertQuote` action do NOT need it — they are read-only.)
- **Simulate-before-send is mandatory** (locked architectural decision L3). The convert handler MUST quote before executing and abort if price impact exceeds the cap.
- **Never drain the gas buffer.** Converting *from* BNB must leave ≥ `0.005` BNB for gas. Enforce in BOTH the UI Max and the backend. (USDT keeps a `$0.50` buffer; ETH has no reservation.)
- **Convertible token set (both sides): `BNB`, `USDT`, `ETH`.** These are the tokens with both a balance in `wallet_state` (`bnb`, `usdt`, `eth`) and a reliable spot price — so the flip button is fully symmetric and every balance shown is real. The exotic allowlist tokens (CAKE/UNI/LINK/AAVE) are deferred — the agent deploys into those automatically; see Notes.
- **Sized in USD under the hood.** `twak swap` is USD-sized (`--usd`). The UI accepts a token-unit amount and converts to USD via the live spot price (`usd = amount × fromPrice`) before enqueuing. The enqueued params are `{from_token, to_token, usd}`.
- **Price-impact cap:** `MAX_CONVERT_IMPACT = 0.05` (5%). A quote above this aborts the convert in the worker.
- **Visual style:** match the reference — two rounded cards, big `font-display` amount, token-picker pills, a circular flip button straddling the cards, a muted rate line, full-width Confirm. Accent tick/Confirm color is `cyan` (Deposit=green/cyan, Withdraw=purple; Convert=cyan). No coin-logo assets exist — use a small colored dot per token (`BNB`=yellow, `USDT`=green, `ETH`=cyan).

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `agent/command_worker.py` | Add `"convert"` case to `_dispatch`: quote → 5% impact gate → execute. | Modify (`_dispatch`, lines 51-104; add module constant) |
| `agent/tests/test_command_worker.py` | Cover convert: happy path executes, high-impact aborts, same-token rejects. | Modify (append tests) |
| `convex/twak.ts` | Add read-only `convertQuote(from, to)` action → fetches `/twak/price` for both tokens, normalizes to USD floats. | Modify (append action) |
| `web/src/views/ConvertPanel.tsx` | The swap-widget UI (form → confirm → done). | Create |
| `web/src/views/DepositView.tsx` | Add third tab `"convert"`; render `<ConvertPanel />`. | Modify (lines 10, 48-58, after 127) |

**Decomposition rationale:** Task 1 (backend dispatch) is independently testable/shippable. Task 2 (the `convertQuote` action) is the read-only price bridge the UI needs and is testable on its own. Task 3 (ConvertPanel) is extracted into its own file rather than inlined — DepositView is only 130 lines and the swap widget would bloat it; the Withdraw flow already proves the standalone-form pattern. Task 4 wires the tab (tiny). Task 5 is manual E2E.

---

### Task 1: Backend — `"convert"` command dispatch (quote → impact-gate → execute)

**Files:**
- Modify: `agent/command_worker.py:51-104` (add a new `if cmd_type == "convert"` branch before the final `raise ValueError`) and add a module constant near the top.
- Test: `agent/tests/test_command_worker.py` (append three tests)

**Interfaces:**
- Consumes (already exist in `agent/twak_cli.py`):
  - `TwakCli.swap_quote(from_token, to_token, *, usd, chain=None, slippage=1.0) -> TwakQuote` where `TwakQuote.price_impact_pct: float` (fraction, e.g. `0.012` == 1.2%) and `TwakQuote.amount_out: float`.
  - `TwakCli.swap_execute(from_token, to_token, *, usd, chain=None, slippage=1.0) -> TwakSwapResult` where `TwakSwapResult.tx_hash: str`.
- Produces: `command_type` value `"convert"`. Params JSON: `{"from_token": str, "to_token": str, "usd": number}`. Result dict: `{"tx_hash", "from_token", "to_token", "usd", "expected_out", "price_impact_pct"}`.

- [ ] **Step 1: Write the failing tests**

Append to `agent/tests/test_command_worker.py`:

```python
def _convert_params(from_token="BNB", to_token="USDT", usd=4.0):
    return {"from_token": from_token, "to_token": to_token, "usd": usd}


def test_convert_quotes_then_executes_when_impact_ok():
    with patch("agent.command_worker.TwakCli") as MockCli:
        twak = MockCli.return_value
        twak.swap_quote.return_value = MagicMock(price_impact_pct=0.012, amount_out=3.98)
        twak.swap_execute.return_value = MagicMock(tx_hash="0xdead", raw={})
        result = _dispatch("convert", _convert_params())
    twak.swap_quote.assert_called_once()
    twak.swap_execute.assert_called_once()
    assert result["tx_hash"] == "0xdead"
    assert result["from_token"] == "BNB"
    assert result["to_token"] == "USDT"
    assert result["expected_out"] == 3.98


def test_convert_aborts_when_price_impact_exceeds_cap():
    import pytest
    with patch("agent.command_worker.TwakCli") as MockCli:
        twak = MockCli.return_value
        twak.swap_quote.return_value = MagicMock(price_impact_pct=0.09, amount_out=3.5)
        with pytest.raises(ValueError, match="price impact"):
            _dispatch("convert", _convert_params())
        twak.swap_execute.assert_not_called()


def test_convert_rejects_same_from_and_to():
    import pytest
    with patch("agent.command_worker.TwakCli") as MockCli:
        with pytest.raises(ValueError, match="differ"):
            _dispatch("convert", _convert_params(from_token="USDT", to_token="USDT"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_command_worker.py -v -k convert`
Expected: 3 FAIL — happy-path raises `ValueError: unknown command_type: 'convert'`; the others fail their match.

- [ ] **Step 3: Add the `convert` branch to `_dispatch`**

In `agent/command_worker.py`, add a module-level constant after the imports, before `run_one_command`:

```python
MAX_CONVERT_IMPACT = 0.05  # abort a convert whose quoted price impact exceeds 5%
```

Then in `_dispatch`, insert this branch immediately **before** the final `raise ValueError(f"unknown command_type: {cmd_type!r}")`:

```python
        if cmd_type == "convert":
            from_token = str(params.get("from_token", "")).upper()
            to_token   = str(params.get("to_token", "")).upper()
            usd        = float(params.get("usd", 0))
            if not from_token or not to_token:
                raise ValueError("convert requires from_token and to_token")
            if from_token == to_token:
                raise ValueError(f"convert from and to must differ: {from_token}")
            if usd <= 0:
                raise ValueError(f"convert usd must be > 0, got {usd}")
            # simulate-before-send (locked architectural decision L3)
            quote = twak.swap_quote(from_token, to_token, usd=usd, chain="bsc", slippage=1.0)
            if quote.price_impact_pct > MAX_CONVERT_IMPACT:
                raise ValueError(
                    f"price impact {quote.price_impact_pct:.2%} exceeds "
                    f"{MAX_CONVERT_IMPACT:.0%} cap — aborting convert"
                )
            res = twak.swap_execute(from_token, to_token, usd=usd, chain="bsc", slippage=1.0)
            return {
                "tx_hash":          res.tx_hash,
                "from_token":       from_token,
                "to_token":         to_token,
                "usd":              usd,
                "expected_out":     quote.amount_out,
                "price_impact_pct": quote.price_impact_pct,
            }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_command_worker.py -v`
Expected: PASS (all existing + 3 new convert tests).

- [ ] **Step 5: Commit**

```bash
cd /root/claude/projects/alien-trade
git add agent/command_worker.py agent/tests/test_command_worker.py
git commit -m "feat(convert): backend convert command — quote, 5% impact gate, twak swap execute"
```

---

### Task 2: Convex — `convertQuote` read-only action (spot prices for the widget)

**Files:**
- Modify: `convex/twak.ts` (append a new `action`)

**Interfaces:**
- Consumes: existing agent endpoint `GET /twak/price?token=<SYM>&chain=bsc` returning `{ ok: boolean, data: any, error?: string }` (see `agent/server.py:397`). `AGENT_URL` env var (defaults to `http://localhost:8000`), same as the existing `getPortfolio` action.
- Produces: `api.twak.convertQuote` — args `{ from: string, to: string }`, returns `{ ok: boolean, fromPrice: number, toPrice: number, error?: string }`. Prices are USD floats; `0` means unavailable. Consumed by ConvertPanel (Task 3).

- [ ] **Step 1: Append the action to `convex/twak.ts`**

Add at the end of `convex/twak.ts` (the file already imports `action` and `v`):

```ts
export const convertQuote = action({
  args: { from: v.string(), to: v.string() },
  returns: v.object({
    ok: v.boolean(),
    fromPrice: v.number(),
    toPrice: v.number(),
    error: v.optional(v.string()),
  }),
  handler: async (_ctx, { from, to }) => {
    const agentUrl = process.env.AGENT_URL ?? "http://localhost:8000";

    const priceOf = async (token: string): Promise<number> => {
      // Stablecoins peg to $1 — avoids a needless round-trip and a 0 if the feed lags.
      if (token.toUpperCase() === "USDT" || token.toUpperCase() === "USDC") return 1;
      const res = await fetch(
        `${agentUrl}/twak/price?token=${encodeURIComponent(token)}&chain=bsc`,
        { signal: AbortSignal.timeout(12_000) },
      );
      const json = (await res.json()) as { ok: boolean; data: Record<string, unknown>; error?: string };
      if (!json.ok) throw new Error(json.error ?? `price failed for ${token}`);
      const d = json.data ?? {};
      // The twak CLI's JSON shape varies by version — pull the USD price defensively.
      const raw = d.price ?? d.priceUsd ?? d.priceUSD ?? d.usd ?? d.value ?? 0;
      const p = Number(raw);
      return Number.isFinite(p) && p > 0 ? p : 0;
    };

    try {
      const [fromPrice, toPrice] = await Promise.all([priceOf(from), priceOf(to)]);
      return { ok: true, fromPrice, toPrice };
    } catch (e) {
      return { ok: false, fromPrice: 0, toPrice: 0, error: String(e) };
    }
  },
});
```

- [ ] **Step 2: Verify Convex accepts the new function**

Run: `cd /root/claude/projects/alien-trade && bunx convex dev --once`
Expected: Convex pushes successfully and `convex/_generated/api.d.ts` now exposes `api.twak.convertQuote`. No type errors.

- [ ] **Step 3: Commit**

```bash
cd /root/claude/projects/alien-trade
git add convex/twak.ts convex/_generated/api.d.ts
git commit -m "feat(convert): convertQuote action — spot prices via /twak/price for the swap widget"
```

---

### Task 3: Frontend — `ConvertPanel` swap widget (matches `docs/screenshots/convert.png`)

**Files:**
- Create: `web/src/views/ConvertPanel.tsx`

**Interfaces:**
- Consumes: `api.walletState.get` (`{ usdt, eth, bnb, ... } | null`), `api.agentCommands.enqueue` (mutation `{ control_token, command_type, params, queued_by }`), `api.twak.convertQuote` (Task 2), `withToken` from `@/lib/control`, shadcn `Select`/`Input`/`Button`, `Panel`. Enqueues `command_type: "convert"` with params `{ from_token, to_token, usd }` (the shape Task 1 consumes; `usd = amount × fromPrice`).
- Produces: named export `ConvertPanel` imported by DepositView in Task 4.

- [ ] **Step 1: Create the component**

Create `web/src/views/ConvertPanel.tsx` with exactly this content:

```tsx
import { useEffect, useState } from "react";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { withToken } from "@/lib/control";
import { ArrowDownUp, Check, AlertTriangle } from "lucide-react";

type Token = "BNB" | "USDT" | "ETH";
type Step = "form" | "confirm" | "done";

const TOKENS: Token[] = ["BNB", "USDT", "ETH"];
const GAS_BUFFER_BNB = 0.005;
const USDT_BUFFER = 0.5;
const TOKEN_DOT: Record<Token, string> = {
  BNB: "var(--yellow)", USDT: "var(--green)", ETH: "var(--cyan)",
};

type WalletFields = { usdt: number; eth: number; bnb: number };

function balanceOf(t: Token, w: WalletFields | null): number {
  if (!w) return 0;
  return t === "USDT" ? w.usdt : t === "ETH" ? w.eth : w.bnb;
}

// Max spendable in token units, leaving the required buffer.
function maxOf(t: Token, w: WalletFields | null): number {
  const bal = balanceOf(t, w);
  if (t === "BNB") return Math.max(0, bal - GAS_BUFFER_BNB);
  if (t === "USDT") return Math.max(0, bal - USDT_BUFFER);
  return bal; // ETH: no gas reservation
}

function TokenPill({ value, onChange }: { value: Token; onChange: (t: Token) => void }) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v as Token)}>
      <SelectTrigger className="w-auto gap-2 bg-elevated border-border rounded-full px-3 py-1.5 font-mono text-[13px] font-bold text-text focus:ring-cyan">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: TOKEN_DOT[value] }} />
          <SelectValue />
        </span>
      </SelectTrigger>
      <SelectContent className="bg-elevated border-border">
        {TOKENS.map((t) => (
          <SelectItem key={t} value={t} className="font-mono text-[13px]">
            <span className="inline-flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: TOKEN_DOT[t] }} />
              {t}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function ConvertPanel() {
  const wallet  = useQuery(api.walletState.get) as WalletFields | null;
  const enqueue = useMutation(api.agentCommands.enqueue);
  const quote   = useAction(api.twak.convertQuote);

  const [from, setFrom]               = useState<Token>("BNB");
  const [to, setTo]                   = useState<Token>("USDT");
  const [amount, setAmount]           = useState("");
  const [fromPrice, setFromPrice]     = useState(0);
  const [toPrice, setToPrice]         = useState(0);
  const [rateLoading, setRateLoading] = useState(false);
  const [step, setStep]               = useState<Step>("form");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");

  // Fetch spot prices whenever the pair changes (depends on tokens, not amount).
  useEffect(() => {
    let cancelled = false;
    setRateLoading(true);
    quote({ from, to })
      .then((r) => {
        if (cancelled) return;
        setFromPrice(r.ok ? r.fromPrice : 0);
        setToPrice(r.ok ? r.toPrice : 0);
      })
      .catch(() => { if (!cancelled) { setFromPrice(0); setToPrice(0); } })
      .finally(() => { if (!cancelled) setRateLoading(false); });
    return () => { cancelled = true; };
  }, [from, to, quote]);

  const amtNum   = parseFloat(amount) || 0;
  const maxFrom  = maxOf(from, wallet);
  const usdValue = amtNum * fromPrice;
  const gaining  = toPrice > 0 ? usdValue / toPrice : 0;
  const rate     = toPrice > 0 ? fromPrice / toPrice : 0;
  const amtValid = amtNum > 0 && amtNum <= maxFrom && fromPrice > 0;

  const flip = () => { setFrom(to); setTo(from); setAmount(""); };
  const pickFrom = (t: Token) => { setAmount(""); if (t === to) setTo(from); setFrom(t); };
  const pickTo   = (t: Token) => { if (t === from) setFrom(to); setTo(t); };

  const submit = () => {
    if (!amtValid || from === to) return;
    setError("");
    setStep("confirm");
  };

  const confirm = async () => {
    setLoading(true);
    try {
      await enqueue(withToken({
        command_type: "convert",
        params: JSON.stringify({ from_token: from, to_token: to, usd: usdValue }),
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

  if (step === "done") {
    return (
      <Panel label="Conversion Queued" tick="green">
        <div className="flex flex-col items-center gap-3 py-6">
          <div className="w-12 h-12 rounded-full bg-green/15 border border-green/30 flex items-center justify-center">
            <Check className="w-6 h-6 text-green" />
          </div>
          <p className="font-mono text-[13px] text-text text-center">
            Convert queued. The agent quotes it, checks price impact, then executes via TWAK in the next command cycle.
          </p>
          <p className="font-mono text-[11px] text-muted-fg text-center">
            Check the Trackers view to see its status.
          </p>
          <Button
            variant="outline"
            className="border-border text-muted-fg mt-2 cursor-pointer"
            onClick={() => { setStep("form"); setAmount(""); }}
          >
            New conversion
          </Button>
        </div>
      </Panel>
    );
  }

  if (step === "confirm") {
    return (
      <Panel label="Confirm Conversion" tick="yellow">
        <div className="space-y-4">
          <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow/8 border border-yellow/25">
            <AlertTriangle className="w-4 h-4 text-yellow flex-shrink-0 mt-0.5" />
            <p className="font-mono text-[11px] text-text leading-relaxed">
              Converting <span className="font-bold text-yellow">{amtNum} {from}</span>
              {" "}(~${usdValue.toFixed(2)}) into <span className="font-bold text-yellow">{to}</span>
              {gaining > 0 && <> — expected ~{gaining.toFixed(6)} {to}</>}.
            </p>
          </div>
          <p className="font-mono text-[10px] text-muted-fg">
            The agent runs a live quote first and aborts if price impact exceeds 5%. On-chain swaps are irreversible.
          </p>
          {error && <p className="font-mono text-[11px] text-red">{error}</p>}
          <div className="flex gap-2">
            <Button
              onClick={confirm}
              disabled={loading}
              className="flex-1 bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowDownUp className="w-4 h-4" />
              {loading ? "Queuing…" : "Yes, convert"}
            </Button>
            <Button
              variant="outline"
              onClick={() => setStep("form")}
              disabled={loading}
              className="flex-1 border-border text-muted-fg hover:text-text cursor-pointer"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <Panel label="Convert" tick="cyan">
      <div className="space-y-1.5">
        {/* Converting (From) card */}
        <div className="bg-bg border border-border rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-muted-fg">Converting</span>
            <button
              onClick={() => setAmount(maxFrom > 0 ? String(maxFrom) : "")}
              className="font-mono text-[11px] text-muted-fg hover:text-cyan cursor-pointer"
            >
              Balance: {balanceOf(from, wallet).toFixed(4)} {from}
            </button>
          </div>
          <div className="flex items-center gap-3">
            <Input
              type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0" min="0" step="any"
              className="border-0 bg-transparent px-0 h-auto text-[28px] font-bold font-display text-text shadow-none focus-visible:ring-0"
            />
            <TokenPill value={from} onChange={pickFrom} />
          </div>
          <p className="font-mono text-[11px] text-muted-fg">
            {fromPrice > 0 ? `($${usdValue.toFixed(2)})` : "(—)"}
          </p>
        </div>

        {/* Flip button straddling the two cards */}
        <div className="relative flex justify-center" style={{ height: 0 }}>
          <button
            onClick={flip}
            aria-label="Flip tokens"
            className="absolute -top-4 z-10 h-9 w-9 rounded-full bg-elevated border border-border flex items-center justify-center text-muted-fg hover:text-cyan hover:border-cyan/40 transition-colors cursor-pointer"
          >
            <ArrowDownUp className="w-4 h-4" />
          </button>
        </div>

        {/* Gaining (To) card */}
        <div className="bg-bg border border-border rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-muted-fg">Gaining</span>
            <span className="font-mono text-[11px] text-muted-fg">
              Balance: {balanceOf(to, wallet).toFixed(4)} {to}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex-1 text-[28px] font-bold font-display text-text truncate">
              {gaining > 0 ? gaining.toFixed(6) : "0.0"}
            </span>
            <TokenPill value={to} onChange={pickTo} />
          </div>
        </div>

        {/* Rate */}
        <p className="font-mono text-[11px] text-muted-fg pt-2 px-1">
          {rateLoading ? "Fetching rate…"
            : rate > 0 ? `1 ${from} = ${rate.toFixed(6)} ${to}`
            : "Rate unavailable"}
        </p>

        {error && <p className="font-mono text-[11px] text-red px-1">{error}</p>}

        <Button
          onClick={submit}
          disabled={!amtValid || from === to}
          className="w-full mt-2 bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer disabled:opacity-50"
        >
          Confirm
        </Button>
      </div>
    </Panel>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit`
Expected: PASS. (`api.twak.convertQuote` exists from Task 2; `Panel` accepts `tick="cyan"`; all shadcn imports resolve.)

- [ ] **Step 3: Commit**

```bash
cd /root/claude/projects/alien-trade
git add web/src/views/ConvertPanel.tsx
git commit -m "feat(convert): ConvertPanel swap widget — token-unit input, live rate, flip, per convert.png"
```

---

### Task 4: Frontend — wire the `convert` tab into DepositView

**Files:**
- Modify: `web/src/views/DepositView.tsx:10` (Tab type), `:48-58` (tab selector), after `:127` (render block)

**Interfaces:**
- Consumes: `ConvertPanel` from `./ConvertPanel` (Task 3).

- [ ] **Step 1: Import ConvertPanel**

In `web/src/views/DepositView.tsx`, add after the `QRCode` import (line 8):

```tsx
import { ConvertPanel } from "./ConvertPanel";
```

- [ ] **Step 2: Extend the Tab type**

Replace line 10:

```tsx
type Tab = "deposit" | "buy";
```

with:

```tsx
type Tab = "deposit" | "buy" | "convert";
```

- [ ] **Step 3: Update the tab selector to include Convert**

Replace the tab-selector block (lines 48-58):

```tsx
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
```

with:

```tsx
      <div className="flex gap-1 p-1 bg-elevated rounded-xl border border-border">
        {(["deposit", "buy", "convert"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={cn(
              "flex-1 font-mono text-[12px] font-bold py-1.5 rounded-lg transition-colors cursor-pointer capitalize",
              tab === t ? "bg-bg text-text border border-border shadow-sm" : "text-muted-fg hover:text-text",
            )}>
            {t === "deposit" ? "Deposit" : t === "buy" ? "Buy Crypto" : "Convert"}
          </button>
        ))}
      </div>
```

- [ ] **Step 4: Render ConvertPanel for the convert tab**

Immediately after the closing `)}` of the `{tab === "buy" && ( ... )}` block (after line 127, before the final `</div>`), add:

```tsx
      {tab === "convert" && <ConvertPanel />}
```

- [ ] **Step 5: Type-check and build**

Run: `cd /root/claude/projects/alien-trade/web && bunx tsc --noEmit && bun run build`
Expected: PASS — clean type-check and a successful Vite production build.

- [ ] **Step 6: Commit**

```bash
cd /root/claude/projects/alien-trade
git add web/src/views/DepositView.tsx
git commit -m "feat(convert): add Convert tab to Fund Wallet screen"
```

---

### Task 5: End-to-end verification (manual, on this VPS)

**Files:** none (verification only).

- [ ] **Step 1: Restart cockpit and confirm the widget matches the reference**

```bash
systemctl restart alien-cockpit
```

Open `http://76.13.243.12:4173/`, pair with `CONTROL_TOKEN` from `.env.local` if needed, go to **Fund Wallet → Convert**. Confirm against `docs/screenshots/convert.png`: a "Converting" card (amount + token pill + `($X)` USD subtext + clickable Balance), a circular flip button straddling the cards, a "Gaining" card (estimated output + token pill), a `1 X = Y Z` rate line, and a full-width cyan **Confirm**.

Expected: with From=BNB, the rate line populates (e.g. `1 BNB = 0.00xxxx ETH` or `… = NNN USDT`), and the USD subtext updates as you type. If it shows "Rate unavailable", the agent's `/twak/price` is unreachable — check `systemctl status alien-trade` and `AGENT_URL` in the Convex deployment.

- [ ] **Step 2: Exercise the controls without spending**

Click the **Balance** label → amount fills to Max (BNB leaves 0.005 for gas). Click the **flip** button → From/To swap, amount clears, rate re-fetches. Pick the same token on both pills → the other side auto-swaps so they're never identical. Enter more than Max → **Confirm** disabled. Enter a valid amount → Confirm enables → click → the confirm screen shows `Converting N FROM (~$X) into TO — expected ~Y TO`.

Expected: gating matches `amtValid` (amount in (0, maxFrom], `fromPrice > 0`) and `from !== to`.

- [ ] **Step 3: (Optional, real funds) Execute one small BNB→USDT convert**

Only if a few dollars of BNB surplus is acceptable to spend. Submit a small convert (e.g. enough BNB for ~$2), then watch:

```bash
tail -f /var/log/alien-trade.log
```

Expected: an `operator_command` audit line with `command_type: "convert"` and a `tx_hash`, OR a `failed` line with `price impact … exceeds 5%` (the gate working). Wallet balances update next cycle (BNB down, USDT up).

- [ ] **Step 4: Record the outcome**

No commit. Note in the session log: widget matches the reference, controls gate correctly, and — if run — the convert tx hash or the impact-gate abort.

---

## Notes / Out of Scope (documented, not built — YAGNI)

- **CAKE/UNI/LINK/AAVE as convert tokens.** `wallet_state` tracks balances only for `usdt`/`eth`/`bnb`, so showing a real "Balance:" line and a symmetric flip for the exotic allowlist tokens would need extra balance plumbing. The agent already deploys capital into those automatically; manual convert focuses on the funding pair (BNB↔USDT) plus ETH. Adding them later = extend `TOKENS` and surface their balances.
- **Slippage/price-impact preview in the rate line.** The widget shows a *spot* rate (`fromPrice/toPrice`); the actual fill may differ by slippage. Price impact is enforced server-side by the 5% gate in Task 1 at execution. A live impact preview would require calling `swap_quote` (USD-sized) per keystroke — deferred as a nicety.
- **Convert history feed.** Convert results land in the `audit` table as `operator_command` events and surface in the Trackers view alongside withdrawals — no separate view needed.
```
