"""Web Push (VAPID) — replaces Telegram as the away-from-app ping.
send_push never raises on a dead subscription; the caller prunes on False."""
from __future__ import annotations

import json
import logging

from pywebpush import webpush

log = logging.getLogger(__name__)


def build_push_payload(title: str, body: str, *, severity: str = "info", url: str = "/") -> dict:
    return {"title": title, "body": body, "severity": severity, "url": url}


def send_push(subscription: dict, payload: dict, *, vapid: dict) -> bool:
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=vapid["private_key"],
            vapid_claims={"sub": vapid["subject"]},
        )
        return True
    except Exception as exc:
        log.warning("web push failed (%s); subscription likely dead", exc)
        return False
