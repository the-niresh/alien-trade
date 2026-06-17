import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { RegimeBadge } from "./RegimeBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// Contrarian strategy weights
const WEIGHTS = { momentum: 0.20, derivatives: 0.20, sentiment: 0.60 };

type SignalRowProps = {
  label: string;
  score?: number | null;
};

function SignalRow({ label, score }: SignalRowProps) {
  const hasValue = score != null;
  const isPositive = hasValue && score >= 0;
  const pct = hasValue ? Math.min(Math.abs(score) * 100, 100) : 0;

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[11px] text-muted-fg w-28 flex-shrink-0 truncate">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-border/30 rounded-full overflow-hidden">
        {hasValue && (
          <div
            className={cn(
              "h-full rounded-full",
              isPositive ? "bg-green" : "bg-red",
            )}
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      <span
        className={cn(
          "font-mono text-[12px] w-12 text-right flex-shrink-0",
          !hasValue ? "text-muted-fg" :
          isPositive ? "text-green" : "text-red",
        )}
      >
        {hasValue ? (score >= 0 ? "+" : "") + score.toFixed(2) : "n/a"}
      </span>
    </div>
  );
}

export function SignalScores() {
  const decisions = useQuery(api.decisions.recent, { limit: 1 });

  if (decisions === undefined) {
    return (
      <Panel label="Signal Scores" tick="green">
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-full bg-elevated rounded" />
          ))}
        </div>
      </Panel>
    );
  }

  const latest = decisions[0];
  const signals = latest?.signals ?? {};
  const regime = latest?.regime;

  const mom = signals.momentum ?? null;
  const deriv = signals.derivatives ?? null;
  const sent = signals.sentiment ?? null;
  const flow = signals.flow ?? null;

  // Composite: weighted sum of available signals
  let composite: number | null = null;
  const hasAny = mom != null || deriv != null || sent != null;
  if (hasAny) {
    let sum = 0;
    let totalWeight = 0;
    if (mom != null) { sum += mom * WEIGHTS.momentum; totalWeight += WEIGHTS.momentum; }
    if (deriv != null) { sum += deriv * WEIGHTS.derivatives; totalWeight += WEIGHTS.derivatives; }
    if (sent != null) { sum += sent * WEIGHTS.sentiment; totalWeight += WEIGHTS.sentiment; }
    composite = totalWeight > 0 ? sum / totalWeight : null;
  }

  return (
    <Panel
      label="Signal Scores"
      tick="green"
      action={regime ? <RegimeBadge regime={regime} /> : undefined}
    >
      {!latest ? (
        <p className="font-mono text-[12px] text-muted-fg py-1">
          // awaiting first decision
        </p>
      ) : (
        <div className="flex flex-col gap-2.5">
          <SignalRow label="Momentum" score={mom} />
          <SignalRow label="Derivatives" score={deriv} />
          <SignalRow label="Fear & Greed" score={sent} />
          <SignalRow label="Flow" score={flow} />
          <div className="border-t border-border/40 pt-2 mt-0.5">
            <SignalRow label="Composite" score={composite} />
          </div>
        </div>
      )}
    </Panel>
  );
}
