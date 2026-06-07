import { logger, schedules } from "@trigger.dev/sdk/v3";

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";

/**
 * Trade-status monitor. Polls the agent's ledger snapshot every minute so a
 * stalled loop, runaway drawdown, or stuck position surfaces fast. The on-chain
 * receipt is already the agent's ledger source-of-truth; this job is the
 * watchdog + alert hook on top of it.
 */
export const tradeMonitor = schedules.task({
  id: "trade-monitor",
  cron: "* * * * *",
  maxDuration: 30,
  run: async () => {
    const res = await fetch(`${AGENT_URL}/status`);
    if (!res.ok) {
      throw new Error(`agent /status returned ${res.status}`);
    }
    const status = await res.json();
    if (status.consecutive_losses >= 5) {
      logger.warn("circuit-breaker territory", status);
    }
    if (status.halted) {
      logger.warn("agent is HALTED", status);
    }
    return status;
  },
});
