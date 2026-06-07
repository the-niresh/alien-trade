"""
Hard guardrails — all non-negotiable code-level limits.
Every check returns a GuardrailResult so the caller knows WHY a trade was blocked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

# ── Token allowlist ───────────────────────────────────────────────────────────

TOKEN_ALLOWLIST: frozenset[str] = frozenset({"BNB", "BTC", "BTCB", "ETH"})


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class RiskConfig:
    # Hard trade limits
    max_trade_usd: float = 2_000.0          # per-trade size cap
    max_position_pct: float = 0.25          # max single position as % of capital
    max_slippage_pct: float = 0.02          # abort if simulated slippage > 2%
    token_allowlist: frozenset = field(default_factory=lambda: TOKEN_ALLOWLIST)

    # Daily-loss kill switch
    daily_loss_limit_pct: float = 0.05      # halt today if daily loss > 5% of capital

    # Circuit breaker
    max_consecutive_losses: int = 5         # pause after N back-to-back losses

    # Sizing params (used by RiskEngine + optimizer)
    target_vol_ann: float = 0.15            # 15% annualized target vol
    base_position_usd: float = 1_000.0      # base trade size before sizing adjustment


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


def check_slippage(simulated_slippage_pct: float, config: RiskConfig) -> GuardrailResult:
    """Pre-send slippage check — called after simulate-before-send (Step 5)."""
    if simulated_slippage_pct > config.max_slippage_pct:
        return GuardrailResult(False,
            f"slippage {simulated_slippage_pct:.2%} > cap {config.max_slippage_pct:.2%}")
    return GuardrailResult(True, "")
