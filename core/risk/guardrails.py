"""
Hard guardrails — all non-negotiable code-level limits.
Every check returns a GuardrailResult so the caller knows WHY a trade was blocked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

# ── Token allowlist ───────────────────────────────────────────────────────────
# A hard risk ceiling: the only tokens the agent will ever trade.
#
# This is a real control, not a formality. Two reasons it exists:
#   1. These five are the ONLY tokens the strategy was backtested on. Trading a
#      token outside this set means trading a setup that was never measured.
#   2. They are liquid majors with full CMC coverage for S1/S2, so the cost model
#      (gas + slippage + fees) is calibrated against real fills. On a thin pair,
#      slippage swamps any edge and the backtest stops predicting anything.
#
# Adding a token requires a clean walk-forward out-of-sample check first. Do not
# widen this list to chase a narrative.
#
# BNB / BTC / BTCB are deliberately absent: BNB is held for gas, and none of the
# three were part of the tested universe.
TRADING_UNIVERSE: tuple[str, ...] = (
    "ETH", "CAKE", "UNI", "LINK", "AAVE",
)
TOKEN_ALLOWLIST: frozenset[str] = frozenset(TRADING_UNIVERSE)


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class RiskConfig:
    # Hard trade limits
    max_trade_usd: float = 2_000.0          # per-trade size cap
    max_position_pct: float = 0.25          # max single position as % of capital
    max_open_exposure_pct: float = 0.30     # max CUMULATIVE open exposure as % of equity
    max_slippage_pct: float = 0.02          # abort if simulated slippage > 2% (executor retries at 5%/8% on TX_FAILED)
    token_allowlist: frozenset = field(default_factory=lambda: TOKEN_ALLOWLIST)

    # Daily-loss kill switch
    daily_loss_limit_pct: float = 0.05      # halt today if daily loss > 5% of capital

    # Circuit breaker
    max_consecutive_losses: int = 5         # pause after N back-to-back losses

    # Sizing params (used by RiskEngine + optimizer)
    target_vol_ann: float = 0.15            # 15% annualized target vol
    base_position_usd: float = 1_000.0      # base trade size before sizing adjustment

    # ── Stop-loss (exit rules — the WS1 drawdown lever) ───────────────────────
    atr_stop_mult: float = 2.0       # hard stop at entry - mult*ATR; 0 disables
    atr_trail_mult: float = 3.0      # trailing stop at high_water - mult*ATR; 0 disables
    atr_period: int = 14             # ATR lookback in bars


# ── Guard result ──────────────────────────────────────────────────────────────

class GuardrailResult(NamedTuple):
    allowed: bool
    reason: str   # empty string when allowed


# ── Checks ────────────────────────────────────────────────────────────────────

def check_guardrails(
    symbol: str,
    size_usd: float,
    daily_loss_pct: float,
    consecutive_losses: int,
    capital: float,
    config: RiskConfig,
) -> GuardrailResult:
    """
    Run all hard guardrail checks. Returns on the first violation.
    Order: most critical checks first (daily-loss → circuit breaker → caps → allowlist).
    """
    if daily_loss_pct >= config.daily_loss_limit_pct:
        return GuardrailResult(False,
            f"daily-loss halt: {daily_loss_pct:.2%} >= limit {config.daily_loss_limit_pct:.2%}")

    if consecutive_losses >= config.max_consecutive_losses:
        return GuardrailResult(False,
            f"circuit breaker: {consecutive_losses} consecutive losses")

    if size_usd > config.max_trade_usd:
        return GuardrailResult(False,
            f"trade size ${size_usd:.0f} > cap ${config.max_trade_usd:.0f}")

    if capital > 0 and (size_usd / capital) > config.max_position_pct:
        return GuardrailResult(False,
            f"position {size_usd/capital:.1%} > max {config.max_position_pct:.1%} of capital")

    if symbol not in config.token_allowlist:
        return GuardrailResult(False, f"token {symbol!r} not in allowlist")

    return GuardrailResult(True, "")


def check_max_exposure(
    open_exposure_usd: float,
    new_size_usd: float,
    equity: float,
    config: RiskConfig,
) -> GuardrailResult:
    """
    Cumulative open-exposure cap. `check_guardrails` only bounds a *single* trade
    vs capital; this bounds the *total* open position after adding `new_size_usd`,
    so a sequence of individually-legal buys can never pile past the cap. This is
    the max-exposure invariant the risk engine enforces on every buy. The bound
    must be provable rather than incidental — drawdown is the metric this agent is
    judged on, and an incidental bound is one that fails on the path nobody tested.
    """
    if equity <= 0:
        return GuardrailResult(True, "")
    cap = config.max_open_exposure_pct * equity
    projected = open_exposure_usd + new_size_usd
    if projected > cap + 1e-9:
        return GuardrailResult(False,
            f"max exposure: ${projected:.0f} > cap ${cap:.0f} "
            f"({config.max_open_exposure_pct:.0%} of equity)")
    return GuardrailResult(True, "")


class EquityFloorCheck(NamedTuple):
    halt: bool    # portfolio_usd <= floor_usd → halt immediately
    warn: bool    # portfolio_usd <= floor_usd * 1.20 (but > floor) → pre-alert
    reason: str


def check_equity_floor(portfolio_usd: float, floor_usd: float) -> EquityFloorCheck:
    """Capital floor guard. floor_usd=0 is a no-op (feature disabled).
    Pre-alert fires at 120% of floor so the operator has time to act.
    Only shrinks (never grows) position — sim treats floor=0 always."""
    if floor_usd <= 0:
        return EquityFloorCheck(halt=False, warn=False, reason="")
    if portfolio_usd <= floor_usd:
        return EquityFloorCheck(
            halt=True, warn=False,
            reason=f"equity floor: ${portfolio_usd:.2f} <= floor ${floor_usd:.2f}",
        )
    if portfolio_usd <= floor_usd * 1.20:
        return EquityFloorCheck(
            halt=False, warn=True,
            reason=(f"portfolio ${portfolio_usd:.2f} approaching floor "
                    f"${floor_usd:.2f} (warn at ${floor_usd * 1.20:.2f})"),
        )
    return EquityFloorCheck(halt=False, warn=False, reason="")


def check_slippage(simulated_slippage_pct: float, config: RiskConfig) -> GuardrailResult:
    """Pre-send slippage check — called after simulate-before-send (Step 5)."""
    if simulated_slippage_pct > config.max_slippage_pct:
        return GuardrailResult(False,
            f"slippage {simulated_slippage_pct:.2%} > cap {config.max_slippage_pct:.2%}")
    return GuardrailResult(True, "")
