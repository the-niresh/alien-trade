# Sponsor Tools Integration — utilization map + special-prize evidence

> The doc PROJECT_PLAN.md (§ key files) promised. Maps every sponsor resource in
> the hackathon's three layers (`harness/hackathon.png`) to how Alien-Trade uses
> it, how deeply, and where the untapped upside is. Two audiences: (1) judges
> scoring the 3 × $2k special prizes (CMC / TWAK / BNB SDK), (2) us, to make sure
> we use the stack *fully* and *differently* from other teams.

Sources: the sponsor links —
- CMC Pro API: https://coinmarketcap.com/api/documentation/pro-api-reference/endpoint-overview
- CMC AI Agent Hub MCP: https://coinmarketcap.com/api/documentation/ai-agent-hub/mcp
- CMC Skills Marketplace: https://coinmarketcap.com/api/skills-marketplace/
- CMC x402: https://coinmarketcap.com/api/documentation/ai-agent-hub/x402
- Trust Wallet portal: https://portal.trustwallet.com/
- BNB Chain quick-guide: https://docs.bnbchain.org/bnb-smart-chain/developers/quick-guide/
- PancakeSwap docs: https://docs.pancakeswap.finance/

---

## The thesis: SDKs are table stakes; depth + data are the edge

Every participant wires CMC + TWAK + BNB — that earns zero alpha and zero
differentiation. We win on **how deep** we use each layer and **what we do with
the data**:

- **Edge data, not just price** (CMC derivatives + social/KOL + on-chain flow).
- **Deterministic, auditable core** (LLM off the trade path) — provable, not a
  black box.
- **Self-learning** (Hermes reflection + Karpathy AutoResearch + 2-yr preload).
- **Risk-first** (drawdown-first objective; simulate-before-send; real costs).
- **Glass-cockpit** transparency (the agent activity channel = demo + audit).

---

## L1 — DATA & SIGNAL · CoinMarketCap (CMC Agent Hub)

| Resource | What it is | Our use | Depth |
|----------|-----------|---------|-------|
| **Data API** (REST: CEX/DEX, derivatives, on-chain, social, KOL, wallets) | the full data surface | OHLCV (backtest + live), the edge fields: funding/OI, social/sentiment, on-chain flow → the S1–S4 signal library | 🟢 core |
| **x402** (pay-per-call) | $0.01/call, USDC on Base, gasless EIP-3009 | live data calls paid per-use via `core/data/cmc_client.py`; dedicated burner wallet, no keys | 🟢 built (path fix pending) |
| **Data MCP** (12 tools) | quotes/technicals/on-chain/derivatives/sentiment/news as MCP tools | **planned, NOT wired** — Second Brain research + co-pilot should call these | 🔴 gap |
| **Skills Marketplace** (smart routing, cloud pipelines) | hosted skills + publish-your-own | **untapped** — consume pipelines AND publish our Track-2 strategy as a CMC Skill | 🔴 gap |

**Differentiator:** we use the *derivatives + social + on-chain* data most teams
ignore, as orthogonal signals — that's `STRATEGY.md`'s whole edge. x402 makes data
spend metered + demonstrable.

**x402 facts (locked):** Base only (`eip155:8453`), USDC only
(`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`), $0.01/call, gasless (payer needs
USDC, no ETH), facilitator `0x271189c860DB25bC43173B0335784aD68a680908`. Endpoints
under `/x402/v3/cryptocurrency/quotes/latest` (+ listings, dex). **No x402
historical-OHLCV** → historical/preload stays on API-key `/v2`. See memory
`reference-cmc-x402`.

---

## L2 — CUSTODY & EXECUTION · Trust Wallet (TWAK)

| Resource | What it is | Our use | Depth |
|----------|-----------|---------|-------|
| **TWAK** (self-custody local signing) | keys on-device; optional autonomous mode | ALL trade signing via `twak` CLI (`agent/twak_cli.py` + `TwakSwapExecutor`); **zero raw keys in code**; `EXECUTION_BACKEND=twak` | 🟢 core |
| **MCP-REST** | drop into Claude/Cursor/LangChain | available as agent tooling | 🟡 partial |
| **Native x402** (agent charges per call, on-chain settle) | *provide* a paid endpoint | **untapped** — expose our regime/signal digest as a paid x402 endpoint → "consume AND provide x402" | 🔴 opportunity |
| **Open-source reference agents** | fork → testnet day one | reference for the execution path | 🟡 |

**Differentiator:** full self-custody with multi-step signed sequences (e.g.
margin deposit + open perp), keys never touch code or logs. The native-x402
provider angle would make us one of the few teams using x402 on *both* sides.

---

## L3 — CHAIN & SDK · BNB Chain (BNB AI Agent SDK)

| Resource | What it is | Our use | Depth |
|----------|-----------|---------|-------|
| **BNB AI Agent SDK** | agent-native primitives on BSC | drives PancakeSwap; simulate-before-send; receipt = ledger truth | 🟢 core |
| **BSC Mainnet** | low-fee, ~1s confirms | live execution venue; gas from real fills feeds the cost model | 🟢 core |
| **PancakeSwap + BSC Perps** | the DEX + perps venue | spot V3 swaps (longs), perps (shorts, ≤2x, regime-gated); V3 calldata in `core/exec/bnb.py` | 🟢 built (testnet) |
| **Quickstart Templates** | reference integrations | bootstrap reference | 🟡 |

**What PancakeSwap is:** the dominant DEX/AMM on BSC (BSC's Uniswap) plus
Perpetuals. It is the *venue* where every Alien-Trade trade executes — spot for
longs, perps for shorts. Not optional: it is L3's execution surface.

**Differentiator:** real gas + size-aware slippage + perp funding from actual
fills feed back into the backtest cost model — the sim charges what live charges,
so sim ≈ live (the parity invariant). Most teams backtest frictionless.

---

## Chain map (don't confuse the two)

| Purpose | Chain | Asset |
|---------|-------|-------|
| **Data payment (x402)** | Base (`eip155:8453`) | USDC |
| **Trade execution** | BNB Smart Chain (`eip155:56`) | BNB + tokens via PancakeSwap |

---

## Gap & opportunity backlog (prioritized — pure prize upside)

| # | Item | Layer | Effort | Why it matters |
|---|------|-------|--------|----------------|
| 1 | Fix `cmc_client.py` to use `/x402/v3/...` live paths | CMC | S | unblocks live x402 (prize evidence) |
| 2 | Wire **CMC MCP (12 tools)** into Second Brain research + co-pilot | CMC | M | deep CMC usage; richer research agent |
| 3 | **Publish Track-2 strategy as a CMC Skill** (Skills Marketplace) | CMC | M | one move → Skills Marketplace + Track 2 + CMC prize |
| 4 | **TWAK native x402 provider** — paid digest endpoint | TWAK | M | rare "both sides of x402" story for TWAK prize |
| 5 | Perps live path on mainnet (shorts) | BNB | M | completes spot+perps depth for BNB prize |
| 6 | Per-day x402 spend budget + cache-hit metric | CMC | S | $15 = ~1,500 calls; show metered, efficient spend |

---

## Prize checklist (what a judge should be able to see)

**CMC ($2k):** edge signals from derivatives/social/on-chain (not just price);
live x402 pay-per-call with on-screen spend; CMC MCP tools in the research loop;
a published CMC Skill. → items 1,2,3,6.

**TWAK ($2k):** 100% self-custody signing, zero keys in code/logs; multi-step
signed sequences; (stretch) native-x402 provider endpoint. → built + item 4.

**BNB SDK ($2k):** PancakeSwap spot + perps on BSC; simulate-before-send; real
gas/slippage feeding the cost model; receipt-as-truth ledger. → built + item 5.

---

## See also

`PROJECT_PLAN.md` (phases/risk), `STRATEGY.md` (signal edge), `AGENT_TEAM_PLAN.md`
(agent architecture), `STEPS.md` (runbook + current status), memory
`reference-cmc-x402` and `reference-twak-cli-execution`.
