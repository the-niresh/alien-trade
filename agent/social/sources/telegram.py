"""
Telegram adapter via Telethon — credential-gated, legit, high-signal for crypto.

Reads public channels (trade-call / news channels). `handle` is the channel
username (e.g. "whalepool" or "https://t.me/whalepool"). Credential-gated: stays
dormant until configured; never blocks the run.

Setup (operator, once):
  uv pip install --python core/.venv/Scripts/python.exe telethon
  # get api_id / api_hash (free) from https://my.telegram.org -> API development
  set TELEGRAM_API_ID=...    set TELEGRAM_API_HASH=...
  # generate a StringSession once (interactive login) and set:
  set TELEGRAM_SESSION=<string session>
"""
from __future__ import annotations

import os

from agent.social.schema import SocialPost, SourceSpec
from agent.social.sources.base import NotConfigured, register


def _telethon_installed() -> bool:
    try:
        import telethon  # noqa: F401
        return True
    except Exception:
        return False


def _channel(handle: str) -> str:
    h = handle.strip()
    for p in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if h.startswith(p):
            h = h[len(p):]
    return h


@register("telegram")
class TelegramSource:
    platform = "telegram"

    def available(self) -> bool:
        return (_telethon_installed()
                and bool(os.environ.get("TELEGRAM_API_ID"))
                and bool(os.environ.get("TELEGRAM_API_HASH")))

    def fetch(self, specs: list[SourceSpec], *, since_ms: int = 0, limit: int = 50) -> list[SocialPost]:
        if not self.available():
            raise NotConfigured(
                "telegram not ready: install telethon and set TELEGRAM_API_ID / "
                "TELEGRAM_API_HASH / TELEGRAM_SESSION. See docs/SOCIAL_LAYER.md.")
        import asyncio
        return asyncio.run(self._fetch_async(specs, since_ms, limit))

    async def _fetch_async(self, specs, since_ms, limit) -> list[SocialPost]:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        api_id = int(os.environ["TELEGRAM_API_ID"])
        api_hash = os.environ["TELEGRAM_API_HASH"]
        session = StringSession(os.environ.get("TELEGRAM_SESSION", ""))
        out: list[SocialPost] = []
        async with TelegramClient(session, api_id, api_hash) as client:
            for spec in specs:
                if not spec.enabled:
                    continue
                chan = _channel(spec.handle)
                try:
                    async for msg in client.iter_messages(chan, limit=limit):
                        text = (msg.message or "").strip()
                        if not text:
                            continue
                        ts_ms = int(msg.date.timestamp() * 1000) if msg.date else 0
                        if since_ms and ts_ms and ts_ms < since_ms:
                            continue
                        out.append(SocialPost(
                            id=f"telegram:{chan}:{msg.id}", platform="telegram",
                            author=chan, author_display=spec.label or chan, text=text,
                            ts_ms=ts_ms, url=f"https://t.me/{chan}/{msg.id}", weight=spec.weight,
                        ))
                except Exception:
                    continue
        return out
