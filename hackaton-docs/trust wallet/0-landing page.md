BNB Hack: AI Trading Agent Edition is live — build with TWAK · $36k pool
Register on DoraHacks →
Quickstart
Capabilities
Integrate
Trust Models
Docs
Get API Credentials →
BNB Hack · $36k pool
Build a self-custody AI trading agent. Win the BNB Hack.

Powered by Trust Wallet AgentKit (TWAK) — self-custody signing across 30+ chains with native x402, plus CoinMarketCap data and the BNB AI Agent SDK. Keys never leave the user.
Track 1 · Autonomous Trading Agents · $24k · flagshipTrack 2 · Strategy Skills · $6k+ 3 special prizes · $2k each
Registration open · build to Jun 21Prize pool · $36k
Register on DoraHacks ↗
TWAK CLI + MCP server live
The agent layer
for self-custody
crypto.

MCP server, CLI, and SDK that give AI agents the power to read, transact, and automate across 25+ chains — without ever holding your users' keys.
Get API Credentials→
Read the docs
Plug into
ClaudeCursorVS CodeLangChain
Start in 60 seconds
$ curl -fsSL https://agent-kit.trustwallet.com/install.sh | bash  ✓ twak installed  ✓ credentials saved  ✓ Claude Code wired # Now ask Claude:# "Swap 100 USDC for ETH on Arbitrum"›

curl -fsSL https://agent-kit.trustwallet.com/install.sh | bash

Installer auto-wires Claude Code, Cursor, and more.
Get my keys →
25+ chains, one integration
EthereumSolanaBitcoinArbitrumBasePolygonBNB ChainOptimismAvalancheCosmosTONAptosTronNEARSuiEthereumSolanaBitcoinArbitrumBasePolygonBNB ChainOptimismAvalancheCosmosTONAptosTronNEARSui
/ 02 — Integrate
Two ways in. Same primitives.

Whether you're shipping with Claude in an afternoon or building a production agent stack, the surface is the same. Pick what fits your team.
A — Conversational
MCP Server

Your AI agent calls the tools.Plug Trust Wallet into any MCP-compatible client — Claude, Cursor, Windsurf, GitHub Copilot, Cline, Codex, and more. They read balances, fetch prices, and propose transactions through natural language, wired up in minutes.
# claude_desktop_config.json
{
  "mcpServers": {
    "twak": {
      "command": "twak",
      "args": ["serve"]
    }
  }
}
VS
B — Programmatic
CLI

Shell-capable agents call the CLI. Claude Code, Codex, and any agent with shell access run twakdirectly. Or wire it into your own agent loop, scripts, CI jobs, or cron — same auth, same surface as the MCP server.
# what your agent runs:
$ twak price ETH
  ETH  $2,286.20  ethereum
$ twak swap 100 USDC ETH --quote-only
  100 USDC → 0.0241 ETH via Jupiter
$ twak alert create --token BTC --above 75000
  Alert created: alt_8f3c2d
$ twak wallet portfolio
  $12,450 · ETH 3.2 · SOL 18.4 · 6 chains
/ 03 — Capabilities
Six primitives. One toolkit.

Wallet, trade, market data, payments, automation, and fiat on/off-ramp — exposed as Skills for conversational clients and as APIs for programmatic ones.
P · 01
Wallet & Identity

Dual-mode by design. Run an autonomous agent wallet with rules, or connect to a user’s existing Trust Wallet via WalletConnect. Self-custody always — keys never leave the user.
Agent WalletWalletConnectSelf-custody
P · 02
Trade & Swap

Cross-chain swaps with the broadest coverage in the industry: EVM, Solana, Bitcoin, Cosmos, TON, Aptos, Tron, NEAR, and Sui — routed for best execution.
25+ chainsBest-routeRisk-scored
P · 03
Market Data

Live prices, on-chain metrics, token risk signals, ENS resolution. Fast, structured, agent-ready.
RealtimeRisk scoreENS
P · 04
Payments · x402

Per-call API gating built on the x402 protocol. Charge agents for access. Pay services autonomously. The payment rail for the agent economy.
x402MicropaymentsPer-call gating
P · 05
Automation

DCA strategies, limit orders, price alerts, scheduled execution. Configure once, your agent runs continuously within the rules you set.
DCALimit ordersTriggers
P · 06
Fiat On & Off-Ramp

Buy and sell crypto with fiat — cards, bank transfers, and regional payment methods. Routed through trusted providers, exposed as a single agent-ready primitive.
On-rampOff-rampFiat
/ 04 — Trust Models
One toolkit.
Two trust models.
“AI can understand what a user wants to do with their money — but it needs a trusted layer before it can safely act on it.”
— Felix Fan, CEO
Mode A · Autonomous
Agent Wallet

A dedicated wallet for the agent. Rules set upfront — assets, limits, strategies. The agent operates autonomously within them. No per-transaction approval.

    Best for
    DCA, limit orders, scheduled execution, recurring buys
    Approval
    Once at setup, then autonomous
    Custody
    Dedicated key, scoped & revocable
    Use case
    Production automations & strategies

Mode B · User-in-the-loop
WalletConnect

The agent connects to the user's existing Trust Wallet. It proposes transactions; the user reviews and approves each one. Maximum sovereignty, zero new keys.

    Best for
    Research, copilots, advisory flows, retail UX
    Approval
    Per-transaction, by the user
    Custody
    User's existing keys, untouched
    Use case
    Consumer agents, AI copilots

/ 05 — Quickstart
From zero to shipping agentin 60 seconds.

    Run the installer

    curl -fsSL https://agent-kit.trustwallet.com/install.sh | bash installs the CLI, prompts for your API credentials, and wires the agent harness you pick. macOS, Linux, WSL.
    Paste your credentials when prompted

    Grab your Access ID and HMAC Secret from portal.trustwallet.com — the installer verifies them inline and saves to ~/.twak/ + your OS keychain.
    Pick a wallet path

    Create a non-custodial agent wallet for signing, use WalletConnect with your existing wallet, or skip and stay read-only. The installer asks — pick one.
    Ship

    Your harness now spawns twak serve on demand, exposing every command as MCP tools for Claude, Cursor, and Codex. Or call the CLI directly from your stack.

~/quickstart
# One command. macOS, Linux, WSL.$ curl -fsSL https://agent-kit.trustwallet.com/install.sh | bash   ▸ installing @trustwallet/cli…  ✓ twak v0.12.0 installed # Step 1 of 3 — API credentials  Access ID: abc12345  HMAC secret: ●●●●●●●●  ✓ verified · saved to ~/.twak # Step 2 of 3 — Wire your harness  [x] Claude Code · [x] Cursor  ✓ wired 2 harnesses # Step 3 of 3 — Wallet  Create a wallet or skip? Create  ✓ HD wallet ready · 25+ chains ✓ Setup complete.
Self-custody, now agentic.

Your keys. Your rules. Your AI.
Start building→
Talk to the team

The agent layer for self-custody crypto.
Product

    Capabilities
    Integrations
    Trust Models
    Quickstart

Developers

    Documentation
    Quickstart
    SDK Reference
    GitHub

Company

    Blog
    Careers
    Contact
    Brand

© 2026 Trust Wallet · Builders
Privacy
Terms
