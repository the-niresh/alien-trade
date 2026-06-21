# Sponsor Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full sponsor control surface (TWAK / CMC / BNB SDK) as an operator console with Portfolio, Pipeline, and Controls views, threaded Co-Pilot streaming, rug-check gate, x402 micropayments, landing page, and visual polish.

**Architecture:** Three-transport control bus (policy/read/imperative). `SponsorControl` registry is the single source of truth for all controls — Controls UI, Docs view, and landing page all render from it. `agent_commands` Convex queue handles signed imperative actions with full audit trail.

**Tech Stack:** Python (agent), Convex (state bus), React + Vite + shadcn/ui + Tailwind (web), vitest (web tests), pytest (agent tests), bun (never npm/npx).

## Global Constraints

- Use `bun` for all web commands — never `npm` or `npx`
- Never restart systemd services or modify `.env.local`
- Scored path: only `TwakCli.swap_execute()` → `twak swap` counts for PnL; never put new logic on this path
- `assertControlToken(args.control_token)` on every state-changing Convex mutation
- Run `cd web && bun run build` after every phase — must stay green
- All TWAK CLI calls in tests MUST be mocked — never hit mainnet in tests
- Commit message format: `feat(web):`, `feat(agent):`, `feat(convex):`, etc.

---

### Task 1: Convex schema extensions + agentCommands module

**Files:**
- Modify: `convex/schema.ts`
- Create: `convex/agentCommands.ts`

**Interfaces:**
- Produces: `api.agentCommands.enqueue`, `api.agentCommands.list`, `api.agentCommands.updateStatus` — consumed by Tasks 7, 3

- [ ] **Step 1: Add `agent_commands` table + co-pilot streaming fields to schema.ts**

Open `convex/schema.ts`. After the `agent_control` table definition, add:

```typescript
  // Operator command queue — imperative TWAK-signed actions dispatched from the cockpit.
  // UI enqueues (token-gated); the agent command worker drains and executes.
  agent_commands: defineTable({
    command_type: v.string(),
    params: v.string(),           // JSON
    status: v.union(
      v.literal("queued"), v.literal("running"),
      v.literal("done"),  v.literal("failed"),
    ),
    result:        v.optional(v.string()),
    error:         v.optional(v.string()),
    audit_id:      v.optional(v.id("audit")),
    queued_by:     v.string(),
    queued_at_ms:  v.number(),
    updated_at_ms: v.number(),
  })
    .index("by_status",    ["status"])
    .index("by_queued_at", ["queued_at_ms"]),

  // Co-pilot thread index — each named conversation.
  copilot_threads: defineTable({
    title:          v.string(),
    created_ms:     v.number(),
    last_active_ms: v.number(),
  })
    .index("by_last_active", ["last_active_ms"]),
```

In the same file, extend the `copilot_messages` table definition to add three optional fields:

```typescript
  copilot_messages: defineTable({
    role: v.union(v.literal("user"), v.literal("assistant")),
    content: v.string(),
    sources_json: v.string(),
    ts_ms: v.number(),
    // Phase 3 additions — optional for backward compat with existing rows
    thread_id:       v.optional(v.id("copilot_threads")),
    partial_content: v.optional(v.string()),
    is_streaming:    v.optional(v.boolean()),
  })
    .index("by_ts", ["ts_ms"])
    .index("by_thread", ["thread_id"]),
```

- [ ] **Step 2: Create `convex/agentCommands.ts`**

```typescript
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

export const enqueue = mutation({
  args: {
    control_token: v.string(),
    command_type:  v.string(),
    params:        v.string(),   // JSON
    queued_by:     v.optional(v.string()),
  },
  returns: v.id("agent_commands"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const now = Date.now();
    return await ctx.db.insert("agent_commands", {
      command_type:  args.command_type,
      params:        args.params,
      status:        "queued",
      queued_by:     args.queued_by ?? "user",
      queued_at_ms:  now,
      updated_at_ms: now,
    });
  },
});

export const list = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("agent_commands")
      .withIndex("by_queued_at")
      .order("desc")
      .take(args.limit ?? 20);
  },
});

export const updateStatus = mutation({
  args: {
    id:            v.id("agent_commands"),
    status:        v.union(v.literal("running"), v.literal("done"), v.literal("failed")),
    result:        v.optional(v.string()),
    error:         v.optional(v.string()),
    audit_id:      v.optional(v.id("audit")),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, {
      status:        args.status,
      result:        args.result,
      error:         args.error,
      audit_id:      args.audit_id,
      updated_at_ms: Date.now(),
    });
    return null;
  },
});
```

- [ ] **Step 3: Verify Convex schema compiles**

```bash
cd /root/claude/projects/alien-trade && bunx convex dev --once 2>&1 | tail -5
```

Expected: no schema errors.

- [ ] **Step 4: Commit**

```bash
git add convex/schema.ts convex/agentCommands.ts
git commit -m "feat(convex): agent_commands queue + copilot thread/streaming schema"
```

---

### Task 2: TwakCli extensions

**Files:**
- Modify: `agent/twak_cli.py`
- Create: `agent/tests/test_twak_extensions.py`

**Interfaces:**
- Produces: `TwakCli.portfolio()`, `TwakCli.price()`, `TwakCli.risk()`, `TwakCli.trending()`, `TwakCli.search()`, `TwakCli.automate_list()`, `TwakCli.automate_add()`, `TwakCli.automate_pause()`, `TwakCli.automate_resume()`, `TwakCli.automate_delete()`, `TwakCli.alert_list()`, `TwakCli.alert_create()`, `TwakCli.alert_delete()`, `TwakCli.erc20_allowance()`, `TwakCli.erc20_approve()`, `TwakCli.erc20_revoke()`, `TwakCli.x402_quote()`, `TwakCli.x402_request()` — consumed by Task 3

- [ ] **Step 1: Write failing tests**

Create `agent/tests/test_twak_extensions.py`:

```python
"""Tests for TwakCli extensions — all TWAK calls are mocked."""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
import pytest
from agent.twak_cli import TwakCli, TwakError


@pytest.fixture()
def cli():
    c = TwakCli()
    c._bin = "/fake/twak"
    return c


def _mock_run(return_value: dict):
    return patch.object(TwakCli, "_run", return_value=return_value)


def test_portfolio_returns_dict(cli):
    with _mock_run({"chains": [{"name": "bsc", "tokens": []}], "totalUsd": 5.0}):
        result = cli.portfolio()
    assert isinstance(result, dict)
    assert "totalUsd" in result


def test_price_returns_dict(cli):
    with _mock_run({"price": 3000.0, "symbol": "ETH"}):
        result = cli.price("ETH")
    assert result["price"] == 3000.0


def test_risk_returns_dict(cli):
    with _mock_run({"isRug": False, "riskScore": 10}):
        result = cli.risk("c60")
    assert result["riskScore"] == 10


def test_trending_returns_list(cli):
    with _mock_run([{"symbol": "CAKE", "priceChange": 5.2}]):
        result = cli.trending()
    assert isinstance(result, list)


def test_automate_list_returns_list(cli):
    with _mock_run([{"id": "auto-1", "status": "active"}]):
        result = cli.automate_list()
    assert result[0]["id"] == "auto-1"


def test_automate_add_dca(cli):
    with _mock_run({"id": "auto-2", "type": "dca"}):
        result = cli.automate_add("USDT", "ETH", "10", interval="1d")
    assert result["id"] == "auto-2"


def test_automate_add_requires_interval_or_price(cli):
    with pytest.raises(ValueError, match="interval or price"):
        cli.automate_add("USDT", "ETH", "10")


def test_alert_create_requires_above_or_below(cli):
    with pytest.raises(ValueError, match="above or below"):
        cli.alert_create("ETH", "bsc")


def test_erc20_allowance_returns_dict(cli):
    with _mock_run({"allowance": "1000000"}):
        result = cli.erc20_allowance("c60_t0xabc", "0xowner", "0xspender")
    assert "allowance" in result


def test_x402_quote_returns_dict(cli):
    with _mock_run({"routes": [{"chain": "bsc", "amount": "10000"}]}):
        result = cli.x402_quote("https://example.com/api")
    assert "routes" in result
```

- [ ] **Step 2: Run tests — expect FAIL (methods don't exist yet)**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_twak_extensions.py -v 2>&1 | tail -20
```

Expected: AttributeError or ImportError on missing methods.

- [ ] **Step 3: Add the new methods to TwakCli**

In `agent/twak_cli.py`, add after the `swap_execute` method:

```python
    # ── portfolio + market data ────────────────────────────────────────────────

    def portfolio(self, chains: Optional[list[str]] = None) -> dict:
        """Full multi-chain portfolio: native + token holdings + USD values."""
        args = ["wallet", "portfolio", "--json"]
        if chains:
            args += ["--chains", ",".join(chains)]
        return self._run(*args)

    def price(self, token: str, chain: Optional[str] = None) -> dict:
        """Spot price for a token (TWAK asset ID or ticker)."""
        args = ["price", token, "--json"]
        if chain:
            args += ["--chain", chain]
        return self._run(*args)

    def risk(self, asset_id: str) -> dict:
        """Token security / rug-risk check."""
        return self._run("risk", asset_id, "--json")

    def trending(
        self,
        category: str = "bnb",
        sort: str = "price_change",
        limit: int = 10,
    ) -> list:
        data = self._run(
            "trending",
            "--category", category,
            "--sort", sort,
            "--limit", str(limit),
            "--json",
        )
        return data if isinstance(data, list) else data.get("items", [])

    def search(self, query: str, networks: Optional[list[str]] = None, limit: int = 10) -> list:
        args = ["search", query, "--limit", str(limit), "--json"]
        if networks:
            args += ["--networks", ",".join(networks)]
        data = self._run(*args)
        return data if isinstance(data, list) else data.get("results", [])

    # ── automate (DCA + limit orders) ─────────────────────────────────────────

    def automate_list(self) -> list:
        data = self._run("automate", "list", "--json")
        return data if isinstance(data, list) else data.get("automations", [])

    def automate_add(
        self,
        from_token: str,
        to_token: str,
        amount: str,
        *,
        chain: Optional[str] = None,
        interval: Optional[str] = None,
        price: Optional[float] = None,
        condition: str = "below",
        max_runs: Optional[int] = None,
    ) -> dict:
        if interval is None and price is None:
            raise ValueError("automate_add: supply interval or price (not neither)")
        if interval is not None and price is not None:
            raise ValueError("automate_add: interval and price are mutually exclusive")
        args = [
            "automate", "add",
            "--from", from_token,
            "--to", to_token,
            "--amount", amount,
            "--chain", chain or self.chain,
            "--json",
        ]
        if interval is not None:
            args += ["--interval", interval]
        if price is not None:
            args += ["--price", str(price), "--condition", condition]
        if max_runs is not None:
            args += ["--max-runs", str(max_runs)]
        return self._run(*args)

    def automate_pause(self, automation_id: str) -> dict:
        return self._run("automate", "pause", automation_id, "--json")

    def automate_resume(self, automation_id: str) -> dict:
        return self._run("automate", "resume", automation_id, "--json")

    def automate_delete(self, automation_id: str) -> dict:
        return self._run("automate", "delete", automation_id, "--json")

    # ── alerts ────────────────────────────────────────────────────────────────

    def alert_list(self) -> list:
        data = self._run("alert", "list", "--json")
        return data if isinstance(data, list) else data.get("alerts", [])

    def alert_create(
        self,
        token: str,
        chain: str,
        *,
        above: Optional[float] = None,
        below: Optional[float] = None,
    ) -> dict:
        if above is None and below is None:
            raise ValueError("alert_create: supply above or below price threshold")
        args = ["alert", "create", "--token", token, "--chain", chain, "--json"]
        if above is not None:
            args += ["--above", str(above)]
        if below is not None:
            args += ["--below", str(below)]
        return self._run(*args)

    def alert_delete(self, alert_id: str) -> dict:
        return self._run("alert", "delete", alert_id, "--json")

    # ── erc20 ─────────────────────────────────────────────────────────────────

    def erc20_allowance(self, token: str, owner: str, spender: str) -> dict:
        return self._run(
            "erc20", "allowance",
            "--token", token, "--owner", owner, "--spender", spender, "--json",
        )

    def erc20_approve(self, token: str, spender: str, amount: str) -> dict:
        return self._run(
            "erc20", "approve",
            "--token", token, "--spender", spender, "--amount", amount, "--json",
        )

    def erc20_revoke(self, token: str, spender: str) -> dict:
        return self._run(
            "erc20", "revoke",
            "--token", token, "--spender", spender, "--json",
        )

    # ── x402 ──────────────────────────────────────────────────────────────────

    def x402_quote(self, url: str, method: str = "GET") -> dict:
        return self._run("x402", "quote", url, "--method", method, "--json")

    def x402_request(
        self,
        url: str,
        max_payment: str,
        *,
        method: str = "POST",
        body: Optional[dict] = None,
        prefer_network: Optional[str] = None,
    ) -> dict:
        args = [
            "x402", "request", url,
            "--max-payment", max_payment,
            "--method", method,
            "--yes", "--json",
        ]
        if body is not None:
            import json as _json
            args += ["--body", _json.dumps(body)]
        if prefer_network:
            args += ["--prefer-network", prefer_network]
        return self._run(*args)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_twak_extensions.py -v 2>&1 | tail -20
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/twak_cli.py agent/tests/test_twak_extensions.py
git commit -m "feat(agent): extend TwakCli with portfolio/risk/automate/alert/erc20/x402 methods"
```

---

### Task 3: FastAPI read endpoints + command worker

**Files:**
- Modify: `agent/server.py`
- Create: `agent/command_worker.py`
- Create: `agent/tests/test_command_worker.py`

**Interfaces:**
- Consumes: `TwakCli.portfolio()`, `TwakCli.risk()`, `TwakCli.price()`, `TwakCli.trending()` from Task 2
- Produces: `GET /twak/portfolio`, `GET /twak/risk`, `GET /twak/price`, `GET /twak/trending`, `POST /twak/drain` — consumed by Convex actions in Tasks 5, 6

- [ ] **Step 1: Add read endpoints to `agent/server.py`**

Add after the existing `/telemetry` endpoint:

```python
# ── TWAK read endpoints (no signing) ─────────────────────────────────────────

def _get_twak() -> "TwakCli":
    from agent.twak_cli import TwakCli
    return TwakCli()


@app.get("/twak/portfolio")
def twak_portfolio() -> dict:
    """Full multi-chain portfolio from TWAK wallet portfolio command."""
    try:
        return {"ok": True, "data": _get_twak().portfolio()}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": {}}


@app.get("/twak/risk")
def twak_risk(asset_id: str) -> dict:
    """Token rug-risk check. GET /twak/risk?asset_id=c60"""
    try:
        return {"ok": True, "data": _get_twak().risk(asset_id)}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": {}}


@app.get("/twak/price")
def twak_price(token: str, chain: str = "bsc") -> dict:
    """Spot price for a token. GET /twak/price?token=ETH"""
    try:
        return {"ok": True, "data": _get_twak().price(token, chain)}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": {}}


@app.get("/twak/trending")
def twak_trending(category: str = "bnb", limit: int = 10) -> dict:
    """Trending tokens on BNB. GET /twak/trending?category=bnb"""
    try:
        return {"ok": True, "data": _get_twak().trending(category=category, limit=limit)}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}


@app.post("/twak/drain")
def twak_drain(request: Request) -> dict:
    """Pull next queued agent_command and execute it. Called by the command worker."""
    _require_api_token(request)
    from agent.command_worker import run_one_command
    try:
        result = run_one_command(get_loop().bridge)
        return {"ok": True, "ran": result}
    except Exception as e:
        return {"ok": False, "error": str(e), "ran": False}
```

- [ ] **Step 2: Create `agent/command_worker.py`**

```python
"""
Command worker — drains queued agent_commands from Convex and executes them.
Called by POST /twak/drain after each main cycle (safe: off the scored path).
Each call processes ONE command (the oldest queued one) to keep latency bounded.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.convex_bridge import ConvexBridge

log = logging.getLogger(__name__)


def run_one_command(bridge: "ConvexBridge") -> bool:
    """Fetch and execute the oldest queued command. Returns True if one ran."""
    cmd = bridge.pop_queued_command()
    if cmd is None:
        return False
    cmd_id   = cmd["_id"]
    cmd_type = cmd.get("command_type", "")
    params   = json.loads(cmd.get("params", "{}"))
    bridge.update_command_status(cmd_id, "running")
    try:
        result = _dispatch(cmd_type, params)
        bridge.update_command_status(cmd_id, "done", result=json.dumps(result))
        bridge.append_audit(
            event_type="operator_command",
            payload=json.dumps({"command_type": cmd_type, "params": params, "result": result}),
            severity="info",
        )
        return True
    except Exception as exc:
        err = str(exc)[:400]
        log.error("command_worker: %s failed: %s", cmd_type, err)
        bridge.update_command_status(cmd_id, "failed", error=err)
        bridge.append_audit(
            event_type="operator_command",
            payload=json.dumps({"command_type": cmd_type, "params": params, "error": err}),
            severity="error",
        )
        return True


def _dispatch(cmd_type: str, params: dict) -> dict:
    from agent.twak_cli import TwakCli
    twak = TwakCli()
    if cmd_type == "automate_add":
        return twak.automate_add(
            params["from_token"], params["to_token"], params["amount"],
            chain=params.get("chain"),
            interval=params.get("interval"),
            price=params.get("price"),
            condition=params.get("condition", "below"),
            max_runs=params.get("max_runs"),
        )
    if cmd_type == "automate_pause":
        return twak.automate_pause(params["id"])
    if cmd_type == "automate_resume":
        return twak.automate_resume(params["id"])
    if cmd_type == "automate_delete":
        return twak.automate_delete(params["id"])
    if cmd_type == "alert_create":
        return twak.alert_create(
            params["token"], params["chain"],
            above=params.get("above"), below=params.get("below"),
        )
    if cmd_type == "alert_delete":
        return twak.alert_delete(params["id"])
    if cmd_type == "erc20_approve":
        return twak.erc20_approve(params["token"], params["spender"], params["amount"])
    if cmd_type == "erc20_revoke":
        return twak.erc20_revoke(params["token"], params["spender"])
    if cmd_type == "x402_request":
        return twak.x402_request(
            params["url"], params["max_payment"],
            method=params.get("method", "POST"),
            body=params.get("body"),
        )
    raise ValueError(f"unknown command_type: {cmd_type!r}")
```

- [ ] **Step 3: Add `pop_queued_command` + `update_command_status` to ConvexBridge**

In `agent/convex_bridge.py`, find the class and add:

```python
    def pop_queued_command(self) -> dict | None:
        """Fetch the oldest queued agent_command. Returns None if queue is empty."""
        rows = self._query("agentCommands:list", {"limit": 1})
        if not rows:
            return None
        cmd = rows[0]
        if cmd.get("status") != "queued":
            return None
        return cmd

    def update_command_status(
        self,
        cmd_id: str,
        status: str,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        self._mutation("agentCommands:updateStatus", {
            "id": cmd_id, "status": status,
            "result": result, "error": error,
        })
```

- [ ] **Step 4: Write a test for command_worker**

Create `agent/tests/test_command_worker.py`:

```python
from unittest.mock import MagicMock, patch
from agent.command_worker import run_one_command, _dispatch


def test_run_one_command_returns_false_when_empty():
    bridge = MagicMock()
    bridge.pop_queued_command.return_value = None
    assert run_one_command(bridge) is False


def test_run_one_command_dispatches_and_marks_done():
    bridge = MagicMock()
    bridge.pop_queued_command.return_value = {
        "_id": "cmd123",
        "command_type": "automate_pause",
        "params": '{"id": "auto-1"}',
    }
    with patch("agent.command_worker._dispatch", return_value={"ok": True}) as mock_d:
        result = run_one_command(bridge)
    assert result is True
    bridge.update_command_status.assert_called_with("cmd123", "done", result='{"ok": true}')


def test_dispatch_raises_on_unknown_type():
    import pytest
    with pytest.raises(ValueError, match="unknown command_type"):
        _dispatch("mystery_command", {})
```

- [ ] **Step 5: Run agent tests**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_command_worker.py -v 2>&1 | tail -15
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/server.py agent/command_worker.py agent/convex_bridge.py agent/tests/test_command_worker.py
git commit -m "feat(agent): /twak/* read endpoints + command worker drain loop"
```

---

### Task 4: SponsorControl registry (web)

**Files:**
- Create: `web/src/lib/sponsorRegistry.ts`
- Create: `web/src/lib/sponsorRegistry.test.ts`

**Interfaces:**
- Produces: `SPONSOR_CONTROLS: SponsorControl[]`, `getControlsByTransport()`, `getControlsBySponsor()` — consumed by Tasks 6, 7, 8, 13

- [ ] **Step 1: Write failing tests**

Create `web/src/lib/sponsorRegistry.test.ts`:

```typescript
import { describe, test, expect } from "vitest";
import {
  SPONSOR_CONTROLS,
  getControlsByTransport,
  getControlsBySponsor,
  type SponsorControl,
} from "./sponsorRegistry";

test("all controls have required fields", () => {
  for (const c of SPONSOR_CONTROLS) {
    expect(c.id).toBeTruthy();
    expect(c.label).toBeTruthy();
    expect(c.description.length).toBeGreaterThan(10);
    expect(["TWAK", "CMC", "BNB_SDK", "agent"]).toContain(c.sponsor);
    expect(["policy", "read", "imperative"]).toContain(c.transport);
    expect(["scored", "neutral", "operator"]).toContain(c.scoringImpact);
  }
});

test("no duplicate ids", () => {
  const ids = SPONSOR_CONTROLS.map((c) => c.id);
  expect(new Set(ids).size).toBe(ids.length);
});

test("imperative controls have commandType", () => {
  for (const c of SPONSOR_CONTROLS.filter((c) => c.transport === "imperative")) {
    expect(c.commandType).toBeTruthy();
  }
});

test("read controls have readEndpoint", () => {
  for (const c of SPONSOR_CONTROLS.filter((c) => c.transport === "read")) {
    expect(c.readEndpoint).toBeTruthy();
  }
});

test("getControlsByTransport filters correctly", () => {
  const imperative = getControlsByTransport("imperative");
  expect(imperative.every((c) => c.transport === "imperative")).toBe(true);
});

test("getControlsBySponsor filters correctly", () => {
  const twak = getControlsBySponsor("TWAK");
  expect(twak.every((c) => c.sponsor === "TWAK")).toBe(true);
  expect(twak.length).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd /root/claude/projects/alien-trade/web && bun run test -- --reporter=verbose sponsorRegistry 2>&1 | tail -15
```

- [ ] **Step 3: Create `web/src/lib/sponsorRegistry.ts`**

```typescript
export type ScoringImpact = "scored" | "neutral" | "operator";
export type Transport    = "policy" | "read" | "imperative";
export type Sponsor      = "TWAK" | "CMC" | "BNB_SDK" | "agent";

export interface SponsorControl {
  id: string;
  label: string;
  description: string;
  sponsor: Sponsor;
  transport: Transport;
  scoringImpact: ScoringImpact;
  confirmRequired?: boolean;
  commandType?: string;
  readEndpoint?: string;
  configKey?: string;
}

export const SPONSOR_CONTROLS: SponsorControl[] = [
  // ── Autonomous (Scored) — policy transport ───────────────────────────────
  {
    id: "kill_switch",
    label: "Kill Switch",
    description: "Immediately halts all autonomous trading. The agent stops executing swaps and waits for manual resume. This is the Tier-0 emergency stop — fastest path to flat. Uses the Convex config.halted flag read every cycle.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "halted",
  },
  {
    id: "trading_mode",
    label: "Trading Mode",
    description: "Controls whether the agent trades on mainnet (real TWAK-signed swaps), paper (simulated fills, no signing), or testnet. Only mainnet mode produces scored PnL. Switching to paper halts open positions safely.",
    sponsor: "TWAK",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "trading_mode",
  },
  {
    id: "strategy",
    label: "Strategy Selector",
    description: "Chooses the active /core strategy (momentum | contrarian | balanced | defensive). Each strategy has different signal weights and regime filters. The change takes effect at the next decision cycle — no restart needed.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "strategy_name",
  },
  {
    id: "equity_floor",
    label: "Equity Floor",
    description: "USD value below which the agent auto-halts. Capital preservation guardrail. When equity drops to this level the kill switch fires automatically. Set to 0 to disable. Evaluated each cycle after position mark-to-market.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "equity_floor",
  },
  {
    id: "rug_check_gate",
    label: "Rug-Check Gate",
    description: "When enabled, the agent calls TWAK `risk <asset>` before every swap. If the token's risk score exceeds the threshold (default 75/100) or isRug=true, the swap is blocked and an audit row is written. Uses the Trust Wallet Agent Kit's on-chain contract analysis.",
    sponsor: "TWAK",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "rug_check_enabled",
  },
  {
    id: "x402_budget",
    label: "x402 Budget Cap",
    description: "Maximum USD the agent may spend per cycle on x402 micropayments to CMC data endpoints. When the cumulative spend exceeds this cap for the cycle, the agent falls back to cached data. Demonstrates both CMC x402 and TWAK EIP-3009 signing depth.",
    sponsor: "CMC",
    transport: "policy",
    scoringImpact: "neutral",
    configKey: "x402_budget_usd",
  },
  // ── Read queries (no signing) ────────────────────────────────────────────
  {
    id: "portfolio_refresh",
    label: "Portfolio Refresh",
    description: "Fetches full multi-chain portfolio from the TWAK wallet (BNB, ETH, BSC tokens, SOL, TRON). Returns native balances, token holdings, and total USD. Read-only — no signing. Cached in Convex wallet_state for the Portfolio view.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/portfolio",
  },
  {
    id: "risk_check",
    label: "Risk Check",
    description: "On-demand TWAK rug-risk scan for any token. Returns isRug, riskScore (0–100), and flags (honeypot, blacklist, sell-tax, LP-lock status). Same data the rug-check gate uses pre-swap. Reference: Trust Wallet Agent SDK risk endpoint.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/risk",
  },
  {
    id: "price_query",
    label: "Price Query",
    description: "Real-time price for any token via the TWAK pricing feed. Supports all chains TWAK tracks. The same source the agent uses for mark-to-market each cycle.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/price",
  },
  {
    id: "trending_tokens",
    label: "Trending Tokens",
    description: "Top trending tokens on BNB Chain by price change, market cap, or volume. Categories: bnb, defi, ai, memes, rwa, launchpad. Powered by TWAK trending feed backed by Trust Wallet's on-chain activity data.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/trending",
  },
  // ── Imperative (TWAK-signed, operator tools) ─────────────────────────────
  {
    id: "dca_setup",
    label: "Setup DCA",
    description: "Create a recurring USDT→token swap on a fixed interval (hourly, daily, weekly). Runs as a TWAK automate job — the wallet signs each execution locally via EIP-3009 gasless transfer. Each execution is audited in the Convex audit log with tx hash.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "automate_add",
  },
  {
    id: "limit_order",
    label: "Limit Order",
    description: "Set a TWAK limit-order automation that fires a swap when price crosses above/below a target. The agent monitors price and triggers `twak automate` when the condition is met. Self-custody: keys never leave the device.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "automate_add",
  },
  {
    id: "automate_pause",
    label: "Pause Automation",
    description: "Pause an active DCA or limit-order automation by ID. The automation is preserved in storage but stops executing. Resume it at any time without reconfiguring.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "automate_pause",
  },
  {
    id: "alert_create",
    label: "Price Alert",
    description: "Create a TWAK price alert for any token. Fires when price crosses above or below a threshold. Alerts are stored in the TWAK wallet's alert registry and checked on-chain. Results appear in the Convex audit log.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "alert_create",
  },
  {
    id: "erc20_approve",
    label: "ERC-20 Approve",
    description: "Grant a spender contract allowance to use a specific ERC-20 token from the agent wallet. Required before some DeFi interactions. TWAK signs the approval transaction locally — amount is capped to reduce over-approval risk.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "erc20_approve",
  },
  {
    id: "erc20_revoke",
    label: "ERC-20 Revoke",
    description: "Revoke an existing ERC-20 allowance. Sets approval to zero. Use after a DCA run completes or if a spender contract is no longer trusted. Signed locally via TWAK, audited in Convex.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "erc20_revoke",
  },
  {
    id: "x402_request",
    label: "x402 Pay-per-Call",
    description: "Pay for a premium CMC data endpoint using the TWAK x402 protocol (EIP-3009 gasless micropayment). The wallet signs an on-chain payment authorization — no gas required. The CMC server validates the payment proof and returns the data. Demonstrates CMC x402 + TWAK signing depth together.",
    sponsor: "CMC",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "x402_request",
  },
];

export function getControlsByTransport(transport: Transport): SponsorControl[] {
  return SPONSOR_CONTROLS.filter((c) => c.transport === transport);
}

export function getControlsBySponsor(sponsor: Sponsor): SponsorControl[] {
  return SPONSOR_CONTROLS.filter((c) => c.sponsor === sponsor);
}

export function getControlById(id: string): SponsorControl | undefined {
  return SPONSOR_CONTROLS.find((c) => c.id === id);
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd /root/claude/projects/alien-trade/web && bun run test -- --reporter=verbose sponsorRegistry 2>&1 | tail -15
```

Expected: 6 PASS.

- [ ] **Step 5: Verify web build still green**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/sponsorRegistry.ts web/src/lib/sponsorRegistry.test.ts
git commit -m "feat(web): SponsorControl registry — typed, tested, single source of truth"
```

---

### Task 5: Portfolio view + Convex action

**Files:**
- Create: `convex/twak.ts`
- Create: `web/src/views/PortfolioView.tsx`

**Interfaces:**
- Consumes: `GET /twak/portfolio` from Task 3; `wallet_state` table from schema
- Produces: `api.twak.getPortfolio` Convex action; `PortfolioView` React component — consumed by Task 8

- [ ] **Step 1: Create `convex/twak.ts` (Convex action for portfolio)**

```typescript
import { action } from "./_generated/server";
import { v } from "convex/values";

export const getPortfolio = action({
  args: {},
  returns: v.object({ ok: v.boolean(), data: v.any(), error: v.optional(v.string()) }),
  handler: async (_ctx) => {
    const agentUrl = process.env.AGENT_URL ?? "http://localhost:8000";
    try {
      const res = await fetch(`${agentUrl}/twak/portfolio`, {
        signal: AbortSignal.timeout(15_000),
      });
      const json = (await res.json()) as { ok: boolean; data: unknown; error?: string };
      return { ok: json.ok, data: json.data ?? {}, error: json.error };
    } catch (e) {
      return { ok: false, data: {}, error: String(e) };
    }
  },
});
```

- [ ] **Step 2: Create `web/src/views/PortfolioView.tsx`**

```tsx
import { useAction, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useState, useEffect } from "react";
import { usd } from "../lib/formatters";

type TokenRow = { symbol: string; balance: string; usdValue: number; chain: string };

function parseHoldings(data: unknown): TokenRow[] {
  if (!data || typeof data !== "object") return [];
  const d = data as Record<string, unknown>;
  const chains = Array.isArray(d.chains) ? d.chains : [];
  const rows: TokenRow[] = [];
  for (const chain of chains) {
    const c = chain as Record<string, unknown>;
    const tokens = Array.isArray(c.tokens) ? c.tokens : [];
    for (const t of tokens) {
      const tok = t as Record<string, unknown>;
      rows.push({
        chain: String(c.name ?? ""),
        symbol: String(tok.symbol ?? ""),
        balance: String(tok.balance ?? "0"),
        usdValue: Number(tok.usdValue ?? 0),
      });
    }
  }
  return rows.sort((a, b) => b.usdValue - a.usdValue);
}

export function PortfolioView() {
  const walletState = useQuery(api.walletState.get);
  const fetchPortfolio = useAction(api.twak.getPortfolio);
  const [portfolio, setPortfolio] = useState<{ ok: boolean; data: unknown; error?: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { setPortfolio(await fetchPortfolio({})); }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const holdings = portfolio?.ok ? parseHoldings(portfolio.data) : [];
  const totalUsd = (portfolio?.data as Record<string, unknown>)?.totalUsd;

  return (
    <div className="max-w-[720px] mx-auto space-y-4">
      <div className="mb-2 flex items-end justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
            TWAK Self-Custody
          </div>
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Portfolio</h1>
        </div>
        <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text cursor-pointer"
          onClick={refresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </Button>
      </div>

      {/* Total */}
      <Panel label="Total Value" tick="green">
        {loading && !portfolio ? <Skeleton className="h-12 w-48 bg-elevated" /> : (
          <div className="py-2">
            <div className="font-mono text-[32px] font-bold text-text tabular-nums">
              {totalUsd != null ? usd(Number(totalUsd)) : walletState ? usd(walletState.total_usd) : "—"}
            </div>
            <div className="font-mono text-[11px] text-muted-fg mt-1">
              {portfolio?.ok ? "live from TWAK wallet" : "from last known wallet_state"}
            </div>
          </div>
        )}
      </Panel>

      {/* Holdings table */}
      <Panel label="Holdings">
        {loading && !portfolio ? (
          <div className="space-y-2">
            {[1,2,3].map(i => <Skeleton key={i} className="h-8 w-full bg-elevated" />)}
          </div>
        ) : holdings.length === 0 ? (
          <p className="font-mono text-[12px] text-muted-fg py-2">
            {portfolio?.error ? `Agent offline: ${portfolio.error}` : "No holdings found."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">Chain</th>
                  <th className="text-left font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">Token</th>
                  <th className="text-right font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">Balance</th>
                  <th className="text-right font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">USD Value</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((row, i) => (
                  <tr key={i} className="border-b border-border/40 hover:bg-elevated/40 transition-colors">
                    <td className="py-2 font-mono text-muted-fg text-[11px]">{row.chain}</td>
                    <td className="py-2 font-mono text-text font-semibold">{row.symbol}</td>
                    <td className="py-2 font-mono text-muted-fg text-right tabular-nums">{row.balance}</td>
                    <td className="py-2 font-mono text-text text-right tabular-nums">{usd(row.usdValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
```

- [ ] **Step 3: Check build**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | grep -E "error|warning|✓" | tail -10
```

Expected: no TypeScript errors; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add convex/twak.ts web/src/views/PortfolioView.tsx
git commit -m "feat(web): Portfolio view — TWAK multi-chain holdings + Convex action"
```

---

### Task 6: Decision Pipeline view

**Files:**
- Create: `web/src/views/PipelineView.tsx`
- Modify: `convex/decisions.ts` (add `latest` query if not present)

**Interfaces:**
- Consumes: `api.decisions.latest`, `api.signals.latest` (or similar), `api.riskState.get`, `api.agentEvents.recent`
- Produces: `PipelineView` React component — consumed by Task 8

- [ ] **Step 1: Check what queries exist in convex/decisions.ts**

```bash
grep "^export const" /root/claude/projects/alien-trade/convex/decisions.ts | head -10
```

- [ ] **Step 2: Add `latest` queries if missing**

In `convex/decisions.ts`, add at the end if a `latest` query isn't there:

```typescript
export const latest = query({
  args: {},
  returns: v.union(v.any(), v.null()),
  handler: async (ctx) => {
    return await ctx.db
      .query("decisions")
      .withIndex("by_timestamp")
      .order("desc")
      .first();
  },
});
```

Do the same in `convex/signals.ts` if a `latest` query isn't there:

```typescript
export const latest = query({
  args: { symbol: v.optional(v.string()) },
  returns: v.union(v.any(), v.null()),
  handler: async (ctx, args) => {
    const q = args.symbol
      ? ctx.db.query("signals").withIndex("by_symbol_time", (q) => q.eq("symbol", args.symbol!))
      : ctx.db.query("signals").withIndex("by_symbol_time");
    return await q.order("desc").first();
  },
});
```

- [ ] **Step 3: Create `web/src/views/PipelineView.tsx`**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { cn } from "@/lib/utils";
import { usd } from "../lib/formatters";

type StageStatus = "pass" | "block" | "stale" | "running";

function StageBadge({ status }: { status: StageStatus }) {
  const styles: Record<StageStatus, string> = {
    pass:    "bg-green/12 text-green border-green/25",
    block:   "bg-red/12 text-red border-red/25",
    stale:   "bg-yellow/12 text-yellow border-yellow/25",
    running: "bg-cyan/12 text-cyan border-cyan/25",
  };
  return (
    <span className={cn("font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest", styles[status])}>
      {status}
    </span>
  );
}

function Stage({
  n, title, badge, rows,
}: {
  n: number;
  title: string;
  badge: StageStatus;
  rows: { label: string; value: string }[];
}) {
  return (
    <div className="flex gap-4 items-start">
      <div className="flex flex-col items-center gap-1 flex-shrink-0">
        <div className="w-7 h-7 rounded-full border border-border flex items-center justify-center font-mono text-[11px] text-muted-fg">
          {n}
        </div>
        {n < 5 && <div className="w-px flex-1 bg-border min-h-[24px]" />}
      </div>
      <div className="panel flex-1 mb-3 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="font-display text-[13px] font-bold text-text">{title}</span>
          <StageBadge status={badge} />
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {rows.map((r) => (
            <div key={r.label} className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-[11px] text-muted-fg">{r.label}</span>
              <span className="font-mono text-[12px] text-text tabular-nums">{r.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function fmt(v: number | null | undefined, decimals = 3) {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

export function PipelineView() {
  const decision   = useQuery(api.decisions.latest);
  const signal     = useQuery(api.signals.latest, {});
  const riskState  = useQuery(api.riskState.get);
  const events     = useQuery(api.agentEvents.recent, { limit: 5 });

  const ageMs = decision ? Date.now() - decision.timestamp_ms : null;
  const ageSec = ageMs != null ? (ageMs / 1000).toFixed(0) : "—";

  const regimeColor: Record<string, string> = {
    trend: "text-green", chop: "text-yellow", high_vol: "text-red", crash: "text-red",
  };

  return (
    <div className="max-w-[680px] mx-auto space-y-4">
      <div className="mb-2">
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

      <div className="space-y-0">
        <Stage n={1} title="Market Data" badge={signal ? "pass" : "stale"} rows={[
          { label: "Symbol",    value: signal?.symbol ?? "—" },
          { label: "EMA fast",  value: fmt(signal?.momentum_ema_fast) },
          { label: "EMA slow",  value: fmt(signal?.momentum_ema_slow) },
          { label: "ATR",       value: fmt(signal?.momentum_atr) },
        ]} />

        <Stage n={2} title="Signal Analysis" badge={signal?.composite_score != null ? "pass" : "stale"} rows={[
          { label: "Momentum",    value: fmt(decision?.signals?.momentum) },
          { label: "Derivatives", value: fmt(decision?.signals?.derivatives) },
          { label: "Sentiment",   value: fmt(decision?.signals?.sentiment) },
          { label: "Flow",        value: fmt(decision?.signals?.flow) },
          { label: "Composite",   value: fmt(signal?.composite_score) },
        ]} />

        <Stage n={3} title="Regime Detection"
          badge={decision?.regime ? "pass" : "stale"}
          rows={[
            { label: "Regime",  value: decision?.regime ?? "—" },
            { label: "Verdict", value: decision?.risk_verdict ?? "—" },
          ]}
        />

        <Stage n={4} title="Risk Check"
          badge={riskState?.circuit_breaker_active ? "block" : riskState ? "pass" : "stale"}
          rows={[
            { label: "Drawdown",    value: riskState ? `${(riskState.current_drawdown_pct * 100).toFixed(1)}%` : "—" },
            { label: "Daily loss",  value: riskState ? usd(riskState.daily_loss_usd) : "—" },
            { label: "Exposure",    value: riskState ? usd(riskState.open_exposure_usd) : "—" },
            { label: "Breaker",     value: riskState?.circuit_breaker_active ? "ACTIVE" : "off" },
          ]}
        />

        <Stage n={5} title="Execution"
          badge={decision?.trade_id ? "pass" : decision ? "running" : "stale"}
          rows={[
            { label: "Target size", value: decision ? usd(decision.final_size_usd) : "—" },
            { label: "Reason",      value: decision?.risk_reason ?? "—" },
          ]}
        />
      </div>

      {/* Recent agent events */}
      {events && events.length > 0 && (
        <Panel label="Recent Events">
          <div className="space-y-1.5">
            {events.slice(0, 4).map((e) => (
              <div key={e._id} className="flex items-baseline gap-3">
                <span className="font-mono text-[10px] text-muted-fg flex-shrink-0 w-20 truncate">{e.agent}</span>
                <span className="font-mono text-[12px] text-text/80">{e.headline}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Build check**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | grep -E "error|✓" | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add convex/decisions.ts convex/signals.ts web/src/views/PipelineView.tsx
git commit -m "feat(web): Decision Pipeline view — live signal/regime/risk/execution stages"
```

---

### Task 7: Controls rework (two-section + command dispatch)

**Files:**
- Modify: `web/src/views/ControlsView.tsx`
- Create: `web/src/components/CommandPanel.tsx`

**Interfaces:**
- Consumes: `SPONSOR_CONTROLS` from Task 4; `api.agentCommands.enqueue`, `api.agentCommands.list` from Task 1
- Produces: reworked `ControlsView` — consumed by Task 8

- [ ] **Step 1: Create `web/src/components/CommandPanel.tsx`**

This is the reusable card for imperative operator controls — shows the control info, a "Run" button, confirm dialog, and last command status.

```tsx
import { useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { withToken } from "../lib/control";
import type { SponsorControl } from "../lib/sponsorRegistry";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const BADGE: Record<string, string> = {
  scored:   "bg-green/12 text-green border-green/25",
  neutral:  "bg-border/40 text-muted-fg border-border",
  operator: "bg-yellow/12 text-yellow border-yellow/25",
};

const BADGE_LABEL: Record<string, string> = {
  scored: "SCORED", neutral: "READ", operator: "OPERATOR",
};

type Props = { control: SponsorControl };

export function ControlCard({ control }: Props) {
  const enqueue = useMutation(api.agentCommands.enqueue);
  const recentCmds = useQuery(api.agentCommands.list, { limit: 5 });
  const lastCmd = recentCmds?.find((c) => c.command_type === control.commandType);

  const statusColor: Record<string, string> = {
    queued: "text-cyan", running: "text-yellow", done: "text-green", failed: "text-red",
  };

  const fire = async (params: Record<string, unknown>) => {
    await enqueue(withToken({ command_type: control.commandType!, params: JSON.stringify(params) }));
  };

  return (
    <div className="panel p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-display text-[13px] font-bold text-text">{control.label}</span>
            <span className={cn("font-mono text-[9px] border rounded px-1.5 py-0.5 uppercase tracking-widest", BADGE[control.scoringImpact])}>
              {BADGE_LABEL[control.scoringImpact]}
            </span>
            <span className="font-mono text-[9px] text-muted-fg/60 border border-border/30 rounded px-1.5 py-0.5">{control.sponsor}</span>
          </div>
          <p className="font-mono text-[11px] text-muted-fg leading-relaxed line-clamp-2">{control.description}</p>
        </div>
      </div>

      {control.transport === "imperative" && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="outline" className="border-yellow/30 text-yellow bg-yellow/5 hover:bg-yellow/10 cursor-pointer w-full">
              Run
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="panel border-border">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-text font-display">{control.label}</AlertDialogTitle>
              <AlertDialogDescription className="text-muted-fg text-[13px] leading-relaxed">
                {control.description}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-yellow text-black font-bold hover:bg-yellow/80"
                onClick={() => fire({})}
              >
                Queue Command
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {lastCmd && (
        <div className="flex items-center gap-2 pt-1">
          <span className="font-mono text-[10px] text-muted-fg">Last:</span>
          <span className={cn("font-mono text-[10px]", statusColor[lastCmd.status] ?? "text-muted-fg")}>
            {lastCmd.status}
          </span>
          {lastCmd.error && (
            <span className="font-mono text-[10px] text-red/70 truncate">{lastCmd.error.slice(0, 40)}</span>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `web/src/views/ControlsView.tsx` — add two-section layout**

Keep all existing autonomous controls (kill switch, trading mode, strategy, equity floor, autopilot, risk caps) in Section 1. Add Section 2 from the registry.

At the top of the existing `ControlsView.tsx` add these imports:

```typescript
import { SPONSOR_CONTROLS } from "../lib/sponsorRegistry";
import { ControlCard } from "../components/CommandPanel";
```

Then after the existing Risk Caps panel, add:

```tsx
      {/* ── Section 2: Manual Operator Tools ── */}
      <div className="mt-6 mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-yellow rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--yellow)" }} />
          Manual Operator Tools
        </div>
        <p className="font-mono text-[11px] text-muted-fg/70">TWAK-signed. Off the scored path. Every action is audited.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        {SPONSOR_CONTROLS
          .filter((c) => c.transport === "imperative" || (c.transport === "read" && c.readEndpoint))
          .map((c) => <ControlCard key={c.id} control={c} />)}
      </div>
```

Also add a Section 1 label before the kill switch:

```tsx
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Autonomous Agent Controls
        </div>
        <p className="font-mono text-[11px] text-muted-fg/70">Scored path. Agent reads these each cycle.</p>
      </div>
```

- [ ] **Step 3: Build check**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | grep -E "error|✓" | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/ControlsView.tsx web/src/components/CommandPanel.tsx
git commit -m "feat(web): Controls two-section layout — autonomous scored vs manual operator tools"
```

---

### Task 8: App/Nav wiring

**Files:**
- Modify: `web/src/components/SideNav.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- Consumes: `PortfolioView`, `PipelineView` from Tasks 5, 6; landing/docs views added inline

- [ ] **Step 1: Update `View` type and nav items in `SideNav.tsx`**

Replace the `View` type:

```typescript
export type View = "overview" | "positions" | "agents" | "controls" | "pipeline" | "portfolio" | "logs" | "notifications" | "docs";
```

Add imports for new icons (Wallet, Activity, BookOpen are in lucide-react):

```typescript
import { LayoutDashboard, List, Users, Settings, FileText, Bot, Sun, Moon, Bell, Wallet, Activity, BookOpen } from "lucide-react";
```

Update `NAV_ITEMS`:

```typescript
const NAV_ITEMS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",      icon: LayoutDashboard, label: "Overview" },
  { view: "portfolio",     icon: Wallet,          label: "Portfolio" },
  { view: "pipeline",      icon: Activity,        label: "Pipeline" },
  { view: "positions",     icon: List,            label: "Positions" },
  { view: "agents",        icon: Users,           label: "Agents" },
  { view: "controls",      icon: Settings,        label: "Controls" },
  { view: "logs",          icon: FileText,        label: "Logs" },
  { view: "notifications", icon: Bell,            label: "Alerts" },
  { view: "docs",          icon: BookOpen,        label: "Docs" },
];
```

- [ ] **Step 2: Update `App.tsx` renderView + add imports**

Add imports:

```typescript
import { PortfolioView }    from "./views/PortfolioView";
import { PipelineView }     from "./views/PipelineView";
import { DocsView }         from "./views/DocsView";
import { LandingView }      from "./views/LandingView";
```

Update the `renderView` switch:

```typescript
  const renderView = () => {
    switch (view) {
      case "overview":      return <OverviewView  onAgentClick={onAgentClick} />;
      case "portfolio":     return <PortfolioView />;
      case "pipeline":      return <PipelineView />;
      case "positions":     return <PositionsView />;
      case "agents":        return <AgentsView    onAgentClick={onAgentClick} />;
      case "controls":      return <ControlsView />;
      case "logs":          return <LogsView />;
      case "notifications": return <NotificationsView />;
      case "docs":          return <DocsView />;
    }
  };
```

Update the no-token branch (currently renders `PairingScreen`) to show `LandingView` when hash doesn't contain `#t=`:

```typescript
  if (!token) {
    // Deep-link with #t= → skip landing, go straight to pairing
    const hasDeepLink = location.hash.startsWith("#t=");
    if (!hasDeepLink) {
      return <LandingView onConnect={() => { /* trigger pairing */ }} />;
    }
    return <PairingScreen onPaired={(t) => { setToken(t); setTokenState(t); }} />;
  }
```

Add `onConnect` prop to `LandingView` that sets a flag to show the pairing screen. For simplicity, add a local `showPairing` state:

```typescript
  const [showPairing, setShowPairing] = useState(false);
  if (!token) {
    const hasDeepLink = location.hash.startsWith("#t=");
    if (hasDeepLink || showPairing) {
      return <PairingScreen onPaired={(t) => { setToken(t); setTokenState(t); }} />;
    }
    return <LandingView onConnect={() => setShowPairing(true)} />;
  }
```

- [ ] **Step 3: Create stub views (DocsView and LandingView) so build passes**

Create `web/src/views/DocsView.tsx`:

```tsx
import { SPONSOR_CONTROLS } from "../lib/sponsorRegistry";
import { Panel } from "../components/Panel";
import { cn } from "@/lib/utils";

const SPONSOR_COLOR: Record<string, string> = {
  TWAK: "text-cyan", CMC: "text-yellow", BNB_SDK: "text-green", agent: "text-muted-fg",
};

export function DocsView() {
  const grouped = ["TWAK", "CMC", "BNB_SDK", "agent"].map((s) => ({
    sponsor: s,
    controls: SPONSOR_CONTROLS.filter((c) => c.sponsor === s),
  })).filter((g) => g.controls.length > 0);

  return (
    <div className="max-w-[720px] mx-auto space-y-6">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Sponsor Integration Depth
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Control Documentation</h1>
      </div>
      {grouped.map(({ sponsor, controls }) => (
        <Panel key={sponsor} label={<span className={cn("font-mono font-bold", SPONSOR_COLOR[sponsor])}>{sponsor}</span>}>
          <div className="space-y-4">
            {controls.map((c) => (
              <div key={c.id} className="border-b border-border/40 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-display text-[14px] font-bold text-text">{c.label}</span>
                  <span className="font-mono text-[9px] border border-border rounded px-1.5 py-0.5 text-muted-fg uppercase tracking-widest">{c.transport}</span>
                  <span className={cn("font-mono text-[9px] uppercase tracking-widest", {
                    "text-green": c.scoringImpact === "scored",
                    "text-yellow": c.scoringImpact === "operator",
                    "text-muted-fg": c.scoringImpact === "neutral",
                  })}>{c.scoringImpact}</span>
                </div>
                <p className="font-mono text-[12px] text-muted-fg leading-relaxed">{c.description}</p>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}
```

Create `web/src/views/LandingView.tsx`:

```tsx
import { SPONSOR_CONTROLS } from "../lib/sponsorRegistry";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SPONSOR_COLOR: Record<string, string> = {
  TWAK: "text-cyan border-cyan/20 bg-cyan/5",
  CMC:  "text-yellow border-yellow/20 bg-yellow/5",
  BNB_SDK: "text-green border-green/20 bg-green/5",
  agent: "text-muted-fg border-border bg-elevated",
};

export function LandingView({ onConnect }: { onConnect: () => void }) {
  const operatorControls = SPONSOR_CONTROLS.filter((c) => c.transport !== "policy");
  return (
    <div className="min-h-screen bg-[#000000] flex flex-col">
      {/* Hero */}
      <div className="flex flex-col items-center justify-center pt-24 pb-16 px-6 text-center">
        <div className="font-display text-[48px] font-bold text-green tracking-[0.12em] mb-2"
          style={{ textShadow: "0 0 40px rgba(74,222,128,0.4)" }}>
          ALIEN·TRADE
        </div>
        <p className="font-mono text-[15px] text-text/80 max-w-lg leading-relaxed mb-2">
          Autonomous BSC trading agent. Deterministic signals. Self-custody execution via Trust Wallet. Real-time operator console.
        </p>
        <p className="font-mono text-[12px] text-muted-fg max-w-md mb-8">
          Track-1: live 7-day risk-adjusted PnL · TWAK self-custody · CMC x402 · BNB AI Agent SDK
        </p>
        <Button
          className="bg-green text-[#04140c] font-bold text-[15px] px-8 py-3 h-auto hover:bg-green/80 cursor-pointer"
          onClick={onConnect}
        >
          Connect Agent →
        </Button>
      </div>

      {/* Capabilities */}
      <div className="max-w-4xl mx-auto px-6 pb-24 w-full">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-6 text-center">
          Full Sponsor Surface — {operatorControls.length} controls
        </div>
        <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          {operatorControls.map((c) => (
            <div key={c.id} className={cn("border rounded-xl p-4", SPONSOR_COLOR[c.sponsor])}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="font-display text-[13px] font-bold">{c.label}</span>
              </div>
              <p className="font-mono text-[11px] opacity-70 leading-relaxed line-clamp-3">{c.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Build check**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | grep -E "error|✓" | tail -5
```

Expected: clean build.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/SideNav.tsx web/src/App.tsx web/src/views/DocsView.tsx web/src/views/LandingView.tsx
git commit -m "feat(web): wire Portfolio/Pipeline/Docs views + landing page + nav update"
```

---

### Task 9: Co-Pilot threads + streaming backend

**Files:**
- Modify: `convex/copilot.ts`

**Interfaces:**
- Consumes: `copilot_threads` table + streaming fields added in Task 1
- Produces: `api.copilot.createThread`, `api.copilot.threadMessages`, `api.copilot.updatePartial` — consumed by Task 10

- [ ] **Step 1: Add thread + streaming mutations to `convex/copilot.ts`**

Append to the existing file:

```typescript
/** Create a new co-pilot thread. */
export const createThread = mutation({
  args: { title: v.string() },
  returns: v.id("copilot_threads"),
  handler: async (ctx, args) => {
    const now = Date.now();
    return await ctx.db.insert("copilot_threads", {
      title: args.title,
      created_ms: now,
      last_active_ms: now,
    });
  },
});

/** List all threads, most-recently-active first. */
export const threads = query({
  args: {},
  returns: v.array(v.any()),
  handler: async (ctx) => {
    return await ctx.db
      .query("copilot_threads")
      .withIndex("by_last_active")
      .order("desc")
      .take(20);
  },
});

/** Read messages for a specific thread. */
export const threadMessages = query({
  args: { thread_id: v.id("copilot_threads"), limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("copilot_messages")
      .withIndex("by_thread", (q) => q.eq("thread_id", args.thread_id))
      .order("asc")
      .take(args.limit ?? 60);
  },
});

/** Write an assistant message row to start streaming. Returns the message id. */
export const startStreamingMessage = mutation({
  args: { thread_id: v.optional(v.id("copilot_threads")) },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("copilot_messages", {
      role: "assistant",
      content: "",
      sources_json: "[]",
      ts_ms: Date.now(),
      thread_id: args.thread_id,
      partial_content: "",
      is_streaming: true,
    });
  },
});

/** Append a token chunk to a streaming assistant message. */
export const updatePartial = mutation({
  args: { id: v.id("copilot_messages"), chunk: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    const msg = await ctx.db.get(args.id);
    if (!msg) return null;
    await ctx.db.patch(args.id, {
      partial_content: (msg.partial_content ?? "") + args.chunk,
    });
    return null;
  },
});

/** Finalise a streaming message — set full content and clear streaming flag. */
export const finaliseStream = mutation({
  args: {
    id:           v.id("copilot_messages"),
    content:      v.string(),
    sources_json: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, {
      content:         args.content,
      partial_content: undefined,
      is_streaming:    false,
      sources_json:    args.sources_json ?? "[]",
    });
    return null;
  },
});
```

- [ ] **Step 2: Build check**

```bash
cd /root/claude/projects/alien-trade && bunx convex dev --once 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add convex/copilot.ts
git commit -m "feat(convex): copilot thread CRUD + streaming mutations (startStreamingMessage/updatePartial/finaliseStream)"
```

---

### Task 10: CoPilotDrawer rework (threads + streaming)

**Files:**
- Modify: `web/src/components/CoPilotDrawer.tsx`

**Interfaces:**
- Consumes: `api.copilot.threads`, `api.copilot.createThread`, `api.copilot.threadMessages`, `api.copilot.startStreamingMessage`, `api.copilot.updatePartial`, `api.copilot.finaliseStream` from Task 9

- [ ] **Step 1: Rewrite the CoPilotDrawer with thread sidebar + streaming rendering**

Replace the full file content. Key structure:
- Left sidebar (180px): thread list + "New" button
- Right main area: message history + input (same as before)
- Streaming: when a message has `is_streaming=true`, render `partial_content` instead of `content`

The new file is a significant rewrite. Replace `CoPilotDrawer.tsx` with:

```tsx
import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import type { Id } from "../../../convex/_generated/dataModel";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Plus, X } from "lucide-react";

const CHIPS = [
  "What's the current regime?",
  "What was the last trade?",
  "What's my risk state?",
  "Why is the agent flat?",
];

type MsgDoc = {
  _id: string;
  role: "user" | "assistant";
  content: string;
  partial_content?: string;
  is_streaming?: boolean;
  ts_ms: number;
};

type ThreadDoc = { _id: string; title: string };

type Props = { isOpen: boolean; onClose: () => void; prefill?: string };

function ThinkingDots() {
  return (
    <div className="flex items-center gap-[5px]">
      {[0, 0.15, 0.3].map((delay, i) => (
        <motion.span key={i} className="block w-[5px] h-[5px] rounded-full"
          style={{ background: "var(--purple)" }}
          animate={{ opacity: [0.15, 1, 0.15], scale: [0.7, 1.15, 0.7] }}
          transition={{ duration: 1.0, repeat: Infinity, delay, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

export function CoPilotDrawer({ isOpen, onClose, prefill = "" }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading]   = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const [activeThreadId, setActiveThreadId] = useState<Id<"copilot_threads"> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const threads      = useQuery(api.copilot.threads) ?? [];
  const flatMsgs     = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const threadMsgs   = useQuery(
    api.copilot.threadMessages,
    activeThreadId ? { thread_id: activeThreadId } : "skip",
  ) ?? [];
  const msgs: MsgDoc[] = (activeThreadId ? threadMsgs : flatMsgs) as MsgDoc[];

  const addMessage    = useMutation(api.copilot.addMessage);
  const createThread  = useMutation(api.copilot.createThread);
  const startStream   = useMutation(api.copilot.startStreamingMessage);
  const finaliseStream = useMutation(api.copilot.finaliseStream);
  const ask           = useAction(api.copilot.ask);

  if (prefill && prefill !== lastPrefill) {
    setQuestion(prefill);
    setLastPrefill(prefill);
  }

  const newThread = async () => {
    const id = await createThread({ title: "New conversation" });
    setActiveThreadId(id);
  };

  const send = async (q = question) => {
    const text = q.trim();
    if (!text || loading) return;
    setQuestion("");
    setLoading(true);
    try {
      await addMessage({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined });
      // Start streaming assistant message
      const streamId = await startStream({ thread_id: activeThreadId ?? undefined });
      const res = await ask({ question: text });
      await finaliseStream({ id: streamId, content: res.answer, sources_json: JSON.stringify(res.sources) });
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" showCloseButton={false}
        className="w-[560px] max-sm:w-full p-0 flex flex-col gap-0 border-l-0 shadow-none bg-transparent overflow-hidden">
        <div className="absolute inset-0 bg-[#050508]" />
        <div className="absolute -top-16 -left-16 w-56 h-56 rounded-full pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(120,40,220,0.18) 0%, transparent 70%)", filter: "blur(32px)" }} />

        <div className="relative flex h-full">
          {/* Thread sidebar */}
          <div className="w-[160px] border-r border-border/40 flex flex-col flex-shrink-0 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-border/40">
              <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Threads</span>
              <button onClick={newThread}
                className="w-5 h-5 rounded flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer">
                <Plus className="w-3 h-3" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-1">
              <button
                onClick={() => setActiveThreadId(null)}
                className={cn(
                  "w-full text-left px-3 py-2 font-mono text-[11px] truncate cursor-pointer transition-colors",
                  activeThreadId === null ? "text-purple bg-purple/10" : "text-muted-fg hover:text-text hover:bg-elevated/50",
                )}>
                Default
              </button>
              {(threads as ThreadDoc[]).map((t) => (
                <button key={t._id}
                  onClick={() => setActiveThreadId(t._id as Id<"copilot_threads">)}
                  className={cn(
                    "w-full text-left px-3 py-2 font-mono text-[11px] truncate cursor-pointer transition-colors",
                    activeThreadId === t._id ? "text-purple bg-purple/10" : "text-muted-fg hover:text-text hover:bg-elevated/50",
                  )}>
                  {t.title}
                </button>
              ))}
            </div>
          </div>

          {/* Main chat area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/40">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-purple" style={{ boxShadow: "0 0 8px var(--purple)" }} />
                <span className="font-display text-[14px] font-bold text-text">Co-Pilot</span>
              </div>
              <button onClick={onClose}
                className="w-7 h-7 rounded flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {msgs.map((m) => {
                const displayText = m.is_streaming ? (m.partial_content ?? "") : m.content;
                return (
                  <div key={m._id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                    <div className={cn(
                      "max-w-[85%] rounded-xl px-3 py-2 font-mono text-[12px] leading-relaxed",
                      m.role === "user"
                        ? "bg-purple/15 text-text border border-purple/20"
                        : "bg-elevated text-text/90 border border-border/60",
                    )}>
                      {m.is_streaming && !displayText ? <ThinkingDots /> : displayText}
                      {m.is_streaming && displayText && (
                        <span className="inline-block w-[2px] h-[12px] bg-purple ml-0.5 animate-pulse" />
                      )}
                    </div>
                  </div>
                );
              })}
              {loading && !msgs.some((m) => m.is_streaming) && (
                <div className="flex justify-start">
                  <div className="bg-elevated border border-border/60 rounded-xl px-3 py-2">
                    <ThinkingDots />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Chips + Input */}
            <div className="px-4 py-3 border-t border-border/40 space-y-2">
              {msgs.length === 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {CHIPS.map((chip) => (
                    <button key={chip} onClick={() => send(chip)}
                      className="font-mono text-[10px] text-purple/80 border border-purple/20 rounded-full px-2.5 py-1 hover:bg-purple/10 transition-colors cursor-pointer">
                      {chip}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-bg border border-border/60 rounded-lg px-3 py-2 font-mono text-[12px] text-text placeholder:text-muted-fg focus:outline-none focus:border-purple/50"
                  placeholder="Ask the agent…"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  disabled={loading}
                />
                <Button size="sm"
                  className="bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer px-3"
                  onClick={() => send()} disabled={!question.trim() || loading}>
                  →
                </Button>
              </div>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Update `convex/copilot.ts` `addMessage` to accept optional thread_id**

The `addMessage` mutation needs `thread_id` in its args:

```typescript
export const addMessage = mutation({
  args: {
    role:        v.union(v.literal("user"), v.literal("assistant")),
    content:     v.string(),
    sources_json: v.optional(v.string()),
    thread_id:   v.optional(v.id("copilot_threads")),
  },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("copilot_messages", {
      role:        args.role,
      content:     args.content,
      sources_json: args.sources_json ?? "[]",
      ts_ms:       Date.now(),
      thread_id:   args.thread_id,
    });
  },
});
```

- [ ] **Step 3: Build check**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | grep -E "error|✓" | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/CoPilotDrawer.tsx convex/copilot.ts
git commit -m "feat(web): Co-Pilot thread sidebar + Convex-native streaming via partial_content"
```

---

### Task 11: Pre-trade rug-check gate

**Files:**
- Modify: `agent/executor.py`
- Modify: `convex/config.ts` (add `rug_check_enabled` + `rug_risk_threshold` fields to schema/config)
- Create: `agent/tests/test_rug_check.py`

**Interfaces:**
- Consumes: `TwakCli.risk()` from Task 2; `config.rug_check_enabled` policy control
- Produces: rug-check logic wired into swap path — win-gate: **yes** (capital preservation + TWAK depth)

- [ ] **Step 1: Add `rug_check_enabled` to Convex config schema**

In `convex/schema.ts`, find the `config` table and add to the defineTable object:

```typescript
    rug_check_enabled:  v.optional(v.boolean()),
    rug_risk_threshold: v.optional(v.number()),   // 0–100, default 75
    x402_budget_usd:    v.optional(v.number()),   // per-cycle x402 spend cap
```

- [ ] **Step 2: Write failing tests**

Create `agent/tests/test_rug_check.py`:

```python
"""Tests for the pre-trade rug-check gate in executor.py."""
from unittest.mock import MagicMock, patch
import pytest


def _make_executor(rug_check_enabled=True, rug_risk_threshold=75):
    from agent.executor import Executor
    bridge = MagicMock()
    bridge.get_config.return_value = {
        "rug_check_enabled": rug_check_enabled,
        "rug_risk_threshold": rug_risk_threshold,
    }
    twak = MagicMock()
    ex = Executor.__new__(Executor)
    ex.bridge = bridge
    ex.twak = twak
    ex.mode = "mainnet"
    return ex, bridge, twak


def test_rug_check_blocks_risky_token():
    ex, bridge, twak = _make_executor()
    twak.risk.return_value = {"isRug": False, "riskScore": 90}
    with pytest.raises(Exception, match="rug risk"):
        ex._rug_check("c60_t0xSUSPECT")


def test_rug_check_blocks_rug_flag():
    ex, bridge, twak = _make_executor()
    twak.risk.return_value = {"isRug": True, "riskScore": 30}
    with pytest.raises(Exception, match="rug risk"):
        ex._rug_check("c60_t0xRUG")


def test_rug_check_passes_safe_token():
    ex, bridge, twak = _make_executor()
    twak.risk.return_value = {"isRug": False, "riskScore": 10}
    ex._rug_check("c60")   # should not raise


def test_rug_check_skipped_when_disabled():
    ex, bridge, twak = _make_executor(rug_check_enabled=False)
    ex._rug_check("c60_t0xANYTHING")   # should not raise, not even call twak
    twak.risk.assert_not_called()
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_rug_check.py -v 2>&1 | tail -10
```

- [ ] **Step 4: Add `_rug_check` to `agent/executor.py`**

Read the current `Executor` class to find where `swap_execute` is called. Add:

```python
    def _rug_check(self, asset_id: str) -> None:
        """Block the swap if TWAK risk endpoint flags the token as a rug.
        No-op when rug_check_enabled=False in Convex config."""
        cfg = self.bridge.get_config() or {}
        if not cfg.get("rug_check_enabled", True):
            return
        threshold = float(cfg.get("rug_risk_threshold") or 75)
        try:
            data = self.twak.risk(asset_id)
        except Exception:
            return   # risk check offline → don't block the trade
        is_rug = bool(data.get("isRug") or data.get("is_rug"))
        score = float(data.get("riskScore") or data.get("risk_score") or 0)
        if is_rug or score >= threshold:
            raise RuntimeError(
                f"rug risk blocked: asset={asset_id} isRug={is_rug} score={score:.0f}"
            )
```

Then call `self._rug_check(to_token_asset_id)` immediately before any `self.twak.swap_execute()` call in the executor.

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_rug_check.py -v 2>&1 | tail -10
```

- [ ] **Step 6: Commit**

```bash
git add agent/executor.py agent/tests/test_rug_check.py convex/schema.ts
git commit -m "feat(agent): pre-trade rug-check gate via TwakCli.risk() — capital preservation + TWAK depth"
```

---

### Task 12: x402 micropayments on CMC data calls

**Files:**
- Modify: `agent/x402_provider.py`
- Modify: `agent/server.py` (wire x402 budget cap check)
- Create: `agent/tests/test_x402_budget.py`

**Interfaces:**
- Consumes: `TwakCli.x402_request()` from Task 2; `config.x402_budget_usd` policy control
- Produces: x402-gated CMC skill endpoint — win-gate: **yes** (CMC + TWAK x402 depth)

- [ ] **Step 1: Write failing test**

Create `agent/tests/test_x402_budget.py`:

```python
from unittest.mock import MagicMock, patch


def test_x402_gated_call_uses_twak_when_enabled():
    from agent.x402_provider import x402_gated_call
    twak = MagicMock()
    twak.x402_request.return_value = {"data": {"value": 42}, "statusCode": 200}
    with patch("agent.x402_provider._get_twak", return_value=twak):
        result = x402_gated_call(
            url="https://cmc.example.com/skill",
            max_payment="10000",
            body={"symbol": "ETH"},
            enabled=True,
            budget_usd=1.0,
            spent_usd=0.0,
        )
    assert result["data"]["value"] == 42
    twak.x402_request.assert_called_once()


def test_x402_gated_call_skips_when_disabled():
    from agent.x402_provider import x402_gated_call
    twak = MagicMock()
    result = x402_gated_call(
        url="https://cmc.example.com/skill",
        max_payment="10000",
        body={},
        enabled=False,
        budget_usd=1.0,
        spent_usd=0.0,
    )
    assert result is None
    twak.x402_request.assert_not_called()


def test_x402_gated_call_skips_when_budget_exceeded():
    from agent.x402_provider import x402_gated_call
    twak = MagicMock()
    result = x402_gated_call(
        url="https://cmc.example.com/skill",
        max_payment="10000",
        body={},
        enabled=True,
        budget_usd=0.5,
        spent_usd=0.6,   # over budget
    )
    assert result is None
```

- [ ] **Step 2: Add `x402_gated_call` to `agent/x402_provider.py`**

```python
def _get_twak():
    from agent.twak_cli import TwakCli
    return TwakCli()


def x402_gated_call(
    url: str,
    max_payment: str,
    body: dict,
    enabled: bool,
    budget_usd: float,
    spent_usd: float,
) -> dict | None:
    """
    Call a CMC x402 endpoint via TWAK x402_request.
    Returns the parsed JSON response dict, or None if skipped (disabled / over budget / error).
    """
    if not enabled:
        return None
    if spent_usd >= budget_usd:
        return None
    try:
        return _get_twak().x402_request(url, max_payment, body=body)
    except Exception:
        return None
```

- [ ] **Step 3: Run tests**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/test_x402_budget.py -v 2>&1 | tail -10
```

Expected: 3 PASS.

- [ ] **Step 4: Commit**

```bash
git add agent/x402_provider.py agent/tests/test_x402_budget.py
git commit -m "feat(agent): x402_gated_call — CMC + TWAK x402 micropayment depth with budget cap"
```

---

### Task 13: Visual theme polish

**Files:**
- Modify: `web/src/globals.css`
- Modify: `web/src/components/Panel.tsx` (tighten padding/border)

**Interfaces:**
- Consumes: all views (no code changes, CSS only)
- Produces: true-black operator console aesthetic — win-gate: **yes** (Trenchers-class demo quality)

- [ ] **Step 1: Update CSS variables in `globals.css`**

Find the `:root` and `.dark` blocks. Update the key colour tokens. The existing alien-green identity stays — we only make backgrounds blacker and remove colour washing:

Replace in the dark theme block:
```css
  /* True-black operator console */
  --bg:         oklch(2% 0 0);        /* was #050508 → pure black */
  --chrome:     oklch(3.5% 0 0);      /* sidebar/header chrome */
  --elevated:   oklch(6% 0 0);        /* raised surfaces */
  --panel:      oklch(5.5% 0 0);      /* panels */
  --border:     oklch(14% 0 0);       /* borders */
  --border-hi:  oklch(20% 0 0);       /* hover borders */
```

Also add a `--panel-border` variable used in panel shadows:
```css
  --panel-border: oklch(12% 0 0);
```

- [ ] **Step 2: Tighten `Panel.tsx` to use denser spacing**

Find `panel-label` and body padding. In `Panel.tsx`, change the header padding from `px-4 pt-3.5 pb-2.5` to `px-3.5 pt-3 pb-2` and the body from `px-4 pb-4` to `px-3.5 pb-3`.

- [ ] **Step 3: Final build + test run**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -5 && bun run test -- --reporter=verbose 2>&1 | tail -15
```

Expected: clean build, all tests pass.

- [ ] **Step 4: Full agent test run**

```bash
cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/ -v 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/globals.css web/src/components/Panel.tsx
git commit -m "feat(web): true-black theme tokens + denser panel layout — Trenchers-class visual pass"
```

---

## Phase Summary

| Phase | Tasks | New Files | Key Deliverable |
|---|---|---|---|
| 1 — Control bus | 1–4 | schema, agentCommands, twak_cli ext, sponsorRegistry | Full typed control surface |
| 2 — Screens | 5–8 | PortfolioView, PipelineView, DocsView, LandingView | New screens wired in |
| 3 — Co-Pilot | 9–10 | copilot.ts additions, CoPilotDrawer rewrite | Threaded + streaming co-pilot |
| 4 — Agent wiring | 11–12 | rug_check in executor, x402_gated_call | Rug gate + x402 depth |
| 5 — Polish | 13 | globals.css update | True-black console look |

## Execution Choice

**Plan complete and saved to `docs/superpowers/plans/2026-06-18-sponsor-cockpit.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch with checkpoints

**Which approach?**
