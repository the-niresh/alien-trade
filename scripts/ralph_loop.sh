#!/usr/bin/env bash
# scripts/ralph_loop.sh — re-invoke claude headless; 1h backoff on rate limit.
# The wrapper (not the model) owns rate-limit handling: a rate-limited model can't act.
# Deploying this as a systemd unit / tmux session is an OPERATOR-GATED step — do not
# start it from inside the loop. Self-terminates at the Jun 21 freeze horizon.
set -uo pipefail
cd "$(dirname "$0")/.."
HORIZON="2026-06-21T23:59:59"
LOG=/var/log/alien-ralph.log

while [ "$(date +%s)" -lt "$(date -d "$HORIZON" +%s)" ]; do
  OUT=$(claude -p "$(cat RALPH.md)" --dangerously-skip-permissions 2>&1)
  echo "$OUT" >> "$LOG"
  if echo "$OUT" | grep -qiE "rate.?limit|usage limit|quota|429|overloaded"; then
    echo "[$(date -Is)] rate-limited -> sleep 3600" >> "$LOG"
    sleep 3600           # wait 1h, then retry (repeats on repeat limit)
    continue
  fi
  sleep 60               # brief gap between successful iterations
done
echo "[$(date -Is)] horizon reached — loop done" >> "$LOG"
