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
      // Stablecoins peg to $1 — avoids a needless round-trip and a 0 if the feed lags.
      if (token.toUpperCase() === "USDT" || token.toUpperCase() === "USDC") return 1;
      const res = await fetch(
        `${agentUrl}/twak/price?token=${encodeURIComponent(token)}&chain=bsc`,
        { signal: AbortSignal.timeout(12_000) },
      );
      const json = (await res.json()) as { ok: boolean; data: Record<string, unknown>; error?: string };
      if (!json.ok) throw new Error(json.error ?? `price failed for ${token}`);
      const d = json.data ?? {};
      // The twak CLI's JSON shape varies by version — pull the USD price defensively.
      const raw = d.price ?? d.priceUsd ?? d.priceUSD ?? d.usd ?? d.value ?? 0;
      const p = Number(raw);
      return Number.isFinite(p) && p > 0 ? p : 0;
    };

    try {
      const [fromPrice, toPrice] = await Promise.all([priceOf(from), priceOf(to)]);
      return { ok: true, fromPrice, toPrice };
    } catch (e) {
      return { ok: false, fromPrice: 0, toPrice: 0, error: String(e) };
    }
  },
});
