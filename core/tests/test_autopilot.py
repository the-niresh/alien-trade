"""Autopilot capital manager — deterministic discipline-layer tests (offline)."""
from __future__ import annotations

from risk.autopilot import (
    AutopilotAction, AutopilotConfig, AutopilotState,
    deployable_capital, evaluate, start_cycle,
)

DAY = "2026-06-22"


def _base_state(eq=100.0):
    return AutopilotState(
        protected_floor=0.0, cycle_start_equity=eq, peak_equity=eq,
        day_start_equity=eq, day_key=DAY,
    )


def _eval(cfg, state, **kw):
    defaults = dict(
        equity=100.0, in_position=True, regime="trend",
        forecast_confidence=1.0, day_key=DAY, now_ms=0, last_close_was_loss=False,
    )
    defaults.update(kw)
    return evaluate(cfg, state, **defaults)


# ── Parity: disabled = no behaviour ───────────────────────────────────────────

def test_disabled_always_holds():
    cfg = AutopilotConfig(enabled=False, profit_target_pct=0.01)
    d = _eval(cfg, _base_state(), equity=200.0)  # huge gain, but autopilot off
    assert d.action is AutopilotAction.HOLD


# ── 1. Profit-lock + capital ratchet ──────────────────────────────────────────

def test_bank_on_pct_target():
    cfg = AutopilotConfig(enabled=True, profit_target_pct=0.10)
    d = _eval(cfg, _base_state(100.0), equity=110.0)
    assert d.action is AutopilotAction.BANK
    assert d.state.protected_floor == 110.0   # protect_principal default -> floor = equity
    assert d.banked == 110.0


def test_bank_on_abs_target_first():
    # abs target ($5) is met before the pct target (10%) — whichever first
    cfg = AutopilotConfig(enabled=True, profit_target_pct=0.10, profit_target_abs=5.0)
    d = _eval(cfg, _base_state(100.0), equity=105.0)  # +5% / +$5
    assert d.action is AutopilotAction.BANK


def test_no_bank_below_target():
    cfg = AutopilotConfig(enabled=True, profit_target_pct=0.10)
    d = _eval(cfg, _base_state(100.0), equity=105.0)  # only +5%
    assert d.action is AutopilotAction.HOLD


def test_floor_is_monotone_ratchet():
    cfg = AutopilotConfig(enabled=True, profit_target_pct=0.05)
    st = AutopilotState(protected_floor=200.0, cycle_start_equity=100.0,
                        peak_equity=100.0, day_start_equity=100.0, day_key=DAY)
    # A smaller bank than the existing floor must NOT lower the floor.
    d = _eval(cfg, st, equity=110.0)
    assert d.action is AutopilotAction.BANK
    assert d.state.protected_floor == 200.0   # unchanged — ratchet only rises
    assert d.banked == 0.0


def test_profit_only_mode():
    cfg = AutopilotConfig(enabled=True, profit_target_pct=0.10, protect_principal=False)
    d = _eval(cfg, _base_state(100.0), equity=110.0)
    assert d.state.protected_floor == 10.0    # only the +$10 gain is banked


# ── 3. Trailing give-back ──────────────────────────────────────────────────────

def test_trailing_giveback_exit():
    cfg = AutopilotConfig(enabled=True, trailing_giveback_pct=0.20)
    st = AutopilotState(cycle_start_equity=100.0, peak_equity=150.0,
                        day_start_equity=100.0, day_key=DAY)
    d = _eval(cfg, st, equity=118.0)  # 150 -> 118 = 21.3% retrace > 20%
    assert d.action is AutopilotAction.TRAIL_EXIT


def test_trailing_no_exit_small_retrace():
    cfg = AutopilotConfig(enabled=True, trailing_giveback_pct=0.20)
    st = AutopilotState(cycle_start_equity=100.0, peak_equity=150.0,
                        day_start_equity=100.0, day_key=DAY)
    d = _eval(cfg, st, equity=140.0)  # only 6.7% retrace
    assert d.action is AutopilotAction.HOLD


# ── 4. Daily profit target ─────────────────────────────────────────────────────

def test_daily_target_halts():
    cfg = AutopilotConfig(enabled=True, daily_profit_target_pct=0.05)
    d = _eval(cfg, _base_state(100.0), equity=106.0, in_position=False)
    assert d.action is AutopilotAction.HALT_DAY
    assert d.state.halted_for_day is True


def test_daily_halt_persists_until_next_day():
    cfg = AutopilotConfig(enabled=True, daily_profit_target_pct=0.05)
    st = replace_halted(_base_state(100.0))
    d = _eval(cfg, st, equity=101.0, in_position=False)
    assert d.action is AutopilotAction.HALT_DAY
    # New calendar day clears the halt -> back to deploying.
    d2 = _eval(cfg, st, equity=101.0, in_position=False, day_key="2026-06-23")
    assert d2.action is not AutopilotAction.HALT_DAY


def replace_halted(st):
    from dataclasses import replace
    return replace(st, halted_for_day=True)


# ── 2. Recycle gate + 5. cooldown ─────────────────────────────────────────────

def test_recycle_blocked_in_bad_regime():
    cfg = AutopilotConfig(enabled=True, recycle_blocked_regimes=("crash", "high_vol"))
    d = _eval(cfg, _base_state(), equity=100.0, in_position=False, regime="crash")
    assert d.action is AutopilotAction.BLOCK_ENTRY


def test_recycle_blocked_low_confidence():
    cfg = AutopilotConfig(enabled=True, min_recycle_confidence=0.7)
    d = _eval(cfg, _base_state(), in_position=False, forecast_confidence=0.5)
    assert d.action is AutopilotAction.BLOCK_ENTRY


def test_recycle_allowed_when_favourable():
    cfg = AutopilotConfig(enabled=True, min_recycle_confidence=0.7,
                          recycle_blocked_regimes=("crash",))
    d = _eval(cfg, _base_state(), in_position=False, regime="trend",
              forecast_confidence=0.9)
    assert d.action is AutopilotAction.HOLD


def test_cooldown_after_loss_blocks_then_clears():
    cfg = AutopilotConfig(enabled=True, loss_cooldown_hours=2.0)
    st = _base_state()
    d = _eval(cfg, st, in_position=False, last_close_was_loss=True, now_ms=0)
    assert d.action is AutopilotAction.BLOCK_ENTRY
    assert d.state.cooldown_until_ms == 2 * 3_600_000
    # Still inside the window -> blocked
    d2 = _eval(cfg, d.state, in_position=False, now_ms=1 * 3_600_000)
    assert d2.action is AutopilotAction.BLOCK_ENTRY
    # After the window -> clear
    d3 = _eval(cfg, d.state, in_position=False, now_ms=3 * 3_600_000)
    assert d3.action is AutopilotAction.HOLD


# ── deployable_capital ─────────────────────────────────────────────────────────

def test_deployable_capital_respects_floor():
    st = AutopilotState(protected_floor=70.0)
    assert deployable_capital(100.0, st) == 30.0


def test_deployable_capital_never_negative():
    st = AutopilotState(protected_floor=120.0)
    assert deployable_capital(100.0, st) == 0.0


def test_start_cycle_anchors_equity():
    st = start_cycle(AutopilotState(), 250.0)
    assert st.cycle_start_equity == 250.0 and st.peak_equity == 250.0


from dataclasses import replace  # noqa: E402 (used by replace_halted helper above)
