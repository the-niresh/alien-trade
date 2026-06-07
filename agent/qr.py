"""
Terminal QR — render the hosted PWA URL as an ASCII QR after onboarding so the
operator can scan it and open the mobile dashboard instantly (no app store).

Uses the optional `qrcode` lib if installed; otherwise prints the URL plainly so
the runtime never hard-depends on it.
"""
from __future__ import annotations


def print_qr(url: str) -> None:
    if not url:
        return
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        print("\n  📱  Scan to open the Alien-Trade dashboard:\n")
        qr.print_ascii(invert=True)
        print(f"\n  {url}\n")
    except Exception:
        print(f"\n  📱  Dashboard: {url}\n  (install `qrcode` for a scannable QR)\n")
