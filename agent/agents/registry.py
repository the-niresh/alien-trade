"""CRUD over spawned_agents via the ConvexBridge. One call site for agent records."""
from __future__ import annotations


def create_agent(bridge, spec: dict):
    return bridge.call("mutation", "spawnedAgents:create", {
        "name": spec["name"], "goal": spec["goal"],
        "allowed_tools": spec.get("allowed_tools", []),
        "trigger": spec.get("trigger"),
        "notify_policy": spec.get("notify_policy"),
        "mode": spec.get("mode", "paper"),
    })


def list_active(bridge):
    return bridge.call("query", "spawnedAgents:list", {}) or []


def rename(bridge, agent_id, name: str):
    bridge.call("mutation", "spawnedAgents:rename", {"id": agent_id, "name": name})


def archive(bridge, agent_id):
    bridge.call("mutation", "spawnedAgents:setStatus", {"id": agent_id, "status": "archived"})


def heartbeat(bridge, agent_id):
    bridge.call("mutation", "spawnedAgents:updateActivity", {"id": agent_id})
