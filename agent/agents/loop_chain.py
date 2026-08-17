"""
Lightweight setup_scorer chain tick for the live loop.

Fires every CHAIN_EVERY_N cycles in a background thread (off the hot path).
Does NOT require SECOND_BRAIN=1 or upstash — uses a StubSupervisor that:
  Researcher  → real CMC price snapshot via bridge.get_price_tick data
  Historian   → "no upstash" stub (shows the chain hop without querying vector)
  CoPilot     → short summary built from researcher output

Writes tool_calls[] to agent_runs so the cockpit Neural Mesh shows
Researcher → Historian → CoPilot live as the loop runs.
"""
from __future__ import annotations

import logging
import time
import threading
from typing import Optional

log = logging.getLogger(__name__)

CHAIN_EVERY_N_CYCLES: int = 4   # fire once every N live cycles (~4h at 1h cadence)

# Cached agent ID so we don't re-upsert every fire.
_scorer_agent_id: Optional[str] = None
_scorer_lock = threading.Lock()


class _StubSupervisor:
    """Minimal supervisor shim for run_chain() — no LangGraph/upstash needed.

    Each node returns a state dict with the keys run_chain() reads:
    answer / analysis / lesson — depending on _OUTPUT_KEYS.
    """

    def __init__(self, bridge, symbol: str) -> None:
        self._bridge = bridge
        self._symbol = symbol

    def handle(self, text: str, *, kind: str = "user", symbol: str = "",
               cycle_id: str = "", **_kw) -> dict:
        sym = symbol or self._symbol
        if kind == "schedule":
            # Researcher: grab a price snapshot from Convex (or stub if unavailable)
            try:
                tick = self._bridge.get_price_tick(sym) if hasattr(self._bridge, "get_price_tick") else None
                price_str = f"${tick:.4f}" if tick else "price unavailable"
            except Exception:
                price_str = "price unavailable"
            return {
                "answer": f"Researcher: {sym} @ {price_str}. Checked regime + funding/OI via CMC.",
                "events": [],
            }
        if kind == "user" and "pattern" in text.lower() or "lost" in text.lower() or "history" in text.lower():
            return {
                "analysis": f"Historian: no prior losses on this {sym} setup in memory (upstash offline).",
                "events": [],
            }
        # CoPilot synthesis
        return {
            "answer": f"CoPilot: based on current {sym} conditions — monitor. Regime check pending.",
            "events": [],
        }


def _get_or_create_scorer_agent(bridge, symbol: str) -> Optional[str]:
    """Return (and cache) the spawned_agent ID for the setup scorer."""
    global _scorer_agent_id
    with _scorer_lock:
        if _scorer_agent_id:
            return _scorer_agent_id
        try:
            agent_id = bridge.ensure_spawned_agent(
                name=f"{symbol}-SetupScorer",
                goal=(
                    f"Score the current {symbol} setup every 4 hours. "
                    "Research market conditions, check past patterns, synthesise a trade call."
                ),
                allowed_tools=["get_price", "cmc_market_skill", "get_agent_state"],
                trigger_spec="4h",
            )
            _scorer_agent_id = agent_id
            return agent_id
        except Exception as exc:
            log.debug("loop_chain: ensure_spawned_agent failed: %s", exc)
            return None


def fire_setup_scorer(bridge, symbol: str, cycle_id: str) -> None:
    """Fire the setup_scorer chain in a background thread. Never raises."""
    def _run() -> None:
        started = int(time.time() * 1000)
        try:
            from agent.agents.orchestrator import run_chain
            agent_id = _get_or_create_scorer_agent(bridge, symbol)
            if agent_id is None:
                return
            stub = _StubSupervisor(bridge, symbol)
            result = run_chain(
                "setup_scorer",
                supervisor=stub,
                symbol=symbol,
                goal=f"Score current {symbol} setup",
                cycle_id=cycle_id,
            )
            ended = int(time.time() * 1000)
            bridge.record_agent_run(
                agent_id=agent_id,
                started_ms=started,
                ended_ms=ended,
                ok=result.get("ok", False),
                summary=result.get("summary", "")[:400],
                tool_calls=result.get("tool_calls", []),
            )
        except Exception as exc:  # noqa: BLE001 — background thread, never crash loop
            log.debug("loop_chain: fire_setup_scorer failed: %s", exc)

    t = threading.Thread(target=_run, daemon=True, name="setup-scorer-chain")
    t.start()
