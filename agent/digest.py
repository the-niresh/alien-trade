"""
Hourly digest — reads the live Convex state bus and pushes a compact Telegram
summary so the operator gets a heartbeat every hour without watching the cockpit.

Self-contained CLI, run by the alien-digest systemd timer:

    python -m agent.digest          # build + send one digest, then exit
    python -m agent.digest --stdout # print to stdout (no Telegram), for testing

Degrades gracefully: no CONVEX_URL → reports "offline"; no TELEGRAM_BOT_TOKEN /
TELEGRAM_CHAT_ID → prints to stdout instead of sending (never raises). It reuses
the same ConvexBridge reads the agent writes through and the same TelegramBot the
loop alerts through — one source of truth, one voice.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

from agent.config import AgentConfig  # loads .env.local as a side effect
from agent.convex_bridge import ConvexBridge
from agent.notify import TelegramBot


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _pct(x) -> str:
    return f"{_f(x) * 100:+.2f}%"


def _usd(x) -> str:
    return f"${_f(x):,.2f}"


def _trades_last_hour(bridge: ConvexBridge, now_ms: float) -> tuple[int, int, int]:
    """(count, buys, sells) of trades in the trailing 60 minutes."""
    cutoff = now_ms - 3600_000
    rows = bridge.recent_trades(limit=200)
    recent = [r for r in rows if _f(r.get("timestamp_ms")) >= cutoff]
    buys = sum(1 for r in recent if str(r.get("side", "")).lower() == "buy")
    sells = sum(1 for r in recent if str(r.get("side", "")).lower() == "sell")
    return len(recent), buys, sells


def build_digest(bridge: ConvexBridge) -> str:
    now_ms = time.time() * 1000
    cfg = bridge.get_config() or {}
    mode = cfg.get("trading_mode", "paper")
    halted = bridge.is_halted()

    ledger = bridge.latest_ledger() or {}
    sc = bridge._call("query", "scorecard:get", {}) or {}
    decisions = bridge.recent_decisions(limit=1)
    last = decisions[0] if decisions else {}

    n_tr, buys, sells = _trades_last_hour(bridge, now_ms)

    # operational stats live as a JSON string inside the scorecard row
    op = {}
    try:
        op = json.loads(sc.get("operational") or "{}")
    except (TypeError, ValueError):
        op = {}

    cum_pnl = _f(ledger.get("cumulative_pnl_usd"))
    equity = 10_000.0 + cum_pnl  # initial paper capital + cumulative PnL
    dd = ledger.get("current_drawdown_pct", sc.get("max_drawdown"))
    fees_gas = _f(ledger.get("cumulative_fees_usd")) + _f(ledger.get("cumulative_gas_usd"))

    flag = "🔴 HALTED" if halted else "🟢 live"
    sig = last.get("signals", {}) or {}
    sig_str = "  ".join(f"{k[:3]}={_f(v):+.2f}" for k, v in sig.items()) if sig else "—"

    lines = [
        f"🛸 Alien-Trade · {mode} · {flag}",
        f"{time.strftime('%Y-%m-%d %H:%M', time.localtime())} · hourly digest",
        "",
        f"💰 Equity: {_usd(equity)}   PnL: {_usd(cum_pnl)} ({_pct(sc.get('total_return'))})",
        f"📉 Drawdown: {_pct(dd)}   (max {_pct(sc.get('max_drawdown'))})",
        f"🎯 Objective: {_f(sc.get('objective')):.3f}   Sortino {_f(sc.get('sortino')):.2f} · Sharpe {_f(sc.get('sharpe')):.2f}",
        f"📊 Trades: {int(_f(sc.get('n_trades')))} total · win {_pct(sc.get('win_rate'))} · PF {_f(sc.get('profit_factor')):.2f}",
        f"⏱ Last hour: {n_tr} fills ({buys}B/{sells}S)   fees+gas {_usd(fees_gas)}",
        f"🧭 Last decision: {last.get('regime', '—')} → {last.get('risk_verdict', '—')}  ({last.get('risk_reason', '—')})",
        f"    signals: {sig_str}",
        f"🛡 Rule-adherence: {'✅ clean' if sc.get('rule_adherence_clean', True) else '⚠️ VIOLATION'}   cycles {op.get('cycles_total', '—')}",
    ]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Alien-Trade hourly Telegram digest")
    ap.add_argument("--stdout", action="store_true", help="print instead of sending to Telegram")
    args = ap.parse_args(argv)

    cfg = AgentConfig()
    bridge = ConvexBridge(url=cfg.convex_url)
    if not bridge.enabled:
        msg = "🛸 Alien-Trade digest: Convex offline (no CONVEX_URL) — agent state unavailable."
    else:
        msg = build_digest(bridge)

    if args.stdout:
        print(msg)
        return 0

    bot = TelegramBot()
    if not bot.enabled:
        print("[digest] TELEGRAM_BOT_TOKEN/CHAT_ID not set — printing instead:\n")
        print(msg)
        return 0

    mid = bot.send(msg, reply_markup=None)
    print(f"[digest] sent (message_id={mid})" if mid else "[digest] send failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
