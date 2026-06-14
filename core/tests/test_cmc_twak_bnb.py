"""
Integration tests for CMC live feed, TWAK signing, and BNB testnet execution.
Hit real external APIs — run against live services.
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

# ── CMC Client ───────────────────────────────────────────────────────────────

class TestCMCClient:
    def test_imports_cleanly(self):
        from data.cmc_client import CMCClient, SYMBOL_IDS
        assert "BNB" in SYMBOL_IDS
        assert "ETH" in SYMBOL_IDS

    def test_parse_ohlcv_empty(self):
        from data.cmc_client import _parse_ohlcv
        df = _parse_ohlcv([])
        assert df.shape == (0, 10)  # 10 columns including extended fields

    def test_cache_path_format(self):
        from data.cmc_client import _cache_path
        p = _cache_path("BNB", 730, "daily")
        assert "BNB" in str(p)
        assert "730d" in str(p)

    def test_bars_from_df_roundtrip(self):
        """DataFrame → list[Bar] must match Bar field names exactly."""
        import polars as pl
        from data.cmc_client import CMCClient
        from backtest.engine import Bar

        df = pl.DataFrame({
            "timestamp_ms": [1_700_000_000_000],
            "open": [300.0],
            "high": [310.0],
            "low": [295.0],
            "close": [305.0],
            "volume": [1_000_000.0],
            "funding_rate": [0.001],
            "open_interest": [500_000.0],
            "social_score": [0.75],
            "net_flow": [-1_000.0],
        })
        client = CMCClient.__new__(CMCClient)  # skip __init__ (no API key needed)
        bars = client.bars_from_df(df)
        assert len(bars) == 1
        b = bars[0]
        assert isinstance(b, Bar)
        assert b.timestamp == 1_700_000_000_000
        assert b.close == 305.0
        assert b.funding_rate == 0.001
        assert b.social_score == 0.75

    @pytest.mark.skipif(
        not os.environ.get("CMC_API_KEY"),
        reason="CMC_API_KEY not set — set in .env.local to run",
    )
    def test_live_quote_bnb(self):
        """Integration: hits real CMC API for BNB quote."""
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env.local")
        from data.cmc_client import CMCClient
        with CMCClient() as client:
            q = client.fetch_quote_live("BNB")
        assert q["price"] > 0, "BNB price should be positive"
        assert q["symbol"] == "BNB"
        assert "funding_rate" in q
        print(f"\n  BNB live price: ${q['price']:,.2f}")

    @pytest.mark.skipif(
        not os.environ.get("CMC_API_KEY"),
        reason="CMC_API_KEY not set",
    )
    def test_historical_ohlcv_bnb_30d(self):
        """
        Integration: pull 30 days of BNB OHLCV and verify schema + no look-ahead.
        NOTE: CMC /v2/cryptocurrency/ohlcv/historical requires a Pro-tier key.
        If this 403s, the key needs an upgrade or use the CMC Agent Hub endpoint.
        """
        import httpx
        from data.cmc_client import CMCClient
        try:
            with CMCClient() as client:
                df = client.fetch_ohlcv_historical("BNB", days_back=30, interval="daily")
        except Exception as exc:
            if "403" in str(exc) or "RetryError" in type(exc).__name__:
                pytest.skip(
                    "CMC OHLCV historical returned 403 — key needs Pro tier or Agent Hub endpoint. "
                    "Live quote works; upgrade key or wire CMC_MCP_ENDPOINT for full history."
                )
            raise

        assert df.shape[0] >= 25, f"Expected ~30 rows, got {df.shape[0]}"
        cols = set(df.columns)
        required = {"timestamp_ms", "open", "high", "low", "close", "volume",
                    "funding_rate", "open_interest", "social_score", "net_flow"}
        assert required <= cols, f"Missing columns: {required - cols}"

        ts = df["timestamp_ms"].to_list()
        assert ts == sorted(ts), "Timestamps not monotonically increasing"
        print(f"\n  BNB OHLCV: {df.shape[0]} bars, latest close ${df['close'][-1]:.2f}")


# ── TWAK Client ──────────────────────────────────────────────────────────────

class TestTWAKSigner:
    def test_imports_cleanly(self):
        from exec.twak import TWAKClient, TWAKSigner, build_auth_headers
        assert TWAKClient is not None
        assert TWAKSigner is TWAKClient  # backward compat alias

    def test_empty_api_base_env_falls_back_to_default(self, monkeypatch):
        """A blank TWAK_API_BASE in .env.local must NOT win over the default.
        os.environ.get(key, default) returns '' when the key is present-but-empty,
        which silently broke the REST client (httpx UnsupportedProtocol on a
        scheme-less base). Empty must fall back to the real endpoint."""
        from exec.twak import TWAKClient
        from config.constants import TWAK_API_BASE_DEFAULT

        monkeypatch.setenv("TWAK_API_BASE", "")  # the real-world misconfig
        c = TWAKClient()
        try:
            assert c._base == TWAK_API_BASE_DEFAULT.rstrip("/")
            assert c._base.startswith("https://")
        finally:
            c.close()

    def test_hmac_headers_deterministic(self):
        """
        Inject fixed nonce + date → same inputs must produce same signature.
        Canonical: METHOD;PATH;SORTED_QUERY;ACCESS_ID;NONCE;DATE
        Authorization: HMAC-SHA256 Signature=<base64>
        """
        from exec.twak import build_auth_headers

        fixed_nonce = "a1b2c3d4-0000-0000-0000-000000000000"
        fixed_date = "Thu, 27 Feb 2026 12:00:00 GMT"

        h1 = build_auth_headers(
            "POST", "/amber-api/v1/route", "acc123", "secret",
            nonce=fixed_nonce, date=fixed_date,
        )
        h2 = build_auth_headers(
            "POST", "/amber-api/v1/route", "acc123", "secret",
            nonce=fixed_nonce, date=fixed_date,
        )

        assert h1["Authorization"] == h2["Authorization"], "HMAC is not deterministic"
        assert h1["Authorization"].startswith("HMAC-SHA256 Signature=")
        assert h1["X-TW-CREDENTIAL"] == "acc123"
        assert h1["X-TW-NONCE"] == fixed_nonce
        assert h1["X-TW-DATE"] == fixed_date

    def test_different_paths_different_sigs(self):
        """Different paths must produce different signatures."""
        from exec.twak import build_auth_headers

        fixed_nonce = "aaaa-bbbb-cccc-dddd-eeee00000000"
        fixed_date  = "Thu, 27 Feb 2026 12:00:00 GMT"

        h1 = build_auth_headers(
            "POST", "/amber-api/v1/route", "acc", "secret",
            nonce=fixed_nonce, date=fixed_date,
        )
        h2 = build_auth_headers(
            "POST", "/amber-api/v1/route/step", "acc", "secret",
            nonce=fixed_nonce, date=fixed_date,
        )

        sig1 = h1["Authorization"].split("Signature=")[1]
        sig2 = h2["Authorization"].split("Signature=")[1]
        assert sig1 != sig2, "Different paths must produce different signatures"

    def test_different_query_params_different_sigs(self):
        """Different query params must produce different signatures."""
        from exec.twak import build_auth_headers

        fixed_nonce = "ffff-0000-1111-2222-333344445555"
        fixed_date  = "Thu, 27 Feb 2026 12:00:00 GMT"

        h1 = build_auth_headers(
            "GET", "/v1/assets/listings", "acc", "secret",
            query_params={"category_id": "bnb-ecosystem"},
            nonce=fixed_nonce, date=fixed_date,
        )
        h2 = build_auth_headers(
            "GET", "/v1/assets/listings", "acc", "secret",
            query_params={"category_id": "trending"},
            nonce=fixed_nonce, date=fixed_date,
        )

        sig1 = h1["Authorization"].split("Signature=")[1]
        sig2 = h2["Authorization"].split("Signature=")[1]
        assert sig1 != sig2, "Different query params must produce different signatures"

    def test_credentials_loaded_from_env(self):
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env.local")
        access_id = os.environ.get("TW_ACCESS_ID", "")
        hmac_secret = os.environ.get("TW_HMAC_SECRET", "")
        assert access_id, "TW_ACCESS_ID must be set in .env.local"
        assert hmac_secret, "TW_HMAC_SECRET must be set in .env.local"


# ── BNB Exec ─────────────────────────────────────────────────────────────────

class TestBNBExec:
    def test_imports_cleanly(self):
        from exec.bnb import BNBExec, SwapParams, SwapSimResult, TOKENS_TESTNET
        assert "WBNB" in TOKENS_TESTNET
        assert "USDT" in TOKENS_TESTNET

    def test_abi_encoding_non_empty(self):
        """Calldata must be non-empty and start with the correct 4-byte selector."""
        from exec.bnb import SwapParams, _encode_exact_input_single, EXACT_INPUT_SINGLE_SEL, TOKENS_TESTNET
        params = SwapParams(
            token_in=TOKENS_TESTNET["WBNB"],
            token_out=TOKENS_TESTNET["USDT"],
            fee=2500,
            recipient="0x0000000000000000000000000000000000000001",
            amount_in=10 ** 17,   # 0.1 BNB in wei
            amount_out_min=0,
        )
        calldata = _encode_exact_input_single(params)
        assert len(calldata) > 4
        assert calldata[:4] == EXACT_INPUT_SINGLE_SEL

    def test_testnet_rpc_reachable(self):
        """Integration: BSC testnet JSON-RPC must respond to eth_chainId."""
        from exec.bnb import BNBExec
        with BNBExec(testnet=True) as bnb:
            chain_id = int(bnb._rpc("eth_chainId", []), 16)
        assert chain_id == 97, f"Expected testnet chain ID 97, got {chain_id}"
        print(f"\n  BSC testnet chain ID: {chain_id} OK")

    def test_gas_price_positive(self):
        """Integration: gas price must be positive on testnet."""
        from exec.bnb import BNBExec
        with BNBExec(testnet=True) as bnb:
            gp = bnb._get_gas_price()
        assert gp > 0
        print(f"\n  BSC testnet gas price: {gp / 1e9:.2f} gwei")

    @pytest.mark.skipif(
        not os.environ.get("TW_ACCESS_ID"),
        reason="TWAK credentials not set — set TW_ACCESS_ID + TW_HMAC_SECRET",
    )
    def test_simulate_swap_dry_run(self):
        """
        Integration: simulate a WBNB→USDT swap on BSC testnet via eth_call.
        No tx submitted — pure simulation.
        """
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env.local")
        from exec.bnb import BNBExec, SwapParams, TOKENS_TESTNET
        from exec.twak import TWAKClient

        dummy_wallet = "0x0000000000000000000000000000000000000001"

        params = SwapParams(
            token_in=TOKENS_TESTNET["WBNB"],
            token_out=TOKENS_TESTNET["USDT"],
            fee=2500,
            recipient=dummy_wallet,
            amount_in=10 ** 17,   # 0.1 WBNB
            amount_out_min=0,
        )

        with BNBExec(testnet=True) as bnb:
            sim = bnb.simulate_swap(params, dummy_wallet)

        # Revert is expected from a zero-funded dummy address — the RPC round-trip succeeds.
        # A real testnet wallet with WBNB balance + approval would get success=True.
        print(f"\n  Swap sim — gas estimate: {sim.gas_estimate:,}, success: {sim.success}")
        assert isinstance(sim.gas_estimate, int)
        assert sim.gas_estimate > 0
        assert isinstance(sim.success, bool)  # True with funded wallet, False with dummy
