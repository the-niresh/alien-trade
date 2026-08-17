# Live Rehearsal & Go-Live Runbook (Track 1)

> Goal: get Alien-Trade **genuinely live** with a real on-chain receipt before Jun 22, so
> "running live for N days" is literally true. Honesty is the product — never claim "live
> since X" until a real `twak swap` receipt exists in the ledger.
>
> Verified 2026-06-14. Commands assume repo root `/root/claude/projects/alien-trade` on the
> VPS, `core/.venv` Python, and **bun** for any JS tooling (never npm).

---

## 0. The finding that reshapes the plan (read first)

The competition scores **only `twak swap` transactions** (organizer ruling, CLAUDE.md L3).
There are two execution surfaces in this repo, and the distinction is everything:

| Path | Code | Scores? | Status here |
| --- | --- | --- | --- |
| **`twak swap` CLI** | `agent/twak_cli.py` → `TwakSwapExecutor` | ✅ **YES** | ⛔ CLI **not installed**; mainnet-only |
| Raw / Amber+key | `core/exec/twak.py` (REST) + `core/exec/bnb.py` + `OnchainExecutor` | ❌ no (the "raw" path) | REST auth ✅ works; Amber = mainnet-liquidity only |

Consequences:
1. **A testnet dress rehearsal cannot exercise the scoring path.** `twak swap` is mainnet,
   and the Amber router has no testnet liquidity. Testnet/paper `--dry-run` validates the
   *plumbing* (executor selection, simulate-before-send, risk caps, idempotency, the loop)
   but produces **no scoring receipt**.
2. **The genuine "live for days" claim requires a tiny-capital MAINNET `twak swap`**, done
   early. That is the standout artifact — plan the mainnet rehearsal first, not last.
3. **Blocker:** the `twak` CLI must be installed + authenticated before any scoring swap is
   possible. As wired today (`EXECUTION_BACKEND=twak`, `--mode mainnet`), a swap attempt
   raises `TwakError: twak CLI not found`.

What DOES work today (verified): TWAK REST auth (`get_prices` returns live tickers, zero
spend); the deterministic strategy loop; simulate-before-send logic in both executors.

---

## 1. Status snapshot (2026-06-14)

- `alien-trade.service` runs `--mode paper` (SIMULATED). **No real swap has ever executed.**
- **Fixed this session** (config hygiene + a real bug):
  - `.env.local TOKEN_ALLOWLIST` → `ETH,CAKE,UNI,LINK,AAVE` (was `BNB,WBNB,USDT`; note the
    *real* gate is the hardcoded `core/risk/guardrails.py::TOKEN_ALLOWLIST` — the env var is
    not read by Python, so this was a foot-gun, not a live hole).
  - `.env.local TWAK_API_BASE` → `https://tws.trustwallet.com` (was empty → broke the REST
    client; also fixed in code so empty falls back to the default — commit `d3d7509`).
- `WALLET_ADDRESS` is **empty** (operator must set after funding).
- Expected score (the **live `contrarian` strategy**, bootstrapped 7-day windows, real cost
  model, sentiment data present): ETH **mean −0.027, median +0.000, P(objective ≥ 0) ≈ 53%**.
  Per asset (mean / P≥0): ETH −0.027/53% · UNI −0.027/56% · AAVE −0.026/48% · CAKE −0.031/40%
  · LINK −0.023/36%. *Honest read: the contrarian agent is genuinely capital-preserving — it
  sits flat in a majority of weeks (median exactly 0), so >50% of 7-day windows score ≥ 0 on
  ETH/UNI; the slightly-negative mean is the losing-capitulation tail. ETH or UNI is the best
  live-window symbol. The standout submission is this honest capital-preservation posture +
  the falsification log; a trending week is the upside.* (Note: AUTOPILOT=1 is on live and is
  not modelled by score_sim, so treat these as the strategy-only baseline.)
- Decision latency: per-cycle deterministic compute **~1.2 ms** (p95 2.3 ms) — a non-issue.

---

## 2. Operator critical path (score = 0 without these — do in order)

> The agent CANNOT do any of these (money / on-chain / key custody). Each is yours.

### (a) Install + authenticate the `twak` CLI  🔴 NEW BLOCKER
```bash
# Verify the exact package name from the TWAK docs first; then (bun, not npm):
bun add -g @trustwallet/cli           # or the documented package; puts `twak` in ~/.bun/bin
which twak                            # must resolve before anything else works
twak auth login                       # authenticate with TW_ACCESS_ID / TW_HMAC_SECRET
twak auth status --json               # expect authenticated: true
twak wallet address --chain bsc --json   # prints the agent wallet address
```
Then copy that address into `.env.local` as `WALLET_ADDRESS=0x...`.

### (b) Fund the wallet (MAINNET, small)  🔴
`twak swap` is mainnet — fund the agent wallet with a small amount of BNB (gas) + USDT
(trading capital, e.g. $20–50 for the rehearsal). The agent buys USDT→token and sells back.

### (c) Register for the competition BEFORE Jun 22  🔴 (late = rejected, score = 0)
```bash
twak compete status --chain bsc --json     # preflight (read-only)
twak compete register --chain bsc --json   # the on-chain registration tx
```

### (d) DoraHacks submission  🔴
Wallet address + strategy writeup (the loop can auto-draft from VALIDATION_1H + THESIS_LEDGER).

### (e) Firewall + cockpit bind  🟡
`ufw allow 22,80,443`; bind the cockpit to the Tailscale IP (touches SSH reachability).

---

## 3. The supervised FIRST real swap (one shot, you trigger it)

Pre-flight (must all be true): `which twak` resolves · `twak auth status` authenticated ·
`WALLET_ADDRESS` set · wallet funded (BNB + USDT) · `TOKEN_ALLOWLIST` correct.

**Simulate-before-send is enforced in code** (`TwakSwapExecutor`: quote → slippage-cap abort
→ only then broadcast). Prove the quote first by hand, then do exactly one tiny live swap:

```bash
# 1. QUOTE ONLY (no broadcast, no spend) — proves routing + impact on the eligible token:
twak swap USDT ETH --usd 10 --chain bsc --slippage 2 --quote-only --json

# 2. If the quote's price impact is sane (< 2%), the ONE-SHOT first real swap:
#    tiny size, eligible token, simulate-before-send + idempotency are automatic.
core/.venv/bin/python -m agent.runtime --mode mainnet --symbol ETH --cycles 1
#    (EXECUTION_BACKEND=twak selects TwakSwapExecutor; --cycles 1 = a single decision.)
```
Expect: an `ExecutionReport(FILLED, tx_hash=0x...)` and a ledger row with the real fill.
**Only after a real tx_hash exists may we say the agent is live.**

---

## 4. Start 24/7 live mode (after the first swap is confirmed)

```bash
# Edit the unit to run mainnet instead of paper, then:
sudo systemctl daemon-reload
sudo systemctl restart alien-trade
systemctl status alien-trade --no-pager
tail -f /var/log/alien-trade.log        # watch decisions + fills (JSON)
```
A prepared mainnet unit variant is at `docs/ops/alien-trade-mainnet.service` (Phase B9 —
written, NOT enabled). Flip by pointing the symlink / copying it in, then the commands above.

### Activity floor
The competition wants ≥1 trade/day. Enable the activity floor (`ACTIVITY_FLOOR=1` in
`.env.local`) so the loop makes the minimum compliant trade when the strategy is flat — but
note (§1) each forced trade has a small cost/risk drag on the score; keep size minimal.

---

## 5. What "good" looks like · kill switch · rollback

**Good:** uptime ≈ 100% unattended; every order shows a `simulated` line *before* any
broadcast; 0 risk-cap violations; fills carry real `tx_hash` + receipt gas; equity drawdown
shallow (the λ=2 objective punishes drawdown); ≥1 trade/day once the floor is on.

**Kill switch (instant, no redeploy)** — any one of these flips the same Convex
`config.halted` flag the loop reads at the top of every cycle (`agent/loop.py:238`),
so the in-flight cycle stops before it sizes a trade:
- **Cockpit:** the paired **Halt** toggle (control-token gated).
- **Telegram:** send `/halt` to the alien-trade bot (`agent/notify.py:185` → `set_halted(True)`).
- **Bluntest, no Convex:** `sudo systemctl stop alien-trade` (kills the process outright).

Risk caps (`core/risk/guardrails.py`): per-trade ≤ $2k, position ≤ 25%, exposure ≤ 30%,
slippage abort > 2%, daily-loss kill > 5%. These fire automatically.

**Rollback to safe (paper):**
```bash
sudo systemctl stop alien-trade
# restore the paper unit (ExecStart ... --mode paper), then:
sudo systemctl daemon-reload && sudo systemctl restart alien-trade
```
Funds are self-custody (TWAK on-device key) — stopping the agent stops trading; it never
holds or moves capital on its own beyond a signed, simulated, capped swap.

---

## 6. Clean-ledger reset for go-live (deferred on purpose)

Stale paper rows (equity ≈ $9,831) still sit in Convex `festive-newt-1`. **Do not reset now**
— the paper service keeps writing, so a reset only matters at the moment we cut to mainnet.
At go-live, before `systemctl restart` into mainnet, run the ledger reset (operator-gated;
mutates live Convex) so the live equity curve starts clean. Command to be wired in Phase A5.
