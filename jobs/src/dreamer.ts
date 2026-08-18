import { logger, schedules } from "@trigger.dev/sdk/v3";

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";

/**
 * Nightly Dreamer consolidation - fires at 02:00 UTC daily.
 *
 * Calls POST /dreamer on the agent server which runs Dreamer.run():
 *   1. Dedupe near-identical reflections (cosine ≥ 0.92)
 *   2. Score forecast calibration (win-rates by confidence bucket)
 *   3. Age out stale research (>48 h old → stale=True in Vector)
 *   4. Write a nightly digest to Second Brain
 *
 * Advisory path - a failed run is logged but never raises.
 */
export const dreamer = schedules.task({
  id: "dreamer-nightly",
  cron: "0 2 * * *",     // 02:00 UTC every day
  maxDuration: 300,       // LLM + vector ops can take a few minutes
  run: async (payload) => {
    let result: Record<string, unknown> = { ok: false, reason: "not attempted" };
    try {
      const res = await fetch(`${AGENT_URL}/dreamer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      result = res.ok
        ? await res.json()
        : { ok: false, reason: `HTTP ${res.status}` };
    } catch (err) {
      result = { ok: false, reason: String(err) };
    }
    logger.info("dreamer nightly", { scheduledAt: payload.timestamp, ...result });
    return result;
  },
});
