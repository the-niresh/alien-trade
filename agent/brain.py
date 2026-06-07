"""
Mistake-avoidance hook (Hermes loop seam).

Before executing, the loop asks: "have we lost on this exact setup/regime
before?" In Step 6 this is wired to Upstash Vector. For Step 5 the default is
AllowAll (no-op), so the seam exists and is tested but the live path is unchanged.
Keeping the interface here means /core strategy code never has to change when the
learning loop lands.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backtest.engine import Bar, Order


@dataclass
class AvoidanceVerdict:
    block: bool = False
    size_penalty: float = 0.0   # 0..1 fraction to shrink the order (Step 6)
    reason: str = ""


class MistakeAvoidance(Protocol):
    def check(self, history: list[Bar], order: Order, regime: str) -> AvoidanceVerdict: ...


class AllowAll:
    """Default: never blocks. Replaced by a Vector-backed lookup in Step 6."""

    def check(self, history: list[Bar], order: Order, regime: str) -> AvoidanceVerdict:
        return AvoidanceVerdict(block=False)
