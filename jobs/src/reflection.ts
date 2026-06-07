import { logger, task } from "@trigger.dev/sdk/v3";

/**
 * Post-trade reflection job (Hermes loop seam). Fired after each trade closes.
 * Step 6 wires the body to: build {signals, regime, outcome, lesson} → compress
 * → upsert to Upstash Vector for mistake-avoidance. For now it's the idempotent
 * scaffold so the executor → reflection plumbing exists end-to-end.
 *
 * Trigger with an idempotencyKey of the trade/cycle id so a retry never writes
 * the same reflection twice.
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
