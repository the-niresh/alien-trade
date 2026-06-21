"""Prebuilt Agent specs the co-pilot/UI can spawn in one tap.

Template catalogue:
  market_watcher  — Level-0: single-tool monitor (existing, Template A)
  setup_scorer    — Level-1: Researcher→Historian→CoPilot chain (Template C)
  daily_brief     — Level-2: delegates to a list of sub-agents (Template D)
"""
from __future__ import annotations

from agent.agents.spec import validate_agent_spec


def market_watcher(symbol: str, condition: str) -> dict:
    """Template A — monitor one symbol, notify on condition (single-hop)."""
    return validate_agent_spec({
        "name": f"{symbol}-Watcher",
        "goal": f"Monitor {symbol}. Notify me when {condition}.",
        "allowed_tools": ["get_price", "cmc_market_skill"],
        "trigger": {"kind": "schedule", "spec": "1h"},
        "mode": "paper",
    })


def setup_scorer(symbol: str) -> dict:
    """Template C — Level-1 chain: Researcher→Historian→CoPilot.

    Scores the current setup for `symbol`: gather market conditions, check
    if we've lost on this pattern before, synthesise a one-paragraph call.
    Requires Phase-2 orchestrator (run_chain("setup_scorer", ...)).
    """
    return validate_agent_spec({
        "name": f"{symbol}-SetupScorer",
        "goal": (
            f"Score the current {symbol} setup. "
            f"Research market conditions and funding/OI. "
            f"Check if we have lost on this pattern before. "
            f"Synthesise a one-paragraph trade call: enter / wait / avoid."
        ),
        "allowed_tools": ["get_price", "cmc_market_skill", "get_agent_state"],
        "trigger": {"kind": "schedule", "spec": "4h"},
        "mode": "paper",
    })


def daily_brief(sub_agent_ids: list[str] | None = None) -> dict:
    """Template D — Level-2 delegation: compiles a brief from sub-agents.

    `sub_agent_ids` are Convex spawned_agents IDs. Each is injected as an
    "agent:<id>" allowed_tool — the orchestrator's delegate() handles them.
    """
    agent_tools = [f"agent:{aid}" for aid in (sub_agent_ids or [])]
    return validate_agent_spec({
        "name": "Daily-Brief",
        "goal": (
            "Compile a daily market brief. Delegate to each of your sub-agents, "
            "merge their findings, and report key opportunities, warnings, and "
            "the overall market posture in bullet-point form."
        ),
        "allowed_tools": agent_tools,
        "trigger": {"kind": "schedule", "spec": "24h"},
        "mode": "paper",
    })
