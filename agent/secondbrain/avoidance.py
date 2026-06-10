"""
Hermes — the READ half of the self-learning loop.

Before the executor runs, the loop asks: "have we lost on this exact setup
before?" This implements `agent.brain.MistakeAvoidance` with a pure Upstash
Vector lookup — NO LLM on the cycle path (locked decision #1). It recomputes the
same deterministic signal breakdown the strategy used, builds the *setup key*,
and queries past reflections stored under that key.

Verdict is deterministic and fail-open: if the memory is empty, offline, or
erroring, it returns "allow" — it can only ever *tighten* a trade the /core risk
engine already approved, never loosen the risk floor. Evidence thresholds:

    loss_rate ≥ 0.75 on ≥ MIN_SAMPLES similar setups, net negative  → block
    loss_rate ≥ 0.50 on ≥ MIN_SAMPLES similar setups, net negative  → size_penalty
    otherwise                                                        → allow
"""
from __future__ import annotations

from dataclasses import dataclass

from backtest.engine import Bar, Order
from strategy.combined import StrategyParams, score_breakdown

from agent.brain import AvoidanceVerdict
from agent.secondbrain.schema import KIND_REFLECTION, setup_key
from agent.secondbrain.vector import VectorStore

SIM_THRESHOLD = 0.55      # min similarity to treat a memory as "the same setup"
MIN_SAMPLES = 2           # need at least this many before acting on history
TOP_K = 8
BLOCK_LOSS_RATE = 0.75
PENALTY_LOSS_RATE = 0.50
SIZE_PENALTY = 0.50       # shrink the order by half on a "soft" bad setup


@dataclass
class VectorMistakeAvoidance:
    vector: VectorStore
    params: StrategyParams

    def check(self, history: list[Bar], order: Order, regime: str) -> AvoidanceVerdict:
        try:
            breakdown = score_breakdown(history, self.params)
            signals = {k: breakdown.get(k) for k in ("momentum", "derivatives", "sentiment", "flow")}
            key = setup_key(regime, signals, order.side)

            hits = self.vector.query(key, top_k=TOP_K, kind=KIND_REFLECTION)
            similar = [h for h in hits if h.score >= SIM_THRESHOLD]
            if len(similar) < MIN_SAMPLES:
                return AvoidanceVerdict(block=False, reason="no prior evidence")

            outcomes = [float(h.metadata.get("outcome_pnl_usd", 0.0)) for h in similar]
            losses = [p for p in outcomes if p < 0]
            net = sum(outcomes)
            loss_rate = len(losses) / len(similar)

            if loss_rate >= BLOCK_LOSS_RATE and net < 0:
                return AvoidanceVerdict(
                    block=True,
                    reason=(f"lost on this setup {len(losses)}/{len(similar)} times "
                            f"(net ${net:.0f}) — blocking"),
                )
            if loss_rate >= PENALTY_LOSS_RATE and net < 0:
                return AvoidanceVerdict(
                    block=False, size_penalty=SIZE_PENALTY,
                    reason=(f"mixed history {len(losses)}/{len(similar)} losses "
                            f"(net ${net:.0f}) — halving size"),
                )
            return AvoidanceVerdict(block=False, reason="prior setups net non-negative")
        except Exception as e:  # noqa: BLE001 — read must never crash a cycle
            print(f"[hermes] avoidance check failed: {e}")
            return AvoidanceVerdict(block=False, reason="avoidance error — fail-open")
