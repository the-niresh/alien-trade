# Thesis Ledger — trial registry (AWAKE_SPRINT §4.4/§4.6)

> Every thesis the factory tests is logged here, **including the failures** — this is
> the multiplicity record the Deflated Sharpe gate reads (`n_trials` = rows below) and
> the "science in public" artifact the cockpit feed mirrors. A FALSIFIED thesis is a
> real result: it narrows the search and is never hidden.
>
> **How a row is produced:** a thesis card's `proposed_rule` (DSL) is run through
> `research/evaluate.py` across the eligible universe `{ETH,CAKE,UNI,LINK,AAVE}` at 1h
> with the **real BSC cost model** (PancakeSwap fee + AMM slippage + gas), single
> forward pass over the development series (the final ~50d holdout is **reserved**,
> scored once only on survivors).
>
> **Keep gate (locked):** a thesis is `VALIDATED` only if its dev objective
> (`sortino − 2·|maxDD|`) beats the **cash bar (0.0)** on ≥4/5 assets — i.e. it must
> actually earn risk-adjusted return *net of costs*, beating "sit in USDT and never
> trade." The 0.0 bar is harder than the v2 baseline (cash beats v2 — see
> `VALIDATION_1H.md`), so it is the only bar that matters. Survivors then clear the
> Deflated Sharpe gate on the untouched holdout before they ship.
>
> Reproduce any row: `core/.venv/bin/python -m research.run_thesis --id <ID> \
> --entry "<expr>" --exit "<expr>"` (append `--claim/--source` for the note).

## Trials

| thesis | claim | source | verdict | n_beat | dev_obj (ETH/CAKE/UNI/LINK/AAVE) | holdout_obj | DSR |
|--------|-------|--------|---------|--------|------------------------------------|-------------|-----|
| T-001 | trend-follow: long while price>EMA100 & ROC+, exit<EMA50 | canonical TA (baseline crossover) | FALSIFIED | 0/5 | -2.167/-1.307/-1.762/-1.843/-1.898 | — | — |
| T-002 | slow trend with 5% exit hysteresis above EMA200 | Dow/Weinstein stage analysis | FALSIFIED | 0/5 | -0.430/-0.400/-0.341/-0.348/-0.472 | — | — |
| T-003 | very-slow regime filter: long above EMA500 | 200-day-MA folklore (scaled to 1h) | FALSIFIED | 0/5 | -0.980/-0.812/-0.657/-1.203/-1.067 | — | — |
| T-004 | momentum band: enter on +10% 50-bar ROC, exit on ROC<0 | momentum factor (Jegadeesh-Titman) | FALSIFIED | 0/5 | -0.306/-0.281/-0.314/-0.289/-0.308 | — | — |
| T-005 | deep hysteresis: enter +5% over EMA100, exit -10% under | whipsaw-avoidance trader lore | FALSIFIED | 0/5 | -0.285/-0.364/-0.273/-0.282/-0.329 | — | — |
| T-006 | deep hysteresis + 20-bar momentum confirm (+2%) | whipsaw lore + momentum factor | FALSIFIED | 0/5 | -0.256/-0.309/-0.221/-0.265/-0.328 | — | — |

## Reading the first batch (2026-06-14)

All six long-biased trend/momentum rules are **FALSIFIED** — none beats sitting in
cash on any asset. Three facts emerge, consistent with the founding finding
(`VALIDATION_1H.md`) and now reproduced through the DSL + real-cost harness:

1. **Transaction costs dominate naive crossovers.** A single EMA line (T-001/T-003)
   makes the rule flip every time price wiggles across it → 400–800 fills over 540d.
   At ~0.85% round-trip (0.25% fee + ~0.56% AMM slippage + gas), 700 fills is ≈ −60%
   from costs *alone*. **Hysteresis is mandatory**: T-005's separated entry/exit bands
   cut fills 700→118 and objective −2.7→−0.28 — a 10× improvement that still loses.
2. **No long-only edge exists in this universe.** Even the lowest-churn rules land in
   the documented OOS baseline band (−0.24…−0.34). The eligible alts fell ~57%
   near-uniformly; any long exposure is a drag. Cash (0.0) wins. This is the moat, not
   the problem (the rubric penalises drawdown at λ=2).
3. **The binding constraint is drawdown, not entry quality.** T-006 (momentum-confirmed
   deep hysteresis, 19 fills on ETH) actually shows **positive Sortino on ETH (+0.038)
   and CAKE (+0.008)** and +1.6% ETH return — a faint real entry edge — yet is
   FALSIFIED because a −14.7% open drawdown swamps it (obj = 0.038 − 2·0.147). The entry
   isn't the problem; **holding through the drawdown is.**

**Search direction implied (next theses):** the lever is *exit/risk*, not entry. (a) a
hard per-position stop or ATR-based exit to cap the −15% drawdowns T-006 carried; (b)
*regime-conditional* entries (long **only** in confirmed trend/crash-recovery, cash
otherwise — CAKE/AAVE showed isolated positive-Sortino regime slices); (c) rules whose
default state is cash with low time-in-market. Every future thesis must justify why its
drawdown stays shallow, since that — not signal — is what the λ=2 objective punishes.
