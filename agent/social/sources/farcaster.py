"""
Farcaster adapter — crypto-native, open, agent-friendly, no credentials.

Reads a user's recent casts via the public Warpcast API:
  1. username -> fid   (GET /v2/user-by-username)
  2. fid      -> casts (GET /v2/casts)
Defensive: any failure on a handle is swallowed so the run continues (§9.3).
`handle` is the Farcaster username (no leading @).
"""
from __future__ import annotations

import httpx

from agent.social.schema import SocialPost, SourceSpec
from agent.social.sources.base import register

_API = "https://api.warpcast.com"
_TIMEOUT = 15.0


def _cast_to_post(cast: dict, *, handle: str, weight: float) -> SocialPost | None:
    text = (cast.get("text") or "").strip()
    if not text:
        return None
    chash = cast.get("hash") or ""
    ts = int(cast.get("timestamp") or 0)  # Warpcast returns epoch ms
    author = (cast.get("author") or {})
    uname = author.get("username") or handle
    return SocialPost(
        id=f"farcaster:{chash}", platform="farcaster", author=uname,
        author_display=author.get("displayName") or uname, text=text, ts_ms=ts,
        url=f"https://warpcast.com/{uname}/{chash[:10]}" if chash else "", weight=weight,
    )


@register("farcaster")
class FarcasterSource:
    platform = "farcaster"

    def available(self) -> bool:
        return True  # public API, no key

    def fetch(self, specs: list[SourceSpec], *, since_ms: int = 0, limit: int = 50) -> list[SocialPost]:
        out: list[SocialPost] = []
        with httpx.Client(timeout=_TIMEOUT, base_url=_API) as http:
            for spec in specs:
                if not spec.enabled:
                    continue
                try:
                    u = http.get("/v2/user-by-username", params={"username": spec.handle})
                    u.raise_for_status()
                    fid = (((u.json().get("result") or {}).get("user") or {}).get("fid"))
                    if not fid:
                        continue
                    c = http.get("/v2/casts", params={"fid": fid, "limit": limit})
                    c.raise_for_status()
                    casts = ((c.json().get("result") or {}).get("casts") or [])
                    for cast in casts:
                        post = _cast_to_post(cast, handle=spec.handle, weight=spec.weight)
                        if post is not None:
                            out.append(post)
                except Exception:
                    continue
        return out
