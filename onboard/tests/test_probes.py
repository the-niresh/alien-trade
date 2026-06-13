from onboard.probes import (
    ProbeResult,
    probe_anthropic,
    probe_binance,
    probe_convex,
    probe_telegram,
)


def test_telegram_probe_offline():
    r = probe_telegram(token="", chat_id="")
    assert isinstance(r, ProbeResult) and r.ok is False and r.detail


def test_convex_probe_empty_url():
    r = probe_convex(url="")
    assert isinstance(r, ProbeResult) and r.ok is False and r.detail


def test_anthropic_probe_empty_key():
    r = probe_anthropic(key="")
    assert isinstance(r, ProbeResult) and r.ok is False and r.detail


def test_probes_never_raise_on_bad_input():
    # Garbage that would fail a real network call must still come back structured.
    for r in (
        probe_convex(url="http://127.0.0.1:1"),
        probe_binance(base="http://127.0.0.1:1"),
        probe_telegram(token="x", chat_id="y", base="http://127.0.0.1:1"),
        probe_anthropic(key="x", base="http://127.0.0.1:1"),
    ):
        assert isinstance(r, ProbeResult) and r.ok is False and r.detail
