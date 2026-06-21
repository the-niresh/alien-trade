"""Flag spawned Agents that have gone silent past their expected cadence.
No Agent fails quietly (2026-06-20 outage lesson)."""
from __future__ import annotations

import re

STALL_FACTOR = 3
_HOUR_MS = 3600_000
_SPEC_RE = re.compile(r"^\s*(\d+)\s*h\s*$", re.I)


def default_cadence_ms(trigger) -> int:
    if isinstance(trigger, dict):
        m = _SPEC_RE.match(str(trigger.get("spec", "")))
        if m:
            return int(m.group(1)) * _HOUR_MS
    return _HOUR_MS


def find_stalled(agents: list[dict], now_ms: int) -> list[dict]:
    out = []
    for a in agents:
        if a.get("status") != "active":
            continue
        last = a.get("last_activity_ms") or 0
        if now_ms - last > STALL_FACTOR * default_cadence_ms(a.get("trigger")):
            out.append(a)
    return out
