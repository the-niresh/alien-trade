import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { usd } from "../lib/formatters";
import { cn } from "@/lib/utils";

export function FeesGasSummary() {
  const trades = useQuery(api.trades.recent, { limit: 200 });

  if (trades === undefined) {
    return (
      <Panel label="Cost Summary" tick="yellow">
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-full bg-elevated rounded" />
          ))}
        </div>
      </Panel>
    );
  }

  const totalFees = trades.reduce((sum, t) => sum + t.fee_usd, 0);
  const totalGas = trades.reduce((sum, t) => sum + t.gas_usd, 0);
  const totalSlippage = trades.reduce((sum, t) => sum + t.slippage_usd, 0);
  const totalCost = totalFees + totalGas + totalSlippage;

  const rows: Array<{ label: string; value: number; highlight?: boolean }> = [
    { label: "Total Fees",     value: totalFees },
    { label: "Total Gas",      value: totalGas },
    { label: "Total Slippage", value: totalSlippage },
    { label: "Total Cost",     value: totalCost, highlight: totalCost > 1 },
  ];

  return (
    <Panel label="Cost Summary" tick="yellow">
      {trades.length === 0 ? (
        <p className="font-mono text-[12px] text-muted-fg py-1">
          // no trades yet
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {rows.map(({ label, value, highlight }, i) => (
            <div
              key={label}
              className={cn(
                "flex justify-between items-center",
                i === rows.length - 1 && "border-t border-border/40 pt-2 mt-0.5",
              )}
            >
              <span className="font-mono text-[11px] text-muted-fg">{label}</span>
              <span
                className={cn(
                  "font-mono text-[12px]",
                  highlight ? "text-yellow" : "text-text",
                )}
              >
                {usd(value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
