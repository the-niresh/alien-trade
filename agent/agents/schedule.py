"""Decide which agents are due and fan a notification out to push subscriptions."""
from __future__ import annotations

from agent.agents.watchdog import default_cadence_ms
from agent.push import send_push as _send_push


def due_agents(agents: list[dict], now_ms: int) -> list[dict]:
    out = []
    for a in agents:
        if a.get("status") != "active":
            continue
        last = a.get("last_activity_ms") or 0
        if now_ms - last >= default_cadence_ms(a.get("trigger")):
            out.append(a)
    return out


def deliver_push(bridge, payload: dict, *, vapid: dict, sender=_send_push) -> int:
    subs = bridge.call("query", "push:list", {}) or []
    delivered = 0
    for s in subs:
        sub = {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}}
        if sender(sub, payload, vapid=vapid):
            delivered += 1
        else:
            bridge.call("mutation", "push:remove", {"id": s["_id"]})
    return delivered
