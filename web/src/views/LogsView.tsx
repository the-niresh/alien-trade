import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { motion } from "framer-motion";
import { ts, usd } from "../lib/formatters";
import { AGENT_DEFS } from "../components/AgentCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const KIND_CLASS: Record<string, string> = {
  observation: "border-green/20 bg-green/10 text-green",
  analysis:    "border-cyan/20 bg-cyan/10 text-cyan",
  verdict:     "border-yellow/20 bg-yellow/10 text-yellow",
  action:      "border-purple/20 bg-purple/10 text-purple",
  handoff:     "border-green/10 bg-green/5 text-green/70",
  control:     "border-red/20 bg-red/10 text-red",
};

const VERDICT_CLASS: Record<string, string> = {
  allow:   "border-green/20 bg-green/10 text-green",
  block:   "border-red/20 bg-red/10 text-red",
  reduce:  "border-yellow/20 bg-yellow/10 text-yellow",
  observe: "border-green/20 bg-green/10 text-green",
};

export function LogsView() {
  const decisions      = useQuery(api.decisions.recent, { limit: 20 });
  const auditLog       = useQuery(api.audit.recent, { limit: 60 });
  const events         = useQuery(api.agentEvents.recent, { limit: 40 });
  const wins           = useQuery(api.reflections.wins, { limit: 5 });
  const recordFeedback = useMutation(api.feedback.record);

  return (
    <div className="space-y-4">
      <h1 className="font-grotesk text-xl font-bold">Logs</h1>

      {/* Decision History */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Decision History</p>
        </CardHeader>
        <CardContent className="p-0">
          {decisions === undefined ? (
            <div className="px-6 pb-4 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-8 w-full bg-elevated" />)}
            </div>
          ) : (
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr>
                  {["Time", "Symbol", "Regime", "Verdict", "Size", "Rate"].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 border-b border-border text-muted-fg font-semibold text-[11px] uppercase tracking-[0.4px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr key={d._id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 text-muted-fg">{ts(d.timestamp_ms)}</td>
                    <td className="px-4 py-2.5 text-cyan font-bold">{d.symbol}</td>
                    <td className="px-4 py-2.5">{d.regime}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant="outline" className={cn("text-[11px] font-bold", VERDICT_CLASS[d.risk_verdict] ?? "")}>
                        {d.risk_verdict}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">{usd(d.final_size_usd)}</td>
                    <td className="px-4 py-2.5">
                      {d.setup_key ? (
                        <span className="inline-flex gap-1">
                          <button
                            className="bg-elevated border border-border rounded-md px-2 py-1 text-[13px] hover:bg-border transition-colors"
                            onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "good" })}
                          >👍</button>
                          <button
                            className="bg-elevated border border-border rounded-md px-2 py-1 text-[13px] hover:bg-border transition-colors"
                            onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "bad" })}
                          >👎</button>
                        </span>
                      ) : <span className="text-muted-fg">—</span>}
                    </td>
                  </tr>
                ))}
                {decisions.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-4 text-muted-fg">No decisions yet.</td></tr>
                )}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Winning Trades */}
      {(wins ?? []).length > 0 && (
        <Card className="bg-surface border-border">
          <CardHeader className="pb-3">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Winning Trades</p>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {(wins ?? []).map((w) => (
              <motion.div
                key={w._id}
                className="bg-green/5 border border-green/20 rounded-xl px-3.5 py-3"
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              >
                <div className="flex justify-between items-center mb-1">
                  <Badge className="bg-green/10 text-green border-green/20 text-[11px] font-bold">WIN</Badge>
                  <span className="text-green font-bold">+{usd(w.outcome_pnl_usd)}</span>
                </div>
                <div className="text-[12px] text-muted-fg">{w.regime} · {ts(w.timestamp_ms)}</div>
                {w.lesson && <div className="text-[12px] text-muted-fg italic mt-1">"{w.lesson}"</div>}
              </motion.div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Agent Activity Channel */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Agent Activity Channel</p>
        </CardHeader>
        <CardContent>
          {events === undefined ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 w-full bg-elevated rounded-xl" />)}
            </div>
          ) : events.length === 0 ? (
            <p className="text-muted-fg text-[13px]">No activity yet.</p>
          ) : (
            <div className="flex flex-col gap-1.5 max-h-[500px] overflow-y-auto pr-1">
              {events.map((e) => {
                const def = AGENT_DEFS.find((a) => a.name === e.agent);
                return (
                  <div key={e._id} className="bg-bg border border-border rounded-[10px] px-3 py-2.5">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-bold text-[12px]" style={{ color: def?.color ?? "var(--cyan)" }}>{e.agent}</span>
                      <Badge variant="outline" className={cn("text-[10px] font-bold", KIND_CLASS[e.kind] ?? "")}>
                        {e.kind}
                      </Badge>
                      <span className="text-[11px] text-muted-fg ml-auto">{ts(e.ts_ms)}</span>
                      {e.cycle_id && <span className="text-[10px] text-border-hi font-mono">{String(e.cycle_id).slice(-8)}</span>}
                    </div>
                    <div className="text-[13px] text-text leading-relaxed">{e.headline}</div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Live Log Console */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Live Log Console</p>
        </CardHeader>
        <CardContent>
          {auditLog === undefined ? (
            <Skeleton className="h-32 w-full bg-elevated rounded-lg" />
          ) : auditLog.length === 0 ? (
            <p className="text-muted-fg text-[13px]">No log entries yet.</p>
          ) : (
            <div className="logconsole max-h-80 overflow-y-auto border border-border rounded-lg p-2.5">
              {auditLog.map((a) => (
                <div key={a._id} className={cn(
                  "flex gap-2 py-px whitespace-nowrap",
                  a.severity === "warn" ? "text-yellow" : a.severity === "error" ? "text-red" : ""
                )}>
                  <span className="text-[#364a60] flex-shrink-0">{ts(a.timestamp_ms)}</span>
                  <span className={cn("flex-shrink-0 min-w-[96px]", a.severity === "error" ? "text-red" : "text-cyan")}>{a.event_type}</span>
                  {a.cycle_id && <span className="text-[#364a60] flex-shrink-0">{String(a.cycle_id).slice(-8)}</span>}
                  <span className={cn(
                    "overflow-hidden text-ellipsis",
                    a.severity === "warn" ? "text-yellow" : a.severity === "error" ? "text-red" : "text-[#7090aa]"
                  )}>{a.payload}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
