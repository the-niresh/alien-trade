"""
Fire-and-forget sponsor-call recorder.

No-op until set_sink() is called. A daemon thread drains the queue and
forwards calls to the sink. Sink failures are swallowed - telemetry must
never impact the trade path.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

_queue: queue.Queue = queue.Queue()
_sink: Optional[Callable] = None
_started = False
_lock = threading.Lock()


@dataclass
class SponsorCall:
    sponsor:    str            # "CMC" | "TWAK" | "BNB_SDK"
    kind:       str
    endpoint:   str
    status:     str            # "ok" | "error"
    latency_ms: float
    cost_usd:   Optional[float] = None
    tx_hash:    Optional[str]   = None
    cycle_id:   Optional[str]   = None
    detail:     str = "{}"
    ts_ms:      int = field(default_factory=lambda: int(time.time() * 1000))

    def as_row(self) -> dict:
        # Convex `v.optional(...)` accepts an ABSENT field but rejects an explicit
        # null, so omit the optional fields entirely when they have no value rather
        # than sending None (which serialises to JSON null → ArgumentValidationError).
        row: dict = {
            "sponsor":    self.sponsor,
            "kind":       self.kind,
            "endpoint":   self.endpoint,
            "status":     self.status,
            "latency_ms": self.latency_ms,
            "detail":     self.detail,
            "ts_ms":      self.ts_ms,
        }
        if self.cost_usd is not None:
            row["cost_usd"] = self.cost_usd
        if self.tx_hash is not None:
            row["tx_hash"] = self.tx_hash
        if self.cycle_id is not None:
            row["cycle_id"] = self.cycle_id
        return row


def _worker() -> None:
    while True:
        call = _queue.get()
        try:
            if _sink is not None:
                _sink(call)
        except Exception:
            pass
        finally:
            _queue.task_done()


def _ensure_started() -> None:
    global _started
    with _lock:
        if not _started:
            t = threading.Thread(target=_worker, daemon=True, name="sponsor-telemetry")
            t.start()
            _started = True


def set_sink(fn: Optional[Callable[[SponsorCall], Any]]) -> None:
    """Register the sink. Call once at runtime startup. Pass None to disable."""
    global _sink
    _sink = fn
    if fn is not None:
        _ensure_started()


def record_sponsor_call(
    sponsor: str,
    kind: str,
    endpoint: str,
    status: str,
    latency_ms: float,
    *,
    cost_usd: Optional[float] = None,
    tx_hash: Optional[str] = None,
    cycle_id: Optional[str] = None,
    detail: str = "{}",
) -> None:
    """Enqueue a sponsor call for async forwarding to the sink. Never raises."""
    if _sink is None:
        return
    call = SponsorCall(
        sponsor=sponsor,
        kind=kind,
        endpoint=endpoint,
        status=status,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        tx_hash=tx_hash,
        cycle_id=cycle_id,
        detail=detail,
    )
    try:
        _queue.put_nowait(call)
    except Exception:
        pass
