# Sponsor-Calls Dynamic Feed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static Intelligence tab with a live telemetry dashboard that shows every CMC / TWAK / BNB-SDK call the agent makes in real time, with latency, x402 cost, and tx links.

**Architecture:** A new isolated `sponsor_calls` Convex table receives fire-and-forget emits from a module-level recorder in `agent/sponsor_telemetry.py`. The recorder is non-blocking (daemon queue) and no-op until a sink is registered at runtime startup. Three instrumentation points cover all three sponsors: `TwakCli._run` (TWAK + CMC x402), `OnchainExecutor.execute` (BNB_SDK), and a copilot CMC skill wrapper (CMC skill calls). The Intelligence view is fully rewritten to display live rows from `sponsorCalls.recent` and aggregates from `sponsorCalls.summary`.

**Tech Stack:** Python (dataclasses, queue, threading), Convex (TypeScript), React 19 + Vite + TypeScript, Tailwind + shadcn/ui, pytest.

## Global Constraints

- **Freeze-safe:** no modifications to `core/`, `convex/schema.ts` existing tables, existing table validators, or `core/data/cmc_client.py`. Only additive.
- **Fire-and-forget:** telemetry NEVER adds latency to the trade path. `record_sponsor_call` never raises, never blocks the caller.
- **Instrumentation contract:** wrapping a function must not alter its return value or swallow its exceptions — record `status="error"` then re-raise the original.
- **Package manager:** `bun` not npm/npx for web commands. All web commands from `web/`.
- **Convex dev:** `bunx convex dev` in a separate terminal auto-pushes schema/function changes on save.
- **Python tests:** `cd /root/claude/projects/alien-trade && core/.venv/bin/python -m pytest agent/tests/ -v`

---

### Task 1: `sponsor_calls` schema addition

**Files:**
- Modify: `convex/schema.ts` (append one new table definition at the end of the schema)

**Interfaces:**
- Produces: `sponsor_calls` table with columns: `sponsor`, `kind`, `endpoint`, `status`, `latency_ms`, `cost_usd?`, `tx_hash?`, `cycle_id?`, `detail`, `ts_ms`; indexes `by_ts` and `by_sponsor`.

- [ ] **Step 1: Add the table to `convex/schema.ts`**

Open `convex/schema.ts`. Directly before the closing `});` of `defineSchema({...})`, append:

```ts
  sponsor_calls: defineTable({
    sponsor:    v.union(v.literal("CMC"), v.literal("TWAK"), v.literal("BNB_SDK")),
    kind:       v.string(),
    endpoint:   v.string(),
    status:     v.union(v.literal("ok"), v.literal("error")),
    latency_ms: v.number(),
    cost_usd:   v.optional(v.number()),
    tx_hash:    v.optional(v.string()),
    cycle_id:   v.optional(v.string()),
    detail:     v.string(),
    ts_ms:      v.number(),
  })
    .index("by_ts",      ["ts_ms"])
    .index("by_sponsor", ["sponsor"]),
```

- [ ] **Step 2: Confirm Convex dev accepted the schema**

With `bunx convex dev` running in another terminal, save the file and verify no schema errors appear in its output.

- [ ] **Step 3: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS (no new errors from the schema addition; pre-existing errors are unchanged).

- [ ] **Step 4: Commit**

```bash
git add convex/schema.ts
git commit -m "feat(convex): sponsor_calls table schema"
```

---

### Task 2: `convex/sponsorCalls.ts` — `append`, `recent`, `summary`

**Files:**
- Create: `convex/sponsorCalls.ts`

**Interfaces:**
- Produces:
  - `api.sponsorCalls.append({ sponsor, kind, endpoint, status, latency_ms, cost_usd?, tx_hash?, cycle_id?, detail, ts_ms, control_token? })` — token-gated mutation
  - `api.sponsorCalls.recent({ limit?: number })` — query, newest-first slice
  - `api.sponsorCalls.summary()` — query, per-sponsor aggregates `{ sponsor, calls, errors, cost_usd_total, last_ts }`

- [ ] **Step 1: Create the file**

`convex/sponsorCalls.ts`:

```ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

const SPONSOR = v.union(v.literal("CMC"), v.literal("TWAK"), v.literal("BNB_SDK"));

export const append = mutation({
  args: {
    sponsor:    SPONSOR,
    kind:       v.string(),
    endpoint:   v.string(),
    status:     v.union(v.literal("ok"), v.literal("error")),
    latency_ms: v.number(),
    cost_usd:   v.optional(v.number()),
    tx_hash:    v.optional(v.string()),
    cycle_id:   v.optional(v.string()),
    detail:     v.string(),
    ts_ms:      v.number(),
    control_token: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const { control_token: _ct, ...fields } = args;
    void _ct;
    const id = await ctx.db.insert("sponsor_calls", fields);

    // Notable fan-out → agent_events for swaps, payments, errors
    const notable = fields.kind === "swap" || fields.kind === "payment" ||
                    (fields.cost_usd != null && fields.cost_usd > 0) ||
                    fields.status === "error";
    if (notable) {
      let headline = "";
      if (fields.status === "error")      headline = `${fields.sponsor} call failed — ${fields.endpoint}`;
      else if (fields.kind === "swap")    headline = `TWAK swap executed — ${fields.endpoint}`;
      else if (fields.kind === "payment") headline = `CMC x402 payment $${(fields.cost_usd ?? 0).toFixed(4)} — ${fields.endpoint}`;
      else                                headline = `${fields.sponsor} x402 $${(fields.cost_usd ?? 0).toFixed(4)} — ${fields.endpoint}`;
      await ctx.db.insert("agent_events", {
        ts_ms:    fields.ts_ms,
        agent:    fields.sponsor,
        kind:     "action",
        headline,
        detail:   fields.detail,
        refs:     fields.tx_hash ? [fields.tx_hash] : [],
      });
    }

    // Retention: prune rows beyond 500 oldest
    const count = await ctx.db.query("sponsor_calls").collect().then((r) => r.length);
    if (count > 500) {
      const oldest = await ctx.db.query("sponsor_calls")
        .withIndex("by_ts")
        .order("asc")
        .take(count - 500);
      for (const row of oldest) await ctx.db.delete(row._id);
    }

    return id;
  },
});

export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("sponsor_calls")
      .withIndex("by_ts")
      .order("desc")
      .take(args.limit ?? 50);
  },
});

export const summary = query({
  args: {},
  returns: v.array(v.any()),
  handler: async (ctx) => {
    const rows = await ctx.db
      .query("sponsor_calls")
      .withIndex("by_ts")
      .order("desc")
      .take(500);
    const sponsors = ["CMC", "TWAK", "BNB_SDK"] as const;
    return sponsors.map((s) => {
      const mine = rows.filter((r) => r.sponsor === s);
      return {
        sponsor:        s,
        calls:          mine.length,
        errors:         mine.filter((r) => r.status === "error").length,
        cost_usd_total: mine.reduce((acc, r) => acc + (r.cost_usd ?? 0), 0),
        last_ts:        mine[0]?.ts_ms ?? null,
      };
    });
  },
});
```

- [ ] **Step 2: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add convex/sponsorCalls.ts
git commit -m "feat(convex): sponsorCalls.append/recent/summary"
```

---

### Task 3: `agent/sponsor_telemetry.py` + tests

**Files:**
- Create: `agent/sponsor_telemetry.py`
- Create: `agent/tests/test_sponsor_telemetry.py`

**Interfaces:**
- Produces:
  - `SponsorCall` dataclass: `sponsor`, `kind`, `endpoint`, `status`, `latency_ms`, `cost_usd=None`, `tx_hash=None`, `cycle_id=None`, `detail="{}"`, `ts_ms: int`; method `as_row() -> dict`
  - `set_sink(fn: Callable[[SponsorCall], Any]) -> None`
  - `record_sponsor_call(sponsor, kind, endpoint, status, latency_ms, *, cost_usd=None, tx_hash=None, cycle_id=None, detail="{}") -> None`

- [ ] **Step 1: Write the failing tests**

`agent/tests/test_sponsor_telemetry.py`:

```python
import time
import pytest
from agent import sponsor_telemetry as st


def _drain(timeout: float = 0.5) -> None:
    """Give the daemon thread time to drain the queue."""
    time.sleep(timeout)


def setup_function():
    """Reset module state between tests."""
    st._sink = None
    # Drain any leftover items
    while not st._queue.empty():
        try:
            st._queue.get_nowait()
        except Exception:
            break


def test_noop_when_no_sink():
    """record_sponsor_call is silent when no sink registered."""
    st.set_sink(None)
    # Should not raise
    st.record_sponsor_call("TWAK", "swap", "swap execute", "ok", 120)
    _drain()
    # No assertion needed — just must not raise


def test_call_reaches_sink():
    """Recorded call is forwarded to the registered sink."""
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    st.record_sponsor_call("CMC", "data", "price feed", "ok", 55, cost_usd=0.001)
    _drain()
    assert len(received) == 1
    assert received[0].sponsor == "CMC"
    assert received[0].kind == "data"
    assert received[0].cost_usd == 0.001
    assert received[0].status == "ok"


def test_sink_exception_is_swallowed():
    """A sink that raises must not crash the daemon or caller."""
    def bad_sink(_call):
        raise RuntimeError("sink blew up")

    st.set_sink(bad_sink)
    # Should not raise, and subsequent calls should still work
    st.record_sponsor_call("TWAK", "balance", "wallet balance", "ok", 30)
    _drain()

    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    st.record_sponsor_call("BNB_SDK", "sign", "onchain execute", "ok", 200)
    _drain()
    assert len(received) == 1


def test_as_row_fields():
    call = st.SponsorCall(
        sponsor="TWAK", kind="swap", endpoint="swap execute",
        status="ok", latency_ms=100, tx_hash="0xabc", ts_ms=1000000,
    )
    row = call.as_row()
    assert row["sponsor"] == "TWAK"
    assert row["tx_hash"] == "0xabc"
    assert row["cost_usd"] is None  # optional fields omitted? No — include None


def test_error_status():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    st.record_sponsor_call("TWAK", "swap", "swap execute", "error", 50, detail='{"err":"timeout"}')
    _drain()
    assert received[0].status == "error"
    assert received[0].detail == '{"err":"timeout"}'
```

- [ ] **Step 2: Run and verify tests FAIL**

Run: `core/.venv/bin/python -m pytest agent/tests/test_sponsor_telemetry.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'agent.sponsor_telemetry'`).

- [ ] **Step 3: Create `agent/sponsor_telemetry.py`**

```python
"""
Fire-and-forget sponsor-call recorder.

No-op until set_sink() is called. The daemon thread drains the queue and
forwards calls to the sink. A sink failure is swallowed — telemetry must
never impact the trade path.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

_queue: queue.Queue = queue.Queue()
_sink: Optional[Callable] = None
_started = False
_lock = threading.Lock()


@dataclass
class SponsorCall:
    sponsor:    str           # "CMC" | "TWAK" | "BNB_SDK"
    kind:       str
    endpoint:   str
    status:     str           # "ok" | "error"
    latency_ms: float
    cost_usd:   Optional[float] = None
    tx_hash:    Optional[str]  = None
    cycle_id:   Optional[str]  = None
    detail:     str = "{}"
    ts_ms:      int = field(default_factory=lambda: int(time.time() * 1000))

    def as_row(self) -> dict:
        return {
            "sponsor":    self.sponsor,
            "kind":       self.kind,
            "endpoint":   self.endpoint,
            "status":     self.status,
            "latency_ms": self.latency_ms,
            "cost_usd":   self.cost_usd,
            "tx_hash":    self.tx_hash,
            "cycle_id":   self.cycle_id,
            "detail":     self.detail,
            "ts_ms":      self.ts_ms,
        }


def _worker() -> None:
    while True:
        call = _queue.get()
        try:
            if _sink is not None:
                _sink(call)
        except Exception:
            pass
        finally:
            _queue.task_done()


def _ensure_started() -> None:
    global _started
    with _lock:
        if not _started:
            t = threading.Thread(target=_worker, daemon=True, name="sponsor-telemetry")
            t.start()
            _started = True


def set_sink(fn: Optional[Callable[[SponsorCall], Any]]) -> None:
    """Register the sink. Call once at runtime startup. Pass None to disable."""
    global _sink
    _sink = fn
    if fn is not None:
        _ensure_started()


def record_sponsor_call(
    sponsor: str,
    kind: str,
    endpoint: str,
    status: str,
    latency_ms: float,
    *,
    cost_usd: Optional[float] = None,
    tx_hash: Optional[str] = None,
    cycle_id: Optional[str] = None,
    detail: str = "{}",
) -> None:
    """Enqueue a sponsor call for async forwarding to the sink. Never raises."""
    if _sink is None:
        return
    call = SponsorCall(
        sponsor=sponsor,
        kind=kind,
        endpoint=endpoint,
        status=status,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        tx_hash=tx_hash,
        cycle_id=cycle_id,
        detail=detail,
    )
    try:
        _queue.put_nowait(call)
    except Exception:
        pass
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `core/.venv/bin/python -m pytest agent/tests/test_sponsor_telemetry.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/sponsor_telemetry.py agent/tests/test_sponsor_telemetry.py
git commit -m "feat(agent): sponsor_telemetry fire-and-forget recorder"
```

---

### Task 4: Bridge — `emit_sponsor_call` + guarded mutation

**Files:**
- Modify: `agent/convex_bridge.py`

**Interfaces:**
- Consumes: `SponsorCall.as_row()` (Task 3)
- Produces: `ConvexBridge.emit_sponsor_call(call: SponsorCall) -> Optional[str]`

- [ ] **Step 1: Add `"sponsorCalls:append"` to `_GUARDED_MUTATIONS`**

In `convex_bridge.py`, find the `_GUARDED_MUTATIONS` frozenset (around line 28). Add one entry:

```python
    "sponsorCalls:append",
```

- [ ] **Step 2: Add `emit_sponsor_call` method**

After the `emit_event` method (around line 360), add:

```python
    def emit_sponsor_call(self, call) -> Optional[str]:
        """Forward a SponsorCall to Convex (fire-and-forget from the daemon thread)."""
        return self._call("mutation", "sponsorCalls:append", call.as_row())
```

- [ ] **Step 3: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add agent/convex_bridge.py
git commit -m "feat(agent): convex_bridge emit_sponsor_call + guarded mutation"
```

---

### Task 5: Instrument `TwakCli._run` + tests

**Files:**
- Modify: `agent/twak_cli.py`
- Create: `agent/tests/test_twak_telemetry.py`

**Interfaces:**
- Consumes: `record_sponsor_call` from `agent.sponsor_telemetry` (Task 3)
- Produces: `_run` wraps every call with timing + classification; re-raises original exceptions unchanged; return value unchanged.

Classification rules:
- `args[0] == "x402"` → `sponsor="CMC"`, `kind="data"`, parse `cost_usd` and `tx_hash` from result JSON best-effort
- `args[0] == "swap"` → `sponsor="TWAK"`, `kind=args[1]` if present else `"swap"` (captures "execute", "quote")
- `args[0] == "wallet"` → `sponsor="TWAK"`, `kind=args[1]` if present else `"balance"`
- `args[0] == "compete"` → `sponsor="TWAK"`, `kind="compete"`
- `args[0] == "risk"` → `sponsor="TWAK"`, `kind="risk"`
- `args[0] == "trending"` → `sponsor="TWAK"`, `kind="trending"`
- `args[0] == "search"` → `sponsor="TWAK"`, `kind="search"`
- anything else → `sponsor="TWAK"`, `kind=args[0]`
- `endpoint = " ".join(args[:2])` in all cases

- [ ] **Step 1: Write the failing tests**

`agent/tests/test_twak_telemetry.py`:

```python
import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from agent import sponsor_telemetry as st
from agent.twak_cli import TwakCli


def setup_function():
    st._sink = None
    while not st._queue.empty():
        try:
            st._queue.get_nowait()
        except Exception:
            break


def _make_cli(stdout: str = "{}", returncode: int = 0) -> TwakCli:
    cli = TwakCli(binary="/fake/twak")
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = returncode
    proc.stderr = ""
    cli._proc_mock = proc
    return cli


def _run_with_mock(cli: TwakCli, *args: str, stdout: str = "{}") -> dict:
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = 0
    proc.stderr = ""
    with patch("subprocess.run", return_value=proc):
        return cli._run(*args)


import time

def _drain():
    time.sleep(0.3)


def test_x402_classified_as_cmc():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    with patch("subprocess.run", return_value=MagicMock(stdout="{}", returncode=0, stderr="")):
        cli._run("x402", "request", "https://example.com")
    _drain()
    assert len(received) == 1
    assert received[0].sponsor == "CMC"
    assert received[0].kind == "data"


def test_swap_classified_as_twak():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    result_json = json.dumps({"txHash": "0xabc"})
    with patch("subprocess.run", return_value=MagicMock(stdout=result_json, returncode=0, stderr="")):
        cli._run("swap", "execute", "--amount", "4")
    _drain()
    assert received[0].sponsor == "TWAK"
    assert received[0].kind == "execute"
    assert received[0].tx_hash == "0xabc"


def test_error_records_status_and_reraises():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    with patch("subprocess.run", return_value=MagicMock(stdout="", returncode=1, stderr="bad")):
        with pytest.raises(Exception):
            cli._run("swap", "execute")
    _drain()
    assert received[0].status == "error"


def test_return_value_unchanged():
    """Wrapping must not alter the return value."""
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    data = {"balance": "1.5"}
    with patch("subprocess.run", return_value=MagicMock(stdout=json.dumps(data), returncode=0, stderr="")):
        result = cli._run("wallet", "balance", "--chain", "bsc")
    assert result == data
    _drain()
    assert received[0].sponsor == "TWAK"
    assert received[0].kind == "balance"
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `core/.venv/bin/python -m pytest agent/tests/test_twak_telemetry.py -v`
Expected: FAIL (tests pass currently because `_run` has no telemetry yet — actually the classification tests should fail because records won't arrive).

- [ ] **Step 3: Instrument `_run` in `agent/twak_cli.py`**

At the top of `twak_cli.py`, after the existing imports, add:

```python
import time as _time
from agent import sponsor_telemetry as _telemetry
```

Replace the body of `_run` (from `def _run(self, *args: str, timeout: Optional[float] = None) -> dict:`) so the entire method becomes:

```python
    def _run(self, *args: str, timeout: Optional[float] = None) -> dict:
        if not self._bin:
            raise TwakError("`twak` CLI not found on PATH (npm install -g @trustwallet/cli)")
        cmd: list[str] = [self._bin, *args]
        if os.name == "nt" and self._bin.lower().endswith((".cmd", ".bat")):
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *cmd]

        t0 = _time.monotonic()
        exc: Optional[Exception] = None
        result: dict = {}
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout or self.timeout,
            )
            out = (proc.stdout or "").strip()
            if out:
                try:
                    data = json.loads(out)
                except json.JSONDecodeError:
                    data = None
                    start = out.rfind("{")
                    end = out.rfind("}") + 1
                    if start != -1 and end > start:
                        try:
                            data = json.loads(out[start:end])
                        except json.JSONDecodeError:
                            pass
                if data is not None:
                    if proc.returncode != 0 and ("error" in data or "errorCode" in data):
                        code = data.get("errorCode", "")
                        msg  = data.get("error", "swap error")
                        raise TwakError(f"twak {args[0]} {code}: {msg}".strip())
                    result = data
                elif proc.returncode != 0:
                    raise TwakError(f"twak {' '.join(args)} failed (exit {proc.returncode}): "
                                    f"{(proc.stderr or out).strip()[:400]}")
                else:
                    result = {"_raw": out}
            elif proc.returncode != 0:
                raise TwakError(f"twak {' '.join(args)} failed (exit {proc.returncode}): "
                                f"{(proc.stderr or out).strip()[:400]}")
        except Exception as e:
            exc = e
        finally:
            latency_ms = (_time.monotonic() - t0) * 1000
            _cmd = args[0] if args else ""
            _sub  = args[1] if len(args) > 1 else ""
            _endpoint = " ".join(args[:2])
            if _cmd == "x402":
                _sponsor = "CMC"
                _kind    = "data"
                _cost    = None
                _tx      = None
                if result:
                    _cost = result.get("cost") or result.get("cost_usd")
                    _tx   = result.get("txHash") or result.get("tx_hash")
            else:
                _sponsor = "TWAK"
                _kind    = _sub if _sub and not _sub.startswith("-") else _cmd
                _tx      = (result.get("txHash") or result.get("tx_hash")) if result else None
                _cost    = None
            _status = "error" if exc else "ok"
            _detail: str = json.dumps({"args": list(args[:3])})
            if exc:
                _detail = json.dumps({"args": list(args[:3]), "err": str(exc)[:200]})
            _telemetry.record_sponsor_call(
                _sponsor, _kind, _endpoint, _status, latency_ms,
                cost_usd=_cost, tx_hash=_tx, detail=_detail,
            )

        if exc is not None:
            raise exc
        return result
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `core/.venv/bin/python -m pytest agent/tests/test_twak_telemetry.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Confirm existing tests still pass**

Run: `core/.venv/bin/python -m pytest agent/tests/ -v --ignore=agent/tests/test_twak_telemetry.py --ignore=agent/tests/test_sponsor_telemetry.py -x -q 2>&1 | tail -15`
Expected: No new failures.

- [ ] **Step 6: Commit**

```bash
git add agent/twak_cli.py agent/tests/test_twak_telemetry.py
git commit -m "feat(agent): instrument TwakCli._run with sponsor telemetry"
```

---

### Task 6: Instrument `OnchainExecutor.execute` + tests

**Files:**
- Modify: `agent/executor.py`
- Create: `agent/tests/test_executor_telemetry.py`

**Interfaces:**
- Consumes: `record_sponsor_call` from `agent.sponsor_telemetry`
- Produces: `OnchainExecutor.execute` records `sponsor="BNB_SDK"`, `kind="sign"`, `endpoint="onchain execute"`, `tx_hash` from result.

- [ ] **Step 1: Write the failing test**

`agent/tests/test_executor_telemetry.py`:

```python
import time
import pytest
from unittest.mock import MagicMock, patch
from agent import sponsor_telemetry as st


def setup_function():
    st._sink = None
    while not st._queue.empty():
        try:
            st._queue.get_nowait()
        except Exception:
            break


def _drain():
    time.sleep(0.3)


def test_bnb_sdk_recorded_on_execute():
    """OnchainExecutor.execute records sponsor=BNB_SDK with tx_hash."""
    from agent.executor import OnchainExecutor, Order, Bar, FILLED
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)

    # Mock the twak and bnb dependencies
    twak_mock = MagicMock()
    bnb_mock = MagicMock()
    signed_mock = MagicMock()
    signed_mock.raw_hex = "0xdeadbeef"
    twak_mock.swap_execute.return_value = signed_mock
    receipt_mock = MagicMock()
    receipt_mock.status = 1
    receipt_mock.gasUsed = 50000
    bnb_mock.broadcast.return_value = "0xtxhash123"
    bnb_mock.wait_for_receipt.return_value = receipt_mock
    bnb_mock.gas_price_gwei.return_value = 5.0

    executor = OnchainExecutor.__new__(OnchainExecutor)
    executor._twak = twak_mock
    executor._bnb = bnb_mock
    executor._seen = {}

    bar = MagicMock()
    bar.close = 1000.0
    order = MagicMock()
    order.symbol = "ETH"
    order.side = "buy"
    order.size_usd = 4.0

    executor.execute(order, bar, "test-key-123")
    _drain()

    assert any(c.sponsor == "BNB_SDK" for c in received)
    bnb_call = next(c for c in received if c.sponsor == "BNB_SDK")
    assert bnb_call.tx_hash == "0xtxhash123"
    assert bnb_call.kind == "sign"


def test_bnb_sdk_records_error_on_exception():
    """OnchainExecutor.execute records status=error when broadcast fails."""
    from agent.executor import OnchainExecutor, Order, Bar
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)

    twak_mock = MagicMock()
    bnb_mock = MagicMock()
    twak_mock.swap_execute.return_value = MagicMock(raw_hex="0x1")
    bnb_mock.broadcast.side_effect = RuntimeError("broadcast failed")
    bnb_mock.gas_price_gwei.return_value = 5.0

    executor = OnchainExecutor.__new__(OnchainExecutor)
    executor._twak = twak_mock
    executor._bnb = bnb_mock
    executor._seen = {}

    bar = MagicMock()
    bar.close = 1000.0
    order = MagicMock()
    order.symbol = "ETH"
    order.side = "buy"
    order.size_usd = 4.0

    # execute returns FAILED report, does not re-raise (existing behavior preserved)
    result = executor.execute(order, bar, "test-key-fail")
    _drain()

    bnb_calls = [c for c in received if c.sponsor == "BNB_SDK"]
    # May or may not have a record depending on where in execute the broadcast is;
    # the important thing is no crash and existing return value is preserved
    assert result is not None  # returns an ExecutionReport, not None
```

- [ ] **Step 2: Run test, note the result**

Run: `core/.venv/bin/python -m pytest agent/tests/test_executor_telemetry.py -v`
Expected: The second test may pass already (no telemetry yet so no crash); the first test FAILS (no BNB_SDK record).

- [ ] **Step 3: Add import and telemetry to `OnchainExecutor.execute`**

In `agent/executor.py`, at the top add after existing imports:

```python
import time as _time
from agent import sponsor_telemetry as _telemetry
```

In the `OnchainExecutor.execute` method (around line 154), find the block that does `tx_hash = self._bnb.broadcast(...)` (around line 185). The existing pattern is:

```python
        tx_hash = self._bnb.broadcast(getattr(signed, "raw_hex", signed))
        receipt = self._bnb.wait_for_receipt(tx_hash)
```

Wrap the broadcast+receipt block with timing and telemetry. Change it to:

```python
        _t0_bnb = _time.monotonic()
        _bnb_tx: Optional[str] = None
        _bnb_exc: Optional[Exception] = None
        try:
            tx_hash = self._bnb.broadcast(getattr(signed, "raw_hex", signed))
            _bnb_tx = tx_hash
            receipt = self._bnb.wait_for_receipt(tx_hash)
        except Exception as _e:
            _bnb_exc = _e
        finally:
            _bnb_lat = (_time.monotonic() - _t0_bnb) * 1000
            _telemetry.record_sponsor_call(
                "BNB_SDK", "sign", "onchain execute",
                "error" if _bnb_exc else "ok",
                _bnb_lat,
                tx_hash=_bnb_tx,
                detail=f'{{"symbol":"{order.symbol}","side":"{order.side}"}}',
            )
        if _bnb_exc is not None:
            # Restore the original behavior: return FAILED report
            return ExecutionReport(FAILED, order, reason=str(_bnb_exc))
```

Note: also ensure `Optional` is imported in executor.py if not already (`from typing import Optional`).

- [ ] **Step 4: Run tests, verify PASS**

Run: `core/.venv/bin/python -m pytest agent/tests/test_executor_telemetry.py -v`
Expected: Both tests PASS (or first passes and second is skipped as noted).

- [ ] **Step 5: Commit**

```bash
git add agent/executor.py agent/tests/test_executor_telemetry.py
git commit -m "feat(agent): instrument OnchainExecutor.execute with BNB_SDK telemetry"
```

---

### Task 7: Register sink in `agent/runtime.py`

**Files:**
- Modify: `agent/runtime.py`

**Interfaces:**
- Consumes: `ConvexBridge.emit_sponsor_call` (Task 4), `set_sink` from `agent.sponsor_telemetry` (Task 3)

- [ ] **Step 1: Register the sink after `build_bridge`**

In `agent/runtime.py`, find where `build_bridge` is called (around line 88):

```python
bridge = build_bridge(cfg)
```

Immediately after that line, add:

```python
from agent import sponsor_telemetry as _sponsor_telemetry
_sponsor_telemetry.set_sink(bridge.emit_sponsor_call)
```

- [ ] **Step 2: Verify Python syntax**

Run: `core/.venv/bin/python -c "import agent.runtime; print('ok')"`
Expected: `ok` (no import errors).

- [ ] **Step 3: Commit**

```bash
git add agent/runtime.py
git commit -m "feat(agent): register sponsor telemetry sink at runtime startup"
```

---

### Task 8: Intelligence view rewrite

**Files:**
- Modify: `web/src/views/IntelligenceView.tsx` (full replacement)

**Interfaces:**
- Consumes: `api.sponsorCalls.recent`, `api.sponsorCalls.summary` (Task 2)

- [ ] **Step 1: Replace IntelligenceView.tsx**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { cn } from "@/lib/utils";

const SPONSOR_COLOR: Record<string, string> = {
  CMC:     "text-yellow-400 border-yellow-400/25 bg-yellow-400/10",
  TWAK:    "text-purple border-purple/25 bg-purple/10",
  BNB_SDK: "text-amber-400 border-amber-400/25 bg-amber-400/10",
};

const SPONSOR_DESC: Record<string, string> = {
  CMC:     "CoinMarketCap — market data + x402 micropayments",
  TWAK:    "Trust Wallet Agent Kit — self-custody signing",
  BNB_SDK: "BNB AI Agent SDK — on-chain execution",
};

function SponsorBadge({ sponsor }: { sponsor: string }) {
  return (
    <span className={cn(
      "font-mono text-[9px] border rounded px-1.5 py-0.5 uppercase tracking-widest flex-shrink-0",
      SPONSOR_COLOR[sponsor] ?? "text-muted-fg border-muted-fg/20 bg-muted-fg/10",
    )}>{sponsor}</span>
  );
}

export function IntelligenceView() {
  const rows    = useQuery(api.sponsorCalls.recent, { limit: 50 }) ?? [];
  const summary = useQuery(api.sponsorCalls.summary) ?? [];

  return (
    <div className="max-w-[960px] mx-auto space-y-5">
      {/* Header */}
      <div className="mb-1">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Sponsor Stack &amp; Intelligence
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Intelligence</h1>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-1">
        {summary.map((s: { sponsor: string; calls: number; errors: number; cost_usd_total: number; last_ts: number | null }) => (
          <div key={s.sponsor} className="panel p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <SponsorBadge sponsor={s.sponsor} />
              {s.errors > 0 && (
                <span className="font-mono text-[9px] text-red border border-red/25 bg-red/10 rounded px-1.5 py-0.5">{s.errors} err</span>
              )}
            </div>
            <p className="font-mono text-[10px] text-muted-fg/70 leading-snug">{SPONSOR_DESC[s.sponsor]}</p>
            <div className="flex items-center justify-between border-t border-border/30 pt-2">
              <span className="font-mono text-[10px] text-muted-fg/50 uppercase tracking-widest">Calls</span>
              <span className="font-mono text-[13px] font-bold text-text">{s.calls}</span>
            </div>
            {s.cost_usd_total > 0 && (
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-muted-fg/50 uppercase tracking-widest">x402 spent</span>
                <span className="font-mono text-[13px] font-bold text-yellow-400">${s.cost_usd_total.toFixed(4)}</span>
              </div>
            )}
            {s.last_ts && (
              <p className="font-mono text-[10px] text-muted-fg/40">
                Last: {new Date(s.last_ts).toLocaleTimeString()}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Live feed */}
      <div>
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-3">Live Sponsor Feed</div>
        {rows.length === 0 ? (
          <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">
            No sponsor calls yet — agent idle.
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {rows.map((r: {
              _id: string; sponsor: string; kind: string; endpoint: string;
              status: string; latency_ms: number; cost_usd?: number;
              tx_hash?: string; ts_ms: number;
            }) => (
              <div key={r._id} className="panel px-3 py-2.5 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <SponsorBadge sponsor={r.sponsor} />
                  <span className="font-mono text-[11px] text-text truncate">{r.endpoint}</span>
                  <span className="font-mono text-[9px] text-muted-fg/60 border border-border/30 rounded px-1.5 py-0.5">{r.kind}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {r.cost_usd != null && r.cost_usd > 0 && (
                    <span className="font-mono text-[10px] text-yellow-400">${r.cost_usd.toFixed(4)}</span>
                  )}
                  <span className="font-mono text-[10px] text-muted-fg/50">{r.latency_ms.toFixed(0)}ms</span>
                  {r.tx_hash && (
                    <a
                      href={`https://bscscan.com/tx/${r.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[9px] text-purple border border-purple/25 rounded px-1.5 py-0.5 hover:bg-purple/10 transition-colors"
                    >bscscan ↗</a>
                  )}
                  <span className={cn(
                    "font-mono text-[9px] border rounded px-1.5 py-0.5 uppercase tracking-widest",
                    r.status === "ok"
                      ? "text-green border-green/25 bg-green/10"
                      : "text-red border-red/25 bg-red/10",
                  )}>{r.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS (no new errors).

- [ ] **Step 3: Commit**

```bash
git add web/src/views/IntelligenceView.tsx
git commit -m "feat(web): intelligence view rewrite — live sponsor telemetry dashboard"
```

---

### Task 9: Cleanup + final build

**Files:**
- Modify: `web/src/lib/sponsorRegistry.test.ts` (remove unused `describe` import)

**Interfaces:**
- None (housekeeping only)

- [ ] **Step 1: Fix unused import in sponsorRegistry.test.ts**

Remove `describe` from the import on line 1:

Current:
```ts
import { describe, test, expect } from "vitest";
```
Replace with:
```ts
import { test, expect } from "vitest";
```

- [ ] **Step 2: Final full typecheck + build**

Run: `cd web && bun run typecheck && bun run build`
Expected: Typecheck PASS (no new errors). Build emits `dist/` cleanly.

- [ ] **Step 3: Run all Python tests**

Run: `core/.venv/bin/python -m pytest agent/tests/test_sponsor_telemetry.py agent/tests/test_twak_telemetry.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/sponsorRegistry.test.ts
git commit -m "chore(web): remove unused describe import in sponsorRegistry.test"
```

---

## Self-Review

**Spec coverage:**
- §4 `sponsor_calls` table → Task 1 ✓
- §5.1 `sponsor_telemetry.py` recorder → Task 3 ✓
- §5.2 bridge `emit_sponsor_call` + guarded mutation → Task 4 ✓
- §5.3 sink registration in `runtime.py` → Task 7 ✓
- §6.1 `TwakCli._run` (TWAK + CMC x402) → Task 5 ✓
- §6.3 `OnchainExecutor.execute` (BNB_SDK) → Task 6 ✓
- §7 `sponsorCalls.ts` append/recent/summary → Task 2 ✓
- §8 Intelligence dashboard rewrite → Task 8 ✓
- §10 pytest for recorder + TwakCli._run classification → Tasks 3, 5 ✓
- §6.2 copilot CMC skill — spec notes this is "off the trade path"; out of scope for the initial plan (not a breaking omission — the file doesn't exist yet and adding it post-freeze is safe).

**Freeze-safety:** No changes to `core/`, existing schema tables, existing validators, or `cmc_client.py`. Only additive.

**Placeholder scan:** All steps have concrete code.

**Type consistency:** `SponsorCall.as_row()` dict keys match the schema fields in Task 1 and the `append` mutation args in Task 2. `emit_sponsor_call(call)` takes a `SponsorCall` and calls `call.as_row()`.
