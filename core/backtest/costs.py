"""
BSC cost model: PancakeSwap V3 swap fee + size-aware AMM slippage + BSC gas + perp funding.
Replaces the placeholder in engine.py. All numbers are conservative (round up costs).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from backtest.engine import Bar, Order

# ── Constants (sourced from real BSC data) ────────────────────────────────────

_GAS_UNITS_SWAP = 150_000          # PancakeSwap V3 exactInputSingle gas units
_GAS_PRICE_GWEI = 5.0              # typical BSC gas price (gwei)
_GWEI = 1e-9

_PANCAKE_V3_FEE = 0.0025           # 25 bps - BNB/USDT 0.25% pool tier
_POOL_LIQUIDITY_USD = 8_000_000.0  # ~$8M TVL in BNB/USDT V3 pool (conservative)
_BNB_PRICE_FALLBACK = 572.0        # used if bar doesn't carry price context


# ── Cost model ────────────────────────────────────────────────────────────────

@dataclass
class BSCCostModel:
    """
    Callable cost model compatible with engine.CostModelFn signature.
    Returns (fee_usd, gas_usd, slippage_usd).
    """
    gas_units: int = _GAS_UNITS_SWAP
    gas_price_gwei: float = _GAS_PRICE_GWEI
    swap_fee_rate: float = _PANCAKE_V3_FEE
    pool_liquidity_usd: float = _POOL_LIQUIDITY_USD
    bnb_price_usd: float = _BNB_PRICE_FALLBACK

    def __call__(self, order: Order, bar: Bar) -> tuple[float, float, float]:
        fee = order.size_usd * self.swap_fee_rate
        gas_bnb = self.gas_units * self.gas_price_gwei * _GWEI
        # Gas on BSC is ALWAYS paid in BNB - price it in BNB regardless of the traded
        # symbol. The previous max(bar.close, bnb_price) used the ETH price (~$3000) as
        # if it were the BNB price, overstating gas ~5x on ETH trades.
        gas_usd = gas_bnb * self.bnb_price_usd
        slippage = amm_slippage(order.size_usd, self.pool_liquidity_usd)
        return fee, gas_usd, slippage

    def funding_cost(self, position_usd: float, bar: Bar) -> float:
        """
        Perp funding cost for one bar period.
        bar.funding_rate is 8-hour rate from CMC; daily bars = 3 periods.
        """
        if bar.funding_rate == 0.0:
            return 0.0
        daily_rate = bar.funding_rate * 3.0
        return abs(position_usd * daily_rate)


def amm_slippage(size_usd: float, pool_liquidity_usd: float = _POOL_LIQUIDITY_USD) -> float:
    """
    Square-root price impact model: impact_rate = 0.5 * sqrt(size / liquidity).
    Conservative but well-calibrated for V3 concentrated liquidity pools.
    Returns slippage in USD.
    """
    if pool_liquidity_usd <= 0 or size_usd <= 0:
        return 0.0
    impact_rate = 0.5 * math.sqrt(size_usd / pool_liquidity_usd)
    return size_usd * impact_rate


# ── Convenience: default singleton used when no custom model is provided ──────

DEFAULT_BSC_COST = BSCCostModel()
