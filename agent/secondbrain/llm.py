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

Resilience: Claude is primary. If the Anthropic call fails (API down / 5xx /
network) and an OPENAI_API_KEY is configured, the call transparently falls back to
OpenAI so the off-hot-path LLM layers never go dark on a 24/7 deploy. Only if every
configured provider fails does it degrade to the offline stub.

Offline (no provider key) it returns a deterministic extractive stub so the loop,
tests, and demo run with zero network — callers that need real synthesis check
`result.stub`.
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

# ── OpenAI fallback ───────────────────────────────────────────────────────────
# Used ONLY when the Anthropic call fails (API down / 5xx / network). Claude stays
# primary; this just keeps the off-hot-path LLM layers (reflection, research,
# co-pilot) alive when Anthropic is unreachable so the 24/7 agent never goes dark.
# A single capable+cheap model is enough for a failover — override via
# OPENAI_FALLBACK_MODEL. Tier is collapsed to this one model on the fallback path.
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_FALLBACK_MODEL = "gpt-4o-mini"


@dataclass
class ClaudeClient:
    api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = OPENAI_FALLBACK_MODEL
    cache: ResponseCache = field(default_factory=ResponseCache)
    telemetry: CostTelemetry = field(default_factory=CostTelemetry)
    timeout: float = 60.0
    _http: Optional[httpx.Client] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.enabled:
            self._http = httpx.Client(timeout=self.timeout)

    @property
    def enabled(self) -> bool:
        # Either provider is enough to be "live"; OpenAI alone makes it the primary.
        return bool(self.api_key or self.openai_api_key)

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
            text, in_tok, out_tok, used_model = self._generate(
                model, system, prompt, max_tokens, schema)
        except Exception as e:  # noqa: BLE001 — degrade to stub, never crash
            print(f"[llm] all providers failed: {e}")
            return _stub(prompt, system, tier, model)
        latency = time.monotonic() - t0

        cost = cost_of(used_model, in_tok, out_tok)
        self.cache.set(ckey, text)
        self.telemetry.record(tier=tier, model=used_model, in_tokens=in_tok, out_tokens=out_tok,
                              cost_usd=cost, cache_hit=False, latency_s=latency)
        return LLMResult(text=text, tier=tier, model=used_model, in_tokens=in_tok,
                         out_tokens=out_tok, cost_usd=cost, latency_s=latency)

    def _generate(self, model, system, prompt, max_tokens, schema):
        """Anthropic primary → OpenAI fallback. Returns (text, in_tok, out_tok,
        used_model) or raises if every configured provider fails. Tries Claude
        first whenever an Anthropic key is present; only on its failure does it
        fall through to OpenAI (locked decision: Claude is primary)."""
        errors: list[str] = []
        if self.api_key:
            try:
                text, in_tok, out_tok = self._call_anthropic(
                    model, system, prompt, max_tokens, schema)
                return text, in_tok, out_tok, model
            except Exception as e:  # noqa: BLE001
                errors.append(f"anthropic/{model}: {e}")
                if self.openai_api_key:
                    print(f"[llm] anthropic {model} failed ({e}); falling back to "
                          f"openai/{self.openai_model}")
        if self.openai_api_key:
            try:
                text, in_tok, out_tok = self._call_openai(
                    self.openai_model, system, prompt, max_tokens, schema)
                return text, in_tok, out_tok, self.openai_model
            except Exception as e:  # noqa: BLE001
                errors.append(f"openai/{self.openai_model}: {e}")
        raise RuntimeError("; ".join(errors) or "no LLM provider configured")

    def _call_anthropic(self, model, system, prompt, max_tokens, schema):
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

    def _call_openai(self, model, system, prompt, max_tokens, schema):
        """OpenAI Chat Completions fallback. Best-effort JSON when a schema is
        requested (json_object mode) — the caller already parses defensively."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if schema is not None:
            body["response_format"] = {"type": "json_object"}
        r = self._http.post(OPENAI_URL, json=body, headers={
            "authorization": f"Bearer {self.openai_api_key}",
            "content-type": "application/json",
        })
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices", [])
        text = (choices[0].get("message", {}).get("content", "") if choices else "").strip()
        usage = data.get("usage", {})
        return text, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))


def _stub(prompt: str, system: str, tier: str, model: str) -> LLMResult:
    """Deterministic offline answer: extract the prompt's salient lines. Lets the
    whole layer run without a key; callers needing real synthesis check .stub."""
    lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
    head = " ".join(lines[-3:]) if lines else prompt.strip()
    text = f"[offline summary] {head[:280]}"
    return LLMResult(text=text, tier=tier, model=model, stub=True)
