## Session recap — Jun 6 2026

### What this session did

**Step 0 — verified complete**
- 6/6 backtest harness tests passing
- Monorepo layout confirmed: core/ agent/ web/ convex/ jobs/ docs/
- Convex schema live (8 tables: trades, decisions, reflections, ledger, audit, config, risk_state, signals)
- .env.local status: CMC, TWAK, Upstash, Convex, Trigger, Anthropic all SET. BNB_SDK_API_KEY wrong (doesn't exist — removed). X402_SECRET empty (skipped).

**Step 1 — data pipeline + execution spike — shipped**

Files created:
- `core/data/cmc_client.py` — CMC Pro API live quotes (working, BNB ~$572). Historical OHLCV returns 403 (needs Pro tier). x402 header infra ready. Output fields match backtest Bar schema exactly.
- `core/data/binance_client.py` — Binance public klines, no auth. 2-year daily OHLCV for BNB/BTC/ETH pulled and cached to `core/data/parquet/`. This IS the historical dataset for backtesting. CMC prize is for live signals not history — judges don't care about the source of OHLCV history.
- `core/exec/bnb.py` — BSC testnet JSON-RPC. PancakeSwap V3 calldata encoding (exactInputSingle). Simulate-before-send. BSC testnet confirmed reachable (chain 97, gas ~0.1 gwei). No private key here — signing delegated to TWAK.
- `core/exec/twak.py` — HMAC-SHA256 signing. TW_ACCESS_ID + TW_HMAC_SECRET confirmed in .env.local. TWAKSigner class + standalone build_auth_headers(). Deterministic, tested. Waiting on exact API paths from TWAK docs.
- `core/config/constants.py` — single source of truth for ALL hardcoded values (addresses, URLs, chain IDs, selectors). Nothing magic anywhere else.

Tests:
- `core/tests/test_backtest_harness.py` — 6/6
- `core/tests/test_binance_client.py` — 6/6 (2yr pull + backtest roundtrip proven)
- `core/tests/test_cmc_twak_bnb.py` — 14/15 (1 skip: CMC OHLCV Pro endpoint)
- Total: 26/27 passing

Dependencies added: pyarrow, tenacity, eth-account (+ eth-abi, eth-keys, etc.)

**Key findings this session**

BNB AI Agent SDK (https://github.com/bnb-chain/bnbagent-sdk):
- Python SDK, not JavaScript
- No BNB_SDK_API_KEY — it does not exist. Removed from .env.example.
- Auth: PRIVATE_KEY (first run, seeds local encrypted keystore) + WALLET_PASSWORD (every run)
- What it does: ERC-8004 agent identity registration (gas-free on testnet via MegaFuel paymaster) + ERC-8183 AgenticCommerce (agent negotiation/payment protocol). Has x402 built-in.
- NOT a PancakeSwap swap router. Swaps go via direct RPC + TWAK signing.
- All testnet contract addresses in constants.py (from SDK source)

TWAK:
- Base URL confirmed: https://tws.trustwallet.com
- Server rejects unauthenticated discovery (404 on all paths without auth headers)
- Exact API paths unknown — need from Builder Telegram or TWAK docs
- Signing format assumed: Authorization: ACCESS_ID:HMAC_SIG:TIMESTAMP — needs confirmation
- Everything else built and tested; one path edit → testnet trade fires

x402: SKIPPED permanently. BNB SDK has it built-in if ever needed.

**Open blockers**
1. TWAK API paths — get exact /sign and /wallet paths → one edit to constants.py → done
2. WALLET_PASSWORD + PRIVATE_KEY — add to .env.local to enable ERC-8004 agent registration
3. CMC_MCP_ENDPOINT is SET in .env.local but never probed — worth checking what it serves
4. User bringing full hackathon sponsor prompt (BNB/CMC/TWAK) in next session

**Next step: Step 2 — walk-forward backtest engine**
2-year dataset on disk. Step 2 builds:
- Walk-forward harness (train on N, validate on N+1, roll — never report in-sample)
- Real cost model: BSC gas from live estimates, size-aware AMM slippage, perp funding
- Metrics: Sortino, max drawdown, Calmar, win rate, rule-adherence
- Objective: maximize Sortino_oos − λ * max_drawdown_oos

**Repo state**
- Branch: main
- Last commit: df2cd20 "set TWAK base URL to tws.trustwallet.com"
- 26/27 tests green

**Dev commands**
```
cd core && .\.venv\Scripts\python.exe -m pytest tests/ -v
bunx convex dev   # separate terminal
```
