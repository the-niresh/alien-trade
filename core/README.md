# core — The Crown Jewel

Strategy + signals + backtest/sim engine. This is the center of gravity of the entire project.

**Critical invariant:** the live agent imports this module directly. There is no "sim version" vs "live version." If they diverge, the sim is worthless.

---

## Structure

```
core/
  backtest/     Event-driven backtester, cost model, walk-forward harness, metrics
  signals/      S1 momentum · S2 funding/OI · S3 sentiment · S4 on-chain flow
  risk/         Position sizing, daily-loss kill, regime gating, drawdown guard
  exec/         BNB SDK adapter (bnb.py) + TWAK signing adapter (twak.py)
  data/         CMC historical + live feed adapters, parquet cache
  tests/        All unit + integration tests — run before every commit
```

## Run tests

```bash
cd core
.venv/Scripts/python -m pytest tests/ -v        # Windows
.venv/bin/python -m pytest tests/ -v            # Mac/Linux
```

## Setup

```bash
cd core
uv venv --python 3.11
uv pip install -e .
```

## Invariants

- Every backtest includes the full cost model (gas, slippage, fees, funding)
- Walk-forward only — never report or optimize on in-sample numbers
- Strategy functions are pure: `(list[Bar]) → Signal` — no side effects, no I/O
- Sim and live share the same `Bar`, `Order`, `Fill` types — no translation layer
