"""
Response cache over Upstash Redis (REST). Keyed by a hash of
(tier, system, prompt, max_tokens), so an identical LLM request is answered for
free on the second ask — the cheap half of the token-optimisation story (the
other half is tier routing in llm.py).

Called a "semantic cache" loosely: it is an exact-prefix hash cache today,
upgradeable to embedding-nearest-neighbour via the VectorStore without changing
this interface. Co-pilot questions and AutoResearch prompts repeat far more than
they vary, so even exact-match cache earns its keep.

Offline (no URL/token) it falls back to an in-process dict. Errors never crash a
call — a cache miss just means we pay for the LLM call we were going to make.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class ResponseCache:
    url: str = ""
    token: str = ""
    ttl_seconds: int = 86_400          # 1 day — research/co-pilot answers age out
    timeout: float = 10.0
    _http: Optional[httpx.Client] = field(default=None, init=False, repr=False)
    _mem: dict[str, str] = field(default_factory=dict, init=False, repr=False)

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

    @staticmethod
    def key(*parts: object) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return "sbcache:" + hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, key: str) -> Optional[str]:
        if not self.enabled:
            return self._mem.get(key)
        try:
            r = self._http.get(f"/get/{key}")
            r.raise_for_status()
            return r.json().get("result")
        except Exception as e:  # noqa: BLE001
            print(f"[cache] get failed: {e}")
            return None

    def set(self, key: str, value: str) -> None:
        if not self.enabled:
            self._mem[key] = value
            return
        try:
            # Upstash REST: /set/{key}/{value}?EX=seconds — value in body for size.
            r = self._http.post(f"/set/{key}", params={"EX": self.ttl_seconds}, content=value)
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            print(f"[cache] set failed: {e}")
