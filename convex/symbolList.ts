import { query } from "./_generated/server";

export const list = query({
  args: {},
  handler: async (ctx) => {
    const positions = await ctx.db
      .query("positions")
      .filter((q) => q.gt(q.field("quantity"), 0))
      .collect();
    const symbols = [...new Set(positions.map((p) => p.symbol))].sort();
    return symbols;
  },
});
