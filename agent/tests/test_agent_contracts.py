"""
Contracts-first guarantees for the agent-team layer (AGENT_TEAM_PLAN §9.2/§9.3).

These tests defend the two things contracts.py exists to keep:
  - every cross-boundary shape is here and serialises to its Convex columns;
  - the failure matrix's governing rule is machine-true: NO Tier-1 agent can
    ever halt a trade.
"""
from __future__ import annotations

import json

import pytest

from agent.graph import contracts as C


# ── Roster + tiers ─────────────────────────────────────────────────────────────

def test_tier0_is_exactly_the_hot_path():
    assert C.TIER0_AGENTS == {C.STRATEGIST, C.RISK_OFFICER, C.TRADE_HANDLER}
    for a in C.TIER0_AGENTS:
        assert C.is_tier0(a) and C.tier_of(a) == 0


def test_tier1_is_advisory_and_never_tier0():
    assert C.HISTORIAN in C.TIER1_AGENTS and C.RESEARCHER in C.TIER1_AGENTS
    for a in C.TIER1_AGENTS:
        assert not C.is_tier0(a) and C.tier_of(a) == 1


def test_orchestrator_and_user_are_neither_tier():
    assert C.tier_of(C.ORCHESTRATOR) is None
    assert C.tier_of(C.USER) is None


# ── AgentEvent row ─────────────────────────────────────────────────────────────

def test_agent_event_row_matches_convex_columns():
    ev = C.AgentEvent(
        agent=C.HISTORIAN, kind=C.KIND_VERDICT,
        headline="Historian: 3 past losses on this setup -> shrink 30%",
        cycle_id="cyc-1", detail={"losses": 3, "rate": 0.5}, refs=["refl-9"],
    )
    row = ev.as_row()
    assert set(row) == {"agent", "kind", "headline", "detail", "refs", "ts_ms", "cycle_id"}
    assert json.loads(row["detail"]) == {"losses": 3, "rate": 0.5}  # detail is JSON


def test_agent_event_omits_cycle_id_when_absent():
    ev = C.AgentEvent(agent=C.USER, kind=C.KIND_CONTROL, headline="User paused the agents")
    assert "cycle_id" not in ev.as_row()


def test_agent_event_rejects_unknown_agent_or_kind():
    with pytest.raises(ValueError):
        C.AgentEvent(agent="Wizard", kind=C.KIND_ACTION, headline="x")
    with pytest.raises(ValueError):
        C.AgentEvent(agent=C.STRATEGIST, kind="gossip", headline="x")


# ── Forecast + control rows ────────────────────────────────────────────────────

def test_forecast_state_row_matches_convex_columns():
    fs = C.ForecastState(symbol="BNB", confidence=0.34567, reason="OI/price divergence")
    row = fs.as_row()
    assert set(row) == {"symbol", "confidence", "reason", "ttl_ms", "ts_ms"}
    assert row["confidence"] == 0.3457  # rounded for reproducible parity
    assert C.NEUTRAL_CONFIDENCE == 1.0  # decayed/failed forecast can't throttle


def test_agent_control_row_matches_convex_columns():
    ac = C.AgentControl(agents_paused=True, paused_agents=[C.RESEARCHER])
    row = ac.as_row()
    assert set(row) == {"key", "agents_paused", "paused_agents", "trading_halted", "updated_by", "ts_ms"}
    assert "stop_response_id" not in row  # omitted when None
    assert C.AgentControl(stop_response_id="m1").as_row()["stop_response_id"] == "m1"


# ── Failure matrix - the governing invariant ────────────────────────────────────

def test_no_tier1_agent_can_halt_a_trade():
    for agent, policy in C.FAILURE_MATRIX.items():
        if agent in C.TIER1_AGENTS:
            assert policy.halts_trade is False
            assert policy.hot_path_effect.startswith("none")


def test_only_tier0_agents_halt_trades():
    halting = {a for a, p in C.FAILURE_MATRIX.items() if p.halts_trade}
    assert halting == C.TIER0_AGENTS


def test_constructing_a_tier1_halting_policy_is_rejected():
    with pytest.raises(ValueError):
        C.FailurePolicy(C.RESEARCHER, on_failure="boom", hot_path_effect="halt", halts_trade=True)


def test_unknown_agent_defaults_to_safe_tier1_stance():
    p = C.failure_policy_for("BrandNewAgent")
    assert p.halts_trade is False and p.hot_path_effect == "none"


# ── Re-export site (one canonical import home, §9.2) ───────────────────────────

def test_existing_payloads_are_reexported():
    assert C.AvoidanceVerdict and C.ResearchDigest and C.Reflection
    assert C.SentimentReading and C.MemoryHit
