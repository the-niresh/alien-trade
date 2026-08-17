"""
Binance klines client — unit + integration tests.
Pulls 2 years of OHLCV for BNB/BTC/ETH. Results cache to core/data/parquet/.
"""
from __future__ import annotations

import pytest
from pathlib import Path

UNIVERSE = ["BNB", "BTC", "ETH"]  # USDT is cash, no OHLCV needed


@pytest.mark.integration   # hits the live Binance API; blocked from CI runners
class TestBinanceClient:
    def test_imports_cleanly(self):
        from data.binance_client import BinanceClient, SYMBOL_PAIRS
        assert "BNB" in SYMBOL_PAIRS
        assert "BTC" in SYMBOL_PAIRS
        assert "ETH" in SYMBOL_PAIRS

    def test_parse_klines_empty(self):
        from data.binance_client import _parse_klines
        df = _parse_klines([])
        assert df.shape == (0, 10)

    def test_schema_matches_cmc(self):
        """Both clients must produce identical column sets — backtest is indifferent."""
        from data.binance_client import _parse_klines
        from data.cmc_client import _parse_ohlcv
        binance_cols = set(_parse_klines([]).columns)
        cmc_cols = set(_parse_ohlcv([]).columns)
        assert binance_cols == cmc_cols, f"Schema mismatch: {binance_cols ^ cmc_cols}"

    def test_bnb_30d_pull(self):
        """Integration: pull 30 days of BNB klines from Binance."""
        from data.binance_client import BinanceClient
        with BinanceClient() as client:
            df = client.fetch_ohlcv_historical("BNB", days_back=30, interval="daily")
        assert df.shape[0] >= 28, f"Expected ~30 bars, got {df.shape[0]}"
        ts = df["timestamp_ms"].to_list()
        assert ts == sorted(ts), "Timestamps not monotonically increasing"
        assert df["close"][0] > 0
        print(f"\n  BNB 30d: {df.shape[0]} bars | latest close ${df['close'][-1]:.2f}")

    def test_2yr_universe_pull(self):
        """
        Integration: pull 2 years of daily OHLCV for BNB, BTC, ETH.
        This is the historical dataset that feeds the backtest engine.
        Results are cached to core/data/parquet/ — only re-fetches on force_refresh.
        """
        from data.binance_client import BinanceClient
        with BinanceClient() as client:
            for sym in UNIVERSE:
                df = client.fetch_ohlcv_historical(sym, days_back=730, interval="daily")
                assert df.shape[0] >= 700, f"{sym}: expected ~730 bars, got {df.shape[0]}"
                assert df["close"].min() > 0, f"{sym}: found zero/negative close price"
                ts = df["timestamp_ms"].to_list()
                assert ts == sorted(ts), f"{sym}: timestamps not monotonically increasing"
                print(
                    f"\n  {sym} 2yr: {df.shape[0]} bars | "
                    f"first=${df['close'][0]:.2f} latest=${df['close'][-1]:.2f}"
                )

    def test_bars_roundtrip_into_engine(self):
        """Bars from Binance must feed cleanly into the backtest engine."""
        from data.binance_client import BinanceClient
        from backtest.engine import run_backtest, Bar, Order

        with BinanceClient() as client:
            df = client.fetch_ohlcv_historical("BNB", days_back=30, interval="daily")
            bars = client.bars_from_df(df)

        assert len(bars) >= 28
        assert all(isinstance(b, Bar) for b in bars)

        def buy_and_hold(history: list[Bar]):
            if len(history) == 1:
                return Order("buy", 1000.0, "BNB", history[-1].timestamp)
            return None

        result = run_backtest(bars, buy_and_hold, initial_capital=10_000.0)
        assert "total_return" in result.metrics
        assert "max_drawdown" in result.metrics
        assert result.metrics["max_drawdown"] <= 0
        print(f"\n  Backtest on Binance data: return={result.metrics['total_return']:.2%} "
              f"drawdown={result.metrics['max_drawdown']:.2%}")
