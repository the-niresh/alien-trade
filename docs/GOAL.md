# GOAL — what the agent is optimising for, and how we score it

This is the single definition of the agent's goal: the **objective** it optimises,
the **scorecard** the judges (and we) read, and the **rule adherence** it must never
violate. It is not aspirational prose — every line here maps to a number computed in
[`core/scorecard.py`](../core/scorecard.py) and surfaced live in the Convex
`scorecard` singleton (read by the glass cockpit).

> Sim and live share `core/scorecard.py` (locked decision #2). The backtest scores a
> `BacktestResult`; the live runtime scores the same shapes built from real fills.
> "How we'd be judged in sim" and "how we're judged live" can never drift.

---

## 1. The objective (the one number we optimise)

The goal is **not** raw profit. It is the Track-1 judging objective — risk-adjusted
return with an explicit drawdown penalty (CLAUDE.md decision #6, enforced in
`core/strategy/optimizer.py`):

```
objective  =  Sortino_oos  −  λ · |max_drawdown_oos|        (λ = 2.0)
```

- **Sortino**, not Sharpe, is primary — it penalises *downside* volatility only, which
  is what "drawdown-first" means.
- **λ = 2.0** is shared between the optimizer (which *selects* params on the train
  objective) and the scorecard (which *scores* the realised one). Same lambda, same goal.
- Out-of-sample only. We never report or select on in-sample numbers
  (CLAUDE.md decision #7).

Everything below is either an **input** to this objective, a **scorecard line** the
judges read alongside it, or a **rule-adherence** fact.

---

## 2. The scorecard

The metric groups the judging rubric rewards, what each means, and where it comes from.
✅ = already computed · 🆕 = added with the scorecard module.

### Returns — *how much money it made*
| Line | Meaning | |
|---|---|---|
| `total_return` | net return vs initial capital | ✅ |
| `net_pnl_usd` | absolute PnL in USD | ✅ |

### Drawdown — *how much it lost in bad periods* (depth **and** time)
| Line | Meaning | |
|---|---|---|
| `max_drawdown` | deepest peak-to-trough fall | ✅ |
| `max_drawdown_duration_days` | longest time spent below a prior peak before recovering | 🆕 |

Over a 7-day live window, *how long* you are underwater is scored as much as *how deep*.

### Risk-adjusted performance — *profit relative to risk taken*
| Line | Meaning | |
|---|---|---|
| `sortino` | return per unit of downside risk (**primary**) | ✅ |
| `sharpe` | return per unit of total volatility | ✅ |
| `calmar` | return per unit of max drawdown | ✅ |

### Consistency — *steady beats spiky*
| Line | Meaning | |
|---|---|---|
| `pct_positive_days` | fraction of days that closed up | 🆕 |
| `daily_pnl_vol` | volatility of daily PnL (lower is better) | 🆕 |

### Trade quality
| Line | Meaning | |
|---|---|---|
| `win_rate` | fraction of trades profitable | ✅ |
| `profit_factor` | gross win ÷ gross loss | 🆕 |
| `expectancy_usd` | average PnL per trade | 🆕 |
| `avg_win_usd` / `avg_loss_usd` | average winning / losing trade | 🆕 |
| `worst_trade_usd` | single worst loss (tail) | 🆕 |

### Cost efficiency — *does the edge survive real BSC costs?*
| Line | Meaning | |
|---|---|---|
| `total_cost_usd` | gas + slippage + fees, summed across fills | ✅ per-fill, 🆕 aggregated |
| `cost_ratio` | total costs ÷ gross trading PnL (near 1.0 = costs ate the edge) | 🆕 |

This is the line that proves the alpha is real after PancakeSwap fees + BSC gas +
slippage — the BNB / real-fill story.

### Exposure efficiency — *returns earned without running hot*
| Line | Meaning | |
|---|---|---|
| `turnover` | traded volume ÷ average equity | ✅ |
| `avg_exposure_pct` / `peak_exposure_pct` | average / peak open exposure vs equity | 🆕 (needs live exposure curve) |

### Autonomy — *it's an autonomous agent; staying alive unattended is the point*
Facts the runtime supplies (`OperationalStats`); all zero/None in sim.
| Line | Meaning |
|---|---|
| `cycles_total` / `cycles_unattended` | decision cycles run, and how many with no manual intervention |
| `uptime_pct` | fraction of the live window the loop was alive |
| `n_recoveries` | crash-recovery resumes (`agent/recovery.py`) |

---

## 3. Rule adherence — *did it respect the constraints we defined?*

Scored as a **binary pass + a violation count (target: 0)** against the hard guardrails
in [`core/risk/guardrails.py`](../core/risk/guardrails.py). The agent already *enforces*
these every cycle; the scorecard *records* that it did (`RuleAdherence`).

| Constraint | Limit |
|---|---|
| Per-trade size cap | $2,000 |
| Max single position | 25% of capital |
| **Max cumulative open exposure** | 30% of equity (the max-exposure invariant) |
| Slippage abort | simulated > 2% |
| Token allowlist | BNB / BTC / BTCB / ETH |
| Daily-loss kill switch | halt if daily loss ≥ 5% |
| Consecutive-loss circuit breaker | pause after 5 back-to-back losses |

Recorded facts:
- `violations` — hard limits breached *at execution*. **Must be 0**; a non-zero value is
  a failure of the agent, not of the market.
- `blocks_fired` — trades a guardrail *correctly* blocked (this is the system working, not a violation).
- `kill_switch_activations` / `circuit_breaker_activations` — fired **and honoured**.
- `max_open_exposure_pct` — peak cumulative exposure actually reached (should stay ≤ 30%).

`rule_adherence_clean = (violations == 0)` is the denormalised badge the UI reads.

---

## 4. How it's wired

```
core/scorecard.py  ──compute_scorecard()──►  Scorecard
   │  (sim: scorecard_from_result(BacktestResult, capital))
   │  (live: same shapes from real fills + OperationalStats + RuleAdherence)
   │
   └─ .as_convex_row() ──► convex/scorecard.ts: update() ──► `scorecard` singleton
                                                                  │
                                            glass cockpit (PWA) ◄─┘  read-only "objective" panel
```

- **Compute**: `compute_scorecard(equity_curve, trades, fills, initial_capital, …)` —
  optional `timestamps` (enables duration + daily-consistency lines), `exposure_curve`
  (enables exposure lines), `operational`, `rule_adherence`.
- **Persist**: `Scorecard.as_convex_row()` produces the flat shape matching the Convex
  `scorecard` table; nullable lines stay `null` in sim (honest, never faked to 0).
- **Read**: `api.scorecard.get` — the live "how are we doing against the objective" panel.

### Remaining integration (not yet wired)
The module, table, and functions exist and are tested. To go live, the runtime
(`agent/runtime.py` / `agent/loop.py`) must, at window close (and optionally each cycle):
maintain an exposure curve + `OperationalStats` + `RuleAdherence`, call
`compute_scorecard(...)`, and `ctx.runMutation(api.scorecard.update, row)`.

---

## 5. Tests

`core/tests/test_scorecard.py` — objective formula, drawdown duration, daily
consistency, profit factor / expectancy, cost ratio, exposure lines, graceful
degradation without timestamps/exposure, Convex-row serialisability, and that
identical inputs score identically (the sim == live guarantee).
