CoinMarketCap MCP for Claude Code

Use the CoinMarketCap MCP server with Claude Code to access live crypto prices, market data, technical analysis, and more — directly from your terminal.
Prerequisites

    Active Claude subscription (Pro, Max, or API access)
    Claude Code installed (npm install -g @anthropic-ai/claude-code)

Setup

    Get your API key

    Sign up or log in at pro.coinmarketcap.com to get your API key.

    Add the CoinMarketCap MCP server

    Run the following command to register the MCP server:

    Code
    claude mcp add cmc-mcp \
      --transport http \
      --url https://mcp.coinmarketcap.com/mcp \
      --header "X-CMC-MCP-API-KEY: your-api-key"

    Replace your-api-key with your actual CoinMarketCap API key.

    Verify the connection

    Start Claude Code and ask: "What tools do you have available?"

    Code
    claude

    You should see CoinMarketCap tools listed in the available tools.

Install Skills (optional)

Install CoinMarketCap skills for structured market analysis and token research workflows:

Code
npx skills add https://github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap

This adds skills for market reports, crypto research, and API integration.
What you can do

Once connected, ask Claude Code things like:

    "What's the current price of Ethereum?"
    "Give me a full market report"
    "Research LINK — is it worth holding?"
    "What's the Fear & Greed index right now?"
    "Show me trending crypto narratives"
    "Help me build a portfolio tracker using the CMC API"
