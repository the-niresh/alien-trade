"""
LangGraph supervisor (2-node scaffold). Pins: single-entry routing (user→co_pilot,
history-intent→historian, events→historian), each node emits exactly one AgentEvent
to the channel, the Pause-Agents control short-circuits Tier-1 nodes without running
them, and historian summarises Vector recall. Hermetic — fake Second Brain + bridge.
"""
from __future__ import annotations

from types import SimpleNamespace

from agent.graph.contracts import (
    COPILOT, HISTORIAN, KIND_ANALYSIS, KIND_CONTROL, KIND_HANDOFF, KIND_OBSERVATION,
    REFLECTOR, RESEARCHER, AgentControl,
)
from agent.graph.supervisor import Supervisor, route
from agent.secondbrain.schema import KIND_REFLECTION, MemoryHit


# ── fakes ──────────────────────────────────────────────────────────────────────

class _FakeVector:
    def __init__(self, hits=None):
        self._hits = hits or []
        self.queries = []

    def query(self, text, top_k=5, kind=None):
        self.queries.append((text, kind))
        return self._hits


class _FakeCoPilot:
    def __init__(self):
        self.asked = []

    def ask(self, q, **kw):
        self.asked.append(q)
        return {"answer": f"answer:{q}", "grounded": True, "skills": [], "sources": []}


class _FakeReflectionWriter:
    def __init__(self):
        self.calls = []

    def reflect(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(lesson="Avoid adding longs in chop.", cycle_id=kw.get("cycle_id"))


class _FakeResearchSup:
    def __init__(self):
        self.ran = 0

    def _fetch_history(self):
        return []   # empty; confidence_from_history([]) returns 1.0

    def run_cycle(self, history=None, **kw):
        self.ran += 1
        return [SimpleNamespace(id="d1", question="what defines this regime?")]


class _FakeSB:
    def __init__(self, hits=None):
        self.vector = _FakeVector(hits)
        self._cp = _FakeCoPilot()
        self.reflection_writer = _FakeReflectionWriter()
        self._research = _FakeResearchSup()

    def copilot(self):
        return self._cp

    def research(self, symbol="ETH"):
        return self._research


class _FakeBridge:
    def __init__(self, paused=False):
        self._paused = paused
        self.events = []

    def get_agent_control(self):
        return AgentControl(agents_paused=self._paused)

    def emit_event(self, event):
        self.events.append(event)

    def set_forecast_state(self, fs):
        pass


def _sup(hits=None, paused=False):
    sb = _FakeSB(hits)
    bridge = _FakeBridge(paused=paused)
    return Supervisor(sb, bridge=bridge), sb, bridge


# ── routing ────────────────────────────────────────────────────────────────────

def test_route_user_question_to_copilot():
    assert route({"kind": "user", "input": "what regime are we in?"}) == "co_pilot"


def test_route_history_intent_to_historian():
    assert route({"kind": "user", "input": "have we lost on this setup before?"}) == "historian"


def test_route_schedule_tick_to_researcher():
    assert route({"kind": "research_tick"}) == "researcher"


def test_route_trade_close_to_reflector():
    assert route({"kind": "position_closed", "input": "ETH closed -2%"}) == "reflector"


def test_route_other_event_to_historian():
    assert route({"kind": "some_other_event"}) == "historian"


# ── co-pilot node ──────────────────────────────────────────────────────────────

def test_user_question_runs_copilot_and_emits_event():
    sup, sb, bridge = _sup()
    out = sup.handle("what is the funding regime?")
    assert out["route"] == "co_pilot"
    assert out["answer"] == "answer:what is the funding regime?"
    assert sb._cp.asked == ["what is the funding regime?"]
    assert len(bridge.events) == 1
    evt = bridge.events[0]
    assert evt.agent == COPILOT and evt.kind == KIND_ANALYSIS


# ── historian node ───────────────────────────────────────────────────────────

def test_historian_summarises_vector_hits():
    hits = [MemoryHit(id="r1", score=0.9, text="Lost on overheated longs in chop.",
                      metadata={"kind": KIND_REFLECTION})]
    sup, sb, bridge = _sup(hits=hits)
    out = sup.handle("have we seen this before?", symbol="ETH")
    assert out["route"] == "historian"
    assert "1 past lesson" in out["analysis"]
    assert sb.vector.queries and sb.vector.queries[-1][1] == KIND_REFLECTION
    assert bridge.events[0].agent == HISTORIAN
    assert bridge.events[0].refs == ["r1"]


def test_historian_handles_no_history():
    sup, _, bridge = _sup(hits=[])
    out = sup.handle("have we seen this setup before?", symbol="ETH")  # read path, no hits
    assert out["route"] == "historian"
    assert "No prior lessons" in out["analysis"]
    assert bridge.events[0].detail["n_hits"] == 0


# ── researcher node ──────────────────────────────────────────────────────────

def test_research_tick_runs_researcher_and_emits():
    sup, sb, bridge = _sup()
    out = sup.handle("", kind="research_tick", symbol="ETH")
    assert out["route"] == "researcher"
    assert sb._research.ran == 1
    assert out["digests"] == ["d1"]
    assert bridge.events[0].agent == RESEARCHER and bridge.events[0].kind == KIND_OBSERVATION


# ── reflector → historian.write chain ─────────────────────────────────────────

def test_trade_close_reflects_then_historian_confirms():
    sup, sb, bridge = _sup()
    out = sup.handle("ETH position closed", kind="position_closed", symbol="ETH",
                     cycle_id="ETH-123",
                     payload={"trade_id": "t1", "regime": "chop", "side": "sell",
                              "signals": {"s1": 0.2}, "realized_pnl": -42.0,
                              "timestamp_ms": 100})
    # reflector ran with the payload, then handed to historian
    assert sb.reflection_writer.calls[-1]["realized_pnl"] == -42.0
    assert out["route"] == "historian"                 # final node
    assert out["lesson"] == "Avoid adding longs in chop."
    kinds = [(e.agent, e.kind) for e in bridge.events]
    assert (REFLECTOR, KIND_HANDOFF) in kinds          # reflector emitted
    assert (HISTORIAN, KIND_ANALYSIS) in kinds         # historian confirmed the write
    assert "Lesson recorded to memory" in out["analysis"]


# ── pause control ──────────────────────────────────────────────────────────────

def test_pause_short_circuits_copilot():
    sup, sb, bridge = _sup(paused=True)
    out = sup.handle("what is the regime?")
    assert sb._cp.asked == []                       # co-pilot NOT run
    assert bridge.events[0].kind == KIND_CONTROL
    assert "paused" in bridge.events[0].headline.lower()


def test_pause_short_circuits_historian():
    sup, sb, bridge = _sup(hits=[MemoryHit(id="x", score=1.0)], paused=True)
    out = sup.handle("have we lost before?")
    assert sb.vector.queries == []                  # no Vector recall when paused
    assert bridge.events[0].agent == HISTORIAN and bridge.events[0].kind == KIND_CONTROL


def test_pause_short_circuits_researcher():
    sup, sb, bridge = _sup(paused=True)
    sup.handle("", kind="research_tick", symbol="ETH")
    assert sb._research.ran == 0                     # AutoResearch NOT run
    assert bridge.events[0].agent == RESEARCHER and bridge.events[0].kind == KIND_CONTROL


def test_pause_short_circuits_reflector_and_historian():
    sup, sb, bridge = _sup(paused=True)
    sup.handle("closed", kind="position_closed", payload={"realized_pnl": -1.0})
    assert sb.reflection_writer.calls == []          # no reflection written when paused
    # reflector control event, then historian (also paused) control event
    assert (REFLECTOR, KIND_CONTROL) in [(e.agent, e.kind) for e in bridge.events]


# ── channel emission shape ─────────────────────────────────────────────────────

def test_emitted_event_serialises_to_channel_row():
    import json
    sup, _, bridge = _sup()
    sup.handle("what regime are we in?")
    row = bridge.events[0].as_row()
    json.dumps(row)                                 # must be channel-writable
    assert row["agent"] == COPILOT and row["kind"] == KIND_ANALYSIS
    assert isinstance(row["detail"], str)            # JSON blob


# ── hop budget ────────────────────────────────────────────────────────────────

def test_budget_exceeded_emits_control_event():
    from agent.graph.supervisor import MAX_HOPS
    sup, _, bridge = _sup()
    state = {"hops": MAX_HOPS, "cycle_id": "test-cycle"}
    result = sup._budget_exceeded(RESEARCHER, state)
    assert result["route"] == RESEARCHER
    assert result["hops"] == 1
    assert bridge.events[-1].kind == KIND_CONTROL
    assert "budget exceeded" in bridge.events[-1].headline.lower()


# ── research-tick dedupe ──────────────────────────────────────────────────────

def test_researcher_dedupe_skips_within_90min():
    import time
    sup, sb, bridge = _sup()
    sup._last_research_ts["ETH"] = time.time() - 60  # 1 minute ago
    out = sup.handle("", kind="research_tick", symbol="ETH")
    assert sb._research.ran == 0                       # NOT run
    assert out["route"] == "researcher"
    assert bridge.events[0].agent == RESEARCHER
    assert bridge.events[0].kind == KIND_CONTROL
    assert "skipped" in bridge.events[0].headline.lower()


def test_researcher_runs_when_window_expired():
    import time
    sup, sb, bridge = _sup()
    sup._last_research_ts["ETH"] = time.time() - 91 * 60  # 91 min ago (stale)
    out = sup.handle("", kind="research_tick", symbol="ETH")
    assert sb._research.ran == 1                       # DID run
    assert out["route"] == "researcher"
    assert bridge.events[0].kind == KIND_OBSERVATION


def test_researcher_first_call_always_runs():
    sup, sb, bridge = _sup()
    assert "ETH" not in sup._last_research_ts         # fresh instance
    out = sup.handle("", kind="research_tick", symbol="ETH")
    assert sb._research.ran == 1
    assert "ETH" in sup._last_research_ts             # timestamp recorded


def test_researcher_dedupe_per_symbol():
    import time
    sup, sb, bridge = _sup()
    sup._last_research_ts["ETH"] = time.time() - 60  # ETH: recent
    # CAKE has no entry → should run
    out = sup.handle("", kind="research_tick", symbol="CAKE")
    assert sb._research.ran == 1


# ── reflection dedupe ─────────────────────────────────────────────────────────

def test_reflector_dedupe_skips_same_cycle_id():
    sup, sb, bridge = _sup()
    sup._reflected_cycle_ids.add("ETH-123")
    out = sup.handle("ETH closed", kind="position_closed", cycle_id="ETH-123",
                     payload={"realized_pnl": -10.0})
    assert sb.reflection_writer.calls == []            # NOT called
    assert bridge.events[0].agent == REFLECTOR
    assert bridge.events[0].kind == KIND_CONTROL
    assert "already reflected" in bridge.events[0].headline.lower()


def test_reflector_runs_for_new_cycle_id():
    sup, sb, bridge = _sup()
    out = sup.handle("ETH closed", kind="position_closed", cycle_id="ETH-456",
                     payload={"trade_id": "t1", "regime": "chop", "side": "sell",
                              "signals": {}, "realized_pnl": -5.0, "timestamp_ms": 1})
    assert sb.reflection_writer.calls                  # called
    assert "ETH-456" in sup._reflected_cycle_ids       # recorded


def test_reflector_idempotent_on_repeated_calls():
    """Two calls with the same cycle_id → reflection written once."""
    sup, sb, bridge = _sup()
    payload = {"trade_id": "t1", "regime": "chop", "side": "sell",
               "signals": {}, "realized_pnl": -5.0, "timestamp_ms": 1}
    sup.handle("closed", kind="position_closed", cycle_id="ETH-789", payload=payload)
    sup.handle("closed", kind="position_closed", cycle_id="ETH-789", payload=payload)
    # Only one reflection should have been written
    assert len(sb.reflection_writer.calls) == 1


# ── node failure visibility ───────────────────────────────────────────────────

def test_researcher_failure_emits_failure_event():
    class _BrokenResearch:
        def _fetch_history(self): return []
        def run_cycle(self, **kw): raise RuntimeError("network timeout")

    sb = _FakeSB()
    sb._research = _BrokenResearch()
    bridge = _FakeBridge()
    sup = Supervisor(sb, bridge=bridge)
    out = sup.handle("", kind="research_tick", symbol="ETH")
    assert out["route"] == "researcher"
    fail_evts = [e for e in bridge.events if e.agent == RESEARCHER and e.kind == KIND_CONTROL]
    assert fail_evts, "expected a failure event from the researcher"
    assert "failed" in fail_evts[0].headline.lower()
    assert "RuntimeError" in fail_evts[0].headline


def test_reflector_failure_emits_failure_event():
    class _BrokenWriter:
        def reflect(self, **kw): raise ValueError("db write failed")

    sb = _FakeSB()
    sb.reflection_writer = _BrokenWriter()
    bridge = _FakeBridge()
    sup = Supervisor(sb, bridge=bridge)
    out = sup.handle("closed", kind="position_closed", cycle_id="new-cycle",
                     payload={"realized_pnl": -1.0})
    fail_evts = [e for e in bridge.events if e.agent == REFLECTOR and e.kind == KIND_CONTROL]
    assert fail_evts
    assert "failed" in fail_evts[0].headline.lower()


def test_historian_failure_emits_failure_event():
    class _BrokenVector:
        def query(self, *a, **kw): raise OSError("upstash unreachable")

    sb = _FakeSB()
    sb.vector = _BrokenVector()
    bridge = _FakeBridge()
    sup = Supervisor(sb, bridge=bridge)
    out = sup.handle("have we seen this setup before?", symbol="ETH")
    assert out["route"] == "historian"
    fail_evts = [e for e in bridge.events if e.agent == HISTORIAN and e.kind == KIND_CONTROL]
    assert fail_evts
    assert "failed" in fail_evts[0].headline.lower()


def test_copilot_failure_emits_failure_event():
    class _BrokenCoPilot:
        def ask(self, q, **kw): raise ConnectionError("anthropic 503")

    sb = _FakeSB()
    sb._cp = _BrokenCoPilot()
    bridge = _FakeBridge()
    sup = Supervisor(sb, bridge=bridge)
    out = sup.handle("what regime are we in?")
    assert out["route"] == "co_pilot"
    fail_evts = [e for e in bridge.events if e.agent == COPILOT and e.kind == KIND_CONTROL]
    assert fail_evts
    assert "failed" in fail_evts[0].headline.lower()


# ── hops counter ─────────────────────────────────────────────────────────────

def test_hops_incremented_per_node():
    """Each node must return hops: 1 so LangGraph accumulates the budget counter."""
    sup, _, bridge = _sup()
    out = sup.handle("what regime are we in?")
    # co_pilot node ran → 1 hop
    assert out.get("hops", 0) == 1


def test_hops_two_for_reflector_chain():
    """reflector + historian = 2 hops."""
    sup, _, bridge = _sup()
    out = sup.handle("ETH closed", kind="position_closed", cycle_id="new-1",
                     payload={"trade_id": "t1", "regime": "chop", "side": "sell",
                              "signals": {}, "realized_pnl": -5.0, "timestamp_ms": 1})
    assert out.get("hops", 0) == 2
