import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { usd, ts } from "../lib/formatters";
import { cn } from "@/lib/utils";

export function RecentTrades() {
  const trades = useQuery(api.trades.recent, { limit: 10 });

  return (
    <Panel
      label="Trade History"
      tick="green"
      action={
        trades && trades.length > 0 ? (
          <span className="font-mono text-[10px] text-muted-fg">
            {trades.length} fill{trades.length !== 1 ? "s" : ""}
          </span>
        ) : undefined
      }
    >
      {trades === undefined ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full bg-elevated rounded-lg" />
          ))}
        </div>
      ) : trades.length === 0 ? (
        <p className="font-mono text-[12px] text-muted-fg py-2">
          // no trades executed yet
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {trades.map((t) => {
            const isBuy = t.side === "buy";
            const txUrl = t.tx_hash
              ? `https://bscscan.com/tx/${t.tx_hash}`
              : null;
            const totalCost = t.fee_usd + t.gas_usd + t.slippage_usd;

            return (
              <div
                key={t._id}
                className="rounded-lg bg-bg/50 border border-border px-3 py-2.5"
              >
                {/* Row 1: side pill · symbol · size · [spacer] · tx link */}
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span
                    className={cn(
                      "font-mono text-[10px] font-bold tracking-[0.16em] uppercase px-2 py-1 rounded border w-12 text-center flex-shrink-0",
                      isBuy
                        ? "text-green border-green/30 bg-green/10"
                        : "text-red border-red/30 bg-red/10",
                    )}
                  >
                    {t.side}
                  </span>

                  <span className="font-display font-bold text-cyan text-[13px] flex-shrink-0">
                    {t.symbol}
                  </span>

                  <span className="font-mono text-[12px] text-text flex-shrink-0">
                    {usd(t.size_usd)}
                  </span>

                  {t.mode === "mainnet" && (
                    <span className="font-mono text-[9px] font-bold tracking-widest uppercase text-green/60 border border-green/20 rounded px-1.5 py-0.5 flex-shrink-0">
                      live
                    </span>
                  )}

                  <div className="ml-auto flex items-center gap-2 flex-shrink-0">
                    {txUrl && (
                      <a
                        href={txUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-[10px] text-green/70 hover:text-green border border-green/20 hover:border-green/40 rounded px-1.5 py-0.5 transition-colors"
                        title="View on BSCScan"
                      >
                        TX ↗
                      </a>
                    )}
                  </div>
                </div>

                {/* Row 2: fill price · fees · timestamp */}
                <div className="flex items-center gap-3 mt-1 flex-wrap">
                  <span className="font-mono text-[11px] text-muted-fg">
                    @ {usd(t.fill_price)}
                  </span>
                  {totalCost > 0 && (
                    <span className="font-mono text-[10px] text-muted-fg/70">
                      fees {usd(totalCost)}
                    </span>
                  )}
                  <span className="font-mono text-[10px] text-muted-fg/60 ml-auto">
                    {ts(t.timestamp_ms)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
