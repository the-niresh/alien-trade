"""Tests for agent/agents/orchestrator.py - Level-1 chains + Level-2 delegation."""
from __future__ import annotations

import pytest
from agent.agents import orchestrator
from agent.agents.orchestrator import (
    MAX_DELEGATION_DEPTH,
    delegate,
    is_agent_tool,
    agent_id_from_tool,
    run_chain,
)


# ── Stubs ────────────────────────────────────────────────────────────────────


class FakeSupervisor:
    """Stub supervisor: records calls and returns configurable state per kind."""

    def __init__(self, responses: dict | None = None, raise_on: set | None = None):
        self.calls: list[dict] = []
        self._responses = responses or {}  # kind -> state dict
        self._raise_on = raise_on or set()  # kinds that raise RuntimeError

    def handle(self, text: str, *, kind: str, symbol: str = "", cycle_id: str = "") -> dict:
        self.calls.append({"text": text, "kind": kind, "symbol": symbol})
        if kind in self._raise_on:
            raise RuntimeError(f"simulated failure for {kind}")
        return self._responses.get(kind, {"answer": f"result-{kind}", "analysis": f"hist-{kind}"})


class FakeRegistry:
    def __init__(self, agents: dict | None = None):
        self._agents = agents or {}

    def get(self, agent_id: str) -> dict | None:
        return self._agents.get(agent_id)


class RecBridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args): self.calls.append((path, args)); return "run1"
    def append_event(self, **kw): self.calls.append(("event", kw))


# ── Level-1 chain tests ───────────────────────────────────────────────────────


class TestRunChain:
    def test_unknown_chain_returns_error(self):
        sup = FakeSupervisor()
        out = run_chain("no_such_chain", supervisor=sup, symbol="ETH")
        assert out["ok"] is False
        assert "unknown chain" in out["error"]
        assert out["tool_calls"] == []
        assert out["events"] == []

    def test_setup_scorer_calls_three_nodes_in_order(self):
        responses = {
            "schedule": {"answer": "ETH momentum strong", "events": []},
            "user": {"analysis": "lost twice on FOMO-buy", "answer": "Avoid", "events": []},
        }
        sup = FakeSupervisor(responses=responses)
        out = run_chain("setup_scorer", supervisor=sup, symbol="ETH", goal="Score ETH setup")

        assert out["ok"] is True
        assert out["chain"] == "setup_scorer"
        # Three steps: researcher, historian, copilot
        tools = [tc["tool"] for tc in out["tool_calls"]]
        assert tools == ["researcher", "historian", "copilot"]

    def test_chain_threads_output_to_next_step(self):
        """Each step's output becomes the next step's input text."""
        sup = FakeSupervisor(responses={
            "schedule": {"answer": "ETH regime=trend", "events": []},
            "user": {"analysis": "no prior losses", "answer": "Enter long", "events": []},
        })
        run_chain("setup_scorer", supervisor=sup, symbol="ETH")

        # The second call (historian) should receive the researcher's output as text
        second_call = sup.calls[1]
        assert "ETH regime=trend" in second_call["text"]

    def test_degraded_tool_skips_but_chain_completes(self):
        """A step that raises degrades (records error) but the chain finishes."""
        responses = {
            "user": {"analysis": "no prior losses", "answer": "Enter long", "events": []},
        }
        sup = FakeSupervisor(responses=responses, raise_on={"schedule"})
        out = run_chain("setup_scorer", supervisor=sup, symbol="ETH")

        assert out["ok"] is True  # chain still completes
        assert out["tool_calls"][0]["tool"] == "researcher"
        assert "error" in out["tool_calls"][0]
        # Subsequent steps still ran
        assert len(out["tool_calls"]) == 3

    def test_chain_accumulates_events_from_all_steps(self):
        """Events from all nodes are collected into one flat list."""
        class EventSupervisor(FakeSupervisor):
            _counter = 0
            def handle(self, text, *, kind, symbol="", cycle_id=""):
                self._counter += 1
                return {"answer": "ok", "analysis": "ok", "lesson": "ok",
                        "events": [{"kind": "analysis", "n": self._counter}]}

        sup = EventSupervisor()
        out = run_chain("setup_scorer", supervisor=sup, symbol="ETH")
        assert len(out["events"]) == 3  # one per step

    def test_learn_from_trade_chain_runs_two_steps(self):
        responses = {
            "position_closed": {"lesson": "don't buy the top", "events": []},
            "user": {"analysis": "lesson stored", "events": []},
        }
        sup = FakeSupervisor(responses=responses)
        out = run_chain("learn_from_trade", supervisor=sup, symbol="ETH")

        assert out["ok"] is True
        tools = [tc["tool"] for tc in out["tool_calls"]]
        assert tools == ["reflector", "historian"]

    def test_combined_dict_has_one_entry_per_successful_step(self):
        responses = {
            "schedule": {"answer": "strong trend", "events": []},
            "user": {"analysis": "no prior losses", "answer": "go long", "events": []},
        }
        sup = FakeSupervisor(responses=responses)
        out = run_chain("setup_scorer", supervisor=sup, symbol="ETH")

        assert "researcher" in out["combined"]
        assert "historian" in out["combined"] or "copilot" in out["combined"]

    def test_summary_is_nonempty_on_success(self):
        responses = {
            "schedule": {"answer": "trend up", "events": []},
            "user": {"analysis": "no losses", "answer": "buy", "events": []},
        }
        sup = FakeSupervisor(responses=responses)
        out = run_chain("setup_scorer", supervisor=sup, symbol="ETH")
        assert len(out["summary"]) > 0


# ── Level-2 delegation tests ─────────────────────────────────────────────────


class TestDelegate:
    def _fake_run(self, rec, *, twak, skills, bridge, client, loop_fn=None):
        return {"ok": True, "summary": f"result from {rec['name']}", "tool_calls": []}

    def _make_runner_patch(self):
        """Patch runner.run_agent with a stub via loop_fn injection."""
        return lambda rec, **kw: {"ok": True, "summary": f"delegated to {rec['name']}", "tool_calls": []}

    def test_delegate_runs_sub_agent_successfully(self, monkeypatch):
        reg = FakeRegistry({"agent-b": {"_id": "agent-b", "name": "B",
                                        "goal": "g", "allowed_tools": [], "mode": "paper"}})

        def fake_run(rec, *, twak, skills, bridge, client, loop_fn=None):
            return {"ok": True, "summary": "B ran", "tool_calls": []}

        monkeypatch.setattr("agent.agents.runner.run_agent", fake_run)
        out = delegate("agent-a", "agent-b", registry=reg, twak=None, skills=None,
                       bridge=RecBridge(), client=None)
        assert out["ok"] is True
        assert "B ran" in out["summary"]

    def test_cycle_detection_direct(self, monkeypatch):
        """A→B→A is rejected immediately."""
        reg = FakeRegistry({"agent-a": {"_id": "agent-a", "name": "A",
                                        "goal": "g", "allowed_tools": [], "mode": "paper"}})
        out = delegate("agent-a", "agent-a", registry=reg,
                       delegation_path=["agent-a"],
                       twak=None, skills=None, bridge=RecBridge(), client=None)
        assert out["ok"] is False
        assert "cycle" in out["error"]

    def test_cycle_detection_transitive(self, monkeypatch):
        """A→B→A (from B's perspective) is rejected."""
        reg = FakeRegistry({})
        out = delegate("agent-b", "agent-a", registry=reg,
                       delegation_path=["agent-a", "agent-b"],
                       twak=None, skills=None, bridge=RecBridge(), client=None)
        assert out["ok"] is False
        assert "cycle" in out["error"]

    def test_depth_cap_rejects_at_limit(self, monkeypatch):
        reg = FakeRegistry({"agent-c": {"_id": "agent-c", "name": "C",
                                        "goal": "g", "allowed_tools": [], "mode": "paper"}})
        out = delegate("agent-b", "agent-c", registry=reg,
                       depth=MAX_DELEGATION_DEPTH,
                       twak=None, skills=None, bridge=RecBridge(), client=None)
        assert out["ok"] is False
        assert "depth cap" in out["error"]

    def test_depth_cap_allows_just_below_limit(self, monkeypatch):
        reg = FakeRegistry({"agent-c": {"_id": "agent-c", "name": "C",
                                        "goal": "g", "allowed_tools": [], "mode": "paper"}})

        def fake_run(rec, *, twak, skills, bridge, client, loop_fn=None):
            return {"ok": True, "summary": "ran", "tool_calls": []}

        monkeypatch.setattr("agent.agents.runner.run_agent", fake_run)
        out = delegate("agent-b", "agent-c", registry=reg,
                       depth=MAX_DELEGATION_DEPTH - 1,
                       twak=None, skills=None, bridge=RecBridge(), client=None)
        assert out["ok"] is True

    def test_not_found_returns_error(self):
        reg = FakeRegistry({})  # empty
        out = delegate("agent-a", "agent-z", registry=reg,
                       twak=None, skills=None, bridge=RecBridge(), client=None)
        assert out["ok"] is False
        assert "not found" in out["error"]

    def test_registry_exception_returns_error(self):
        class BrokenRegistry:
            def get(self, _): raise RuntimeError("db down")

        out = delegate("agent-a", "agent-b", registry=BrokenRegistry(),
                       twak=None, skills=None, bridge=RecBridge(), client=None)
        assert out["ok"] is False
        assert "not found" in out["error"]


# ── Tool-name helpers ─────────────────────────────────────────────────────────


class TestAgentToolHelpers:
    def test_is_agent_tool_true_for_prefixed(self):
        assert is_agent_tool("agent:abc123") is True

    def test_is_agent_tool_false_for_regular(self):
        assert is_agent_tool("get_price") is False
        assert is_agent_tool("cmc_market_skill") is False

    def test_agent_id_from_tool_extracts_id(self):
        assert agent_id_from_tool("agent:abc123") == "abc123"
        assert agent_id_from_tool("agent:") == ""


# ── Template tests ────────────────────────────────────────────────────────────


class TestTemplates:
    def test_setup_scorer_template_is_valid(self):
        from agent.agents.templates import setup_scorer
        spec = setup_scorer("ETH")
        assert spec["name"] == "ETH-SetupScorer"
        assert "ETH" in spec["goal"]
        assert spec["mode"] == "paper"

    def test_daily_brief_template_injects_agent_tools(self):
        from agent.agents.templates import daily_brief
        spec = daily_brief(["id1", "id2"])
        tools = spec["allowed_tools"]
        assert "agent:id1" in tools
        assert "agent:id2" in tools

    def test_daily_brief_empty_sub_agents(self):
        from agent.agents.templates import daily_brief
        spec = daily_brief()
        assert spec["allowed_tools"] == []

    def test_spec_allows_agent_id_tools(self):
        from agent.agents.spec import validate_agent_spec
        spec = validate_agent_spec({
            "name": "Daily",
            "goal": "brief me",
            "allowed_tools": ["get_price", "agent:someconvexid123"],
            "mode": "paper",
        })
        assert "agent:someconvexid123" in spec["allowed_tools"]
