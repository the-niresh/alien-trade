"""
Trust Wallet Agent Kit (TWAK) signing client.
All transaction signing goes through TWAK — zero raw private keys in code or logs.
Auth: HMAC-SHA256 with TW_ACCESS_ID + TW_HMAC_SECRET.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from config.constants import TWAK_API_BASE_DEFAULT, TWAK_SIGN_PATH, TWAK_WALLET_PATH

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")


@dataclass
class SignedTx:
    raw_hex: str          # 0x-prefixed signed transaction ready for broadcast
    tx_hash: str          # expected tx hash (may differ after broadcast due to mempool)
    wallet_address: str   # signer address from TWAK wallet


@dataclass
class TWAKWalletInfo:
    address: str
    chain_id: int
    balance_wei: int


class TWAKSigner:
    """
    Wraps TWAK API for:
    - Fetching the managed wallet address
    - Signing arbitrary EVM transactions
    - Optionally submitting via TWAK (or broadcast separately via BNBExec)
    """

    def __init__(
        self,
        access_id: Optional[str] = None,
        hmac_secret: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.access_id = access_id or os.environ.get("TW_ACCESS_ID", "")
        self._secret = (hmac_secret or os.environ.get("TW_HMAC_SECRET", "")).encode()
        # env var TWAK_API_BASE lets operators override without touching code
        resolved = api_base or os.environ.get("TWAK_API_BASE", TWAK_API_BASE_DEFAULT)
        self._base = resolved.rstrip("/")
        self._http = httpx.Client(timeout=15.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TWAKSigner":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Public API ───────────────────────────────────────────────────────────

    def get_wallet(self, chain_id: int = 97) -> TWAKWalletInfo:
        """Return the TWAK-managed wallet info for the given chain."""
        resp = self._signed_request("GET", f"/wallet?chain_id={chain_id}")
        return TWAKWalletInfo(
            address=resp["address"],
            chain_id=resp["chain_id"],
            balance_wei=int(resp.get("balance_wei", 0)),
        )

    def sign_transaction(self, unsigned_tx: dict) -> SignedTx:
        """
        Send an unsigned EVM tx dict to TWAK for signing.
        unsigned_tx keys: to, data, value (hex), gas (hex), gasPrice (hex),
                          nonce (hex), chainId.
        Returns SignedTx with raw_hex ready for eth_sendRawTransaction.
        """
        payload = {"transaction": unsigned_tx}
        resp = self._signed_request("POST", "/sign", body=payload)
        return SignedTx(
            raw_hex=resp["raw_transaction"],
            tx_hash=resp["hash"],
            wallet_address=resp["from"],
        )

    def sign_and_submit(self, unsigned_tx: dict) -> str:
        """Sign + broadcast via TWAK in one call. Returns tx hash."""
        payload = {"transaction": unsigned_tx, "submit": True}
        resp = self._signed_request("POST", "/sign", body=payload)
        return resp["hash"]

    # ── HMAC signing ────────────────────────────────────────────────────────

    def _signed_request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        ts = str(int(time.time() * 1000))
        body_bytes = json.dumps(body, separators=(",", ":")).encode() if body else b""
        body_hash = hashlib.sha256(body_bytes).hexdigest()

        # Canonical string: METHOD\nPATH\nTIMESTAMP\nBODY_HASH
        canonical = f"{method}\n{path}\n{ts}\n{body_hash}"
        sig = hmac.new(self._secret, canonical.encode(), hashlib.sha256).hexdigest()

        headers = {
            "Authorization": f"{self.access_id}:{sig}:{ts}",
            "Content-Type": "application/json",
            "X-Timestamp": ts,
        }
        url = f"{self._base}{path}"

        if method == "GET":
            r = self._http.get(url, headers=headers)
        else:
            r = self._http.post(url, headers=headers, content=body_bytes)

        r.raise_for_status()
        return r.json()


# ── Standalone signing utility ────────────────────────────────────────────────

def build_auth_headers(
    method: str,
    path: str,
    access_id: str,
    secret: str,
    body: Optional[dict] = None,
) -> dict[str, str]:
    """
    Pure function — build TWAK HMAC auth headers without an HTTP client.
    Useful for testing and for ad-hoc requests.
    """
    ts = str(int(time.time() * 1000))
    body_bytes = json.dumps(body, separators=(",", ":")).encode() if body else b""
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = f"{method}\n{path}\n{ts}\n{body_hash}"
    sig = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return {
        "Authorization": f"{access_id}:{sig}:{ts}",
        "Content-Type": "application/json",
        "X-Timestamp": ts,
    }
