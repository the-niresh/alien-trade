# agent - Live Runtime ✅ (Step 5)

Runs the **same `/core` strategy** as the backtest, on a live (or replayed) feed.
Zero duplicate strategy logic - this package only orchestrates.

## Modules

| File | Role |
|------|------|
| `loop.py` | **DecisionLoop** - the heart. Per cycle: feed → kill-switch → core risk-wrapped strategy → mistake-avoidance → executor → ledger reconcile → Convex rows. |
| `executor.py` | `PaperExecutor` (sim-faithful) + `TwakSwapExecutor` (self-custody live: quote→cap→`twak swap`→confirm) + `OnchainExecutor` (raw BNB-SDK path). Idempotency keys, slippage cap. |
| `twak_cli.py` | Wrapper around the `twak` CLI - wallet status/address/balance + swap quote/execute. Keys stay on-device; agent never holds a key. |
| `wallet.py` | `python -m agent.wallet` - connection check (twak → auth → wallet → address → balance) with exact next-step commands. |
| `recovery.py` | Crash-state recovery: rebuild ledger + risk + idempotency set from the Convex event log on restart (no double-trade). |
| `feed.py` | `ReplayFeed` (deterministic, paper/parity/chaos) + `BinanceLiveFeed` (real live bars). |
| `ledger.py` | Live PnL / drawdown / daily-loss accountant; mirrors `backtest.engine` accounting. |
| `convex_bridge.py` | Convex state/audit/UI bus over HTTP. Degrades gracefully offline. |
| `brain.py` | Mistake-avoidance seam (Hermes loop) - `AllowAll` default; Vector-backed in Step 6. |
| `config.py` | `AgentConfig` - shares `RiskConfig` + `StrategyParams` with the sim. |
| `runtime.py` | Wiring + CLI. `qr.py` renders the PWA QR. |
| `server.py` | FastAPI: `/health /cycle /status /halt /resume` (Trigger.dev + PWA poke these). |
| `smoke.py` | Paper rehearsal: replay historical bars through the full stack into Convex. |

## Run

```bash
# tests (parity + chaos)
core/.venv/Scripts/python.exe -m pytest agent/tests -v

# paper smoke over real history (set CONVEX_URL to write live rows)
core/.venv/Scripts/python.exe -m agent.smoke --bars 250

# live runtime
core/.venv/Scripts/python.exe -m agent.runtime --mode paper --cycles 50
core/.venv/Scripts/python.exe -m uvicorn agent.server:app --port 8000
```

## Invariant

The live strategy is built by the **same** `make_strategy` + `RiskEngine` the
backtest uses. The parity tests assert the paper loop reproduces the backtest
fill-for-fill - if they ever diverge, the sim is lying and the build is broken.
