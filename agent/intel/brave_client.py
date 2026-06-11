"""
Brave Search API client — news + web (free tier, key in BRAVE_API_KEY).

Offline-first: with no key the client is a no-op that returns [] so the whole intel
layer degrades gracefully (tests run with zero network; a laptop demo never hangs on
a missing key). The operator drops BRAVE_API_KEY into .env.local to activate.

Docs: https://api.search.brave.com/app/documentation/news-search/get-started
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BRAVE_BASE_URL = os.getenv("BRAVE_BASE_URL", "https://api.search.brave.com")
NEWS_PATH = "/res/v1/news/search"


@dataclass
class NewsItem:
    title: str
    description: str
    url: str
    source: str
    age: str          # human string from Brave, e.g. "3 hours ago"

    @property
    def text(self) -> str:
        return f"{self.title}. {self.description}".strip()


class BraveSearchClient:
    """Thin wrapper over the Brave News endpoint. No key -> enabled is False."""

    def __init__(self, api_key: str | None = None, timeout: float = 15.0):
        self.api_key = api_key if api_key is not None else os.getenv("BRAVE_API_KEY", "")
        self.enabled = bool(self.api_key)
        self._http = httpx.Client(base_url=BRAVE_BASE_URL, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BraveSearchClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def news(self, query: str, count: int = 20, freshness: str = "pd") -> list[NewsItem]:
        """Recent news for `query`. `freshness`: pd=past day, pw=week, pm=month.
        Returns [] when disabled or on any error (advisory layer never raises)."""
        if not self.enabled:
            return []
        try:
            return self._news(query, count, freshness)
        except Exception:
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6))
    def _news(self, query: str, count: int, freshness: str) -> list[NewsItem]:
        r = self._http.get(
            NEWS_PATH,
            params={"q": query, "count": count, "freshness": freshness,
                    "spellcheck": 0, "safesearch": "off"},
            headers={"Accept": "application/json",
                     "X-Subscription-Token": self.api_key},
        )
        r.raise_for_status()
        results = r.json().get("results", []) or []
        items: list[NewsItem] = []
        for it in results:
            meta = it.get("meta_url") or {}
            items.append(NewsItem(
                title=str(it.get("title", "")),
                description=str(it.get("description", "")),
                url=str(it.get("url", "")),
                source=str(meta.get("hostname", "") or it.get("source", "")),
                age=str(it.get("age", "") or it.get("page_age", "")),
            ))
        return items
