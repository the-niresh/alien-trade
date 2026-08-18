"""Live key-validation probes for the onboarding wizard.

Each probe returns a structured ProbeResult and NEVER raises - the TUI renders
red/green per field from `ok`, and shows `detail` on failure. Timeouts are short
so a wrong key fails fast instead of stalling the wizard. The `base` arg exists so
tests can point at a dead address without touching real services.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

_TIMEOUT = 4.0


@dataclass
class ProbeResult:
    ok: bool
    detail: str


def probe_convex(url: str, *, timeout: float = _TIMEOUT) -> ProbeResult:
    if not url:
        return ProbeResult(False, "no CONVEX_URL set")
    try:
        r = httpx.post(
            f"{url.rstrip('/')}/api/query",
            json={"path": "config:isHalted", "args": {}, "format": "json"},
            timeout=timeout,
        )
        if r.status_code == 200 and r.json().get("status") == "success":
            return ProbeResult(True, "reachable")
        return ProbeResult(False, f"HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001 - probes never raise
        return ProbeResult(False, str(e) or "connection failed")


def probe_binance(*, base: str = "https://api.binance.com", timeout: float = _TIMEOUT) -> ProbeResult:
    try:
        r = httpx.get(f"{base.rstrip('/')}/api/v3/ping", timeout=timeout)
        return ProbeResult(r.status_code == 200, "reachable" if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001
        return ProbeResult(False, str(e) or "connection failed")


def probe_telegram(
    token: str, chat_id: str, *, base: str = "https://api.telegram.org", timeout: float = _TIMEOUT
) -> ProbeResult:
    if not token:
        return ProbeResult(False, "no bot token")
    try:
        r = httpx.get(f"{base.rstrip('/')}/bot{token}/getMe", timeout=timeout)
        body = r.json()
        if r.status_code == 200 and body.get("ok"):
            name = body.get("result", {}).get("username", "bot")
            return ProbeResult(True, f"@{name}")
        return ProbeResult(False, body.get("description", f"HTTP {r.status_code}"))
    except Exception as e:  # noqa: BLE001
        return ProbeResult(False, str(e) or "connection failed")


def probe_anthropic(key: str, *, base: str = "https://api.anthropic.com", timeout: float = _TIMEOUT) -> ProbeResult:
    if not key:
        return ProbeResult(False, "no API key")
    try:
        r = httpx.get(
            f"{base.rstrip('/')}/v1/models",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            timeout=timeout,
        )
        if r.status_code == 200:
            return ProbeResult(True, "key valid")
        return ProbeResult(False, f"HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001
        return ProbeResult(False, str(e) or "connection failed")
