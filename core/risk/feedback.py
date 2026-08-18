"""
Human-feedback gate - the deterministic side of the human-in-the-loop.

The operator supervises the live run and marks decisions good or bad from the
cockpit (a thumbs up/down on a setup). Those labels are stored per *setup key*
(regime + dominant signal) and consulted before the next trade on the same setup:
enough "bad" marks block it, a single net-bad mark shrinks it. This is the human
feedback loop the project's intelligence rests on - pure arithmetic, off the LLM
path, sim/live-shared in shape (offline → no records → ALLOW, so parity holds).

Mirrors the mistake-avoidance verdict shape so the loop treats both the same way.
"""
from __future__ import annotations

from dataclasses import dataclass

# How many net-bad marks before we block vs merely shrink.
BLOCK_THRESHOLD = 2       # net (bad - good) >= 2 → block the setup
PENALTY_THRESHOLD = 1     # net (bad - good) >= 1 → halve size
PENALTY_SIZE = 0.5

_SIGNAL_KEYS = ("momentum", "derivatives", "sentiment", "flow")


def setup_key(regime: str, signals: dict) -> str:
    """A coarse, stable label for the *kind* of trade, so feedback on one instance
    generalises to similar ones. = regime + the dominant signal with its sign,
    e.g. "chop|momentum-" or "trend_up|sentiment+". Coarse on purpose: too-fine a
    key never accumulates enough feedback to matter."""
    dominant, mag, sign = "none", 0.0, "+"
    for k in _SIGNAL_KEYS:
        v = signals.get(k)
        if v is None:
            continue
        if abs(v) > mag:
            mag, dominant, sign = abs(v), k, ("+" if v >= 0 else "-")
    if dominant == "none":
        return f"{regime}|flat"
    return f"{regime}|{dominant}{sign}"


@dataclass(frozen=True)
class FeedbackVerdict:
    block: bool
    size_penalty: float   # 0.0 = full size, 0.5 = halve, etc.
    reason: str


def evaluate_feedback(records: list[dict]) -> FeedbackVerdict:
    """Given the human labels for the current setup key, decide block / shrink / allow.
    Each record carries `label` in {"good","bad"}. Net = bad − good. Empty → ALLOW."""
    if not records:
        return FeedbackVerdict(False, 0.0, "no human feedback on this setup")
    bad = sum(1 for r in records if r.get("label") == "bad")
    good = sum(1 for r in records if r.get("label") == "good")
    net = bad - good
    if net >= BLOCK_THRESHOLD:
        return FeedbackVerdict(True, 1.0,
                               f"operator flagged this setup bad x{bad} (net {net}) - blocked")
    if net >= PENALTY_THRESHOLD:
        return FeedbackVerdict(False, PENALTY_SIZE,
                               f"operator flagged this setup bad (net {net}) - size halved")
    return FeedbackVerdict(False, 0.0,
                           f"human feedback net {net} (good {good}/bad {bad}) - allowed")
