"""
Source adapters. Importing this package registers every built-in adapter
against the registry in `base.py` (so `get_source("rss")` etc. work).
"""
from __future__ import annotations

from agent.social.sources import farcaster, rss, telegram, twitter  # noqa: F401  (register side-effect)
from agent.social.sources.base import (
    NotConfigured,
    SocialSource,
    available_platforms,
    get_source,
    registered_platforms,
)

__all__ = [
    "NotConfigured",
    "SocialSource",
    "available_platforms",
    "get_source",
    "registered_platforms",
]
