"""
Cost telemetry — per-call {tier, in/out tokens, cost, cache_hit, latency} plus a
running "$ saved vs naive baseline".

The naive baseline = every call routed to the top tier (Opus) with no cache. The
saving is (what Opus would have cost for the same tokens) − (what we actually
paid). Tier routing + semantic cache is the whole token-optimisation story, and
this turns it into a number we can put on a slide.

Pricing is per the Anthropic model catalog (USD per 1M tokens), kept beside the
router so they can't drift apart.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# USD per 1M tokens — Anthropic catalog. Keep in sync with llm.MODEL_TIERS.
PRICING: dict[str, tuple[float, float]] = {   # model -> (input, output)
    "claude-opus-4-8":   (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5":  (1.00,  5.00),
    # OpenAI fallback models (only billed when Claude is down — see llm.py)
    "gpt-4o-mini":       (0.15,  0.60),
    "gpt-4o":            (2.50, 10.00),
}
BASELINE_MODEL = "claude-opus-4-8"   # naive = always top tier, no cache


def cost_of(model: str, in_tokens: int, out_tokens: int) -> float:
    pin, pout = PRICING.get(model, PRICING[BASELINE_MODEL])
    return (in_tokens * pin + out_tokens * pout) / 1_000_000.0


@dataclass
class CostTelemetry:
    calls: int = 0
    cache_hits: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    actual_cost_usd: float = 0.0
    baseline_cost_usd: float = 0.0     # if every call were Opus, uncached
    total_latency_s: float = 0.0
    by_tier: dict[str, int] = field(default_factory=dict)

    def record(self, *, tier: str, model: str, in_tokens: int, out_tokens: int,
               cost_usd: float, cache_hit: bool, latency_s: float) -> None:
        self.calls += 1
        self.by_tier[tier] = self.by_tier.get(tier, 0) + 1
        self.total_latency_s += latency_s
        if cache_hit:
            self.cache_hits += 1
            # A cache hit still counts against the baseline (Opus would have paid).
            self.baseline_cost_usd += cost_of(BASELINE_MODEL, in_tokens, out_tokens)
            return
        self.in_tokens += in_tokens
        self.out_tokens += out_tokens
        self.actual_cost_usd += cost_usd
        self.baseline_cost_usd += cost_of(BASELINE_MODEL, in_tokens, out_tokens)

    @property
    def saved_usd(self) -> float:
        return max(self.baseline_cost_usd - self.actual_cost_usd, 0.0)

    @property
    def cache_hit_rate(self) -> float:
        return self.cache_hits / self.calls if self.calls else 0.0

    def snapshot(self) -> dict:
        return {
            "calls": self.calls,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "in_tokens": self.in_tokens,
            "out_tokens": self.out_tokens,
            "actual_cost_usd": round(self.actual_cost_usd, 6),
            "baseline_cost_usd": round(self.baseline_cost_usd, 6),
            "saved_usd": round(self.saved_usd, 6),
            "avg_latency_s": round(self.total_latency_s / self.calls, 4) if self.calls else 0.0,
            "by_tier": dict(self.by_tier),
        }
