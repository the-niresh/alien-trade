"""
The swappable source interface + a tiny registry.

Every platform is one adapter implementing `SocialSource`. Adding a channel later
is: write an adapter, decorate with `@register("name")`, done — nothing else in
the pipeline changes (the "swappable adapter" vision).
"""
from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from agent.social.schema import SocialPost, SourceSpec


class NotConfigured(RuntimeError):
    """An adapter whose credentials/deps are not set up was asked to fetch.

    Callers catch this and skip the source (failure-isolation, §9.3) — it is
    never fatal to the ingest run.
    """


@runtime_checkable
class SocialSource(Protocol):
    platform: str

    def available(self) -> bool:
        """True if this adapter can actually fetch right now (deps + creds present)."""
        ...

    def fetch(self, specs: list[SourceSpec], *, since_ms: int = 0, limit: int = 50) -> list[SocialPost]:
        """Pull recent posts for the given watchlist entries on this platform."""
        ...


_REGISTRY: dict[str, type] = {}


def register(platform: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        cls.platform = platform  # type: ignore[attr-defined]
        _REGISTRY[platform] = cls
        return cls
    return deco


def get_source(platform: str) -> SocialSource:
    cls = _REGISTRY.get(platform)
    if cls is None:
        raise KeyError(f"no social source registered for platform={platform!r}")
    return cls()  # type: ignore[return-value]


def registered_platforms() -> list[str]:
    return sorted(_REGISTRY)


def available_platforms() -> dict[str, bool]:
    """Map platform -> whether it can fetch right now (for the UI / status line)."""
    out: dict[str, bool] = {}
    for p, cls in _REGISTRY.items():
        try:
            out[p] = bool(cls().available())  # type: ignore[call-arg]
        except Exception:
            out[p] = False
    return out
