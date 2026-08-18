"""alien_trade_thesis_check - falsification-as-a-service over the thesis ledger.

A second CMC Skills Marketplace skill (AWAKE_SPRINT §3.5, L1 depth). Given a free-text
trading idea, it finds the nearest card in our thesis ledger and reports whether the
idea was VALIDATED or FALSIFIED in honest walk-forward + holdout testing - with its OOS
objective, deflated Sharpe, and source citation. The honest-research story as an API.

Reuses the Track-2 skill endpoint pattern (agent/skills/track2.py).
"""
from __future__ import annotations

import os
import re
from typing import Optional

_VERDICT = {"validated": "supported", "FALSIFIED": "avoid"}


_STOP = {"the", "a", "an", "in", "into", "on", "of", "to", "and", "or", "for",
         "is", "are", "be", "does", "do", "work", "works", "every"}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in _STOP and len(t) >= 3}


def _fuzzy_overlap(a: set[str], b: set[str]) -> int:
    """Count idea tokens that share a 4-char stem with any card token (so
    'rotation'~'rotate', 'momentum'~'momentum'). Falls back to exact for short tokens."""
    n = 0
    for x in a:
        sx = x[:4]
        if any(x == y or (len(x) >= 4 and len(y) >= 4 and y[:4] == sx) for y in b):
            n += 1
    return n


class ThesisCheckSkill:
    def __init__(self, bridge=None):
        if bridge is None:
            from agent.convex_bridge import ConvexBridge
            bridge = ConvexBridge(url=os.environ.get("CONVEX_URL", ""))
        self.bridge = bridge

    def compute(self, idea_text: str) -> dict:
        cards = self.bridge.recent_theses(limit=200) or []
        idea = _tokens(idea_text)
        best, best_overlap = None, 0
        for c in cards:
            overlap = _fuzzy_overlap(idea, _tokens(c.get("claim", "")))
            if overlap > best_overlap:
                best, best_overlap = c, overlap
        if best is None or best_overlap == 0:
            return {"status": "untested", "oos_objective": None, "deflated_sharpe": None,
                    "source": None, "verdict": "unknown",
                    "note": "no matching thesis in the ledger yet"}
        status = best.get("status", "untested")
        return {
            "status": status,
            "oos_objective": best.get("oos_objective"),
            "deflated_sharpe": best.get("deflated_sharpe"),
            "source": best.get("source"),
            "verdict": _VERDICT.get(status, "unknown"),
            "matched_claim": best.get("claim"),
        }
