import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

export function ScanningSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryScanning />;
  return <SpawnedScanning agent={agent} />;
}

function PrimaryScanning() {
  const decisions = useQuery(api.decisions.recent, { limit: 20 }) ?? [];
  if (decisions.length === 0) return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">No cycles recorded yet.</div>;
  return (
    <div className="flex flex-col gap-2">
      {decisions.map((d) => (
        <div key={d._id} className="panel p-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-mono text-[11px] text-text">{d.symbol}</span>
            <span className="font-mono text-[9px] text-purple border border-purple/20 bg-purple/10 rounded px-1.5 py-0.5 uppercase">{d.regime}</span>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {d.signals.momentum != null && <Sig label="mom" v={d.signals.momentum} />}
            {d.signals.sentiment != null && <Sig label="sent" v={d.signals.sentiment} />}
            <span className={cn("font-mono text-[10px] uppercase",
              d.risk_verdict === "block" ? "text-red" : d.risk_verdict === "reduce" ? "text-yellow-400" : "text-green")}>{d.risk_verdict}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Sig({ label, v }: { label: string; v: number }) {
  return <span className="font-mono text-[9px] text-muted-fg">{label} <span className={v >= 0 ? "text-green" : "text-red"}>{v.toFixed(2)}</span></span>;
}

function SpawnedScanning({ agent }: { agent: DetailAgent }) {
  const runs = useQuery(api.agentRuns.recent, agent.id ? { agent_id: agent.id } : "skip") ?? [];
  if (runs.length === 0) return <div className="panel p-8 text-center font-mono text-[12px] text-muted-fg/60">No runs yet.</div>;
  return (
    <div className="flex flex-col gap-2">
      {runs.map((r) => (
        <div key={r._id} className="panel p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-text">{r.ok ? "✅" : "⚠️"} {r.summary}</span>
            <span className="font-mono text-[9px] text-muted-fg/50">{new Date(r.started_ms).toLocaleTimeString()}</span>
          </div>
          {r.tool_calls.length > 0 && (
            <div className="flex items-center gap-0.5 flex-wrap">
              {r.tool_calls.map((tc: { tool: string }, i: number) => (
                <span key={i} className="font-mono text-[9px] rounded px-1.5 py-0.5 border bg-purple/10 text-purple border-purple/20">{tc.tool}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
