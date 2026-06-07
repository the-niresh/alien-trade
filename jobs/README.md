# jobs — Trigger.dev Tasks ✅ (Step 5)

Scheduled background jobs with built-in retries, backoff, dead-letter, alerting.
Each job only talks to the agent's FastAPI runtime — no strategy logic here.

| Job | File | Schedule | Purpose |
|-----|------|----------|---------|
| `decision-loop` | `src/decisionLoop.ts` | hourly (`0 * * * *`) | POST `/cycle` — fetch → signal → decide → execute |
| `trade-monitor` | `src/tradeMonitor.ts` | every minute | GET `/status` — watchdog; alerts on circuit-breaker / halt |
| `reflection` | `src/reflection.ts` | after each trade | Hermes reflection seam → Upstash Vector (wired in Step 6) |

## Reliability

- Retries 3× with exponential backoff, then dead-letters + alerts (`trigger.config.ts`).
- A non-2xx response throws → triggers the retry path.
- The decision cycle is **idempotent** (cycle_id keyed) so a retry can never double-trade.

## Run

```bash
cd jobs && bun install
# set TRIGGER_PROJECT_REF + AGENT_URL in env (see .env.example)
bun run dev      # local
bun run deploy   # to Trigger.dev
```
