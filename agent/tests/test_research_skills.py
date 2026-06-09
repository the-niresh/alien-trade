"""
Research agent ↔ SkillHub wiring. The AutoResearch agent pulls curated CMC skill
reads into its context so digests are grounded in the orthogonal signals (funding
/sentiment/regime) price can't show. Pins: the nested skill envelope is parsed to
one compact line, offline/error/empty yields nothing, and a failing skill is
advisory (guarded, never breaks the cycle). Hermetic — fake hub, no network.
"""
from __future__ import annotations

import json

from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.research import ResearchAgent, _skill_brief


def _envelope(summary: str, status: str = "ok") -> dict:
    """Mirror the live hub shape: result.output is a JSON string whose
    result.data.summary holds the evidence-pack headline."""
    inner = {"skill": "x", "result": {"type": "evidence_pack",
             "data": {"status": status, "summary": summary}}}
    return {"result": {"output": json.dumps(inner), "success": True,
                       "exitCode": 0, "error": ""}, "executionMeta": {}}


class _FakeHub:
    def __init__(self, enabled=True, payload=None, raise_on=None):
        self._enabled = enabled
        self._payload = payload if payload is not None else _envelope("baseline read")
        self.raise_on = raise_on
        self.calls: list[str] = []

    @property
    def enabled(self):
        return self._enabled

    def run_curated(self, key, ctx=None):
        self.calls.append(key)
        if self.raise_on and key == self.raise_on:
            raise RuntimeError("skill blew up")
        return self._payload


def _agent(**kw):
    return ResearchAgent(llm=ClaudeClient(api_key=""), symbol="ETH", **kw)


# ── _skill_brief parsing ────────────────────────────────────────────────────

def test_skill_brief_parses_nested_output():
    line = _skill_brief("market_regime", _envelope("Market regime is mixed_transition."))
    assert line == "[market_regime] Market regime is mixed_transition."


def test_skill_brief_flags_non_ok_status():
    line = _skill_brief("funding_regime", _envelope("Funding history thin.", status="blocked"))
    assert line.startswith("[funding_regime] Funding history thin.")
    assert "status=blocked" in line


def test_skill_brief_empty_on_offline_error_or_missing():
    assert _skill_brief("k", {"status": "offline", "unique_name": "x"}) == ""
    assert _skill_brief("k", {"status": "error", "error": "boom"}) == ""
    assert _skill_brief("k", _envelope("")) == ""           # no summary text
    assert _skill_brief("k", {"garbage": 1}) == ""


# ── _skill_evidence integration ──────────────────────────────────────────────

def test_skill_evidence_collects_one_line_per_skill():
    hub = _FakeHub(payload=_envelope("read for the symbol"))
    agent = _agent(skills=hub, skill_keys=("market_regime", "funding_regime"))
    lines = agent._skill_evidence()
    assert len(lines) == 2
    assert all(ln.endswith("read for the symbol") for ln in lines)
    assert hub.calls == ["market_regime", "funding_regime"]


def test_skill_evidence_empty_when_offline():
    agent = _agent(skills=_FakeHub(enabled=False))
    assert agent._skill_evidence() == []


def test_skill_evidence_empty_when_no_hub():
    assert _agent(skills=None)._skill_evidence() == []


def test_skill_evidence_guards_individual_failures():
    hub = _FakeHub(payload=_envelope("ok read"), raise_on="funding_regime")
    agent = _agent(skills=hub, skill_keys=("market_regime", "funding_regime", "kol_sentiment"))
    lines = agent._skill_evidence()
    # the failing skill is skipped; the others still contribute; no exception
    assert len(lines) == 2
    assert hub.calls == ["market_regime", "funding_regime", "kol_sentiment"]
