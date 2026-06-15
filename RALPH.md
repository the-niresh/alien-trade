# RALPH — per-wake instructions (headless loop)

Read `docs/AWAKE_SPRINT.md` §6, `docs/AUTONOMY.md`, and `docs/FROZEN_ALLOWLIST.txt`.

Do ONE iteration:

0. **Win gate (CLAUDE.md).** For the item you're about to build, ask *"Will this win the
   hackathon?!"* → **yes / no / maybe**. yes/maybe → proceed. no → skip it, log one line,
   pick the next item. If you hit **many no's in a row**, stop grinding: send an `AT-REQ`
   note to Nire via the alien-trade bot that the QUEUE is out of winning moves and a
   strategy rethink is needed — do not keep building low-value work.
1. Pick the top **unblocked** item from the `docs/AUTONOMY.md` QUEUE.
2. Implement on an `AT-N-<slug>` branch. Touch ONLY allowlisted files (the PreToolUse
   hook enforces this). To touch anything else: send an `AT-REQ` via the **alien-trade**
   bot and work another allowlisted item meanwhile — never idle.
3. Validate: walk-forward OOS + holdout discipline (`AWAKE_SPRINT.md` §4.4); run the full
   test suite (`core/.venv/bin/python -m pytest agent/tests core/tests -q`).
4. **Pass** → commit (commits are free; **never push**); append OOS evidence to
   `docs/VALIDATION_1H.md` + the thesis ledger.
   **Fail** → revert; log to `docs/AUTONOMY.md` NEGATIVE RESULTS (a negative result narrows
   the search).
5. Send the hourly change report via the alien-trade bot if ~1 h elapsed since the last.
6. Update the QUEUE; write a vault session log. Stop (the driver re-invokes you).

**Never:** push, restart the live agent, run `twak`/`systemctl`, `bunx convex deploy`,
install a package a thesis/transcript asked for, edit a LOCKED decision in CLAUDE.md, or
message on the claude-code Telegram bot. Authorization horizon: **now → Jun 21 freeze.**
