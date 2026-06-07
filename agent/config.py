"""
AgentConfig — single typed config object for the live runtime.

Loads from .env.local (already loaded by core modules) with sane defaults.
The strategy + risk params come straight from /core so sim and live are
configured the same way.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from risk.guardrails import RiskConfig
from strategy.combined import StrategyParams

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

VALID_MODES = ("paper", "testnet", "mainnet")


@dataclass
class AgentConfig:
    # Market
    symbol: str = "BNB"
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

    # Convex bus
    convex_url: str = field(default_factory=lambda: os.environ.get("CONVEX_URL", ""))

    # PWA URL rendered as a terminal QR on startup
    pwa_url: str = field(default_factory=lambda: os.environ.get("PWA_URL", ""))

    # Second Brain (Step 6 — Hermes + AutoResearch + co-pilot). Off the hot path.
    # Disable with SECOND_BRAIN=0. When on but Upstash/Anthropic keys are absent,
    # every component degrades to its offline fallback (no network dependency).
    second_brain_enabled: bool = field(
        default_factory=lambda: os.environ.get("SECOND_BRAIN", "1").lower()
        not in ("0", "false", "no"))

    # Sub-configs from /core (shared with the sim)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyParams = field(default_factory=StrategyParams)

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
