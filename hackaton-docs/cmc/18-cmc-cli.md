# CMC CLI

GitHub repo: [coinmarketcap-official/CoinMarketCap-CLI](https://github.com/coinmarketcap-official/CoinMarketCap-CLI)

Use this skill when your agent should work through the CoinMarketCap CLI instead of direct REST calls or MCP tools.

## Prerequisites

Before using this skill, set up the CLI runtime:

```bash
brew install coinmarketcap-official/CoinMarketCap-CLI/cmc
cmc auth
cmc status -o json
```

If you have not installed the CLI yet, start with the [CoinMarketCap CLI runtime page](/ai-agent-hub/cmc-cli).

## Quick Reference

| Need | Use | Notes |
|---|---|---|
| Exact asset lookup | `resolve` | Prefer `--id`, `--slug`, or `--symbol` for deterministic identity. |
| Quote and enrichments | `price` | Add `--with-info` and `--with-chain-stats` when you need more context. |
| Search and discovery | `search` | Use for name, symbol, or chain-scoped address discovery. |
| Market scan | `markets`, `trending`, `top-gainers-losers` | Use `-o table` when a human is reading the terminal output. |
| Time series | `history` | Use `--interval 5m|hourly|daily` only where supported by plan. |
| Global context | `metrics`, `news`, `pairs` | Good bundle commands when you need broader market context. |
| Live monitoring | `monitor` | Polling only, not websocket streaming. |
| Interactive inspection | `tui` | Human-facing terminal workflow, not for scripting. |

## Workflow

1. Use `resolve` when the user already knows the asset and you need a stable identifier.
2. Use `search` when the user knows a name, symbol, or contract address but not the exact identity.
3. Use `price` for quotes, then add enrichments only when they are needed.
4. Use `markets`, `trending`, `top-gainers-losers`, `metrics`, `news`, or `pairs` for broader market context.
5. Use `tui` only when a human wants an interactive terminal view.

## Output Rules

- Default output is compact JSON.
- Use `-o table` for readable terminal output.
- Use `--dry-run` to inspect request shape without calling the API.
- Keep identity flags explicit when determinism matters.

## Slash Command Note

This skill does not create a built-in `/cmc` slash command by itself.

- Treat `CMC CLI` as reusable skill guidance on top of the `cmc` runtime.
- Whether an agent host shows it as a slash command, a skill card, or contextual workflow depends on that host's own registration model.
- For environments such as Claude Code or OpenClaw, a `/cmc` command would only appear if that host explicitly maps this skill to a slash-command alias or wrapper.

## Common Mistakes

- Do not use `search` as an exact-lookup replacement when `resolve` is available.
- Do not send scripting workloads to `tui`.
- Do not split a bundle into smaller commands unless the user asked for the narrow view.
- Do not assume every numeric or token-like string should map cleanly to a symbol.

## Example Commands

```bash
cmc resolve --id 1
cmc price --id 1 --with-info --with-chain-stats -o json
cmc history --id 1 --days 30 --dry-run -o json
cmc markets --limit 20 -o table
```
