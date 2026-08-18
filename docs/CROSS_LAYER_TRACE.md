# The Cent That Became a Trade - Cross-Layer Trace (L1 + L2 + L3)

> AWAKE_SPRINT §3.5. One annotated path that touches **all three sponsor layers** end to
> end - the demo spine for the three stackable $2k prizes. Every hop cites the exact file
> and function so a judge can verify the claim in the codebase.

```
$0.01 USDC  ──x402──▶  CMC data  ──▶  /core decision  ──TWAK sign──▶  swap  ──BNB SDK──▶  receipt  ──▶  ledger  ──▶  cockpit
   L2/L1            L1                deterministic           L2                  L3                  state              UI
```

## Hop-by-hop

| # | Hop | Layer | File · function | What happens |
|---|-----|-------|-----------------|--------------|
| 1 | **$0.01 USDC paid via TWAK-native x402** | L2→L1 | `agent/x402_provider.py::register` (wired in `agent/server.py:78-79`) | The runtime's CMC data call is metered at $0.01/call. One wallet both **pays** (x402) and later **trades** (swap) - TWAK's "unlock once, then act" tagline made literal. |
| 2 | **CMC data call returns** | L1 | `core/data/cmc_client.py::CMCClient._get` (x402 HTTP via `_build_x402_http`) | OHLCV + funding/OI + social/flow for an eligible token (ETH/CAKE/UNI/LINK/AAVE). |
| 3 | **Signals computed** | L1→core | `core/signals/{momentum,derivatives,sentiment,onchain}.py` | S1-S4 turned into ATR-normalized scores. No LLM (locked decision #1). |
| 4 | **Deterministic decision** | core | `core/strategy/combined.py::make_strategy → strategy(history)` | The trade decision: regime-gated size, cash-default trend filter. Pure Python; sim and live share this exact code (locked decision #2). |
| 5 | **Risk veto + sizing** | core | `core/risk/guardrails.py` | Caps, equity floor, allowlist. Can only shrink size. |
| 6 | **Simulate-before-send** | L3 | `core/exec/bnb.py::simulate_swap` | Slippage/route simulated; a risky send is blocked here (the "N risky sends blocked" counter). |
| 7 | **TWAK-signed swap** | L2 | `core/exec/twak.py::TWAKClient.get_swap_route → get_step_transaction` + `build_auth_headers` (HMAC) | The only scored path: a `twak swap`, signed locally - zero raw keys in code/logs. |
| 8 | **On-chain execution + receipt** | L3 | `core/exec/bnb.py::execute_swap_pipeline` | BNB AI Agent SDK lands the swap on BSC; the on-chain receipt is the source of truth (real fill price, real gas). |
| 9 | **Ledger write** | state | `agent/convex_bridge.py::record_trade` | Real fill + gas → Convex ledger ("if it's not in Convex, it didn't happen"). Feeds the cost model back into the backtest. |
| 10 | **Cockpit update** | UI | `web/src/App.tsx` (reactive `api.ledger.latest`, `api.config.get`) | PnL, drawdown, self-custody badge update live. State-changing controls are gated by the pairing `control_token` (CSO-1 fix). |

## Why this is one artifact for three prizes

- **L1 (CMC Data):** hops 1-3 + the 8/12-tool coverage map (`docs/CMC_COVERAGE.md`); x402
  provenance on every data call.
- **L2 (TWAK):** hops 1 (x402 pay) + 7 (local signing) - one wallet pays and trades,
  "unlock once" demonstrated; guardrails map to the rubric's "rule adherence".
- **L3 (BNB SDK):** hops 6 + 8 - simulate-before-send + on-chain receipt as ledger truth;
  gas/slippage calibrated from real fills (sim-vs-live drift quantified in the writeup).

The cost model in the backtest is calibrated from hop 8's real receipts, so the same
`/core` that decides the trade (hop 4) is the one validated offline - no sim/live divergence.
