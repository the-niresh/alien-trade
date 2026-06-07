import { logger, schedules } from "@trigger.dev/sdk/v3";

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";

/**
 * Scheduled decision scan. Hourly cron == the 1h decision cadence in STRATEGY.md.
 * It only POSTs /cycle — all strategy/risk logic stays in /core behind the agent.
 *
 * Reliability: a non-2xx throws, so Trigger.dev applies exponential backoff and,
 * after 3 attempts, dead-letters the run (alert). The cycle itself is idempotent
 * (cycle_id keyed) so a retry can never double-trade.
 */
export const decisionLoop = schedules.task({
  id: "decision-loop",
  cron: "0 * * * *",
  maxDuration: 120,
  run: async (payload) => {
    const res = await fetch(`${AGENT_URL}/cycle`, { method: "POST" });
    if (!res.ok) {
      throw new Error(`agent /cycle returned ${res.status}`);
    }
    const body = await res.json();
    logger.info("decision cycle", { scheduledAt: payload.timestamp, ...body });
    return body;
  },
});
