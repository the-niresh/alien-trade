"""8.15 - Researcher fan-out across all eligible symbols."""
from __future__ import annotations
from unittest.mock import MagicMock, call, patch

import pytest

from agent.secondbrain.research import ResearchSupervisor
from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.vector import VectorStore
from backtest.engine import Bar


# ── helpers ────────────────────────────────────────────────────────────────────

def _bar():
    return Bar(timestamp=0, open=100, high=110, low=90, close=105, volume=1000)


def _make_sup(bridge=None, fetch_history_returns=None):
    llm = MagicMock(spec=ClaudeClient)
    llm.enabled = False
    llm.complete.return_value = MagicMock(text="stub digest", stub=True)

    vector = MagicMock(spec=VectorStore)
    vector.enabled = False
    vector.upsert.return_value = True

    sup = ResearchSupervisor(vector=vector, llm=llm, symbol="ETH", bridge=bridge)

    # Override _fetch_history to avoid real network calls
    if fetch_history_returns is not None:
        sup._fetch_history = MagicMock(return_value=fetch_history_returns)
    else:
        sup._fetch_history = MagicMock(return_value=[_bar()] * 30)

    return sup


# ── single-symbol backward-compat ─────────────────────────────────────────────

def test_run_cycle_single_symbol_unchanged():
    sup = _make_sup()
    digests = sup.run_cycle()
    assert isinstance(digests, list)
    # At least one digest produced for the baseline regime question
    assert len(digests) >= 1


def test_run_cycle_single_symbol_via_symbols_list():
    sup = _make_sup()
    digests = sup.run_cycle(symbols=["ETH"])
    assert isinstance(digests, list)
    assert len(digests) >= 1


def test_run_cycle_no_symbols_uses_self_symbol():
    sup = _make_sup()
    digests = sup.run_cycle(symbols=None)
    assert all(d.id.startswith("research-ETH-") for d in digests)


# ── multi-symbol fan-out ───────────────────────────────────────────────────────

def test_fanout_covers_all_symbols():
    sup = _make_sup()
    symbols = ["ETH", "CAKE", "UNI"]
    digests = sup.run_cycle(symbols=symbols)
    # Each symbol must produce at least 1 digest
    covered = {d.id.split("-")[1] for d in digests}
    assert covered == set(symbols)


def test_fanout_stores_digest_per_symbol():
    sup = _make_sup()
    digests = sup.run_cycle(symbols=["ETH", "LINK"])
    eth_ids = [d.id for d in digests if "ETH" in d.id]
    link_ids = [d.id for d in digests if "LINK" in d.id]
    assert len(eth_ids) >= 1
    assert len(link_ids) >= 1


def test_fanout_one_symbol_failure_does_not_abort_others():
    sup = _make_sup()
    call_count = {"n": 0}
    original_run_one = sup._run_one

    def _failing_run_one(symbol, history=None, max_questions=3):
        call_count["n"] += 1
        if symbol == "CAKE":
            raise RuntimeError("CMC timeout")
        return original_run_one(symbol, history, max_questions)

    sup._run_one = _failing_run_one
    # Should not raise; ETH and UNI digests still returned
    digests = sup.run_cycle(symbols=["ETH", "CAKE", "UNI"])
    covered = {d.id.split("-")[1] for d in digests}
    assert "ETH" in covered
    assert "UNI" in covered
    assert "CAKE" not in covered  # failed gracefully


def test_fanout_writes_vector_upserts_per_symbol():
    sup = _make_sup()
    sup.run_cycle(symbols=["ETH", "CAKE"])
    upsert_ids = [c.kwargs.get("id") or c.args[0]
                  for c in sup.vector.upsert.call_args_list]
    eth_upserts = [u for u in upsert_ids if u and "ETH" in str(u)]
    cake_upserts = [u for u in upsert_ids if u and "CAKE" in str(u)]
    assert len(eth_upserts) >= 1
    assert len(cake_upserts) >= 1


# ── per-symbol forecast_state write ───────────────────────────────────────────

def test_run_one_writes_forecast_per_symbol_when_bridge_provided():
    bridge = MagicMock()
    bridge.set_forecast_state.return_value = None
    sup = _make_sup(bridge=bridge)
    sup._run_one("ETH", history=[_bar()] * 20)
    bridge.set_forecast_state.assert_called_once()
    fs = bridge.set_forecast_state.call_args.args[0]
    assert fs.symbol == "ETH"


def test_run_one_no_forecast_write_without_bridge():
    sup = _make_sup(bridge=None)
    # Should not raise even with no bridge
    digests = sup._run_one("ETH", history=[_bar()] * 20)
    assert isinstance(digests, list)


# ── bridge.get_token_allowlist ────────────────────────────────────────────────

def test_get_token_allowlist_offline_returns_default():
    from agent.convex_bridge import ConvexBridge
    bridge = ConvexBridge(url="")   # offline
    tokens = bridge.get_token_allowlist()
    assert "ETH" in tokens


def test_get_token_allowlist_from_convex_config():
    from agent.convex_bridge import ConvexBridge
    bridge = ConvexBridge(url="http://fake")
    bridge.get_config = MagicMock(return_value={
        "token_allowlist": ["ETH", "CAKE", "UNI", "LINK", "AAVE"],
    })
    tokens = bridge.get_token_allowlist()
    assert set(tokens) == {"ETH", "CAKE", "UNI", "LINK", "AAVE"}


# ── supervisor _filter_dedupe ─────────────────────────────────────────────────

def test_filter_dedupe_includes_fresh_symbols():
    from agent.graph.supervisor import Supervisor
    from agent.secondbrain.builder import SecondBrain

    sb = MagicMock(spec=SecondBrain)
    sb.vector = MagicMock(spec=VectorStore)
    sb.vector.enabled = False
    bridge = MagicMock()
    bridge.get_agent_control.return_value = MagicMock(agents_paused=False)
    bridge.get_token_allowlist.return_value = ["ETH", "CAKE", "UNI"]
    sup = Supervisor(sb, bridge=bridge)

    # No prior research - all symbols should be included
    result = sup._filter_dedupe("ETH", {})
    assert "ETH" in result
    assert "CAKE" in result
    assert "UNI" in result


def test_filter_dedupe_skips_recently_researched():
    import time
    from agent.graph.supervisor import Supervisor
    from agent.secondbrain.builder import SecondBrain

    sb = MagicMock(spec=SecondBrain)
    sb.vector = MagicMock(spec=VectorStore)
    sb.vector.enabled = False
    bridge = MagicMock()
    bridge.get_agent_control.return_value = MagicMock(agents_paused=False)
    bridge.get_token_allowlist.return_value = ["ETH", "CAKE", "UNI"]
    sup = Supervisor(sb, bridge=bridge)

    # Mark CAKE as recently researched
    sup._last_research_ts["CAKE"] = time.time()

    result = sup._filter_dedupe("ETH", {})
    assert "ETH" in result
    assert "CAKE" not in result   # deduped
    assert "UNI" in result


def test_filter_dedupe_always_returns_at_least_primary():
    import time
    from agent.graph.supervisor import Supervisor
    from agent.secondbrain.builder import SecondBrain

    sb = MagicMock(spec=SecondBrain)
    sb.vector = MagicMock(spec=VectorStore)
    sb.vector.enabled = False
    bridge = MagicMock()
    bridge.get_agent_control.return_value = MagicMock(agents_paused=False)
    bridge.get_token_allowlist.return_value = ["ETH"]
    sup = Supervisor(sb, bridge=bridge)

    # Even if primary was recently researched, it should still be in the result
    # (the fallback ensures at least primary is always returned)
    # Mark all as recently researched
    sup._last_research_ts["ETH"] = time.time()
    result = sup._filter_dedupe("ETH", {})
    assert result == ["ETH"]   # fallback: at least primary
