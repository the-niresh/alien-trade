Done. I had the previous session via llm.md, so I reworked the plan around your decision: win Track 1.

What changed

The old plan treated the agent/Second Brain/token-optimization as the centerpiece and buried backtesting at Phase 6. But Track 1 is scored on PnL replay over held-out live data (Jun 22–28) — so the winner is whoever has the best trading edge + drawdown control, not the smartest LLM. I flipped the whole structure to match that.

3 files rewritten/added:

1. PROJECT_PLAN.md — Track-1-first. New center of gravity is Phases 2–4: the backtest/sim engine, the signal strategy, and the drawdown-first risk engine. The LLM/Second Brain dropped to Phase 6, off the trade hot path. Added a "What Wins Track 1" table and an explicit anti-overfitting protocol.
2. STEPS.md — re-sequenced runbook. New priority order: data pipeline first (historical CMC data is the #1 spike — no history = no backtest = no edge), then the sim engine, then the alpha, then risk. ★ markers flag the wins-the-track steps.
3. STRATEGY.md (new — this was the missing piece) — the actual alpha spec: 4 orthogonal CMC signals (momentum + funding/OI + sentiment + on-chain flow), how they combine into a target position, regime gating, drawdown-first sizing, and the optimization objective Sortino − λ·maxDrawdown.

The three things that actually decide it

- The simulator is your optimization engine — but it's also the trap. It's built honest from day one (walk-forward, out-of-sample only, real gas/slippage/funding costs) because judges replay on data you've never seen. Tune to a beautiful in-sample curve and you overfit → lose live.
- Sim and live run the same /core code. No "sim version" vs "live version." If they diverge, the sim lies and you lose live. Phase 7 is a multi-day paper run to reconcile them before any mainnet capital.
- Drawdown is the scoring weapon. Over 7 days, variance is huge; a steady low-drawdown bot beats a volatile high-return one on risk-adjusted scoring. The risk engine optimizes for that, not raw return.

Track 2 is now a free byproduct — the same backtest engine + strategy package is the Track 2 submission, so you don't lose your shot at it.

I also saved two project memories (Track-1 priority + the edge spec) so this survives across sessions.

Want me to write the next docs (BACKTEST.md, ARCHITECTURE.md) or start scaffolding the /core backtest engine?

✻ Cogitated for 4m 34s

※ recap: Goal is to win Track 1 of the BNB hackathon with the Alien-Trade agent. I reworked PROJECT_PLAN.md, STEPS.md, and added STRATEGY.md to center on the backtest engine and trading edge. Next: scaffold the /core backtest engine or write BACKTEST.md. (disable recaps in /config)
