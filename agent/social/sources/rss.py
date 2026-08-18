"""
RSS / Atom adapter - the zero-credential, never-bans, build-it-today source.

Most crypto news sites and many traders expose an RSS/Atom feed. `handle` is the
feed URL. Parsing is stdlib (no feedparser dep) and tolerant of both RSS 2.0 and
Atom. `parse_feed` is pure (no network) so it's unit-testable offline.
"""
from __future__ import annotations

import datetime as dt
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

from agent.social.schema import SocialPost, SourceSpec
from agent.social.sources.base import register

_ATOM = "{http://www.w3.org/2005/Atom}"
_TIMEOUT = 15.0
_UA = "alien-trade-social/0.1 (+https://github.com)"


def _to_ms(value: str | None) -> int:
    if not value:
        return 0
    value = value.strip()
    # RSS pubDate (RFC 822) first, then Atom/ISO 8601.
    try:
        return int(parsedate_to_datetime(value).timestamp() * 1000)
    except (TypeError, ValueError):
        pass
    try:
        iso = value.replace("Z", "+00:00")
        d = dt.datetime.fromisoformat(iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return int(d.timestamp() * 1000)
    except ValueError:
        return 0


def _clean(text: str | None) -> str:
    if not text:
        return ""
    # Strip naive HTML tags; feeds often wrap descriptions in markup.
    out, depth = [], 0
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())


def parse_feed(text: str, *, handle: str, weight: float = 1.0, limit: int = 50) -> list[SocialPost]:
    """Pure parse of an RSS/Atom document into SocialPosts (no network)."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    posts: list[SocialPost] = []

    # RSS 2.0: <rss><channel><item>
    for item in root.iterfind(".//item"):
        title = _clean(item.findtext("title"))
        desc = _clean(item.findtext("description"))
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link or title).strip()
        ts = _to_ms(item.findtext("pubDate"))
        body = title if not desc else (f"{title} - {desc}" if title else desc)
        if not body:
            continue
        posts.append(SocialPost(
            id=f"rss:{guid}", platform="rss", author=handle, author_display=handle,
            text=body, ts_ms=ts, url=link, weight=weight,
        ))
        if len(posts) >= limit:
            return posts

    # Atom: <feed><entry>
    for entry in root.iterfind(f".//{_ATOM}entry"):
        title = _clean(entry.findtext(f"{_ATOM}title"))
        summary = _clean(entry.findtext(f"{_ATOM}summary")) or _clean(entry.findtext(f"{_ATOM}content"))
        link_el = entry.find(f"{_ATOM}link")
        link = (link_el.get("href") if link_el is not None else "") or ""
        ident = (entry.findtext(f"{_ATOM}id") or link or title).strip()
        ts = _to_ms(entry.findtext(f"{_ATOM}updated") or entry.findtext(f"{_ATOM}published"))
        body = title if not summary else (f"{title} - {summary}" if title else summary)
        if not body:
            continue
        posts.append(SocialPost(
            id=f"rss:{ident}", platform="rss", author=handle, author_display=handle,
            text=body, ts_ms=ts, url=link, weight=weight,
        ))
        if len(posts) >= limit:
            break

    return posts


@register("rss")
class RssSource:
    platform = "rss"

    def available(self) -> bool:
        return True  # no credentials needed

    def fetch(self, specs: list[SourceSpec], *, since_ms: int = 0, limit: int = 50) -> list[SocialPost]:
        out: list[SocialPost] = []
        with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}, follow_redirects=True) as http:
            for spec in specs:
                if not spec.enabled:
                    continue
                try:
                    r = http.get(spec.handle)
                    r.raise_for_status()
                    out.extend(parse_feed(r.text, handle=spec.label or spec.handle,
                                          weight=spec.weight, limit=limit))
                except Exception:
                    # One bad feed never blocks the rest (failure-isolation §9.3).
                    continue
        return out
