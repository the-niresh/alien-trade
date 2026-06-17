import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "./KillSwitch";
import { RegimeBadge } from "./RegimeBadge";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { usd } from "../lib/formatters";

type Props = {
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
  selectedSymbol?: string;
  onSymbolChange?: (s: string) => void;
};

const MODE_CLASS: Record<string, string> = {
  paper:   "bg-yellow/10 text-yellow border-yellow/25",
  mainnet: "bg-red/10 text-red border-red/30",
  testnet: "bg-cyan/10 text-cyan border-cyan/25",
};

export function LiveHeader({ halted, mode, onKillToggle, selectedSymbol = "ALL", onSymbolChange }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const decisions = useQuery(api.decisions.recent, { limit: 1 });
  const symbols   = useQuery(api.symbolList.list) ?? [];
  const ticks     = useQuery(api.priceTicks.forSymbol, { symbol: selectedSymbol === "ALL" ? "ETH" : selectedSymbol, limit: 2 }) ?? [];

  const pnl      = ledger?.cumulative_pnl_usd;
  const regime   = decisions?.[0]?.regime ?? null;
  const pnlPos   = (pnl ?? 0) >= 0;
  const latestTick = ticks[0];
  const prevTick   = ticks[1];
  const priceUp    = latestTick && prevTick ? latestTick.price >= prevTick.price : true;

  return (
    <header className="chrome h-14 border-b border-border flex items-center px-4 gap-3.5 flex-shrink-0 z-20">
      {/* Brand mark */}
      <div className="flex items-center gap-2.5">
        <span className="relative flex h-2 w-2">
          <span className={cn(
            "absolute inline-flex h-full w-full rounded-full opacity-70 animate-ping",
            halted ? "bg-red" : "bg-green",
          )} />
          <span className={cn("relative inline-flex h-2 w-2 rounded-full", halted ? "bg-red" : "bg-green")} />
        </span>
        <span className="font-display text-[15px] font-bold tracking-[0.22em] text-green glow-green">
          ALIEN<span className="text-text/40">·</span>TRADE
        </span>
      </div>

      <div className="w-px h-7 bg-border flex-shrink-0" />

      {regime && <RegimeBadge regime={regime} />}

      {latestTick && (
        <>
          <div className="w-px h-7 bg-border flex-shrink-0" />
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-fg">
              {selectedSymbol === "ALL" ? "ETH" : selectedSymbol}
            </span>
            <span className={cn(
              "font-display text-[18px] font-bold leading-none tabular-nums",
              priceUp ? "text-green" : "text-red",
            )}>
              ${latestTick.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            {prevTick && (
              <span className={cn("font-mono text-[10px]", priceUp ? "text-green/70" : "text-red/70")}>
                {priceUp ? "▲" : "▼"}
                {Math.abs((latestTick.price - prevTick.price) / prevTick.price * 100).toFixed(2)}%
              </span>
            )}
          </div>
        </>
      )}

      {mode && (
        <Badge
          variant="outline"
          className={cn("font-mono text-[10px] font-bold tracking-[0.2em] rounded-md px-2.5 py-0.5", MODE_CLASS[mode] ?? "")}
        >
          {mode === "mainnet" ? "● LIVE" : mode.toUpperCase()}
        </Badge>
      )}

      {pnl != null && (
        <>
          <div className="w-px h-7 bg-border flex-shrink-0 max-sm:hidden" />
          <div className="flex items-baseline gap-1.5 max-sm:hidden">
            <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-fg">PnL</span>
            <span className={cn("font-display text-[22px] font-bold leading-none tabular-nums", pnlPos ? "text-green glow-green" : "text-red glow-red")}>
              {usd(pnl)}
            </span>
          </div>
        </>
      )}

      <div className="flex-1" />

      {symbols.length > 0 && onSymbolChange && (
        <Select value={selectedSymbol} onValueChange={onSymbolChange}>
          <SelectTrigger className="w-28 h-7 font-mono text-[11px] bg-elevated/60 border-border text-text focus:ring-green">
            <SelectValue placeholder="ALL" />
          </SelectTrigger>
          <SelectContent className="bg-surface border-border text-text">
            <SelectItem value="ALL" className="font-mono text-[11px]">ALL</SelectItem>
            {symbols.map((s) => (
              <SelectItem key={s} value={s} className="font-mono text-[11px] text-cyan font-bold">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {halted && (
        <Badge className="bg-red/10 text-red border border-red/40 font-mono text-[10px] font-bold tracking-[0.16em] rounded-md animate-pulse">
          HALTED
        </Badge>
      )}

      <KillSwitch halted={halted} onToggle={onKillToggle} />
    </header>
  );
}
