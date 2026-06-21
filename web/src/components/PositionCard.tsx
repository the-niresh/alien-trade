import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sparkline } from "./Sparkline";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, pct, elapsed } from "../lib/formatters";
import { withToken } from "../lib/control";
import { X, Loader2 } from "lucide-react";

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

  const enqueue = useMutation(api.agentCommands.enqueue);
  const [confirm, setConfirm] = useState(false);
  const [queued, setQueued] = useState(false);

  const baseToken = position.symbol.split("/")[0];

  async function handleClose() {
    setQueued(true);
    setConfirm(false);
    try {
      await enqueue(withToken({
        command_type: "convert",
        params: JSON.stringify({ from_token: baseToken, to_token: "USDT", usd: position.current_value_usd }),
        queued_by: "cockpit",
      }));
    } finally {
      setTimeout(() => setQueued(false), 5000);
    }
  }

  const positive = position.unrealized_pnl_usd >= 0;
  const pnlPct   = position.avg_entry_price > 0
    ? (position.current_price - position.avg_entry_price) / position.avg_entry_price
    : 0;
  const sign = positive ? "+" : "";

  return (
    <motion.div
      className={cn(
        "panel relative p-4 overflow-hidden",
        positive ? "border-green/25" : "border-red/25",
      )}
      style={{ boxShadow: positive
        ? "0 0 28px color-mix(in oklab, var(--green) 6%, transparent)"
        : "0 0 28px color-mix(in oklab, var(--red) 6%, transparent)" }}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
    >
      <div className="flex justify-between items-center mb-2 relative">
        <div className="flex items-center gap-2">
          <span className="font-display text-[18px] font-bold tracking-wide">{position.symbol}</span>
          <span className="font-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyan/10 text-cyan tracking-[0.18em] border border-cyan/20">LONG</span>
        </div>
        <span className={cn("font-mono text-[10px] tracking-wide", positive ? "text-green" : "text-red")}>
          {sign}{pct(Math.abs(pnlPct))}
        </span>
      </div>

      {ticks.length >= 2
        ? <Sparkline ticks={ticks} positive={positive} />
        : <Skeleton className="h-14 w-full bg-elevated rounded-lg my-2" />
      }

      <div className="flex items-center gap-3 my-2.5">
        <div className="flex-1">
          <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted-fg mb-0.5">Entry</div>
          <div className="font-mono text-[13px] font-semibold tabular-nums">{usd(position.avg_entry_price)}</div>
        </div>
        <span className="text-border-hi text-sm">→</span>
        <div className="flex-1 text-right">
          <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted-fg mb-0.5">Mark</div>
          <div className="font-mono text-[13px] font-semibold tabular-nums">{usd(position.current_price)}</div>
        </div>
      </div>

      <div className="flex justify-between items-center mt-2 pt-2.5 border-t border-border">
        <span className="font-mono text-[11px] text-muted-fg tabular-nums">
          {position.quantity.toFixed(4)} · {elapsed(position.updated_ms)}
        </span>
        <span className={cn("font-display text-[16px] font-bold tabular-nums", positive ? "text-green glow-green" : "text-red glow-red")}>
          {sign}{usd(position.unrealized_pnl_usd)}
        </span>
      </div>

      {/* Close position control */}
      <div className="mt-2.5 pt-2 border-t border-border/50">
        {queued ? (
          <div className="flex items-center gap-1.5 font-mono text-[10px] text-yellow">
            <Loader2 className="w-3 h-3 animate-spin" />
            Close order queued — agent will execute next cycle
          </div>
        ) : confirm ? (
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-muted-fg flex-1">
              Sell {baseToken} → USDT at market?
            </span>
            <button
              onClick={handleClose}
              className="px-2.5 py-1 rounded-md bg-red/15 border border-red/30 text-red text-[10px] font-mono font-bold hover:bg-red/25 transition-colors cursor-pointer"
            >
              Confirm
            </button>
            <button
              onClick={() => setConfirm(false)}
              className="px-2.5 py-1 rounded-md bg-elevated border border-border text-muted-fg text-[10px] font-mono hover:text-text transition-colors cursor-pointer"
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="flex justify-end">
            <button
              onClick={() => setConfirm(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-elevated border border-border text-[10px] font-mono text-muted-fg hover:text-text hover:border-red/40 hover:bg-red/8 transition-colors cursor-pointer"
            >
              <X className="w-3 h-3" />
              Close Position
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
