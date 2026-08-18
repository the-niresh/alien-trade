"""
Structured logging for the live runtime (Step 7 observability).

One JSON line per event on stdout, keyed by `trace` = cycle_id - the correlation
id that also ties together the Convex decision / trade / audit rows. Machine-
parseable so a testnet shadow-run can be streamed/grepped for the exceptions the
code didn't anticipate, then tuned. `json.dumps` defaults to ensure_ascii=True,
so every line is cp1252-safe on a Windows console.

Deliberately tiny and dependency-free - the Convex audit log is still the
durable event store; this is the live stdout tap for ops + exception harvesting.
"""
from __future__ import annotations

import json
import time
from typing import Optional


def jlog(event: str, *, trace: Optional[str] = None, level: str = "info", **fields) -> str:
    """Emit one structured JSON log line; returns it (handy for tests)."""
    rec: dict = {"ts_ms": int(time.time() * 1000), "level": level, "event": event}
    if trace is not None:
        rec["trace"] = trace
    rec.update(fields)
    line = json.dumps(rec, default=str)     # ensure_ascii=True → cp1252-safe
    print(line, flush=True)
    return line
