"""
KOL stance -> trade intent. PURE and deterministic (no LLM, no I/O): it maps the
existing deterministic SentimentReading into one of three bounded actions, gated
by the eligible-token allowlist and the spot-long-only scoring rule.

  bullish + eligible + flat   -> open_long   (a scored twak swap long)
  bearish + eligible + held   -> reduce      (capital preservation; never a short)
  everything else             -> none

This is the seam the loop's _apply_kol_signal overlay consumes; the overlay still
runs every resulting order through check_guardrails, so this layer never sizes.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent.social.schema import SentimentReading
from core.risk.guardrails import TOKEN_ALLOWLIST


@dataclass(frozen=True)
class KolIntent:
    symbol: str
    action: str        # "open_long" | "reduce" | "none"
    confidence: float
    reason: str


def kol_intent(
    reading: SentimentReading,
    *,
    holds_symbol: bool,
    score_open: float = 0.35,
    score_close: float = -0.35,
    min_conf: float = 0.5,
) -> KolIntent:
    sym = reading.symbol.upper()
    if sym not in TOKEN_ALLOWLIST:
        return KolIntent(sym, "none", reading.confidence, "token not in eligible allowlist")
    if reading.confidence < min_conf:
        return KolIntent(sym, "none", reading.confidence, "confidence below threshold")
    if reading.score >= score_open:
        return KolIntent(sym, "open_long", reading.confidence,
                         f"bullish KOL score {reading.score:+.2f}")
    if reading.score <= score_close and holds_symbol:
        return KolIntent(sym, "reduce", reading.confidence,
                         f"bearish KOL score {reading.score:+.2f} — de-risk held long")
    return KolIntent(sym, "none", reading.confidence, "no actionable stance")
