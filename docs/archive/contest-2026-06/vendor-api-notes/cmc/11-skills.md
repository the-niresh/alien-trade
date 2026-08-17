CoinMarketCap AI Agent Hub

    For the complete CoinMarketCap API documentation index, see llms.txt. For a single-file dump of all documentation, see llms-full.txt.

Use this page to choose the fastest path through the CoinMarketCap AI Agent Hub for editors, assistants, and agents.
Choose your path
If you want to...	Start here	Best for
Use CoinMarketCap inside Cursor, Claude Code, or Windsurf	IDE integrations	Interactive coding, research, and agent-assisted development
Work directly in the terminal with a CoinMarketCap-native runtime	CMC CLI	Shell workflows, automation, and agent runs that benefit from stable command output
Connect any MCP-compatible client to live CMC data	MCP	Real-time tool access with an API key
Pay per request without managing an API key	x402	Experiments, episodic usage, and agent workflows with on-chain payment
Reuse pre-built workflows like market reports and token research	Skills for AI Agents	Faster repeatable workflows on top of MCP, x402, or direct API integrations
Build your own application logic instead of using AI-specific tooling	REST API docs	Custom backends, apps, and integrations
Fastest way to get started

    If you want the quickest hands-on experience, start with an IDE integration and connect the CoinMarketCap MCP server.
    If you want a shell-native workflow with stable output contracts, start with CMC CLI.
    If you already know you want a protocol-level integration, choose MCP or x402 directly.
    If you want reusable prompts and workflows, start with Skills after you choose your underlying data-access path.

IDE Integrations

Connect the CoinMarketCap MCP server to your IDE so the AI assistant can access live crypto prices, market data, technical analysis, and more while you code.
Cursor
Add CMC MCP to Cursor for real-time crypto data in chat.
Claude Code
Connect CMC MCP to Claude Code for terminal-based crypto intelligence.
Windsurf
Give Cascade access to CMC data via MCP.
Choose between MCP and x402

    Use CMC CLI when you want terminal-native access, automation, and reproducible command-line workflows.
    Use MCP when you have a CoinMarketCap API key and want stable real-time access in an IDE or another MCP-compatible client.
    Use x402 when you want pay-per-request access and do not want to manage an API key or subscription for the integration itself.
    Use Skills when you want reusable workflows layered on top of MCP, x402, or direct REST API integrations.

Terminal-native workflows

Use the CoinMarketCap CLI when you want to stay close to the shell and keep the workflow scriptable.
CMC CLI
Install a terminal-native CoinMarketCap runtime for JSON output, CSV export, dry-run previews, and interactive terminal workflows.
Data access protocols

These are the two protocol-level ways to connect AI agents to live CoinMarketCap data:
x402
Pay-per-request data access via USDC on Base. No API key or subscription required — just $0.01 per request.
MCP
Model Context Protocol server for real-time crypto data. Connect any MCP-compatible client to CoinMarketCap.
Skills for AI Agents

Skills are pre-built workflows that help an AI agent use CoinMarketCap data more effectively. Use them when you want repeatable behavior such as market reports, token research, or direct API integration patterns.
Category	Skills	What they do
MCP Skills	CMC MCP, Market Report, Crypto Research	Real-time data via MCP — prices, technical analysis, holder metrics, market reports, and token due diligence
x402 Skills	CMC x402	Pay-per-request data access with on-chain USDC payments, including MCP endpoint for AI agents
API Integration Skills	Crypto, DEX, Exchange, Market	Direct REST API integration covering cryptocurrency, DEX, exchange, and market-wide data

If you want a terminal-native runtime instead of a reusable skill, use CMC CLI.
Browse all skills
View the full catalog of skills with installation instructions and detailed documentation.
What a first success looks like

    IDE integration: your editor can list CoinMarketCap tools and answer a live market question
    CMC CLI: your terminal can return stable JSON or table output for a live market command
    MCP: your client can connect to https://mcp.coinmarketcap.com/mcp and discover tools
    x402: your request receives a 402 Payment-Required response and then succeeds after payment handling
    Skills: your agent can run a structured workflow such as a market report or token research task

AI agent integrations in the hub are in beta. Features and setup steps may change.
