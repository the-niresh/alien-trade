import { motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sparkline } from "./Sparkline";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, pct, elapsed } from "../lib/formatters";

type Position = {
  _id: string;
  symbol: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  current_value_usd: number;
  unrealized_pnl_usd: number;
  updated_ms: number;
};

export function PositionCard({ position }: { position: Position }) {
  const rawTicks = useQuery(api.priceTicks.forSymbol, { symbol: position.symbol, limit: 24 }) ?? [];
  const ticks = [...rawTicks].reverse().map((t) => ({ t: t.timestamp_ms, p: t.price }));

  const positive = position.unrealized_pnl_usd >= 0;
  const pnlPct   = position.avg_entry_price > 0
    ? (position.current_price - position.avg_entry_price) / position.avg_entry_price
    : 0;
  const sign = positive ? "+" : "";

  return (
    <motion.div
      className={cn(
        "bg-surface rounded-2xl p-4 border transition-[border-color,box-shadow] duration-300",
        positive
          ? "border-green/20 shadow-[0_0_20px_rgba(0,255,157,0.03)]"
          : "border-red/20 shadow-[0_0_20px_rgba(255,48,96,0.03)]"
      )}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
    >
      <div className="flex justify-between items-center mb-2">
        <span className="font-grotesk text-[17px] font-bold">{position.symbol}</span>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-cyan/10 text-cyan tracking-widest">LONG</span>
      </div>

      {ticks.length >= 2
        ? <Sparkline ticks={ticks} positive={positive} />
        : <Skeleton className="h-14 w-full bg-elevated rounded-lg my-2" />
      }

      <div className="flex items-center gap-2 my-2.5">
        <div className="flex-1">
          <div className="text-[10px] text-muted-fg mb-0.5">Entry</div>
          <div className="font-grotesk text-[13px] font-semibold">{usd(position.avg_entry_price)}</div>
        </div>
        <span className="text-muted-fg text-sm">→</span>
        <div className="flex-1">
          <div className="text-[10px] text-muted-fg mb-0.5">Current</div>
          <div className="font-grotesk text-[13px] font-semibold">{usd(position.current_price)}</div>
        </div>
      </div>

      <div className="flex justify-between items-center mt-2">
        <span className="text-[12px] text-muted-fg">
          {position.quantity.toFixed(4)} · {elapsed(position.updated_ms)}
        </span>
        <span className={cn("font-grotesk text-[15px] font-bold", positive ? "text-green" : "text-red")}>
          {sign}{usd(position.unrealized_pnl_usd)} ({sign}{pct(Math.abs(pnlPct))})
        </span>
      </div>
    </motion.div>
  );
}
