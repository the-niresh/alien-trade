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
