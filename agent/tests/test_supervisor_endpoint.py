"""
POST /supervisor endpoint + observe→react wiring.

Tests that the FastAPI endpoint correctly routes events to the LangGraph
supervisor, returns safe responses when supervisor is unavailable, and that
_cycle_to_dict exposes the side/realized_pnl fields Trigger.dev needs.
All hermetic - no Convex, no LLM, no real loop.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

try:
    from fastapi.testclient import TestClient
    from agent.server import app, _cycle_to_dict
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi not installed")


# ── fake supervisor ────────────────────────────────────────────────────────────

class _FakeSupervisor:
    def __init__(self, route="co_pilot", n_events=1, raise_on_handle=False):
        self._route = route
        self._n = n_events
        self._raise = raise_on_handle
        self.calls: list[dict] = []

    def handle(self, text, *, kind="user", symbol="", cycle_id=None, payload=None):
        if self._raise:
            raise RuntimeError("supervisor exploded")
        self.calls.append({"kind": kind, "symbol": symbol, "cycle_id": cycle_id})
        return {"route": self._route, "events": [object()] * self._n}


# ── context-manager client ─────────────────────────────────────────────────────

@contextmanager
def _client(fake_sup):
    """Yield a TestClient with get_supervisor() and get_loop() patched for the
    duration of the block, so patches are active during each request."""
    with patch("agent.server.get_supervisor", return_value=fake_sup):
        with patch("agent.server.get_loop"):
            yield TestClient(app, raise_server_exceptions=False)


# ── /supervisor endpoint ───────────────────────────────────────────────────────

def test_supervisor_user_question_routes_copilot():
    sup = _FakeSupervisor(route="co_pilot")
    with _client(sup) as client:
        r = client.post("/supervisor", json={"kind": "user", "text": "what regime?"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["route"] == "co_pilot"
    assert body["events_emitted"] == 1
    assert sup.calls[-1]["kind"] == "user"


def test_supervisor_research_tick_routes_researcher():
    sup = _FakeSupervisor(route="researcher", n_events=2)
    with _client(sup) as client:
        r = client.post("/supervisor", json={"kind": "research_tick", "symbol": "ETH"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["route"] == "researcher"
    assert body["events_emitted"] == 2
    assert sup.calls[-1]["kind"] == "research_tick"


def test_supervisor_position_closed_routes_historian():
    sup = _FakeSupervisor(route="historian", n_events=2)
    with _client(sup) as client:
        r = client.post("/supervisor", json={
            "kind": "position_closed",
            "symbol": "ETH",
            "cycle_id": "ETH-99",
            "payload": {"realized_pnl": -10.0, "regime": "chop", "side": "sell"},
        })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    call = sup.calls[-1]
    assert call["kind"] == "position_closed"
    assert call["cycle_id"] == "ETH-99"


def test_supervisor_unavailable_returns_ok_false():
    with patch("agent.server.get_supervisor", return_value=None):
        with patch("agent.server.get_loop"):
            client = TestClient(app, raise_server_exceptions=False)
            r = client.post("/supervisor", json={"kind": "research_tick"})
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert "unavailable" in r.json()["reason"]


def test_supervisor_exception_is_swallowed():
    """A supervisor crash must return ok=False, not a 500."""
    sup = _FakeSupervisor(raise_on_handle=True)
    with _client(sup) as client:
        r = client.post("/supervisor", json={"kind": "user", "text": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "supervisor exploded" in body["reason"]


# ── _cycle_to_dict side/realized_pnl fields ───────────────────────────────────

def _make_exec(is_fill=True, realized_pnl=-5.0, tx_hash=None):
    return SimpleNamespace(is_fill=is_fill, realized_pnl=realized_pnl, tx_hash=tx_hash)

def _make_order(side="sell"):
    return SimpleNamespace(side=side)

def _make_result(**kw):
    defaults = dict(
        cycle_id="ETH-1", timestamp_ms=0, halted=False, regime="chop",
        verdict="allow", reason="ok", order=None, execution=None,
        equity=1000.0, drawdown_pct=0.0, breakdown={},
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_cycle_dict_side_sell_on_sell_fill():
    r = _make_result(
        order=_make_order("sell"),
        execution=_make_exec(is_fill=True, realized_pnl=-5.0),
    )
    d = _cycle_to_dict(r)
    assert d["filled"] is True
    assert d["side"] == "sell"
    assert d["realized_pnl"] == pytest.approx(-5.0)


def test_cycle_dict_side_buy_on_buy_fill():
    r = _make_result(
        order=_make_order("buy"),
        execution=_make_exec(is_fill=True, realized_pnl=0.0),
    )
    d = _cycle_to_dict(r)
    assert d["side"] == "buy"


def test_cycle_dict_side_none_when_no_fill():
    r = _make_result(order=_make_order("sell"), execution=_make_exec(is_fill=False))
    d = _cycle_to_dict(r)
    assert d["filled"] is False
    assert d["side"] is None
    assert d["realized_pnl"] is None


def test_cycle_dict_none_result():
    d = _cycle_to_dict(None)
    assert d["ran"] is False
