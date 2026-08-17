"""
Deterministic market/trade watches — token-efficient monitoring.

A watch is a row {kind, target, op, threshold, last_state}. A cheap pure
predicate evaluates it each loop tick against a point-in-time snapshot the
loop already has (price / regime / drawdown / equity). NO LLM runs here.

Edge-trigger only: a watch fires on the cycle its condition becomes newly
true, then arms 'fired' so it never re-fires until the condition clears and
re-arms. Steady-state cost is zero — the one short LLM "why it matters"
explain call happens in the loop's fire callback, only on an actual fire.

Governed by locked decision #1 (LLM off the hot path) and #6 (a watch failing
must never crash the cycle — the loop wraps the call defensively).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

# What a watch can observe. price/drawdown/equity are numeric; regime is a label.
WATCH_KINDS = ("price", "regime", "drawdown", "equity")
NUMERIC_KINDS = ("price", "drawdown", "equity")
NUMERIC_OPS = ("lt", "gt")

# last_state values
CLEAR = "clear"
FIRED = "fired"


def validate_watch_spec(raw: dict) -> dict:
    """Normalize + validate a watch spec from the cockpit. Raises ValueError on a
    bad spec so the create mutation rejects it loudly rather than storing junk."""
    kind = str(raw.get("kind", "")).strip().lower()
    if kind not in WATCH_KINDS:
        raise ValueError(f"unknown watch kind: {kind!r} (one of {WATCH_KINDS})")

    target = str(raw.get("target", "")).strip()
    label = str(raw.get("label", "")).strip()

    if kind == "regime":
        if not target:
            raise ValueError("regime watch needs a target regime (e.g. 'CRASH')")
        return {"kind": kind, "target": target.upper(), "op": "eq",
                "threshold": 0.0, "label": label}

    # numeric kinds
    op = str(raw.get("op", "")).strip().lower()
    if op not in NUMERIC_OPS:
        raise ValueError(f"{kind} watch needs op in {NUMERIC_OPS}, got {op!r}")
    if kind == "price" and not target:
        raise ValueError("price watch needs a target symbol (e.g. 'CAKE')")
    try:
        threshold = float(raw.get("threshold"))
    except (TypeError, ValueError):
        raise ValueError("threshold must be a number")
    return {"kind": kind, "target": target.upper() if kind == "price" else "",
            "op": op, "threshold": threshold, "label": label}


def _current(kind: str, target: str, snapshot: dict) -> Optional[Any]:
    """The observed value for this watch on this tick, or None if not observable
    now (e.g. a price watch on a symbol the loop isn't currently trading)."""
    if kind == "price":
        if target and target != str(snapshot.get("symbol", "")).upper():
            return None
        return snapshot.get("price")
    if kind == "regime":
        return snapshot.get("regime")
    if kind == "drawdown":
        return snapshot.get("drawdown_pct")
    if kind == "equity":
        return snapshot.get("equity_usd")
    return None


def _condition_true(kind: str, op: str, cur: Any, threshold: float, target: str) -> bool:
    if kind == "regime":
        return str(cur).upper() == str(target).upper()
    if cur is None:
        return False
    if op == "lt":
        return cur < threshold
    if op == "gt":
        return cur > threshold
    return False


def _headline(watch: dict, cur: Any) -> str:
    kind = watch.get("kind")
    label = watch.get("label") or ""
    prefix = f"{label}: " if label else ""
    if kind == "price":
        sym = watch.get("target")
        word = "below" if watch.get("op") == "lt" else "above"
        return f"{prefix}{sym} price {word} {watch.get('threshold')} (now {cur})"
    if kind == "regime":
        return f"{prefix}regime is {watch.get('target')} (now {cur})"
    if kind == "drawdown":
        word = "below" if watch.get("op") == "lt" else "above"
        return f"{prefix}drawdown {word} {watch.get('threshold')}% (now {cur})"
    if kind == "equity":
        word = "below" if watch.get("op") == "lt" else "above"
        return f"{prefix}equity {word} ${watch.get('threshold')} (now ${cur})"
    return f"{prefix}watch fired (now {cur})"


def evaluate(watch: dict, snapshot: dict) -> Optional[dict]:
    """Pure edge-trigger. Returns:
      - a fire dict {watch_id, fired=True, headline, value, new_state='fired'} on a
        NEW trigger,
      - a re-arm dict {watch_id, fired=False, new_state='clear'} when a fired watch's
        condition clears,
      - None when nothing changed (the common case — zero side effects).
    Never raises on a malformed watch — unknown kind/op degrades to None."""
    try:
        kind = watch.get("kind")
        cur = _current(kind, watch.get("target", ""), snapshot)
        if cur is None and kind != "regime":
            return None  # not observable this tick → no state change
        last = watch.get("last_state", CLEAR)
        is_true = _condition_true(kind, watch.get("op", ""), cur, watch.get("threshold", 0.0), watch.get("target", ""))
        if is_true and last != FIRED:
            return {"watch_id": watch.get("_id"), "fired": True,
                    "headline": _headline(watch, cur), "value": cur, "new_state": FIRED}
        if not is_true and last == FIRED:
            return {"watch_id": watch.get("_id"), "fired": False, "new_state": CLEAR}
        return None
    except Exception:  # noqa: BLE001 — a checker bug must never crash the cycle
        return None


def process_watches(
    watches: list[dict],
    snapshot: dict,
    *,
    fire_cb: Callable[[dict, dict], None],
    state_cb: Callable[[Any, str], None],
) -> list[dict]:
    """Run every active watch against the snapshot. `state_cb(id, new_state)` persists
    the armed/clear flag; `fire_cb(watch, result)` runs ONLY on an actual fire (this is
    the single place an LLM explain call may happen). Returns the list of fire results.

    Token invariant: when nothing fires, fire_cb is never called → zero LLM calls."""
    fired: list[dict] = []
    for w in watches:
        res = evaluate(w, snapshot)
        if res is None:
            continue
        state_cb(res["watch_id"], res["new_state"])
        if res.get("fired"):
            fire_cb(w, res)
            fired.append(res)
    return fired
