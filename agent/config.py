"""
AgentConfig - single typed config object for the live runtime.

Loads from .env.local (already loaded by core modules) with sane defaults.
The strategy + risk params come straight from /core so sim and live are
configured the same way.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from risk.autopilot import AutopilotConfig
from risk.guardrails import RiskConfig
from strategy.combined import StrategyParams
from strategy.registry import get_strategy_params

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

VALID_MODES = ("paper", "testnet", "mainnet")


def _env_float(name: str):
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _autopilot_from_env() -> AutopilotConfig:
    """Build the Autopilot capital-manager config from env. Disabled by default so
    sim/paper parity holds; the operator turns it on for the live/testnet run."""
    blocked = tuple(
        s.strip() for s in os.environ.get("AUTOPILOT_BLOCK_REGIMES", "crash,high_vol").split(",")
        if s.strip()
    )
    return AutopilotConfig(
        enabled=os.environ.get("AUTOPILOT", "").lower() in ("1", "true", "yes"),
        profit_target_pct=_env_float("AUTOPILOT_PROFIT_TARGET_PCT"),
        profit_target_abs=_env_float("AUTOPILOT_PROFIT_TARGET_ABS"),
        protect_principal=os.environ.get("AUTOPILOT_PROTECT_PRINCIPAL", "1").lower()
        not in ("0", "false", "no"),
        min_recycle_confidence=_env_float("AUTOPILOT_MIN_RECYCLE_CONF") or 0.0,
        recycle_blocked_regimes=blocked,
        trailing_giveback_pct=_env_float("AUTOPILOT_TRAIL_GIVEBACK_PCT"),
        daily_profit_target_pct=_env_float("AUTOPILOT_DAILY_TARGET_PCT"),
        loss_cooldown_hours=_env_float("AUTOPILOT_LOSS_COOLDOWN_HOURS") or 0.0,
    )


@dataclass
class AgentConfig:
    # Market - must be in risk.guardrails.TOKEN_ALLOWLIST (BNB/BTC/BTCB are never traded).
    symbol: str = "ETH"
    bar_interval: str = "1h"          # decision cadence (matches STRATEGY.md)
    history_bars: int = 200           # rolling window handed to the strategy

    # Capital + mode
    initial_capital: float = 10_000.0
    mode: str = field(default_factory=lambda: os.environ.get("TRADING_MODE", "paper"))

    # Wallet (mainnet/testnet only; managed via TWAK credentials)
    wallet_address: str = field(default_factory=lambda: os.environ.get("WALLET_ADDRESS", ""))

    # Live execution backend: "twak" (self-custody CLI, mainnet) | "raw" (BNB SDK + key)
    execution_backend: str = field(
        default_factory=lambda: os.environ.get("EXECUTION_BACKEND", "twak"))
    chain: str = "bsc"

    # Loop cadence (seconds between cycles when running live/forever)
    cycle_seconds: int = 3600

    # Minimum-activity mode: force >= 1 trade/day. OFF by default - a forced trade
    # has no signal behind it and makes a live run diverge from the backtest. Enable
    # only if an external rule requires it (ACTIVITY_FLOOR=1 or --activity-floor).
    enforce_activity_floor: bool = field(
        default_factory=lambda: os.environ.get("ACTIVITY_FLOOR", "").lower()
        in ("1", "true", "yes"))
    activity_trade_usd: float = field(
        default_factory=lambda: float(os.environ.get("ACTIVITY_TRADE_USD", "15.0")))

    # Convex bus
    convex_url: str = field(default_factory=lambda: os.environ.get("CONVEX_URL", ""))

    # PWA URL rendered as a terminal QR on startup
    pwa_url: str = field(default_factory=lambda: os.environ.get("PWA_URL", ""))

    # Second Brain (Step 6 - Hermes + AutoResearch + co-pilot). Off the hot path.
    # Disable with SECOND_BRAIN=0. When on but Upstash/Anthropic keys are absent,
    # every component degrades to its offline fallback (no network dependency).
    second_brain_enabled: bool = field(
        default_factory=lambda: os.environ.get("SECOND_BRAIN", "1").lower()
        not in ("0", "false", "no"))

    # Named strategy from the registry (momentum|contrarian|balanced|defensive).
    # Resolved into `strategy` params below, carrying the chosen symbol.
    strategy_name: str = field(default_factory=lambda: os.environ.get("STRATEGY_NAME", ""))

    # Sub-configs from /core (shared with the sim)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyParams = field(default_factory=StrategyParams)

    # Autopilot capital manager (profit-lock + ratchet + trailing + daily target).
    # Off by default (sim/paper parity); operator enables via AUTOPILOT=1 env.
    autopilot: AutopilotConfig = field(default_factory=_autopilot_from_env)

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
        # A named strategy overrides the default params (keeping the chosen symbol).
        if self.strategy_name:
            self.strategy = get_strategy_params(self.strategy_name, symbol=self.symbol)
        # Allow position size override via env so live capital doesn't have to match
        # the backtest's notional $1000. On mainnet with $5 wallet, set POSITION_SIZE_USD=4.
        pos_override = os.environ.get("POSITION_SIZE_USD", "").strip()
        if pos_override:
            try:
                from dataclasses import replace as _replace
                self.strategy = _replace(self.strategy, position_size_usd=float(pos_override))
            except (ValueError, TypeError):
                pass
