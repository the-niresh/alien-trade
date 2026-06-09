"""
CMC Skill Hub two-tier loader. Pins: curated param-builders match each skill's
schema (window formats / enums), curated dispatch resolves the right unique_name,
dynamic find_skill/execute_skill route through the transport, offline-first
returns explicit markers (never fabricated results), and SSE/payload parsing.
No live network — a fake transport records calls and returns canned payloads.
"""
from __future__ import annotations

import pytest

from agent.skills import CURATED, SkillContext, SkillHub
from agent.skills.transport import _extract_payload, _parse_response


# ── Fake transport ─────────────────────────────────────────────────────────────

class _FakeTransport:
    def __init__(self, enabled=True, payload=None):
        self._enabled = enabled
        self.calls: list[tuple[str, dict]] = []
        self._payload = payload or {"status": "ok"}

    @property
    def enabled(self):
        return self._enabled

    def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments or {}))
        if name == "find_skill":
            return {"candidates": [{"uniqueName": "x", "skillDescription": "d"}]}
        return self._payload


def _hub(**kw):
    return SkillHub(transport=_FakeTransport(**kw))


# ── Curated registry: param builders match schemas ─────────────────────────────

def test_curated_covers_all_signals():
    signals = {s.signal for s in CURATED.values()}
    assert {"S2", "S3", "S4", "regime"} <= signals
    assert len(CURATED) >= 8


def test_funding_regime_params_use_nd_window():
    p = CURATED["funding_regime"].build(SkillContext(symbol="ETH", window_days=30))
    assert p == {"symbol": "ETH", "venue": "Binance", "window": "30d"}


def test_oi_dark_flow_clamps_window_enum():
    # bad oi_window must clamp to a schema-valid enum, never pass through
    p = CURATED["oi_dark_flow"].build(SkillContext(symbol="ETH", oi_window="9h"))
    assert p["window"] == "4h"
    assert p["symbol"] == "ETH" and p["lookback_days"] == 14


def test_market_regime_uses_time_window_enum_only():
    p = CURATED["market_regime"].build(SkillContext(regime_window="7d"))
    assert p == {"time_window": "7d"}            # market-wide: no symbol key
    bad = CURATED["market_regime"].build(SkillContext(regime_window="3d"))
    assert bad == {"time_window": "30d"}          # clamps invalid enum


def test_social_divergence_builds_query():
    p = CURATED["social_divergence"].build(SkillContext(symbol="ETH", name="Ethereum"))
    assert p["query"] == "Ethereum OR ETH"
    assert p["symbol"] == "ETH" and 1 <= p["max_posts"] <= 10


def test_nd_window_clamped_to_2_90():
    assert SkillContext(window_days=1).nd() == "2d"
    assert SkillContext(window_days=500).nd() == "90d"


def test_funding_compare_caps_venues_and_direction():
    p = CURATED["funding_compare"].build(
        SkillContext(venues=tuple(f"V{i}" for i in range(12)), direction="bogus"))
    assert len(p["venues"]) <= 8
    assert p["direction"] == "neutral"            # invalid direction clamped


# ── Two-tier dispatch ────────────────────────────────────────────────────────

def test_run_curated_resolves_unique_name():
    hub = _hub()
    hub.run_curated("funding_regime", SkillContext(symbol="ETH"))
    name, args = hub.transport.calls[-1]
    assert name == "execute_skill"
    assert args["unique_name"] == "detect_funding_rate_regime_shift"
    assert args["parameters"]["symbol"] == "ETH"


def test_run_curated_unknown_key_raises():
    with pytest.raises(KeyError):
        _hub().run_curated("not_a_skill")


def test_find_skill_routes_through_transport():
    hub = _hub()
    out = hub.find_skill("is BTC a risk asset vs Nasdaq?", top_k=3)
    assert hub.transport.calls[-1][0] == "find_skill"
    assert isinstance(out, list) and out and out[0]["uniqueName"] == "x"


# ── Offline-first ──────────────────────────────────────────────────────────────

def test_offline_find_skill_returns_empty():
    assert _hub(enabled=False).find_skill("anything") == []


def test_offline_execute_returns_marker_not_fabrication():
    res = _hub(enabled=False).run_curated("kol_sentiment", SkillContext(symbol="ETH"))
    assert res["status"] == "offline"
    assert res["unique_name"] == "altcoin_kol_sentiment"


def test_curated_manifest_lists_every_skill():
    m = SkillHub.curated_manifest()
    for key in CURATED:
        assert key in m


# ── SSE / payload parsing ──────────────────────────────────────────────────────

def test_parse_sse_picks_data_line():
    sse = 'event:message\ndata:{"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
    assert _parse_response(sse)["result"] == {"ok": True}


def test_parse_plain_json_body():
    assert _parse_response('{"jsonrpc":"2.0","result":1}')["result"] == 1


def test_extract_payload_decodes_content_text():
    result = {"content": [{"type": "text", "text": '{"candidates":[]}'}]}
    assert _extract_payload(result) == {"candidates": []}
