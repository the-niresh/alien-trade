"""
ConvexBridge — the agent's link to the Convex state/audit/UI bus.

Talks to Convex via its HTTP API (POST {url}/api/query|mutation). Convex is the
single source of live state: the kill switch lives here, and every decision /
trade / ledger / risk-state / audit row is written here ("if it's not in Convex,
it didn't happen").

Degrades gracefully: with no CONVEX_URL the bridge runs offline — it logs each
write to stdout and keeps them in-memory — so the loop, tests, and a laptop demo
all work without a network. Network errors never crash a cycle; they're logged
and the cycle continues (the kill-switch read fails *safe* = not halted only when
explicitly offline; a live-but-erroring Convex is treated as halted-unknown=False
but audited).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class ConvexBridge:
    url: str = ""
    timeout: float = 15.0
    _http: Optional[httpx.Client] = field(default=None, init=False, repr=False)
    _offline_log: list[dict] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.enabled:
            self._http = httpx.Client(base_url=self.url.rstrip("/"), timeout=self.timeout)

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    # ── low-level HTTP ─────────────────────────────────────────────────────────

    def _call(self, kind: str, path: str, args: dict) -> Any:
        """kind = 'query' | 'mutation'. Returns the function's value or None."""
        if not self.enabled:
            self._offline_log.append({"kind": kind, "path": path, "args": args})
            return None
        try:
            r = self._http.post(f"/api/{kind}", json={"path": path, "args": args, "format": "json"})
            r.raise_for_status()
            body = r.json()
            if body.get("status") == "success":
                return body.get("value")
            print(f"[convex] {path} error: {body.get('errorMessage')}")
            return None
        except Exception as e:  # noqa: BLE001 — Convex must never crash a trading cycle
            print(f"[convex] {path} call failed: {e}")
            return None

    # ── reads ──────────────────────────────────────────────────────────────────

    def is_halted(self) -> bool:
        """Kill-switch read. Offline → False (paper/tests run free)."""
        if not self.enabled:
            return False
        val = self._call("query", "config:isHalted", {})
        return bool(val) if val is not None else False

    def get_config(self) -> Optional[dict]:
        return self._call("query", "config:get", {})

    def get_equity_floor(self) -> float:
        """Read the equity floor from Convex config. 0 = disabled. Offline → 0."""
        if not self.enabled:
            return 0.0
        cfg = self.get_config()
        return float(cfg.get("equity_floor") or 0) if cfg else 0.0

    def get_token_allowlist(self) -> list[str]:
        """Read the eligible-token allowlist from Convex config.
        Falls back to the core/risk default when offline or unseeded."""
        if not self.enabled:
            from risk.guardrails import TOKEN_ALLOWLIST
            return sorted(TOKEN_ALLOWLIST)
        cfg = self.get_config()
        if cfg and cfg.get("token_allowlist"):
            return list(cfg["token_allowlist"])
        from risk.guardrails import TOKEN_ALLOWLIST
        return sorted(TOKEN_ALLOWLIST)

    def get_trading_mode(self) -> Optional[str]:
        """Live trading-mode read (the UI toggle writes config.trading_mode).
        Offline or unseeded → None, so the loop keeps the mode it booted with."""
        if not self.enabled:
            return None
        cfg = self.get_config()
        return cfg.get("trading_mode") if cfg else None

    def get_autopilot_config(self) -> Optional[dict]:
        """Live autopilot overrides set from the cockpit (config.autopilot).
        Offline / unseeded → None, so the loop keeps its env-built config."""
        if not self.enabled:
            return None
        cfg = self.get_config()
        return cfg.get("autopilot") if cfg else None

    def get_strategy_choice(self) -> Optional[str]:
        """Live strategy pick from the cockpit (config.strategy_name).
        Offline / unseeded → None, so the loop keeps its boot strategy."""
        if not self.enabled:
            return None
        cfg = self.get_config()
        return cfg.get("strategy_name") if cfg else None

    def set_autopilot_state(self, state_row: dict) -> None:
        """Persist the autopilot ratchet (protected_floor etc.) so a restart keeps
        the banked floor. Best-effort: offline or before the mutation exists → no-op."""
        if not self.enabled:
            return
        try:
            self._call("mutation", "config:setAutopilotState", {"state": state_row})
        except Exception:  # noqa: BLE001 — persistence is best-effort, never fatal
            pass

    def get_autopilot_state(self) -> Optional[dict]:
        """Read the persisted autopilot ratchet on restart. None → start fresh."""
        if not self.enabled:
            return None
        cfg = self.get_config()
        return cfg.get("autopilot_state") if cfg else None

    def recent_trades(self, limit: int = 200) -> list[dict]:
        """Trades newest-first (for crash recovery, reverse to replay)."""
        return self._call("query", "trades:recent", {"limit": limit}) or []

    def recent_decisions(self, limit: int = 200) -> list[dict]:
        return self._call("query", "decisions:recent", {"limit": limit}) or []

    def latest_ledger(self) -> Optional[dict]:
        return self._call("query", "ledger:latest", {})

    def set_halted(self, halted: bool) -> None:
        """Flip the kill switch (used by the API /halt and /resume routes)."""
        self._call("mutation", "config:setHalted", {"halted": halted})

    # ── writes ─────────────────────────────────────────────────────────────────

    def ensure_config(self, trading_mode: str = "paper") -> None:
        self._call("mutation", "config:ensure", {"trading_mode": trading_mode})

    def record_decision(
        self,
        *,
        cycle_id: str,
        symbol: str,
        timestamp_ms: int,
        regime: str,
        signals: dict,
        target_position_usd: float,
        risk_verdict: str,
        risk_reason: str,
        final_size_usd: float,
        trade_id: Optional[str] = None,
        setup_key: Optional[str] = None,
    ) -> Optional[str]:
        args: dict = {
            "cycle_id": cycle_id,
            "symbol": symbol,
            "timestamp_ms": timestamp_ms,
            "regime": regime,
            "signals": signals,
            "target_position_usd": target_position_usd,
            "risk_verdict": risk_verdict,
            "risk_reason": risk_reason,
            "final_size_usd": final_size_usd,
        }
        if trade_id:
            args["trade_id"] = trade_id
        if setup_key:
            args["setup_key"] = setup_key
        return self._call("mutation", "decisions:record", args)

    def get_feedback(self, setup_key: str) -> list[dict]:
        """Human good/bad labels for a setup_key (the feedback gate reads this before
        trading the setup). Offline → [] so there is no behaviour change (parity)."""
        if not self.enabled:
            return []
        return self._call("query", "feedback:bySetup", {"setup_key": setup_key}) or []

    def record_feedback(self, *, cycle_id: str, setup_key: str, symbol: str,
                        label: str, note: Optional[str] = None) -> Optional[str]:
        """Write a human label (cockpit normally writes this directly; exposed for
        the agent/CLI too)."""
        args = {"cycle_id": cycle_id, "setup_key": setup_key,
                "symbol": symbol, "label": label}
        if note:
            args["note"] = note
        return self._call("mutation", "feedback:record", args)

    def record_trade(
        self,
        *,
        symbol: str,
        side: str,
        size_usd: float,
        fill_price: float,
        fee_usd: float,
        gas_usd: float,
        slippage_usd: float,
        mode: str,
        tx_hash: Optional[str] = None,
        timestamp_ms: Optional[int] = None,
    ) -> Optional[str]:
        args: dict = {
            "symbol": symbol, "side": side, "size_usd": size_usd,
            "fill_price": fill_price, "fee_usd": fee_usd, "gas_usd": gas_usd,
            "slippage_usd": slippage_usd, "mode": mode,
        }
        if tx_hash:
            args["tx_hash"] = tx_hash
        if timestamp_ms is not None:
            args["timestamp_ms"] = timestamp_ms
        return self._call("mutation", "trades:record", args)

    def append_ledger(self, **kw) -> Optional[str]:
        return self._call("mutation", "ledger:append", kw)

    def record_reflection(self, **kw) -> Optional[str]:
        """Hermes post-trade reflection row (idempotent on trade_id+cycle_id)."""
        return self._call("mutation", "reflections:record", kw)

    def recent_reflections(self, limit: int = 50) -> list[dict]:
        return self._call("query", "reflections:recent", {"limit": limit}) or []

    def soft_delete_reflection(self, convex_id: str) -> None:
        """Dreamer: mark a duplicate reflection as stale (soft-delete)."""
        self._call("mutation", "reflections:softDelete", {"id": convex_id})

    def record_forecast_calibration(
        self,
        *,
        cycle_id: str,
        symbol: str,
        forecast_confidence: float,
        regime: str,
        realized_pnl: float,
        ts_ms: int,
    ) -> Optional[str]:
        return self._call("mutation", "forecastCalibration:record", {
            "cycle_id": cycle_id, "symbol": symbol,
            "forecast_confidence": forecast_confidence,
            "regime": regime, "realized_pnl": realized_pnl, "ts_ms": ts_ms,
        })

    def recent_forecast_calibration(self, symbol: Optional[str] = None,
                                    limit: int = 200) -> list[dict]:
        args: dict = {"limit": limit}
        if symbol:
            args["symbol"] = symbol
        return self._call("query", "forecastCalibration:recent", args) or []

    def get_forecast_calibration_summary(self, symbol: Optional[str] = None) -> dict:
        args: dict = {}
        if symbol:
            args["symbol"] = symbol
        return self._call("query", "forecastCalibration:getSummary", args) or {}

    def update_risk_state(self, **kw) -> None:
        self._call("mutation", "riskState:update", kw)

    def update_scorecard(self, **kw) -> None:
        """Upsert the live scorecard singleton (core/scorecard.py as_convex_row)."""
        self._call("mutation", "scorecard:update", kw)

    # ── agent team: activity channel + control ─────────────────────────────────

    def emit_event(self, event) -> Optional[str]:
        """Append one AgentEvent to the Activity Channel (glass cockpit). Takes a
        contracts.AgentEvent; offline → logged like any other write."""
        return self._call("mutation", "agentEvents:append", event.as_row())

    def recent_events(self, limit: int = 50) -> list[dict]:
        return self._call("query", "agentEvents:recent", {"limit": limit}) or []

    def get_agent_control(self):
        """Read the user control doc as a contracts.AgentControl. Offline / unseeded
        → defaults (nothing paused) so the supervisor never blocks on a missing doc."""
        from agent.graph.contracts import AgentControl
        if not self.enabled:
            return AgentControl()
        doc = self._call("query", "agentControl:get", {})
        if not doc:
            return AgentControl()
        keep = {"agents_paused", "paused_agents", "trading_halted",
                "stop_response_id", "updated_by", "ts_ms", "key"}
        return AgentControl(**{k: v for k, v in doc.items() if k in keep})

    def set_agent_paused(self, paused: bool) -> None:
        """Toggle advisory-agents pause via agentControl:set."""
        if not self.enabled:
            return
        self._call("mutation", "agentControl:set", {"agents_paused": paused})

    def get_sentiment_state(self, symbol: str) -> Optional[dict]:
        """Read the latest SentimentReading for a symbol. Offline / missing → None."""
        if not self.enabled:
            return None
        return self._call("query", "social:getSentiment", {"symbol": symbol})

    def set_sentiment_state(self, reading) -> None:
        """Write a SentimentReading row (upsert by symbol). Takes a social.schema.SentimentReading."""
        self._call("mutation", "social:setSentiment", reading.as_row())

    def record_social_posts(self, posts: list) -> int:
        """Batch-insert normalised SocialPost rows (deduped by post_id). Returns insert count."""
        rows = [{"post_id": p.id, "platform": p.platform, "author": p.author,
                 "text": p.text[:500], "url": p.url, "ts_ms": p.ts_ms,
                 "symbols": p.symbols} for p in posts]
        return self._call("mutation", "social:writePosts", {"posts": rows}) or 0

    def get_forecast_state(self, symbol: str) -> Optional[dict]:
        """Read the latest ForecastState for a symbol. Offline / missing → None."""
        if not self.enabled:
            return None
        return self._call("query", "forecastState:get", {"symbol": symbol})

    def set_forecast_state(self, forecast) -> None:
        """Write a ForecastState row (upsert by symbol). Takes a contracts.ForecastState."""
        self._call("mutation", "forecastState:set", forecast.as_row())

    def audit(self, event_type: str, cycle_id: Optional[str], payload: dict, severity: str = "info") -> None:
        self._call("mutation", "audit:log", {
            "event_type": event_type,
            "cycle_id": cycle_id,
            "payload": json.dumps(payload, default=str),
            "severity": severity,
        })
