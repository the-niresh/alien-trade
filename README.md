# Alien-Trade

Autonomous BSC trading agent for **BNB Hack 2026 (DoraHacks) — Track 1**, scored on
risk-adjusted PnL + max drawdown over a live 7-day window (Jun 22–28, 2026).

The honest version of the pitch: **an agent that reads decades of markets and the best
traders, turns what it reads into testable rules, keeps only what survives out-of-sample
validation, and trades self-custody and unattended — with every decision auditable.**

---

## Objective function (locked)

```
maximize  Sortino_oos − λ · max_drawdown_oos          (long-only)
```

Raw return is not the goal — drawdown is the scoring weapon. The judging rubric rewards
returns, drawdown, risk-adjusted performance, and **rule adherence**. Only `twak swap`
trades count toward PnL, so the scored agent is **spot-long-only** on the eligible universe
`{ETH, CAKE, UNI, LINK, AAVE}`.

## Where the strategy actually stands (read this before trusting a number)

Honest walk-forward at the traded cadence (1h) shows **no out-of-sample edge** from the
original trend/EMA-cross strategy, even with funding + sentiment live. The current posture
is **cash-default capital preservation**: hold USDT by default (zero drawdown), deploy long
only on high-conviction regime setups. In a drawdown-penalized rubric, shallow-drawdown
beats clever-but-losing. The active work (see `docs/AWAKE_SPRINT.md`) is a **thesis factory**
that mines a large market + trader-wisdom corpus for rule candidates and validates them
against an anti-data-snooping harness (walk-forward + untouched holdout + deflated Sharpe).
Negative results are logged, not hidden — the falsification log is part of the submission.

---

## Architecture

```
core/       ★ Strategy + signals + backtest/sim engine (Python) — shared by sim AND live
agent/      Live runtime: FastAPI + LangGraph supervisor (imports /core, zero duplicate logic)
web/        React + Vite + Tailwind + PWA — the glass cockpit
convex/     Real-time state bus: trades, decisions, ledger, audit, config, risk_state
jobs/       Trigger.dev scheduled tasks
onboard/    Textual TUI onboarding wizard (pairing-token device flow)   [in build]
docs/       Strategy spec, backtest design, build runbook, sprint design
```

**Locked design decisions:** the LLM is **off** the trade hot path (the trade decision is
deterministic Python in `/core`); sim and live run the **same** `/core` code; out-of-sample
numbers only, full cost model in every backtest, 2–3 signals max.

## Signal library

| Signal | Source | Role |
| --- | --- | --- |
| S1 Momentum/Trend | CMC / Binance OHLCV | Backbone — EMA cross + ROC, ATR-normalized |
| S2 Derivatives | funding rate + open interest | Contrarian on extremes; OI confirms/denies trend |
| S3 Sentiment | CMC social + KOL / Fear&Greed | Rate-of-change of attention, not absolute level |
| S4 On-chain flow | CMC exchange flow + whale | Net outflow = accumulation = bullish precursor |

## Sponsor layers (the three-layer stack)

| Layer | Tech | How we use it |
| --- | --- | --- |
| **L1 Data & Signal** | CMC Agent Hub | Data API + MCP (12 tools) + Skills Marketplace + x402 pay-per-call |
| **L2 Custody & Execution** | Trust Wallet Agent Kit | Self-custody signing — keys never in code; "unlock once, act unattended" |
| **L3 Chain & SDK** | BNB AI Agent SDK | PancakeSwap spot swaps on BSC; real fills calibrate the cost model |

---

## Quickstart

```bash
bash install.sh                 # dep checks + .env.local wizard + launch instructions
# then fill keys (copy .env.example → .env.local) and:

# Python core — strategy + backtest (Linux venv via uv)
cd core && uv venv && uv pip install -e . && .venv/bin/python -m pytest tests/ -q

# Convex real-time state (from repo root — keep running)
bunx convex dev

# Glass cockpit
cd web && bun install && bun run dev
```

A reproducible walk-forward report (out-of-sample, cost-inclusive):

```bash
cd core && .venv/bin/python -m report
```

## Live operations (deployed 24/7 on the VPS)

Runs in place via systemd (all `enabled`, survive reboot):

| Unit | Role | Logs |
| --- | --- | --- |
| `alien-trade.service` | 24/7 paper runtime, 1h cadence, autopilot | `/var/log/alien-trade.log` |
| `alien-cockpit.service` | cockpit PWA on `:4173` (reads Convex) | `/var/log/alien-cockpit.log` |
| `alien-digest.timer` | hourly Telegram digest | `/var/log/alien-digest.log` |

```bash
systemctl status alien-trade --no-pager     # is the agent running?
tail -f /var/log/alien-trade.log            # live decision/audit JSON
systemctl restart alien-trade                # after a change
```

---

## Docs

- [`docs/AWAKE_SPRINT.md`](docs/AWAKE_SPRINT.md) — current sprint design (productization + thesis-factory loop)
- [`docs/STRATEGY.md`](docs/STRATEGY.md) — signal spec, combination logic, anti-overfitting protocol
- [`docs/AUTONOMY.md`](docs/AUTONOMY.md) — autonomous-loop guardrails + prioritized backlog
- [`docs/VALIDATION_1H.md`](docs/VALIDATION_1H.md) — honest out-of-sample results (incl. the no-edge finding)
- [`docs/STEPS.md`](docs/STEPS.md) — ordered build runbook
- [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) — full architecture, phases, risk register

## Compliance gates (hard — miss one and live PnL doesn't count)

- On-chain registration via `twak compete register` **before Jun 22**.
- DoraHacks submission (agent wallet address + strategy writeup).
- Only `twak swap` trades count; hold ≥1 eligible asset at window start; ≥1 trade/day; never let the portfolio fall to ≤ $1.
