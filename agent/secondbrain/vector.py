"""
VectorStore - the Second Brain index, over Upstash Vector's REST API.

The Upstash index was provisioned with a server-side embedding model
(BAAI/bge-small-en-v1.5), so we send raw text to `/upsert-data` and `/query-data`
and Upstash embeds it - no local embedding model, no extra dependency, same
house style as ConvexBridge (raw httpx REST).

Offline (no URL/token) it falls back to an in-memory token-overlap index, so the
Hermes loop, the tests, and a laptop demo all run with zero network. A
live-but-erroring Upstash never crashes a cycle - errors are logged and treated
as "no memory found" (fail-open on the read path, which only ever *relaxes* a
block; the deterministic risk engine remains the hard floor).

`kind` is stored in metadata and filtered client-side (request a larger topK,
then keep the matching kind) - robust across Upstash metadata-filter syntax
versions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from agent.secondbrain.schema import MemoryHit


@dataclass
class VectorStore:
    url: str = ""
    token: str = ""
    timeout: float = 15.0
    _http: Optional[httpx.Client] = field(default=None, init=False, repr=False)
    _mem: list[dict] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.enabled:
            self._http = httpx.Client(
                base_url=self.url.rstrip("/"),
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.token)

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    # ── writes ─────────────────────────────────────────────────────────────────

    def upsert(self, id: str, text: str, metadata: Optional[dict] = None) -> bool:
        """Upsert one record (id is the idempotency key - re-upsert overwrites)."""
        meta = dict(metadata or {})
        meta.setdefault("text", text)
        if not self.enabled:
            self._mem = [r for r in self._mem if r["id"] != id]
            self._mem.append({"id": id, "data": text, "metadata": meta})
            return True
        try:
            r = self._http.post("/upsert-data",
                                 json={"id": id, "data": text, "metadata": meta})
            r.raise_for_status()
            return True
        except Exception as e:  # noqa: BLE001 - memory must never crash a cycle
            print(f"[vector] upsert {id!r} failed: {e}")
            return False

    # ── reads ──────────────────────────────────────────────────────────────────

    def query(self, text: str, top_k: int = 5, kind: Optional[str] = None) -> list[MemoryHit]:
        """Nearest neighbours to `text`. `kind` filters by metadata client-side."""
        over = top_k * 4 if kind else top_k
        if not self.enabled:
            hits = self._mem_query(text, over)
        else:
            hits = self._remote_query(text, over)
        if kind:
            hits = [h for h in hits if h.metadata.get("kind") == kind]
        return hits[:top_k]

    def _remote_query(self, text: str, top_k: int) -> list[MemoryHit]:
        try:
            r = self._http.post("/query-data", json={
                "data": text, "topK": top_k,
                "includeMetadata": True, "includeData": True,
            })
            r.raise_for_status()
            result = r.json().get("result", []) or []
            return [
                MemoryHit(
                    id=str(h.get("id", "")),
                    score=float(h.get("score", 0.0)),
                    text=str(h.get("data") or (h.get("metadata") or {}).get("text", "")),
                    metadata=h.get("metadata") or {},
                )
                for h in result
            ]
        except Exception as e:  # noqa: BLE001
            print(f"[vector] query failed: {e}")
            return []

    # ── offline token-overlap index ──────────────────────────────────────────────

    def _mem_query(self, text: str, top_k: int) -> list[MemoryHit]:
        q = _tokens(text)
        scored = []
        for r in self._mem:
            score = _jaccard(q, _tokens(r["data"]))
            scored.append(MemoryHit(id=r["id"], score=score,
                                    text=r["data"], metadata=r["metadata"]))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0
