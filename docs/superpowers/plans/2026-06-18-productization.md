# Alien-Trade Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden risk (hard ATR stop + trailing exit), add an in-cockpit notification panel that removes the Telegram dependency, wire deterministic X/KOL auto-trade bounded by the risk engine, and make the three sponsor integrations legible — without disturbing the deterministic `/core` trade math or existing cockpit views.

**Architecture:** Four phases in dependency order. Phase 1 (risk) ships first because it is the seatbelt for Phase 3 (KOL auto-trade). The ATR stop lives inside `RiskEngine.__call__` so sim and live share it (parity invariant). The KOL path reuses the existing deterministic lexicon scorer (`agent/social/score.py`) — no LLM on the hot path — and routes every KOL-triggered order through the existing `check_guardrails` caps as a live-only loop overlay, exactly like `_apply_autopilot`. Phase 2 (notifications) and Phase 4 (sponsor depth) are read-only UI over existing Convex tables.

**Tech Stack:** Python 3.11 (numpy, pytest) for `/core` + `agent/`; TypeScript + React 19 + Vite + shadcn/ui + Convex + Sonner for `web/`.

## Global Constraints

- Deterministic `/core` trade math — no LLM in signal computation or execution path.
- Sim and live share `/core` — no sim-only vs live-only code paths in the decision math (loop *overlays* may be live-only, like the existing autopilot, but must be no-ops offline so parity holds).
- Scored path is spot-long-only on the eligible allowlist: `ETH, CAKE, UNI, LINK, AAVE` (`core/risk/guardrails.py:15`, `TOKEN_ALLOWLIST`).
- Drawdown-first — never optimize for raw return; never select any rule on in-sample numbers.
- Additive only — no edits to existing working cockpit views beyond adding nav entries; no Convex schema changes except additive optional fields.
- Every KOL-triggered order passes `check_guardrails` + `check_max_exposure` (same caps as any signal). KOL cannot bypass any cap.
- A KOL signal can OPEN a long only on an eligible token while flat; a bearish KOL signal can only REDUCE/CLOSE a held position (never opens a short).
- Tier-1 / off-hot-path code must never crash a trading cycle — wrap in try/except and degrade (the codebase convention: `# noqa: BLE001`).
- Python: type annotations on all signatures, `black`/`ruff` clean. Run tests with the repo venv: `core/.venv/bin/python -m pytest`.

---

## File Structure

**Phase 1 — Risk hardening**
- Create `core/risk/stops.py` — pure ATR + stop-level + trailing functions (no I/O).
- Modify `core/risk/guardrails.py` — add stop config fields to `RiskConfig`.
- Modify `core/risk/engine.py` — enforce stops inside `RiskEngine.__call__`.
- Modify `agent/loop.py` — emit a `RiskGuard` `agent_events` row when a stop fires.
- Create `core/tests/test_stops.py`, `core/tests/test_engine_stops.py`.

**Phase 2 — Notification panel**
- Create `web/src/lib/eventSeverity.ts` — map `(agent, kind, headline)` → severity tier.
- Create `web/src/components/NotificationPanel.tsx` — reactive list with tier filter.
- Create `web/src/views/NotificationsView.tsx` — full-page panel.
- Modify `web/src/components/SideNav.tsx` — add `notifications` to the `View` union + nav item.
- Modify `web/src/App.tsx` — generalized debounced toast routing + render the new view.

**Phase 3 — X/KOL auto-trade**
- Modify `agent/graph/contracts.py` — add `SCOUT = "Scout"` to the agent roster.
- Create `agent/social/kol_intent.py` — pure stance→intent mapping + allowlist/eligibility filter.
- Create `agent/social/live.py` — live ingest pass that writes `sentiment_state` (eligible symbols only).
- Modify `agent/loop.py` — add the `_apply_kol_signal` live-only overlay (risk-gated).
- Create `agent/tests/test_kol_intent.py`, `agent/tests/test_kol_overlay.py`.

**Phase 4 — Sponsor depth**
- Create `docs/SPONSOR_DEPTH.md` — code-path map for CMC / TWAK / BNB SDK.
- Create `web/src/views/SponsorsView.tsx` — live view over `ledger`/`trades`/`walletState`.
- Modify `web/src/components/SideNav.tsx` + `web/src/App.tsx` — add `sponsors` view.

---

# Phase 1 — Risk Hardening

### Task 1: ATR + stop-level pure functions

**Files:**
- Create: `core/risk/stops.py`
- Test: `core/tests/test_stops.py`

**Interfaces:**
- Consumes: `from backtest.engine import Bar`.
- Produces:
  - `compute_atr(history: list[Bar], period: int = 14) -> float` — Wilder-style ATR over the last `period` bars; `0.0` if fewer than 2 bars.
  - `hard_stop_level(avg_entry: float, atr: float, mult: float) -> float` — `avg_entry - mult * atr`.
  - `trailing_stop_level(high_water: float, atr: float, mult: float) -> float` — `high_water - mult * atr`.
  - `stop_triggered(price: float, stop: float) -> bool` — `stop > 0 and price <= stop`.

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_stops.py
from backtest.engine import Bar
from risk.stops import compute_atr, hard_stop_level, trailing_stop_level, stop_triggered


def _bar(h: float, l: float, c: float) -> Bar:
    return Bar(timestamp=0, open=c, high=h, low=l, close=c, volume=0.0)


def test_compute_atr_true_range_average():
    bars = [_bar(10, 9, 9.5), _bar(11, 9.5, 10.5), _bar(12, 10, 11.5)]
    atr = compute_atr(bars, period=2)
    assert atr > 0.0
    assert round(atr, 4) == 1.75   # TR of last two bars: (11-9.5)=1.5, (12-10)=2.0 -> mean 1.75


def test_compute_atr_too_short_is_zero():
    assert compute_atr([_bar(10, 9, 9.5)], period=14) == 0.0


def test_hard_stop_level_below_entry():
    assert hard_stop_level(avg_entry=100.0, atr=5.0, mult=2.0) == 90.0


def test_trailing_stop_tracks_high_water():
    assert trailing_stop_level(high_water=120.0, atr=5.0, mult=2.0) == 110.0


def test_stop_triggered_only_when_breached():
    assert stop_triggered(price=89.0, stop=90.0) is True
    assert stop_triggered(price=91.0, stop=90.0) is False
    assert stop_triggered(price=50.0, stop=0.0) is False   # disabled stop never fires
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest core/tests/test_stops.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'risk.stops'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/risk/stops.py
"""
Pure stop-loss math — no I/O, no state. Used by RiskEngine to enforce a hard ATR
stop and an ATR trailing stop. Sim and live both run RiskEngine, so these run
identically in backtest and production (parity invariant, locked decision #2).
"""
from __future__ import annotations

from backtest.engine import Bar


def compute_atr(history: list[Bar], period: int = 14) -> float:
    """Average True Range over the last `period` bars. 0.0 if < 2 bars."""
    if len(history) < 2:
        return 0.0
    bars = history[-(period + 1):] if len(history) > period else history
    trs: list[float] = []
    for prev, cur in zip(bars[:-1], bars[1:]):
        tr = max(
            cur.high - cur.low,
            abs(cur.high - prev.close),
            abs(cur.low - prev.close),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def hard_stop_level(avg_entry: float, atr: float, mult: float) -> float:
    """Fixed stop a multiple of ATR below entry. 0.0 (disabled) if no ATR/entry."""
    if avg_entry <= 0.0 or atr <= 0.0 or mult <= 0.0:
        return 0.0
    return avg_entry - mult * atr


def trailing_stop_level(high_water: float, atr: float, mult: float) -> float:
    """Stop trailing a multiple of ATR below the position's high-water mark."""
    if high_water <= 0.0 or atr <= 0.0 or mult <= 0.0:
        return 0.0
    return high_water - mult * atr


def stop_triggered(price: float, stop: float) -> bool:
    """True when a positive stop level has been breached to the downside."""
    return stop > 0.0 and price <= stop
```

- [ ] **Step 4: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest core/tests/test_stops.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/risk/stops.py core/tests/test_stops.py
git commit -m "feat(risk): ATR + hard/trailing stop-level pure functions"
```

---

### Task 2: Stop config + enforce hard ATR stop in RiskEngine

**Files:**
- Modify: `core/risk/guardrails.py` (`RiskConfig`, after line 37)
- Modify: `core/risk/engine.py` (`_PosTracker` + `RiskEngine.__call__`)
- Test: `core/tests/test_engine_stops.py`

**Interfaces:**
- Consumes: `compute_atr`, `hard_stop_level`, `trailing_stop_level`, `stop_triggered` from `risk.stops`.
- Produces: when the engine holds a position (`units > 0`) and the bar's price breaches the active stop, `RiskEngine.__call__` returns a `sell` `Order` sized to the full open position (a forced exit) BEFORE consulting the inner strategy. Adds `RiskConfig.atr_stop_mult`, `RiskConfig.atr_trail_mult`, `RiskConfig.atr_period`. Adds `RiskEngine.last_stop_exit: dict | None` — set on the cycle a stop fires (`{"kind": "hard"|"trail", "stop": float, "price": float}`), else `None`.

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_engine_stops.py
from backtest.engine import Bar, Order
from risk.engine import RiskEngine
from risk.guardrails import RiskConfig


def _bar(ts: int, price: float, high: float, low: float) -> Bar:
    return Bar(timestamp=ts, open=price, high=high, low=low, close=price, volume=0.0)


def _buy_once(history):
    # Inner strategy: buy on the first bar only, then hold (None).
    return Order(side="buy", size_usd=1000.0, symbol="ETH", timestamp=history[-1].timestamp) \
        if len(history) == 1 else None


def test_hard_atr_stop_forces_exit_on_breach():
    cfg = RiskConfig(atr_stop_mult=2.0, atr_trail_mult=0.0, atr_period=2,
                     base_position_usd=1000.0, max_position_pct=1.0, max_open_exposure_pct=1.0)
    eng = RiskEngine(_buy_once, cfg, initial_capital=10_000.0)

    h = [_bar(0, 100.0, 101.0, 99.0)]
    eng(h)                                   # opens a long at ~100
    h.append(_bar(86_400_000, 100.0, 101.0, 98.0))
    eng(h)                                    # builds ATR, no breach
    # Drop price well below entry - 2*ATR -> stop must fire a sell.
    h.append(_bar(2 * 86_400_000, 80.0, 81.0, 79.0))
    order = eng(h)

    assert order is not None
    assert order.side == "sell"
    assert eng.last_stop_exit is not None
    assert eng.last_stop_exit["kind"] == "hard"


def test_no_stop_when_flat():
    cfg = RiskConfig(atr_stop_mult=2.0, atr_period=2)
    eng = RiskEngine(lambda h: None, cfg, initial_capital=10_000.0)
    assert eng([_bar(0, 100.0, 101.0, 99.0)]) is None
    assert eng.last_stop_exit is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest core/tests/test_engine_stops.py -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'atr_stop_mult'`

- [ ] **Step 3a: Add stop config fields to `RiskConfig`**

In `core/risk/guardrails.py`, inside the `RiskConfig` dataclass after the sizing params (line 37 `base_position_usd`), add:

```python
    # ── Stop-loss (exit rules — the WS1 drawdown lever) ───────────────────────
    atr_stop_mult: float = 2.0       # hard stop at entry - mult*ATR; 0 disables
    atr_trail_mult: float = 3.0      # trailing stop at high_water - mult*ATR; 0 disables
    atr_period: int = 14             # ATR lookback in bars
```

- [ ] **Step 3b: Track high-water mark in `_PosTracker`**

In `core/risk/engine.py`, add a field to `_PosTracker` (after `avg_entry: float = 0.0`, line 36):

```python
    high_water: float = 0.0   # peak price seen since the position opened (trailing stop)
```

And at the end of `apply_buy` (after line 62 `self.cash -= size_usd`) reset the high-water on a fresh open and update it:

```python
        self.high_water = max(self.high_water, price) if self.units > units else price
```

In `apply_sell`, when the position is fully closed reset it — after line 68 (`self.units = max(...)`):

```python
        if self.units <= 0.0:
            self.high_water = 0.0
```

- [ ] **Step 3c: Enforce the stop at the top of `RiskEngine.__call__`**

In `core/risk/engine.py`, add the import near the top (after line 22):

```python
from risk.stops import compute_atr, hard_stop_level, trailing_stop_level, stop_triggered
```

Initialize the attribute in `RiskEngine.__init__` (after `self._pos = ...`, line 97):

```python
        self.last_stop_exit: Optional[dict] = None
```

At the very start of `__call__`, after `price = bar.close` (line 102), insert the stop check and high-water update:

```python
        self.last_stop_exit = None

        # ── Hard + trailing ATR stop (forced exit BEFORE the inner strategy) ──
        if self._pos.units > 0.0:
            self._pos.high_water = max(self._pos.high_water, bar.high)
            atr = compute_atr(history, self._config.atr_period)
            hard = hard_stop_level(self._pos.avg_entry, atr, self._config.atr_stop_mult)
            trail = trailing_stop_level(self._pos.high_water, atr, self._config.atr_trail_mult)
            stop = max(hard, trail)   # whichever is higher (tighter) governs
            if stop_triggered(bar.low, stop):
                exit_usd = self._pos.units * price
                self._pos.apply_sell(exit_usd, price)
                self.last_stop_exit = {
                    "kind": "trail" if trail >= hard and trail > 0 else "hard",
                    "stop": round(stop, 6), "price": round(price, 6),
                }
                return Order(side="sell", size_usd=exit_usd,
                             symbol="ETH", timestamp=bar.timestamp)
```

> Note: `symbol="ETH"` is a placeholder consistent with the engine's existing `symbol="BNB"` placeholder at line 116; the live loop overrides the symbol on its own order. The forced-exit size equals the full open position so a stop always flattens.

- [ ] **Step 4: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest core/tests/test_engine_stops.py core/tests/test_stops.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Run the existing risk suite to confirm no regression**

Run: `core/.venv/bin/python -m pytest core/tests/ -k "risk or engine or guardrail" -v`
Expected: PASS (all existing tests still green)

- [ ] **Step 6: Commit**

```bash
git add core/risk/guardrails.py core/risk/engine.py core/tests/test_engine_stops.py
git commit -m "feat(risk): hard ATR + trailing stop enforced in RiskEngine (sim/live parity)"
```

---

### Task 3: Emit a RiskGuard event when a stop fires

**Files:**
- Modify: `agent/loop.py` (`run_cycle`, after the decision line ~255)

**Interfaces:**
- Consumes: `RiskEngine.last_stop_exit` (Task 2); `AgentEvent`, `KIND_CONTROL` from `agent.graph.contracts`; `self.bridge.emit_event` (existing, used at `agent/loop.py:373`).
- Produces: a `RiskGuard` `control` event on the Agent Activity Channel whenever a stop fires, so it surfaces in the Phase 2 notification panel.

- [ ] **Step 1: Add the emit after the strategy call**

In `agent/loop.py`, immediately after `order = self.strategy(history)` (line 255), insert:

```python
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
```

- [ ] **Step 2: Verify the loop still imports and the smoke test passes**

Run: `core/.venv/bin/python -m pytest agent/tests/ -k "loop or smoke" -v`
Expected: PASS (existing loop tests still green; the new branch is inert unless a stop fires)

- [ ] **Step 3: Commit**

```bash
git add agent/loop.py
git commit -m "feat(agent): emit RiskGuard channel event when an ATR stop fires"
```

---

### Task 4: Walk-forward OOS validation of the stops

**Files:**
- Create: `core/tests/test_stops_walkforward.py`

**Interfaces:**
- Consumes: `run_walk_forward` (existing in `core/backtest/`), `RiskEngine`, `RiskConfig`. (If the walk-forward entry point differs, the implementer greps `core/backtest/` for the public function and adapts the import — do not invent a new harness.)
- Produces: an OOS assertion that enabling stops does not worsen out-of-sample max-drawdown versus stops-disabled on the same bars. This is a guard test, not a tuning loop — it must read OOS only.

- [ ] **Step 1: Write the OOS guard test**

```python
# core/tests/test_stops_walkforward.py
"""
OOS guard: stops must not worsen out-of-sample max-drawdown. Anti-overfitting
rule (locked decision #7) — we assert on OOS, never select params on in-sample.
"""
import pytest
from backtest.engine import Bar, run_backtest
from risk.engine import RiskEngine
from risk.guardrails import RiskConfig


def _ramp_then_crash(n: int = 120) -> list[Bar]:
    bars: list[Bar] = []
    price = 100.0
    for i in range(n):
        price = price * (1.01 if i < n // 2 else 0.98)   # rally then sustained drawdown
        bars.append(Bar(timestamp=i * 86_400_000, open=price, high=price * 1.01,
                        low=price * 0.99, close=price, volume=1.0))
    return bars


def _always_long(history):
    from backtest.engine import Order
    return Order(side="buy", size_usd=1000.0, symbol="ETH", timestamp=history[-1].timestamp) \
        if len(history) == 1 else None


@pytest.mark.unit
def test_stops_do_not_worsen_oos_drawdown():
    bars = _ramp_then_crash()
    no_stop = RiskEngine(_always_long, RiskConfig(atr_stop_mult=0.0, atr_trail_mult=0.0,
                         max_position_pct=1.0, max_open_exposure_pct=1.0), 10_000.0)
    with_stop = RiskEngine(_always_long, RiskConfig(atr_stop_mult=2.0, atr_trail_mult=3.0,
                           max_position_pct=1.0, max_open_exposure_pct=1.0), 10_000.0)

    dd_off = run_backtest(bars, no_stop).metrics.get("max_drawdown", 0.0)
    dd_on = run_backtest(bars, with_stop).metrics.get("max_drawdown", 0.0)

    # max_drawdown is negative; "not worse" means on >= off (closer to zero).
    assert dd_on >= dd_off
```

- [ ] **Step 2: Run it**

Run: `core/.venv/bin/python -m pytest core/tests/test_stops_walkforward.py -v`
Expected: PASS — the stop cuts the crash-half drawdown, so `dd_on >= dd_off`.

- [ ] **Step 3: Commit**

```bash
git add core/tests/test_stops_walkforward.py
git commit -m "test(risk): OOS guard — ATR stops never worsen max-drawdown"
```

---

# Phase 2 — Notification Panel + Toast Feed

### Task 5: Event severity mapping

**Files:**
- Create: `web/src/lib/eventSeverity.ts`
- Test: covered by the panel render (no separate test runner for `web/`; verify by `bun run build`).

**Interfaces:**
- Produces: `type Severity = "info" | "trade" | "risk" | "critical"` and `eventSeverity(e: { agent: string; kind: string; headline: string }): Severity`. The panel and the toast router both consume it (single source of truth — DRY).

- [ ] **Step 1: Write the module**

```ts
// web/src/lib/eventSeverity.ts
export type Severity = "info" | "trade" | "risk" | "critical";

const RISK_AGENTS = new Set(["RiskGuard", "Risk Officer", "Autopilot"]);

/** Single source of truth for how an agent_events row maps to a UI severity tier. */
export function eventSeverity(e: {
  agent: string;
  kind: string;
  headline: string;
}): Severity {
  const h = e.headline.toLowerCase();
  if (h.includes("floor hit") || h.includes("kill switch") || h.includes("halt")) {
    return "critical";
  }
  if (h.includes("stop") || h.includes("circuit") || RISK_AGENTS.has(e.agent)) {
    return "risk";
  }
  if (e.kind === "action" || h.includes("filled") || h.includes("trade")) {
    return "trade";
  }
  return "info";
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  info: "Info",
  trade: "Trade",
  risk: "Risk",
  critical: "Critical",
};
```

- [ ] **Step 2: Type-check**

Run: `cd web && bun run build`
Expected: build succeeds (module compiles; unused until the panel imports it).

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/eventSeverity.ts
git commit -m "feat(web): event severity tier mapping for notifications"
```

---

### Task 6: NotificationPanel component

**Files:**
- Create: `web/src/components/NotificationPanel.tsx`

**Interfaces:**
- Consumes: `api.agentEvents.recent` (existing query, `convex/agentEvents.ts`), `eventSeverity` + `SEVERITY_LABEL` (Task 5), `Panel` (`web/src/components/Panel.tsx`), `ts` formatter (`web/src/lib/formatters.ts`), `cn` (`@/lib/utils`).
- Produces: `export function NotificationPanel({ limit }: { limit?: number })` — a reactive, severity-filterable list of recent events.

- [ ] **Step 1: Write the component**

```tsx
// web/src/components/NotificationPanel.tsx
import { useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { ts } from "../lib/formatters";
import { cn } from "@/lib/utils";
import { eventSeverity, SEVERITY_LABEL, type Severity } from "../lib/eventSeverity";

const TIER_STYLE: Record<Severity, string> = {
  info: "text-muted-fg border-border bg-bg/50",
  trade: "text-cyan border-cyan/30 bg-cyan/10",
  risk: "text-amber border-amber/30 bg-amber/10",
  critical: "text-red border-red/30 bg-red/10",
};

const FILTERS: Array<Severity | "all"> = ["all", "critical", "risk", "trade", "info"];

export function NotificationPanel({ limit = 50 }: { limit?: number }) {
  const events = useQuery(api.agentEvents.recent, { limit });
  const [filter, setFilter] = useState<Severity | "all">("all");

  const rows = (events ?? [])
    .map((e) => ({ ...e, sev: eventSeverity(e) }))
    .filter((e) => filter === "all" || e.sev === filter);

  return (
    <Panel
      label="Notifications"
      tick="green"
      action={
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded border transition-colors cursor-pointer",
                filter === f
                  ? "text-green border-green/40 bg-green/10"
                  : "text-muted-fg border-border hover:border-green/30",
              )}
            >
              {f === "all" ? "all" : SEVERITY_LABEL[f]}
            </button>
          ))}
        </div>
      }
    >
      {events === undefined ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full bg-elevated rounded-lg" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="font-mono text-[12px] text-muted-fg py-2">// no notifications</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {rows.map((e) => (
            <div key={e._id} className={cn("rounded-lg border px-3 py-2", TIER_STYLE[e.sev])}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[9px] font-bold uppercase tracking-widest flex-shrink-0">
                  {SEVERITY_LABEL[e.sev]}
                </span>
                <span className="font-display text-[11px] font-bold flex-shrink-0">{e.agent}</span>
                <span className="font-mono text-[10px] text-muted-fg/60 ml-auto flex-shrink-0">
                  {ts(e.ts_ms)}
                </span>
              </div>
              <p className="font-mono text-[12px] text-text mt-1 leading-snug">{e.headline}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
```

> If `text-amber` is not a defined token, the implementer greps `web/src/globals.css` for an existing warning colour (e.g. `yellow`/`gold`) and uses it — do not introduce a new palette token.

- [ ] **Step 2: Type-check**

Run: `cd web && bun run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/NotificationPanel.tsx
git commit -m "feat(web): NotificationPanel — severity-filterable agent event feed"
```

---

### Task 7: Notifications view + nav entry + debounced toast routing

**Files:**
- Create: `web/src/views/NotificationsView.tsx`
- Modify: `web/src/components/SideNav.tsx` (`View` union + nav items)
- Modify: `web/src/App.tsx` (render view + generalized toast routing)

**Interfaces:**
- Consumes: `NotificationPanel` (Task 6), `eventSeverity` (Task 5), existing `View` switch in `App.tsx:220-228`, existing `events` query already present at `App.tsx:168`.
- Produces: a `notifications` route; high-priority new events (`risk`/`critical`) raise a Sonner toast once each (deduped by `_id`).

- [ ] **Step 1: Create the view**

```tsx
// web/src/views/NotificationsView.tsx
import { NotificationPanel } from "../components/NotificationPanel";

export function NotificationsView() {
  return (
    <div className="p-3 sm:p-4">
      <NotificationPanel limit={100} />
    </div>
  );
}
```

- [ ] **Step 2: Add `notifications` to the `View` union + nav**

In `web/src/components/SideNav.tsx`, find the `View` type union and the nav-items array. Add `"notifications"` to the union and a nav item (match the existing item shape — icon from `lucide-react`, e.g. `Bell`):

```tsx
// in the View union:
  | "notifications"
// in the nav items array (alongside the existing { id: "logs", ... }):
  { id: "notifications", label: "Alerts", icon: Bell },
```

Add `Bell` to the existing `lucide-react` import at the top of the file.

- [ ] **Step 3: Render the view in `App.tsx`**

In `web/src/App.tsx`, import the view (after line 12):

```tsx
import { NotificationsView } from "./views/NotificationsView";
```

Add a case to the `renderView` switch (after the `logs` case, line 226):

```tsx
      case "notifications": return <NotificationsView />;
```

- [ ] **Step 4: Generalized debounced toast routing**

In `web/src/App.tsx`, change the events query limit so the router sees more rows (line 168):

```tsx
  const events = useQuery(api.agentEvents.recent, { limit: 20 });
```

Add a ref + effect below the existing equity-floor effect (after line 198). This dedupes by event `_id` so each high-priority event toasts exactly once:

```tsx
  const seenEventIds = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!events) return;
    // Prime on first load so historical rows don't toast in a burst.
    if (seenEventIds.current.size === 0) {
      for (const e of events) seenEventIds.current.add(e._id);
      return;
    }
    for (const e of [...events].reverse()) {
      if (seenEventIds.current.has(e._id)) continue;
      seenEventIds.current.add(e._id);
      const sev = eventSeverity(e);
      if (sev === "critical") toast.error(e.headline, { duration: 8000 });
      else if (sev === "risk") toast.warning(e.headline, { duration: 5000 });
      else if (sev === "trade") toast.success(e.headline, { duration: 3000 });
    }
  }, [events]);
```

Add the imports at the top of `App.tsx` (extend line 1 and line 15 area):

```tsx
import { eventSeverity } from "./lib/eventSeverity";
```

`useRef` is already imported (line 1). `toast.warning` is provided by Sonner with `richColors` (already set at line 263).

> Remove the now-redundant equity-floor-only effect (lines 185-198) ONLY if the generalized router fully covers it — the floor event maps to `critical`, so it does. Delete it to avoid a double toast; keep `lastFloorHalt` state removal consistent.

- [ ] **Step 5: Type-check + build**

Run: `cd web && bun run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add web/src/views/NotificationsView.tsx web/src/components/SideNav.tsx web/src/App.tsx
git commit -m "feat(web): notifications view + nav + debounced toast routing (Telegram-optional cockpit)"
```

---

# Phase 3 — X/KOL Auto-Trade (deterministic, risk-gated)

### Task 8: Add the Scout agent to the roster

**Files:**
- Modify: `agent/graph/contracts.py` (roster constants + `AGENTS`)
- Test: `agent/tests/test_kol_intent.py` (created in Task 9 also exercises this)

**Interfaces:**
- Produces: `SCOUT = "Scout"` added to `AGENTS` so `AgentEvent(agent="Scout", ...)` passes the `__post_init__` validation (`agent/graph/contracts.py:135`).

- [ ] **Step 1: Add the constant and include it in AGENTS**

In `agent/graph/contracts.py`, after `RISK_GUARD = "RiskGuard" ...` (line 74) add:

```python
SCOUT = "Scout"   # X/KOL watcher — emits social-trigger events, never a Tier-0 decision
```

Extend the `AGENTS` frozenset (line 88) to include it:

```python
AGENTS = frozenset({ORCHESTRATOR, USER, SUPERVISOR, RISK_GUARD, SCOUT}) | TIER0_AGENTS | TIER1_AGENTS
```

Add `"SCOUT"` to `__all__` near `RISK_GUARD` (line 55).

- [ ] **Step 2: Quick verification**

Run: `core/.venv/bin/python -c "from agent.graph.contracts import AgentEvent, SCOUT, KIND_OBSERVATION; AgentEvent(agent=SCOUT, kind=KIND_OBSERVATION, headline='x'); print('ok')"`
Expected: prints `ok` (no ValueError).

- [ ] **Step 3: Commit**

```bash
git add agent/graph/contracts.py
git commit -m "feat(agent): add Scout agent to the roster (X/KOL watcher)"
```

---

### Task 9: KOL intent mapping (pure, allowlist + eligibility filter)

**Files:**
- Create: `agent/social/kol_intent.py`
- Test: `agent/tests/test_kol_intent.py`

**Interfaces:**
- Consumes: `SentimentReading` (`agent/social/schema.py`), `TOKEN_ALLOWLIST` (`risk/guardrails.py`).
- Produces:
  - `@dataclass(frozen=True) KolIntent` with fields `symbol: str`, `action: str` (`"open_long" | "reduce" | "none"`), `confidence: float`, `reason: str`.
  - `kol_intent(reading: SentimentReading, *, holds_symbol: bool, score_open: float = 0.35, score_close: float = -0.35, min_conf: float = 0.5) -> KolIntent`.
  - Rules: ineligible symbol → `none`. Bullish (`score >= score_open`) and `confidence >= min_conf` → `open_long`. Bearish (`score <= score_close`) and `holds_symbol` → `reduce`. Else `none`.

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/test_kol_intent.py
from agent.social.schema import SentimentReading
from agent.social.kol_intent import kol_intent, KolIntent


def _reading(symbol: str, score: float, conf: float) -> SentimentReading:
    return SentimentReading(symbol=symbol, score=score, confidence=conf, n_posts=5)


def test_bullish_eligible_opens_long_when_flat():
    out = kol_intent(_reading("ETH", 0.6, 0.8), holds_symbol=False)
    assert out.action == "open_long"
    assert out.symbol == "ETH"


def test_bullish_below_confidence_is_none():
    assert kol_intent(_reading("ETH", 0.6, 0.2), holds_symbol=False).action == "none"


def test_bearish_reduces_only_when_held():
    assert kol_intent(_reading("CAKE", -0.7, 0.9), holds_symbol=True).action == "reduce"
    assert kol_intent(_reading("CAKE", -0.7, 0.9), holds_symbol=False).action == "none"


def test_ineligible_token_never_trades():
    # BTC is NOT in the eligible allowlist — must be inert regardless of hype.
    assert kol_intent(_reading("BTC", 0.9, 0.9), holds_symbol=False).action == "none"


def test_neutral_is_none():
    assert kol_intent(_reading("ETH", 0.0, 0.9), holds_symbol=True).action == "none"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest agent/tests/test_kol_intent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.social.kol_intent'`

- [ ] **Step 3: Write the implementation**

```python
# agent/social/kol_intent.py
"""
KOL stance -> trade intent. PURE and deterministic (no LLM, no I/O): it maps the
existing deterministic SentimentReading into one of three bounded actions, gated
by the eligible-token allowlist and the spot-long-only scoring rule.

  bullish + eligible + flat   -> open_long   (a scored twak swap long)
  bearish + eligible + held   -> reduce      (capital preservation; never a short)
  everything else             -> none

This is the seam the loop's _apply_kol_signal overlay consumes; the overlay still
runs every resulting order through check_guardrails, so this layer never sizes.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent.social.schema import SentimentReading
from risk.guardrails import TOKEN_ALLOWLIST


@dataclass(frozen=True)
class KolIntent:
    symbol: str
    action: str        # "open_long" | "reduce" | "none"
    confidence: float
    reason: str


def kol_intent(
    reading: SentimentReading,
    *,
    holds_symbol: bool,
    score_open: float = 0.35,
    score_close: float = -0.35,
    min_conf: float = 0.5,
) -> KolIntent:
    sym = reading.symbol.upper()
    if sym not in TOKEN_ALLOWLIST:
        return KolIntent(sym, "none", reading.confidence, "token not in eligible allowlist")
    if reading.confidence < min_conf:
        return KolIntent(sym, "none", reading.confidence, "confidence below threshold")
    if reading.score >= score_open:
        return KolIntent(sym, "open_long", reading.confidence,
                         f"bullish KOL score {reading.score:+.2f}")
    if reading.score <= score_close and holds_symbol:
        return KolIntent(sym, "reduce", reading.confidence,
                         f"bearish KOL score {reading.score:+.2f} — de-risk held long")
    return KolIntent(sym, "none", reading.confidence, "no actionable stance")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest agent/tests/test_kol_intent.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/social/kol_intent.py agent/tests/test_kol_intent.py
git commit -m "feat(social): deterministic KOL stance->intent mapping (allowlist + long-only)"
```

---

### Task 10: Live X ingest → sentiment_state writer

**Files:**
- Create: `agent/social/live.py`

**Interfaces:**
- Consumes: `ingest`, `load_watchlist` (`agent/social/ingest.py`), `SentimentReading.as_row()` (`agent/social/schema.py`), `TOKEN_ALLOWLIST` (`risk/guardrails.py`), the Convex `social:setSentiment` mutation (`convex/social.ts:29`) via the existing `ConvexBridge` HTTP path (the implementer greps `agent/convex_bridge.py` for the existing `set_sentiment`/mutation helper; if absent, reuse the generic mutation caller the bridge already uses for `setSentiment`).
- Produces: `run_live_ingest(bridge, *, watchlist_path: str | None = None, limit: int = 50) -> dict[str, SentimentReading]` — runs one ingest pass, writes `sentiment_state` for ELIGIBLE symbols only, returns the readings. Failure-isolated: a dead source or a write error never raises.

- [ ] **Step 1: Write the module**

```python
# agent/social/live.py
"""
Live social ingest → Convex sentiment_state, for the KOL auto-trade path.

One pass: load the watchlist (Convex social_sources if present, else the JSON
file), fan out across adapters (existing ingest()), then write one sentiment_state
row per ELIGIBLE symbol so the loop's _inject_sentiment (S3) and _apply_kol_signal
overlay can read it. Eligible-only: an ineligible token can never reach execution,
so we don't even persist its reading into the trade path.

Failure-isolated (§9.3): never raises — social is advisory/off the hot path.
"""
from __future__ import annotations

from pathlib import Path

from agent.social.ingest import ingest, load_watchlist
from agent.social.schema import SentimentReading
from risk.guardrails import TOKEN_ALLOWLIST

_DEFAULT_WATCHLIST = Path(__file__).resolve().parent / "watchlist.example.json"


def run_live_ingest(bridge, *, watchlist_path: str | None = None,
                    limit: int = 50) -> dict[str, SentimentReading]:
    try:
        path = Path(watchlist_path) if watchlist_path else _DEFAULT_WATCHLIST
        symbols, specs = load_watchlist(path)
        # Only ingest/persist eligible symbols into the trade path.
        symbols = [s for s in symbols if s.upper() in TOKEN_ALLOWLIST]
        if not symbols:
            return {}
        result = ingest(symbols, specs, limit=limit)
    except Exception:  # noqa: BLE001 — ingest must never crash the caller
        return {}

    for sym, reading in result.readings.items():
        if sym.upper() not in TOKEN_ALLOWLIST:
            continue
        try:
            bridge.set_sentiment(**reading.as_row())
        except Exception:  # noqa: BLE001 — a bad write must not sink the pass
            pass
    return result.readings
```

> The implementer confirms `bridge.set_sentiment(**row)` exists in `agent/convex_bridge.py` (the loop already reads sentiment via `bridge.get_sentiment_state`). If the writer method has a different name, match it; if missing, add a thin `set_sentiment` that calls the `social:setSentiment` mutation with the same arg names as `convex/social.ts:29`.

- [ ] **Step 2: Smoke-test the import + eligibility filter offline**

```bash
core/.venv/bin/python -c "
from agent.social.live import run_live_ingest
class _B:
    def set_sentiment(self, **k): print('wrote', k['symbol'])
out = run_live_ingest(_B(), limit=5)
print('readings:', sorted(out))
"
```
Expected: no exception; prints whatever eligible symbols the default watchlist yields (may be empty offline — that is the failure-isolated path working).

- [ ] **Step 3: Commit**

```bash
git add agent/social/live.py
git commit -m "feat(social): live X/KOL ingest -> sentiment_state (eligible symbols only)"
```

---

### Task 11: KOL auto-trade overlay in DecisionLoop

**Files:**
- Modify: `agent/loop.py` (`__init__` adds a flag; `run_cycle` calls the overlay; new `_apply_kol_signal` method)
- Test: `agent/tests/test_kol_overlay.py`

**Interfaces:**
- Consumes: `kol_intent`, `KolIntent` (Task 9); `check_guardrails`, `check_max_exposure`, `RiskConfig` (`risk/guardrails.py`); `bridge.get_sentiment_state` (existing); `self.executor.execute`, `self._handle_execution` (existing); `AgentEvent`, `KIND_ACTION` from contracts; `SCOUT` (Task 8).
- Produces: a live-only overlay `_apply_kol_signal(self, bar, cycle_id) -> Optional[CycleResult]`. When enabled and a high-conviction eligible reading yields `open_long` (while flat) or `reduce` (while held), it builds an order, runs it through `check_guardrails` + (for buys) `check_max_exposure`, executes via the same executor, emits a `Scout` `action` event, and returns a finalised `CycleResult`. Otherwise returns `None`. Disabled (`enforce_kol=False`) or offline → `None` (parity preserved). Gated `kol_enabled` defaults `False`; the systemd service flips `KOL_AUTOTRADE=1`.

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/test_kol_overlay.py
from backtest.engine import Bar
from agent.loop import DecisionLoop


def _bar(ts=0, price=100.0):
    return Bar(timestamp=ts, open=price, high=price * 1.01, low=price * 0.99,
               close=price, volume=1.0)


class _Bridge:
    def __init__(self, reading):
        self._reading = reading
        self.events = []
    def get_sentiment_state(self, symbol):
        return self._reading
    def emit_event(self, ev):
        self.events.append(ev)
    def audit(self, *a, **k): pass


class _Executor:
    def __init__(self):
        self.calls = []
    def execute(self, order, bar, idempotency_key=None):
        self.calls.append(order)
        from agent.executor import ExecutionReport
        from backtest.engine import Fill
        fill = Fill(order=order, fill_price=bar.close, fee_usd=0.0, gas_usd=0.0, slippage_usd=0.0)
        return ExecutionReport(status="FILLED", reason="ok", fill=fill, tx_hash="0xabc", order=order)


def _loop(reading, *, enforce_kol=True):
    loop = DecisionLoop.__new__(DecisionLoop)          # bypass full __init__ wiring
    loop.symbol = "ETH"
    loop.mode = "paper"
    loop.bridge = _Bridge(reading)
    loop.executor = _Executor()
    loop.base_position_usd = 100.0
    loop.kol_enabled = enforce_kol
    loop._kol_min_conf = 0.5
    return loop


def test_bullish_kol_opens_long_through_executor():
    reading = {"symbol": "ETH", "score": 0.7, "confidence": 0.9, "ts_ms": 0, "n_posts": 6}
    loop = _loop(reading)
    # Stub the bits _apply_kol_signal calls on a real loop:
    loop.ledger = type("L", (), {"open_exposure": lambda self, p: 0.0,
                                 "mark": lambda self, p: 1000.0})()
    handled = {}
    loop._handle_execution = lambda *a, **k: ("allow", "ok", "t1")
    loop._finalise = lambda *a, **k: handled.setdefault("done", True)
    out = loop._apply_kol_signal(_bar(), "ETH-0")
    assert loop.executor.calls and loop.executor.calls[0].side == "buy"
    assert any(ev.agent == "Scout" for ev in loop.bridge.events)


def test_disabled_overlay_is_noop():
    loop = _loop({"symbol": "ETH", "score": 0.9, "confidence": 0.9, "ts_ms": 0, "n_posts": 9},
                 enforce_kol=False)
    assert loop._apply_kol_signal(_bar(), "ETH-0") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `core/.venv/bin/python -m pytest agent/tests/test_kol_overlay.py -v`
Expected: FAIL with `AttributeError: 'DecisionLoop' object has no attribute '_apply_kol_signal'`

- [ ] **Step 3: Add the `kol_enabled` flag to `__init__`**

In `agent/loop.py`, in `DecisionLoop.__init__`, add a parameter (near `enforce_activity_floor`, line 70) and store it. Add to the signature:

```python
        kol_enabled: bool = False,
        kol_min_conf: float = 0.5,
```

And in the body (near line 126):

```python
        self.kol_enabled = kol_enabled
        self._kol_min_conf = kol_min_conf
```

- [ ] **Step 4: Write the overlay method**

Add this method to `DecisionLoop` (place it near `_apply_autopilot`, after line 640):

```python
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
                gr = check_guardrails(symbol=self.symbol, size_usd=size, daily_loss_pct=0.0,
                                      consecutive_losses=0, capital=equity, config=cfg)
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
```

- [ ] **Step 5: Wire the overlay into `run_cycle`**

In `agent/loop.py`, in `run_cycle`, after the autopilot intervention block (after line 252) and before `order = self.strategy(history)` (line 255), insert:

```python
        # ── KOL auto-trade overlay (live-only; flat→open / held→reduce) ──────
        kol_intervention = self._apply_kol_signal(bar, cycle_id)
        if kol_intervention is not None:
            return kol_intervention
```

- [ ] **Step 6: Run test to verify it passes**

Run: `core/.venv/bin/python -m pytest agent/tests/test_kol_overlay.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Run the full agent + core suites for regressions**

Run: `core/.venv/bin/python -m pytest core/tests/ agent/tests/ -q`
Expected: PASS (no regressions; parity tests still green because the overlay is `None` when `kol_enabled` is False, which is the default the sim uses).

- [ ] **Step 8: Commit**

```bash
git add agent/loop.py agent/tests/test_kol_overlay.py
git commit -m "feat(agent): KOL auto-trade overlay — deterministic, allowlist + risk-gated, live-only"
```

---

### Task 12: Wire live ingest into the runtime + config flag

**Files:**
- Modify: `agent/runtime.py` (or wherever `DecisionLoop` is constructed — grep for `DecisionLoop(` and `enforce_activity_floor=`)

**Interfaces:**
- Consumes: `run_live_ingest` (Task 10), env `KOL_AUTOTRADE` + `KOL_MIN_CONF`.
- Produces: when `KOL_AUTOTRADE=1`, the runtime constructs `DecisionLoop(..., kol_enabled=True, kol_min_conf=float(os.environ.get("KOL_MIN_CONF", "0.5")))` and calls `run_live_ingest(bridge)` once per cycle cadence before `loop.run_cycle` (or on the existing feed tick). Default off → no behaviour change.

- [ ] **Step 1: Read the construction site**

Run: `grep -n "DecisionLoop(\|enforce_activity_floor\|run_forever" agent/runtime.py`
Expected: locate where the loop is built and driven.

- [ ] **Step 2: Pass the KOL flags at construction**

At the `DecisionLoop(...)` call, add (mirroring how `enforce_activity_floor` is read from env elsewhere):

```python
        kol_enabled=os.environ.get("KOL_AUTOTRADE", "0") == "1",
        kol_min_conf=float(os.environ.get("KOL_MIN_CONF", "0.5")),
```

- [ ] **Step 3: Refresh sentiment before each cycle when KOL is on**

Where the runtime drives cycles (the `run_forever`/feed loop), add a guarded pre-cycle ingest when enabled. If the runtime uses `loop.run_forever(...)`, instead schedule it in the existing per-cycle path; the simplest non-invasive option is a wrapper:

```python
    if os.environ.get("KOL_AUTOTRADE", "0") == "1":
        from agent.social.live import run_live_ingest
        # called once per cadence tick, before run_cycle; failure-isolated inside.
        run_live_ingest(bridge)
```

> Keep this OUTSIDE the hot decision path — it only refreshes `sentiment_state`; the deterministic decision still happens inside `run_cycle`. If `run_forever` owns the cadence with no injectable hook, the implementer adds a `pre_cycle: Callable | None = None` param to `run_forever` and calls it each tick — minimal and additive.

- [ ] **Step 4: Verify the runtime still boots in paper mode (KOL off)**

Run: `KOL_AUTOTRADE=0 core/.venv/bin/python -m pytest agent/tests/ -k "runtime or smoke" -v`
Expected: PASS (default path unchanged).

- [ ] **Step 5: Commit**

```bash
git add agent/runtime.py
git commit -m "feat(agent): KOL_AUTOTRADE env flag — wire live ingest + overlay into runtime"
```

---

# Phase 4 — Sponsor-Depth Legibility

### Task 13: Sponsor-depth doc

**Files:**
- Create: `docs/SPONSOR_DEPTH.md`

**Interfaces:**
- Produces: a judge-facing map from each sponsor capability to the real code path + a live artifact. No code dependency.

- [ ] **Step 1: Write the doc**

```markdown
# Sponsor Integration Depth

Three sponsor capabilities, each mapped to the real code path and a live artifact
a judge can verify in the cockpit.

## CMC Agent Hub — data & signals
- Signals S1–S4 derive from CMC OHLCV / funding+OI / social / on-chain flow:
  `core/signals/{momentum,derivatives,sentiment,onchain}.py`.
- x402 micropayments on every metered CMC call: `agent/x402_provider.py`.
- Live social/KOL ingest → `sentiment_state` → S3: `agent/social/live.py`,
  `agent/loop.py:_inject_sentiment`.
- **Live artifact:** the Notifications panel shows `Scout` events when a KOL
  reading triggers; the regime/signal panels show S1–S4 scores per cycle.

## Trust Wallet Agent Kit (TWAK) — self-custody signing
- Every swap is signed via TWAK; zero raw keys in code/logs: `agent/twak_cli.py`.
- Auth via `TW_ACCESS_ID` + `TW_HMAC_SECRET`; wallet password via env only.
- **Live artifact:** Sponsors view shows the last TWAK-signed tx hash linking to
  BscScan; the wallet-balance panel reads the TWAK-managed wallet.

## BNB AI Agent SDK — on-chain execution
- Spot longs execute as `twak swap` (the only scored path): `agent/executor.py`.
- On-chain receipt is the ledger source of truth (real fill price, real gas):
  `agent/loop.py:_handle_execution`, `convex/ledger.ts`.
- **Live artifact:** Trade History + Sponsors view show fill price, gas paid, and
  the BscScan tx for each on-chain fill.
```

- [ ] **Step 2: Commit**

```bash
git add docs/SPONSOR_DEPTH.md
git commit -m "docs: sponsor integration depth map (CMC / TWAK / BNB SDK)"
```

---

### Task 14: Sponsors view in the cockpit

**Files:**
- Create: `web/src/views/SponsorsView.tsx`
- Modify: `web/src/components/SideNav.tsx` (`View` union + nav item)
- Modify: `web/src/App.tsx` (render the view)

**Interfaces:**
- Consumes: existing reactive queries — `api.trades.recent` (last on-chain fill + tx), `api.walletState.get` (TWAK-managed wallet), `api.ledger.*` (cumulative gas/fees). The implementer greps `convex/` for exact query names (`trades.ts`, `walletState.ts`, `ledger.ts`) and matches signatures.
- Produces: a `sponsors` route showing three cards (CMC / TWAK / BNB SDK), each with a live artifact.

- [ ] **Step 1: Create the view**

```tsx
// web/src/views/SponsorsView.tsx
import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { usd } from "../lib/formatters";

export function SponsorsView() {
  const trades = useQuery(api.trades.recent, { limit: 1 });
  const wallet = useQuery(api.walletState.get);
  const last = trades?.[0];
  const tx = last?.tx_hash ? `https://bscscan.com/tx/${last.tx_hash}` : null;

  return (
    <div className="p-3 sm:p-4 grid gap-3 sm:grid-cols-3">
      <Panel label="CMC — Data & Signals" tick="cyan">
        <p className="font-mono text-[12px] text-text leading-relaxed">
          S1–S4 from CMC OHLCV · funding/OI · social · flow. x402 micropayments per
          metered call. Live KOL ingest feeds S3.
        </p>
      </Panel>

      <Panel label="TWAK — Self-Custody" tick="green">
        <p className="font-mono text-[12px] text-text leading-relaxed">
          Every swap signed via Trust Wallet Agent Kit. Keys never in code.
        </p>
        {wallet && (
          <p className="font-mono text-[11px] text-muted-fg mt-2">
            Wallet: {usd(wallet.total_usd ?? 0)} managed
          </p>
        )}
      </Panel>

      <Panel label="BNB SDK — Execution" tick="amber">
        <p className="font-mono text-[12px] text-text leading-relaxed">
          Spot longs as <code>twak swap</code>; on-chain receipt is ledger truth.
        </p>
        {last ? (
          <div className="font-mono text-[11px] text-muted-fg mt-2">
            Last fill: {last.side} {last.symbol} @ {usd(last.fill_price)}
            {tx && (
              <a href={tx} target="_blank" rel="noopener noreferrer"
                 className="block text-green/70 hover:text-green mt-1">
                TX ↗ BscScan
              </a>
            )}
          </div>
        ) : (
          <p className="font-mono text-[11px] text-muted-fg mt-2">// no fills yet</p>
        )}
      </Panel>
    </div>
  );
}
```

> Match the `Panel` `tick` prop's accepted values (grep `web/src/components/Panel.tsx`); if `amber` is not accepted, use an accepted accent.

- [ ] **Step 2: Add `sponsors` to the `View` union + nav + render**

In `web/src/components/SideNav.tsx`: add `| "sponsors"` to the `View` union and a nav item `{ id: "sponsors", label: "Sponsors", icon: Award }` (add `Award` to the `lucide-react` import).

In `web/src/App.tsx`: import `SponsorsView` and add `case "sponsors": return <SponsorsView />;` to the `renderView` switch.

- [ ] **Step 3: Build**

Run: `cd web && bun run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/views/SponsorsView.tsx web/src/components/SideNav.tsx web/src/App.tsx
git commit -m "feat(web): Sponsors view — live CMC/TWAK/BNB-SDK depth artifacts"
```

---

## Final Verification

- [ ] **Run the full Python suite:** `core/.venv/bin/python -m pytest core/tests/ agent/tests/ -q` → all green (parity tests pass because all new live overlays default off).
- [ ] **Build the web app:** `cd web && bun run build` → succeeds.
- [ ] **Confirm defaults are safe:** `KOL_AUTOTRADE` unset → KOL overlay inert; `atr_stop_mult`/`atr_trail_mult` defaults active (stops ON by default — this is the intended drawdown protection); notification panel + toasts live with no backend change.
- [ ] **Restart the service to pick up changes:** `systemctl restart alien-trade` then `tail -f /var/log/alien-trade.log` to confirm clean boot.
```
