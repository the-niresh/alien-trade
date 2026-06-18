"""
Inter-agent contracts — the single, versioned source of every payload that
crosses an agent boundary, plus the failure matrix. Defined BEFORE the supervisor
is wired (AGENT_TEAM_PLAN §9.2): "standardize output formats before building
anything; if A outputs text and B expects JSON the handoff silently fails."

Three rules this file exists to keep:

  1. No agent emits an ad-hoc shape. If a payload crosses a boundary, its
     dataclass lives here (or is re-exported here from where it already lives).
  2. The shapes that land in Convex carry an `as_row()` whose keys match the
     table columns in `convex/schema.ts` exactly — one write path, no drift.
  3. The failure matrix (§9.3) is data, not prose: a Tier-1 (advisory/learning)
     agent failing must NEVER halt or distort a trade. `tier_of()` /
     `is_tier0()` make that machine-checkable.

What lives where (deliberate boundary, locked decision #2 — `/core` is
standalone and must not import `agent/`):
  - This file owns the *data shapes* the agents and Convex share.
  - The Option-B forecast *math* (decay + shrink-only clamp) lives in `core/risk/`
    (STEP 8.4) and operates on plain floats/ints, so `/core` never imports this.
    `ForecastState` here is just what the Researcher writes and the agent reads
    before handing a plain number across the seam.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

CONTRACTS_VERSION = 1  # bump when any cross-boundary shape changes


def _now_ms() -> int:
    return int(time.time() * 1000)


# ── Re-exported existing payloads (one canonical import site) ──────────────────
# These already exist and are tested; §9.2 says reuse them, don't redefine. Import
# them from here so every agent has a single place to look for "what shape?".
from agent.brain import AvoidanceVerdict  # Historian read-path verdict (block/shrink)
from agent.secondbrain.schema import (  # noqa: E402
    Reflection,        # Hermes post-trade lesson (Reflector → Historian write)
    ResearchDigest,    # Karpathy AutoResearch digest (Researcher output)
    MemoryHit,         # Upstash Vector recall hit
)
from agent.social.schema import SentimentReading  # social S3 bridge number

__all__ = [
    "CONTRACTS_VERSION",
    # re-exports
    "AvoidanceVerdict", "Reflection", "ResearchDigest", "MemoryHit", "SentimentReading",
    # agent roster / event taxonomy
    "AGENTS", "TIER0_AGENTS", "TIER1_AGENTS", "tier_of", "is_tier0",
    "RISK_GUARD", "SCOUT", "SUPERVISOR",
    "EVENT_KINDS", "AgentEvent",
    # option-B forecast bridge
    "NEUTRAL_CONFIDENCE", "DEFAULT_FORECAST_TTL_MS", "ForecastState",
    # user control surface
    "AgentControl",
    # failure matrix
    "FAILURE_MATRIX", "FailurePolicy", "failure_policy_for",
]


# ── The roster + its two tiers (AGENT_TEAM_PLAN §1) ────────────────────────────
# Tier 0 = the deterministic trade hot path (the only tier allowed to stop a
# trade). Tier 1 = advisory/learning (LLM, off the hot path; failing here is
# never allowed to touch a trade — see FAILURE_MATRIX).

ORCHESTRATOR = "Orchestrator"
STRATEGIST = "Strategist"
RISK_OFFICER = "Risk Officer"
RISK_GUARD = "RiskGuard"   # deterministic guardrail (equity floor, staleness) — emits to channel
SCOUT = "Scout"   # X/KOL watcher — emits social-trigger events, never a Tier-0 decision
TRADE_HANDLER = "Trade Handler"
HISTORIAN = "Historian"
RESEARCHER = "Researcher"
REFLECTOR = "Reflector"
COPILOT = "Co-pilot"
DREAMER = "Dreamer"
USER = "User"  # control-surface events ("User paused the agents")
SUPERVISOR = "Supervisor"  # orchestrator endpoint failure events

TIER0_AGENTS = frozenset({STRATEGIST, RISK_OFFICER, TRADE_HANDLER})
TIER1_AGENTS = frozenset({HISTORIAN, RESEARCHER, REFLECTOR, COPILOT, DREAMER})
# Guardrails / infrastructure agents — in AGENTS but not in either tier
# (they observe, enforce limits, and emit events; they don't make trade decisions)
AGENTS = frozenset({ORCHESTRATOR, USER, SUPERVISOR, RISK_GUARD, SCOUT}) | TIER0_AGENTS | TIER1_AGENTS


def tier_of(agent: str) -> Optional[int]:
    """0 for the deterministic hot path, 1 for advisory/learning, None otherwise
    (Orchestrator/User are neither — they route/observe, they don't trade)."""
    if agent in TIER0_AGENTS:
        return 0
    if agent in TIER1_AGENTS:
        return 1
    return None


def is_tier0(agent: str) -> bool:
    """True only for agents allowed to halt a trade cycle (§9.3 governing rule)."""
    return agent in TIER0_AGENTS


# ── Agent Activity Channel event (the "glass cockpit" stream, §7) ──────────────
# Append-only; the marketing surface AND the human-readable audit log, same data.
# `headline` is template-rendered from structured fields (cheap, deterministic,
# zero added hot-path latency — no LLM call to write a trace).

KIND_OBSERVATION = "observation"  # "what I saw"   (Strategist: regime + signals)
KIND_ANALYSIS = "analysis"        # "what I think" (Historian: 3 past losses)
KIND_VERDICT = "verdict"          # "my call"      (Risk Officer: size 1.2 -> 0.84)
KIND_ACTION = "action"            # "what I did"   (Trade Handler: signed + filled)
KIND_HANDOFF = "handoff"          # "passing on"   (Reflector: will reflect on close)
KIND_CONTROL = "control"          # "user acted"   (User: paused agents / kill switch)
EVENT_KINDS = (
    KIND_OBSERVATION, KIND_ANALYSIS, KIND_VERDICT,
    KIND_ACTION, KIND_HANDOFF, KIND_CONTROL,
)


@dataclass
class AgentEvent:
    """One trace row in the Agent Activity Channel (`agent_events` table)."""
    agent: str                                  # one of AGENTS
    kind: str                                   # one of EVENT_KINDS
    headline: str                               # one-line, the agent's own voice
    cycle_id: Optional[str] = None              # ties a team's actions to one decision
    detail: dict = field(default_factory=dict)  # structured payload (numbers/lists)
    refs: list[str] = field(default_factory=list)  # reflection/digest ids, tx hash
    ts_ms: int = field(default_factory=_now_ms)

    def __post_init__(self) -> None:
        if self.agent not in AGENTS:
            raise ValueError(f"unknown agent {self.agent!r}; add it to contracts.AGENTS")
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"unknown event kind {self.kind!r}; one of {EVENT_KINDS}")

    def as_row(self) -> dict:
        """Shape written to the Convex `agent_events` table. `detail` is JSON like
        `audit.payload` so the structured payload stays flexible per agent."""
        import json
        row: dict = {
            "agent": self.agent,
            "kind": self.kind,
            "headline": self.headline,
            "detail": json.dumps(self.detail, default=str),
            "refs": list(self.refs),
            "ts_ms": self.ts_ms,
        }
        if self.cycle_id is not None:
            row["cycle_id"] = self.cycle_id
        return row


# ── Option-B forecast bridge (AGENT_TEAM_PLAN §6) ──────────────────────────────
# The ONE number the Researcher's forecast is allowed to push across the boundary
# into the decision. It can only SHRINK size, never enlarge — same one-way valve
# as the Historian's veto. The clamp + decay MATH lives in `core/risk/` (8.4) on
# plain floats so `/core` stays standalone; this is just the carried shape.

NEUTRAL_CONFIDENCE = 1.0          # "no opinion" — decays here so it can't throttle
DEFAULT_FORECAST_TTL_MS = 6 * 60 * 60 * 1000  # 6h; older than this → neutral


@dataclass
class ForecastState:
    """The Researcher's deterministic confidence for a symbol's current setup.

    `confidence` ∈ [FLOOR, 1.0] is read by the Risk Officer as a size multiplier
    (1.0 = full size, lower = shrink). A bad/stale forecast can only de-risk —
    locked decisions #1/#2/#6 all hold (see plan §6). The FLOOR clamp + the
    time-decay to NEUTRAL_CONFIDENCE are applied in `core/risk/` (8.4); this row
    is what gets snapshotted so sim/live replay the exact same value.
    """
    symbol: str
    confidence: float                           # in [0, 1]; 1.0 = neutral/no-shrink
    reason: str = ""                            # one-line why (e.g. "OI/price divergence")
    ttl_ms: int = DEFAULT_FORECAST_TTL_MS       # age past which it decays to neutral
    ts_ms: int = field(default_factory=_now_ms)

    def as_row(self) -> dict:
        """Shape written to the Convex `forecast_state` table (per-symbol)."""
        return {
            "symbol": self.symbol,
            "confidence": round(float(self.confidence), 4),
            "reason": self.reason,
            "ttl_ms": self.ttl_ms,
            "ts_ms": self.ts_ms,
        }


# ── User control surface (the only thing the user can WRITE, §7) ───────────────
# Three graduated stops. The PWA is the only writer; the supervisor + DecisionLoop
# are reactive readers. `trading_halted` mirrors the existing `config.halted`
# kill-switch (the hot path already reads config each cycle); the other two flags
# only ever quiet the Tier-1 team and NEVER touch trading (§7 table).

@dataclass
class AgentControl:
    """Singleton control doc (`agent_control` table, key='global')."""
    agents_paused: bool = False                 # quiet the whole Tier-1 advisory team
    paused_agents: list[str] = field(default_factory=list)  # finer-grained per-agent pause
    trading_halted: bool = False                # mirrors config.halted (Tier-0 kill)
    stop_response_id: Optional[str] = None      # cancel one in-flight agent action
    updated_by: str = USER
    ts_ms: int = field(default_factory=_now_ms)
    key: str = "global"

    def as_row(self) -> dict:
        row: dict = {
            "key": self.key,
            "agents_paused": self.agents_paused,
            "paused_agents": list(self.paused_agents),
            "trading_halted": self.trading_halted,
            "updated_by": self.updated_by,
            "ts_ms": self.ts_ms,
        }
        if self.stop_response_id is not None:
            row["stop_response_id"] = self.stop_response_id
        return row


# ── Failure matrix (AGENT_TEAM_PLAN §9.3) — data, not prose ────────────────────
# Governing rule: a Tier-1 agent failing must NEVER halt or distort a trade. Only
# Tier 0 may stop a cycle. Every failure is a VISIBLE agent_events row, never a
# silent swallow.

@dataclass(frozen=True)
class FailurePolicy:
    agent: str
    on_failure: str          # what the agent does when it errors
    hot_path_effect: str     # "none" for every Tier-1 agent; only Tier 0 may halt
    halts_trade: bool        # the machine-checkable invariant

    def __post_init__(self) -> None:
        # Enforce the governing rule at construction time: no Tier-1 policy may
        # ever claim it halts a trade.
        if self.agent in TIER1_AGENTS and self.halts_trade:
            raise ValueError(
                f"failure-matrix violation: Tier-1 agent {self.agent!r} must never halt a trade"
            )


FAILURE_MATRIX: dict[str, FailurePolicy] = {
    RESEARCHER: FailurePolicy(
        RESEARCHER,
        on_failure="log to channel; forecast_state decays to neutral (1.0)",
        hot_path_effect="none — trades at full deterministic size",
        halts_trade=False,
    ),
    HISTORIAN: FailurePolicy(
        HISTORIAN,
        on_failure="log; verdict defaults to AllowAll (no veto)",
        hot_path_effect="none — core decision stands",
        halts_trade=False,
    ),
    REFLECTOR: FailurePolicy(
        REFLECTOR,
        on_failure="log; queue lesson for retry",
        hot_path_effect="none — off-path",
        halts_trade=False,
    ),
    DREAMER: FailurePolicy(
        DREAMER,
        on_failure="log; queue for retry next night",
        hot_path_effect="none — off-path",
        halts_trade=False,
    ),
    COPILOT: FailurePolicy(
        COPILOT,
        on_failure='log; tell user "context unavailable"',
        hot_path_effect="none",
        halts_trade=False,
    ),
    # Tier 0 — the only tier allowed to stop trading.
    STRATEGIST: FailurePolicy(
        STRATEGIST,
        on_failure="halt that cycle, write audit, flip kill-switch if needed",
        hot_path_effect="halts the cycle (Tier-0)",
        halts_trade=True,
    ),
    RISK_OFFICER: FailurePolicy(
        RISK_OFFICER,
        on_failure="halt that cycle, write audit, flip kill-switch if needed",
        hot_path_effect="halts the cycle (Tier-0)",
        halts_trade=True,
    ),
    TRADE_HANDLER: FailurePolicy(
        TRADE_HANDLER,
        on_failure="halt that cycle, write audit, flip kill-switch if needed",
        hot_path_effect="halts the cycle (Tier-0)",
        halts_trade=True,
    ),
}


def failure_policy_for(agent: str) -> FailurePolicy:
    """The failure behaviour for an agent. Unknown agents default to the safest
    Tier-1 stance (log, never halt) so a new advisory agent can't accidentally
    take down the hot path before it's added to the matrix."""
    if agent in FAILURE_MATRIX:
        return FAILURE_MATRIX[agent]
    # SUPERVISOR / ORCHESTRATOR / USER are routing agents, not trade agents —
    # they observe and route; they don't trade, so they can't halt trading.
    return FailurePolicy(
        agent,
        on_failure="log to channel; continue (default Tier-1 safe stance)",
        hot_path_effect="none",
        halts_trade=False,
    )
