# Alien-Trade - Strategy & Edge Spec

> **This is the alpha.** Track 1 is won here - not in the agent, the LLM, or the UI.
> Everything is deterministic, backtestable code so the simulator can optimize and validate it.

---

## 0. Design principles

1. **Edge = orthogonal CMC data others ignore.** Most teams trade price/TA only. Our edge is combining price with **derivatives (funding, OI)**, **social/sentiment**, and **on-chain flow**. Orthogonal signals → better risk-adjusted returns.
2. **2-3 signals, not 15.** Few parameters = less overfit = survives the held-out live window. Every knob must earn its place in walk-forward.
3. **Drawdown-first.** The objective function is risk-adjusted return with a hard drawdown penalty - not raw return.
4. **Regime-aware.** No strategy works in all regimes. Detect regime; size down or sit out when conditions are hostile.
5. **Deterministic.** No LLM in the trade decision. The LLM only narrates regimes and stores reflections (off the hot path).

---

## 1. Universe & cadence

- **Universe:** a small allowlist of liquid BSC-tradable assets (e.g. BNB, BTC, ETH and 2-4 high-liquidity alts with reliable CMC funding/OI/social coverage). Small universe = less overfit, lower gas, easier to reason about.
- **Decision cadence:** start at **1h bars** (enough signal, low turnover, low gas drag). Validate 15m and 4h in sim; pick by net-of-cost out-of-sample Sharpe, not gut.
- **Holding horizon:** hours to ~2 days. We are *not* HFT (we can't win latency races on-chain) and *not* multi-week (the judged window is only 7 days).

---

## 2. Signal library

Each signal outputs a normalized score in **[-1, +1]** (short → long). Each is independently backtestable and attributable.

### S1 - Momentum / Trend (price)
- Inputs: OHLCV.
- Core: trend-following - e.g. fast/slow EMA cross + ROC, normalized by ATR (volatility-scaled so it's comparable across assets).
- Intuition: crypto trends persist intraday-to-days; this is the backbone signal.
- Score: `+1` strong uptrend → `-1` strong downtrend; near 0 in chop.

### S2 - Derivatives: Funding + Open Interest (CMC)
- Inputs: perp funding rate, open interest.
- Core:
  - **Funding extreme = contrarian.** Very positive funding (crowded longs) → fade up-moves; very negative → fade down-moves.
  - **OI confirmation:** rising OI + rising price = real trend (confirm S1); rising OI + flat price = squeeze risk.
- Intuition: positioning data front-runs liquidations. **This is the lever most teams don't have.**
- Score: contrarian on funding extremes, confirmatory via OI/price divergence.

### S3 - Social / Sentiment (CMC)
- Inputs: social volume, sentiment score, KOL/news signals.
- Core: **sentiment momentum** (rate-of-change of attention), not absolute level. A spike in social volume + improving sentiment ahead of price = early trend; euphoric extreme = caution/fade.
- Intuition: attention leads retail flow leads price on alts.
- Score: positive on accelerating constructive attention; negative on blow-off euphoria.

### S4 - On-chain flow (CMC)
- Inputs: exchange in/out flow, whale/large-holder movement, net flow.
- Core: net **outflow from exchanges** (accumulation) = bullish; net **inflow** (distribution/sell pressure) = bearish.
- Intuition: smart-money flow precedes price; structurally orthogonal to TA.
- Score: scaled net-flow z-score.

> **Start with S1 + S2 + (S3 or S4).** Trend backbone + positioning + one of sentiment/flow. Add the third only if it improves *out-of-sample* risk-adjusted return. Drop any signal that doesn't.

---

## 3. Combination → target position

```
raw   = w1*S1 + w2*S2 + w3*S3   # weights tuned via walk-forward, kept stable
gate  = regime_gate(regime)      # 0..1 multiplier, 0 = sit out
target = clip(raw, -1, +1) * gate
```

- `target` is the **desired position** in [-1,+1] (fraction of risk budget, sign = direction).
- Enter/adjust only when `|target - current|` exceeds a **rebalance band** (kills churn → saves gas/slippage).
- Weights `w*` constrained (e.g. sum to 1, each ≥ 0 for confirmatory signals) to limit degrees of freedom.

---

## 4. Regime detection

Deterministic classifier (LLM only narrates it later, off path):

| Regime        | Detected by                                  | Action                                         |
| ------------- | -------------------------------------------- | ---------------------------------------------- |
| **Trend**     | ADX/EMA-slope high, vol moderate             | Full S1 weight, normal size                    |
| **Chop**      | Low ADX, mean-reverting, tight range         | Cut S1, lean on S2 contrarian, **size down**   |
| **High-vol**  | ATR/realized-vol spike                       | **Size down hard** (vol-target), widen stops   |
| **Crash/risk-off** | Sharp drawdown + funding/flow capitulation | **Sit out or tiny defensive** (gate→0)         |

Regime gate is the single biggest drawdown protector - it's why we don't get wrecked when the 7-day window turns hostile.

---

## 5. Risk engine (drawdown-first - this wins the risk-adjusted score)

- **Volatility-targeted sizing:** position size ∝ target_vol / realized_vol → constant risk, auto-shrinks in turbulence.
- **Fractional Kelly, capped:** size by edge but hard-cap fraction (e.g. ≤ 0.25 Kelly) - Kelly over a 7-day sample is too aggressive.
- **Hard caps (code, non-negotiable):** per-trade max, max total exposure, max open positions, slippage cap, token allowlist.
- **Daily-loss kill:** cumulative daily loss past threshold → **halt trading** until next day. This single rule prevents the catastrophic day that tanks risk-adjusted scoring.
- **Circuit breaker:** N consecutive losses or anomalous data → pause + alert.
- **Mistake-avoidance:** before entering, query Second Brain - "have we lost on this exact setup/regime before?" → block or penalize size.

**Optimization objective (walk-forward):**
```
maximize   Sortino_oos  −  λ * max_drawdown_oos
```
Tune `λ` so the selected strategy is *steady*, not *spectacular*. A modest steady return with tiny drawdown beats a volatile high-return one on the judging rubric.

---

## 6. Execution model (must match sim)

- **Order type:** market swaps via PancakeSwap (BNB SDK) / perp orders; sized to stay within slippage cap.
- **Pre-trade simulate-before-send;** abort on bad quote/slippage.
- **Costs charged in sim AND live:** gas, AMM slippage (size-aware), swap fee, perp funding, latency. The sim's cost model is calibrated from real testnet/mainnet fills in Phase 7.
- **Rebalance band + low cadence** keep turnover (and cost drag) low - critical because gas/slippage silently kills crypto strategies.

---

## 7. Anti-overfitting protocol (the discipline that decides win/lose)

> A backtest tuned to perfection on data we've seen will lose on the data judges replay. Defend against it:

1. **Out-of-sample only** - never report or select on in-sample numbers.
2. **Walk-forward** - optimize window N, validate untouched N+1, roll forward; report the stitched OOS curve.
3. **Parameter stability** - pick a robust plateau, not a fragile peak. Plot the objective surface; reject spiky optima.
4. **Few parameters** - 2-3 signals, constrained weights, minimal knobs.
5. **Cost realism** - full cost model in every run.
6. **Regime stress test** - evaluate trend/chop/high-vol/crash slices separately; require "doesn't blow up" in each, not "great in one."
7. **Paper reconciliation (Phase 7)** - multi-day live paper run must track the sim before any mainnet capital. Drift = bug.
8. **No peeking at the live window** - once frozen (Jun 21), only risk caps change.

---

## 8. What we explicitly do NOT do

- ❌ LLM "should I buy now" calls - slow, costly, untestable, no edge at short horizon.
- ❌ LLM pattern-recognition as a trade signal - the simulator can't optimize a black box.
- ❌ 15-knob mega-strategy - overfit machine.
- ❌ Max-return swinging - variance loses on risk-adjusted scoring over 7 days.
- ❌ Frictionless backtests - they lie and the gap shows up as live losses.
- ❌ Different code paths for sim vs live - guarantees the sim is wrong.

---

## 9. Track 2 (free byproduct)

The exact `/core` strategy + walk-forward report *is* the Track 2 Strategy Skill: backtestable, explainable (co-pilot answers "why this trade" from the recorded signals/regime), reproducible from a clean clone. No extra strategy work - only packaging.
