"""8.13 — Tier-1 self-eval rubrics: Researcher / Co-pilot / Reflector."""
from __future__ import annotations
from unittest.mock import MagicMock, call

import pytest

from agent.secondbrain.schema import Reflection, ResearchDigest
from agent.secondbrain.reflection import ReflectionWriter, _is_generic
from agent.secondbrain.research import ResearchAgent
from agent.secondbrain.copilot import CoPilot, _is_uncited
from agent.secondbrain.schema import MemoryHit
from agent.secondbrain.vector import VectorStore
from agent.secondbrain.llm import ClaudeClient


# ── _is_generic helper ────────────────────────────────────────────────────────

def test_is_generic_short_lesson():
    assert _is_generic("avoid this")

def test_is_generic_no_regime_no_signal_no_number():
    assert _is_generic("The market moved against us so we should be careful next time.")

def test_is_generic_has_regime_and_number():
    assert not _is_generic("Avoid buy in CHOP regime when S1 signal -0.45 (loss $15).")

def test_is_generic_has_signal_and_number():
    assert not _is_generic("S2 funding -0.02 → avoid long; realized $-12.")

def test_is_generic_regime_but_no_number():
    assert _is_generic("In trend regime avoid momentum entries that look like this.")

def test_is_generic_empty():
    assert _is_generic("")


# ── Reflector self-check ──────────────────────────────────────────────────────

def _make_reflection_writer(complete_returns=None, enabled=True):
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = enabled
    if complete_returns is None:
        complete_returns = [MagicMock(text="In CHOP S1=-0.3 avoid buy (loss $10).", stub=False)]
    llm.complete.side_effect = complete_returns
    vector = MagicMock(spec=VectorStore)
    vector.upsert.return_value = True
    return ReflectionWriter(vector=vector, llm=llm), llm


def _refl(**kw):
    defaults = dict(cycle_id="c1", trade_id="t1", timestamp_ms=0, regime="chop",
                    side="buy", signals={"momentum": -0.3}, outcome_pnl_usd=-10.0,
                    setup_key="buy in chop regime driven by momentum signal")
    defaults.update(kw)
    return Reflection(**defaults)


def test_reflector_quality_normal_lesson():
    writer, llm = _make_reflection_writer(complete_returns=[
        MagicMock(text="In CHOP regime with S1=-0.30, avoid buy; loss $10.00.", stub=False),
    ])
    r = _refl()
    r.lesson = "In CHOP regime with S1=-0.30, avoid buy; loss $10.00."
    quality = writer._eval_quality(r)
    assert quality == ""  # passes rubric immediately


def test_reflector_quality_generic_first_retry_passes():
    writer, llm = _make_reflection_writer(complete_returns=[
        # retry: a specific lesson
        MagicMock(text="In CHOP S1=-0.30 avoid buy; realized $-10.00.", stub=False),
    ])
    r = _refl()
    r.lesson = "Be careful next time."  # generic
    quality = writer._eval_quality(r)
    assert quality == ""   # retry produced a good lesson
    assert "CHOP" in r.lesson  # lesson was upgraded


def test_reflector_quality_generic_retry_also_generic():
    writer, llm = _make_reflection_writer(complete_returns=[
        MagicMock(text="Try to be careful.", stub=False),   # retry also generic
    ])
    r = _refl()
    r.lesson = "Be careful."
    quality = writer._eval_quality(r)
    assert quality == "low"


def test_reflector_quality_offline_skips_check():
    writer, _ = _make_reflection_writer(enabled=False)
    r = _refl()
    r.lesson = "Be careful."  # would be generic if checked
    quality = writer._eval_quality(r)
    assert quality == ""   # offline → always normal


def test_reflector_persist_passes_quality_to_bridge():
    writer, llm = _make_reflection_writer(complete_returns=[
        MagicMock(text="Be careful.", stub=False),   # generic → retry
        MagicMock(text="Be careful again.", stub=False),  # still generic
    ])
    bridge = MagicMock()
    bridge.record_reflection.return_value = "refl-id"
    bridge.audit.return_value = None
    writer.bridge = bridge

    r = _refl()
    r.lesson = "Be careful."
    r.quality = writer._eval_quality(r)
    writer._persist(r)

    call_kwargs = bridge.record_reflection.call_args.kwargs
    assert call_kwargs.get("quality") == "low"


# ── Researcher self-check ─────────────────────────────────────────────────────

def _make_research_agent(rubric_results=None, synth_text="BNB in chop; watch OI."):
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = True
    # synthesise T1 call returns synth_text; rubric T0 calls return rubric_results
    if rubric_results is None:
        rubric_results = ["YES"]
    synth_r = MagicMock(text=synth_text, stub=False)
    rubric_iters = iter(rubric_results)

    def _complete(prompt, system, tier, max_tokens):
        if tier == "T0":
            return MagicMock(text=next(rubric_iters, "YES"), stub=False)
        return synth_r

    llm.complete.side_effect = _complete
    return ResearchAgent(llm=llm, symbol="ETH")


def test_researcher_rubric_passes():
    agent = _make_research_agent(rubric_results=["YES"])
    text, low_conf = agent.synthesise("What is the regime?", "close=590")
    assert low_conf is False


def test_researcher_rubric_fails_first_passes_second():
    agent = _make_research_agent(rubric_results=["NO", "YES"])
    text, low_conf = agent.synthesise("What is the regime?", "close=590")
    assert low_conf is False


def test_researcher_rubric_fails_both():
    agent = _make_research_agent(rubric_results=["NO", "NO"])
    text, low_conf = agent.synthesise("What is the regime?", "close=590")
    assert low_conf is True


def test_researcher_rubric_skipped_offline():
    agent = _make_research_agent()
    agent.llm.enabled = False
    agent.llm.complete.return_value = MagicMock(text="stub digest", stub=True)
    text, low_conf = agent.synthesise("What is the regime?", "close=590")
    assert low_conf is False


def test_researcher_run_cycle_sets_low_confidence():
    from agent.secondbrain.research import ResearchSupervisor
    from agent.secondbrain.vector import VectorStore

    vector = MagicMock(spec=VectorStore)
    vector.upsert.return_value = True
    vector.enabled = False

    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = True
    call_count = {"n": 0}

    def _complete(prompt, system, tier, max_tokens):
        call_count["n"] += 1
        if tier == "T0":
            return MagicMock(text="NO", stub=False)  # rubric fails
        return MagicMock(text="some digest text", stub=False)

    llm.complete.side_effect = _complete
    sup = ResearchSupervisor(vector=vector, llm=llm, symbol="ETH")
    from backtest.engine import Bar
    bar = Bar(timestamp=0, open=1, high=1, low=1, close=1, volume=0)
    digests = sup.run_cycle(history=[bar] * 20)
    assert any(d.low_confidence for d in digests)


# ── Co-pilot citation self-check ──────────────────────────────────────────────

def test_is_uncited_short_answer_not_flagged():
    assert not _is_uncited("In CHOP regime, avoid.")

def test_is_uncited_has_bracket_citation():
    assert not _is_uncited("[reflection] In CHOP S1 negative, avoid buy based on history.")

def test_is_uncited_has_source_word():
    assert not _is_uncited("Based on source: reflection memory, the regime is CHOP with S1 down.")

def test_is_uncited_long_no_citation():
    long_ans = "The market is currently in a choppy regime. Based on recent price action, " \
               "it appears momentum is weak. We should consider reducing exposure."
    assert _is_uncited(long_ans)

def test_copilot_prepends_warning_on_uncited():
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = False
    # Answer is > 20 words but has no citation markers
    llm.complete.return_value = MagicMock(
        text=("The market is currently in a choppy regime. Based on recent price action, "
              "momentum is weak and we should consider reducing exposure significantly "
              "until a clearer trend emerges and the signals realign."),
        stub=True,
    )
    vector = MagicMock(spec=VectorStore)
    # Return some hits so the check triggers
    vector.query.return_value = [
        MemoryHit(id="h1", score=0.9, text="loss in chop", metadata={"kind": "reflection"}),
    ]
    cp = CoPilot(vector=vector, llm=llm)
    out = cp.ask("Should I enter now?")
    # Warning prepended for long uncited answer
    assert "grounded in retrieved memory" in out["answer"]

def test_copilot_no_warning_when_cited():
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = False
    llm.complete.return_value = MagicMock(
        text="[reflection] Based on past chop losses, avoid buy here.",
        stub=True,
    )
    vector = MagicMock(spec=VectorStore)
    vector.query.return_value = [
        MemoryHit(id="h1", score=0.9, text="loss in chop", metadata={"kind": "reflection"}),
    ]
    cp = CoPilot(vector=vector, llm=llm)
    out = cp.ask("Should I enter?")
    assert "grounded in retrieved memory" not in out["answer"]

def test_copilot_no_warning_when_no_hits():
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = False
    llm.complete.return_value = MagicMock(
        text="No relevant history found; current regime appears to be chop.",
        stub=True,
    )
    vector = MagicMock(spec=VectorStore)
    vector.query.return_value = []
    cp = CoPilot(vector=vector, llm=llm)
    out = cp.ask("What is the regime?")
    assert "grounded in retrieved memory" not in out["answer"]
