"""
Shared dataclasses for the Second Brain layer.

A *setup key* is the deterministic English fingerprint of a trade context
(regime + which signal dominates + side). The same function builds it on the
write path (reflection) and the read path (mistake-avoidance), so a stored
lesson and a new lookup land in the same neighbourhood of vector space - that is
what makes "have we lost on this exact setup before?" actually retrieve.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Memory namespaces (stored in metadata.kind; client-side filtered on query).
KIND_REFLECTION = "reflection"        # Hermes post-trade lessons
KIND_INSTITUTIONAL = "institutional"  # 2-year walk-forward labels
KIND_RESEARCH = "research"            # Karpathy AutoResearch digests


@dataclass
class MemoryHit:
    id: str
    score: float                      # cosine similarity in [0, 1]
    text: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Reflection:
    """One post-trade lesson: {signals, regime, outcome, lesson}."""
    cycle_id: str
    trade_id: Optional[str]
    timestamp_ms: int
    regime: str
    side: str
    signals: dict
    outcome_pnl_usd: float
    setup_key: str
    lesson: str = ""
    quality: str = ""              # "" = normal, "low" = rubric failed twice (8.13)
    source_cycle_id: Optional[str] = None  # closing cycle that triggered this reflection (8.12)

    @property
    def outcome_label(self) -> str:
        if self.outcome_pnl_usd > 0:
            return "win"
        if self.outcome_pnl_usd < 0:
            return "loss"
        return "scratch"


@dataclass
class ResearchDigest:
    id: str
    timestamp_ms: int
    question: str
    findings: str
    tags: list[str] = field(default_factory=list)
    low_confidence: bool = False           # rubric self-check failed twice (8.13)
    source_cycle_id: Optional[str] = None  # research-tick cycle that produced this digest (8.12)


@dataclass
class LLMResult:
    text: str
    tier: str                 # "T0" | "T1" | "T2"
    model: str
    in_tokens: int = 0
    out_tokens: int = 0
    cost_usd: float = 0.0
    cache_hit: bool = False
    latency_s: float = 0.0
    stub: bool = False        # True = produced offline without an API call


# ── Setup-key fingerprint (shared by write + read paths) ───────────────────────

def dominant_signal(signals: dict) -> str:
    """Name the signal with the largest absolute contribution."""
    # Accept both the canonical names and any legacy keys that may appear in
    # older stored reflections.
    keys = {
        "momentum":    "momentum",
        "derivatives": "derivatives",
        "sentiment":   "sentiment",
        "flow":        "flow",
    }
    best_name, best_abs = "none", 0.0
    for k, v in signals.items():
        canonical = keys.get(k)
        if canonical is None or v is None:
            continue
        if abs(float(v)) > best_abs:
            best_abs, best_name = abs(float(v)), canonical
    return best_name


def setup_key(regime: str, signals: dict, side: str) -> str:
    """
    Deterministic English fingerprint of a trade setup. Stable across write/read
    so the embedding lands two records about the same setup near each other.
    """
    dom = dominant_signal(signals)
    return f"{side} in {regime} regime driven by {dom} signal"
