"""
Track-2 strategy skill — exposes the Alien-Trade multi-signal score as a
callable CMC Skill endpoint.

Input schema:  {symbol: str, lookback_bars: int = 60}
Output schema: {symbol, timestamp, regime, regime_gate, momentum_score,
                derivatives_score, sentiment_score, flow_score,
                composite_score, verdict, signal_strength, bars_used[, error]}

The same /core strategy that drives the live agent is queryable as a hosted
skill. Other AI agents can call POST /skill/signal_score to get a structured,
walk-forward-validated signal score for any token on the tested allowlist.

The implementation is a thin wrapper: fetch recent daily bars from Binance
(free, no auth), pass to /core score_breakdown(), rename fields to the public
schema. Zero /core duplication, zero LLM on this path.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional


ELIGIBLE_SYMBOLS = ("ETH", "CAKE", "UNI", "LINK", "AAVE")
DEFAULT_LOOKBACK = 60
MIN_LOOKBACK = 30
MAX_LOOKBACK = 200

# Skill identity — matches skill_manifest.json
SKILL_UNIQUE_NAME = "alien_trade_multi_signal_score"
SKILL_VERSION = "1.0.0"


@dataclass
class SignalScoreResult:
    symbol: str
    timestamp: str
    regime: str
    regime_gate: float
    momentum_score: float
    derivatives_score: float
    sentiment_score: float
    flow_score: float
    composite_score: float
    verdict: str            # "buy" | "sell" | "hold"
    signal_strength: str    # "strong" | "moderate" | "weak"
    bars_used: int
    error: Optional[str] = field(default=None)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()}
        if self.error is None:
            del d["error"]
        return d


class SignalScoreSkill:
    """
    Computes the Alien-Trade multi-signal score for a BSC-eligible token.

    Fetches recent daily bars from Binance (free, no key), runs the /core
    signal library (S1 momentum + S2 derivatives + S3 sentiment + S4 flow),
    returns a structured verdict. Offline-safe: returns an error result rather
    than raising if data fetch or computation fails.
    """

    def __init__(self) -> None:
        # Import lazily so the file is importable without /core on PYTHONPATH
        from strategy.combined import StrategyParams  # noqa: PLC0415
        self._params = StrategyParams()

    def compute(self, symbol: str, lookback_bars: int = DEFAULT_LOOKBACK) -> SignalScoreResult:
        symbol = symbol.upper().strip()
        if symbol not in ELIGIBLE_SYMBOLS:
            return self._error(symbol, 0,
                               f"Symbol {symbol!r} not eligible; allowed: {ELIGIBLE_SYMBOLS}")

        lookback_bars = max(MIN_LOOKBACK, min(lookback_bars, MAX_LOOKBACK))
        fetch_limit = lookback_bars + 50   # warm-up bars so EMA has history

        try:
            from data.binance_client import BinanceClient  # noqa: PLC0415
            client = BinanceClient()
            bars = client.fetch_recent_bars(symbol, interval="daily", limit=fetch_limit)
        except Exception as exc:  # noqa: BLE001
            return self._error(symbol, lookback_bars, f"Data fetch failed: {exc}")

        if len(bars) < MIN_LOOKBACK:
            return self._error(symbol, len(bars),
                               f"Insufficient data: got {len(bars)} bars, need {MIN_LOOKBACK}")

        history = bars[-lookback_bars:]
        try:
            from strategy.combined import score_breakdown  # noqa: PLC0415
            bd = score_breakdown(history, self._params)
        except Exception as exc:  # noqa: BLE001
            return self._error(symbol, len(history), f"Signal computation failed: {exc}")

        composite = bd["target"]
        return SignalScoreResult(
            symbol=symbol,
            timestamp=_utc_now(),
            regime=bd["regime"],
            regime_gate=bd["gate"],
            momentum_score=bd["momentum"],
            derivatives_score=bd["derivatives"],
            sentiment_score=bd["sentiment"],
            flow_score=bd["flow"],
            composite_score=composite,
            verdict=_verdict(composite, self._params.entry_threshold,
                             self._params.exit_threshold),
            signal_strength=_strength(abs(composite)),
            bars_used=len(history),
        )

    @staticmethod
    def _error(symbol: str, bars_used: int, msg: str) -> SignalScoreResult:
        return SignalScoreResult(
            symbol=symbol, timestamp=_utc_now(), regime="unknown",
            regime_gate=0.0, momentum_score=0.0, derivatives_score=0.0,
            sentiment_score=0.0, flow_score=0.0, composite_score=0.0,
            verdict="hold", signal_strength="weak",
            bars_used=bars_used, error=msg,
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _verdict(composite: float, entry: float, exit_: float) -> str:
    if composite > entry:
        return "buy"
    if composite < exit_:
        return "sell"
    return "hold"


def _strength(abs_score: float) -> str:
    if abs_score >= 0.60:
        return "strong"
    if abs_score >= 0.30:
        return "moderate"
    return "weak"
