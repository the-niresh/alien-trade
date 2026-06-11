"""
Autopilot capital manager — the discipline layer (deterministic, off the LLM path).

The agent's edge is not a magic signal; it is ruthless, emotionless discipline:
take profit at the target, protect banked capital forever, refuse to redeploy into
a bad market, and quit for the day when ahead. Every rule here is pure arithmetic so
sim and live behave identically (locked decision #2) — the same way guardrails.py and
forecast.py are shared.

Six behaviours, all optional and independently configurable:
  1. Profit-Lock + Capital Ratchet — hit the target -> flatten to stable, bank it.
     The protected floor ONLY EVER RISES; the agent never re-risks banked capital.
  2. Auto-Recycle gate — after banking, redeploy only when regime + forecast are
     favourable (not a blind re-entry). This is the "knows when to stop" valve.
  3. Trailing Give-Back — exit if price retraces X% from its peak since entry.
  4. Daily Profit Target — up X% today -> stop for the day (mirror of daily-loss halt).
  5. Cooldown-after-loss — pause N hours after a losing close (kills revenge trading).
  6. Sizing off (equity - protected_floor) — see deployable_capital().

Invariants (tested in test_autopilot.py):
  - protected_floor is monotone non-decreasing (ratchet can never lower it).
  - With autopilot disabled, evaluate() always returns HOLD (parity: no behaviour change).
  - BANK fires when EITHER the % or the absolute target is met (whichever first).
  - A blocked regime or below-threshold confidence always blocks recycle entry.
  - deployable_capital() never exceeds (equity - protected_floor) and never goes negative.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class AutopilotAction(str, Enum):
    HOLD = "hold"                # no intervention — normal strategy proceeds
    BANK = "bank"                # take profit: flatten to stable, ratchet the floor
    TRAIL_EXIT = "trail_exit"    # trailing give-back exit (lock gains before reversal)
    HALT_DAY = "halt_day"        # daily profit target hit — stop trading for the day
    BLOCK_ENTRY = "block_entry"  # recycle gate / cooldown — stay in cash this cycle


@dataclass(frozen=True)
class AutopilotConfig:
    """User-set, persisted in Convex `config`. All thresholds optional (None = off)."""
    enabled: bool = False
    # 1+2 Profit-lock + ratchet
    profit_target_pct: float | None = None     # e.g. 0.10 -> bank at +10% on the cycle
    profit_target_abs: float | None = None     # e.g. 50.0 -> bank at +$50 gain
    protect_principal: bool = True             # ratchet the principal too, not just profit
    # 2 Recycle gate ("future-predicting view")
    min_recycle_confidence: float = 0.0        # require forecast confidence >= this to redeploy
    recycle_blocked_regimes: tuple[str, ...] = ()   # e.g. ("crash", "high_vol")
    # 3 Trailing give-back
    trailing_giveback_pct: float | None = None  # exit if retrace from peak >= this
    # 4 Daily profit target
    daily_profit_target_pct: float | None = None
    # 5 Cooldown after a losing close
    loss_cooldown_hours: float = 0.0


@dataclass
class AutopilotState:
    """Mutable, persisted in Convex `risk_state`. Carries the ratchet + cycle marks."""
    protected_floor: float = 0.0          # banked capital — never re-risked; only rises
    cycle_start_equity: float = 0.0       # equity when the current deployment began
    peak_equity: float = 0.0              # peak since cycle start (trailing reference)
    day_start_equity: float = 0.0         # equity at the start of the calendar day
    day_key: str = ""                     # calendar day; daily target resets on change
    halted_for_day: bool = False          # set when the daily target is banked
    cooldown_until_ms: int = 0            # no new entries before this timestamp


@dataclass(frozen=True)
class AutopilotDecision:
    action: AutopilotAction
    state: AutopilotState                 # next state (caller persists it)
    reason: str
    banked: float = 0.0                   # amount added to the protected floor on BANK


def deployable_capital(equity: float, state: AutopilotState) -> float:
    """Capital the agent may put at risk this cycle = equity above the protected floor.
    Never negative, never above (equity - floor). The RiskEngine sizes off THIS, not
    raw equity, so banked gains stay out of harm's way."""
    return max(0.0, equity - max(0.0, state.protected_floor))


def start_cycle(state: AutopilotState, equity: float) -> AutopilotState:
    """Mark the start of a fresh deployment — anchors the cycle PnL + trailing peak."""
    return replace(state, cycle_start_equity=equity, peak_equity=equity)


def evaluate(
    config: AutopilotConfig,
    state: AutopilotState,
    *,
    equity: float,
    in_position: bool,
    regime: str,
    forecast_confidence: float,
    day_key: str,
    now_ms: int,
    last_close_was_loss: bool = False,
) -> AutopilotDecision:
    """Single deterministic decision per cycle. Returns the action + the next state.

    Order of precedence (first match wins):
      daily target -> (in position: take-profit -> trailing) -> (flat: cooldown ->
      recycle gate) -> HOLD.
    Disabled config short-circuits to HOLD so sim/live parity holds with no behaviour.
    """
    if not config.enabled:
        return AutopilotDecision(AutopilotAction.HOLD, state, "autopilot off")

    # ── Daily roll-over: reset the day anchor + clear the day-halt + reset peak ──
    if day_key != state.day_key:
        state = replace(
            state, day_key=day_key, day_start_equity=equity,
            halted_for_day=False, peak_equity=max(state.peak_equity, equity),
        )

    # Track the running peak (used by trailing + only ever rises within a cycle).
    if equity > state.peak_equity:
        state = replace(state, peak_equity=equity)

    # ── 4. Daily profit target — bank the day, stop trading until tomorrow ───────
    if config.daily_profit_target_pct is not None and state.day_start_equity > 0:
        day_gain_pct = (equity - state.day_start_equity) / state.day_start_equity
        if day_gain_pct >= config.daily_profit_target_pct:
            return AutopilotDecision(
                AutopilotAction.HALT_DAY,
                replace(state, halted_for_day=True),
                f"daily profit target +{config.daily_profit_target_pct:.0%} reached "
                f"(+{day_gain_pct:.2%}) — banking the day",
            )
    if state.halted_for_day:
        return AutopilotDecision(AutopilotAction.HALT_DAY, state,
                                 "already banked for the day — flat until tomorrow")

    if in_position:
        gain = equity - state.cycle_start_equity
        gain_pct = gain / state.cycle_start_equity if state.cycle_start_equity > 0 else 0.0

        # ── 1. Profit-lock + capital ratchet ────────────────────────────────────
        hit_pct = config.profit_target_pct is not None and gain_pct >= config.profit_target_pct
        hit_abs = config.profit_target_abs is not None and gain >= config.profit_target_abs
        if hit_pct or hit_abs:
            # Bank the gain (and principal if protecting it). The floor only rises.
            banked_total = equity if config.protect_principal else (state.protected_floor + max(0.0, gain))
            new_floor = max(state.protected_floor, banked_total)
            added = new_floor - state.protected_floor
            return AutopilotDecision(
                AutopilotAction.BANK,
                replace(state, protected_floor=new_floor),
                f"profit target hit (+{gain_pct:.2%} / +{gain:.2f}) — securing, "
                f"floor -> {new_floor:.2f}",
                banked=added,
            )

        # ── 3. Trailing give-back — lock gains before a reversal eats them ──────
        if (config.trailing_giveback_pct is not None
                and state.peak_equity > state.cycle_start_equity > 0):
            retrace = (state.peak_equity - equity) / state.peak_equity
            if retrace >= config.trailing_giveback_pct:
                return AutopilotDecision(
                    AutopilotAction.TRAIL_EXIT, state,
                    f"trailing give-back {retrace:.2%} from peak — locking gains",
                )
        return AutopilotDecision(AutopilotAction.HOLD, state, "in position — targets not met")

    # ── Flat: decide whether a fresh deployment is allowed ─────────────────────
    # 5. Cooldown after a loss
    if last_close_was_loss and config.loss_cooldown_hours > 0:
        cooldown_until = now_ms + int(config.loss_cooldown_hours * 3_600_000)
        state = replace(state, cooldown_until_ms=cooldown_until)
    if now_ms < state.cooldown_until_ms:
        return AutopilotDecision(AutopilotAction.BLOCK_ENTRY, state,
                                 "cooldown after a losing trade — sitting out")
    # 2. Recycle gate — don't redeploy into a bad/uncertain market
    if regime in config.recycle_blocked_regimes:
        return AutopilotDecision(AutopilotAction.BLOCK_ENTRY, state,
                                 f"recycle blocked in {regime} regime — staying in cash")
    if forecast_confidence < config.min_recycle_confidence:
        return AutopilotDecision(
            AutopilotAction.BLOCK_ENTRY, state,
            f"recycle blocked — forecast confidence {forecast_confidence:.2f} "
            f"< {config.min_recycle_confidence:.2f}",
        )
    return AutopilotDecision(AutopilotAction.HOLD, state, "clear to deploy")
