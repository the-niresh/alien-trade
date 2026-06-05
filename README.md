# Alien-Trade

Autonomous BSC trading agent built for **BNB Hack 2026 (DoraHacks) — Track 1**.

Scored on risk-adjusted PnL + max drawdown over a live 7-day window (Jun 22–28, 2026).

---

## What it does

- Pulls 4 orthogonal signal types from CMC Agent Hub (momentum, derivatives/funding, sentiment, on-chain flow)
- Runs a deterministic strategy through a walk-forward backtester — no LLM in the trade decision path
- Executes via BNB AI Agent SDK (PancakeSwap spot + perps), signed by Trust Wallet Agent Kit (TWAK)
- Learns from every trade via a Hermes-style reflection loop stored in Upstash Vector
- Real-time state (PnL, drawdown, kill switch) synced through Convex to a PWA dashboard

## Objective function

```
maximize  Sortino_oos − λ × max_drawdown_oos
```

Raw return is not the goal. Drawdown is the scoring weapon.

---

## Monorepo

```
core/       ★ Strategy + signals + backtest/sim engine (Python) — shared by sim and live
agent/      Live runtime: FastAPI + LangGraph supervisor
web/        React + Vite + shadcn/ui + Tailwind + PWA
convex/     Real-time state bus: trades, decisions, ledger, audit, config, risk_state
jobs/       Trigger.dev scheduled tasks
docs/       Architecture, strategy spec, build runbook
```

## Sponsor layers

| Layer | Tech | Role |
|-------|------|------|
| L1 | CMC Agent Hub | All data (OHLCV + funding/OI + social + on-chain) |
| L2 | Trust Wallet Agent Kit | Self-custody signing — keys never in code |
| L3 | BNB AI Agent SDK | PancakeSwap spot swaps + perps on BSC |

---

## Quickstart

```bash
# Python core (strategy + backtest)
cd core
uv venv && uv pip install -e .
.venv/Scripts/python -m pytest tests/ -v

# Convex (real-time state)
# from repo root:
bunx convex dev

# Web dashboard
cd web
bun install && bun dev
```

Copy `.env.example` → `.env.local` and fill in your keys before running anything.

---

## Docs

- [`docs/STRATEGY.md`](docs/STRATEGY.md) — signal spec + combination logic + anti-overfitting protocol
- [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) — full architecture, phases, risk register
- [`docs/STEPS.md`](docs/STEPS.md) — ordered build runbook with checkboxes
