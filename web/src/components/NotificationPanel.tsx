import { useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { ts } from "../lib/formatters";
import { cn } from "@/lib/utils";
import { eventSeverity, SEVERITY_LABEL, type Severity } from "../lib/eventSeverity";

const TIER_STYLE: Record<Severity, string> = {
  info: "text-muted-fg border-border bg-bg/50",
  trade: "text-cyan border-cyan/30 bg-cyan/10",
  risk: "text-yellow border-yellow/30 bg-yellow/10",
  critical: "text-red border-red/30 bg-red/10",
};

const FILTERS: Array<Severity | "all"> = ["all", "critical", "risk", "trade", "info"];

export function NotificationPanel({ limit = 50 }: { limit?: number }) {
  const events = useQuery(api.agentEvents.recent, { limit });
  const [filter, setFilter] = useState<Severity | "all">("all");

  const rows = (events ?? [])
    .map((e) => ({ ...e, sev: eventSeverity(e) }))
    .filter((e) => filter === "all" || e.sev === filter);

  return (
    <Panel
      label="Notifications"
      tick="green"
      action={
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded border transition-colors cursor-pointer",
                filter === f
                  ? "text-green border-green/40 bg-green/10"
                  : "text-muted-fg border-border hover:border-green/30",
              )}
            >
              {f === "all" ? "all" : SEVERITY_LABEL[f]}
            </button>
          ))}
        </div>
      }
    >
      {events === undefined ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full bg-elevated rounded-lg" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="font-mono text-[12px] text-muted-fg py-2">// no notifications</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {rows.map((e) => (
            <div key={e._id} className={cn("rounded-lg border px-3 py-2", TIER_STYLE[e.sev])}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[9px] font-bold uppercase tracking-widest flex-shrink-0">
                  {SEVERITY_LABEL[e.sev]}
                </span>
                <span className="font-display text-[11px] font-bold flex-shrink-0">{e.agent}</span>
                <span className="font-mono text-[10px] text-muted-fg/60 ml-auto flex-shrink-0">
                  {ts(e.ts_ms)}
                </span>
              </div>
              <p className="font-mono text-[12px] text-text mt-1 leading-snug">{e.headline}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
