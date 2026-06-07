"""
Assemble the Second Brain from environment config, with offline-safe defaults.

One place wires Vector + Redis cache + Claude + telemetry together and hands the
runtime the two cycle-relevant pieces (mistake-avoidance + reflection writer)
plus the async tools (co-pilot, research supervisor). If the env keys are
absent, every component degrades to its offline fallback — nothing here forces a
network dependency on the trade loop.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from strategy.combined import StrategyParams

from agent.secondbrain.avoidance import VectorMistakeAvoidance
from agent.secondbrain.cache import ResponseCache
from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.reflection import ReflectionWriter
from agent.secondbrain.telemetry import CostTelemetry
from agent.secondbrain.vector import VectorStore


@dataclass
class SecondBrain:
    vector: VectorStore
    llm: ClaudeClient
    cache: ResponseCache
    telemetry: CostTelemetry
    avoidance: VectorMistakeAvoidance
    reflection_writer: ReflectionWriter
    bridge: Optional[object] = None

    @property
    def enabled(self) -> bool:
        return self.vector.enabled or self.llm.enabled

    def copilot(self):
        from agent.secondbrain.copilot import CoPilot
        return CoPilot(vector=self.vector, llm=self.llm, bridge=self.bridge)

    def research(self, symbol: str = "BNB"):
        from agent.secondbrain.research import ResearchSupervisor
        return ResearchSupervisor(vector=self.vector, llm=self.llm, symbol=symbol)

    def close(self) -> None:
        for c in (self.vector, self.cache, self.llm):
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass


def build_second_brain(
    *,
    params: Optional[StrategyParams] = None,
    bridge: Optional[object] = None,
    env: Optional[dict] = None,
) -> SecondBrain:
    e = env if env is not None else os.environ
    params = params or StrategyParams()

    vector = VectorStore(
        url=e.get("UPSTASH_VECTOR_REST_URL", ""),
        token=e.get("UPSTASH_VECTOR_REST_TOKEN", ""),
    )
    cache = ResponseCache(
        url=e.get("UPSTASH_REDIS_REST_URL", ""),
        token=e.get("UPSTASH_REDIS_REST_TOKEN", ""),
    )
    telemetry = CostTelemetry()
    llm = ClaudeClient(
        api_key=e.get("ANTHROPIC_API_KEY", ""),
        cache=cache, telemetry=telemetry,
    )
    reflection_writer = ReflectionWriter(vector=vector, llm=llm, bridge=bridge)
    avoidance = VectorMistakeAvoidance(vector=vector, params=params)
    return SecondBrain(
        vector=vector, llm=llm, cache=cache, telemetry=telemetry,
        avoidance=avoidance, reflection_writer=reflection_writer, bridge=bridge,
    )
