"""
Second Brain - the LLM + memory layer (Step 6), strictly OFF the trade hot path.

Locked decision #1: the buy/sell decision is deterministic Python in /core. The
LLM and the vector memory earn their place only in:

  • Hermes self-learning   - post-trade reflection (write) + pre-trade
                             mistake-avoidance (read). See reflection.py / avoidance.py.
  • 2-year institutional   - one-time walk-forward labelled memory. See preload.py.
  • Karpathy AutoResearch  - async research sub-agent → market digest. See research.py.
  • Co-pilot chat          - grounded Q&A over the Second Brain. See copilot.py.

Everything degrades gracefully offline (no Upstash / no Anthropic key): the
vector store falls back to an in-memory token-overlap index and the LLM returns
a deterministic extractive stub, so the loop, the tests, and a laptop demo all
run with zero network. The mistake-avoidance read is the only Second-Brain call
on the cycle path and it never invokes the LLM - it is a pure vector lookup with
deterministic thresholds.
"""
from __future__ import annotations

from agent.secondbrain.builder import SecondBrain, build_second_brain

__all__ = ["SecondBrain", "build_second_brain"]
