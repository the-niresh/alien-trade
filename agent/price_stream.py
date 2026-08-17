"""
Optional low-latency price feed (default OFF).

The deterministic watch checker (agent/watches.py) works fine on the loop's
per-cycle price (bar.close). This module is the *latency upgrade* from the design
doc: a Binance WebSocket stream that pushes price in ~ms, held in a thread-safe
cache. When enabled and fresh, the loop's watch snapshot uses it instead of the
hourly bar — so a price watch trips in seconds, not at the next cycle. Still zero
LLM, still off the scored trade cadence (locked decision #6).

Safety: this is OFF by default. The live loop only consumes it if a stream is
explicitly attached (PRICE_STREAM=1 at runtime). With no stream attached, every
caller degrades to the existing per-cycle price — nothing changes. Binance WS is
its own streaming protocol (not JSON-RPC); the on-chain eth_subscribe path is a
separate, endpoint-gated follow-on (see docs/AGENTS_MONITOR_DESIGN.md §8).
"""
from __future__ import annotations

import threading
import time
from typing import Optional

try:  # async WS client — present in this venv; absence simply keeps the feed off.
    import websockets  # noqa: F401
    _HAS_WS = True
except Exception:  # noqa: BLE001
    _HAS_WS = False

_QUOTES = ("USDT", "BUSD", "USDC", "USD")


def base_token(symbol: str) -> str:
    s = symbol.upper()
    for q in _QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return s[: -len(q)]
    return s


class PriceCache:
    """Thread-safe latest-price store with staleness. Pure (no network) — unit tested."""

    def __init__(self) -> None:
        self._d: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def update(self, symbol: str, price: float, ts: Optional[float] = None) -> None:
        with self._lock:
            self._d[base_token(symbol)] = (float(price), ts if ts is not None else time.time())

    def get(self, symbol: str) -> Optional[tuple[float, float]]:
        with self._lock:
            return self._d.get(base_token(symbol))

    def fresh_price(self, symbol: str, max_age_s: float = 10.0, *, now: Optional[float] = None) -> Optional[float]:
        """Latest price if seen within max_age_s, else None (caller falls back to poll)."""
        v = self.get(symbol)
        if v is None:
            return None
        price, ts = v
        if (now if now is not None else time.time()) - ts > max_age_s:
            return None
        return price


class BinancePriceStream:
    """Binance miniTicker WS feed → PriceCache, in a daemon thread with reconnect/backoff.
    `start()` is a no-op returning False when websockets is unavailable, so callers stay safe."""

    def __init__(self, tokens: list[str], cache: Optional[PriceCache] = None,
                 base: str = "wss://stream.binance.com:9443") -> None:
        self.tokens = [t.upper() for t in tokens]
        self.cache = cache or PriceCache()
        self._base = base
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        if not _HAS_WS or not self.tokens:
            return False
        self._thread = threading.Thread(target=self._run, name="binance-price-ws", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:  # pragma: no cover — network loop, exercised live not in unit tests
        import asyncio
        try:
            asyncio.run(self._loop())
        except Exception:  # noqa: BLE001 — a dead feed must never raise into the process
            pass

    async def _loop(self) -> None:  # pragma: no cover — network loop
        import json
        import websockets

        streams = "/".join(f"{t.lower()}usdt@miniTicker" for t in self.tokens)
        url = f"{self._base}/stream?streams={streams}"
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    backoff = 1.0
                    while not self._stop.is_set():
                        msg = await ws.recv()
                        data = json.loads(msg).get("data", {})
                        sym, price = data.get("s", ""), data.get("c")
                        if sym and price is not None:
                            self.cache.update(sym, price)
            except Exception:  # noqa: BLE001 — reconnect with capped backoff
                if self._stop.is_set():
                    break
                time.sleep(min(backoff, 30.0))
                backoff *= 2
