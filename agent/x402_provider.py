"""
TWAK native x402 provider — Alien-Trade as an x402 paywall operator.

Exposes POST /skill/signal_score as a metered $0.01-per-call endpoint.
Any agent can call it; callers that include a valid x402 payment header
(0.01 USDC on Base) receive a structured multi-signal score. Callers
without payment get an HTTP 402 with machine-readable payment requirements.

This is the "both sides of x402" story for the TWAK special prize:

  CONSUME  core/data/cmc_client.py pays $0.01 per CMC live data call.
  PROVIDE  this module charges $0.01 per /skill/signal_score call.

Both use the same asset (USDC on Base eip155:8453), the same facilitator
(x402.org), and the same x402 library — symmetric, demonstrable, auditable.

Offline-first: if X402_WALLET_ADDRESS is absent or the x402 library is not
installed/configured, this module is a no-op and the endpoint stays free.
The server never crashes because of a missing payment config.

Env vars (all optional):
  X402_WALLET_ADDRESS   The BSC/Base wallet that collects USDC payments.
                        Falls back to WALLET_ADDRESS if not set.
  X402_FACILITATOR_URL  Override the facilitator (default: x402.org).
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastapi import FastAPI

log = logging.getLogger(__name__)

# ── Payment constants ─────────────────────────────────────────────────────────

PRICE        = "$0.01"               # USDC per call
NETWORK      = "eip155:8453"         # Base mainnet — USDC only, gasless
SCHEME       = "exact"               # EIP-3009 exact-amount transfer

DEFAULT_FACILITATOR_URL = "https://x402.org/facilitator"

# Route that requires payment.  Only this one endpoint is metered.
PROTECTED_PATH = "/skill/signal_score"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_routes(wallet_address: str) -> dict:
    """Build the x402 routes config dict with the operator's wallet injected."""
    return {
        f"POST {PROTECTED_PATH}": {
            "accepts": {
                "scheme":  SCHEME,
                "payTo":   wallet_address,
                "price":   PRICE,
                "network": NETWORK,
            }
        }
    }


def _wallet_address() -> str:
    """Resolve the operator wallet address from env, empty string if absent."""
    return (
        os.environ.get("X402_WALLET_ADDRESS", "").strip()
        or os.environ.get("WALLET_ADDRESS", "").strip()
    )


# ── Public API ────────────────────────────────────────────────────────────────

def register(app: "FastAPI", wallet_address: Optional[str] = None) -> bool:
    """
    Attach the x402 payment middleware to the FastAPI app.

    Call this once, at module level, BEFORE the first request (e.g. right
    after `app = FastAPI(...)`). FastAPI middleware is immutable after startup.

    Returns:
        True   — middleware attached; POST /skill/signal_score now costs $0.01.
        False  — nothing attached; endpoint stays free (offline / unconfigured).

    Never raises — any failure silently leaves the endpoint free.
    """
    addr = wallet_address or _wallet_address()
    if not addr:
        log.info(
            "[x402-provider] X402_WALLET_ADDRESS not set — "
            "/skill/signal_score is free (set the env var to enable metering)"
        )
        return False

    try:
        from x402 import x402ResourceServer                          # noqa: PLC0415
        from x402.http import HTTPFacilitatorClient                  # noqa: PLC0415
        from x402.http.middleware.fastapi import PaymentMiddlewareASGI  # noqa: PLC0415
        from x402.mechanisms.evm.exact import register_exact_evm_server  # noqa: PLC0415
    except ImportError as exc:
        log.warning(f"[x402-provider] x402 library not available ({exc}) — endpoint is free")
        return False

    try:
        facilitator_url = os.environ.get("X402_FACILITATOR_URL", DEFAULT_FACILITATOR_URL)
        facilitator = HTTPFacilitatorClient(url=facilitator_url)

        server = x402ResourceServer(facilitator)
        register_exact_evm_server(server, networks=NETWORK)

        routes = _build_routes(addr)
        app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

        log.info(
            f"[x402-provider] POST /skill/signal_score metered: "
            f"{PRICE} USDC on Base → payTo {addr[:10]}... "
            f"(facilitator: {facilitator_url})"
        )
        return True

    except Exception as exc:  # noqa: BLE001 — never break the server
        log.warning(
            f"[x402-provider] middleware setup failed ({type(exc).__name__}: {exc}) "
            "— /skill/signal_score is free"
        )
        return False


def route_config(wallet_address: str) -> dict:
    """Return the route config dict (for inspection / tests / docs)."""
    return _build_routes(wallet_address)


# ── x402 consumer (CMC data calls) ───────────────────────────────────────────

def _get_twak():
    """Construct a TwakCli instance. Extracted so tests can patch it."""
    from agent.twak_cli import TwakCli  # noqa: PLC0415
    return TwakCli()


def x402_gated_call(
    url: str,
    max_payment: str,
    body: dict,
    enabled: bool,
    budget_usd: float,
    spent_usd: float,
) -> "dict | None":
    """
    Call a CMC x402 endpoint via TWAK x402_request with a daily budget cap.

    Returns the parsed JSON response dict, or None if skipped
    (disabled / over budget / error).  Never raises.
    """
    if not enabled:
        return None
    if spent_usd >= budget_usd:
        return None
    try:
        return _get_twak().x402_request(url, max_payment, body=body)
    except Exception:  # noqa: BLE001 — caller gets None, not a crash
        return None
