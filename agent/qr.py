"""
Terminal QR - render the hosted PWA URL as an ASCII QR after onboarding so the
operator can scan it and open the mobile dashboard instantly (no app store).

URL resolution order:
  1. `url` argument (explicit override)
  2. `PWA_URL` env var (set by install.sh after Vercel deploy)
  3. `VITE_CONVEX_URL`-based heuristic (local dev fallback: http://localhost:5173)

Uses the optional `qrcode` lib if installed; otherwise prints the URL plainly so
the runtime never hard-depends on it.
"""
from __future__ import annotations

import os


def resolve_url(url: str = "") -> str:
    """Return the best available PWA URL."""
    if url:
        return url
    if pwa := os.environ.get("PWA_URL", ""):
        return pwa
    # Local dev fallback
    return "http://localhost:5173"


def qr_string(url: str = "") -> str:
    """Return the ASCII QR for `url` as a string (for embedding in a TUI widget).
    Falls back to the plain URL when the qrcode lib is unavailable."""
    resolved = resolve_url(url)
    if not resolved:
        return ""
    try:
        import io

        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=1)
        qr.add_data(resolved)
        qr.make(fit=True)
        buf = io.StringIO()
        qr.print_ascii(out=buf, invert=True)
        return buf.getvalue()
    except Exception:
        return resolved


def print_qr(url: str = "") -> None:
    resolved = resolve_url(url)
    if not resolved:
        return
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=1)
        qr.add_data(resolved)
        qr.make(fit=True)
        print("\n  Scan to open the Alien-Trade glass cockpit:\n")
        qr.print_ascii(invert=True)
        print(f"\n  {resolved}\n")
    except Exception:
        print(f"\n  Dashboard: {resolved}\n  (pip install qrcode for a scannable QR)\n")
