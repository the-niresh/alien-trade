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
