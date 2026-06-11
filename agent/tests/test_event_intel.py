"""Event Intelligence — deterministic scoring + risk-off + alert wiring (offline)."""
from __future__ import annotations

from agent.intel.brave_client import BraveSearchClient, NewsItem
from agent.intel.event_intel import EventIntel, score_headline


# ── Deterministic scoring ──────────────────────────────────────────────────────

def test_critical_risk_headline_is_severe_and_bearish():
    s = score_headline("Major DeFi protocol exploited, $200M drained from vault")
    assert s.risk_severity >= 0.9
    assert s.sentiment < 0
    assert "exploit" in s.matched or "drain" in s.matched


def test_depeg_is_critical():
    s = score_headline("Stablecoin depegs to $0.92 amid panic selling")
    assert s.risk_severity >= 0.9


def test_regulatory_is_major_not_critical():
    s = score_headline("SEC charges exchange in new lawsuit over token sales")
    assert 0.5 <= s.risk_severity < 1.0


def test_bullish_headline_positive_no_risk():
    s = score_headline("Spot ETF approval sparks institutional adoption rally")
    assert s.risk_severity == 0.0
    assert s.sentiment > 0


def test_neutral_headline_is_flat():
    s = score_headline("Analysts discuss market structure at conference")
    assert s.risk_severity == 0.0
    assert -0.2 <= s.sentiment <= 0.2


def test_word_boundary_avoids_false_match():
    # "ban" must not match inside "urban"; "hack" must not match "hackathon"
    s = score_headline("Urban developers attend a crypto hackathon downtown")
    assert s.risk_severity == 0.0


# ── Digest + risk-off ──────────────────────────────────────────────────────────

class _FakeClient(BraveSearchClient):
    def __init__(self, items):
        self._items = items
        self.enabled = True
    def news(self, query, count=20, freshness="pd"):
        return self._items


def _item(title):
    return NewsItem(title=title, description="", url="http://x", source="x", age="1h")


def test_digest_flips_risk_off_on_exploit():
    intel = EventIntel(_FakeClient([_item("Protocol hacked, funds drained")]))
    out = intel.scan(["ETH"])
    assert out["per_symbol"]["ETH"].risk_off is True
    assert out["per_symbol"]["ETH"].max_severity >= 0.9


def test_digest_calm_when_no_risk():
    intel = EventIntel(_FakeClient([_item("ETH steady as traders eye upgrade")]))
    out = intel.scan(["ETH"])
    assert out["per_symbol"]["ETH"].risk_off is False


def test_empty_news_is_neutral_digest():
    intel = EventIntel(_FakeClient([]))
    out = intel.scan(["ETH"])
    d = out["per_symbol"]["ETH"]
    assert d.n_headlines == 0 and d.risk_off is False and d.sentiment == 0.0


# ── Alert wiring (emit + notify) ───────────────────────────────────────────────

def test_alert_emits_and_notifies_on_risk_off():
    emitted, notified, logged = [], [], []
    intel = EventIntel(
        _FakeClient([_item("Exchange insolvency: withdrawals halted")]),
        emit=lambda **kw: emitted.append(kw),
        notify=lambda t: notified.append(t),
        log=lambda e, **f: logged.append((e, f)),
    )
    intel.scan(["ETH"])
    assert any(e["agent"] == "Scout" for e in emitted)
    assert any("RISK-OFF" in t for t in notified)
    assert any(ev == "intel.scan" for ev, _ in logged)


def test_no_alert_on_calm_market():
    notified = []
    intel = EventIntel(_FakeClient([_item("Quiet session for major tokens")]),
                       notify=lambda t: notified.append(t))
    intel.scan(["ETH"])
    assert notified == []


# ── Offline safety ─────────────────────────────────────────────────────────────

def test_disabled_client_returns_empty():
    c = BraveSearchClient(api_key="")
    assert c.enabled is False
    assert c.news("anything") == []


def test_intel_offline_is_quiet_noop():
    intel = EventIntel(BraveSearchClient(api_key=""))   # no key
    out = intel.scan(["ETH", "CAKE"])
    assert out["per_symbol"]["ETH"].n_headlines == 0
    assert out["market"].risk_off is False
