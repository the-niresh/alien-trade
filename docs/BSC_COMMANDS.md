# BSC Execution Commands — TWAK CLI Reference

> **Purpose:** Complete reference for every TWAK CLI command the agent uses for
> swaps, transfers, and DCA automations on BSC. Update this file whenever a new
> command is added to the agent.
>
> **Testing rule:** ALL execution testing must happen from the **Alien-Trade cockpit
> UI at http://76.13.243.12:4173** — never trigger live trades directly from
> Claude Code terminal. Use the Co-Pilot "Start Trading with AI" flow or the
> Controls panel for manual overrides. Terminal testing is only for quoting
> (`--quote-only`) and balance checks — never `swap_execute` or `transfer` from
> Claude Code.

---

## Eligible Scoring Tokens (Track-1)

Only `twak swap` transactions count toward competition PnL. Eligible tokens:

| Symbol | BSC Contract Address | Notes |
|--------|---------------------|-------|
| **ETH** | _(symbol works — no contract needed)_ | BEP-20 wrapped ETH |
| **CAKE** | `0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82` | PancakeSwap token |
| **UNI** | `0xBf5140A22578168FD562DCcF235E5D43A02ce9B1` | Uniswap (BSC) |
| **LINK** | `0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD` | Chainlink (BSC) |
| **AAVE** | `0xfb6115445Bff7b52FeB98650C87f44907E58f802` | Aave (BSC) |
| **USDT** | `0x55d398326f99059fF775485246999027B3197955` | BEP-20 Tether (quote currency) |

⚠️ **CAKE, UNI, LINK, AAVE must use contract addresses, NOT symbols.**
Only `ETH` works by symbol on BSC via the TWAK CLI.

**NOT eligible (do not trade):** BNB, WBNB, BTC, BTCB

---

## Environment Setup

```bash
export TWAK_WALLET_PASSWORD="<password from .env.local>"
# Or: systemd loads it automatically from EnvironmentFile=.env.local
```

---

## 1. Swap Commands

### Quote (simulate, no execution)

```bash
# Buy ETH with USDT — by symbol (works for ETH only)
twak swap USDT ETH --usd 4 --chain bsc --slippage 3 --quote-only --json

# Buy CAKE with USDT — must use contract address
twak swap USDT 0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82 --usd 4 --chain bsc --slippage 3 --quote-only --json

# Buy UNI
twak swap USDT 0xBf5140A22578168FD562DCcF235E5D43A02ce9B1 --usd 4 --chain bsc --slippage 3 --quote-only --json

# Buy LINK
twak swap USDT 0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD --usd 4 --chain bsc --slippage 3 --quote-only --json

# Buy AAVE
twak swap USDT 0xfb6115445Bff7b52FeB98650C87f44907E58f802 --usd 4 --chain bsc --slippage 3 --quote-only --json

# Sell ETH back to USDT
twak swap ETH USDT --usd 4 --chain bsc --slippage 3 --quote-only --json
```

**Quote response:**
```json
{
  "input": "4.005200482502813131 USDT",
  "output": "0.002323240468455196 ETH",
  "minReceived": "0.002254443254201540 ETH",
  "provider": "0x",
  "priceImpact": "0"
}
```

### Execute Swap

```bash
# ⚠️  MAINNET — real money. Use from cockpit UI, not terminal.
twak swap USDT ETH --usd 4 --chain bsc --slippage 3 --json
```

**Execute response (success):**
```json
{
  "input": "4.005200482502813131 USDT",
  "output": "0.002323240468455196 ETH",
  "minReceived": "0.002254443254201540 ETH",
  "provider": "0x",
  "priceImpact": "0",
  "hash": "0x23563d1a2ca38dbd01d90efe42a3b90ad2dfe2bd34e2914da96d90daec60e936",
  "fromChain": "bsc",
  "toChain": "bsc",
  "explorer": "https://bscscan.com/tx/0x23563d1..."
}
```

**Execute response (failure — TX_FAILED):**
```json
{ "error": "execution reverted: 0xf4059071", "errorCode": "TX_FAILED" }
```

### Routing Behavior (BSC)

| Trade Size | Slippage | Router | Result |
|-----------|---------|--------|--------|
| Any | 2% | LiquidMesh | ❌ TX_FAILED (no prior approval) |
| Any | ≥3% | 0x | ✅ Works |
| ≥$2 | 3% | LiquidMesh | ❌ TX_FAILED |
| <$2 | 3% | 0x | ✅ Works |

**Agent retry ladder (automatic):** 2% → 5% → 8%. Each step re-routes to a
different provider. Implemented in `agent/executor.py` `TwakSwapExecutor.execute()`.

---

## 2. Token Addresses for Swaps (in TwakCli)

The agent's `swap_execute` / `swap_quote` methods accept token symbols.
For CAKE/UNI/LINK/AAVE, the symbol lookup fails — the agent must pass the
contract address. Update `agent/twak_cli.py` constants:

```python
# BSC BEP-20 token registry (symbols that twak does NOT resolve natively)
BSC_TOKEN_REGISTRY: dict[str, str] = {
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "UNI":  "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",
    "LINK": "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
    "AAVE": "0xfb6115445Bff7b52FeB98650C87f44907E58f802",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    # ETH works by symbol — no entry needed
}

def _resolve_token(symbol: str, chain: str = "bsc") -> str:
    """Return contract address for tokens that twak doesn't resolve by symbol."""
    if chain == "bsc":
        return BSC_TOKEN_REGISTRY.get(symbol.upper(), symbol)
    return symbol
```

Pass through `swap_quote` and `swap_execute`:
```python
def swap_quote(self, from_token: str, to_token: str, *, usd: float, chain: Optional[str] = None, slippage: float = 1.0) -> TwakQuote:
    c = chain or self.chain
    return self._run("swap", _resolve_token(from_token, c), _resolve_token(to_token, c), ...)
```

---

## 3. Transfer (Withdraw)

```bash
# Transfer USDT to another BSC address
twak transfer --to 0xDESTINATION --amount 5.0 --chain bsc --token 0x55d398326f99059fF775485246999027B3197955 --json

# Transfer ETH to another BSC address
twak transfer --to 0xDESTINATION --amount 0.001 --chain bsc --token 0x2170Ed0880ac9A755fd29B2688956BD959F933F8 --json

# Transfer native BNB (omit --token for native coin)
twak transfer --to 0xDESTINATION --amount 0.005 --chain bsc --json
```

**Transfer response:**
```json
{
  "hash": "0xabc...",
  "explorer": "https://bscscan.com/tx/0xabc...",
  "status": "confirmed"
}
```

**Token contract addresses for transfer:**

| Token | Contract |
|-------|---------|
| USDT | `0x55d398326f99059fF775485246999027B3197955` |
| ETH (BEP-20) | `0x2170Ed0880ac9A755fd29B2688956BD959F933F8` |
| BNB (native) | _(omit --token flag)_ |

---

## 4. DCA / Limit Order Automations

```bash
# Create a DCA (dollar cost average) automation
twak automate add --from-token USDT --to-token ETH --amount 1 --interval 3600 --chain bsc --json

# Create a limit order (buy ETH when price drops below $1600)
twak automate add --from-token USDT --to-token ETH --amount 2 --price 1600 --condition below --chain bsc --json

# List active automations
twak automate list --chain bsc --json

# Pause/resume/delete by ID
twak automate pause --id <automation-id> --json
twak automate resume --id <automation-id> --json
twak automate delete --id <automation-id> --json
```

**These are wired in `agent/command_worker.py`** as command types:
- `automate_add` — create DCA or limit order
- `automate_pause` / `automate_resume` / `automate_delete` — manage by ID

---

## 5. Wallet & Balance

```bash
# Check balance (safe — no execution)
twak wallet balance --chain bsc --json

# Get wallet address
twak wallet address --chain bsc --json

# Check portfolio across all chains
twak wallet portfolio --json
```

**Balance response:**
```json
{
  "chain": "bsc",
  "address": "0x485Ec1b615369d8a6dFb452471C4994f2e4d062d",
  "symbol": "BNB",
  "available": "0.0099960875",
  "totalUsd": 5.78,
  "tokens": [
    { "symbol": "ETH",  "contract": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "balance": "0.002535" },
    { "symbol": "USDT", "contract": "0x55d398326f99059fF775485246999027B3197955", "balance": "0.508427" }
  ]
}
```

---

## 6. ERC-20 Approvals

```bash
# Check current allowance for a spender (e.g., LiquidMesh router)
twak erc20 allowance --token 0x55d398326f99059fF775485246999027B3197955 --owner 0x485Ec1b6... --spender 0xROUTER --chain bsc --json

# Approve router to spend USDT (one-time, fixes TX_FAILED from LiquidMesh)
twak erc20 approve --token 0x55d398326f99059fF775485246999027B3197955 --spender 0xROUTER --amount 1000000 --chain bsc --json

# Revoke approval
twak erc20 revoke --token 0x55d398326f99059fF775485246999027B3197955 --spender 0xROUTER --chain bsc --json
```

**Why the retry ladder exists:** Rather than pre-approving the LiquidMesh router
(which would require knowing the router address), the agent escalates slippage
to force re-routing to the 0x provider, which handles approvals internally.

---

## 7. Competition Registration

```bash
# Check competition status (safe — read-only)
twak compete status --json

# Register wallet for Track-1 (one-time, already done)
twak compete register --json
```

⚠️ `compete status` and `compete register` do NOT accept `--chain` flag.

---

## 8. Testing Protocol

### Safe to run from terminal (read-only):
```bash
twak swap USDT ETH --usd 1 --chain bsc --slippage 3 --quote-only --json  # ✅
twak wallet balance --chain bsc --json                                     # ✅
twak compete status --json                                                  # ✅
twak automate list --json                                                   # ✅
```

### Must use cockpit UI (execution — real money):
| Action | Cockpit path |
|--------|-------------|
| Test a swap | Co-Pilot → "Start Trading with AI" → type "buy 1 ETH" → confirm card |
| Set strategy | Co-Pilot → "Start a conservative run" chip |
| Withdraw | Withdraw view → form → double-confirm |
| Trigger a cycle | Controls view → "Force Cycle" button (if implemented) |
| Check trade landed | Trackers view → Ongoing Trades |
| Check wallet balance | Portfolio view |

**URL:** http://76.13.243.12:4173 (pair with `CONTROL_TOKEN` from `.env.local`)

---

## 9. Known Issues & Workarounds

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| CAKE/UNI/LINK/AAVE fail with `TOKEN_NOT_FOUND` | twak doesn't resolve these symbols on BSC | Use contract addresses (see §2) |
| USDT→X fails with `TX_FAILED: 0xf4059071` at slippage <3% | LiquidMesh router requires prior ERC-20 approval | Retry ladder (2%→5%→8%) auto-reroutes to 0x |
| `twak compete status --chain bsc` fails | `compete` subcommand doesn't accept `--chain` | Omit `--chain` flag |
| Chart crashes with "data must be asc ordered" | Convex returns ticks DESC, restarts create overlapping timestamps | Monotonic filter in `TradingChart.tsx` |

---

## 10. Agent Token Allowlist Fix (TODO — implement before Jun 21)

The agent service currently runs with `--symbol ETH` only. To trade CAKE/UNI/LINK/AAVE:

1. Add `BSC_TOKEN_REGISTRY` dict to `agent/twak_cli.py` (see §2).
2. Update `TwakCli.swap_quote()` and `TwakCli.swap_execute()` to call `_resolve_token()`.
3. Update `agent/runtime.py` or the service `ExecStart` to accept multiple symbols,
   OR let the strategy pick from `TOKEN_ALLOWLIST` on each cycle.
4. Test via cockpit quote (not execution) before enabling on mainnet.
