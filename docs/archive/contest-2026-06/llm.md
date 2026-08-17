 Okay. Let me be straight with you, because you're asking the right question at the right moment and you deserve a real answer, not
  reassurance.

  The hard truth I just found

  The blindfold is real, and it's worse than "we don't know if we have alpha." I checked the actual wiring:

  1. The agent has never executed a single real swap. agent/executor.py has the real classes (TwakSwapExecutor, OnchainExecutor), but
  the live unit runs --mode paper (simulated fills), and the code comment literally says "twak swap is mainnet — paper mode covers
  pre-mainnet rehearsal." That assumption is the trap. Paper does not cover the real thing: TWAK auth, RPC reliability, gas, real
  slippage, token approvals, latency. All untested.
  2. TOKEN_ALLOWLIST=BNB,WBNB,USDT is wrong for scoring. Your own CLAUDE.md ruling says BNB/BTC/BTCB are not eligible and only twak
  swap on ETH/CAKE/UNI/LINK/AAVE counts. As configured, the agent could trade tokens that don't score. That's a config bug that could
  quietly zero you.
  3. WALLET_ADDRESS is empty. Nothing has touched a wallet.

  So the real risk isn't "flat returns." It's the agent fails to trade, or trades ineligible tokens, during the live window → score =
  0. A flat-but-functional agent scores something on drawdown/adherence. A crashed or non-executing one scores nothing.

  Are the docs good enough to win?

  For research and safety, yes — AWAKE_SPRINT / AUTONOMY are genuinely strong. But they're built around the thesis factory (finding
  alpha) and treat live execution as "Phase 7, operator-gated, paper covers it." That priority is now wrong for your situation. With
  ~a week left and no edge found in 2.5 weeks, more thesis search has near-zero marginal value. Proving execution works has enormous
  value. The docs are optimizing the wrong axis for the time you have left.

  How to make this win (the pivot)

  Stop the alpha grind. Spend every remaining day making live execution real and tested. Your instinct is correct — get it live and
  tested — with one correction: don't make the official window your first real trade.

  - Now → Jun 21: TESTNET dress rehearsal. BSC testnet (chainId 97, you have the RPC). Prove one real twak swap lands end-to-end,
  measure latency, fix what breaks, run it 24/7 so you watch it behave.
  - Jun 22 → 28: mainnet, the official window. By then the path is proven, not a prayer.

  That converts "blindfolded" into "tested," which is exactly what you said, and it's right.

  Your direct question — what is the control token?

  It's just a password your agent and cockpit share to prove they're allowed to change the agent (halt it, flip mode, set caps). Not
  a wallet key. See yours:
  grep CONTROL_TOKEN /root/claude/projects/alien-trade/.env.local

  Next steps before going live (ordered)

  I can do these right now, no money, to de-blindfold you:
  1. Run core/backtest/score_sim.py → give you an expected competition percentile number for the cash-default posture (real number,
  not a feeling).
  2. Measure the agent's decision latency in paper mode.
  3. Dry-run the TWAK path — swap_quote only, no execution — to see if the auth/endpoint even responds with your creds (proves the
  connection without spending anything).
  4. Fix the TOKEN_ALLOWLIST to the eligible set and confirm the agent maps symbols correctly.
  5. Write a tight testnet rehearsal runbook (exact commands, what "good" looks like, what to watch).

  Only you can do these (I'll nag/guide):
  6. Set WALLET_ADDRESS + fund a testnet wallet (testnet BNB faucet).
  7. Run one real testnet swap, watch the receipt + latency together.
  8. twak compete register before Jun 22 (late = rejected — this is the #1 score=0 risk).
  9. Flip to mainnet for Jun 22–28.

  One unknown I can't resolve from here: whether TWAK even offers a testnet swap endpoint (the code comment implies twak swap is
  mainnet-only). If it doesn't, the rehearsal has to be a tiny-capital mainnet swap instead. I'll find that out in step 3.

  Want me to start with steps 1–5 right now? That gives you, within this session: an expected-score number, a latency number, a
  yes/no on whether TWAK responds to your creds, the allowlist fixed, and a runbook for the testnet rehearsal. That's most of the
  blindfold gone in one pass.

✻ Brewed for 2m 52s


● Here's the handoff prompt. It's aimed squarely at making "we kept it live for days" a true, tested claim — testnet rehearsal now,
  mainnet for the official window — and it bakes in the three real gaps I found (never executed a swap, wrong token allowlist, empty
  wallet address). Copy-paste into the fresh Sonnet session:

  ---
  You are continuing Alien-Trade (BNB Hack 2026, Track 1) at
  /root/claude/projects/alien-trade on branch AT-2-awake-sprint-productization.
  Claude Code runs ON the target VPS; deploy is local (no SSH). Model: sonnet.
  Today is 2026-06-14. Freeze Jun 21. Live window Jun 22–28.

  MISSION
  Get the agent GENUINELY LIVE and tested before Jun 22 so we can honestly say it
  has been running live for several days — that is our standout claim. Plan:
  TESTNET dress rehearsal now → mainnet for the official window. Honesty is the
  product ethos (we ship a falsification log); never make a "live since X" claim
  that isn't literally true (a real on-chain receipt must exist first).

  STEP 0 — READ, then VERIFY yourself (git log, grep — don't trust this prompt blindly)
    - CLAUDE.md — LOCKED decisions. Critical: the L3 scoring ruling — ONLY `twak swap`
      transactions count; eligible tokens = ETH/CAKE/UNI/LINK/AAVE; BNB/BTC/BTCB are
      NOT eligible. Also the "Self-check before every implementation (win gate)".
    - docs/AWAKE_SPRINT.md §7 (operator critical path), docs/VPS_STEPS.md (runbook).
    - agent/executor.py (PaperExecutor / OnchainExecutor / TwakSwapExecutor),
      agent/twak_cli.py (swap_quote / swap_execute), core/exec/bnb.py
      (simulate_swap / execute_swap_pipeline), agent/runtime.py (--mode paper|testnet|mainnet).

  STATE (verified 2026-06-14 — confirm, then act):
    - alien-trade.service runs `--mode paper` (SIMULATED). The agent has NEVER executed
      a real swap. This is the core blindfold.
    - .env.local HAS: TW_ACCESS_ID, TW_HMAC_SECRET, TWAK_API_BASE, TWAK_WALLET_PASSWORD,
      PRIVATE_KEY, BNB_RPC_URL, BNB_TESTNET_RPC_URL, BNB_TESTNET_CHAIN_ID=97,
      EXECUTION_BACKEND=twak, TRADING_MODE=testnet. WALLET_ADDRESS is EMPTY.
    - BUG: TOKEN_ALLOWLIST=BNB,WBNB,USDT — wrong for scoring; must be the eligible set.
    - Convex = festive-newt-1; cockpit :4173 (paired via CONTROL_TOKEN). Do NOT print secrets.

  PHASE A — De-blindfold (NO spending; do all, commit each with evidence)
    1. Fix TOKEN_ALLOWLIST → ETH,CAKE,UNI,LINK,AAVE in .env.local. Verify the symbol
       mapping through agent/config.py + executor so the agent acts ONLY on eligible tokens.
    2. Run core/backtest/score_sim.py on the current cash-default posture → report the
       expected competition-score distribution / percentile (Sortino − 2·|maxDD| over
       bootstrapped 7-day windows). Give Nire a real number.
    3. Measure decision latency: one paper cycle — strategy compute time and full
       loop time. Report ms.
    4. TWAK reachability (NO execution): call swap_quote with current creds — testnet
       first, then mainnet — and report the raw responses. ANSWER: (a) does auth work?
       (b) is `twak swap` testnet-capable, or mainnet-only? This decides whether the
       rehearsal is testnet or tiny-capital mainnet.
    5. Reset the stale Convex ledger rows (equity ≈ $9,831 from old paper runs) so the
       live equity curve starts clean (AUTONOMY P2).
    6. Write docs/LIVE_REHEARSAL.md: the exact operator commands to (a) fund the wallet,
       (b) run ONE supervised real swap, (c) start 24/7 live mode, (d) flip to mainnet
       for Jun 22; plus what "good" looks like, the kill switch, and rollback.

  PHASE B — Execution readiness (build to the SPEND LINE, then STOP)
    7. Confirm `--mode testnet` (or mainnet if twak is mainnet-only) selects the
       TwakSwapExecutor/OnchainExecutor correctly and that simulate-before-send runs on
       EVERY order. Add a focused test if missing.
    8. Confirm/implement the ≥1-trade/day activity-floor on the eligible allowlist.
    9. Prepare (write, do NOT enable/restart) the systemd unit variant that runs live
       mode, so Nire can flip it with one command.
   10. Produce the EXACT one-shot command Nire runs for the FIRST real swap: tiny size,
       simulate-before-send, idempotency key, eligible token.

  HARD RULES (this work touches money — stricter than the research loop)
    - DO NOT autonomously: execute a real swap, fund anything, restart/flip the live
      unit into a money mode, or run `twak compete register`. Build to the edge, output
      the exact command, hand the trigger to Nire.
    - simulate-before-send on every order; honor risk caps + kill switch.
    - Enforce: only `twak swap` on ETH/CAKE/UNI/LINK/AAVE counts.
    - Never `git push`; commit locally with evidence. Apply the CLAUDE.md win-gate
      ("will this win the hackathon? yes/no/maybe") to each item; skip the no's.
    - Do not claim "live" until a real receipt exists; log real receipts to the ledger.
    - Leave pre-existing uncommitted files alone; stage only what your change touches.

  OPERATOR CRITICAL PATH (you CANNOT do these — surface + nag every report)
    - Fund wallet: testnet faucet first, then a small mainnet amount.
    - Set WALLET_ADDRESS in .env.local.
    - `twak compete register` BEFORE Jun 22 (late = rejected — #1 score=0 risk).
    - DoraHacks submission (wallet + writeup). Approve each money step.

  EACH REPORT back to Nire: the score number, the latency number, the twak quote
  yes/no + testnet-vs-mainnet verdict, the allowlist-fix commit, LIVE_REHEARSAL.md,
  and the exact first-swap command.

  BEGIN: read the docs, get the suite green
  (core/.venv/bin/python -m pytest agent/tests core/tests -q — known-failing &
  out of scope: test_trades_paired_from_real_fills, one hanging agent test, the
  parquet TestDataLoader tests), then do Phase A in order.

  ---
  Two honest flags before you run it:

  - The "live for days" claim only counts if it's real. The fastest path to a true claim is getting a testnet (or tiny mainnet) swap
  working in the next day or two, then leaving it running. If TWAK turns out to be mainnet-only (Phase A step 4 will tell you), the
  rehearsal becomes small real money — that's fine and still honest, just fund it lightly.
  - The single thing that still outranks everything: twak compete register before Jun 22. No amount of live uptime matters if the
  registration is missed. Put that on a hard reminder now.

  Want me to also run Phase A here in this Opus session in parallel, so you get the score/latency/twak-quote numbers immediately
  while Sonnet works the other terminal? Or leave it entirely to Sonnet?

✻ Brewed for 1m 54s
