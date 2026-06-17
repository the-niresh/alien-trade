"""
Strategy Registry — named, user-selectable strategies over ONE engine.

The product wins by giving the user customization without ever forking the trade
logic. Every strategy here is a *preset* of StrategyParams fed to the same
combined.py engine (locked decision #2: sim and live share one code path; there is
no "contrarian engine" vs "momentum engine", only different weights/thresholds).

Strategies:
  momentum   — trend-follower; rides confirmed uptrends. Best in trending markets.
  contrarian — fear-buyer; the Fear & Greed signal is the backbone (buy capitulation,
               trim into greed), momentum is only a filter. Best in choppy/down/fear
               markets — which is the regime we are actually in (F&G ~ extreme fear).
  balanced   — blends momentum + derivatives + fear; regime-aware all-rounder.
  defensive  — cash-default; only rare, high-conviction longs. Minimises drawdown
               (pairs naturally with the Autopilot capital manager).

Risk profiles scale how much capital each entry risks (mapped to the RiskEngine caps
by the loop): conservative / balanced / aggressive.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from strategy.combined import StrategyParams


# ── Strategy presets (weights sum ~1.0; same engine, different emphasis) ───────

def _momentum(symbol: str) -> StrategyParams:
    return StrategyParams(
        symbol=symbol, ema_fast=8, ema_slow=21,
        w_momentum=0.65, w_derivatives=0.35, w_sentiment=0.0,
        entry_threshold=0.30, exit_threshold=-0.10,
    )


def _contrarian(symbol: str) -> StrategyParams:
    # Fear & Greed is the backbone; momentum only confirms. A lower entry threshold
    # lets the agent act on capitulation, where the long-only edge actually lives.
    # chop_gate=0.8: contrarian is DESIGNED for sideways/choppy markets — the
    # generic 0.5 CHOP gate halves scores and prevents entries in the exact regime
    # where this strategy has its edge.
    return StrategyParams(
        symbol=symbol, ema_fast=13, ema_slow=34,
        w_momentum=0.20, w_derivatives=0.20, w_sentiment=0.60,
        entry_threshold=0.20, exit_threshold=-0.05,
        chop_gate=0.8,
        bypass_trend_filter=True,
    )


def _balanced(symbol: str) -> StrategyParams:
    return StrategyParams(
        symbol=symbol, ema_fast=8, ema_slow=34,
        w_momentum=0.45, w_derivatives=0.25, w_sentiment=0.30,
        entry_threshold=0.30, exit_threshold=-0.10,
    )


def _defensive(symbol: str) -> StrategyParams:
    # High conviction only: rare entries, wide rebalance band -> minimal turnover,
    # minimal drawdown. The Autopilot floor + cash-default do the rest.
    return StrategyParams(
        symbol=symbol, ema_fast=8, ema_slow=34,
        w_momentum=0.50, w_derivatives=0.25, w_sentiment=0.25,
        entry_threshold=0.50, exit_threshold=-0.05, rebalance_band=0.25,
    )


@dataclass(frozen=True)
class StrategyInfo:
    name: str
    factory: callable          # (symbol:str) -> StrategyParams
    label: str
    blurb: str                 # one-line, shown in the cockpit picker


STRATEGIES: dict[str, StrategyInfo] = {
    "momentum":   StrategyInfo("momentum",   _momentum,
                               "Momentum", "Rides confirmed uptrends. Best in trending markets."),
    "contrarian": StrategyInfo("contrarian", _contrarian,
                               "Contrarian / Fear-Buyer",
                               "Buys capitulation, trims into greed. Best in choppy/down markets."),
    "balanced":   StrategyInfo("balanced",   _balanced,
                               "Balanced", "Momentum + derivatives + fear. Regime-aware all-rounder."),
    "defensive":  StrategyInfo("defensive",  _defensive,
                               "Cash-Defensive",
                               "Rare high-conviction longs only. Minimises drawdown."),
}

DEFAULT_STRATEGY = "balanced"


# ── Risk profiles (scale entry risk; mapped to RiskEngine caps by the loop) ────

@dataclass(frozen=True)
class RiskProfile:
    name: str
    max_position_pct: float    # cap on a single position as a fraction of capital
    target_vol_ann: float      # annualized vol target for the sizer
    label: str


RISK_PROFILES: dict[str, RiskProfile] = {
    "conservative": RiskProfile("conservative", 0.10, 0.08, "Conservative"),
    "balanced":     RiskProfile("balanced",     0.25, 0.15, "Balanced"),
    "aggressive":   RiskProfile("aggressive",   0.50, 0.25, "Aggressive"),
}

DEFAULT_RISK_PROFILE = "balanced"


# ── Resolvers ──────────────────────────────────────────────────────────────────

def get_strategy_params(name: str, symbol: str = "ETH") -> StrategyParams:
    """Resolve a strategy name -> StrategyParams. Unknown name falls back to the
    default (never raises — a bad config value must not crash the live loop)."""
    info = STRATEGIES.get((name or "").lower(), STRATEGIES[DEFAULT_STRATEGY])
    return info.factory(symbol)


def get_risk_profile(name: str) -> RiskProfile:
    """Resolve a risk-profile name -> RiskProfile (fail-safe to balanced)."""
    return RISK_PROFILES.get((name or "").lower(), RISK_PROFILES[DEFAULT_RISK_PROFILE])


def list_strategies() -> list[dict]:
    """Cockpit picker payload: [{name, label, blurb}, ...]."""
    return [{"name": s.name, "label": s.label, "blurb": s.blurb} for s in STRATEGIES.values()]
