"""
Co-pilot ↔ SkillHub wiring (Tier-2 dynamic). For open-ended questions the co-pilot
discovers a skill via find_skill, runs it with best-effort params from the returned
schema, and folds the evidence into its answer context. Pins: schema→params
building, symbol detection, the discover→execute→summarise flow, guarding, and
offline-first. Hermetic - fake hub, no network/LLM.
"""
from __future__ import annotations

import json

from agent.secondbrain.copilot import CoPilot
from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.vector import VectorStore
from agent.skills import detect_symbol, params_from_schema, route_curated


def _envelope(summary: str) -> dict:
    inner = {"result": {"data": {"status": "ok", "summary": summary}}}
    return {"result": {"output": json.dumps(inner), "success": True}, "executionMeta": {}}


# A question with no curated trigger words → forces the dynamic fallback path.
_NONCURATED_Q = "Is BTC decoupling from Nasdaq and gold lately?"


class _FakeHub:
    """Fake SkillHub covering both tiers: run_curated (Tier 1) + find_skill/
    execute_skill (Tier 2). Records which path was exercised."""
    def __init__(self, enabled=True, candidates=None, payload=None):
        self._enabled = enabled
        self._candidates = candidates if candidates is not None else [{
            "uniqueName": "decode_macro_event_impact",
            "inputSchema": {"type": "object",
                            "properties": {"event": {"type": "string"},
                                           "time_window": {"type": "string", "default": "30d"}},
                            "required": ["event"]},
        }]
        self._payload = payload if payload is not None else _envelope("BTC is trading risk-on.")
        self.executed: list[tuple[str, dict]] = []
        self.curated_calls: list[str] = []

    @property
    def enabled(self):
        return self._enabled

    def find_skill(self, query, top_k=5):
        return self._candidates if self._enabled else []

    def execute_skill(self, unique_name, parameters=None):
        self.executed.append((unique_name, parameters or {}))
        return self._payload if self._enabled else {"status": "offline"}

    def run_curated(self, key, ctx=None):
        self.curated_calls.append(key)
        return self._payload


def _pilot(hub):
    return CoPilot(vector=VectorStore(), llm=ClaudeClient(api_key=""), skills=hub)


# ── schema → params ────────────────────────────────────────────────────────

def test_params_fills_only_identity_and_required():
    schema = {"properties": {"symbol": {"type": "string"},
                             "window": {"type": "string", "default": "30d"},
                             "direction": {"enum": ["long", "short", "neutral"]}},
              "required": ["symbol"]}
    p = params_from_schema(schema, "funding on ETH?", "ETH")
    assert p == {"symbol": "ETH"}          # identity/required only; optionals → server


def test_required_enum_uses_default_or_first():
    schema = {"properties": {"window": {"enum": ["1h", "4h", "24h"], "default": "4h"}},
              "required": ["window"]}
    assert params_from_schema(schema, "q", "ETH")["window"] == "4h"


def test_params_fills_query_and_claim_fields():
    schema = {"properties": {"query": {"type": "string"}, "symbol": {"type": "string"}},
              "required": ["query", "symbol"]}
    p = params_from_schema(schema, "is BTC overheated?", "BTC")
    assert p["symbol"] == "BTC"
    assert "BTC" in p["query"] or "overheated" in p["query"]


def test_detect_symbol():
    assert detect_symbol("what's funding on ETH right now") == "ETH"
    assert detect_symbol("is the market overheated") == "BTC"   # default


# ── curated routing (Tier 1) ──────────────────────────────────────────────────

def test_route_curated_maps_keywords():
    assert "funding_regime" in route_curated("what is ETH funding doing?")
    assert "kol_sentiment" in route_curated("social sentiment on PEPE?")
    assert route_curated("is BTC decoupling from Nasdaq?") == []   # long tail


def test_funding_question_uses_curated_not_dynamic():
    hub = _FakeHub()
    lines = _pilot(hub)._skill_evidence("where is ETH funding carry hottest?")
    assert lines                                  # got curated evidence
    assert hub.curated_calls                       # Tier 1 used
    assert hub.executed == []                      # dynamic NOT touched


# ── dynamic fallback (Tier 2) ─────────────────────────────────────────────────

def test_noncurated_question_uses_dynamic_path():
    hub = _FakeHub()
    lines = _pilot(hub)._skill_evidence(_NONCURATED_Q)
    assert lines == ["[decode_macro_event_impact] BTC is trading risk-on."]
    name, params = hub.executed[-1]
    assert name == "decode_macro_event_impact"
    assert params["event"]                         # required string filled
    assert hub.curated_calls == []                 # no curated match → Tier 2 only


def test_skill_evidence_offline_returns_empty():
    assert _pilot(_FakeHub(enabled=False))._skill_evidence("anything") == []


def test_dynamic_no_candidates_returns_empty():
    assert _pilot(_FakeHub(candidates=[]))._skill_evidence(_NONCURATED_Q) == []


def test_dynamic_skips_unusable_result():
    # execute returns a payload with no summary → skipped, no crash
    hub = _FakeHub(payload={"result": {"output": json.dumps({"result": {"data": {}}})}})
    assert _pilot(hub)._skill_evidence(_NONCURATED_Q) == []


def test_build_prompt_includes_skill_block():
    prompt = CoPilot._build_prompt("q?", [], "", ["[skill_x] reads constructive"])
    assert "LIVE CMC SKILLS:" in prompt
    assert "[skill_x] reads constructive" in prompt


def test_ask_marks_grounded_on_skill_evidence_only():
    # no memory, no live state - skill evidence alone should ground the answer
    out = _pilot(_FakeHub()).ask("where is ETH funding carry hottest?")
    assert out["grounded"] is True
    assert out["skills"]
