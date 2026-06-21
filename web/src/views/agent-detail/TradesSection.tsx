import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

export function TradesSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryTrades />;
  return <SpawnedApprovals agent={agent} />;
}

function PrimaryTrades() {
  const trades = useQuery(api.trades.recent, { limit: 30 }) ?? [];
  if (trades.length === 0) return <Empty text="No trades yet." />;
  return (
    <div className="panel p-0 overflow-hidden">
      <table className="w-full font-mono text-[11px]">
        <thead>
          <tr className="text-muted-fg/60 uppercase tracking-widest text-[9px] border-b border-border/30">
            <th className="text-left px-3 py-2">Side</th>
            <th className="text-left px-3 py-2">Symbol</th>
            <th className="text-right px-3 py-2">Size</th>
            <th className="text-right px-3 py-2">Fill</th>
            <th className="text-right px-3 py-2">Gas</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t._id} className="border-b border-border/15">
              <td className={cn("px-3 py-2 uppercase", t.side === "buy" ? "text-green" : "text-red")}>{t.side}</td>
              <td className="px-3 py-2 text-text">{t.symbol}</td>
              <td className="px-3 py-2 text-right text-text">${t.size_usd.toFixed(2)}</td>
              <td className="px-3 py-2 text-right text-muted-fg">${t.fill_price.toFixed(4)}</td>
              <td className="px-3 py-2 text-right text-muted-fg/70">${t.gas_usd.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SpawnedApprovals({ agent }: { agent: DetailAgent }) {
  const pending = useQuery(api.approvals.listPending) ?? [];
  const mine = pending.filter((p) => p.agent_id === agent.id);
  return (
    <div className="flex flex-col gap-3">
      <p className="font-mono text-[10px] text-muted-fg/60 uppercase tracking-widest">Assistant agents propose trades — they don't execute directly.</p>
      {mine.length === 0 ? <Empty text="No pending trade proposals." /> : mine.map((p) => (
        <div key={p._id} className="panel p-3 font-mono text-[11px] text-text">{p.kind}: {p.payload}</div>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">{text}</div>;
}
