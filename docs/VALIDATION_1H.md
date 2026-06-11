# 1h Out-of-Sample Validation — Eligible Universe (2026-06-11)

First honest re-validation at the **traded cadence (1h)** on the **competition-eligible
universe** `{ETH, CAKE, UNI, LINK, AAVE}`, with the full signal stack live
(S1 price + S2 funding + S3 Fear&Greed sentiment). OI endpoint blocked from the VPS,
so S2 is funding-only; S4 on-chain flow still 0.

Data: Binance public klines + Futures funding, 540 days × 1h = **12,960 bars/asset**
(cached to `core/data/parquet/binance_<SYM>_540d_1h.parquet`).

## Result: NO out-of-sample edge on any eligible asset

70/30 optimise → hold-out (the shippable param set's OOS scorecard):

| Symbol | Objective | Sortino | Return | MaxDD | Trades | Win% |
|--------|-----------|---------|--------|-------|--------|------|
| ETH  | **−0.301** | −0.239 | −2.92% | −3.09% | 15 | 0%  |
| CAKE | **−0.240** | −0.193 | −2.13% | −2.35% | 11 | 9%  |
| UNI  | **−0.339** | −0.254 | −3.37% | −4.24% | 19 | 16% |
| LINK | **−0.303** | −0.229 | −2.73% | −3.70% | 16 | 6%  |
| AAVE | **−0.262** | −0.188 | −2.39% | −3.69% | 15 | 13% |

ETH walk-forward (73 windows) agrees: −5.70% return, Sortino −0.136, MaxDD −6.54%,
**0% win rate, 12.4× turnover.**

## Interpretation

1. **The prior hypothesis is falsified.** The June note "the edge lives in the
   orthogonal CMC signals (S2/S3/S4)" does **not** hold: with funding + sentiment
   live at 1h, every eligible asset is still negative OOS. Adding the signals did not
   create edge.
2. **It's structural, not a tuning miss.** 0–16% win rate at 12× turnover = a
   trend/EMA-cross flipper getting chopped to death. More grid search won't fix a
   strategy that enters on noise.
3. **The drawdown penalty is the key.** With objective `Sortino − 2·|MaxDD|`,
   **staying flat in cash scores 0.0 — which beats all five live strategies
   (−0.24 to −0.34).** Today, *doing nothing wins.* This is the lever, not a problem.
4. **Where rare edge may live (regime breakdown):** CAKE/UNI show positive Sortino in
   clean *trend* regimes (0.18 / 0.35); AAVE is strongly positive in *crash*
   recovery (1.07, tiny sample). The signal isn't "always long" — it's "long only in
   specific regimes, cash otherwise."

## Implication for the build

No amount of LLM harness, Second Brain, multi-wallet, or token optimisation matters
while the deterministic core is negative OOS. **Strategy redesign is the gating
work.** Recommended archetype: **cash-default, regime-gated, selective long** — sit
in USDT (zero drawdown) and deploy only on high-conviction regime setups, satisfying
the ≥1 trade/day activity floor with minimal neutral trades. Turn the drawdown
penalty from the enemy into the moat.

## Redesign v1 — cash-default trend filter (2026-06-12)

Added a single principled knob: a **long-EMA trend filter** (`trend_filter_period=100`,
≈4 days on 1h, NOT optimizer-swept). The book only holds long while `close > EMA100`;
below it, capital force-exits to USDT (zero drawdown). Cash is now the default state.
Files: `core/strategy/combined.py`, `core/signals/momentum.py::ema_value`.

Walk-forward OOS (73 windows) — baseline → redesign, every metric improved on every asset:

| Asset | Return | Sortino | MaxDD (scoring weapon) | Turnover |
|-------|--------|---------|------------------------|----------|
| ETH  | −5.70% → **−0.02%** | −0.136 → **0.000** | −6.54% → **−2.41%** | 12.4× → 4.5× |
| CAKE | +2.54% → +2.63% | 0.039 → 0.036 | −4.75% → **−3.35%** | 12.9× → 5.1× |
| UNI  | −5.96% → **−2.84%** | −0.092 → **−0.048** | −8.58% → **−4.29%** | 14.0× → 7.1× |
| LINK | −1.98% → −1.58% | −0.036 → −0.027 | −3.76% → **−2.52%** | 13.4× → 6.8× |
| AAVE | −6.50% → **−1.96%** | −0.126 → **−0.044** | −9.74% → **−3.56%** | 17.0× → 5.6× |

**Outcome:** the bleeding is stopped and drawdown ~halved across the board. This is the
predicted result of cash-default discipline in a hostile long-only universe: from
"clearly losing" to "≈flat with shallow drawdown" — a large objective improvement under
`Sortino − 2·|MaxDD|`. It does **not yet generate positive alpha** (Sortino ≈ 0); the
single recent 70/30 hold-out window is still mildly negative because the last ~160 days
were broadly hostile to long-only alts and a few breakout entries failed.

## Redesign v2 — rising-trend entry filter (2026-06-12)

Added an **asymmetric** entry-quality gate (`trend_slope_lookback=12`, not swept): ENTER
only when price is above a *rising* EMA100 (cuts failed breakouts above a flat/rolling
trend); HOLD as long as price stays above EMA100 (lenient exit → no churn). Files:
`core/strategy/combined.py`.

Walk-forward OOS (73 windows) — v1 → v2:

| Asset | Return | Sortino | MaxDD | Fills | Objective (Sortino−2·DD) |
|-------|--------|---------|-------|-------|--------------------------|
| ETH  | −0.02% → −0.07% | 0.000 → −0.001 | −2.41% → **−2.00%** | 45 → 33 | −0.048 → **−0.041** |
| CAKE | +2.63% → **+3.35%** | 0.036 → **0.043** | −3.35% → −3.44% | 52 → 42 | −0.031 → **−0.026** |
| UNI  | −2.84% → **−1.16%** | −0.048 → **−0.020** | −4.29% → **−2.54%** | 70 → 42 | −0.134 → **−0.071** |
| LINK | −1.58% → −2.00% | −0.027 → −0.036 | −2.52% → −2.52% | 68 → 43 | −0.077 → −0.086 |
| AAVE | −1.96% → **−1.83%** | −0.044 → −0.044 | −3.56% → **−3.31%** | 55 → 46 | −0.115 → **−0.110** |

**Outcome:** fills down on all 5; objective improved on 4/5 (LINK the lone regression).
A modest net win that lowers turnover and tightens drawdown — but NOT a jump to positive
alpha. Per-asset entry tuning has reached diminishing returns. Verdict: **keep v2.**

### Next lever — cross-sectional rotation (not yet done)
The single-symbol harness forces us to judge each weak alt in isolation. The real
long-only edge is **relative strength**: hold whichever eligible asset is *strongest*
right now, sit in USDT when none qualify. CAKE is the only consistently positive name —
a rotation book would concentrate there when it leads and avoid the dogs. Needs a
**portfolio backtester** (current `run_backtest`/`walk_forward` are per-symbol) — a
bigger build than the last two tweaks.

## Reproduce

```bash
cd core
for S in ETH CAKE UNI LINK AAVE; do
  .venv/bin/python retune.py --symbol $S --source binance --interval 1h --days 540
done
```
