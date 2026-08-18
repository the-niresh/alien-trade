import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

export function LivePositionsSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind !== "primary") {
    return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">Assistant agents hold no positions.</div>;
  }
  return <PrimaryPositions />;
}

function PrimaryPositions() {
  const positions = useQuery(api.positions.open) ?? [];
  if (positions.length === 0) return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">Flat - no open positions.</div>;
  return (
    <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
      {positions.map((p) => (
        <div key={p._id} className="panel p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-display text-[14px] font-bold text-text">{p.symbol}</span>
            <span className={cn("font-mono text-[12px] font-bold", p.unrealized_pnl_usd >= 0 ? "text-green" : "text-red")}>
              {p.unrealized_pnl_usd >= 0 ? "+" : ""}${p.unrealized_pnl_usd.toFixed(2)}
            </span>
          </div>
          <div className="font-mono text-[10px] text-muted-fg/70 flex justify-between">
            <span>{p.quantity.toFixed(4)} @ ${p.avg_entry_price.toFixed(4)}</span>
            <span>now ${p.current_price.toFixed(4)}</span>
          </div>
          <div className="font-mono text-[10px] text-muted-fg/50">value ${p.current_value_usd.toFixed(2)}</div>
        </div>
      ))}
    </div>
  );
}
