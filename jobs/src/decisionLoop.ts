import { logger, schedules } from "@trigger.dev/sdk/v3";

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";

/**
 * Scheduled decision scan. Hourly cron == the 1h decision cadence in STRATEGY.md.
 * It only POSTs /cycle - all strategy/risk logic stays in /core behind the agent.
 *
 * After a sell fill (position_closed) it fires POST /supervisor so the
 * Reflector→Historian chain runs automatically - the agent team is self-driving.
 *
 * Reliability: a non-2xx throws, so Trigger.dev applies exponential backoff and,
 * after 3 attempts, dead-letters the run (alert). The cycle itself is idempotent
 * (cycle_id keyed) so a retry can never double-trade. The supervisor call is
 * fire-and-forget (failure swallowed) - advisory path must never block the trade.
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

    // Observe→react: if a position just closed, fire the Reflector→Historian chain.
    if (body.filled && body.side === "sell") {
      try {
        const supRes = await fetch(`${AGENT_URL}/supervisor`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "position_closed",
            symbol: body.symbol,
            cycle_id: body.cycle_id,
            payload: {
              cycle_id: body.cycle_id,
              regime: body.regime,
              side: body.side,
              signals: body.signals ?? {},
              realized_pnl: body.realized_pnl ?? 0,
              timestamp_ms: body.timestamp_ms ?? 0,
            },
          }),
        });
        const supBody = supRes.ok ? await supRes.json() : { ok: false };
        logger.info("supervisor: position_closed", supBody);
      } catch (err) {
        // Advisory path - a supervisor failure must never surface as an error here.
        logger.warn("supervisor call failed (non-critical)", { err: String(err) });
      }
    }

    return body;
  },
});
