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

export const convertQuote = action({
  args: { from: v.string(), to: v.string() },
  returns: v.object({
    ok: v.boolean(),
    fromPrice: v.number(),
    toPrice: v.number(),
    error: v.optional(v.string()),
  }),
  handler: async (_ctx, { from, to }) => {
    const agentUrl = process.env.AGENT_URL ?? "http://localhost:8000";

    const priceOf = async (token: string): Promise<number> => {
      const t = token.toUpperCase();
      if (t === "USDT" || t === "USDC") return 1;
      const res = await fetch(
        `${agentUrl}/twak/price?token=${encodeURIComponent(t)}`,
        { signal: AbortSignal.timeout(10_000) },
      );
      const json = (await res.json()) as { ok: boolean; data?: { priceUsd: number }; error?: string };
      if (!json.ok || !json.data) throw new Error(json.error ?? `No price for ${t}`);
      const p = json.data.priceUsd;
      if (!Number.isFinite(p) || p <= 0) throw new Error(`Bad price for ${t}`);
      return p;
    };

    try {
      const [fromPrice, toPrice] = await Promise.all([priceOf(from), priceOf(to)]);
      return { ok: true, fromPrice, toPrice };
    } catch (e) {
      return { ok: false, fromPrice: 0, toPrice: 0, error: String(e) };
    }
  },
});
