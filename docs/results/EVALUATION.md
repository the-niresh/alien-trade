# Evaluation results

Generated `2026-08-17T16:17:07+00:00` by `cd core && python -m evaluate`.

**These are simulated results, not live trading.** Hourly bars from disk, replayed
through the same `/core` strategy the live agent uses, with the full BSC cost model
(gas, slippage, swap fees) charged on every fill.

- Window: `2024-12-18` → `2026-06-11` (540d_1h, 12960 bars per token)
- Starting capital: $10,000
- Parameter search: none - fixed presets from strategy/registry.py

## Benchmarks over the same window

Two things to beat. Buy-and-hold is the obvious one. **Cash is the one that
matters here** - this is a long-only strategy that holds USDT by default, so
switching it off is a real, available alternative that returns exactly 0%.

| Benchmark | Return | Max drawdown |
|---|---|---|
| **Cash (agent switched off)** | **+0.00%** | **0.00%** |
| Buy and hold ETH | -57.73% | -69.15% |
| Buy and hold CAKE | -56.66% | -74.84% |
| Buy and hold UNI | -84.03% | -85.36% |
| Buy and hold LINK | -72.11% | -74.68% |
| Buy and hold AAVE | -83.04% | -84.94% |

## Strategy - risk engine OFF (strategy alone)

| Preset | Token | Trades | Return | Sharpe | Sortino | Max DD | Win rate |
|---|---|---|---|---|---|---|---|
| momentum | ETH | 94 | -25.65% | -0.778 | -0.587 | -26.02% | 13.8% |
| momentum | CAKE | 104 | -24.37% | -0.412 | -0.419 | -29.39% | 17.3% |
| momentum | UNI | 92 | -26.73% | -0.548 | -0.512 | -26.73% | 12.0% |
| momentum | LINK | 89 | -26.46% | -0.742 | -0.586 | -27.73% | 14.6% |
| momentum | AAVE | 99 | -32.38% | -0.872 | -0.675 | -33.24% | 19.2% |
| contrarian | ETH | 435 | -100.00% | -1.469 | -0.492 | -100.00% | 0.9% |
| contrarian | CAKE | 450 | -100.00% | -1.373 | -0.699 | -100.00% | 2.4% |
| contrarian | UNI | 437 | -100.00% | -1.174 | -0.386 | -100.00% | 1.4% |
| contrarian | LINK | 440 | -100.00% | -1.215 | -0.594 | -100.00% | 2.5% |
| contrarian | AAVE | 448 | -100.00% | -0.794 | -0.290 | -100.00% | 3.8% |
| balanced | ETH | 57 | -17.08% | -0.522 | -0.475 | -17.10% | 17.5% |
| balanced | CAKE | 62 | -12.21% | -0.173 | -0.195 | -18.70% | 19.4% |
| balanced | UNI | 68 | -21.57% | -0.378 | -0.388 | -21.85% | 13.2% |
| balanced | LINK | 57 | -19.38% | -0.516 | -0.445 | -19.69% | 17.5% |
| balanced | AAVE | 57 | -18.48% | -0.473 | -0.425 | -18.95% | 19.3% |
| defensive | ETH | 23 | -10.81% | -0.679 | -0.207 | -10.92% | 0.0% |
| defensive | CAKE | 19 | -4.27% | -0.112 | -0.114 | -8.70% | 21.1% |
| defensive | UNI | 32 | -11.72% | -0.338 | -0.218 | -12.58% | 12.5% |
| defensive | LINK | 27 | -12.67% | -0.619 | -0.394 | -12.77% | 7.4% |
| defensive | AAVE | 31 | -12.95% | -0.573 | -0.362 | -13.59% | 12.9% |

## Strategy - risk engine ON

| Preset | Token | Trades | Return | Sharpe | Sortino | Max DD | Win rate |
|---|---|---|---|---|---|---|---|
| momentum | ETH | 16 | -4.29% | -0.508 | -0.067 | -4.29% | 0.0% |
| momentum | CAKE | 12 | -0.93% | -0.100 | -0.016 | -1.43% | 25.0% |
| momentum | UNI | 8 | -2.33% | -0.372 | -0.047 | -2.33% | 0.0% |
| momentum | LINK | 9 | -2.04% | -0.316 | -0.048 | -2.36% | 0.0% |
| momentum | AAVE | 5 | -0.92% | -0.161 | -0.023 | -1.66% | 20.0% |
| contrarian | ETH | 110 | -11.94% | -1.656 | -0.383 | -11.94% | 0.0% |
| contrarian | CAKE | 117 | -7.65% | -1.443 | -0.286 | -7.65% | 0.9% |
| contrarian | UNI | 90 | -9.52% | -1.365 | -0.338 | -9.52% | 2.2% |
| contrarian | LINK | 86 | -5.84% | -0.942 | -0.193 | -5.84% | 4.7% |
| contrarian | AAVE | 33 | -2.91% | -0.829 | -0.090 | -2.91% | 0.0% |
| balanced | ETH | 5 | -2.79% | -0.443 | -0.033 | -2.79% | 0.0% |
| balanced | CAKE | 61 | -2.95% | -0.304 | -0.107 | -3.77% | 19.7% |
| balanced | UNI | 5 | -2.39% | -0.342 | -0.028 | -2.39% | 0.0% |
| balanced | LINK | 9 | -3.03% | -0.366 | -0.038 | -3.03% | 0.0% |
| balanced | AAVE | 8 | -2.28% | -0.486 | -0.060 | -2.28% | 0.0% |
| defensive | ETH | 5 | -2.67% | -0.409 | -0.028 | -2.72% | 0.0% |
| defensive | CAKE | 19 | -2.95% | -0.363 | -0.068 | -3.14% | 15.8% |
| defensive | UNI | 7 | -2.38% | -0.434 | -0.046 | -2.39% | 0.0% |
| defensive | LINK | 6 | -2.07% | -0.297 | -0.025 | -2.39% | 0.0% |
| defensive | AAVE | 5 | -2.06% | -0.445 | -0.041 | -2.08% | 0.0% |

## Reading of the result

- **0 of 40 configurations finished above break-even.**
- 0 of 40 beat holding cash.
- 5 lost the entire account (−100%): contrarian with the risk engine off.

No preset is profitable on any token on the allowlist. This is not a tuning
problem - the sign is wrong across every combination tested, so there is no
parameter set in this family worth searching for. The signals as combined here
do not carry an edge that survives trading costs.

The strategy does beat buy-and-hold, but that is not evidence of skill: it is
long-only and mostly in cash, so it was always going to fall less than a market
that halved. The benchmark that decides whether the agent earns its existence is
cash, and it loses to cash everywhere.

The risk engine is the part that works. It cuts the worst case from a total
wipeout to a few percent - it cannot manufacture an edge, only limit the damage
of not having one.

### Accounting integrity

40 of 40 runs asked the engine for something impossible - selling more than held, or buying
with cash that was not there. The engine refused and sized each fill to what was
actually available, so nothing above is inflated by it. Before that clamp existed
these same requests created $46,814 of cash out of nothing on a single token.

The cause is a gap in the strategy interface, not a rounding error. `StrategyFn`
receives only bars - it is never told the position or the cash. So a strategy has
no way to size an exit against what it actually holds, and every strategy ends up
either shadowing the account itself or guessing. The risk engine shadows it, which
is why its counts are small (slippage drift between its copy and the engine's); a
bare strategy guesses, which is why its counts are large.

The durable fix is to pass the real position and cash into the strategy call, so
there is one set of books. Until then the engine is the authority and clamps.

Largest single offender: `contrarian`/UNI (risk engine off) - 1710 oversized sells, 1453 underfunded buys.
