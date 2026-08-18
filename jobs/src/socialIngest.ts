import { logger, schedules } from "@trigger.dev/sdk/v3";

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";

/**
 * Social ingest schedule (8.2). Every 30 min: POST /social/ingest → agent runs
 * ingest(), scores sentiment, writes sentiment_state + social_posts to Convex.
 * Off the hot path - a failure here never affects trading.
 */
export const socialIngest = schedules.task({
  id: "social-ingest",
  cron: "*/30 * * * *",
  maxDuration: 60,
  run: async (payload) => {
    try {
      const res = await fetch(`${AGENT_URL}/social/ingest`, { method: "POST" });
      if (!res.ok) {
        logger.warn("social ingest non-2xx", { status: res.status });
        return { ok: false, status: res.status };
      }
      const body = await res.json();
      logger.info("social ingest done", { scheduledAt: payload.timestamp, ...body });
      return body;
    } catch (err) {
      // Advisory - never surface as a hard error that blocks other jobs.
      logger.warn("social ingest failed (non-critical)", { err: String(err) });
      return { ok: false, error: String(err) };
    }
  },
});
