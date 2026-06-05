# convex — Real-time State Bus

Convex is the single source of truth for all live agent state. It bridges the Python agent, the background jobs, and the web dashboard — no separate webhook server needed.

## Tables (schema v0)

| Table | Purpose |
|-------|---------|
| `trades` | Every executed or simulated trade with fill price, fees, gas |
| `decisions` | Every cycle: signals snapshot, regime, risk verdict, sizing |
| `reflections` | Hermes loop: post-trade lessons linked to Upstash Vector |
| `ledger` | Running PnL, cumulative costs, drawdown per trade |
| `audit` | Immutable append-only log of every agent event |
| `config` | Kill switch + risk caps — UI writes, agent reads each cycle |
| `risk_state` | Live exposure, daily loss, circuit breaker status |
| `signals` | Per-cycle signal values for debugging + regime analysis |

## Dev

```bash
# from repo root (not inside convex/)
bunx convex dev
```

## Key rule

`config.halted = true` is the kill switch. The agent checks this every cycle and halts within one loop if set. Never bypass this check.
