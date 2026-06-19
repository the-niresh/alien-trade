import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "./KillSwitch";
import { RegimeBadge } from "./RegimeBadge";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Wallet } from "lucide-react";
import { cn } from "@/lib/utils";
import { usd } from "../lib/formatters";

type Props = {
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
  selectedSymbol?: string;
  onSymbolChange?: (s: string) => void;
  onDeposit?: () => void;
};

const MODE_CLASS: Record<string, string> = {
  paper:   "bg-yellow/10 text-yellow border-yellow/25",
  mainnet: "bg-red/10 text-red border-red/30",
  testnet: "bg-cyan/10 text-cyan border-cyan/25",
};

export function LiveHeader({ halted, mode, onKillToggle, selectedSymbol = "ALL", onSymbolChange, onDeposit }: Props) {
  const ledger      = useQuery(api.ledger.latest);
  const decisions   = useQuery(api.decisions.recent, { limit: 1 });
  const symbols     = useQuery(api.symbolList.eligible) ?? [];
  const walletState = useQuery(api.walletState.get);
  const ticks       = useQuery(api.priceTicks.forSymbol, { symbol: selectedSymbol || "ETH", limit: 2 }) ?? [];

  const pnl      = ledger?.cumulative_pnl_usd;
  const regime   = decisions?.[0]?.regime ?? null;
  const pnlPos   = (pnl ?? 0) >= 0;
  const latestTick = ticks[0];
  const prevTick   = ticks[1];
  const priceUp    = latestTick && prevTick ? latestTick.price >= prevTick.price : true;

  return (
    <header className="chrome h-14 border-b border-border flex items-center px-3 sm:px-4 gap-2 sm:gap-3.5 flex-shrink-0 z-20 overflow-hidden">
      {/* Brand mark */}
      <div className="flex items-center gap-2 sm:gap-2.5 flex-shrink-0" data-tour="brand">
        <div className="relative flex-shrink-0">
          <img
            src="/logo.png"
            alt="Alien-Trade"
            className="w-8 h-8 rounded-full object-contain"
            style={{ mixBlendMode: "screen" }}
          />
          <span className={cn(
            "absolute bottom-0 right-0 w-2 h-2 rounded-full border-[1.5px] border-[#050508]",
            halted ? "bg-red" : "bg-green animate-pulse",
          )} />
        </div>
        <span className="font-display text-[13px] sm:text-[15px] font-bold tracking-[0.18em] sm:tracking-[0.22em] text-green glow-green whitespace-nowrap">
          ALIEN<span className="text-text/40">·</span>TRADE
        </span>
      </div>

      {/* Regime + price — hidden on mobile */}
      <div className="hidden sm:flex items-center gap-3.5 flex-shrink-0">
        <div className="w-px h-7 bg-border" />
        {regime && <RegimeBadge regime={regime} />}

        {latestTick && (
          <>
            <div className="w-px h-7 bg-border" />
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-fg">
                {selectedSymbol || "ETH"}
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
      </div>

      {mode && (
        <Badge
          variant="outline"
          className={cn("font-mono text-[9px] sm:text-[10px] font-bold tracking-[0.15em] sm:tracking-[0.2em] rounded-md px-2 sm:px-2.5 py-0.5 flex-shrink-0", MODE_CLASS[mode] ?? "")}
        >
          {mode === "mainnet" ? "● LIVE" : mode.toUpperCase()}
        </Badge>
      )}

      {/* PnL — hidden on mobile */}
      {pnl != null && (
        <div className="hidden sm:flex items-center gap-3.5 flex-shrink-0">
          <div className="w-px h-7 bg-border" />
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-fg">PnL</span>
            <span className={cn("font-display text-[22px] font-bold leading-none tabular-nums", pnlPos ? "text-green glow-green" : "text-red glow-red")}>
              {usd(pnl)}
            </span>
          </div>
        </div>
      )}

      {/* Wallet balance — hidden on mobile */}
      {walletState != null && (
        <div className="hidden sm:flex items-center gap-3.5 flex-shrink-0">
          <div className="w-px h-7 bg-border" />
          <div className="flex items-center gap-1.5">
            <Wallet className="w-3 h-3 text-muted-fg" />
            <span className="font-mono text-[11px] text-muted-fg tabular-nums">
              {usd(walletState.total_usd)}
            </span>
          </div>
        </div>
      )}

      <div className="flex-1" />

      {/* Symbol select — hidden on mobile */}
      {onSymbolChange && (
        <div className="hidden sm:block flex-shrink-0">
          <Select value={selectedSymbol} onValueChange={onSymbolChange}>
            <SelectTrigger className="w-28 h-7 font-mono text-[11px] bg-elevated/60 border-border text-text focus:ring-green">
              <SelectValue placeholder="ETH" />
            </SelectTrigger>
            <SelectContent className="bg-surface border-border text-text">
              {symbols.map((s) => (
                <SelectItem key={s} value={s} className="font-mono text-[11px] text-cyan font-bold">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {halted && (
        <Badge className="bg-red/10 text-red border border-red/40 font-mono text-[10px] font-bold tracking-[0.16em] rounded-md animate-pulse flex-shrink-0">
          HALTED
        </Badge>
      )}

      {onDeposit && (
        <button
          onClick={onDeposit}
          data-tour="deposit-btn"
          className="hidden sm:flex items-center gap-1.5 font-mono text-[10px] font-bold text-cyan border border-cyan/25 bg-cyan/8 rounded-lg px-2.5 py-1 hover:bg-cyan/15 transition-colors cursor-pointer flex-shrink-0"
        >
          ↓ Deposit
        </button>
      )}

      {/* desktop only — mobile has a FAB in AppShell */}
      <div className="hidden sm:flex" data-tour="kill-switch">
        <KillSwitch halted={halted} onToggle={onKillToggle} />
      </div>
    </header>
  );
}
