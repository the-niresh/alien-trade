"""
DecisionLoop — the live trading heart.

Per cycle, identical in shape to one bar of the backtest:
    feed → kill-switch check → SAME /core risk-wrapped strategy → mistake-avoidance
    → executor (simulate→sign→send→confirm) → reconcile ledger → write Convex rows.

The strategy callable IS the sim's strategy (RiskEngine-wrapped core). Because
the loop hands it the same point-in-time history the sim does, the live decision
is provably the sim's decision — that's the sim/live parity invariant.

Every cycle writes exactly one decision row (idempotent on cycle_id) so the audit
trail is complete: "if it's not in Convex, it didn't happen."
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from backtest.engine import Bar, Fill, Order, StrategyFn, Trade
from risk.guardrails import check_equity_floor
from backtest.regime import detect_regime
from scorecard import OperationalStats, RuleAdherence, compute_scorecard
from strategy.combined import StrategyParams, score_breakdown

from agent.brain import AllowAll, MistakeAvoidance
from agent.convex_bridge import ConvexBridge
from agent.executor import DUPLICATE, FAILED, REJECTED, Executor, ExecutionReport
from agent.ledger import LedgerState

if TYPE_CHECKING:
    from agent.notify import TelegramNotifier
    from risk.autopilot import AutopilotConfig


@dataclass
class CycleResult:
    cycle_id: str
    timestamp_ms: int
    halted: bool
    regime: str
    verdict: str                       # allow | reduce | block
    reason: str
    order: Optional[Order]
    execution: Optional[ExecutionReport]
    equity: float
    drawdown_pct: float
    breakdown: dict = field(default_factory=dict)


class DecisionLoop:
    def __init__(
        self,
        *,
        feed,
        strategy: StrategyFn,
        executor: Executor,
        bridge: ConvexBridge,
        params: StrategyParams,
        symbol: str = "BNB",
        mode: str = "paper",
        initial_capital: float = 10_000.0,
        base_position_usd: float = 1_000.0,
        max_consecutive_losses: int = 5,
        mistake_avoidance: Optional[MistakeAvoidance] = None,
        reflection_writer: Optional[object] = None,
        executor_factory: Optional[Callable[[str], Executor]] = None,
        enforce_activity_floor: bool = False,
        activity_deadline_hour: int = 23,
        activity_trade_usd: float = 15.0,
        notifier: Optional["TelegramNotifier"] = None,
        autopilot_config: Optional["AutopilotConfig"] = None,
        kol_enabled: bool = False,
        kol_min_conf: float = 0.5,
        symbol_scanner=None,
    ):
        self.feed = feed
        self.strategy = strategy            # the SAME risk-wrapped /core strategy
        self.executor = executor
        self.bridge = bridge
        self.params = params
        self.symbol = symbol
        self._scanner = symbol_scanner
        self.mode = mode
        self.notifier = notifier
        # Live mode toggle (the UI writes config.trading_mode). When a factory is
        # supplied, the loop swaps its executor to match the toggle each cycle —
        # but only while FLAT (an open position must close under the mode it was
        # opened in). None → mode is fixed at the boot value (no live switching).
        self.executor_factory = executor_factory
        self._pending_mode: Optional[str] = None   # desired mode deferred until flat
        self._exposure_epsilon = 1e-6
        self.base_position_usd = base_position_usd
        self.max_consecutive_losses = max_consecutive_losses
        self.brain = mistake_avoidance or AllowAll()
        # Hermes write-side (post-trade reflection). None = disabled (Step 5 default).
        self.reflection_writer = reflection_writer
        self.ledger = LedgerState(initial_capital=initial_capital)

        # ── Live scorecard accumulators (docs/GOAL.md) ──────────────────────
        # The same shapes core/scorecard.py scores in sim, built up cycle-by-cycle
        # from real fills so the live objective is computed identically. Trades are
        # paired exactly as backtest.engine does (single entry fill → close on sell),
        # which holds because live fills reproduce the sim's fills (parity invariant).
        self._initial_capital = initial_capital
        self._equity_curve: list[float] = []
        self._equity_ts: list[int] = []
        self._exposure_curve: list[float] = []
        self._fills: list[Fill] = []
        self._trades: list[Trade] = []
        self._entry_fill: Optional[Fill] = None
        self._entry_forecast_confidence: float = 1.0  # snapshot at buy fill for calibration
        # Passthrough facts the curve can't reveal (autonomy + rule adherence).
        self._cycles_total = 0
        self._blocks_fired = 0
        self._chain_cycle_n = 0   # cycles since last setup_scorer chain fire
        self._kill_switch_activations = 0
        self._circuit_breaker_activations = 0
        self._peak_exposure_pct = 0.0
        self._was_halted = False
        self._was_circuit = False

        # ── Activity floor: minimum-trades-per-day mode ─────────────────────
        # Some venues and mandates require at least one trade per calendar day. When
        # enabled, the loop forces ONE minimal swap late in the day if nothing has
        # traded yet.
        #
        # OFF by default, and it should stay off unless an external rule demands it:
        # a forced trade has no signal behind it, so it costs gas and slippage for
        # no expected edge, and it makes a live run diverge from the backtest (which
        # has no such forced trade). Enabling it breaks sim/live parity by design.
        self.enforce_activity_floor = enforce_activity_floor
        self.activity_deadline_hour = activity_deadline_hour
        self.activity_trade_usd = activity_trade_usd
        self.kol_enabled = kol_enabled
        self._kol_min_conf = kol_min_conf
        self._activity_day = -1
        self._trades_today = 0

        # ── Telegram alert state ────────────────────────────────────────────
        # Distinguish equity-floor-triggered halts from user-triggered ones so
        # we don't double-fire (floor sends its own specific message).
        self._halted_by_floor: bool = False
        # Daily PnL summary: snapshot equity at day-start; send on rollover.
        self._daily_pnl_start: float = initial_capital
        self._daily_max_dd: float = 0.0

        # ── 8.11 Degraded-mode observability ────────────────────────────────
        # Track which sources are currently stale so we emit on each transition
        # (stale → fresh, fresh → stale) rather than every cycle.
        self._stale_sources: set = set()

        # ── Autopilot capital manager (profit-lock + ratchet + trailing) ────
        # Live-only overlay (default None → disabled → sim/paper parity holds).
        # State (the protected-floor ratchet) is rebuilt from Convex on restart.
        from risk.autopilot import AutopilotState
        self._autopilot_config = autopilot_config
        self._autopilot_state = AutopilotState()
        self._block_entry = False           # set by the recycle gate / cooldown
        self._current_setup_key = ""        # regime+dominant-signal, for human feedback
        # Live USDT balance cache — updated in _finalise, used in _cap_to_deployable.
        # Starts at inf so the first cycle isn't blocked before we've fetched the balance.
        self._cached_usdt_balance: float = float("inf")
        self._cached_eth_balance: float = 0.0
        # Consecutive execution failures → escalating Telegram alert after threshold.
        self._consecutive_exec_failures: int = 0
        self._EXEC_FAIL_ALERT_THRESHOLD: int = 3   # alert after 3 straight FAILED cycles
        self._wallet_mismatch_alerted: bool = False  # fire once per session, not every cycle
        self._position_reconciled: bool = False      # fire once per session after forced close
        # Time-based sustained-failure watchdog.
        # Tracks when the first FAILED execution started in the current streak.
        # Warn at 2h, auto-halt at 4h. Cleared on any confirmed fill.
        self._first_exec_failure_ms: Optional[int] = None
        self._sustained_warn_sent: bool = False
        self._SUSTAINED_WARN_MS: int = 2 * 3_600_000   # 2 hours
        self._SUSTAINED_HALT_MS: int = 4 * 3_600_000   # 4 hours
        if autopilot_config is not None and autopilot_config.enabled:
            try:
                saved = self.bridge.get_autopilot_state()
                if saved:
                    self._autopilot_state = AutopilotState(
                        protected_floor=float(saved.get("protected_floor", 0.0)),
                        cycle_start_equity=float(saved.get("cycle_start_equity", 0.0)),
                        peak_equity=float(saved.get("peak_equity", 0.0)),
                        day_start_equity=float(saved.get("day_start_equity", 0.0)),
                        day_key=str(saved.get("day_key", "")),
                        halted_for_day=bool(saved.get("halted_for_day", False)),
                        cooldown_until_ms=int(saved.get("cooldown_until_ms", 0)),
                    )
            except Exception:  # noqa: BLE001 — fresh state is a safe fallback
                pass

    # ── notify helper (Telegram 8.9) ─────────────────────────────────────────

    def _notify(self, text: str) -> None:
        if self.notifier is not None:
            self.notifier.send(text)

    def _notify_with_approval(
        self, text: str,
        on_approve=None, on_reject=None,
        approve_label: str = "Approve",
        reject_label: str = "Reject",
        timeout_s: float = 300.0,
    ) -> None:
        """Send with inline buttons if the notifier supports it, else plain send."""
        if self.notifier is None:
            return
        if hasattr(self.notifier, "send_approval"):
            self.notifier.send_approval(
                text, on_approve=on_approve, on_reject=on_reject,
                approve_label=approve_label, reject_label=reject_label,
                timeout_s=timeout_s,
            )
        else:
            self.notifier.send(text)

    # ── cross-sectional rotation ─────────────────────────────────────────────

    def _switch_symbol(self, new_symbol: str) -> None:
        """Rotate to a new symbol.  Only safe to call when FLAT (no open position)."""
        old = self.symbol
        self.symbol = new_symbol
        interval = getattr(self.feed, "interval", "1h")
        history_bars = getattr(self.feed, "history_bars", 200)
        from agent.feed import BinanceLiveFeed
        self.feed = BinanceLiveFeed(new_symbol, interval=interval, history_bars=history_bars)
        from agent.observability import jlog
        jlog("symbol_switch", old_symbol=old, new_symbol=new_symbol)
        if self.notifier:
            self._notify(f"Rotating {old} → {new_symbol} (scanner)")

    # ── one cycle ────────────────────────────────────────────────────────────

    def run_cycle(self, history: list[Bar]) -> CycleResult:
        bar = history[-1]
        cycle_id = f"{self.symbol}-{bar.timestamp}"
        self.ledger.roll_day(bar.timestamp, bar.open)

        # Reset the per-day trade counter on a calendar-day rollover (activity floor).
        day = bar.timestamp // 86_400_000
        if day != self._activity_day:
            if self._activity_day != -1:
                self._send_daily_summary(bar)
            self._activity_day = day
            self._trades_today = 0
            self._daily_pnl_start = self.ledger.mark(bar.open)
            self._daily_max_dd = 0.0

        # ── Sustained-failure watchdog: halt after 4h of unbroken FAILED execs ─
        self._check_sustained_failure(bar, cycle_id)

        # ── Live trading-mode toggle: align the executor with the UI ─────────
        self._sync_trading_mode(bar, cycle_id)
        # ── Live autopilot config: pick up cockpit changes (offline → keep env) ─
        self._sync_autopilot_config()

        # Social S3 bridge: inject live sentiment into the last bar (point-in-time,
        # live-only overlay — offline/sim bridge returns None → history unchanged).
        history = self._inject_sentiment(history, bar)
        regime = detect_regime(history)
        breakdown = score_breakdown(history, self.params)
        signals = _signals_obj(breakdown)
        target_usd = breakdown["target"] * self.base_position_usd
        # Setup key for the human-feedback loop (regime + dominant signal).
        from risk.feedback import setup_key as _setup_key
        self._current_setup_key = _setup_key(regime.value, signals)

        # 8.11 — emit RiskGuard observation when advisory signals go stale
        self._check_staleness(bar, cycle_id)

        # ── Equity floor: halt if capital fell below user-set minimum ───────
        if self._check_equity_floor(bar, cycle_id):
            return self._finalise(
                cycle_id, bar, regime.value, "block", "equity floor halt",
                None, None, 0.0, 0.0, None, {}, {}, halted=True,
            )

        # ── Kill switch: halt within one cycle ──────────────────────────────
        if self.bridge.is_halted():
            self.bridge.audit("kill_switch", cycle_id,
                              {"symbol": self.symbol, "regime": regime.value}, "warn")
            return self._finalise(
                cycle_id, bar, regime.value, "block", "kill switch active",
                None, None, target_usd, 0.0, None, breakdown, signals, halted=True,
            )

        # ── Autopilot capital manager: bank / trail-exit / halt-for-day ─────
        # Runs before the strategy so a profit-lock or daily target can pre-empt a
        # fresh entry. Returns a finalised result when it intervened this cycle;
        # otherwise it only sets self._block_entry (recycle gate / cooldown).
        ap_intervention = self._apply_autopilot(bar, cycle_id, regime.value)
        if ap_intervention is not None:
            return ap_intervention

        # ── KOL auto-trade overlay (live-only; flat→open / held→reduce) ──────
        kol_intervention = self._apply_kol_signal(bar, cycle_id)
        if kol_intervention is not None:
            return kol_intervention

        # ── Decision (same code as the sim) ─────────────────────────────────
        order = self.strategy(history)

        # ── Stop-loss telemetry: surface a forced ATR-stop exit on the channel ─
        stop_exit = getattr(self.strategy, "last_stop_exit", None)
        if stop_exit:
            try:
                from agent.graph.contracts import AgentEvent, KIND_CONTROL
                self.bridge.emit_event(AgentEvent(
                    agent="RiskGuard", kind=KIND_CONTROL,
                    headline=(f"STOP: {stop_exit['kind']} ATR stop hit "
                              f"@ ${stop_exit['price']:.2f} (stop ${stop_exit['stop']:.2f})"),
                    cycle_id=cycle_id, detail=stop_exit,
                ))
            except Exception:  # noqa: BLE001 — channel write must never crash the loop
                pass

        verdict, reason, execution, trade_id, final_size = "block", "no signal / risk veto", None, None, 0.0

        if order is not None and self._block_entry and order.side == "buy":
            # Recycle gate / cooldown: a fresh long is suppressed, but exits proceed.
            order = None
            verdict, reason = "block", "autopilot: recycle gate / cooldown — staying in cash"

        if order is not None:
            order = self._cap_to_deployable(order, bar, cycle_id)

        # ── Human-feedback gate: operator's good/bad marks on this setup ─────
        if order is not None and order.side == "buy":
            order, fb_block_reason = self._apply_feedback_gate(order, cycle_id)
            if order is None:
                verdict, reason = "block", fb_block_reason

        if order is not None:
            ma = self.brain.check(history, order, regime.value)
            if ma.block:
                verdict, reason = "block", f"mistake-avoidance: {ma.reason}"
                self.bridge.audit("risk_veto", cycle_id, {"reason": ma.reason}, "warn")
            else:
                exec_order = order
                # Hermes soft veto: shrink the order on a historically-bad setup.
                if ma.size_penalty > 0.0:
                    exec_order = Order(
                        side=order.side, size_usd=order.size_usd * (1.0 - ma.size_penalty),
                        symbol=order.symbol, timestamp=order.timestamp,
                    )
                    self.bridge.audit("risk_veto", cycle_id,
                                      {"reason": ma.reason, "size_penalty": ma.size_penalty}, "warn")
                # Option-B forecast bridge: Researcher confidence can only shrink size
                exec_order = self._apply_forecast(exec_order, bar, cycle_id)
                final_size = exec_order.size_usd
                execution = self.executor.execute(exec_order, bar, idempotency_key=cycle_id)
                verdict, reason, trade_id = self._handle_execution(
                    execution, bar, cycle_id, regime.value, breakdown)

        # ── Activity floor: guarantee >= 1 trade this calendar day ───────────
        self._maybe_compliance_trade(bar, cycle_id)

        # ── Deterministic watches: edge-fire alerts (no LLM unless one trips) ──
        self._check_watches(bar, regime.value, cycle_id)

        return self._finalise(
            cycle_id, bar, regime.value, verdict, reason, order, execution,
            target_usd, final_size, trade_id, breakdown, signals, halted=False,
        )

    # ── deterministic market/trade watches ───────────────────────────────────

    @staticmethod
    def _watch_base_symbol(symbol: str) -> str:
        """Normalize a trading symbol to its base token for price-watch matching
        (e.g. 'CAKEUSDT' → 'CAKE')."""
        s = symbol.upper()
        for quote in ("USDT", "BUSD", "USDC", "USD"):
            if s.endswith(quote) and len(s) > len(quote):
                return s[: -len(quote)]
        return s

    def _check_watches(self, bar: Bar, regime_value: str, cycle_id: str) -> None:
        """Evaluate active watches against a point-in-time snapshot. Pure predicate
        (no LLM); the one short explain call happens only on an actual fire. Wrapped
        so a watch bug can never crash the trade cycle (locked decision #6)."""
        try:
            watches = self.bridge.active_watches()
            if not watches:
                return
            from agent.watches import process_watches, FIRED

            base_sym = self._watch_base_symbol(self.symbol)
            # Latency upgrade: if an optional push feed is attached and fresh, use it;
            # otherwise fall back to this cycle's price. Default (no feed) = bar.close.
            price = bar.close
            stream = getattr(self, "price_stream", None)
            if stream is not None:
                fp = stream.cache.fresh_price(base_sym)
                if fp is not None:
                    price = fp

            snapshot = {
                "symbol": base_sym,
                "price": price,
                "regime": regime_value,
                "drawdown_pct": self.ledger.drawdown_pct(bar.close) * 100.0,
                "equity_usd": self.ledger.mark(bar.close),
            }

            def _state(watch_id: Any, new_state: str) -> None:
                fired_ms = int(bar.timestamp) if new_state == FIRED else None
                self.bridge.set_watch_state(watch_id, new_state, fired_ms)

            def _fire(watch: dict, res: dict) -> None:
                headline = res["headline"]
                try:
                    from agent.graph.contracts import AgentEvent, KIND_OBSERVATION
                    self.bridge.emit_event(AgentEvent(
                        agent="Watcher", kind=KIND_OBSERVATION,
                        headline=f"WATCH: {headline}", cycle_id=cycle_id, detail=res,
                    ))
                except Exception:  # noqa: BLE001 — channel write must not crash the cycle
                    pass
                why = self._explain_watch(headline)
                self._notify(f"🔔 {headline}" + (f"\n{why}" if why else ""))

            process_watches(watches, snapshot, fire_cb=_fire, state_cb=_state)
        except Exception:  # noqa: BLE001 — monitoring must never break trading
            pass

    def _explain_watch(self, headline: str) -> str:
        """One short, token-frugal 'why it matters' line. Runs only on a fire, only if
        an Anthropic client is wired; any failure degrades to no explanation."""
        client = getattr(self, "anthropic_client", None)
        if client is None:
            return ""
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=80,
                system=("You explain a market alert for a drawdown-first BSC spot trader in "
                        "ONE short sentence. No preamble."),
                messages=[{"role": "user",
                           "content": f"Alert: {headline}. Why does it matter, in one sentence?"}],
            )
            return "".join(getattr(b, "text", "") for b in resp.content
                           if getattr(b, "type", None) == "text").strip()
        except Exception:  # noqa: BLE001 — explanation is best-effort
            return ""

    # ── live mode toggle ─────────────────────────────────────────────────────

    def _sync_trading_mode(self, bar: Bar, cycle_id: str) -> None:
        """Read the UI's trading-mode toggle and swap the executor to match — but
        only while flat. Switching paper↔mainnet moves real funds, so a position
        opened under one mode must close under that same mode; while a position is
        open the switch is DEFERRED (audited once) and applied the first flat cycle.
        Offline / no factory / unseeded config → no-op (mode stays at boot value)."""
        if self.executor_factory is None:
            return
        desired = self.bridge.get_trading_mode()
        if not desired or desired == self.mode:
            self._pending_mode = None
            return

        open_exposure = self.ledger.open_exposure(bar.close)
        if open_exposure > self._exposure_epsilon:
            # Position open — defer. Audit only when the deferred target changes,
            # so a long-held position doesn't spam the audit log every cycle.
            if self._pending_mode != desired:
                self._pending_mode = desired
                self.bridge.audit("mode_switch_deferred", cycle_id, {
                    "from": self.mode, "to": desired,
                    "open_exposure_usd": round(open_exposure, 2),
                    "reason": "position open — switch applies once flat",
                }, "warn")
            return

        # Flat → safe to switch. Rebuild the executor for the new mode.
        try:
            new_executor = self.executor_factory(desired)
        except Exception as e:  # noqa: BLE001 — a bad rebuild must not crash the cycle
            self.bridge.audit("error", cycle_id, {
                "error": str(e), "error_type": type(e).__name__,
                "reason": f"executor rebuild for mode {desired!r} failed; staying on {self.mode!r}",
            }, "error")
            return
        previous = self.mode
        self.executor = new_executor
        self.mode = desired
        self._pending_mode = None
        self.bridge.audit("mode_switch", cycle_id,
                          {"from": previous, "to": desired}, "info")

    # ── equity floor guard ───────────────────────────────────────────────────────

    def _check_equity_floor(self, bar: Bar, cycle_id: str) -> bool:
        """Returns True (and sets config.halted) if equity hit the user-set floor.
        Emits an agent_events warn/halt row for the glass cockpit. Live-only overlay:
        floor=0 (default) is a no-op so sim/paper parity is preserved."""
        floor = self.bridge.get_equity_floor()
        if floor <= 0:
            return False
        equity = self.ledger.mark(bar.close)
        result = check_equity_floor(equity, floor)
        if not result.halt and not result.warn:
            return False
        severity = "warn"
        headline = (
            f"HALT: equity floor hit (${equity:.2f} <= ${floor:.2f})"
            if result.halt
            else f"WARNING: portfolio ${equity:.2f} approaching floor ${floor:.2f}"
        )
        self.bridge.audit(
            "equity_floor_halt" if result.halt else "equity_floor_warn",
            cycle_id, {"equity_usd": equity, "floor_usd": floor, "reason": result.reason},
            severity,
        )
        try:
            from agent.graph.contracts import AgentEvent, KIND_CONTROL
            self.bridge.emit_event(AgentEvent(
                agent="RiskGuard", kind=KIND_CONTROL, headline=headline,
                cycle_id=cycle_id,
                detail={"equity_usd": equity, "floor_usd": floor, "halt": result.halt},
            ))
        except Exception:  # noqa: BLE001 — channel write must never crash the loop
            pass
        if result.halt:
            def _resume_trading():
                self.bridge.set_halted(False)
            self._notify_with_approval(
                f"HALT: Equity floor hit (${equity:.2f} <= ${floor:.2f}).\n"
                f"Trading halted. Fund wallet or tap Resume.",
                on_approve=_resume_trading,
                on_reject=None,
                approve_label="Resume Trading",
                reject_label="Keep Halted",
            )
            self._halted_by_floor = True
            self.bridge.set_halted(True)
            return True
        # warn path — plain notification, no action buttons
        self._notify(
            f"WARNING: Portfolio ${equity:.2f} approaching floor ${floor:.2f}"
            f" — consider adding capital or tightening caps."
        )
        return False

    # ── sustained-failure watchdog ────────────────────────────────────────────

    def _check_sustained_failure(self, bar: Bar, cycle_id: str) -> None:
        """Warn at 2h and auto-halt at 4h if execution has been continuously
        failing (FAILED status, not regime blocks). Never raises — observability
        must not crash a cycle. No-op when no failure streak is active."""
        if self._first_exec_failure_ms is None:
            return
        elapsed_ms = bar.timestamp - self._first_exec_failure_ms
        if elapsed_ms < self._SUSTAINED_WARN_MS:
            return
        if not self._sustained_warn_sent:
            elapsed_h = elapsed_ms / 3_600_000
            self._notify(
                f"WARNING: swap execution has been failing for {elapsed_h:.1f}h.\n"
                f"All orders are BLOCKED until swaps succeed.\n"
                f"Check: wallet USDT balance, TWAK status, network.\n"
                f"Wallet manager will analyse and report shortly."
            )
            self._sustained_warn_sent = True
            # Trigger the wallet manager agent in background for diagnosis
            try:
                from agent.wallet_manager import run_wallet_check
                run_wallet_check(
                    bridge=self.bridge,
                    notifier=self.notifier,
                    symbol=self.symbol,
                    mode=self.mode,
                )
            except Exception:  # noqa: BLE001 — manager must never crash the loop
                pass
        if elapsed_ms >= self._SUSTAINED_HALT_MS:
            self._notify(
                f"AUTO-HALT: swap execution failed for "
                f"{elapsed_ms / 3_600_000:.1f}h — halting to prevent "
                f"further failed attempts. Resume from cockpit or Telegram."
            )
            self.bridge.set_halted(True)
            self.bridge.audit("sustained_failure_halt", cycle_id, {
                "elapsed_ms": elapsed_ms,
                "first_failure_ms": self._first_exec_failure_ms,
            }, "error")
            self._first_exec_failure_ms = None   # don't re-trigger every cycle after halt
            self._sustained_warn_sent = False

    # ── daily summary ─────────────────────────────────────────────────────────

    def _send_daily_summary(self, bar: Bar) -> None:
        """Fire end-of-day Telegram summary at calendar-day rollover."""
        try:
            import datetime
            equity = self.ledger.mark(bar.close)
            pnl = equity - self._daily_pnl_start
            pnl_sign = "+" if pnl >= 0 else ""
            date_str = datetime.datetime.utcfromtimestamp(
                self._activity_day * 86_400
            ).strftime("%Y-%m-%d")
            adherence = (
                1.0 - (self._blocks_fired / max(self._cycles_total, 1))
            )
            self._notify(
                f"Daily summary {date_str}\n"
                f"PnL: {pnl_sign}${pnl:.2f}  Equity: ${equity:.2f}\n"
                f"Max DD: {self._daily_max_dd:.2%}  Trades: {self._trades_today}\n"
                f"Rule adherence: {adherence:.1%}"
            )
        except Exception:  # noqa: BLE001 — summary must never crash the loop
            pass

    # ── activity floor ─────────────────────────────────────────────────────────

    def _maybe_compliance_trade(self, bar: Bar, cycle_id: str) -> None:
        """Force ONE minimal swap late in the day if nothing has traded yet, to
        satisfy a minimum-activity rule. Safe by construction: it TRIMS
        an open position when we hold one (a sell can never breach an exposure cap)
        and otherwise opens a tiny position. Never fires when disabled, when a trade
        already happened today, or before the deadline hour. Routed through the same
        executor as every other trade, so it's a real `twak swap` that counts."""
        if not self.enforce_activity_floor or self._trades_today > 0:
            return
        hour = (bar.timestamp // 3_600_000) % 24
        if hour < self.activity_deadline_hour:
            return   # still early in the day — give the strategy room to trade

        from risk.guardrails import check_guardrails, check_max_exposure, RiskConfig
        cfg = RiskConfig()

        # Allowlist gate FIRST — never fire a compliance swap on a non-eligible token
        # (e.g. BNB), which would be an unscored / ineligible trade. Applies to buys
        # AND sells: we should not be trading an off-allowlist symbol at all.
        if self.symbol not in cfg.token_allowlist:
            self.bridge.audit("activity_floor_blocked", cycle_id, {
                "reason": f"symbol {self.symbol!r} not in allowlist", "hour": hour,
            }, "warn")
            return

        price = bar.close
        held_usd = self.ledger.open_exposure(price)
        if held_usd > self.activity_trade_usd:
            side, size = "sell", self.activity_trade_usd      # trim — always safe
        elif held_usd > 0.0:
            side, size = "sell", held_usd                     # close the dust
        else:
            side, size = "buy", self.activity_trade_usd       # flat → open tiny
        if size <= 0.0:
            return

        # For the OPENING (buy) path, run the full guardrail chain — daily-loss kill
        # switch, circuit breaker, position/exposure caps — exactly like every other
        # trade. Sells only trim/close, which can't breach an exposure or loss cap.
        if side == "buy":
            equity = self.ledger.mark(price)
            daily_loss_usd = self.ledger.daily_loss_usd(price)
            daily_loss_pct = daily_loss_usd / max(equity, 1.0)
            gr = check_guardrails(symbol=self.symbol, size_usd=size,
                                  daily_loss_pct=daily_loss_pct,
                                  consecutive_losses=self.ledger.consecutive_losses,
                                  capital=equity, config=cfg)
            if not gr.allowed:
                self.bridge.audit("activity_floor_blocked", cycle_id, {
                    "reason": gr.reason, "hour": hour, "source": "guardrail",
                }, "warn")
                return
            ex = check_max_exposure(open_exposure_usd=held_usd, new_size_usd=size,
                                    equity=equity, config=cfg)
            if not ex.allowed:
                self.bridge.audit("activity_floor_blocked", cycle_id, {
                    "reason": ex.reason, "hour": hour, "source": "exposure",
                }, "warn")
                return

        order = Order(side=side, size_usd=size, symbol=self.symbol, timestamp=bar.timestamp)
        execution = self.executor.execute(order, bar, idempotency_key=f"{cycle_id}-activity")
        self.bridge.audit("activity_floor", cycle_id, {
            "side": side, "size_usd": round(size, 2), "hour": hour,
            "reason": "no trade yet today — forcing minimal compliance swap",
        }, "info")
        self._handle_execution(execution, bar, cycle_id)

    # ── social S3 bridge ─────────────────────────────────────────────────────

    def _inject_sentiment(self, history: list[Bar], bar: Bar) -> list[Bar]:
        """Read live sentiment_state from Convex and stamp it onto history[-1].
        Returns history unchanged when offline (sim parity: social_score stays 0.0).
        Any exception is swallowed — social is off the hot path."""
        try:
            ss = self.bridge.get_sentiment_state(self.symbol)
            if ss is None:
                return history
            score = float(ss.get("score", 0.0))
            if score == 0.0:
                return history
            import dataclasses
            patched = dataclasses.replace(history[-1], social_score=score)
            return list(history[:-1]) + [patched]
        except Exception:  # noqa: BLE001 — social is advisory; never crash a cycle
            return history

    # ── 8.11 degraded-mode observability ─────────────────────────────────────

    def _check_staleness(self, bar: Bar, cycle_id: str) -> None:
        """Emit a RiskGuard observation event each time an advisory signal goes stale
        or recovers. Staleness thresholds: forecast > 4h, sentiment > 2h.
        Never raises — observability must not crash a cycle."""
        now_ms = bar.timestamp
        stale_now: set = set()
        try:
            fs = self.bridge.get_forecast_state(self.symbol)
            if fs is not None:
                age_ms = now_ms - int(fs.get("ts_ms", now_ms))
                if age_ms > 4 * 3_600_000:
                    stale_now.add("forecast")
        except Exception:  # noqa: BLE001
            pass
        try:
            ss = self.bridge.get_sentiment_state(self.symbol)
            if ss is not None:
                age_ms = now_ms - int(ss.get("ts_ms", now_ms))
                if age_ms > 2 * 3_600_000:
                    stale_now.add("sentiment")
        except Exception:  # noqa: BLE001
            pass
        for src in stale_now - self._stale_sources:
            self._emit_staleness_event(src, bar, cycle_id, stale=True)
        for src in self._stale_sources - stale_now:
            self._emit_staleness_event(src, bar, cycle_id, stale=False)
        self._stale_sources = stale_now

    def _emit_staleness_event(self, source: str, bar: Bar, cycle_id: str,
                              stale: bool) -> None:
        stale_hours = 2 if source == "sentiment" else 4
        headline = (f"STALE: {source} signal not updated in >{stale_hours}h"
                    if stale else f"RECOVERED: {source} signal is fresh again")
        try:
            from agent.graph.contracts import AgentEvent, KIND_OBSERVATION
            self.bridge.emit_event(AgentEvent(
                agent="RiskGuard", kind=KIND_OBSERVATION, headline=headline,
                cycle_id=cycle_id, detail={"source": source, "stale": stale},
            ))
        except Exception:  # noqa: BLE001
            pass
        if stale:
            self._notify(headline)

    # ── forecast bridge ──────────────────────────────────────────────────────

    def _apply_forecast(self, exec_order: Order, bar: Bar, cycle_id: str) -> Order:
        """Read the latest Researcher forecast from Convex, apply decay + shrink-only
        multiply. A missing / stale / error forecast decays to NEUTRAL (1.0) — it
        can NEVER silently block a trade (Researcher is Tier-1; failure-matrix §9.3)."""
        from risk.forecast import NEUTRAL, apply_forecast_multiplier, decay_confidence
        try:
            fs = self.bridge.get_forecast_state(self.symbol)
            if fs is None:
                return exec_order
            raw_conf = float(fs.get("confidence", NEUTRAL))
            ts_ms = int(fs.get("ts_ms", bar.timestamp))
            ttl_ms = int(fs.get("ttl_ms", 6 * 3_600_000))
            age_ms = max(0, bar.timestamp - ts_ms)
            conf = decay_confidence(raw_conf, age_ms, ttl_ms)
            if conf >= NEUTRAL - 1e-9:
                return exec_order   # fast path: neutral → no-op
            new_size = apply_forecast_multiplier(exec_order.size_usd, conf)
            if new_size < exec_order.size_usd - 1e-6:
                self.bridge.audit("forecast_shrink", cycle_id, {
                    "confidence": round(conf, 4), "age_ms": age_ms,
                    "from_size": round(exec_order.size_usd, 2),
                    "to_size": round(new_size, 2),
                    "reason": fs.get("reason", ""),
                }, "info")
            return Order(side=exec_order.side, size_usd=new_size,
                         symbol=exec_order.symbol, timestamp=exec_order.timestamp)
        except Exception:  # noqa: BLE001 — Tier-1; must never crash a trading cycle
            return exec_order

    def _current_forecast_confidence(self) -> float:
        """Read the live forecast confidence (for calibration snapshot at entry).
        Returns NEUTRAL (1.0) on any error — never blocks a trade."""
        from risk.forecast import NEUTRAL
        try:
            fs = self.bridge.get_forecast_state(self.symbol)
            if fs is None:
                return NEUTRAL
            return float(fs.get("confidence", NEUTRAL))
        except Exception:  # noqa: BLE001
            return NEUTRAL

    def _record_forecast_calibration(self, cycle_id: str, bar, regime: str,
                                     realized_pnl: float) -> None:
        """Write a forecast_calibration row: entry-time confidence + realized PnL.
        Off the hot path — any failure is silently swallowed."""
        try:
            self.bridge.record_forecast_calibration(
                cycle_id=cycle_id, symbol=self.symbol,
                forecast_confidence=self._entry_forecast_confidence,
                regime=regime, realized_pnl=realized_pnl,
                ts_ms=bar.timestamp,
            )
        except Exception:  # noqa: BLE001 — calibration is observability
            pass

    # ── autopilot capital manager ────────────────────────────────────────────

    def _apply_autopilot(self, bar: Bar, cycle_id: str, regime: str):
        """Evaluate the autopilot each cycle. Returns a finalised CycleResult when it
        intervenes (BANK / TRAIL_EXIT flatten the position; HALT_DAY stops for the
        day); otherwise returns None and sets self._block_entry for the recycle gate.
        Disabled / offline → no-op (self._block_entry cleared) so parity holds."""
        cfg = self._autopilot_config
        if cfg is None or not cfg.enabled:
            self._block_entry = False
            return None
        from risk.autopilot import AutopilotAction, evaluate

        equity = self.ledger.mark(bar.close)
        open_exp = self.ledger.open_exposure(bar.close)
        in_position = open_exp > self._exposure_epsilon
        day_key = _day_key(bar.timestamp)
        last_loss = self.ledger.consecutive_losses > 0
        try:
            decision = evaluate(
                cfg, self._autopilot_state,
                equity=equity, in_position=in_position, regime=regime,
                forecast_confidence=self._current_forecast_confidence(),
                day_key=day_key, now_ms=bar.timestamp, last_close_was_loss=last_loss,
            )
        except Exception:  # noqa: BLE001 — autopilot must never crash a trading cycle
            self._block_entry = False
            return None

        self._autopilot_state = decision.state
        self._persist_autopilot_state()
        self._block_entry = decision.action is AutopilotAction.BLOCK_ENTRY

        if decision.action in (AutopilotAction.BANK, AutopilotAction.TRAIL_EXIT) and in_position:
            order = Order(side="sell", size_usd=open_exp, symbol=self.symbol,
                          timestamp=bar.timestamp)
            execution = self.executor.execute(order, bar, idempotency_key=f"{cycle_id}-autopilot")
            verdict, reason, trade_id = self._handle_execution(
                execution, bar, cycle_id, regime, None)
            self._emit_autopilot(decision, bar, cycle_id, equity)
            self.bridge.audit("autopilot", cycle_id, {
                "action": decision.action.value, "reason": decision.reason,
                "banked": round(decision.banked, 2),
                "protected_floor": round(self._autopilot_state.protected_floor, 2),
            }, "info")
            return self._finalise(
                cycle_id, bar, regime, "allow", f"autopilot: {decision.reason}",
                order, execution, 0.0, order.size_usd, trade_id, {}, {}, halted=False,
            )

        if decision.action is AutopilotAction.HALT_DAY:
            self._emit_autopilot(decision, bar, cycle_id, equity)
            self.bridge.audit("autopilot", cycle_id, {
                "action": "halt_day", "reason": decision.reason,
            }, "info")
            return self._finalise(
                cycle_id, bar, regime, "block", f"autopilot: {decision.reason}",
                None, None, 0.0, 0.0, None, {}, {}, halted=False,
            )
        return None

    # ── KOL auto-trade overlay (live-only; deterministic; risk-gated) ─────────

    def _apply_kol_signal(self, bar: "Bar", cycle_id: str):
        """When enabled, turn a high-conviction eligible KOL reading into a scored
        order — open_long while flat, reduce while held — gated by check_guardrails.
        Disabled/offline → None (sim parity). Never raises (Tier-1, off hot path)."""
        if not getattr(self, "kol_enabled", False):
            return None
        try:
            ss = self.bridge.get_sentiment_state(self.symbol)
            if not ss:
                return None
            from agent.social.schema import SentimentReading
            from agent.social.kol_intent import kol_intent
            from risk.guardrails import check_guardrails, check_max_exposure, RiskConfig

            reading = SentimentReading(
                symbol=self.symbol, score=float(ss.get("score", 0.0)),
                confidence=float(ss.get("confidence", 0.0)),
                n_posts=int(ss.get("n_posts", 0)), ts_ms=int(ss.get("ts_ms", bar.timestamp)),
            )
            held = self.ledger.open_exposure(bar.close) > 1e-6
            intent = kol_intent(reading, holds_symbol=held, min_conf=self._kol_min_conf)
            if intent.action == "none":
                return None

            from backtest.engine import Order
            cfg = RiskConfig()
            equity = self.ledger.mark(bar.close)
            if intent.action == "open_long":
                size = min(self.base_position_usd, cfg.max_trade_usd)
                daily_loss_usd = self.ledger.daily_loss_usd(bar.close)
                daily_loss_pct = daily_loss_usd / max(equity, 1.0)
                gr = check_guardrails(symbol=self.symbol, size_usd=size,
                                      daily_loss_pct=daily_loss_pct,
                                      consecutive_losses=self.ledger.consecutive_losses,
                                      capital=equity, config=cfg)
                if not gr.allowed:
                    self.bridge.audit("risk_veto", cycle_id,
                                      {"reason": gr.reason, "source": "kol"}, "warn")
                    return None
                ex = check_max_exposure(
                    open_exposure_usd=self.ledger.open_exposure(bar.close),
                    new_size_usd=size, equity=equity, config=cfg)
                if not ex.allowed:
                    self.bridge.audit("risk_veto", cycle_id,
                                      {"reason": ex.reason, "source": "kol"}, "warn")
                    return None
                order = Order(side="buy", size_usd=size, symbol=self.symbol, timestamp=bar.timestamp)
            else:  # reduce
                held_usd = self.ledger.open_exposure(bar.close)
                if held_usd <= 0.0:
                    return None
                order = Order(side="sell", size_usd=held_usd, symbol=self.symbol,
                              timestamp=bar.timestamp)

            execution = self.executor.execute(order, bar, idempotency_key=f"{cycle_id}-kol")
            verdict, reason, trade_id = self._handle_execution(
                execution, bar, cycle_id, "", None)
            try:
                from agent.graph.contracts import AgentEvent, KIND_ACTION
                self.bridge.emit_event(AgentEvent(
                    agent="Scout", kind=KIND_ACTION,
                    headline=(f"KOL {intent.action.upper()} {self.symbol}: {intent.reason} "
                              f"(conf {intent.confidence:.2f})"),
                    cycle_id=cycle_id,
                    detail={"action": intent.action, "symbol": self.symbol,
                            "score": reading.score, "confidence": reading.confidence},
                    refs=[execution.tx_hash] if execution.tx_hash else [],
                ))
            except Exception:  # noqa: BLE001
                pass
            return self._finalise(
                cycle_id, bar, "", verdict, f"kol: {intent.reason}", order, execution,
                0.0, order.size_usd, trade_id, {}, {}, halted=False)
        except Exception as e:  # noqa: BLE001 — Tier-1; must never crash a cycle
            try:
                self.bridge.audit("error", cycle_id,
                                  {"error": str(e), "source": "kol_overlay"}, "error")
            except Exception:  # noqa: BLE001
                pass
            return None

    def _sync_autopilot_config(self) -> None:
        """Pick up cockpit autopilot changes live (config.autopilot). Offline /
        unseeded → bridge returns None → keep the env-built config. Fail-safe:
        any parse error leaves the current config untouched."""
        try:
            raw = self.bridge.get_autopilot_config()
        except Exception:  # noqa: BLE001
            return
        if not raw:
            return
        try:
            from risk.autopilot import AutopilotConfig
            self._autopilot_config = AutopilotConfig(
                enabled=bool(raw.get("enabled", False)),
                profit_target_pct=raw.get("profit_target_pct"),
                profit_target_abs=raw.get("profit_target_abs"),
                protect_principal=bool(raw.get("protect_principal", True)),
                min_recycle_confidence=float(raw.get("min_recycle_confidence") or 0.0),
                recycle_blocked_regimes=tuple(raw.get("recycle_blocked_regimes") or ()),
                trailing_giveback_pct=raw.get("trailing_giveback_pct"),
                daily_profit_target_pct=raw.get("daily_profit_target_pct"),
                loss_cooldown_hours=float(raw.get("loss_cooldown_hours") or 0.0),
            )
        except Exception:  # noqa: BLE001 — a bad cockpit value must not crash the loop
            pass

    _MIN_TRADE_USD: float = 0.05   # below this, BSC DEX fees eat the trade

    def _cap_to_deployable(self, order: Order, bar: Bar, cycle_id: str) -> Optional[Order]:
        """Shrink a buy to the capital above the protected floor (capital ratchet) AND
        the live USDT balance. Banked gains are never re-risked. Sells pass through
        untouched. Returns None if there is no deployable capital left for a buy."""
        if order.side != "buy":
            return order

        size = order.size_usd

        # 1. Autopilot floor cap (paper-ledger equity above the protected floor)
        cfg = self._autopilot_config
        if cfg is not None and cfg.enabled:
            from risk.autopilot import deployable_capital
            cap = deployable_capital(self.ledger.mark(bar.close), self._autopilot_state)
            if cap <= self._exposure_epsilon:
                self.bridge.audit("autopilot", cycle_id, {
                    "action": "block_buy", "reason": "no capital above protected floor",
                    "protected_floor": round(self._autopilot_state.protected_floor, 2),
                }, "info")
                return None
            size = min(size, cap)

        # 2. Live wallet balance cap — auto-size to what USDT is actually available.
        #    Prevents silent TWAK failures when the static position size exceeds balance.
        usdt_avail = self._cached_usdt_balance
        if usdt_avail != float("inf"):          # inf = not yet fetched, skip cap
            spendable = usdt_avail * 0.95       # leave 5% buffer for price movement
            if spendable < self._MIN_TRADE_USD:
                self.bridge.audit("autopilot", cycle_id, {
                    "action": "block_buy",
                    "reason": f"insufficient USDT: ${usdt_avail:.4f} < min ${self._MIN_TRADE_USD}",
                    "usdt_balance": round(usdt_avail, 6),
                }, "warn")
                return None
            size = min(size, spendable)

        if size != order.size_usd:
            return Order(side="buy", size_usd=size, symbol=order.symbol,
                         timestamp=order.timestamp)
        return order

    def _apply_feedback_gate(self, order: Order, cycle_id: str):
        """Consult the operator's good/bad marks on this setup (human-in-the-loop).
        Returns (order, reason): a blocked setup → (None, reason); a net-bad setup →
        (shrunk order, ''); clear → (order, ''). Offline → no records → (order, '')
        so parity holds. Never raises."""
        try:
            from risk.feedback import evaluate_feedback
            records = self.bridge.get_feedback(self._current_setup_key)
            if not records:
                return order, ""
            fb = evaluate_feedback(records)
            if fb.block:
                self.bridge.audit("risk_veto", cycle_id, {
                    "reason": fb.reason, "source": "human", "setup": self._current_setup_key,
                }, "warn")
                return None, f"human feedback: {fb.reason}"
            if fb.size_penalty > 0.0:
                self.bridge.audit("risk_veto", cycle_id, {
                    "reason": fb.reason, "size_penalty": fb.size_penalty,
                    "source": "human", "setup": self._current_setup_key,
                }, "warn")
                return Order(side=order.side, size_usd=order.size_usd * (1.0 - fb.size_penalty),
                             symbol=order.symbol, timestamp=order.timestamp), ""
            return order, ""
        except Exception:  # noqa: BLE001 — feedback is advisory; never crash a cycle
            return order, ""

    def _persist_autopilot_state(self) -> None:
        try:
            s = self._autopilot_state
            self.bridge.set_autopilot_state({
                "protected_floor": s.protected_floor,
                "cycle_start_equity": s.cycle_start_equity,
                "peak_equity": s.peak_equity,
                "day_start_equity": s.day_start_equity,
                "day_key": s.day_key,
                "halted_for_day": s.halted_for_day,
                "cooldown_until_ms": s.cooldown_until_ms,
            })
        except Exception:  # noqa: BLE001 — persistence is best-effort
            pass

    def _emit_autopilot(self, decision, bar: Bar, cycle_id: str, equity: float) -> None:
        from risk.autopilot import AutopilotAction
        headline = f"Autopilot {decision.action.value.upper()}: {decision.reason}"
        try:
            from agent.graph.contracts import AgentEvent, KIND_CONTROL
            self.bridge.emit_event(AgentEvent(
                agent="Autopilot", kind=KIND_CONTROL, headline=headline, cycle_id=cycle_id,
                detail={"action": decision.action.value, "equity": round(equity, 2),
                        "protected_floor": round(self._autopilot_state.protected_floor, 2),
                        "banked": round(decision.banked, 2)},
            ))
        except Exception:  # noqa: BLE001
            pass
        if decision.action in (AutopilotAction.BANK, AutopilotAction.HALT_DAY):
            self._notify(f"🤖 {headline} (equity ${equity:.2f}, "
                         f"floor ${self._autopilot_state.protected_floor:.2f})")

    # ── execution → ledger → trade/ledger rows ──────────────────────────────

    def _handle_execution(self, execution: ExecutionReport, bar: Bar, cycle_id: str,
                          regime: str = "", breakdown: Optional[dict] = None):
        if execution.is_fill and execution.fill is not None:
            realized = self.ledger.apply(execution.fill)
            # Clear failure streak on any confirmed fill
            self._consecutive_exec_failures = 0
            self._first_exec_failure_ms = None
            self._sustained_warn_sent = False
            self._trades_today += 1   # counts toward the >= 1 trade/day floor
            # Accumulate for the live scorecard, pairing trades like the backtest.
            self._fills.append(execution.fill)
            if execution.fill.order.side == "buy":
                if self._entry_fill is None:
                    self._entry_fill = execution.fill
                    # Snapshot the current forecast confidence at entry for calibration.
                    self._entry_forecast_confidence = self._current_forecast_confidence()
                    # Anchor the autopilot cycle: profit-lock + trailing measure
                    # gains from this fresh deployment's equity.
                    if self._autopilot_config is not None and self._autopilot_config.enabled:
                        from risk.autopilot import start_cycle
                        self._autopilot_state = start_cycle(
                            self._autopilot_state, self.ledger.mark(bar.close))
            elif self._entry_fill is not None:
                self._trades.append(
                    Trade(entry=self._entry_fill, exit=execution.fill, pnl_usd=realized))
                self._entry_fill = None
                self._record_forecast_calibration(cycle_id, bar, regime, realized)
            trade_id = self.bridge.record_trade(
                symbol=execution.order.symbol,
                side=execution.order.side,
                size_usd=execution.order.size_usd,
                fill_price=execution.fill.fill_price,
                fee_usd=execution.fill.fee_usd,
                gas_usd=execution.fill.gas_usd,
                slippage_usd=execution.fill.slippage_usd,
                mode=self.mode,
                tx_hash=execution.tx_hash,
                timestamp_ms=bar.timestamp,
            )
            if trade_id:
                self.bridge.append_ledger(
                    trade_id=trade_id,
                    realized_pnl_usd=realized,
                    cumulative_pnl_usd=self.ledger.cumulative_pnl(bar.close),
                    cumulative_fees_usd=self.ledger.cumulative_fees,
                    cumulative_gas_usd=self.ledger.cumulative_gas,
                    peak_equity_usd=self.ledger.peak_equity,
                    current_drawdown_pct=self.ledger.drawdown_pct(bar.close),
                    timestamp_ms=bar.timestamp,
                )
            self.bridge.audit("trade", cycle_id,
                             {"side": execution.order.side, "size_usd": execution.order.size_usd,
                              "fill_price": execution.fill.fill_price, "tx_hash": execution.tx_hash,
                              "realized_pnl": realized}, "info")
            # ── Immediate trade alert (Telegram) ────────────────────────────
            # Fire the moment the fill is confirmed — users must not wait for the
            # next cycle log line to know a trade happened.
            side_emoji = "🟢" if execution.order.side == "buy" else "🔴"
            tx_url = (f"https://bscscan.com/tx/{execution.tx_hash}"
                      if execution.tx_hash else "")
            pnl_str = (f"  PnL: ${realized:+.2f}" if execution.order.side == "sell" else "")
            alert = (
                f"{side_emoji} TRADE FILLED — {execution.order.side.upper()} "
                f"{execution.order.symbol}\n"
                f"  Size: ${execution.order.size_usd:.2f}  @  ${execution.fill.fill_price:,.2f}\n"
                f"  Mode: {self.mode}{pnl_str}\n"
                + (f"  TX: {tx_url}" if tx_url else "")
            )
            self._notify(alert)

            # Hermes write-side: a sell closes/reduces a position → reflect on the
            # realized outcome. (Buys open positions — no outcome to learn yet.)
            if (self.reflection_writer is not None
                    and execution.order.side == "sell" and breakdown is not None):
                self.reflection_writer.reflect(
                    cycle_id=cycle_id, trade_id=trade_id, timestamp_ms=bar.timestamp,
                    regime=regime, side=execution.order.side, signals=breakdown,
                    realized_pnl=realized,
                )
            return "allow", execution.reason, trade_id

        if execution.status == DUPLICATE:
            return "block", execution.reason, None
        if execution.status == REJECTED:
            # A guardrail correctly blocked a trade — this is the system working,
            # not a rule violation (scorecard rule-adherence counts it as such).
            self._blocks_fired += 1
            self.bridge.audit("risk_veto", cycle_id, {"reason": execution.reason}, "warn")
            return "block", execution.reason, None
        if execution.status == FAILED:
            self.bridge.audit("error", cycle_id, {"reason": execution.reason}, "error")
            self._consecutive_exec_failures += 1
            if self._first_exec_failure_ms is None:
                self._first_exec_failure_ms = int(execution.order.timestamp)
            if self._consecutive_exec_failures >= self._EXEC_FAIL_ALERT_THRESHOLD:
                self._notify(
                    f"ALERT: {self._consecutive_exec_failures} consecutive swap failures.\n"
                    f"Last error: {execution.reason}\n"
                    f"Order: {execution.order.side.upper()} "
                    f"${execution.order.size_usd:.2f} {execution.order.symbol}\n"
                    f"Mode: {self.mode} — check wallet balance and TWAK status."
                )
                self._consecutive_exec_failures = 0   # reset so we don't spam
            return "block", execution.reason, None
        return "reduce", execution.reason, None

    # ── finalise: decision row + risk_state every cycle ─────────────────────

    def _finalise(self, cycle_id, bar, regime, verdict, reason, order, execution,
                  target_usd, final_size, trade_id, breakdown, signals, halted):
        equity = self.ledger.mark(bar.close)
        drawdown = self.ledger.drawdown_pct(bar.close)
        circuit = self.ledger.consecutive_losses >= self.max_consecutive_losses

        self.bridge.record_decision(
            cycle_id=cycle_id, symbol=self.symbol, timestamp_ms=bar.timestamp,
            regime=regime, signals=signals, target_position_usd=target_usd,
            risk_verdict=verdict, risk_reason=reason, final_size_usd=final_size,
            trade_id=trade_id, setup_key=self._current_setup_key,
        )
        self.bridge.update_risk_state(
            daily_loss_usd=self.ledger.daily_loss_usd(bar.close),
            open_exposure_usd=self.ledger.open_exposure(bar.close),
            current_drawdown_pct=drawdown,
            peak_equity_usd=self.ledger.peak_equity,
            circuit_breaker_active=circuit,
        )
        self.bridge.update_positions(
            symbol=self.symbol,
            quantity=self.ledger.units,
            avg_entry_price=self.ledger.avg_entry,
            current_price=bar.close,
            mode=self.mode,
            updated_ms=bar.timestamp,
        )

        # ── Wallet balance snapshot (best-effort, never block the cycle) ────
        try:
            from agent.twak_cli import TwakCli
            _twak = TwakCli()
            _chain = self._chain if hasattr(self, "_chain") else "bsc"
            _bal = _twak.balance(_chain)
            _tokens = {t["symbol"]: float(t["balance"]) for t in _bal.get("tokens", [])}
            _bnb = float(_bal.get("available", 0))

            def _live_price(sym: str, fallback: float) -> float:
                # Live USD price via twak; fall back to `fallback` on any failure.
                try:
                    return float(_twak.price(sym, _chain).get("priceUsd") or 0) or fallback
                except Exception:
                    return fallback

            _eth_price = _live_price("ETH", bar.close if self.symbol == "ETH" else 0.0)
            _bnb_price = _live_price("BNB", bar.close if self.symbol == "BNB" else 650.0)
            _usdt = _tokens.get("USDT", 0.0)
            _eth = _tokens.get("ETH", 0.0)
            self._cached_usdt_balance = _usdt   # used by _cap_to_deployable next cycle
            self._cached_eth_balance = _eth

            # Wallet mismatch watchdog: real ETH held but paper ledger thinks flat.
            # Fires once per session so the operator knows the agent lost sync.
            _ledger_units = self.ledger.units
            _eth_mismatch = (
                self.symbol == "ETH"
                and _eth > 1e-6                         # real wallet has ETH
                and _ledger_units < 1e-9                # but ledger says flat
            )
            if _eth_mismatch and not self._wallet_mismatch_alerted:
                _eth_usd = round(_eth * _eth_price, 2)
                self._notify(
                    f"WALLET MISMATCH: real wallet holds {_eth:.6f} ETH (≈${_eth_usd}) "
                    f"but paper ledger shows FLAT.\n"
                    f"USDT remaining: ${_usdt:.4f}\n"
                    f"This means a swap executed on-chain without a confirmed tx hash.\n"
                    f"Action: to realign, restart the agent. The ETH is safe in your wallet."
                )
                self._wallet_mismatch_alerted = True

            # Position reconciliation: ledger says long, wallet says flat.
            # Triggered when the operator manually converts/sells outside the agent.
            # Cascade-closes the position: zeroes the ledger, writes a trade row +
            # ledger row, pushes quantity=0 to Convex so the portfolio clears.
            _sym_token = self.symbol.split("/")[0]   # "ETH" from "ETH" or "ETH/USDT"
            _on_chain_held = _tokens.get(_sym_token, 0.0)
            _position_gone = (
                _ledger_units > 1e-6
                and _on_chain_held < _ledger_units * 0.05   # <5% of expected → gone
            )
            if _position_gone and not self._position_reconciled:
                _exit_price = _eth_price if _sym_token == "ETH" else bar.close
                _exit_size_usd = _ledger_units * _exit_price
                _realized = (_exit_price - self.ledger.avg_entry) * _ledger_units

                # Force-close the in-memory ledger (mirrors what apply() does on sell)
                self.ledger.cash += _exit_size_usd
                self.ledger.realized_pnl_total += _realized
                if _realized < 0:
                    self.ledger.consecutive_losses += 1
                else:
                    self.ledger.consecutive_losses = 0
                self.ledger.units = 0.0
                self.ledger.avg_entry = 0.0
                self._entry_fill = None   # drop the unpaired entry fill

                # Write a reconciliation trade row so Recent Trades shows the close
                _trade_id = self.bridge.record_trade(
                    symbol=self.symbol,
                    side="sell",
                    size_usd=round(_exit_size_usd, 4),
                    fill_price=round(_exit_price, 4),
                    fee_usd=0.0,
                    gas_usd=0.0,
                    slippage_usd=0.0,
                    mode=self.mode,
                    tx_hash=None,
                    timestamp_ms=bar.timestamp,
                )
                # Write ledger row so the PnL chart reflects the close
                if _trade_id:
                    self.bridge.append_ledger(
                        trade_id=_trade_id,
                        realized_pnl_usd=round(_realized, 4),
                        cumulative_pnl_usd=round(self.ledger.cumulative_pnl(bar.close), 4),
                        cumulative_fees_usd=round(self.ledger.cumulative_fees, 4),
                        cumulative_gas_usd=round(self.ledger.cumulative_gas, 4),
                        peak_equity_usd=round(self.ledger.peak_equity, 4),
                        current_drawdown_pct=round(self.ledger.drawdown_pct(bar.close), 6),
                        timestamp_ms=bar.timestamp,
                    )
                # Zero the Convex position row → portfolio `open` query filters it out
                self.bridge.update_positions(
                    symbol=self.symbol,
                    quantity=0.0,
                    avg_entry_price=0.0,
                    current_price=_exit_price,
                    mode=self.mode,
                    updated_ms=bar.timestamp,
                )
                self._position_reconciled = True
                self._notify(
                    f"⚡ POSITION RECONCILED — external close detected\n"
                    f"  Ledger held {_ledger_units:.6f} {_sym_token} "
                    f"(on-chain: {_on_chain_held:.6f})\n"
                    f"  Est. exit @ ${_exit_price:,.2f}  |  PnL: ${_realized:+.2f}\n"
                    f"  Portfolio position cleared automatically."
                )

            # All non-zero token balances (including BNB) for dynamic Convert UI
            _all_tokens = [
                {"symbol": t["symbol"], "balance": float(t["balance"])}
                for t in _bal.get("tokens", [])
                if float(t.get("balance", 0)) > 0
            ]
            if _bnb > 0:
                _all_tokens = [t for t in _all_tokens if t["symbol"] != "BNB"]
                _all_tokens.append({"symbol": "BNB", "balance": _bnb})

            self.bridge.update_wallet_state(
                address=_bal.get("address", ""),
                usdt=_usdt,
                eth=_eth,
                bnb=_bnb,
                bnb_usd=round(_bnb * _bnb_price, 4),
                total_usd=round(_usdt + _eth * _eth_price + _bnb * _bnb_price, 2),
                updated_ms=bar.timestamp,
                tokens=_all_tokens if _all_tokens else None,
            )
        except Exception as exc:  # wallet balance is display-only; never block the trade cycle
            logging.getLogger(__name__).warning("wallet_state snapshot failed: %r", exc)

        self.bridge.append_price_tick(
            symbol=self.symbol,
            price=bar.close,
            timestamp_ms=bar.timestamp,
        )

        # ── Accumulate the scorecard series + push the live objective ────────
        open_exp = self.ledger.open_exposure(bar.close)
        self._cycles_total += 1
        self._equity_curve.append(equity)
        self._equity_ts.append(bar.timestamp)
        self._exposure_curve.append(open_exp)
        if equity > 0:
            self._peak_exposure_pct = max(self._peak_exposure_pct, open_exp / equity)
        if halted and not self._was_halted:        # rising edge only
            self._kill_switch_activations += 1
            if not self._halted_by_floor:
                def _resume_from_ks():
                    self.bridge.set_halted(False)
                self._notify_with_approval(
                    "Kill switch activated. Agent halted.",
                    on_approve=_resume_from_ks,
                    on_reject=None,
                    approve_label="Resume",
                    reject_label="Stay Halted",
                )
        if not halted:
            self._halted_by_floor = False
        self._was_halted = halted
        self._daily_max_dd = max(self._daily_max_dd, drawdown)
        if circuit and not self._was_circuit:
            self._circuit_breaker_activations += 1
        self._was_circuit = circuit
        self._push_scorecard()

        return CycleResult(
            cycle_id=cycle_id, timestamp_ms=bar.timestamp, halted=halted,
            regime=regime, verdict=verdict, reason=reason, order=order,
            execution=execution, equity=equity, drawdown_pct=drawdown,
            breakdown=breakdown,
        )

    # ── live scorecard ────────────────────────────────────────────────────────

    def build_scorecard(self):
        """Score the run so far against the agent's goal (docs/GOAL.md). Same
        core/scorecard.py the backtest uses — sim and live score identically."""
        ops = OperationalStats(cycles_total=self._cycles_total)
        rules = RuleAdherence(
            violations=0,   # a breach can't reach execution — guardrails block first
            blocks_fired=self._blocks_fired,
            kill_switch_activations=self._kill_switch_activations,
            circuit_breaker_activations=self._circuit_breaker_activations,
            max_open_exposure_pct=self._peak_exposure_pct,
        )
        return compute_scorecard(
            self._equity_curve, self._trades, self._fills, self._initial_capital,
            timestamps=self._equity_ts, exposure_curve=self._exposure_curve,
            operational=ops, rule_adherence=rules,
        )

    def _push_scorecard(self) -> None:
        """Upsert the live scorecard. Pure telemetry — a failure here must never
        crash a trading cycle, so it's fully guarded."""
        try:
            self.bridge.update_scorecard(**self.build_scorecard().as_convex_row())
        except Exception:  # noqa: BLE001 — scorecard is observability, not the trade
            pass

    # ── drivers ─────────────────────────────────────────────────────────────

    def run(self, max_cycles: Optional[int] = None) -> list[CycleResult]:
        """Drive the feed to exhaustion (replay) or for max_cycles. No sleeps."""
        results: list[CycleResult] = []
        n = 0
        while max_cycles is None or n < max_cycles:
            history = self.feed.next()
            if history is None:
                break
            results.append(self.run_cycle(history))
            n += 1
        return results

    def run_forever(self, cycle_seconds: int) -> None:
        """Live driver: one cycle, sleep to cadence, repeat. Ctrl-C to stop.

        Each cycle is wrapped so an unanticipated exception is logged (structured,
        keyed by trace) and audited to Convex, then the loop CONTINUES — a testnet
        shadow-run must survive the surprises it exists to surface, not die on the
        first one."""
        from agent.observability import jlog
        while True:
            try:
                # Refresh KOL sentiment before each cycle when enabled (off hot path,
                # failure-isolated inside run_live_ingest).
                if getattr(self, "kol_enabled", False):
                    try:
                        from agent.social.live import run_live_ingest
                        run_live_ingest(self.bridge)
                    except Exception:  # noqa: BLE001
                        pass
                # Cross-sectional rotation: when flat, pick the strongest signal
                # across the full universe instead of being locked to one symbol.
                if self._scanner is not None:
                    try:
                        flat = self.ledger.open_exposure <= self._exposure_epsilon
                        if flat:
                            best = self._scanner.best_symbol()
                            if best and best != self.symbol:
                                self._switch_symbol(best)
                    except Exception:  # noqa: BLE001 — never block the trade cycle
                        pass
                history = self.feed.next()
                if history:
                    res = self.run_cycle(history)
                    jlog("cycle", trace=res.cycle_id, regime=res.regime,
                         verdict=res.verdict, equity=round(res.equity, 2),
                         drawdown=round(res.drawdown_pct, 4),
                         filled=bool(res.execution and res.execution.is_fill),
                         halted=res.halted, reason=res.reason)
                    # Neural Mesh chain trace — fire setup_scorer every N cycles
                    self._chain_cycle_n += 1
                    try:
                        from agent.agents.loop_chain import (
                            fire_setup_scorer, CHAIN_EVERY_N_CYCLES,
                        )
                        if self._chain_cycle_n >= CHAIN_EVERY_N_CYCLES:
                            self._chain_cycle_n = 0
                            fire_setup_scorer(self.bridge, self.symbol, res.cycle_id)
                    except Exception:  # noqa: BLE001 — chain trace is telemetry only
                        pass
            except Exception as e:  # noqa: BLE001 — shadow-run resilience
                jlog("cycle_error", level="error",
                     error=str(e), error_type=type(e).__name__)
                try:
                    self.bridge.audit("error", None,
                                      {"error": str(e), "error_type": type(e).__name__}, "error")
                except Exception:  # noqa: BLE001
                    pass
            # Spawned-agent tick — run due agents + deliver push (off scored path)
            try:
                from agent.agents.schedule import due_agents, deliver_push
                from agent.agents.runner import run_agent
                from agent.agents.registry import list_active
                from agent.push import build_push_payload
                import os
                _vapid = {"private_key": os.environ.get("VAPID_PRIVATE_KEY", ""),
                          "subject": os.environ.get("VAPID_SUBJECT", "mailto:noreply@alien-trade.app")}
                _now = int(time.time() * 1000)
                _agents = list_active(self.bridge)
                for _a in due_agents(_agents, _now):
                    _res = run_agent(_a, twak=self.twak, skills=getattr(self, "skills", None),
                                     bridge=self.bridge, client=getattr(self, "anthropic_client", None))
                    if _res["ok"] and (_a.get("notify_policy") or {}).get("webpush", True):
                        deliver_push(self.bridge,
                                     build_push_payload(_a["name"], _res["summary"], url="/agents"),
                                     vapid=_vapid)
            except Exception:  # noqa: BLE001 — never break the loop
                pass
            # Watchdog sweep — flag stalled spawned agents (off scored path)
            try:
                from agent.agents.watchdog import find_stalled
                from agent.agents.registry import list_active
                from agent.graph.contracts import AgentEvent, KIND_CONTROL
                _now = int(time.time() * 1000)
                for _a in find_stalled(list_active(self.bridge), _now):
                    self.bridge.emit_event(AgentEvent(
                        agent="WalletManager", kind=KIND_CONTROL,
                        headline=f"Agent '{_a['name']}' is stalled — no activity",
                        detail="{}", refs=[],
                    ))
            except Exception:  # noqa: BLE001 — never break the loop
                pass
            # Drain operator commands (convert, withdraw, etc) — off scored path.
            # Drain up to 5 per cycle so a burst doesn't block the next cycle.
            try:
                from agent.command_worker import run_one_command
                for _ in range(5):
                    if not run_one_command(self.bridge):
                        break
            except Exception:  # noqa: BLE001 — command drain must never crash the loop
                pass
            time.sleep(cycle_seconds)


# ── helpers ────────────────────────────────────────────────────────────────

def _day_key(timestamp_ms: int) -> str:
    """UTC calendar-day key (YYYY-MM-DD) for the autopilot daily target/reset."""
    import datetime
    return datetime.datetime.utcfromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")


def _signals_obj(breakdown: dict) -> dict:
    """Map score_breakdown → the Convex decisions.signals object shape."""
    return {
        "momentum":    breakdown.get("momentum"),
        "derivatives": breakdown.get("derivatives"),
        "sentiment":   breakdown.get("sentiment"),
        "flow":        breakdown.get("flow"),
    }
