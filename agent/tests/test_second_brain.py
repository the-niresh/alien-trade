"""
Step 6 — Second Brain: Hermes loop, institutional pre-load, AutoResearch,
co-pilot, and token/cost telemetry. All tests run OFFLINE (no Upstash, no
Anthropic key) against the in-memory fallbacks — hermetic and fast.

The load-bearing guarantees:
  • a stored reflection demonstrably changes a later decision (block / penalize)
  • the read path never invokes the LLM and fails open (can only tighten risk)
  • tier routing + cache produce a measurable saving vs a naive all-Opus baseline
  • the Hermes write/read paths bolt onto the loop WITHOUT touching /core
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar, Order
from backtest.costs import BSCCostModel
from strategy.combined import StrategyParams, score_breakdown

from agent.brain import AvoidanceVerdict
from agent.convex_bridge import ConvexBridge
from agent.feed import ReplayFeed
from agent.loop import DecisionLoop
from agent.secondbrain.avoidance import VectorMistakeAvoidance
from agent.secondbrain.builder import build_second_brain
from agent.secondbrain.cache import ResponseCache
from agent.secondbrain.copilot import CoPilot
from agent.secondbrain.llm import ClaudeClient, MODEL_TIERS
from agent.secondbrain.preload import _label_symbol
from agent.secondbrain.reflection import ReflectionWriter
from agent.secondbrain.research import ResearchSupervisor
from agent.secondbrain.schema import (
    KIND_INSTITUTIONAL, KIND_REFLECTION, KIND_RESEARCH,
    dominant_signal, setup_key,
)
from agent.secondbrain.telemetry import CostTelemetry, cost_of
from agent.secondbrain.vector import VectorStore
from agent.executor import PaperExecutor


# ── helpers ────────────────────────────────────────────────────────────────────

def _bars(n: int, start: float = 300.0, trend: float = 1.004, vol: float = 0.012, seed: int = 7):
    rng = np.random.default_rng(seed)
    bars, price = [], start
    for i in range(n):
        price *= trend * (1 + rng.normal(0, vol))
        bars.append(Bar(timestamp=1_700_000_000_000 + i * 86_400_000,
                        open=price * 0.999, high=price * 1.01,
                        low=price * 0.99, close=price, volume=5e6))
    return bars


def _seed_setup(vector: VectorStore, history, side: str, pnls: list[float]):
    """Seed the vector with reflections for the setup `history`/`side` produces."""
    bd = score_breakdown(history, StrategyParams())
    signals = {k: bd.get(k) for k in ("s1", "s2", "s3", "s4")}
    key = setup_key(bd["regime"], signals, side)
    for i, p in enumerate(pnls):
        vector.upsert(id=f"refl-seed-{i}", text=key, metadata={
            "kind": KIND_REFLECTION, "setup_key": key, "side": side,
            "outcome_pnl_usd": p, "outcome_label": "loss" if p < 0 else "win",
        })
    return bd["regime"]


# ── 1. setup-key fingerprint (shared write/read key) ───────────────────────────

class TestSetupKey:
    def test_dominant_signal_picks_largest_abs(self):
        assert dominant_signal({"s1": 0.1, "s2": -0.9, "s3": 0.0}) == "derivatives"
        assert dominant_signal({"s1_momentum": 0.8, "s2_funding": 0.2}) == "momentum"

    def test_setup_key_is_deterministic(self):
        s = {"s1": 0.7, "s2": 0.1}
        assert setup_key("trend", s, "buy") == setup_key("trend", s, "buy")
        assert "trend" in setup_key("trend", s, "buy")
        assert "momentum" in setup_key("trend", s, "buy")


# ── 2. VectorStore offline ─────────────────────────────────────────────────────

class TestVectorStore:
    def test_upsert_query_and_kind_filter(self):
        v = VectorStore()  # offline
        v.upsert("a", "buy in trend regime driven by momentum signal", {"kind": KIND_REFLECTION})
        v.upsert("b", "sell in crash regime driven by flow signal", {"kind": KIND_RESEARCH})
        hits = v.query("buy in trend regime driven by momentum signal", top_k=5)
        assert hits and hits[0].id == "a" and hits[0].score > 0.5
        only = v.query("trend momentum", top_k=5, kind=KIND_RESEARCH)
        assert all(h.metadata.get("kind") == KIND_RESEARCH for h in only)

    def test_upsert_overwrites_same_id(self):
        v = VectorStore()
        v.upsert("x", "first", {"kind": "k"})
        v.upsert("x", "second", {"kind": "k"})
        assert len(v._mem) == 1 and v._mem[0]["data"] == "second"


# ── 3. cache + telemetry ───────────────────────────────────────────────────────

class TestCacheAndTelemetry:
    def test_cache_roundtrip_offline(self):
        c = ResponseCache()
        k = ResponseCache.key("T1", "sys", "prompt", 100, False)
        assert c.get(k) is None
        c.set(k, "answer")
        assert c.get(k) == "answer"

    def test_cost_of_uses_catalog_pricing(self):
        # Opus: $5/$25 per 1M
        assert cost_of("claude-opus-4-8", 1_000_000, 0) == 5.0
        assert cost_of("claude-opus-4-8", 0, 1_000_000) == 25.0
        # Haiku cheaper than Opus for identical tokens
        assert cost_of("claude-haiku-4-5", 1000, 1000) < cost_of("claude-opus-4-8", 1000, 1000)

    def test_telemetry_tracks_saving_vs_opus_baseline(self):
        t = CostTelemetry()
        # A Haiku (T0) call: cheaper than the Opus baseline → positive saving.
        t.record(tier="T0", model="claude-haiku-4-5", in_tokens=1000, out_tokens=500,
                 cost_usd=cost_of("claude-haiku-4-5", 1000, 500), cache_hit=False, latency_s=0.1)
        snap = t.snapshot()
        assert snap["calls"] == 1 and snap["saved_usd"] > 0
        # A cache hit adds baseline cost but no actual cost → more saving, hit-rate up.
        t.record(tier="T0", model="claude-haiku-4-5", in_tokens=1000, out_tokens=500,
                 cost_usd=0.0, cache_hit=True, latency_s=0.0)
        assert t.snapshot()["cache_hit_rate"] == 0.5


# ── 4. LLM client offline (stub + tier routing + cache) ────────────────────────

class TestClaudeClientOffline:
    def test_stub_when_no_key_and_telemetry_recorded(self):
        c = ClaudeClient(api_key="")
        r = c.complete("hello world", tier="T0", max_tokens=50)
        assert r.stub is True and r.model == MODEL_TIERS["T0"]
        assert c.telemetry.calls == 1

    def test_second_identical_call_is_cache_hit(self):
        c = ClaudeClient(api_key="")
        c.complete("same prompt", tier="T1")
        r2 = c.complete("same prompt", tier="T1")
        assert r2.cache_hit is True
        assert c.telemetry.cache_hits == 1

    def test_tier_routes_to_expected_model(self):
        c = ClaudeClient(api_key="")
        assert c.model_for("T0") == "claude-haiku-4-5"
        assert c.model_for("T2") == "claude-opus-4-8"


# ── 5. Hermes WRITE — reflection ───────────────────────────────────────────────

class _FakeBridge:
    enabled = True
    def __init__(self):
        self.reflections, self.audits = [], []
    def record_reflection(self, **kw): self.reflections.append(kw); return "r1"
    def audit(self, *a, **k): self.audits.append((a, k))


class TestReflectionWriter:
    def test_reflect_stores_to_vector_and_bridge(self):
        v = VectorStore()
        bridge = _FakeBridge()
        w = ReflectionWriter(vector=v, llm=ClaudeClient(api_key=""), bridge=bridge)
        r = w.reflect(cycle_id="BNB-1", trade_id="trade_1", timestamp_ms=1,
                      regime="trend", side="sell",
                      signals={"s1": 0.8, "s2": 0.1}, realized_pnl=-42.0)
        assert r is not None and r.outcome_label == "loss"
        # vector got a reflection-kind memory keyed on the setup
        assert v._mem and v._mem[0]["metadata"]["kind"] == KIND_REFLECTION
        # bridge persisted the row + an audit entry
        assert len(bridge.reflections) == 1 and bridge.reflections[0]["outcome_label"] == "loss"
        assert any(a[0][0] == "reflection" for a in bridge.audits)

    def test_deterministic_lesson_offline(self):
        w = ReflectionWriter(vector=VectorStore(), llm=ClaudeClient(api_key=""))
        r = w.reflect(cycle_id="c", trade_id=None, timestamp_ms=0, regime="chop",
                      side="sell", signals={"s2": -0.6}, realized_pnl=15.0)
        assert "reinforce" in r.lesson and r.outcome_label == "win"


# ── 6. Hermes READ — mistake-avoidance changes a later decision ────────────────

class TestMistakeAvoidance:
    def test_repeated_losses_block_the_setup(self):
        v = VectorStore()
        hist = _bars(80)
        regime = _seed_setup(v, hist, "buy", [-50.0, -60.0, -40.0])   # 3/3 losses
        ma = VectorMistakeAvoidance(vector=v, params=StrategyParams())
        verdict = ma.check(hist, Order(side="buy", size_usd=1000, symbol="BNB", timestamp=1), regime)
        assert verdict.block is True and "blocking" in verdict.reason

    def test_mixed_history_penalizes_size(self):
        v = VectorStore()
        hist = _bars(80)
        regime = _seed_setup(v, hist, "buy", [-100.0, -100.0, 10.0, 10.0])  # 50% loss, net<0
        ma = VectorMistakeAvoidance(vector=v, params=StrategyParams())
        verdict = ma.check(hist, Order(side="buy", size_usd=1000, symbol="BNB", timestamp=1), regime)
        assert verdict.block is False and verdict.size_penalty > 0

    def test_winning_history_allows(self):
        v = VectorStore()
        hist = _bars(80)
        regime = _seed_setup(v, hist, "buy", [20.0, 30.0, 25.0])
        ma = VectorMistakeAvoidance(vector=v, params=StrategyParams())
        verdict = ma.check(hist, Order(side="buy", size_usd=1000, symbol="BNB", timestamp=1), regime)
        assert verdict.block is False and verdict.size_penalty == 0.0

    def test_no_evidence_allows(self):
        ma = VectorMistakeAvoidance(vector=VectorStore(), params=StrategyParams())
        v = ma.check(_bars(80), Order(side="buy", size_usd=1000, symbol="BNB", timestamp=1), "trend")
        assert v.block is False

    def test_read_path_never_calls_llm(self):
        # avoidance holds no LLM at all — structurally cannot touch the hot path
        ma = VectorMistakeAvoidance(vector=VectorStore(), params=StrategyParams())
        assert not hasattr(ma, "llm")


# ── 7. Loop integration — penalty shrinks size, reflection fires on close ──────

class _PenaltyBrain:
    def check(self, history, order, regime):
        return AvoidanceVerdict(block=False, size_penalty=0.5, reason="halve")


class _RecordingReflection:
    def __init__(self): self.calls = []
    def reflect(self, **kw): self.calls.append(kw)


class TestLoopIntegration:
    def test_size_penalty_halves_executed_order(self):
        bar = Bar(timestamp=5, open=300, high=301, low=299, close=300, volume=1e6)
        always_buy = lambda h: Order(side="buy", size_usd=1000.0, symbol="BNB",
                                     timestamp=h[-1].timestamp)
        loop = DecisionLoop(
            feed=ReplayFeed([bar]), strategy=always_buy, executor=PaperExecutor(BSCCostModel()),
            bridge=ConvexBridge(url=""), params=StrategyParams(), symbol="BNB",
            mode="paper", initial_capital=10_000.0, mistake_avoidance=_PenaltyBrain(),
        )
        res = loop.run()[0]
        assert res.execution.is_fill
        assert abs(res.execution.fill.order.size_usd - 500.0) < 1e-9   # halved

    def test_reflection_fires_on_sell_close(self):
        # buy then sell across two bars → reflection emitted on the sell
        bars = [Bar(timestamp=t, open=300, high=301, low=299, close=300 + (10 if t == 2 else 0),
                    volume=1e6) for t in (1, 2)]
        sides = iter(["buy", "sell"])
        strat = lambda h: Order(side=next(sides), size_usd=1000.0, symbol="BNB",
                                timestamp=h[-1].timestamp)
        refl = _RecordingReflection()
        loop = DecisionLoop(
            feed=ReplayFeed(bars), strategy=strat, executor=PaperExecutor(BSCCostModel()),
            bridge=ConvexBridge(url=""), params=StrategyParams(), symbol="BNB",
            mode="paper", initial_capital=10_000.0, reflection_writer=refl,
        )
        loop.run()
        assert len(refl.calls) == 1 and refl.calls[0]["side"] == "sell"


# ── 8. 2-year institutional pre-load (offline labelling) ───────────────────────

class TestPreload:
    def test_label_symbol_writes_institutional_memory(self):
        v = VectorStore()
        bars = _bars(200)
        n = _label_symbol(v, "BNB", bars, StrategyParams(), horizon=10, stride=5)
        assert n > 0 and len(v._mem) == n
        rec = v._mem[0]["metadata"]
        assert rec["kind"] == KIND_INSTITUTIONAL
        assert rec["outcome_label"] in ("win", "loss")
        assert "dominant_signal" in rec


# ── 9. Karpathy AutoResearch (one full cycle, offline) ─────────────────────────

class TestAutoResearch:
    def test_cycle_produces_and_stores_digests(self):
        v = VectorStore()
        sup = ResearchSupervisor(vector=v, llm=ClaudeClient(api_key=""), symbol="BNB")
        sup.agent.gather_context = lambda history: "ctx: flat market"   # bypass network
        digests = sup.run_cycle(history=_bars(60), max_questions=2)
        assert len(digests) >= 1
        assert all(d.findings for d in digests)
        assert any(m["metadata"]["kind"] == KIND_RESEARCH for m in v._mem)

    def test_identify_unknowns_always_returns_baseline_question(self):
        agent = ResearchSupervisor(vector=VectorStore(), llm=ClaudeClient(api_key=""),
                                   symbol="BNB").agent
        assert len(agent.identify_unknowns([])) >= 1


# ── 10. Co-pilot grounded answer ───────────────────────────────────────────────

class TestCoPilot:
    def test_answer_is_grounded_in_memory(self):
        v = VectorStore()
        v.upsert("r1", "buy in trend regime driven by momentum signal",
                 {"kind": KIND_REFLECTION, "outcome_label": "loss"})
        v.upsert("i1", "BNB: buy in trend regime driven by momentum signal",
                 {"kind": KIND_INSTITUTIONAL, "outcome_label": "win"})
        pilot = CoPilot(vector=v, llm=ClaudeClient(api_key=""), bridge=None)
        out = pilot.ask("what happens when we buy in a trend regime on momentum?")
        assert out["grounded"] is True
        assert out["sources"] and any(s["kind"] == KIND_REFLECTION for s in out["sources"])


# ── 11. Builder wiring ─────────────────────────────────────────────────────────

class TestBuilder:
    def test_offline_env_disables(self):
        sb = build_second_brain(env={})
        assert sb.enabled is False
        assert hasattr(sb, "avoidance") and hasattr(sb, "reflection_writer")

    def test_enabled_when_keys_present(self):
        sb = build_second_brain(env={"ANTHROPIC_API_KEY": "sk-test"})
        assert sb.enabled is True
        assert sb.llm.enabled is True
