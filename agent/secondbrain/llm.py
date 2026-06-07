"""
ClaudeClient — tier-routed LLM access for the Second Brain, with semantic cache
and cost telemetry baked in. Raw httpx against the Anthropic Messages API
(`POST /v1/messages`), matching the codebase's REST-first house style.

Model router (locked decision: LLM is OFF the trade hot path — this is only used
by reflection synthesis, AutoResearch, and the co-pilot):

    T0  claude-haiku-4-5    cheapest — short structured jobs (reflection lessons)
    T1  claude-sonnet-4-6   balanced — research synthesis, co-pilot default
    T2  claude-opus-4-8     deepest  — only when explicitly asked

Token optimisation: every call is cache-checked first (ResponseCache), routed to
the smallest adequate tier, and capped with max_tokens. Telemetry records the
saving vs a naive "always-Opus, no-cache" baseline.

Offline (no ANTHROPIC_API_KEY) it returns a deterministic extractive stub so the
loop, tests, and demo run with zero network — callers that need real synthesis
check `result.stub`.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from agent.secondbrain.cache import ResponseCache
from agent.secondbrain.schema import LLMResult
from agent.secondbrain.telemetry import CostTelemetry, cost_of

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Tier → model id (exact Anthropic catalog strings; no date suffixes).
MODEL_TIERS: dict[str, str] = {
    "T0": "claude-haiku-4-5",
    "T1": "claude-sonnet-4-6",
    "T2": "claude-opus-4-8",
}
DEFAULT_TIER = "T1"


@dataclass
class ClaudeClient:
    api_key: str = ""
    cache: ResponseCache = field(default_factory=ResponseCache)
    telemetry: CostTelemetry = field(default_factory=CostTelemetry)
    timeout: float = 60.0
    _http: Optional[httpx.Client] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.enabled:
            self._http = httpx.Client(timeout=self.timeout)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    def model_for(self, tier: str) -> str:
        return MODEL_TIERS.get(tier, MODEL_TIERS[DEFAULT_TIER])

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        tier: str = DEFAULT_TIER,
        max_tokens: int = 512,
        schema: Optional[dict] = None,
    ) -> LLMResult:
        """One LLM round-trip (cache → route → call). Never raises — falls back
        to a deterministic stub on any error so a Second-Brain task can't crash
        the runtime."""
        model = self.model_for(tier)
        ckey = ResponseCache.key(tier, system, prompt, max_tokens, bool(schema))

        cached = self.cache.get(ckey)
        if cached is not None:
            res = LLMResult(text=cached, tier=tier, model=model, cache_hit=True)
            self.telemetry.record(tier=tier, model=model, in_tokens=0, out_tokens=0,
                                  cost_usd=0.0, cache_hit=True, latency_s=0.0)
            return res

        if not self.enabled:
            res = _stub(prompt, system, tier, model)
            self.cache.set(ckey, res.text)   # exercise the cache offline too
            self.telemetry.record(tier=tier, model=model, in_tokens=0, out_tokens=0,
                                  cost_usd=0.0, cache_hit=False, latency_s=0.0)
            return res

        t0 = time.monotonic()
        try:
            text, in_tok, out_tok = self._call(model, system, prompt, max_tokens, schema)
        except Exception as e:  # noqa: BLE001 — degrade to stub, never crash
            print(f"[llm] {model} call failed: {e}")
            return _stub(prompt, system, tier, model)
        latency = time.monotonic() - t0

        cost = cost_of(model, in_tok, out_tok)
        self.cache.set(ckey, text)
        self.telemetry.record(tier=tier, model=model, in_tokens=in_tok, out_tokens=out_tok,
                              cost_usd=cost, cache_hit=False, latency_s=latency)
        return LLMResult(text=text, tier=tier, model=model, in_tokens=in_tok,
                         out_tokens=out_tok, cost_usd=cost, latency_s=latency)

    def _call(self, model, system, prompt, max_tokens, schema):
        body: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        if schema is not None:
            body["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
        r = self._http.post(ANTHROPIC_URL, json=body, headers={
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        })
        r.raise_for_status()
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text").strip()
        usage = data.get("usage", {})
        return text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))


def _stub(prompt: str, system: str, tier: str, model: str) -> LLMResult:
    """Deterministic offline answer: extract the prompt's salient lines. Lets the
    whole layer run without a key; callers needing real synthesis check .stub."""
    lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
    head = " ".join(lines[-3:]) if lines else prompt.strip()
    text = f"[offline summary] {head[:280]}"
    return LLMResult(text=text, tier=tier, model=model, stub=True)
