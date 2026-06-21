"""Telegram approval gate for the headless ralph loop (AWAKE_SPRINT §6.3).

When the loop needs to touch a file outside docs/FROZEN_ALLOWLIST.txt it raises an
AT-REQ via the **alien-trade** bot (agent/notify.py TelegramBot — NEVER the claude-code
Telegram plugin; that is a hard rule). The operator replies "approve AT-REQ-n" (or a
bare "yes" for the latest). re_ping_if_stale resends every 30 min while pending.

ingest_text is decoupled from any bot so it is unit-testable; attach() wires it into a
real TelegramBot's command dispatch (/approve, /yes) for live use.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

_REQ_RE = re.compile(r"at-req-\d+", re.I)
_BARE_YES = {"yes", "approve", "y", "ok", "approved"}


@dataclass
class _Req:
    files: list
    reason: str
    ts: float
    approved: bool = False


class ApprovalGate:
    def __init__(self, bot):
        self.bot = bot
        self._reqs: dict[str, _Req] = {}
        self._order: list[str] = []

    def request(self, req_id: str, files: list, reason: str) -> None:
        self._reqs[req_id] = _Req(list(files), reason, time.time())
        self._order.append(req_id)
        files_s = ", ".join(files)
        self.bot.send(f"Approve {req_id}? +files: {files_s} · reason: {reason}")

    def is_approved(self, req_id: str) -> bool:
        r = self._reqs.get(req_id)
        return bool(r and r.approved)

    def _pending_ids(self) -> list[str]:
        return [rid for rid in self._order
                if rid in self._reqs and not self._reqs[rid].approved]

    def ingest_text(self, text: str) -> bool:
        """Apply a Telegram reply. Returns True if it approved a pending request."""
        t = (text or "").strip().lower()
        m = _REQ_RE.search(t)
        if m:
            target = m.group(0).lower()
            for k in self._reqs:
                if k.lower() == target:
                    self._reqs[k].approved = True
                    return True
            return False
        if t in _BARE_YES:
            pend = self._pending_ids()
            if pend:
                self._reqs[pend[-1]].approved = True
                return True
        return False

    def re_ping_if_stale(self, req_id: str, seconds: int = 1800) -> bool:
        r = self._reqs.get(req_id)
        if r and not r.approved and (time.time() - r.ts) >= seconds:
            self.bot.send(f"⏳ still pending {req_id}: {r.reason}")
            r.ts = time.time()
            return True
        return False

    def attach(self, bot=None) -> None:
        """Wire /approve and /yes into a real TelegramBot's command dispatch."""
        b = bot or self.bot
        if hasattr(b, "register_command"):
            b.register_command(
                "approve",
                lambda args: "✅ approved" if self.ingest_text(f"approve {args}") else "no matching AT-REQ",
            )
            b.register_command(
                "yes",
                lambda _args: "✅ approved latest" if self.ingest_text("yes") else "nothing pending",
            )
