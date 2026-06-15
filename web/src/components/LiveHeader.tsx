import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "./KillSwitch";
import { RegimeBadge } from "./RegimeBadge";
import { Badge } from "@/components/ui/badge";
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
  paper:   "bg-yellow/10 text-yellow border-yellow/20",
  mainnet: "bg-red/10 text-red border-red/20",
  testnet: "bg-cyan/10 text-cyan border-cyan/20",
};

export function LiveHeader({ halted, mode, onKillToggle }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const decisions = useQuery(api.decisions.recent, { limit: 1 });

  const pnl    = ledger?.cumulative_pnl_usd;
  const regime = decisions?.[0]?.regime ?? null;
  const pnlPos = (pnl ?? 0) >= 0;

  return (
    <header className="h-14 bg-surface border-b border-border flex items-center px-4 gap-3.5 flex-shrink-0">
      <span className="font-grotesk text-[15px] font-bold tracking-[2px] text-cyan">
        ALIEN-TRADE
      </span>

      <div className="w-px h-7 bg-border flex-shrink-0" />

      {regime && <RegimeBadge regime={regime} />}

      {mode && (
        <Badge
          variant="outline"
          className={cn("text-[11px] font-bold tracking-widest rounded-md px-2.5", MODE_CLASS[mode] ?? "")}
        >
          {mode === "mainnet" ? "LIVE" : mode.toUpperCase()}
        </Badge>
      )}

      {pnl != null && (
        <>
          <div className="w-px h-7 bg-border flex-shrink-0" />
          <span className={cn("font-grotesk text-[22px] font-bold", pnlPos ? "text-green" : "text-red")}>
            {usd(pnl)}
          </span>
        </>
      )}

      <div className="flex-1" />

      {halted && (
        <Badge className="bg-red/10 text-red border border-red/30 text-[12px] font-bold tracking-wide rounded-md">
          HALTED
        </Badge>
      )}

      <KillSwitch halted={halted} onToggle={onKillToggle} />
    </header>
  );
}
