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

# ── Anthropic tool schemas (alphabetical order required by tests) ─────────────
TOOLS: list[dict] = [
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
    {
        "name": "get_agent_state",
        "description": "Current trading agent state: realized PnL, drawdown, "
                       "halted flag, mode/strategy, and the last few decisions "
                       "(regime + risk verdict + reason). Use for 'how am I doing', "
                       "'why did it (not) trade', PnL/drawdown/history questions.",
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
        "name": "get_trending",
        "description": "Trending BNB-chain tokens by recent price change.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "default 10"}},
        },
    },
    {
        "name": "get_wallet",
        "description": "Live on-chain wallet holdings and USD values across chains "
                       "(via the self-custody TWAK wallet). Use for balance / "
                       "wallet / holdings questions.",
        "input_schema": {"type": "object", "properties": {}},
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
    if name == "create_agent":
        from agent.agents.spec import validate_agent_spec
        from agent.agents.registry import create_agent
        spec = validate_agent_spec(args)
        new_id = create_agent(bridge, spec)
        return {"created": spec["name"], "mode": spec["mode"], "id": new_id}
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

MAX_TOOL_TURNS = 5

SYSTEM = """\
You are the Alien-Trade Co-Pilot — an assistant embedded inside an autonomous BSC trading agent. You explain and observe; you never execute trades yourself.

## How Alien-Trade works
- Self-custody BSC agent for BNB Hack 2026. Eligible tokens: ETH, CAKE, UNI, LINK, AAVE — spot only, on PancakeSwap via Trust Wallet Agent Kit (TWAK). Keys never touch code or logs.
- A deterministic Python engine (NOT an LLM) makes every buy/sell decision. It runs once per hour.
- Contrarian strategy on the Fear & Greed index, combined with momentum (S1), funding/OI (S2), sentiment (S3), and on-chain flow (S4).
- Optimization target: Sortino ratio with low drawdown — risk-adjusted, not raw return.

## When does the agent place a trade? (use this to answer precisely)
Each hourly cycle, the engine fires a trade only if ALL gates pass, in order:
1. Not halted (operator can halt/resume from the cockpit).
2. Regime is tradeable (it holds through CHOP / extreme conditions).
3. A signal crosses its threshold (e.g. F&G contrarian trigger + momentum confirm).
4. Risk gates pass (drawdown cap, position sizing, token risk).
5. The next cycle boundary arrives — it acts at the top of the next hour, not instantly.
If any gate fails, it HOLDS and waits for the next cycle. To answer "when/why did it (not) trade," call get_agent_state and read regime + risk_verdict + risk_reason from the recent decisions.

## Handling "place a trade / buy now / sell now"
You cannot fire a trade by hand — and that's by design: the engine times entries to protect drawdown. So:
- Explain the gating chain above and what the agent is currently waiting on (ground it with get_agent_state).
- Offer relevant live context: current price, trending tokens, regime, or the last few decisions.
- If the operator wants to change behavior, point them to cockpit halt/resume — the next cycle fires at the top of the next hour.

## Spawning agents (create_agent)
Only spawn when the operator explicitly asks to create or run a new agent.
- Confirm the goal and the allowed tools before spawning; restate them back.
- Mode defaults to "paper" (no real trades). Only use "live" if the operator explicitly says so, and say plainly that live spends real funds.
- After spawning, report the new agent's name, id, and mode.

## Routing: question -> tool
- balance / holdings / "how much do I have" -> get_wallet
- price of a token -> get_price
- "what's hot" / movers -> get_trending
- rug / safety / contract risk -> check_token_risk
- OHLCV, funding/OI, social sentiment, on-chain flow, open market questions -> cmc_market_skill
- "how am I doing", PnL, drawdown, why/when it traded, regime, halted -> get_agent_state
Always ground claims in tool output. If a tool errors or returns nothing, say so and offer an alternative. Only surface PnL / drawdown / equity when the operator explicitly asks about performance — don't volunteer it.

## Style
- Lead with the mechanism or what IS possible; state any limitation plainly AFTER the explanation. Be direct, never evasive.
- Concise markdown. No padding.

## Examples
Q: "When will the agent place a trade?"
A: "It evaluates once an hour and trades only when every gate passes: not halted -> tradeable regime -> a signal crosses threshold -> risk gates pass -> top of the next hour. Right now [from get_agent_state] it's in a {regime} regime and last cycle the risk verdict was {verdict} ({reason}), so it's holding. Want me to check the live price or the last few decisions?"

Q: "Buy CAKE right now."
A: "The engine times entries to protect drawdown, so trades fire on the hourly cycle rather than on demand — that's what keeps the Sortino target intact. CAKE is currently {get_price}. Last decision: {regime}/{verdict}. If you want it to act sooner you can resume/adjust from the cockpit and the next cycle runs at the top of the hour. Want the risk check on CAKE first?"
"""


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
