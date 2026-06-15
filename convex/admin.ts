import { internalMutation, mutation } from "./_generated/server";
import { v } from "convex/values";

/**
 * Wipe the paper-trading corpus (ledger, trades, decisions, reflections).
 * Config, risk_state, and audit are deliberately preserved.
 * Intended for use before the live trading window to start with a clean slate.
 *
 * Run via CLI:
 *   bunx convex run admin:resetCorpus
 */
export const resetCorpus = mutation({
  args: {},
  returns: v.object({
    deleted_ledger: v.number(),
    deleted_trades: v.number(),
    deleted_decisions: v.number(),
    deleted_reflections: v.number(),
  }),
  handler: async (ctx) => {
    const deletePage = async (table: "ledger" | "trades" | "decisions" | "reflections") => {
      const rows = await (ctx.db.query(table) as any).collect();
      for (const row of rows) {
        await ctx.db.delete(row._id);
      }
      return rows.length;
    };

    const deleted_ledger     = await deletePage("ledger");
    const deleted_trades     = await deletePage("trades");
    const deleted_decisions  = await deletePage("decisions");
    const deleted_reflections = await deletePage("reflections");

    return { deleted_ledger, deleted_trades, deleted_decisions, deleted_reflections };
  },
});
