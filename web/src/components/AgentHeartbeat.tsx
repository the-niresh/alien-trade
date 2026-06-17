import { useState, useEffect } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { ts, elapsed } from "../lib/formatters";
import { cn } from "@/lib/utils";

const CYCLE_MS = 3_600_000; // 1 hour

function formatCountdown(ms: number): string {
  if (ms <= 0) return "now";
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function AgentHeartbeat() {
  const decisions = useQuery(api.decisions.recent, { limit: 1 });
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  if (decisions === undefined) {
    return (
      <Panel label="Agent Heartbeat" tick="green">
        <div className="space-y-2">
          <Skeleton className="h-5 w-full bg-elevated rounded" />
          <Skeleton className="h-5 w-3/4 bg-elevated rounded" />
          <Skeleton className="h-5 w-1/2 bg-elevated rounded" />
        </div>
      </Panel>
    );
  }

  const lastMs = decisions[0]?.timestamp_ms ?? null;
  const nextMs = lastMs != null ? lastMs + CYCLE_MS : null;
  const timeUntilNext = nextMs != null ? nextMs - now : null;
  const isAlive = lastMs != null && now - lastMs < 2 * CYCLE_MS;

  return (
    <Panel label="Agent Heartbeat" tick={isAlive ? "green" : "red"}>
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="font-mono text-[11px] text-muted-fg w-24">Last cycle</span>
          {lastMs != null ? (
            <span className="font-mono text-[12px] text-text ml-2">
              {ts(lastMs)}{" "}
              <span className="text-muted-fg">({elapsed(lastMs)} ago)</span>
            </span>
          ) : (
            <span className="font-mono text-[12px] text-muted-fg">—</span>
          )}
        </div>

        <div className="flex justify-between items-center">
          <span className="font-mono text-[11px] text-muted-fg w-24">Next cycle</span>
          {nextMs != null ? (
            <span className="font-mono text-[12px] text-text ml-2">
              {ts(nextMs)}{" "}
              <span className="text-muted-fg">
                {timeUntilNext != null && timeUntilNext > 0
                  ? `in ${formatCountdown(timeUntilNext)}`
                  : "overdue"}
              </span>
            </span>
          ) : (
            <span className="font-mono text-[12px] text-muted-fg">—</span>
          )}
        </div>

        <div className="flex items-center gap-2 mt-1">
          <span
            className={cn(
              "inline-block w-2 h-2 rounded-full",
              isAlive
                ? "bg-green animate-pulse"
                : "bg-red",
            )}
          />
          <span
            className={cn(
              "font-mono text-[11px] font-bold tracking-[0.14em] uppercase",
              isAlive ? "text-green" : "text-red",
            )}
          >
            {isAlive ? "ALIVE" : "STALE"}
          </span>
        </div>
      </div>
    </Panel>
  );
}
