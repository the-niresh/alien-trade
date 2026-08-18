"""
X / Twitter adapter via twscrape - the swappable, credential-gated source.

NOTE (see docs/SOCIAL_LAYER.md): twscrape scrapes X. It violates X's ToS, needs a
logged-in (use a BURNER) X account, and is ban-prone - so it is one adapter, not
the foundation. It stays dormant until configured; nothing depends on it.

Setup (operator, once):
  uv pip install --python core/.venv/Scripts/python.exe twscrape
  python -m twscrape add_accounts ...   # add a burner account
  python -m twscrape login_accounts
  set TWSCRAPE_DB=...  (or X_ACCOUNTS_READY=1 once accounts are in twscrape's db)
`handle` is the X username (no leading @).
"""
from __future__ import annotations

import os

from agent.social.schema import SocialPost, SourceSpec
from agent.social.sources.base import NotConfigured, register


def _twscrape_installed() -> bool:
    try:
        import twscrape  # noqa: F401
        return True
    except Exception:
        return False


@register("twitter")
class TwitterSource:
    platform = "twitter"

    def available(self) -> bool:
        if not _twscrape_installed():
            return False
        # twscrape needs at least one logged-in account in its db; the operator
        # signals readiness via env once that's done.
        return os.environ.get("X_ACCOUNTS_READY", "").lower() in ("1", "true", "yes") \
            or bool(os.environ.get("TWSCRAPE_DB"))

    def fetch(self, specs: list[SourceSpec], *, since_ms: int = 0, limit: int = 50) -> list[SocialPost]:
        if not self.available():
            raise NotConfigured(
                "twitter(twscrape) not ready: install twscrape + add a burner X "
                "account, then set X_ACCOUNTS_READY=1. See docs/SOCIAL_LAYER.md.")
        import asyncio
        return asyncio.run(self._fetch_async(specs, since_ms, limit))

    async def _fetch_async(self, specs, since_ms, limit) -> list[SocialPost]:
        import twscrape

        api = twscrape.API(os.environ.get("TWSCRAPE_DB") or "accounts.db")
        out: list[SocialPost] = []
        for spec in specs:
            if not spec.enabled:
                continue
            try:
                user = await api.user_by_login(spec.handle.lstrip("@"))
                if user is None:
                    continue
                async for tw in api.user_tweets(user.id, limit=limit):
                    ts_ms = int(tw.date.timestamp() * 1000) if getattr(tw, "date", None) else 0
                    if since_ms and ts_ms and ts_ms < since_ms:
                        continue
                    out.append(SocialPost(
                        id=f"twitter:{tw.id}", platform="twitter",
                        author=spec.handle.lstrip("@"),
                        author_display=getattr(user, "displayname", "") or spec.handle,
                        text=tw.rawContent or "", ts_ms=ts_ms,
                        url=f"https://x.com/{spec.handle.lstrip('@')}/status/{tw.id}",
                        weight=spec.weight,
                    ))
            except Exception:
                continue
        return out
