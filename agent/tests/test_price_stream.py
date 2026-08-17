"""PriceCache staleness + base-token normalization. No network."""
from __future__ import annotations

from agent.price_stream import PriceCache, base_token, BinancePriceStream


def test_base_token_strips_quote():
    assert base_token("CAKEUSDT") == "CAKE"
    assert base_token("ethusdt") == "ETH"
    assert base_token("AAVE") == "AAVE"


def test_cache_update_and_get():
    c = PriceCache()
    c.update("CAKEUSDT", 2.50, ts=100.0)
    assert c.get("CAKE") == (2.50, 100.0)


def test_fresh_price_within_window():
    c = PriceCache()
    c.update("CAKE", 2.50, ts=100.0)
    assert c.fresh_price("CAKE", max_age_s=10.0, now=105.0) == 2.50


def test_stale_price_returns_none():
    c = PriceCache()
    c.update("CAKE", 2.50, ts=100.0)
    assert c.fresh_price("CAKE", max_age_s=10.0, now=130.0) is None


def test_unknown_symbol_returns_none():
    assert PriceCache().fresh_price("UNI") is None


def test_stream_start_is_safe_without_tokens():
    # No tokens → start() must be a no-op returning False, never raise.
    assert BinancePriceStream([]).start() is False
