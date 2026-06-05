# jobs — Trigger.dev Tasks

Scheduled background jobs with built-in retries, backoff, dead-letter, and alerting.

## Planned jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `decision-loop` | Every N minutes | Fetch → signal → decide → execute |
| `trade-monitor` | Every minute | Confirm pending txs, reconcile ledger |
| `reflection-job` | After each trade | Emit structured reflection → Upstash Vector |
| `research-loop` | Every N hours | Karpathy AutoResearch — CMC MCP + on-chain digest |

## Key rules

- Every job is idempotent — safe to retry on failure
- Dead-letter any job that fails 3× — alert immediately
- Never duplicate a trade — idempotency keys on every execution call

Built in Step 5 (Jun 15–18).
