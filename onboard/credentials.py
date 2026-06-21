"""Pairing-token credential store.

The pairing token is the single shared secret: it is the cockpit's pairing gate
AND the value every state-changing Convex mutation validates (convex/control.ts).
It lives at ~/.alien-trade/credentials.json (chmod 600) and is mirrored into
.env.local as CONTROL_TOKEN (read by the agent) + the Convex deployment env.
"""
import json
import os
import secrets
import stat
from pathlib import Path


def _path() -> Path:
    return Path(os.path.expanduser("~")) / ".alien-trade" / "credentials.json"


def load_token() -> str | None:
    p = _path()
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("control_token")


def save_token(token: str) -> str:
    """Persist a specific token (used to reconcile an externally-set CONTROL_TOKEN)."""
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"control_token": token}))
    p.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
    return token


def ensure_pairing_token() -> str:
    """Return the existing token, or mint + persist a new one. Idempotent."""
    existing = load_token()
    if existing:
        return existing
    return save_token(secrets.token_hex(24))
