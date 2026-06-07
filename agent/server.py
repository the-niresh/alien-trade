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


def get_loop() -> DecisionLoop:
    global _loop
    if _loop is None:
        cfg = AgentConfig(symbol=os.environ.get("AGENT_SYMBOL", "BNB"))
        dry = os.environ.get("AGENT_DRY_RUN", "").lower() in ("1", "true", "yes")
        recover = os.environ.get("AGENT_RECOVER", "").lower() in ("1", "true", "yes")
        _loop = build_loop(cfg, dry_run=dry, recover=recover)
    return _loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_loop()   # warm the singleton (seeds Convex config too)
    yield


app = FastAPI(title="Alien-Trade Agent", version="0.1.0", lifespan=lifespan)


def _cycle_to_dict(res: CycleResult | None) -> dict:
    if res is None:
        return {"ran": False, "reason": "no market data available"}
    return {
        "ran": True,
        "cycle_id": res.cycle_id,
        "timestamp_ms": res.timestamp_ms,
        "halted": res.halted,
        "regime": res.regime,
        "verdict": res.verdict,
        "reason": res.reason,
        "filled": bool(res.execution and res.execution.is_fill),
        "tx_hash": res.execution.tx_hash if res.execution else None,
        "equity": res.equity,
        "drawdown_pct": res.drawdown_pct,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
