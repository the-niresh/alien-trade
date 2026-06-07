import { logger, task } from "@trigger.dev/sdk/v3";

/**
 * Post-trade reflection job (Hermes loop seam). Fired after each trade closes.
 *
 * Step 6 status: the Hermes write-path is IMPLEMENTED in the Python runtime —
 * `agent/secondbrain/reflection.py::ReflectionWriter` builds {signals, regime,
 * outcome, lesson}, embeds it under the setup key in Upstash Vector, and writes
 * the Convex `reflections` row, fired in-process by the decision loop on a
 * closing fill. This Trigger.dev task remains as an external backstop: it can
 * POST {tradeId, cycleId, ...} to the agent if you prefer to drive reflection
 * out-of-band. Keep the idempotencyKey = trade/cycle id so a retry never writes
 * the same reflection twice (the Convex mutation is also idempotent on it).
 */
export const reflection = task({
  id: "reflection",
  maxDuration: 60,
  run: async (payload: {
    tradeId: string;
    cycleId: string;
    signals: Record<string, number | undefined>;
    regime: string;
    realizedPnlUsd: number;
  }) => {
    const outcome =
      payload.realizedPnlUsd > 0 ? "win" : payload.realizedPnlUsd < 0 ? "loss" : "scratch";

    // TODO(Step 6): summarise → embed → Upstash Vector upsert; write reflections row.
    logger.info("reflection (stub)", {
      tradeId: payload.tradeId,
      cycleId: payload.cycleId,
      regime: payload.regime,
      outcome,
    });

    return { tradeId: payload.tradeId, outcome, stored: false };
  },
});
