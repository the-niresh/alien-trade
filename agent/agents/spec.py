"""Validation for user-spawned Agent records. Validates structured input from
the co-pilot's create_agent tool - never parses free text. Default mode is paper."""
from __future__ import annotations

from agent.copilot_agent import TOOLS

# Tier-A Agent Tools an Agent may compose = the co-pilot's read tools.
AGENT_TOOL_NAMES = frozenset(t["name"] for t in TOOLS)

_DEFAULT_NOTIFY = {"webpush": True, "severity_min": "info"}


def validate_agent_spec(raw: dict) -> dict:
    name = str(raw.get("name", "")).strip()
    goal = str(raw.get("goal", "")).strip()
    if not name or not goal:
        raise ValueError("agent requires a non-empty name and goal")

    tools = list(raw.get("allowed_tools") or [])
    for t in tools:
        # Level-2 delegation: "agent:<id>" tools reference other spawned agents
        if t.startswith("agent:"):
            continue
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
