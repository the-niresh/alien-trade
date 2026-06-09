import { logger, schedules } from "@trigger.dev/sdk/v3";

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";
const AGENT_SYMBOL = process.env.AGENT_SYMBOL ?? "ETH";

/**
 * Periodic supervisor tick — drives the Researcher node on a 2-hour cadence.
 *
 * The LangGraph supervisor routes kind=research_tick to the ResearchAgent, which
 * identifies regime anomalies / social spikes / OI divergence, synthesises a
 * digest via CMC Skills, and stores it in the Second Brain. Advisory path only —
 * a failed tick is logged but never raises (non-critical, must not alert on-call).
 */
export const supervisorTick = schedules.task({
  id: "supervisor-tick",
  cron: "0 */2 * * *",   // every 2 hours, on the hour
  maxDuration: 180,       // research cycle can be slow (LLM + CMC calls)
  run: async (payload) => {
    let result: Record<string, unknown> = { ok: false, reason: "not attempted" };
    try {
      const res = await fetch(`${AGENT_URL}/supervisor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "research_tick",
          symbol: AGENT_SYMBOL,
          text: "research_tick",
        }),
      });
      result = res.ok
        ? await res.json()
        : { ok: false, reason: `HTTP ${res.status}` };
    } catch (err) {
      result = { ok: false, reason: String(err) };
    }
    logger.info("supervisor tick", { scheduledAt: payload.timestamp, ...result });
    // Return result but do NOT throw on failure — advisory path.
    return result;
  },
});
