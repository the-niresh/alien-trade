CMC x402

GitHub repo: coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap

Pay-per-request crypto market data powered by the x402 protocol. Access CoinMarketCap endpoints instantly with on-chain USDC payment. No API key or subscription required.
What is x402?

x402 is an open payment protocol developed by Coinbase that enables automatic stablecoin payments over HTTP. Instead of managing API keys, you pay $0.01 USDC per request on Base. The x402 client library handles payment signing automatically.

Learn more: https://docs.x402.org
Prerequisites

    Node.js 18+ and npm installed
    Base network wallet with a private key you control
    USDC on Base to pay for requests ($0.01 per request)
    Small amount of ETH on Base for gas fees

Quick Start

Install the x402 TypeScript SDK:

Code
npm install @x402/axios @x402/evm viem

Fetch data with automatic payment:

Code
import { createX402AxiosClient } from "@x402/axios";
import { ExactEvmScheme, toClientEvmSigner } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, http } from "viem";
import { base } from "viem/chains";

// SECURITY: Never hardcode private keys in source code.
// Use environment variables: process.env.PRIVATE_KEY
const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${string}`);
const publicClient = createPublicClient({ chain: base, transport: http() });
const signer = toClientEvmSigner(account, publicClient);

const client = createX402AxiosClient({
  schemes: [new ExactEvmScheme(signer)],
});

const response = await client.get(
  "https://pro-api.coinmarketcap.com/x402/v3/cryptocurrency/quotes/latest",
  { params: { symbol: "BTC,ETH" } }
);

console.log(response.data);

Endpoints

Base URL: https://pro-api.coinmarketcap.com
Endpoint	Path	Use For
Quotes	/x402/v3/cryptocurrency/quotes/latest	Current prices for specific coins
Listings	/x402/v3/cryptocurrency/listings/latest	Top coins by market cap
DEX Search	/x402/v1/dex/search	Find DEX tokens by keyword
DEX Pairs	/x402/v4/dex/pairs/quotes/latest	DEX pair trading data

All parameters from the standard CMC Pro API work with x402 endpoints.
Use Cases

    Get current prices for specific coins: Use /x402/v3/cryptocurrency/quotes/latest with symbol or id parameter
    List top cryptocurrencies: Use /x402/v3/cryptocurrency/listings/latest with limit parameter
    Search for DEX tokens: Use /x402/v1/dex/search with keyword parameter
    Get DEX pair trading data: Use /x402/v4/dex/pairs/quotes/latest with pair address
    AI agent data access: Use the MCP endpoint at https://mcp.coinmarketcap.com/x402/mcp

MCP for AI Agents

The x402 MCP endpoint lets AI agents access CMC data with automatic payment.

Connection URL:

Code
https://mcp.coinmarketcap.com/x402/mcp

Transport: Streamable HTTP (POST)

Connect using any MCP client with an x402-aware HTTP transport. The server exposes the same tools as the REST endpoints and supports automatic tool discovery.
Pricing

$0.01 USDC per request on Base (Chain ID: 8453).

Payment only occurs on successful data delivery. If the request fails, no payment is deducted.
Resources

    x402 Protocol
    x402 Documentation
    x402 GitHub
    CMC API Documentation
