"""
FastAPI front for the live runtime.

Trigger.dev (scheduled jobs) and the PWA poke these routes; the heavy lifting is
still the /core strategy inside DecisionLoop. Endpoints:

    GET  /health   - liveness
    POST /cycle    - run exactly one decision cycle (Trigger.dev calls this)
    GET  /status   - ledger + risk snapshot
    POST /halt     - kill switch on  (also flips Convex config.halted)
    POST /resume   - kill switch off

The loop is a process singleton built once from AgentConfig. /cycle is safe to
call repeatedly: idempotency keys (cycle_id) stop any double execution.

Run:  core/.venv/Scripts/python.exe -m uvicorn agent.server:app --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from typing import TYPE_CHECKING

from agent.config import AgentConfig
from agent.loop import DecisionLoop, CycleResult
from agent.runtime import build_loop

if TYPE_CHECKING:                # imported lazily at call time; annotation only
    from agent.twak_cli import TwakCli

try:
    from fastapi import FastAPI, HTTPException, Request
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "FastAPI not installed. Install the agent extras: "
        "core/.venv/Scripts/python.exe -m pip install fastapi uvicorn"
    ) from e


def _require_api_token(request: Request) -> None:
    """Reject requests to sensitive endpoints unless AGENT_API_TOKEN matches.
    No-op when AGENT_API_TOKEN is unset (dev/paper convenience)."""
    token = os.environ.get("AGENT_API_TOKEN", "")
    if not token:
        return
    header = request.headers.get("X-API-Token", "")
    if header != token:
        raise HTTPException(status_code=401, detail="Unauthorized")


_loop: DecisionLoop | None = None
_supervisor = None   # agent.graph.supervisor.Supervisor - built lazily after loop warms


_ACTION_VERBS = {
    "halt": {"type": "halt", "params": {}, "summary": "Halt all trading."},
    "resume": {"type": "resume", "params": {}, "summary": "Resume trading."},
    "stop trading": {"type": "halt", "params": {}, "summary": "Halt all trading."},
}


def _extract_action(question: str, answer: str) -> dict | None:
    """Lightweight server-side action extraction. Client grammar is the primary path."""
    q = question.lower()
    for trigger, action in _ACTION_VERBS.items():
        if trigger in q:
            return action
    return None


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
    except Exception:  # noqa: BLE001 - advisory layer; never break the trading server
        return None
    return _supervisor


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_loop()   # warm the singleton (seeds Convex config too)
    yield


app = FastAPI(title="Alien-Trade Agent", version="0.1.0", lifespan=lifespan)

# Routes reachable without the API token. Everything else (copilot/LLM-cost,
# twak wallet reads, supervisor/dreamer, telemetry, skill compute) is gated by
# the middleware below when AGENT_API_TOKEN is set. The primary protection is
# binding uvicorn to 127.0.0.1 (see alien-api.service); this is defense in depth.
_PUBLIC_PATHS = frozenset({"/health", "/skill/manifest", "/skill/manifests", "/docs", "/openapi.json"})


@app.middleware("http")
async def _api_token_guard(request: Request, call_next):
    """Enforce AGENT_API_TOKEN on every non-public route when a token is configured.
    No-op when the token is unset (local/paper dev) - in that mode the localhost
    bind is what keeps these endpoints off the public internet."""
    token = os.environ.get("AGENT_API_TOKEN", "")
    if token and request.url.path not in _PUBLIC_PATHS:
        if request.headers.get("X-API-Token", "") != token:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

# TWAK native x402 provider: meters POST /skill/signal_score at $0.01/call.
# No-op when X402_WALLET_ADDRESS is absent - endpoint stays free.
from agent.x402_provider import register as _x402_register  # noqa: E402
_x402_register(app)


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
    Off the hot path - returns ok:false on any error without raising."""
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
def run_cycle(request: Request) -> dict:
    _require_api_token(request)
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
def halt(request: Request) -> dict:
    _require_api_token(request)
    get_loop().bridge.set_halted(True)
    return {"halted": True}


@app.post("/resume")
def resume(request: Request) -> dict:
    _require_api_token(request)
    get_loop().bridge.set_halted(False)
    return {"halted": False}


# ── Second Brain (Step 6) - all off the trade hot path ──────────────────────────

def _second_brain():
    return getattr(get_loop(), "second_brain", None)


def _copilot_fallback(question: str) -> str:
    """Call Claude directly with live trading context when Second Brain is offline."""
    import os, anthropic as _anthropic
    loop = get_loop()
    led = loop.ledger
    halted = loop.bridge.is_halted()
    position_str = (
        f"{led.units:.6f} units @ ${led.avg_entry:.2f} avg entry"
        if led.units > 0 else "flat (no open position)"
    )
    system = (
        "You are the Alien-Trade Co-Pilot - an intelligent assistant embedded inside an autonomous BSC trading agent.\n\n"
        "## About Alien-Trade\n"
        "Alien-Trade is a fully autonomous, self-custody BSC trading agent.\n"
        "- Token allowlist: ETH, CAKE, UNI, LINK, AAVE - traded on PancakeSwap spot via Trust Wallet Agent Kit (TWAK).\n"
        "  The allowlist is a risk control: these are the only tokens the strategy was tested on.\n"
        "- Self-custody: all signing goes through TWAK; private keys never touch the code or logs\n"
        "- Strategy engine: deterministic Python makes all buy/sell decisions on a 1-hour cycle - LLM is advisory only\n"
        "- Strategy: contrarian approach using Fear & Greed index, momentum (S1), derivatives/funding rate (S2), sentiment (S3), on-chain flow (S4)\n"
        "- Optimization target: Sortino ratio + low drawdown - risk-adjusted performance, not raw returns\n"
        "- Live on BSC mainnet - the agent evaluates regime and risk gates each hour, then acts or holds\n\n"
        "## How to Handle Trade Requests\n"
        "When asked to place a trade, buy, or sell: lead with how the autonomous system works. "
        "The strategy engine decides each cycle when conditions align. "
        "Operators can halt/resume via cockpit controls. Offer to share current market context instead.\n\n"
        "## Strict Response Rules\n"
        "1. Never start a response with 'No', 'I can't', 'I'm unable', 'Unfortunately', or any negative opener\n"
        "2. Lead with context or what IS possible - state any limitation only after the explanation\n"
        "3. Only surface PnL, drawdown, or equity data when the user explicitly asks about performance or results\n"
        "4. Answer concisely in markdown\n\n"
        f"## Live Agent State\n"
        f"- Mode: {loop.mode} | Symbol: {loop.symbol} | Status: {'HALTED' if halted else 'running'}\n"
        f"- Cash: ${led.cash:,.2f} | Position: {position_str}\n"
        f"- Consecutive losses: {led.consecutive_losses}\n"
    )
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "_Co-Pilot unavailable: ANTHROPIC_API_KEY not set._"
    client = _anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return msg.content[0].text


def _copilot_read_loop(question: str) -> dict | None:
    """Live-read tool-loop brain for the co-pilot. Returns the loop result, or
    None when no ANTHROPIC_API_KEY (caller falls back to the narrator)."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    import anthropic
    from agent.copilot_agent import run_read_loop
    from agent.skills import SkillHub
    from agent.twak_cli import TwakCli

    client = anthropic.Anthropic(api_key=api_key)
    return run_read_loop(
        question,
        twak=TwakCli(),
        skills=SkillHub(),
        bridge=get_loop().bridge,
        client=client,
    )


@app.post("/copilot")
def copilot(body: dict) -> dict:
    """Grounded Q&A over the Second Brain. POST {"question": "..."}.
    Falls back to live-read tool-loop when SECOND_BRAIN=0 and API key present,
    then to the narrator."""
    question = str(body.get("question", ""))
    sb = _second_brain()
    if sb is None:
        loop_res = _copilot_read_loop(question)
        if loop_res is not None:
            loop_res["action"] = _extract_action(question, loop_res["answer"])
            return loop_res
        answer = _copilot_fallback(question)
        action = _extract_action(question, answer)
        return {"answer": answer, "grounded": False, "sources": [], "action": action}
    res = sb.copilot().ask(question)
    action = _extract_action(question, res.get("answer", ""))
    res["action"] = action
    return res


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
    returns - a failed advisory run must never surface as a 5xx to Trigger.dev
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
    except Exception as exc:  # noqa: BLE001 - advisory path; never raise to Trigger.dev
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


@app.post("/dreamer")
def dreamer() -> dict:
    """Run one Dreamer nightly consolidation: dedupe reflections, score forecast
    calibration, age stale research, write nightly digest."""
    sb = _second_brain()
    if sb is None:
        return {"ok": False, "reason": "Second Brain disabled or offline."}
    try:
        from agent.secondbrain.dreamer import Dreamer
        d = Dreamer(vector=sb.vector, llm=sb.llm, bridge=get_loop().bridge)
        res = d.run()
        return {
            "ok": True,
            "reflections_checked": res.reflections_checked,
            "reflections_deduped": res.reflections_deduped,
            "research_aged": res.research_aged,
            "forecast_summary": res.forecast_summary,
            "nightly_digest_id": res.nightly_digest_id,
            "errors": res.errors,
        }
    except Exception as e:  # noqa: BLE001 - dreamer must never break the server
        return {"ok": False, "reason": str(e)}


@app.get("/telemetry")
def telemetry() -> dict:
    """LLM cost telemetry: tokens, cost, cache-hit rate, $ saved vs naive Opus."""
    sb = _second_brain()
    if sb is None:
        return {"enabled": False}
    return {"enabled": True, **sb.telemetry.snapshot()}


# ── Track-2 CMC Skill endpoint ────────────────────────────────────────────────

@app.post("/skill/signal_score")
def skill_signal_score(body: dict) -> dict:
    """Track-2 CMC Skill - multi-signal score for a BSC-eligible token.

    POST {"symbol": "ETH", "lookback_bars": 60}
    Returns structured score: regime, momentum/derivatives/sentiment/flow scores,
    composite, verdict, signal_strength. Described in agent/skills/skill_manifest.json.
    """
    symbol = str(body.get("symbol", "ETH"))
    lookback_bars = int(body.get("lookback_bars", 60))
    try:
        from agent.skills.track2 import SignalScoreSkill
        return SignalScoreSkill().compute(symbol, lookback_bars).as_dict()
    except Exception as exc:  # noqa: BLE001
        return {"symbol": symbol, "error": str(exc), "verdict": "hold",
                "signal_strength": "weak", "bars_used": 0}


@app.post("/skill/thesis_check")
def skill_thesis_check(body: dict) -> dict:
    """CMC Skill - falsification-as-a-service over the thesis ledger.

    POST {"idea_text": "momentum works in uptrends"}
    Returns {status, verdict, oos_objective, deflated_sharpe, source, matched_claim}.
    Described in agent/skills/thesis_check_manifest.json.
    """
    idea_text = str(body.get("idea_text", ""))
    try:
        from agent.skills.thesis_check import ThesisCheckSkill
        return ThesisCheckSkill().compute(idea_text)
    except Exception as exc:  # noqa: BLE001
        return {"status": "untested", "verdict": "unknown", "error": str(exc)}


@app.get("/skill/manifest")
def skill_manifest() -> dict:
    """Return the CMC Skills Marketplace manifest for the Track-2 strategy skill."""
    import json
    from pathlib import Path
    manifest_path = Path(__file__).parent / "skills" / "skill_manifest.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ── TWAK read endpoints (no signing) ─────────────────────────────────────────

def _get_twak() -> "TwakCli":
    from agent.twak_cli import TwakCli
    return TwakCli()


@app.get("/twak/portfolio")
def twak_portfolio() -> dict:
    """Full multi-chain portfolio from TWAK wallet portfolio command."""
    try:
        return {"ok": True, "data": _get_twak().portfolio()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "data": {}}


@app.get("/twak/risk")
def twak_risk(asset_id: str) -> dict:
    """Token rug-risk check. GET /twak/risk?asset_id=c60"""
    try:
        return {"ok": True, "data": _get_twak().risk(asset_id)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "data": {}}


@app.get("/twak/price")
def twak_price(token: str, chain: str = "bsc") -> dict:
    """Spot price for a token. GET /twak/price?token=ETH"""
    try:
        return {"ok": True, "data": _get_twak().price(token, chain)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "data": {}}


@app.get("/twak/trending")
def twak_trending(category: str = "bnb", limit: int = 10) -> dict:
    """Trending tokens on BNB. GET /twak/trending?category=bnb"""
    try:
        return {"ok": True, "data": _get_twak().trending(category=category, limit=limit)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "data": []}


@app.post("/twak/drain")
def twak_drain(request: Request) -> dict:
    """Pull next queued agent_command and execute it. Called by the command worker."""
    _require_api_token(request)
    from agent.command_worker import run_one_command
    try:
        result = run_one_command(get_loop().bridge)
        return {"ok": True, "ran": result}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "ran": False}


@app.get("/skill/manifests")
def skill_manifests() -> list:
    """Return all published CMC Skills Marketplace manifests (Track-2 score + thesis-check)."""
    import json
    from pathlib import Path
    out = []
    skills_dir = Path(__file__).parent / "skills"
    for name in ("skill_manifest.json", "thesis_check_manifest.json"):
        try:
            out.append(json.loads((skills_dir / name).read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return out
