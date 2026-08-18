export type ScoringImpact = "scored" | "neutral" | "operator";
export type Transport    = "policy" | "read" | "imperative";
export type Sponsor      = "TWAK" | "CMC" | "BNB_SDK" | "agent";

export interface SponsorControl {
  id: string;
  label: string;
  description: string;
  sponsor: Sponsor;
  transport: Transport;
  scoringImpact: ScoringImpact;
  confirmRequired?: boolean;
  commandType?: string;
  readEndpoint?: string;
  configKey?: string;
}

export const SPONSOR_CONTROLS: SponsorControl[] = [
  // ── Autonomous (Scored) - policy transport ───────────────────────────────
  {
    id: "kill_switch",
    label: "Kill Switch",
    description: "Immediately halts all autonomous trading. The agent stops executing swaps and waits for manual resume. This is the Tier-0 emergency stop - fastest path to flat. Uses the Convex config.halted flag read every cycle.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "halted",
  },
  {
    id: "trading_mode",
    label: "Trading Mode",
    description: "Controls whether the agent trades on mainnet (real TWAK-signed swaps), paper (simulated fills, no signing), or testnet. Only mainnet mode produces scored PnL. Switching to paper halts open positions safely.",
    sponsor: "TWAK",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "trading_mode",
  },
  {
    id: "strategy",
    label: "Strategy Selector",
    description: "Chooses the active /core strategy (momentum | contrarian | balanced | defensive). Each strategy has different signal weights and regime filters. The change takes effect at the next decision cycle - no restart needed.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "strategy_name",
  },
  {
    id: "equity_floor",
    label: "Equity Floor",
    description: "USD value below which the agent auto-halts. Capital preservation guardrail. When equity drops to this level the kill switch fires automatically. Set to 0 to disable. Evaluated each cycle after position mark-to-market.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "equity_floor",
  },
  {
    id: "rug_check_gate",
    label: "Rug-Check Gate",
    description: "When enabled, the agent calls TWAK `risk <asset>` before every swap. If the token's risk score exceeds the threshold (default 75/100) or isRug=true, the swap is blocked and an audit row is written. Uses the Trust Wallet Agent Kit's on-chain contract analysis.",
    sponsor: "TWAK",
    transport: "policy",
    scoringImpact: "scored",
    configKey: "rug_check_enabled",
  },
  {
    id: "x402_budget",
    label: "x402 Budget Cap",
    description: "Maximum USD the agent may spend per cycle on x402 micropayments to CMC data endpoints. When the cumulative spend exceeds this cap for the cycle, the agent falls back to cached data. Demonstrates both CMC x402 and TWAK EIP-3009 signing depth.",
    sponsor: "CMC",
    transport: "policy",
    scoringImpact: "neutral",
    configKey: "x402_budget_usd",
  },
  // ── Operator-only policy ─────────────────────────────────────────────────
  {
    id: "position_size",
    label: "Position Size (USD)",
    description: "Maximum USD amount per individual swap. Acts as a per-trade size cap independent of total equity. Reducing this limits exposure on any single trade. The agent will not exceed this value even if the risk engine allows a larger position.",
    sponsor: "agent",
    transport: "policy",
    scoringImpact: "operator",
    configKey: "position_size_usd",
  },
  // ── Read queries (no signing) ────────────────────────────────────────────
  {
    id: "portfolio_refresh",
    label: "Portfolio Refresh",
    description: "Fetches full multi-chain portfolio from the TWAK wallet (BNB, ETH, BSC tokens, SOL, TRON). Returns native balances, token holdings, and total USD. Read-only - no signing. Cached in Convex wallet_state for the Portfolio view.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/portfolio",
  },
  {
    id: "risk_check",
    label: "Risk Check",
    description: "On-demand TWAK rug-risk scan for any token. Returns isRug, riskScore (0-100), and flags (honeypot, blacklist, sell-tax, LP-lock status). Same data the rug-check gate uses pre-swap. Reference: Trust Wallet Agent SDK risk endpoint.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/risk",
  },
  {
    id: "price_query",
    label: "Price Query",
    description: "Real-time price for any token via the TWAK pricing feed. Supports all chains TWAK tracks. The same source the agent uses for mark-to-market each cycle.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/price",
  },
  {
    id: "trending_tokens",
    label: "Trending Tokens",
    description: "Top trending tokens on BNB Chain by price change, market cap, or volume. Categories: bnb, defi, ai, memes, rwa, launchpad. Powered by TWAK trending feed backed by Trust Wallet's on-chain activity data.",
    sponsor: "TWAK",
    transport: "read",
    scoringImpact: "neutral",
    readEndpoint: "/twak/trending",
  },
  // ── Imperative (TWAK-signed, operator tools) ─────────────────────────────
  {
    id: "dca_setup",
    label: "Setup DCA",
    description: "Create a recurring USDT→token swap on a fixed interval (hourly, daily, weekly). Runs as a TWAK automate job - the wallet signs each execution locally via EIP-3009 gasless transfer. Each execution is audited in the Convex audit log with tx hash.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "automate_add",
  },
  {
    id: "limit_order",
    label: "Limit Order",
    description: "Set a TWAK limit-order automation that fires a swap when price crosses above/below a target. The agent monitors price and triggers `twak automate` when the condition is met. Self-custody: keys never leave the device.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "automate_add",
  },
  {
    id: "automate_pause",
    label: "Pause Automation",
    description: "Pause an active DCA or limit-order automation by ID. The automation is preserved in storage but stops executing. Resume it at any time without reconfiguring.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "automate_pause",
  },
  {
    id: "alert_create",
    label: "Price Alert",
    description: "Create a TWAK price alert for any token. Fires when price crosses above or below a threshold. Alerts are stored in the TWAK wallet's alert registry and checked on-chain. Results appear in the Convex audit log.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "alert_create",
  },
  {
    id: "erc20_approve",
    label: "ERC-20 Approve",
    description: "Grant a spender contract allowance to use a specific ERC-20 token from the agent wallet. Required before some DeFi interactions. TWAK signs the approval transaction locally - amount is capped to reduce over-approval risk.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "erc20_approve",
  },
  {
    id: "erc20_revoke",
    label: "ERC-20 Revoke",
    description: "Revoke an existing ERC-20 allowance. Sets approval to zero. Use after a DCA run completes or if a spender contract is no longer trusted. Signed locally via TWAK, audited in Convex.",
    sponsor: "TWAK",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "erc20_revoke",
  },
  {
    id: "x402_request",
    label: "x402 Pay-per-Call",
    description: "Pay for a premium CMC data endpoint using the TWAK x402 protocol (EIP-3009 gasless micropayment). The wallet signs an on-chain payment authorization - no gas required. The CMC server validates the payment proof and returns the data. Demonstrates CMC x402 + TWAK signing depth together.",
    sponsor: "CMC",
    transport: "imperative",
    scoringImpact: "operator",
    confirmRequired: true,
    commandType: "x402_request",
  },
];

export function getControlsByTransport(transport: Transport): SponsorControl[] {
  return SPONSOR_CONTROLS.filter((c) => c.transport === transport);
}

export function getControlsBySponsor(sponsor: Sponsor): SponsorControl[] {
  return SPONSOR_CONTROLS.filter((c) => c.sponsor === sponsor);
}

export function getControlById(id: string): SponsorControl | undefined {
  return SPONSOR_CONTROLS.find((c) => c.id === id);
}
