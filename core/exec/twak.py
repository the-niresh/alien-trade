"""
Trust Wallet Agent Kit (TWAK) client.
REST API at tws.trustwallet.com — HMAC-SHA256 authenticated.

Signing format (confirmed from developer.trustwallet.com/developer/agent-sdk/authentication):
  plaintext = "METHOD;PATH;SORTED_QUERY;ACCESS_ID;NONCE;DATE"
  signature = base64(hmac_sha256(hmac_secret, plaintext))
  Authorization: HMAC-SHA256 Signature={base64_signature}

Covers: token prices (POST /v2/market/tickers),
        Amber swap routes (POST /amber-api/v1/route),
        Amber step transactions (POST /amber-api/v1/route/step).

Transaction signing uses eth-account with PRIVATE_KEY (Phase 5: switch to
twak serve for managed-key signing without raw key exposure).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from config.constants import (
    TWAK_API_BASE_DEFAULT,
    TWAK_AMBER_ROUTE_PATH,
    TWAK_AMBER_STEP_PATH,
    TWAK_PRICES_PATH,
)

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")


# ── Response dataclasses ──────────────────────────────────────────────────────

@dataclass
class SwapRoute:
    route_id: str
    steps: list[dict]
    expiration: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class StepTransaction:
    step_id: str
    evm_tx: dict                    # {to, value, data, gasLimit}
    approve: Optional[dict] = None  # ERC-20 approval tx (send first if present)
    revoke: Optional[dict] = None   # revoke previous unlimited approval if present


# ── Client ────────────────────────────────────────────────────────────────────

class TWAKClient:
    """
    TWAK REST API client.
    Market data + Amber aggregator swap routing.
    """

    def __init__(
        self,
        access_id: Optional[str] = None,
        hmac_secret: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.access_id = access_id or os.environ.get("TW_ACCESS_ID", "")
        self._secret = hmac_secret or os.environ.get("TW_HMAC_SECRET", "")
        # `or` (not get's default) so a present-but-EMPTY TWAK_API_BASE in .env.local
        # falls back to the real endpoint instead of yielding a scheme-less base URL
        # (which httpx rejects with UnsupportedProtocol — silently broke the client).
        resolved = api_base or os.environ.get("TWAK_API_BASE") or TWAK_API_BASE_DEFAULT
        self._base = resolved.rstrip("/")
        self._http = httpx.Client(timeout=20.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TWAKClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Market data ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def get_prices(self, asset_ids: list[str], currency: str = "USD") -> list[dict]:
        """
        Current prices for SLIP-44 asset IDs (e.g. 'c714' for BNB, 'c60' for ETH).
        Aggregated from CMC + CoinGecko.
        """
        body = {"currency": currency, "assets": asset_ids}
        headers = _build_signed_headers("POST", TWAK_PRICES_PATH, "", self.access_id, self._secret)
        r = self._http.post(f"{self._base}{TWAK_PRICES_PATH}", json=body, headers=headers)
        r.raise_for_status()
        return r.json().get("tickers", [])

    # ── Amber swap routing ────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_swap_route(
        self,
        from_asset: str,
        to_asset: str,
        amount_wei: str,
        from_address: str,
        from_domain: str = "bsc",
        to_domain: str = "bsc",
        slippage: str = "1",
    ) -> SwapRoute:
        """
        Best swap route via Amber aggregator (1inch, KyberSwap, 0x, etc.).
        from_asset/to_asset: token contract address or 0xEeee... for native BNB.
        amount_wei: amount in smallest unit as string.
        Returns the top route sorted by output amount.
        """
        body = {
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "amount": amount_wei,
            "fromAddress": from_address,
            "fromDomain": from_domain,
            "toDomain": to_domain,
            "slippage": slippage,
            "sortBy": "outcome",
            "contractCall": False,
        }
        headers = _build_signed_headers("POST", TWAK_AMBER_ROUTE_PATH, "", self.access_id, self._secret)
        r = self._http.post(f"{self._base}{TWAK_AMBER_ROUTE_PATH}", json=body, headers=headers)
        r.raise_for_status()
        routes = r.json().get("routes", [])
        if not routes:
            raise ValueError("No swap routes returned from TWAK Amber API")
        best = routes[0]
        return SwapRoute(
            route_id=best["id"],
            steps=best.get("steps", []),
            expiration=best.get("expirationDate", ""),
            warnings=best.get("warnings", []),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_step_transaction(self, step_id: str) -> StepTransaction:
        """
        Executable EVM transaction for a single route step.
        Returns evm_tx {to, value, data, gasLimit} ready to sign and broadcast.
        If approve is set, send the approval tx first and wait for confirmation.
        """
        body = {"stepId": step_id}
        headers = _build_signed_headers("POST", TWAK_AMBER_STEP_PATH, "", self.access_id, self._secret)
        r = self._http.post(f"{self._base}{TWAK_AMBER_STEP_PATH}", json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
        tx = data.get("transaction", {})
        return StepTransaction(
            step_id=step_id,
            evm_tx=tx.get("evmTx", {}),
            approve=data.get("approve"),
            revoke=data.get("revokeApproval"),
        )


# ── Backward compat alias (tests + bnb.py still import TWAKSigner) ───────────
TWAKSigner = TWAKClient


# ── Auth header utilities ─────────────────────────────────────────────────────

def build_auth_headers(
    method: str,
    path: str,
    access_id: str,
    secret: str,
    query_params: Optional[dict] = None,
    nonce: Optional[str] = None,
    date: Optional[str] = None,
) -> dict[str, str]:
    """
    Build TWAK HMAC-SHA256 auth headers.
    Inject nonce and date for deterministic testing.
    query_params replaces the old 'body' arg — body is not part of the signature.
    """
    sorted_query = _sort_query(query_params)
    return _build_signed_headers(method, path, sorted_query, access_id, secret, nonce, date)


def _sort_query(params: Optional[dict]) -> str:
    if not params:
        return ""
    return "&".join(f"{k}={v}" for k, v in sorted(params.items()))


def _build_signed_headers(
    method: str,
    path: str,
    sorted_query: str,
    access_id: str,
    secret: str,
    nonce: Optional[str] = None,
    date: Optional[str] = None,
) -> dict[str, str]:
    _nonce = nonce or str(uuid.uuid4())
    _date = date or datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    plaintext = ";".join([method.upper(), path, sorted_query, access_id, _nonce, _date])
    sig = base64.b64encode(
        hmac.new(secret.encode(), plaintext.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "X-TW-CREDENTIAL": access_id,
        "X-TW-NONCE": _nonce,
        "X-TW-DATE": _date,
        "Authorization": f"HMAC-SHA256 Signature={sig}",
        "Content-Type": "application/json",
    }
