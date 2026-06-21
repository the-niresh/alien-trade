import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "green" | "red" | "muted" }) {
  return (
    <div className="panel p-3 flex flex-col gap-1">
      <span className="font-mono text-[9px] text-muted-fg/60 uppercase tracking-widest">{label}</span>
      <span className={cn("font-mono text-[16px] font-bold",
        tone === "green" ? "text-green" : tone === "red" ? "text-red" : "text-text")}>{value}</span>
    </div>
  );
}

export function DashboardSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryDashboard />;
  return <SpawnedDashboard agent={agent} />;
}

function PrimaryDashboard() {
  const sc = useQuery(api.scorecard.get);
  const decision = useQuery(api.decisions.latest);
  const pnl = sc?.net_pnl_usd ?? null;
  const dd = sc?.max_drawdown ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-2">
        <Stat label="Realized PnL" value={pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`} tone={pnl == null ? "muted" : pnl >= 0 ? "green" : "red"} />
        <Stat label="Win Rate" value={sc?.win_rate == null ? "—" : `${(sc.win_rate * 100).toFixed(0)}%`} />
        <Stat label="Trades" value={sc?.n_trades?.toString() ?? "—"} />
        <Stat label="Max Drawdown" value={dd == null ? "—" : `${(dd * 100).toFixed(1)}%`} tone={dd ? "red" : "muted"} />
        <Stat label="Sortino" value={sc?.sortino?.toFixed(2) ?? "—"} />
        <Stat label="Profit Factor" value={sc?.profit_factor?.toFixed(2) ?? "—"} />
      </div>

      <div className="panel p-4">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-2">AI Insights</div>
        {decision ? (
          <div className="flex flex-col gap-1.5">
            <p className="font-mono text-[12px] text-text leading-relaxed">
              Regime <span className="text-purple">{decision.regime}</span> on {decision.symbol} ·
              verdict <span className={cn(decision.risk_verdict === "block" ? "text-red" : decision.risk_verdict === "reduce" ? "text-yellow-400" : "text-green")}>{decision.risk_verdict}</span>
            </p>
            {decision.risk_reason && <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed">{decision.risk_reason}</p>}
            <p className="font-mono text-[10px] text-muted-fg/50">target ${decision.target_position_usd.toFixed(0)} → final ${decision.final_size_usd.toFixed(0)}</p>
          </div>
        ) : (
          <p className="font-mono text-[11px] text-muted-fg/60">No decisions recorded yet.</p>
        )}
      </div>
    </div>
  );
}

function SpawnedDashboard({ agent }: { agent: DetailAgent }) {
  const runs = useQuery(api.agentRuns.recent, agent.id ? { agent_id: agent.id } : "skip") ?? [];
  const lastRun = runs[0];
  const okCount = runs.filter((r) => r.ok).length;
  const avgTools = runs.length ? (runs.reduce((s, r) => s + r.tool_calls.length, 0) / runs.length) : 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-2">
        <Stat label="Runs" value={runs.length.toString()} />
        <Stat label="OK / Total" value={`${okCount}/${runs.length}`} tone={runs.length > 0 && okCount === runs.length ? "green" : "muted"} />
        <Stat label="Avg Tools/Run" value={avgTools.toFixed(1)} />
      </div>
      <div className="panel p-4">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-2">Goal</div>
        <p className="font-mono text-[12px] text-text leading-relaxed">{agent.goal ?? "—"}</p>
        {lastRun && <p className="font-mono text-[11px] text-muted-fg/70 mt-2">Last run: {lastRun.ok ? "✅" : "⚠️"} {lastRun.summary}</p>}
      </div>
    </div>
  );
}
