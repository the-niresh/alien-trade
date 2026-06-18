import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { cn } from "@/lib/utils";
import { usd } from "../lib/formatters";

type StageStatus = "pass" | "block" | "stale" | "running";

function StageBadge({ status }: { status: StageStatus }) {
  const styles: Record<StageStatus, string> = {
    pass:    "bg-green/12 text-green border-green/25",
    block:   "bg-red/12 text-red border-red/25",
    stale:   "bg-yellow/12 text-yellow border-yellow/25",
    running: "bg-cyan/12 text-cyan border-cyan/25",
  };
  return (
    <span
      className={cn(
        "font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest",
        styles[status],
      )}
    >
      {status}
    </span>
  );
}

function Stage({
  n,
  title,
  badge,
  rows,
  isLast = false,
}: {
  n: number;
  title: string;
  badge: StageStatus;
  rows: { label: string; value: string }[];
  isLast?: boolean;
}) {
  return (
    <div className="flex gap-4 items-start">
      {/* Step indicator + connector line */}
      <div className="flex flex-col items-center gap-1 flex-shrink-0">
        <div className="w-7 h-7 rounded-full border border-border flex items-center justify-center font-mono text-[11px] text-muted-fg">
          {n}
        </div>
        {!isLast && <div className="w-px flex-1 bg-border min-h-[24px]" />}
      </div>

      {/* Stage card */}
      <div className="panel flex-1 mb-3 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="font-display text-[13px] font-bold text-text">{title}</span>
          <StageBadge status={badge} />
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {rows.map((r) => (
            <div key={r.label} className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-[11px] text-muted-fg">{r.label}</span>
              <span className="font-mono text-[12px] text-text tabular-nums">{r.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function fmt(v: number | null | undefined, decimals = 3): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

export function PipelineView() {
  const decision  = useQuery(api.decisions.latest);
  const signal    = useQuery(api.signals.latest, {});
  const riskState = useQuery(api.riskState.get);
  const events    = useQuery(api.agentEvents.recent, { limit: 5 });

  const ageMs  = decision ? Date.now() - decision.timestamp_ms : null;
  const ageSec = ageMs != null ? (ageMs / 1000).toFixed(0) : "—";

  return (
    <div className="max-w-[680px] mx-auto space-y-4">
      {/* Header */}
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span
            className="h-[2px] w-4 bg-cyan rounded-full inline-block"
            style={{ boxShadow: "0 0 6px var(--cyan)" }}
          />
          Deterministic Pipeline
        </div>
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">
            Decision Pipeline
          </h1>
          {ageMs != null && (
            <span className="font-mono text-[11px] text-muted-fg">
              last cycle {ageSec}s ago
            </span>
          )}
        </div>
      </div>

      {/* 5-stage pipeline */}
      <div className="space-y-0">
        <Stage
          n={1}
          title="Market Data"
          badge={signal ? "pass" : "stale"}
          rows={[
            { label: "Symbol",   value: signal?.symbol ?? "—" },
            { label: "EMA fast", value: fmt(signal?.momentum_ema_fast) },
            { label: "EMA slow", value: fmt(signal?.momentum_ema_slow) },
            { label: "ATR",      value: fmt(signal?.momentum_atr) },
          ]}
        />

        <Stage
          n={2}
          title="Signal Analysis"
          badge={signal?.composite_score != null ? "pass" : "stale"}
          rows={[
            { label: "Momentum",    value: fmt(decision?.signals?.momentum) },
            { label: "Derivatives", value: fmt(decision?.signals?.derivatives) },
            { label: "Sentiment",   value: fmt(decision?.signals?.sentiment) },
            { label: "Flow",        value: fmt(decision?.signals?.flow) },
            { label: "Composite",   value: fmt(signal?.composite_score) },
          ]}
        />

        <Stage
          n={3}
          title="Regime Detection"
          badge={decision?.regime ? "pass" : "stale"}
          rows={[
            { label: "Regime",  value: decision?.regime ?? "—" },
            { label: "Verdict", value: decision?.risk_verdict ?? "—" },
          ]}
        />

        <Stage
          n={4}
          title="Risk Check"
          badge={
            riskState?.circuit_breaker_active
              ? "block"
              : riskState
              ? "pass"
              : "stale"
          }
          rows={[
            {
              label: "Drawdown",
              value: riskState
                ? `${(riskState.current_drawdown_pct * 100).toFixed(1)}%`
                : "—",
            },
            { label: "Daily loss", value: riskState ? usd(riskState.daily_loss_usd) : "—" },
            { label: "Exposure",   value: riskState ? usd(riskState.open_exposure_usd) : "—" },
            { label: "Breaker",    value: riskState?.circuit_breaker_active ? "ACTIVE" : "off" },
          ]}
        />

        <Stage
          n={5}
          title="Execution"
          badge={decision?.trade_id ? "pass" : decision ? "running" : "stale"}
          isLast
          rows={[
            { label: "Target size", value: decision ? usd(decision.final_size_usd) : "—" },
            { label: "Reason",      value: decision?.risk_reason ?? "—" },
          ]}
        />
      </div>

      {/* Recent agent events feed */}
      {events && events.length > 0 && (
        <Panel label="Recent Events" tick="cyan">
          <div className="space-y-1.5">
            {events.slice(0, 4).map((e: { _id: string; agent: string; headline: string }) => (
              <div key={e._id} className="flex items-baseline gap-3">
                <span className="font-mono text-[10px] text-muted-fg flex-shrink-0 w-20 truncate">
                  {e.agent}
                </span>
                <span className="font-mono text-[12px] text-text/80">{e.headline}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
