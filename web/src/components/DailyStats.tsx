import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { StatCard } from "./StatCard";
import { Skeleton } from "@/components/ui/skeleton";
import { usd } from "../lib/formatters";

export function DailyStats() {
  const trades = useQuery(api.trades.recent, { limit: 50 });

  if (trades === undefined) {
    return (
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-[104px] w-full bg-elevated rounded-xl" />
        <Skeleton className="h-[104px] w-full bg-elevated rounded-xl" />
      </div>
    );
  }

  const startOfDayMs = new Date().setHours(0, 0, 0, 0);
  const todayTrades = trades.filter((t) => t.timestamp_ms >= startOfDayMs);

  const tradeCount = todayTrades.length;
  const volumeUsd = todayTrades.reduce((sum, t) => sum + t.size_usd, 0);

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        label="Trades Today"
        value={String(tradeCount)}
        unit="fills"
        tone={tradeCount > 0 ? "positive" : "neutral"}
        animKey={tradeCount}
      />
      <StatCard
        label="Volume Today"
        value={usd(volumeUsd)}
        unit="USD"
        tone="neutral"
        animKey={volumeUsd}
      />
    </div>
  );
}
