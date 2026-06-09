"""
FastAPI front for the live runtime.

Trigger.dev (scheduled jobs) and the PWA poke these routes; the heavy lifting is
still the /core strategy inside DecisionLoop. Endpoints:

    GET  /health   — liveness
    POST /cycle    — run exactly one decision cycle (Trigger.dev calls this)
    GET  /status   — ledger + risk snapshot
    POST /halt     — kill switch on  (also flips Convex config.halted)
    POST /resume   — kill switch off

The loop is a process singleton built once from AgentConfig. /cycle is safe to
call repeatedly: idempotency keys (cycle_id) stop any double execution.

Run:  core/.venv/Scripts/python.exe -m uvicorn agent.server:app --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from agent.config import AgentConfig
from agent.loop import DecisionLoop, CycleResult
from agent.runtime import build_loop

try:
    from fastapi import FastAPI
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "FastAPI not installed. Install the agent extras: "
        "core/.venv/Scripts/python.exe -m pip install fastapi uvicorn"
    ) from e


_loop: DecisionLoop | None = None
_supervisor = None   # agent.graph.supervisor.Supervisor — built lazily after loop warms


def get_loop() -> DecisionLoop:
    global _loop
    if _loop is None:
        cfg = AgentConfig(symbol=os.environ.get("AGENT_SYMBOL", "ETH"))
        dry = os.environ.get("AGENT_DRY_RUN", "").lower() in ("1", "true", "yes")
        recover = os.environ.get("AGENT_RECOVER", "").lower() in ("1", "true", "yes")
        _loop = build_loop(cfg, dry_run=dry, recover=recover)
    return _loop


def get_supervisor():
    """Lazily build the LangGraph supervisor, reusing the loop's second_brain + bridge.
    Returns None gracefully when SECOND_BRAIN=0 or langgraph is absent."""
    global _supervisor
    if _supervisor is not None:
        return _supervisor
    loop = get_loop()
    sb = getattr(loop, "second_brain", None)
    if sb is None:
        return None
    try:
        from agent.graph.supervisor import Supervisor
        _supervisor = Supervisor(sb, bridge=loop.bridge)
    except Exception:  # noqa: BLE001 — advisory layer; never break the trading server
        return None
    return _supervisor


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_loop()   # warm the singleton (seeds Convex config too)
    yield


app = FastAPI(title="Alien-Trade Agent", version="0.1.0", lifespan=lifespan)


def _cycle_to_dict(res: CycleResult | None) -> dict:
    if res is None:
        return {"ran": False, "reason": "no market data available"}
    filled = bool(res.execution and res.execution.is_fill)
    return {
        "ran": True,
        "cycle_id": res.cycle_id,
        "timestamp_ms": res.timestamp_ms,
        "halted": res.halted,
        "regime": res.regime,
        "verdict": res.verdict,
        "reason": res.reason,
        "filled": filled,
        "side": res.order.side if (filled and res.order) else None,
        "realized_pnl": res.execution.realized_pnl if (filled and res.execution) else None,
        "signals": res.breakdown,
        "tx_hash": res.execution.tx_hash if res.execution else None,
        "equity": res.equity,
        "drawdown_pct": res.drawdown_pct,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/social/ingest")
def social_ingest() -> dict:
    """Run one social ingest pass: fetch posts → score sentiment → write Convex.
    Off the hot path — returns ok:false on any error without raising."""
    try:
        from pathlib import Path
        from agent.social.ingest import ingest, load_watchlist
        wl = Path(__file__).resolve().parent / "social" / "watchlist.example.json"
        symbols, specs = load_watchlist(wl)
        res = ingest(symbols, specs)
        loop = get_loop()
        inserted = loop.bridge.record_social_posts(res.posts)
        for sym, reading in res.readings.items():
            loop.bridge.set_sentiment_state(reading)
        return {
            "ok": True,
            "posts_ingested": len(res.posts),
            "posts_inserted": inserted,
            "symbols": list(res.readings.keys()),
            "skipped": res.skipped,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@app.post("/cycle")
def run_cycle() -> dict:
    loop = get_loop()
    history = loop.feed.next()
    if history is None:
        return _cycle_to_dict(None)
    return _cycle_to_dict(loop.run_cycle(history))


@app.get("/status")
def status() -> dict:
    loop = get_loop()
    led = loop.ledger
    return {
        "mode": loop.mode,
        "symbol": loop.symbol,
        "halted": loop.bridge.is_halted(),
        "cash": led.cash,
        "units": led.units,
        "realized_pnl": led.realized_pnl_total,
        "cumulative_fees": led.cumulative_fees,
        "cumulative_gas": led.cumulative_gas,
        "peak_equity": led.peak_equity,
        "consecutive_losses": led.consecutive_losses,
    }


@app.post("/halt")
def halt() -> dict:
    get_loop().bridge.set_halted(True)
    return {"halted": True}


@app.post("/resume")
def resume() -> dict:
    get_loop().bridge.set_halted(False)
    return {"halted": False}


# ── Second Brain (Step 6) — all off the trade hot path ──────────────────────────

def _second_brain():
    return getattr(get_loop(), "second_brain", None)


@app.post("/copilot")
def copilot(body: dict) -> dict:
    """Grounded Q&A over the Second Brain. POST {"question": "..."}."""
    sb = _second_brain()
    if sb is None:
        return {"answer": "Second Brain disabled or offline.", "grounded": False}
    return sb.copilot().ask(str(body.get("question", "")))


@app.post("/research")
def research() -> dict:
    """Run one Karpathy AutoResearch cycle and store digests."""
    sb = _second_brain()
    if sb is None:
        return {"digests": 0, "note": "Second Brain disabled or offline."}
    digests = sb.research(symbol=get_loop().symbol).run_cycle()
    return {"digests": len(digests),
            "questions": [d.question for d in digests]}


@app.post("/supervisor")
def supervisor_event(body: dict) -> dict:
    """Observe→react entry for the LangGraph supervisor team.

    Trigger.dev calls this on schedule ticks (kind=research_tick) and after
    sell fills (kind=position_closed). The supervisor routes to the right
    advisory node and emits AgentEvents to the Activity Channel. Always
    returns — a failed advisory run must never surface as a 5xx to Trigger.dev
    (which would dead-letter and alert on a non-critical path).
    """
    sup = get_supervisor()
    if sup is None:
        return {"ok": False, "reason": "supervisor unavailable (SECOND_BRAIN=0 or langgraph absent)"}
    kind = str(body.get("kind", "user"))
    symbol = str(body.get("symbol", "") or get_loop().symbol)
    cycle_id = body.get("cycle_id")
    payload = body.get("payload") or {}
    try:
        out = sup.handle(
            body.get("text", kind),
            kind=kind, symbol=symbol,
            cycle_id=cycle_id, payload=payload,
        )
        return {
            "ok": True,
            "route": out.get("route"),
            "events_emitted": len(out.get("events", [])),
        }
    except Exception as exc:  # noqa: BLE001 — advisory path; never raise to Trigger.dev
        # 8.14: surface the failure in the cockpit channel so the operator can see it
        try:
            from agent.graph.contracts import AgentEvent, KIND_CONTROL
            sup._emit(AgentEvent(
                agent="Supervisor", kind=KIND_CONTROL,
                headline=f"Supervisor endpoint failed: {type(exc).__name__}",
                cycle_id=cycle_id,
                detail={"error": str(exc)[:200], "error_type": type(exc).__name__},
            ))
        except Exception:  # noqa: BLE001
            pass
        return {"ok": False, "reason": str(exc)}


@app.get("/telemetry")
def telemetry() -> dict:
    """LLM cost telemetry: tokens, cost, cache-hit rate, $ saved vs naive Opus."""
    sb = _second_brain()
    if sb is None:
        return {"enabled": False}
    return {"enabled": True, **sb.telemetry.snapshot()}
