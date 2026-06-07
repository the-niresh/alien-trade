"""
Hermes — the WRITE half of the self-learning loop.

After a position closes, the loop hands us {signals, regime, side, realized_pnl}.
We compress it into a one-line lesson, embed it under the *setup key* (so the
read path can find it later), and store it in three places:

  • Upstash Vector (kind="reflection")  — the searchable institutional memory
  • Convex `reflections` row             — the durable, auditable record
  • Convex `audit` log                   — "if it's not in Convex, it didn't happen"

The lesson is synthesised by the cheapest LLM tier (T0/Haiku, off the hot path);
with no API key it falls back to a deterministic rule-based lesson, so the loop
still learns offline. Zero changes to /core strategy code (locked decision #3).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.schema import KIND_REFLECTION, Reflection, setup_key
from agent.secondbrain.vector import VectorStore

_LESSON_SYSTEM = (
    "You are a trading post-mortem analyst. In ONE sentence (max 25 words), state "
    "the actionable lesson from this trade outcome for this market setup. No preamble."
)


@dataclass
class ReflectionWriter:
    vector: VectorStore
    llm: ClaudeClient
    bridge: Optional[object] = None      # ConvexBridge (duck-typed)
    enabled: bool = True

    def reflect(
        self,
        *,
        cycle_id: str,
        trade_id: Optional[str],
        timestamp_ms: int,
        regime: str,
        side: str,
        signals: dict,
        realized_pnl: float,
    ) -> Optional[Reflection]:
        """Emit + store one reflection. Never raises (off-hot-path, guarded)."""
        if not self.enabled:
            return None
        try:
            key = setup_key(regime, signals, side)
            r = Reflection(
                cycle_id=cycle_id, trade_id=trade_id, timestamp_ms=timestamp_ms,
                regime=regime, side=side, signals=signals,
                outcome_pnl_usd=float(realized_pnl), setup_key=key,
            )
            r.lesson = self._lesson(r)

            self.vector.upsert(
                id=f"refl-{cycle_id}",
                text=key,                       # embed the setup fingerprint
                metadata={
                    "kind": KIND_REFLECTION,
                    "setup_key": key,
                    "regime": regime,
                    "side": side,
                    "outcome_pnl_usd": round(r.outcome_pnl_usd, 4),
                    "outcome_label": r.outcome_label,
                    "lesson": r.lesson,
                    "timestamp_ms": timestamp_ms,
                },
            )
            self._persist(r)
            return r
        except Exception as e:  # noqa: BLE001 — learning must never crash a cycle
            print(f"[hermes] reflect failed: {e}")
            return None

    # ── lesson synthesis ─────────────────────────────────────────────────────────

    def _lesson(self, r: Reflection) -> str:
        if self.llm.enabled:
            prompt = (
                f"Setup: {r.setup_key}\n"
                f"Regime: {r.regime}\nSide: {r.side}\n"
                f"Signals: {json.dumps(r.signals, default=str)}\n"
                f"Outcome: {r.outcome_label} (realized PnL ${r.outcome_pnl_usd:.2f})\n"
                f"Lesson:"
            )
            res = self.llm.complete(prompt, system=_LESSON_SYSTEM, tier="T0", max_tokens=80)
            if not res.stub and res.text:
                return res.text
        return self._deterministic_lesson(r)

    @staticmethod
    def _deterministic_lesson(r: Reflection) -> str:
        verb = {"win": "reinforce", "loss": "avoid/penalize", "scratch": "neutral on"}[r.outcome_label]
        return (f"{verb} {r.side} entries in {r.regime} regime on this setup "
                f"(realized ${r.outcome_pnl_usd:.2f}).")

    # ── persistence ────────────────────────────────────────────────────────────

    def _persist(self, r: Reflection) -> None:
        b = self.bridge
        if b is None:
            return
        record = getattr(b, "record_reflection", None)
        if callable(record) and r.trade_id:
            record(
                trade_id=r.trade_id, cycle_id=r.cycle_id, timestamp_ms=r.timestamp_ms,
                signals_snapshot=json.dumps(r.signals, default=str), regime=r.regime,
                outcome_pnl_usd=r.outcome_pnl_usd, outcome_label=r.outcome_label,
                lesson=r.lesson, vector_id=f"refl-{r.cycle_id}",
            )
        audit = getattr(b, "audit", None)
        if callable(audit):
            audit("reflection", r.cycle_id, {
                "setup_key": r.setup_key, "outcome": r.outcome_label,
                "pnl": r.outcome_pnl_usd, "lesson": r.lesson,
            }, "info")
