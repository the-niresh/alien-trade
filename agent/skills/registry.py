"""
Curated skill registry - the static map from "what we need" to a pinned CMC skill
(unique_name + a param-builder that matches that skill's input_schema exactly).

This is Tier 1 of the two-tier loader (the other tier is dynamic `find_skill`):
for the handful of skills that map to our signals we skip discovery entirely and
call `execute_skill` directly with correct params. Every skill here is RESEARCH
context only - locked decision #1 keeps them off the deterministic trade path;
they feed the AutoResearch digest, regime narrative, co-pilot, and at most the
shrink-only Option-B forecast.

Param builders are written against the schemas returned by find_skill (window
formats and enums differ per skill), so each sends only schema-valid keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Allowed enum values per the skills' schemas (validated/clamped in builders).
_OI_WINDOWS = ("1h", "4h", "12h", "24h")
_REGIME_WINDOWS = ("1d", "7d", "30d", "90d")
_DIRECTIONS = ("long", "short", "neutral")


@dataclass
class SkillContext:
    """The agent's current research context; builders pull what each skill needs."""
    symbol: str = "ETH"
    name: str = ""                              # full name to disambiguate / social query
    window_days: int = 30                       # for Nd-format skills
    oi_window: str = "4h"                       # one of _OI_WINDOWS
    regime_window: str = "30d"                  # one of _REGIME_WINDOWS
    venues: tuple[str, ...] = ("Binance", "OKX", "Bybit")
    direction: str = "neutral"                  # one of _DIRECTIONS
    lookback_hours: int = 24
    lookback_days: int = 14

    def social_query(self) -> str:
        return f"{self.name} OR {self.symbol}" if self.name else self.symbol

    # clamped accessors so a bad context can never send an invalid enum
    def oi_win(self) -> str:
        return self.oi_window if self.oi_window in _OI_WINDOWS else "4h"

    def regime_win(self) -> str:
        return self.regime_window if self.regime_window in _REGIME_WINDOWS else "30d"

    def dir_(self) -> str:
        return self.direction if self.direction in _DIRECTIONS else "neutral"

    def nd(self) -> str:
        return f"{max(2, min(self.window_days, 90))}d"


@dataclass(frozen=True)
class CuratedSkill:
    key: str                                    # our internal handle
    unique_name: str                            # the hub's uniqueName (verified)
    signal: str                                 # S2 | S3 | S4 | regime
    when_to_use: str                            # one-line guidance (for prompt manifest)
    build: Callable[[SkillContext], dict]       # ctx -> params matching input_schema


# ── Param builders (each respects its skill's schema) ──────────────────────────

def _funding_regime(c: SkillContext) -> dict:
    return {"symbol": c.symbol, "venue": c.venues[0], "window": c.nd()}

def _funding_compare(c: SkillContext) -> dict:
    return {"symbol": c.symbol, "venues": list(c.venues[:8]),
            "window": c.nd(), "direction": c.dir_()}

def _oi_dark_flow(c: SkillContext) -> dict:
    return {"symbol": c.symbol, "venue": c.venues[0],
            "window": c.oi_win(), "lookback_days": c.lookback_days}

def _kol_sentiment(c: SkillContext) -> dict:
    return {"symbol": c.symbol}

def _social_divergence(c: SkillContext) -> dict:
    return {"query": c.social_query(), "symbol": c.symbol,
            "lookback_hours": c.lookback_hours, "max_posts": 10}

def _exchange_flow(c: SkillContext) -> dict:
    return {"symbol": c.symbol, "window": c.nd()}

def _etf_perp(c: SkillContext) -> dict:
    return {"symbol": c.symbol, "window": c.nd()}

def _market_regime(c: SkillContext) -> dict:
    return {"time_window": c.regime_win()}


# ── The registry ───────────────────────────────────────────────────────────────

CURATED: dict[str, CuratedSkill] = {
    s.key: s for s in (
        CuratedSkill("funding_regime", "detect_funding_rate_regime_shift", "S2",
                     "Has funding shifted into a new long/short/neutral regime?", _funding_regime),
        CuratedSkill("funding_compare", "compare_funding_rate_across_venues", "S2",
                     "Where is long/short carry hottest/cheapest across venues?", _funding_compare),
        CuratedSkill("oi_dark_flow", "detect_oi_dark_flow_setup", "S2",
                     "Is OI growth diverging from bounded price (hidden positioning)?", _oi_dark_flow),
        CuratedSkill("kol_sentiment", "altcoin_kol_sentiment", "S3",
                     "What is KOL/community sentiment + narrative quality on the token?", _kol_sentiment),
        CuratedSkill("social_divergence", "track_social_price_divergence", "S3",
                     "Is social attention diverging from short-term price?", _social_divergence),
        CuratedSkill("exchange_flow", "track_exchange_inflow_outflow_pressure", "S4",
                     "Do exchange reserves imply inflow (distribution) or outflow (accumulation)?", _exchange_flow),
        CuratedSkill("etf_perp", "review_etf_flow_vs_perp_sentiment", "S4",
                     "Is ETF flow vs perp sentiment risk-on, defensive, or short-squeeze-prone?", _etf_perp),
        CuratedSkill("market_regime", "detect_market_regime", "regime",
                     "Direct market-wide regime label (trend/chop/overheated/stress).", _market_regime),
    )
}


def manifest() -> str:
    """A compact, injectable description of the curated skills (key · signal · use)
    - what a research/co-pilot agent reads to pick a curated skill without a
    find_skill round-trip."""
    return "\n".join(
        f"- {s.key} [{s.signal}]: {s.when_to_use}" for s in CURATED.values()
    )


# Keyword → curated key. Lets the co-pilot answer common questions with a known-good
# curated skill (reliable params) before falling back to dynamic find_skill.
_TRIGGERS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("funding", "carry", "perp"), "funding_regime"),
    (("open interest", " oi ", "crowded", "positioning", "dark flow"), "oi_dark_flow"),
    (("sentiment", "social", "kol", "twitter", "narrative", "chatter"), "kol_sentiment"),
    (("flow", "inflow", "outflow", "reserve", "whale", "accumulat", "distribut"), "exchange_flow"),
    (("etf",), "etf_perp"),
    (("venue", "across exchange", "cheapest", "hottest"), "funding_compare"),
    (("regime", "trend", "chop", "overheated", "risk-on", "risk off"), "market_regime"),
)


def route_curated(question: str) -> list[str]:
    """Curated skill keys whose triggers appear in the question (deduped, in
    trigger order). Empty → no curated match, caller should fall back to dynamic."""
    q = f" {(question or '').lower()} "
    keys: list[str] = []
    for terms, key in _TRIGGERS:
        if key not in keys and any(t in q for t in terms):
            keys.append(key)
    return keys
