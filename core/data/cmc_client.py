"""
CMC data client — historical + live feed.
All output fields match the backtest Bar exactly (parity from day 1).
Extended fields (funding_rate, OI, social, flow) are stubbed at 0.0 until
the CMC Agent Hub endpoints are confirmed; the schema is already wired.

x402 micropayments: if X402_PRIVATE_KEY is set, the client uses the full
x402 protocol (HTTP 402 → sign EVM payment → retry) for every CMC API call.
Payment wallet must hold USDC on Base (eip155:8453).  Set X402_NETWORK to
override the network.  If the key is absent, falls back to plain API-key auth.
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Optional

import httpx
import polars as pl
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from backtest.engine import Bar
from config.constants import CMC_BASE_URL, CMC_SYMBOL_IDS, X402_DEFAULT_NETWORK

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

CMC_BASE = CMC_BASE_URL
CACHE_DIR = Path(__file__).parent / "parquet"
SYMBOL_IDS = CMC_SYMBOL_IDS


def _build_x402_http(
    base_url: str,
    base_headers: dict[str, str],
    timeout: float,
) -> "_X402HttpxClient | None":
    """Build an x402-enabled httpx wrapper if X402_PRIVATE_KEY is set."""
    private_key = os.environ.get("X402_PRIVATE_KEY", "").strip()
    if not private_key:
        return None
    try:
        from x402 import x402ClientSync
        from x402.http.x402_http_client import x402HTTPClientSync
        from x402.mechanisms.evm.exact import register_exact_evm_client
        from x402.mechanisms.evm.signers import EthAccountSigner
        from eth_account import Account

        network = os.environ.get("X402_NETWORK", X402_DEFAULT_NETWORK)
        signer = EthAccountSigner(Account.from_key(private_key))
        core = x402ClientSync()
        register_exact_evm_client(core, signer, networks=network)
        http_client = x402HTTPClientSync(core)
        return _X402HttpxClient(
            httpx.Client(base_url=base_url, headers=base_headers, timeout=timeout),
            http_client,
        )
    except Exception:
        return None


class _X402HttpxClient:
    """
    Thin wrapper: makes a GET, auto-retries with payment headers on HTTP 402.
    Falls back gracefully — if x402 signing fails, raises the original error.
    """

    def __init__(self, http: httpx.Client, x402: "x402HTTPClientSync") -> None:
        self._http = http
        self._x402 = x402

    def get(self, path: str, **kwargs) -> httpx.Response:
        r = self._http.get(path, **kwargs)
        if r.status_code == 402:
            payment_hdrs, _ = self._x402.handle_402_response(
                dict(r.headers), r.content
            )
            r = self._http.get(path, headers=payment_hdrs, **kwargs)
        return r

    def close(self) -> None:
        self._http.close()


class CMCClient:
    """
    CMC Pro API wrapper for historical OHLCV and live quotes.
    Caches to parquet so a 2-year pull is a one-time cost.
    Uses x402 pay-per-call if X402_PRIVATE_KEY is set.
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.environ.get("CMC_API_KEY", "")
        base_headers: dict[str, str] = {
            "X-CMC_PRO_API_KEY": key,
            "Accept": "application/json",
        }
        x402_client = _build_x402_http(CMC_BASE, base_headers, timeout=30.0)
        if x402_client is not None:
            self._x402_client = x402_client
            self._http = None                   # not used when x402 active
        else:
            self._x402_client = None
            self._http = httpx.Client(
                base_url=CMC_BASE, headers=base_headers, timeout=30.0
            )

    def _get(self, path: str, **params) -> httpx.Response:
        """GET with automatic x402 402-payment-retry if enabled."""
        if self._x402_client is not None:
            return self._x402_client.get(path, params=params)
        assert self._http is not None
        return self._http.get(path, params=params)

    def close(self) -> None:
        if self._x402_client is not None:
            self._x402_client.close()
        if self._http is not None:
            self._http.close()

    def __enter__(self) -> "CMCClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Historical ──────────────────────────────────────────────────────────

    def fetch_ohlcv_historical(
        self,
        symbol: str,
        days_back: int = 730,
        interval: str = "daily",
        force_refresh: bool = False,
    ) -> pl.DataFrame:
        """
        Pull OHLCV for `symbol` over `days_back` days and cache to parquet.
        Returns columns: timestamp_ms, open, high, low, close, volume,
                         funding_rate, open_interest, social_score, net_flow.
        """
        if symbol not in SYMBOL_IDS:
            raise ValueError(f"Unknown symbol {symbol!r}. Add it to SYMBOL_IDS.")

        cache = _cache_path(symbol, days_back, interval)
        if cache.exists() and not force_refresh:
            return pl.read_parquet(cache)

        end = datetime.date.today()
        start = end - datetime.timedelta(days=days_back)
        quotes = self._get_ohlcv(SYMBOL_IDS[symbol], start.isoformat(), end.isoformat(), interval)
        df = _parse_ohlcv(quotes)

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(cache)
        return df

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get_ohlcv(
        self, cmc_id: int, time_start: str, time_end: str, interval: str
    ) -> list[dict]:
        r = self._get(
            "/v2/cryptocurrency/ohlcv/historical",
            id=cmc_id,
            time_start=time_start,
            time_end=time_end,
            interval=interval,
            convert="USD",
            count=10000,
        )
        r.raise_for_status()
        return r.json()["data"]["quotes"]

    # ── Live ────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def fetch_quote_live(self, symbol: str) -> dict:
        """Latest price + volume from CMC quotes endpoint."""
        if symbol not in SYMBOL_IDS:
            raise ValueError(f"Unknown symbol {symbol!r}.")
        cmc_id = SYMBOL_IDS[symbol]
        r = self._get(
            "/v2/cryptocurrency/quotes/latest",
            id=cmc_id,
            convert="USD",
        )
        r.raise_for_status()
        data = r.json()["data"][str(cmc_id)]
        q = data["quote"]["USD"]
        return {
            "timestamp_ms": int(
                datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000
            ),
            "symbol": symbol,
            "price": float(q["price"]),
            "volume_24h": float(q.get("volume_24h") or 0),
            "percent_change_1h": float(q.get("percent_change_1h") or 0),
            "percent_change_24h": float(q.get("percent_change_24h") or 0),
            # Extended signal fields — CMC Agent Hub wires these in Phase 6
            "funding_rate": 0.0,
            "open_interest": 0.0,
            "social_score": 0.0,
            "net_flow": 0.0,
        }

    # ── Bar conversion ───────────────────────────────────────────────────────

    def bars_from_df(self, df: pl.DataFrame) -> list[Bar]:
        """Convert cached OHLCV DataFrame -> list[Bar] for the backtest engine."""
        return [
            Bar(
                timestamp=int(row["timestamp_ms"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                funding_rate=float(row["funding_rate"]),
                open_interest=float(row["open_interest"]),
                social_score=float(row["social_score"]),
                net_flow=float(row["net_flow"]),
            )
            for row in df.to_dicts()
        ]

    def live_bar(self, symbol: str) -> Bar:
        """Fetch a synthetic Bar from the live quote endpoint."""
        q = self.fetch_quote_live(symbol)
        p = q["price"]
        return Bar(
            timestamp=q["timestamp_ms"],
            open=p,
            high=p,
            low=p,
            close=p,
            volume=q["volume_24h"],
            funding_rate=q["funding_rate"],
            open_interest=q["open_interest"],
            social_score=q["social_score"],
            net_flow=q["net_flow"],
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cache_path(symbol: str, days_back: int, interval: str) -> Path:
    return CACHE_DIR / f"{symbol}_{days_back}d_{interval}.parquet"


def _parse_ohlcv(quotes: list[dict]) -> pl.DataFrame:
    rows = []
    for q in quotes:
        usd = q["quote"]["USD"]
        ts = datetime.datetime.fromisoformat(q["time_open"].replace("Z", "+00:00"))
        rows.append(
            {
                "timestamp_ms": int(ts.timestamp() * 1000),
                "open": float(usd.get("open") or 0),
                "high": float(usd.get("high") or 0),
                "low": float(usd.get("low") or 0),
                "close": float(usd.get("close") or 0),
                "volume": float(usd.get("volume") or 0),
                "funding_rate": 0.0,
                "open_interest": 0.0,
                "social_score": 0.0,
                "net_flow": 0.0,
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "timestamp_ms": pl.Int64,
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
            "funding_rate": pl.Float64,
            "open_interest": pl.Float64,
            "social_score": pl.Float64,
            "net_flow": pl.Float64,
        },
    )
