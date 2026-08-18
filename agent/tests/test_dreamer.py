"""Dreamer nightly consolidation - unit tests."""
from __future__ import annotations
import time
from unittest.mock import MagicMock, patch

import pytest

from agent.secondbrain.dreamer import Dreamer, DreamerResult, _DEDUPE_THRESHOLD
from agent.secondbrain.schema import KIND_RESEARCH, MemoryHit
from agent.secondbrain.vector import VectorStore
from agent.secondbrain.llm import ClaudeClient


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_dreamer(*, reflections=None, fc_summary=None, vector_hits=None):
    bridge = MagicMock()
    bridge.recent_reflections.return_value = reflections or []
    bridge.get_forecast_calibration_summary.return_value = fc_summary or {}
    bridge.record_forecast_calibration.return_value = "cal-id"
    bridge.soft_delete_reflection.return_value = None

    vector = MagicMock(spec=VectorStore)
    vector.enabled = False
    vector.query.return_value = vector_hits or []
    vector.upsert.return_value = True

    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = False
    llm.complete.return_value = MagicMock(text="nightly brief stub", stub=False)

    return Dreamer(vector=vector, llm=llm, bridge=bridge)


def _reflection(idx, lesson, pnl, stale=False):
    return {
        "_id": f"refl-{idx}",
        "cycle_id": f"cycle-{idx}",
        "lesson": lesson,
        "outcome_pnl_usd": pnl,
        "outcome_label": "win" if pnl > 0 else "loss",
        "vector_id": f"vec-{idx}",
        "stale": stale,
    }


# ── phase 1: dedupe ────────────────────────────────────────────────────────────

def test_dedupe_below_threshold_keeps_both():
    d = _make_dreamer(reflections=[
        _reflection(0, "avoid chop entries", -10),
        _reflection(1, "sell early in trend up", 20),
    ])
    # Similarity returns 0.0 (low) - no dedup
    d.vector.query.return_value = []
    result = d.run()
    assert result.reflections_deduped == 0
    d.bridge.soft_delete_reflection.assert_not_called()


def test_dedupe_above_threshold_removes_lower_pnl():
    lesson = "avoid chop buy entries when S2 negative"
    high_sim_hit = MemoryHit(id="vec-1", score=_DEDUPE_THRESHOLD + 0.02,
                             text=lesson, metadata={})
    d = _make_dreamer(reflections=[
        _reflection(0, lesson, -10),   # lower |PnL|
        _reflection(1, lesson, -30),   # higher |PnL| - keep this one
    ])
    # Vector query returns the second lesson as a near-duplicate
    d.vector.query.return_value = [high_sim_hit]
    result = d.run()
    assert result.reflections_deduped == 1
    d.bridge.soft_delete_reflection.assert_called_once_with("refl-0")


def test_dedupe_skips_already_stale():
    lesson = "same lesson repeated"
    d = _make_dreamer(reflections=[
        _reflection(0, lesson, -5, stale=True),  # already stale
        _reflection(1, lesson, -5),
    ])
    result = d.run()
    assert result.reflections_checked == 1   # stale skipped in count


def test_dedupe_single_reflection_no_op():
    d = _make_dreamer(reflections=[_reflection(0, "only one", 10)])
    result = d.run()
    assert result.reflections_deduped == 0


# ── phase 2: forecast calibration ─────────────────────────────────────────────

def test_forecast_summary_propagated():
    summary = {"high": {"win_rate": 0.7, "n": 10}, "low": {"win_rate": 0.4, "n": 5}}
    d = _make_dreamer(fc_summary=summary)
    result = d.run()
    assert result.forecast_summary == summary


def test_forecast_summary_empty_ok():
    d = _make_dreamer(fc_summary={})
    result = d.run()
    assert result.forecast_summary == {}


# ── phase 3: age out stale research ───────────────────────────────────────────

def test_age_stale_research_marks_old_docs():
    now_ms = int(time.time() * 1000)
    old_ts = now_ms - 50 * 3_600_000   # 50h ago - past the 48h threshold
    fresh_ts = now_ms - 1 * 3_600_000   # 1h ago - should NOT be aged

    old_hit = MemoryHit(
        id="research-old", score=0.9, text="old digest",
        metadata={"kind": KIND_RESEARCH, "timestamp_ms": old_ts},
    )
    fresh_hit = MemoryHit(
        id="research-fresh", score=0.8, text="fresh digest",
        metadata={"kind": KIND_RESEARCH, "timestamp_ms": fresh_ts},
    )
    d = _make_dreamer(vector_hits=[old_hit, fresh_hit])
    result = d.run()
    assert result.research_aged == 1
    # The old doc was re-upserted with stale=True
    call_args = d.vector.upsert.call_args_list
    stale_upserts = [c for c in call_args if c.kwargs.get("metadata", {}).get("stale")
                     or (len(c.args) > 2 and (c.args[2] or {}).get("stale"))]
    assert len(stale_upserts) >= 1


def test_age_skips_already_stale():
    now_ms = int(time.time() * 1000)
    old_ts = now_ms - 50 * 3_600_000
    stale_hit = MemoryHit(
        id="research-stale", score=0.9, text="stale",
        metadata={"kind": KIND_RESEARCH, "timestamp_ms": old_ts, "stale": True},
    )
    d = _make_dreamer(vector_hits=[stale_hit])
    result = d.run()
    assert result.research_aged == 0


# ── phase 4: nightly digest ───────────────────────────────────────────────────

def test_nightly_digest_written_to_vector():
    d = _make_dreamer()
    result = d.run()
    assert result.nightly_digest_id is not None
    assert result.nightly_digest_id.startswith("dreamer-nightly-")
    d.vector.upsert.assert_called()


def test_nightly_digest_uses_llm():
    d = _make_dreamer()
    result = d.run()
    d.llm.complete.assert_called_once()
    assert result.nightly_digest_id is not None


# ── resilience ────────────────────────────────────────────────────────────────

def test_bridge_error_does_not_crash():
    bridge = MagicMock()
    bridge.recent_reflections.side_effect = RuntimeError("DB down")
    bridge.get_forecast_calibration_summary.side_effect = RuntimeError("DB down")
    vector = MagicMock(spec=VectorStore)
    vector.enabled = False
    vector.query.return_value = []
    vector.upsert.return_value = True
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = False
    llm.complete.return_value = MagicMock(text="stub", stub=False)

    d = Dreamer(vector=vector, llm=llm, bridge=bridge)
    result = d.run()
    assert len(result.errors) >= 1   # logged, not raised


def test_vector_error_does_not_crash():
    d = _make_dreamer()
    d.vector.query.side_effect = RuntimeError("vector down")
    d.vector.upsert.side_effect = RuntimeError("vector down")
    result = d.run()
    # Dreamer completes all phases; errors are recorded
    assert isinstance(result.errors, list)
