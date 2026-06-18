import { action } from "./_generated/server";
import { v } from "convex/values";

export const getPortfolio = action({
  args: {},
  returns: v.object({ ok: v.boolean(), data: v.any(), error: v.optional(v.string()) }),
  handler: async (_ctx) => {
    const agentUrl = process.env.AGENT_URL ?? "http://localhost:8000";
    try {
      const res = await fetch(`${agentUrl}/twak/portfolio`, {
        signal: AbortSignal.timeout(15_000),
      });
      const json = (await res.json()) as { ok: boolean; data: unknown; error?: string };
      return { ok: json.ok, data: json.data ?? {}, error: json.error };
    } catch (e) {
      return { ok: false, data: {}, error: String(e) };
    }
  },
});
