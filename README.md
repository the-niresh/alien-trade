# Alien-Trade

An autonomous crypto trading agent that runs itself: it reads the market every hour,
decides whether to buy or sell, signs its own transactions, and keeps a full record of
why it did each thing.

I built it, then I measured it properly. **The measurement says the trading strategy
does not work.** That result is published below rather than hidden, because the point of
building a test harness is to believe it when it tells you something you don't want to
hear.

[![CI](https://github.com/the-niresh/alien-trade/actions/workflows/ci.yml/badge.svg)](https://github.com/the-niresh/alien-trade/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Status](https://img.shields.io/badge/status-archived%20%C2%B7%20read--only-lightgrey)

**Live dashboard: [alientrade.niresh.tech](https://alientrade.niresh.tech)** — the real
cockpit, running on a VPS behind Traefik with a Let's Encrypt cert, reading live state from
Convex. The trading loop itself is stopped (see the result below), so the panels show the
last state it recorded rather than a moving equity curve.

---

## The result, up front

Four strategy settings × five tokens × risk engine on and off. **40 configurations.**
540 days of hourly price history. Real costs charged on every trade — network gas,
slippage, swap fees. No parameter tuning: these are the settings exactly as committed.

**0 of 40 made money.**

| Setting | Risk engine off | Risk engine on |
|---|---|---|
| momentum | −24% to −32% | −0.9% to −4.3% |
| contrarian | **−100%** (whole account, all five tokens) | −2.9% to −12% |
| balanced | −12% to −22% | −2.3% to −3.0% |
| defensive | −4.3% to −13% | −2.1% to −3.0% |

Two benchmarks over the same window:

| Benchmark | Return |
|---|---|
| **Cash — agent switched off** | **0.00%** |
| Buy and hold | −57% to −84% depending on the token |

It beats buy-and-hold, and that is not a point in its favour. It is long-only and mostly
sitting in cash, so of course it fell less than a market that halved. The benchmark that
decides whether this agent deserves to exist is **cash**, and it loses to cash in all
forty configurations. Switching it off was the better trade.

The risk engine is the piece that works: it cuts the worst case from losing the entire
account to a few percent. It cannot invent an edge — only limit the cost of not having one.

**Live record:** the agent traded real money on BSC mainnet for a few days in June 2026.
4 trades, **−$0.44** total, of which $0.43 was gas. The hold-cash default and the risk
caps meant a broken strategy cost 44 cents instead of the account.

There are no profits here, simulated or real.

Full 40-row table with Sharpe, Sortino and drawdown:
[`docs/results/EVALUATION.md`](docs/results/EVALUATION.md).

### Reproduce it

```bash
cd core
.venv/bin/python -m fetch_data     # public Binance data, no API key, ~1 min
.venv/bin/python -m evaluate       # ~8 min, writes docs/results/
```

Nothing is random and the history is fixed, so the same window gives the same numbers.

---

## The interesting part: my backtest was lying in my favour

Before any of the numbers above were true, three bugs had to be found. All three inflated
the result, and all three were completely silent — no exception, no failing test, no
warning. This is the part of the project I would actually want to talk about.

**1. The engine created money out of nothing.** On a sell it credited the full requested
proceeds to cash while clamping the position at zero. So a sell larger than the position
minted the difference. Over 540 days of ETH that added **$46,814 of imaginary cash** and
turned a −16% strategy into a reported **+452% return with a 0.45% max drawdown**.

**2. Exits were sized by the entry sizer.** The risk engine ran sell orders through
`compute_position_size` — volatility targeting, which only means something for a *new*
position. So exit sizes had no relationship to what was actually held: **180 of 180 sells**
asked for more than the position, and the engine happily emitted sells while flat. This is
what fed bug 1.

**3. Buys could spend cash that was not there.** No cash check on the buy path, so the
contrarian setting reported **−470%** — which is not a bad result, it is an impossible one.
You cannot lose 470% of your own money with no leverage. Any long-only number past −100%
is a bug report.

A +452% equity curve with almost no drawdown is the kind of chart people put in a README.
It was an accounting error. The lesson I actually took from this project is that a
measurement tool needs its own tests more urgently than the thing it measures — because
when it breaks, it breaks quietly and in the direction you were hoping for.

All three are fixed at the point that matters: the engine now refuses impossible fills,
counts every refusal on `BacktestResult`, and prints the count in every evaluation.
[`core/tests/test_accounting_integrity.py`](core/tests/test_accounting_integrity.py) pins
all three and I verified it fails on the old code — checking that a regression test actually
fails is the only thing that makes writing one worthwhile.

**What is fixed vs what is still wrong.** The clamp stops the corruption, but the reason the
strategy asked for the impossible in the first place is a design gap I have not closed:
`StrategyFn` receives only bars. It is never told the position or the cash. A strategy
therefore cannot size an exit against what it actually holds — it either shadows the account
itself (what the risk engine does, which is why its violation counts are small and only
drift by the slippage fraction) or it guesses (what a bare strategy does, which is why its
counts run into the thousands). The durable fix is to pass the real position and cash into
the strategy call so there is one set of books instead of two. Until then the engine is the
single authority and clamps, and the counters make every disagreement visible.

### A fourth one, from running the linter for the first time

`ruff` was configured in `pyproject.toml` and had never been run. It found six undefined
names. Five were missing type imports. One was real: `agent/loop.py` used `list_active` and
`_now` before either existed, so the entire spawned-agent scheduler raised `NameError` on
every single cycle — straight into a bare `except Exception: pass`. That feature had never
run once, and nothing ever said so.

### And the bug that hid the whole thing for weeks

The original report command ran on **daily** bars. At daily resolution this strategy trades
roughly once a year, so every test window held zero trades and printed `0.00%` across the
board. It looked harmless because it never traded. The live agent decides once an **hour**;
run it at the speed it actually runs and the loss is immediate. A green test measuring a
configuration nobody runs is worse than no test.

---

## What is actually built here

The trading idea failed. The system around it is the real work, and it is independent of
whether the strategy made money.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       LangGraph Supervisor                          │
│  Researcher ──► Strategist ──► Reflector ──► Historian (Co-pilot)   │
└───────────────────────┬─────────────────────────────────────────────┘
                        │  advisory only — never on the trade path
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  /core — Deterministic Python                       │
│  S1 Momentum  S2 Derivatives  S3 Sentiment  S4 On-chain Flow        │
│  RegimeDetector ──► SignalCombiner ──► RiskEngine ──► Order         │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │   TwakSwapExecutor (TWAK)  │  ← self-custody, zero raw keys
          │   simulate → sign → send   │
          └─────────────┬──────────────┘
                        │ on-chain receipt
          ┌─────────────▼──────────────┐
          │      Convex (real-time)    │  ← trades, decisions, ledger,
          │      state bus + UI bridge │     risk_state, config, audit
          └─────────────┬──────────────┘
                        │
          ┌─────────────▼──────────────┐
          │    Glass Cockpit (PWA)     │  ← React + Vite, installs on
          │                            │     home screen via service worker
          └────────────────────────────┘
```

### The language model never makes the trade decision

This is the decision I would defend hardest, and it is the reason the failure above was
*measurable* at all.

Every buy and sell comes from plain Python in `/core` — the same code in simulation and
in live trading, no separate paths. Given the same input it always returns the same
answer. So a backtest is meaningful: replaying history through it tells you exactly what
would have happened.

The model layer does four things, all of them off the critical path and all of them
allowed to fail without stopping trading:

| Job | Runs when | If the model is down |
|---|---|---|
| Explains the current market in words | after the detector has already decided | you lose the explanation, not the decision |
| Reflects on a finished trade | after the trade closed | nothing is learned this cycle |
| Checks "have we lost on this setup before?" | before sizing | falls back to normal sizing |
| Answers operator questions in chat | on demand | chat is unavailable |

Put a model in the decision itself and the same input gives different answers on
different days. At that point you cannot backtest, you cannot reproduce a bug, and you
cannot tell a broken strategy from an unlucky one. I would not have been able to write
the table at the top of this file.

### Model layer engineering

- **Tier routing** (`agent/secondbrain/llm.py`) — three tiers, cheapest adequate model
  per job. Haiku for short structured work, Sonnet for synthesis and chat, Opus only when
  explicitly asked.
- **Semantic cache** — repeated questions do not repeat the spend.
- **Cost telemetry** (`agent/secondbrain/telemetry.py`) — tokens, dollars, latency and
  cache-hit recorded per call, against a "naive baseline" of routing everything to Opus
  with no cache, so the saving is a measured number rather than a claim.
- **Vector memory** — every finished trade is written as a structured reflection
  (`{signals, regime, outcome, lesson}`) into Upstash Vector. Before sizing a new
  position the agent asks whether this setup has lost before.
- **Per-cycle event trace** — `agent_events` in Convex is keyed by `cycle_id`, so one
  hour of the agent's life can be read end to end: what it saw, what it decided, which
  gate stopped it.
- **Graceful degradation** — with no API key the model layer returns stubs and trading
  continues. See [known weaknesses](#known-weaknesses); this is currently *too* quiet.

### Risk engine

The part that earned its keep. A strategy with a negative edge lost 44 cents.

- **Hold cash by default** — no position unless a setup clears its threshold. Flat means
  zero drawdown.
- **Token allowlist** (`core/risk/guardrails.py`) — five tokens, the only ones the
  strategy was ever tested on. Not a preference: trading outside the tested set means
  trading a setup with no measurement behind it, and on a thin pair slippage swamps any
  edge so the cost model stops predicting anything.
- **Kill switch** — halts within one cycle, flipped from the dashboard or Telegram.
- **Equity floor** — hard stop if the account falls below a set floor.
- **Cumulative exposure cap** — bounds *total* open position, so a run of individually
  legal buys cannot pile past the limit.
- **Volatility-targeted sizing** — size from ATR, not a fixed notional.
- **Simulate before send** — every order is dry-run before it is signed.

### Testing and evaluation

- 81 test files across `agent/`, `core/`, `onboard/`, `research/`, `scripts/`.
- **Simulation/live parity tests** — the paper loop must reproduce the backtest fill for
  fill. If they drift the backtest is fiction.
- **Failure-mode tests** — bad quote, failed transaction, timeout, risk veto, double
  execution, kill switch mid-cycle.
- **Walk-forward harness** (`core/backtest/walk_forward.py`) — trains on one period,
  tests on the next, reports out-of-sample only. Includes a deflated Sharpe calculation
  that penalises you for the number of variations you tried.
- **Full cost model** (`core/backtest/costs.py`) — gas, slippage and fees on every fill,
  calibrated against real on-chain receipts. A costless backtest would have shown a
  profit here. That gap *is* the finding.
- [`docs/THESIS_LEDGER.md`](docs/THESIS_LEDGER.md) — six trading ideas tested, six
  rejected, written down at the time rather than after.

### Self-custody

All signing goes through Trust Wallet Agent Kit. No private key appears in the code, the
logs, or the environment of any process that talks to the network.

---

## Known weaknesses

Written down because they are real, not because they are fixed.

- **The strategy has no edge.** The headline finding. Not a tuning problem.
- **The model layer fails silently.** `complete()` in `agent/secondbrain/llm.py` never
  raises. With a missing or expired key it returns stubs and everything downstream
  reports success. Trading correctly survives a model outage — but nothing tells you the
  agent stopped thinking. The fix is a visible degraded state, not an exception.
- **Prompts are string constants.** No version is recorded against the output it
  produced, so no per-prompt score would mean anything.
- **Cost data is recorded and dropped.** Per-call cost exists in telemetry but is not
  written onto the event trace, so a traced cycle cannot say what it cost.
- **Confidence is never checked.** `ForecastState.confidence` scales real position
  sizes. The table to measure whether it is honest exists and is wired up
  (`forecast_calibration`), and it is **empty** — the agent stopped running before it
  collected rows. Sizing on an unverified confidence number is the most common unexamined
  assumption in agent systems, and this one is still unexamined.
- **Two signals are dead.** `open_interest` and `net_flow` are all zeros in the stored
  history, so S2's open-interest half and S4 never contributed anything.
- **It died quietly.** The agent stopped in June 2026 and nothing alerted. Same class of
  bug as the silent model fallback: no news read as good news.
- **Two tests are marked `xfail`, both undiagnosed.** They are not skipped and not
  deleted, and each carries its reason in the file:
  - *post-restart replay* — after recovery marks the pre-crash cycles as executed,
    replaying the same bars still produces a second trade. Either the assertion is too
    strict (comparing trade counts rather than executed cycle ids) or recovery misses a
    cycle. Not yet separated.
  - *paper/sim parity* — `reconcile()` runs past its time budget instead of asserting.
    Something on the replay path blocks for minutes; the twak subprocess is already
    stubbed, so another per-cycle call is reaching for the network.

  The parity one matters most: it is the check that says a paper run reproduces the
  backtest fill for fill, which is what makes the evaluation numbers mean anything. It
  needs a real fix.
- **The live token allowlist disagreed with the code.** `TOKEN_ALLOWLIST` in
  `core/risk/guardrails.py` names the five tested tokens, but `get_token_allowlist()`
  prefers the Convex config row when online — and that row says `BNB, BTCB, ETH`. So the
  running agent was allowed to trade two tokens the code itself calls untested. The code
  is the honest version; the row is stale config from the contest.

---

## Running it

Requires Python 3.11+, [uv](https://github.com/astral-sh/uv), and [bun](https://bun.sh).

```bash
bash install.sh          # guided setup: checks deps, writes .env.local, probes Convex
```

Manually:

```bash
uv venv core/.venv && uv pip install --python core/.venv/bin/python -e ./core

# Evaluation — no keys, no network, reads history from disk
cd core && .venv/bin/python -m evaluate

# Tests
core/.venv/bin/python -m pytest agent/tests core/tests -q

# The agent. Paper mode is the default and needs no wallet.
core/.venv/bin/python -m agent.runtime

# Dashboard
cd web && bun install && bun run dev
```

**Paper mode is the default** (`agent/config.py`, `Dockerfile`, `fly.toml`). Live trading
requires you to supply your own wallet credentials and set `TRADING_MODE=mainnet`
deliberately. Given the result at the top of this file, don't.

| Layer | Built with |
|---|---|
| Strategy + backtest | Python, numpy, pandas, Polars |
| Agent runtime | FastAPI, LangGraph |
| Market data | CoinMarketCap Agent Hub, Binance |
| Execution | BNB AI Agent SDK, PancakeSwap |
| Signing | Trust Wallet Agent Kit |
| Real-time state | Convex |
| Cache + vectors | Upstash Redis, Upstash Vector |
| Dashboard | React, Vite, Tailwind, shadcn/ui, PWA |
| Models | Claude (tier-routed) |

---

## Status

**Archived, read-only.** It is published as an engineering record, not as something to
trade with. Bug fixes only.

If I carried this further I would not tune this strategy. I would keep the harness — the
cost model, the parity tests, the walk-forward split, the risk engine — point it at a
different hypothesis, and expect to reject that one too. The harness is the reusable
part. The strategy was one hypothesis, and it is now a measured no.

History from the project's origin as a three-week hackathon build is preserved in
[`docs/archive/`](docs/archive/).
