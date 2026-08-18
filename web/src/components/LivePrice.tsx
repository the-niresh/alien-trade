import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { usd, elapsed } from "../lib/formatters";
import { cn } from "@/lib/utils";

type Props = { symbol: string };

export function LivePrice({ symbol }: Props) {
  const ticks = useQuery(api.priceTicks.forSymbol, { symbol, limit: 2 });

  if (ticks === undefined) {
    return (
      <Panel label={symbol} tick="cyan">
        <Skeleton className="h-10 w-48 bg-elevated rounded-lg" />
        <Skeleton className="h-4 w-32 bg-elevated rounded mt-2" />
      </Panel>
    );
  }

  const latest = ticks[0];
  const prev = ticks[1];

  if (!latest) {
    return (
      <Panel label={symbol} tick="cyan">
        <span className="font-display text-[32px] font-bold text-muted-fg">-</span>
      </Panel>
    );
  }

  const delta = prev ? latest.price - prev.price : 0;
  const pctChange = prev && prev.price > 0 ? (delta / prev.price) * 100 : 0;
  const isUp = delta >= 0;

  return (
    <Panel label={symbol} tick="cyan">
      <div className="flex items-baseline gap-4">
        <span
          className={cn(
            "font-display text-[32px] font-bold leading-none tabular-nums",
            isUp ? "text-green glow-green" : "text-red glow-red",
          )}
        >
          {usd(latest.price)}
        </span>
        {prev && (
          <span
            className={cn(
              "font-mono text-[13px] font-bold",
              isUp ? "text-green" : "text-red",
            )}
          >
            {isUp ? "↑" : "↓"} {Math.abs(pctChange).toFixed(2)}%
          </span>
        )}
      </div>
      <p className="font-mono text-[11px] text-muted-fg mt-1.5">
        updated {elapsed(latest.timestamp_ms)} ago
      </p>
    </Panel>
  );
}
