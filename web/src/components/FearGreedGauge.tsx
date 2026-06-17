import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type Zone = {
  label: string;
  color: string;
  bar: string;
};

function getZone(score100: number): Zone {
  if (score100 <= 25) return { label: "EXTREME FEAR", color: "text-red",     bar: "bg-red" };
  if (score100 <= 45) return { label: "FEAR",         color: "text-yellow",  bar: "bg-yellow" };
  if (score100 <= 55) return { label: "NEUTRAL",      color: "text-muted-fg", bar: "bg-border-hi" };
  if (score100 <= 75) return { label: "GREED",        color: "text-yellow",  bar: "bg-yellow" };
  return                      { label: "EXTREME GREED", color: "text-red",   bar: "bg-red" };
}

function getStrategySignal(score: number): { label: string; cls: string } {
  if (score < 0.2)  return { label: "BUY SIGNAL",  cls: "text-green" };
  if (score > 0.6)  return { label: "TRIM SIGNAL", cls: "text-yellow" };
  return                    { label: "WATCHING",    cls: "text-muted-fg" };
}

export function FearGreedGauge() {
  const sentiment = useQuery(api.social.getSentiment, { symbol: "ETH" });

  if (sentiment === undefined) {
    return (
      <Panel label="Fear & Greed" tick="yellow">
        <div className="space-y-3">
          <Skeleton className="h-8 w-40 bg-elevated rounded" />
          <Skeleton className="h-3 w-full bg-elevated rounded" />
          <Skeleton className="h-4 w-48 bg-elevated rounded" />
        </div>
      </Panel>
    );
  }

  if (!sentiment) {
    return (
      <Panel label="Fear & Greed" tick="yellow">
        <p className="font-mono text-[12px] text-muted-fg py-1">
          // awaiting sentiment data
        </p>
      </Panel>
    );
  }

  // score is [-1, 1], convert to 0-100
  const score100 = Math.round((sentiment.score + 1) * 50);
  const zone = getZone(score100);
  const signal = getStrategySignal(sentiment.score);

  return (
    <Panel
      label="Fear & Greed"
      tick="yellow"
      action={
        <span className="font-mono text-[10px] text-muted-fg">
          ETH · {sentiment.n_posts} posts
        </span>
      }
    >
      <div className="flex flex-col gap-3">
        {/* Big number + zone label */}
        <div className="flex items-baseline gap-2.5">
          <span className={cn("font-display text-[36px] font-bold leading-none tabular-nums", zone.color)}>
            {score100}
          </span>
          <span className={cn("font-mono text-[11px] font-bold tracking-[0.12em] uppercase", zone.color)}>
            — {zone.label}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2.5 bg-border/30 rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-500", zone.bar)}
            style={{ width: `${score100}%` }}
          />
        </div>
        <div className="flex justify-between font-mono text-[9px] text-muted-fg/50">
          <span>0 EXTREME FEAR</span>
          <span>100 EXTREME GREED</span>
        </div>

        {/* Strategy signal */}
        <div className="flex items-center gap-2 border-t border-border/40 pt-2">
          <span className="font-mono text-[11px] text-muted-fg">Agent strategy:</span>
          <span className={cn("font-mono text-[11px] font-bold tracking-[0.1em]", signal.cls)}>
            {signal.label}
          </span>
        </div>
      </div>
    </Panel>
  );
}
