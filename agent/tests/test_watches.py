"""Tests for the deterministic watch checker - edge-trigger correctness and the
zero-LLM token invariant."""
from __future__ import annotations

import pytest

from agent.watches import evaluate, process_watches, validate_watch_spec, CLEAR, FIRED


# ── validation ────────────────────────────────────────────────────────────────

def test_validate_price_watch():
    w = validate_watch_spec({"kind": "price", "target": "cake", "op": "lt", "threshold": "2.40"})
    assert w == {"kind": "price", "target": "CAKE", "op": "lt", "threshold": 2.40, "label": ""}


def test_validate_regime_watch_forces_eq():
    w = validate_watch_spec({"kind": "regime", "target": "crash"})
    assert w["op"] == "eq" and w["target"] == "CRASH"


@pytest.mark.parametrize("bad", [
    {"kind": "nope", "target": "X", "op": "lt", "threshold": 1},
    {"kind": "price", "op": "lt", "threshold": 1},            # missing symbol
    {"kind": "price", "target": "CAKE", "op": "sideways", "threshold": 1},
    {"kind": "drawdown", "op": "lt", "threshold": "abc"},     # bad number
    {"kind": "regime"},                                       # missing target
])
def test_validate_rejects_bad_specs(bad):
    with pytest.raises(ValueError):
        validate_watch_spec(bad)


# ── edge-trigger semantics ──────────────────────────────────────────────────────

def _price_watch(state=CLEAR):
    return {"_id": "w1", "kind": "price", "target": "CAKE", "op": "lt",
            "threshold": 2.40, "last_state": state}


def test_fires_on_edge():
    res = evaluate(_price_watch(), {"symbol": "CAKE", "price": 2.30})
    assert res and res["fired"] is True and res["new_state"] == FIRED


def test_does_not_refire_while_armed():
    res = evaluate(_price_watch(state=FIRED), {"symbol": "CAKE", "price": 2.20})
    assert res is None  # already fired, condition still true → no event


def test_rearms_when_condition_clears():
    res = evaluate(_price_watch(state=FIRED), {"symbol": "CAKE", "price": 2.55})
    assert res and res["fired"] is False and res["new_state"] == CLEAR


def test_not_observable_for_other_symbol():
    res = evaluate(_price_watch(), {"symbol": "ETH", "price": 1.0})
    assert res is None  # price watch on CAKE, loop is on ETH → skip, no state change


def test_regime_watch_fires_on_match():
    w = {"_id": "r1", "kind": "regime", "target": "CRASH", "op": "eq", "last_state": CLEAR}
    assert evaluate(w, {"regime": "CRASH"})["fired"] is True
    assert evaluate(w, {"regime": "TREND"}) is None


def test_gt_op_and_drawdown():
    w = {"_id": "d1", "kind": "drawdown", "op": "gt", "threshold": 10.0, "last_state": CLEAR}
    assert evaluate(w, {"drawdown_pct": 12.5})["fired"] is True
    assert evaluate(w, {"drawdown_pct": 4.0}) is None


def test_malformed_watch_degrades_to_none():
    assert evaluate({"kind": "price"}, {"symbol": "CAKE", "price": 1.0}) is None


# ── token invariant - idle watches never invoke the fire callback (the LLM path) ──

def test_idle_watches_make_zero_fire_calls():
    llm_calls = []
    state_writes = []
    watches = [
        _price_watch(),                                              # CAKE, loop on ETH → skip
        {"_id": "d1", "kind": "drawdown", "op": "gt", "threshold": 50.0, "last_state": CLEAR},
    ]
    snap = {"symbol": "ETH", "price": 1.0, "drawdown_pct": 3.0}
    fired = process_watches(
        watches, snap,
        fire_cb=lambda w, r: llm_calls.append(r),
        state_cb=lambda i, s: state_writes.append((i, s)),
    )
    assert llm_calls == []      # nothing fired → no LLM explain call → zero tokens
    assert fired == []


def test_fire_callback_runs_once_on_trigger():
    llm_calls = []
    process_watches(
        [_price_watch()], {"symbol": "CAKE", "price": 2.30},
        fire_cb=lambda w, r: llm_calls.append(r),
        state_cb=lambda i, s: None,
    )
    assert len(llm_calls) == 1
