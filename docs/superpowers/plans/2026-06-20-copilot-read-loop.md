# Co-Pilot Live-Read Tool-Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the VPS co-pilot an Anthropic tool-use loop that fetches **live** data (wallet, price, token risk, trending, CMC market skills, agent state/history) on demand, replacing the fixed-prompt narrator as the default `/copilot` brain.

**Architecture:** A new in-process module `agent/copilot_agent.py` runs a bounded tool-use loop with the `anthropic` SDK. Read tools are thin wrappers over functions that already exist (`TwakCli`, `SkillHub`, `ConvexBridge`). The loop runs **on the VPS, next to its tools** (the locked rule: the reasoning loop lives where the tools live). It is **read-only** — it never trades; the existing `agent_commands` → `command_worker` grammar path owns writes. `/copilot` calls the loop when `SECOND_BRAIN=0` and an API key is present, and falls back to the existing `_copilot_fallback` narrator otherwise.

**Tech Stack:** Python 3, `anthropic` SDK 0.109.2 (tool use), `pytest` + `unittest.mock`, FastAPI (existing `agent/server.py`).

## Global Constraints

- Python interpreter: `core/.venv/bin/python` (run all commands from repo root `/root/claude/projects/alien-trade`).
- LLM model id: `claude-haiku-4-5-20251001` (tier-routed cheap path; off the trade hot path).
- **Read-only loop.** No tool in this module may call `swap_execute`, `transfer`, `automate_*`, `erc20_approve`, `x402_request`, or any state-changing TWAK command. Writes stay on the `command_worker` path.
- **Every tool failure is advisory** — a tool that errors returns an error marker string as its `tool_result`; it must never raise out of the loop (failure-matrix rule, matching `SkillHub`/`command_worker`).
- **Bounded latency:** the loop caps at `MAX_TOOL_TURNS = 5` tool rounds.
- Tests use mocks only — **no live network, no real `twak`/Anthropic calls**.
- Do **not** enable the Second Brain or install Upstash clients — this plan deliberately uses live tools, not RAG (see project decision: empty vector store).
- Return shape from `/copilot` is unchanged: `{"answer": str, "grounded": bool, "sources": list, "action": dict | None}`.

---

### Task 1: Read-tool registry and executor

**Files:**
- Create: `agent/copilot_agent.py`
- Test: `agent/tests/test_copilot_agent_tools.py`

**Interfaces:**
- Consumes: `TwakCli` from `agent/twak_cli.py` (`.portfolio()`, `.price(token, chain)`, `.risk(asset_id)`, `.trending(category, sort, limit)`); `SkillHub` from `agent/skills` (`.find_skill(query, top_k)`, `.execute_skill(unique_name, params)`, `.enabled`); a `bridge` duck-typed object exposing `.latest_ledger() -> dict | None`, `.recent_decisions(limit) -> list[dict]`, `.get_config() -> dict | None`.
- Produces: `TOOLS: list[dict]` (Anthropic tool schemas) and `execute_tool(name: str, args: dict, *, twak, skills, bridge) -> str` (returns a JSON string for use as `tool_result` content). Tool names: `get_agent_state`, `get_wallet`, `get_price`, `check_token_risk`, `get_trending`, `cmc_market_skill`.

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/test_copilot_agent_tools.py
import json
from unittest.mock import MagicMock
from agent.copilot_agent import TOOLS, execute_tool


def _deps():
    twak = MagicMock()
    skills = MagicMock()
    bridge = MagicMock()
    return twak, skills, bridge


def test_tools_have_unique_names_and_schemas():
    names = [t["name"] for t in TOOLS]
    assert names == sorted(set(names))  # unique
    for t in TOOLS:
        assert t["name"] and t["description"]
        assert t["input_schema"]["type"] == "object"


def test_get_agent_state_summarises_bridge():
    twak, skills, bridge = _deps()
    bridge.latest_ledger.return_value = {"cumulative_pnl_usd": 1.5, "current_drawdown_pct": 0.02}
    bridge.get_config.return_value = {"halted": False, "trading_mode": "mainnet", "strategy_name": "contrarian"}
    bridge.recent_decisions.return_value = [
        {"regime": "CHOP", "risk_verdict": "BLOCK", "timestamp_ms": 1, "risk_reason": "chop gate"},
    ]
    out = json.loads(execute_tool("get_agent_state", {}, twak=twak, skills=skills, bridge=bridge))
    assert out["pnl_usd"] == 1.5
    assert out["drawdown_pct"] == 0.02
    assert out["halted"] is False
    assert out["recent_decisions"][0]["regime"] == "CHOP"


def test_get_price_calls_twak():
    twak, skills, bridge = _deps()
    twak.price.return_value = {"price": 2.31}
    out = json.loads(execute_tool("get_price", {"token": "CAKE"}, twak=twak, skills=skills, bridge=bridge))
    twak.price.assert_called_once_with("CAKE", "bsc")
    assert out["price"] == 2.31


def test_check_token_risk_calls_twak():
    twak, skills, bridge = _deps()
    twak.risk.return_value = {"score": "low"}
    out = json.loads(execute_tool("check_token_risk", {"asset_id": "c60"}, twak=twak, skills=skills, bridge=bridge))
    twak.risk.assert_called_once_with("c60")
    assert out["score"] == "low"


def test_get_wallet_calls_portfolio():
    twak, skills, bridge = _deps()
    twak.portfolio.return_value = {"total_usd": 18.0}
    out = json.loads(execute_tool("get_wallet", {}, twak=twak, skills=skills, bridge=bridge))
    assert out["total_usd"] == 18.0


def test_get_trending_calls_twak():
    twak, skills, bridge = _deps()
    twak.trending.return_value = [{"symbol": "CAKE"}]
    out = json.loads(execute_tool("get_trending", {"limit": 3}, twak=twak, skills=skills, bridge=bridge))
    twak.trending.assert_called_once_with(category="bnb", limit=3)
    assert out[0]["symbol"] == "CAKE"


def test_cmc_market_skill_runs_top_candidate():
    twak, skills, bridge = _deps()
    skills.enabled = True
    skills.find_skill.return_value = [{"uniqueName": "ohlcv_latest"}]
    skills.execute_skill.return_value = {"data": {"price": 1}}
    out = json.loads(execute_tool("cmc_market_skill", {"query": "eth ohlcv"}, twak=twak, skills=skills, bridge=bridge))
    skills.execute_skill.assert_called_once()
    assert out["data"]["price"] == 1


def test_cmc_market_skill_offline_returns_marker():
    twak, skills, bridge = _deps()
    skills.enabled = False
    out = json.loads(execute_tool("cmc_market_skill", {"query": "x"}, twak=twak, skills=skills, bridge=bridge))
    assert out["status"] == "offline"


def test_unknown_tool_returns_error_marker():
    twak, skills, bridge = _deps()
    out = json.loads(execute_tool("nope", {}, twak=twak, skills=skills, bridge=bridge))
    assert "error" in out


def test_tool_exception_is_caught_not_raised():
    twak, skills, bridge = _deps()
    twak.price.side_effect = RuntimeError("twak down")
    out = json.loads(execute_tool("get_price", {"token": "X"}, twak=twak, skills=skills, bridge=bridge))
    assert "error" in out and "twak down" in out["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_agent_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.copilot_agent'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/copilot_agent.py
"""
Live-read co-pilot tool-loop.

A bounded Anthropic tool-use loop that fetches LIVE data on demand —
wallet, price, token risk, trending, CMC market skills, and agent
state/history — by wrapping functions that already exist (TwakCli,
SkillHub, ConvexBridge). Runs in-process on the VPS, next to its tools.

READ-ONLY: no tool here ever changes state. Writes (trades) stay on the
agent_commands -> command_worker path. Off the trade hot path.
"""
from __future__ import annotations

import json
from typing import Any

# ── Anthropic tool schemas ──────────────────────────────────────────────────
TOOLS: list[dict] = [
    {
        "name": "get_agent_state",
        "description": "Current trading agent state: realized PnL, drawdown, "
                       "halted flag, mode/strategy, and the last few decisions "
                       "(regime + risk verdict + reason). Use for 'how am I doing', "
                       "'why did it (not) trade', PnL/drawdown/history questions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_wallet",
        "description": "Live on-chain wallet holdings and USD values across chains "
                       "(via the self-custody TWAK wallet). Use for balance / "
                       "wallet / holdings questions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_price",
        "description": "Live spot price for a token symbol or TWAK asset id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "e.g. ETH, CAKE, or a TWAK asset id"},
                "chain": {"type": "string", "description": "default bsc"},
            },
            "required": ["token"],
        },
    },
    {
        "name": "check_token_risk",
        "description": "Security / rug-risk check for a token (TWAK asset id).",
        "input_schema": {
            "type": "object",
            "properties": {"asset_id": {"type": "string"}},
            "required": ["asset_id"],
        },
    },
    {
        "name": "get_trending",
        "description": "Trending BNB-chain tokens by recent price change.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "default 10"}},
        },
    },
    {
        "name": "cmc_market_skill",
        "description": "Run a CoinMarketCap market-data skill (OHLCV, funding/OI, "
                       "social/sentiment, on-chain flow) for an open-ended market "
                       "question. Returns the top matching skill's result.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def execute_tool(name: str, args: dict, *, twak, skills, bridge) -> str:
    """Run one read tool and return a JSON string for use as a tool_result.
    Never raises: any failure is returned as an {"error": ...} marker."""
    try:
        result = _dispatch_tool(name, args or {}, twak=twak, skills=skills, bridge=bridge)
    except Exception as exc:  # noqa: BLE001 — advisory only, never break the loop
        return json.dumps({"error": str(exc)[:300]})
    return json.dumps(result, default=str)


def _dispatch_tool(name: str, args: dict, *, twak, skills, bridge) -> Any:
    if name == "get_agent_state":
        led = bridge.latest_ledger() or {}
        cfg = bridge.get_config() or {}
        decisions = bridge.recent_decisions(limit=5) or []
        return {
            "pnl_usd": led.get("cumulative_pnl_usd", 0.0),
            "drawdown_pct": led.get("current_drawdown_pct", 0.0),
            "halted": bool(cfg.get("halted", False)),
            "mode": cfg.get("trading_mode", "unknown"),
            "strategy": cfg.get("strategy_name", "contrarian"),
            "recent_decisions": [
                {
                    "regime": d.get("regime"),
                    "risk_verdict": d.get("risk_verdict"),
                    "timestamp_ms": d.get("timestamp_ms"),
                    "risk_reason": d.get("risk_reason", ""),
                }
                for d in decisions
            ],
        }
    if name == "get_wallet":
        return twak.portfolio()
    if name == "get_price":
        return twak.price(args["token"], args.get("chain", "bsc"))
    if name == "check_token_risk":
        return twak.risk(args["asset_id"])
    if name == "get_trending":
        return twak.trending(category="bnb", limit=int(args.get("limit", 10)))
    if name == "cmc_market_skill":
        if not getattr(skills, "enabled", False):
            return {"status": "offline"}
        candidates = skills.find_skill(args["query"], top_k=3)
        if not candidates:
            return {"status": "no_skill_found"}
        unique = candidates[0].get("uniqueName")
        return skills.execute_skill(unique, {})
    raise ValueError(f"unknown tool: {name!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_agent_tools.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot_agent.py agent/tests/test_copilot_agent_tools.py
git commit -m "feat(copilot): live read-tool registry and executor"
```

---

### Task 2: The bounded tool-use loop

**Files:**
- Modify: `agent/copilot_agent.py` (append `run_read_loop` + constants)
- Test: `agent/tests/test_copilot_agent_loop.py`

**Interfaces:**
- Consumes: `TOOLS` and `execute_tool` from Task 1; an injected `client` exposing `client.messages.create(model, max_tokens, system, tools, messages) -> response` where `response.stop_reason` is a string and `response.content` is a list of blocks (each block has `.type`; `tool_use` blocks have `.id`, `.name`, `.input`; `text` blocks have `.text`).
- Produces: `run_read_loop(question, *, twak, skills, bridge, client, model="claude-haiku-4-5-20251001", max_turns=MAX_TOOL_TURNS) -> dict` returning `{"answer": str, "grounded": bool, "sources": list[dict]}`. Each source is `{"tool": name, "args": args}`. `MAX_TOOL_TURNS = 5`.

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/test_copilot_agent_loop.py
from types import SimpleNamespace
from unittest.mock import MagicMock
from agent.copilot_agent import run_read_loop, MAX_TOOL_TURNS


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _tool_block(tid, name, inp):
    return SimpleNamespace(type="tool_use", id=tid, name=name, input=inp)


def _resp(stop_reason, content):
    return SimpleNamespace(stop_reason=stop_reason, content=content)


def _deps():
    return MagicMock(), MagicMock(), MagicMock()


def test_answers_without_tools_when_model_does_not_call_any():
    twak, skills, bridge = _deps()
    client = MagicMock()
    client.messages.create.return_value = _resp("end_turn", [_text_block("All good, flat.")])
    out = run_read_loop("hi", twak=twak, skills=skills, bridge=bridge, client=client)
    assert out["answer"] == "All good, flat."
    assert out["grounded"] is False
    assert out["sources"] == []
    assert client.messages.create.call_count == 1


def test_executes_tool_then_returns_final_text():
    twak, skills, bridge = _deps()
    twak.price.return_value = {"price": 2.31}
    client = MagicMock()
    client.messages.create.side_effect = [
        _resp("tool_use", [_tool_block("t1", "get_price", {"token": "CAKE"})]),
        _resp("end_turn", [_text_block("CAKE is $2.31.")]),
    ]
    out = run_read_loop("price of cake?", twak=twak, skills=skills, bridge=bridge, client=client)
    assert out["answer"] == "CAKE is $2.31."
    assert out["grounded"] is True
    assert out["sources"] == [{"tool": "get_price", "args": {"token": "CAKE"}}]
    assert client.messages.create.call_count == 2


def test_loop_stops_at_max_turns():
    twak, skills, bridge = _deps()
    client = MagicMock()
    # Always returns tool_use -> would loop forever without the cap.
    client.messages.create.return_value = _resp(
        "tool_use", [_tool_block("t", "get_wallet", {})]
    )
    out = run_read_loop("x", twak=twak, skills=skills, bridge=bridge, client=client)
    # One create() per turn, capped at MAX_TOOL_TURNS.
    assert client.messages.create.call_count == MAX_TOOL_TURNS
    assert isinstance(out["answer"], str)


def test_tool_error_does_not_crash_loop():
    twak, skills, bridge = _deps()
    twak.price.side_effect = RuntimeError("twak down")
    client = MagicMock()
    client.messages.create.side_effect = [
        _resp("tool_use", [_tool_block("t1", "get_price", {"token": "X"})]),
        _resp("end_turn", [_text_block("Couldn't fetch the price.")]),
    ]
    out = run_read_loop("price?", twak=twak, skills=skills, bridge=bridge, client=client)
    assert out["answer"] == "Couldn't fetch the price."
    assert out["grounded"] is True  # a tool was attempted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_agent_loop.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_read_loop'`

- [ ] **Step 3: Write minimal implementation**

Append to `agent/copilot_agent.py`:

```python
MAX_TOOL_TURNS = 5

SYSTEM = (
    "You are Alien-Trade's read-only co-pilot for an autonomous BSC trading agent. "
    "Use the provided tools to fetch LIVE data when the question needs it — wallet, "
    "price, token risk, trending tokens, CMC market data, or the agent's own state "
    "and recent decisions. Do not invent data: if a tool returns an error or nothing, "
    "say so plainly. You CANNOT place or close trades — if the operator wants to act, "
    "tell them to issue a trade command. Answer concisely in markdown."
)


def run_read_loop(
    question: str,
    *,
    twak,
    skills,
    bridge,
    client,
    model: str = "claude-haiku-4-5-20251001",
    max_turns: int = MAX_TOOL_TURNS,
) -> dict:
    """Drive a bounded Anthropic tool-use loop and return the grounded answer."""
    messages: list[dict] = [{"role": "user", "content": question}]
    sources: list[dict] = []

    resp = client.messages.create(
        model=model, max_tokens=700, system=SYSTEM, tools=TOOLS, messages=messages,
    )
    turns = 1
    while resp.stop_reason == "tool_use" and turns < max_turns:
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            args = dict(block.input or {})
            sources.append({"tool": block.name, "args": args})
            out = execute_tool(block.name, args, twak=twak, skills=skills, bridge=bridge)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": out}
            )
        messages.append({"role": "user", "content": tool_results})
        resp = client.messages.create(
            model=model, max_tokens=700, system=SYSTEM, tools=TOOLS, messages=messages,
        )
        turns += 1

    answer = "".join(
        getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text"
    ).strip()
    if not answer:
        answer = "_(no answer produced — tool budget exhausted)_"
    return {"answer": answer, "grounded": bool(sources), "sources": sources}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_agent_loop.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot_agent.py agent/tests/test_copilot_agent_loop.py
git commit -m "feat(copilot): bounded live-read tool-use loop"
```

---

### Task 3: Wire the loop into the `/copilot` endpoint

**Files:**
- Modify: `agent/server.py` (add `_copilot_read_loop` helper; route `/copilot` to it when `SECOND_BRAIN=0` + API key present)
- Test: `agent/tests/test_copilot_endpoint_readloop.py`

**Interfaces:**
- Consumes: `run_read_loop` from `agent/copilot_agent.py`; `get_loop().bridge`; `TwakCli`; `SkillHub`; `anthropic.Anthropic`.
- Produces: `_copilot_read_loop(question: str) -> dict | None` (returns the loop result dict, or `None` when no `ANTHROPIC_API_KEY` so the caller falls back to the narrator). `/copilot` behaviour: when `_second_brain()` is `None`, try `_copilot_read_loop`; if it returns `None`, use the existing `_copilot_fallback`.

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/test_copilot_endpoint_readloop.py
from unittest.mock import patch, MagicMock
import agent.server as server


def test_copilot_uses_read_loop_when_second_brain_off():
    body = {"question": "what's my pnl?"}
    loop_result = {"answer": "Up $1.50.", "grounded": True,
                   "sources": [{"tool": "get_agent_state", "args": {}}]}
    with patch.object(server, "_second_brain", return_value=None), \
         patch.object(server, "_copilot_read_loop", return_value=loop_result) as rl:
        out = server.copilot(body)
    rl.assert_called_once_with("what's my pnl?")
    assert out["answer"] == "Up $1.50."
    assert out["grounded"] is True
    assert "action" in out  # server attaches action (None for a read)


def test_copilot_falls_back_to_narrator_when_read_loop_returns_none():
    body = {"question": "hello"}
    with patch.object(server, "_second_brain", return_value=None), \
         patch.object(server, "_copilot_read_loop", return_value=None), \
         patch.object(server, "_copilot_fallback", return_value="hi there") as fb:
        out = server.copilot(body)
    fb.assert_called_once()
    assert out["answer"] == "hi there"
    assert out["grounded"] is False


def test_read_loop_helper_returns_none_without_api_key():
    with patch.dict("os.environ", {}, clear=False) as _env:
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        assert server._copilot_read_loop("x") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_endpoint_readloop.py -v`
Expected: FAIL — `AttributeError: module 'agent.server' has no attribute '_copilot_read_loop'`

- [ ] **Step 3: Write minimal implementation**

Add this helper to `agent/server.py` directly above the existing `@app.post("/copilot")` (near line 243):

```python
def _copilot_read_loop(question: str) -> dict | None:
    """Live-read tool-loop brain for the co-pilot. Returns the loop result, or
    None when no ANTHROPIC_API_KEY (caller falls back to the narrator)."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    import anthropic
    from agent.copilot_agent import run_read_loop
    from agent.skills import SkillHub
    from agent.twak_cli import TwakCli

    client = anthropic.Anthropic(api_key=api_key)
    return run_read_loop(
        question,
        twak=TwakCli(),
        skills=SkillHub(),
        bridge=get_loop().bridge,
        client=client,
    )
```

Then change the `SECOND_BRAIN=0` branch of `copilot()` (the `if sb is None:` block, currently lines 249-252) from:

```python
    if sb is None:
        answer = _copilot_fallback(question)
        action = _extract_action(question, answer)
        return {"answer": answer, "grounded": False, "sources": [], "action": action}
```

to:

```python
    if sb is None:
        loop_res = _copilot_read_loop(question)
        if loop_res is not None:
            loop_res["action"] = _extract_action(question, loop_res["answer"])
            return loop_res
        answer = _copilot_fallback(question)
        action = _extract_action(question, answer)
        return {"answer": answer, "grounded": False, "sources": [], "action": action}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest agent/tests/test_copilot_endpoint_readloop.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full co-pilot test suite to check nothing regressed**

Run: `core/.venv/bin/python -m pytest agent/tests/ -k "copilot" -v`
Expected: PASS (all copilot tests green)

- [ ] **Step 6: Commit**

```bash
git add agent/server.py agent/tests/test_copilot_endpoint_readloop.py
git commit -m "feat(copilot): route /copilot to live-read tool-loop when Second Brain off"
```

---

### Task 4: Live smoke test on the VPS

**Files:** none (manual verification against the running service)

**Interfaces:**
- Consumes: the running `alien-trade` service + the `/copilot` endpoint on the VPS (`http://localhost:8000` from on-box).

- [ ] **Step 1: Restart the service to load the new code**

```bash
systemctl restart alien-trade
systemctl status alien-trade --no-pager
```
Expected: `active (running)`.

- [ ] **Step 2: Ask a read question that should trigger a tool**

```bash
curl -s -X POST http://localhost:8000/copilot \
  -H 'Content-Type: application/json' \
  -d '{"question":"what is my wallet balance and current PnL?"}' | python3 -m json.tool
```
Expected: JSON with a non-empty `answer`, `grounded: true`, and `sources` listing `get_wallet` and/or `get_agent_state`.

- [ ] **Step 3: Ask a trivial question that should NOT trigger a tool**

```bash
curl -s -X POST http://localhost:8000/copilot \
  -H 'Content-Type: application/json' \
  -d '{"question":"what are you?"}' | python3 -m json.tool
```
Expected: JSON with an `answer`, `grounded: false`, `sources: []`.

- [ ] **Step 4: Confirm the trade path is untouched (read-only guarantee)**

```bash
grep -n "swap_execute\|transfer\|automate_add" agent/copilot_agent.py || echo "OK: no write calls in read-loop"
```
Expected: `OK: no write calls in read-loop`.

---

## Out of scope (deliberate)

- **Web search tool** — the TWAK + CMC + bridge tools already cover market, wallet, price, risk, and history. Web search is the long tail; defer until after the Jun 21 freeze.
- **Second Brain / RAG** — stays off (empty vector store). This loop uses live tools only.
- **Frontend transport** — the cockpit currently streams via Convex `askStreaming` (narrator). Pointing the UI's tool questions at the `ask` action (which proxies to this `/copilot`) is a separate small frontend task; the backend here returns the full grounded answer that `ask` already relays.
- **Trade-by-chat** — already works via the `agent_commands` → `command_worker` grammar path; this loop is read-only by design.
- **Duplicate narrator cleanup** — `_copilot_fallback` (VPS) vs `askStreaming` (Convex) remain; `_copilot_fallback` is now the no-API-key fallback. Consolidation is a follow-up, not required here.
