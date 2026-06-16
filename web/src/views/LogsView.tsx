import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { motion } from "framer-motion";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { ts, usd } from "../lib/formatters";
import { AGENT_DEFS } from "../components/AgentCard";
import { Panel } from "../components/Panel";
import { RegimeBadge } from "../components/RegimeBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const KIND_CLASS: Record<string, string> = {
  observation: "border-green/25 bg-green/10 text-green",
  analysis:    "border-cyan/25 bg-cyan/10 text-cyan",
  verdict:     "border-yellow/25 bg-yellow/10 text-yellow",
  action:      "border-purple/25 bg-purple/10 text-purple",
  handoff:     "border-green/15 bg-green/5 text-green/70",
  control:     "border-red/25 bg-red/10 text-red",
};

const VERDICT_CLASS: Record<string, string> = {
  allow:   "border-green/30 bg-green/10 text-green",
  block:   "border-red/30 bg-red/10 text-red",
  reduce:  "border-yellow/30 bg-yellow/10 text-yellow",
  observe: "border-green/30 bg-green/10 text-green",
};

export function LogsView() {
  const decisions      = useQuery(api.decisions.recent, { limit: 20 });
  const auditLog       = useQuery(api.audit.recent, { limit: 60 });
  const events         = useQuery(api.agentEvents.recent, { limit: 40 });
  const wins           = useQuery(api.reflections.wins, { limit: 5 });
  const recordFeedback = useMutation(api.feedback.record);

  return (
    <div className="space-y-4 max-w-[1180px] mx-auto">
      <h1 className="font-display text-[20px] font-bold tracking-wide">Logs</h1>

      {/* Decision History */}
      <Panel label="Decision History" tick="cyan" bodyClassName="px-0 pb-2">
        {decisions === undefined ? (
          <div className="px-4 space-y-2">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-8 w-full bg-elevated" />)}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px] min-w-[560px]">
              <thead>
                <tr>
                  {["Time", "Symbol", "Regime", "Verdict", "Size", "Rate"].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 border-b border-border text-muted-fg font-mono font-semibold text-[10px] uppercase tracking-[0.14em]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr key={d._id} className="border-b border-border last:border-0 hover:bg-elevated/40 transition-colors">
                    <td className="px-4 py-2.5 font-mono text-[11px] text-muted-fg">{ts(d.timestamp_ms)}</td>
                    <td className="px-4 py-2.5 font-display text-cyan font-bold">{d.symbol}</td>
                    <td className="px-4 py-2.5"><RegimeBadge regime={d.regime} /></td>
                    <td className="px-4 py-2.5">
                      <span className={cn("font-mono text-[10px] font-bold tracking-[0.12em] uppercase px-2 py-1 rounded border", VERDICT_CLASS[d.risk_verdict] ?? "border-border text-muted-fg")}>
                        {d.risk_verdict}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono tabular-nums">{usd(d.final_size_usd)}</td>
                    <td className="px-4 py-2.5">
                      {d.setup_key ? (
                        <span className="inline-flex gap-1.5">
                          <button
                            aria-label="Good call"
                            className="grid place-items-center h-7 w-7 bg-elevated border border-border rounded-md text-muted-fg hover:text-green hover:border-green/40 transition-colors cursor-pointer"
                            onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "good" })}
                          ><ThumbsUp className="w-3.5 h-3.5" /></button>
                          <button
                            aria-label="Bad call"
                            className="grid place-items-center h-7 w-7 bg-elevated border border-border rounded-md text-muted-fg hover:text-red hover:border-red/40 transition-colors cursor-pointer"
                            onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "bad" })}
                          ><ThumbsDown className="w-3.5 h-3.5" /></button>
                        </span>
                      ) : <span className="text-border-hi">—</span>}
                    </td>
                  </tr>
                ))}
                {decisions.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-4 font-mono text-[12px] text-muted-fg">// no decisions yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {/* Winning Trades */}
      {(wins ?? []).length > 0 && (
        <Panel label="Winning Trades">
          <div className="space-y-2.5">
            {(wins ?? []).map((w) => (
              <motion.div
                key={w._id}
                className="bg-green/[0.06] border border-green/25 rounded-xl px-3.5 py-3"
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[10px] font-bold tracking-[0.16em] text-green border border-green/30 bg-green/10 rounded px-2 py-0.5">WIN</span>
                  <span className="font-display text-green font-bold tabular-nums glow-green">+{usd(w.outcome_pnl_usd)}</span>
                </div>
                <div className="font-mono text-[11px] text-muted-fg">{w.regime} · {ts(w.timestamp_ms)}</div>
                {w.lesson && <div className="text-[12px] text-muted-fg italic mt-1">"{w.lesson}"</div>}
              </motion.div>
            ))}
          </div>
        </Panel>
      )}

      {/* Agent Activity Channel */}
      <Panel label="Agent Activity Channel" tick="purple">
        {events === undefined ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 w-full bg-elevated rounded-xl" />)}
          </div>
        ) : events.length === 0 ? (
          <p className="font-mono text-[12px] text-muted-fg">// no activity yet</p>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-[500px] overflow-y-auto pr-1">
            {events.map((e) => {
              const def = AGENT_DEFS.find((a) => a.name === e.agent);
              return (
                <div key={e._id} className="bg-bg/50 border border-border rounded-[10px] px-3 py-2.5 hover:border-border-hi transition-colors">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-display font-bold text-[12px]" style={{ color: def?.color ?? "var(--cyan)" }}>{e.agent}</span>
                    <span className={cn("font-mono text-[9px] font-bold tracking-[0.12em] uppercase px-1.5 py-0.5 rounded border", KIND_CLASS[e.kind] ?? "border-border text-muted-fg")}>
                      {e.kind}
                    </span>
                    <span className="font-mono text-[10px] text-muted-fg ml-auto">{ts(e.ts_ms)}</span>
                    {e.cycle_id && <span className="font-mono text-[9px] text-border-hi">{String(e.cycle_id).slice(-8)}</span>}
                  </div>
                  <div className="text-[13px] text-text/85 leading-relaxed">{e.headline}</div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* Live Log Console */}
      <Panel label="Live Log Console" tick="green">
        {auditLog === undefined ? (
          <Skeleton className="h-32 w-full bg-elevated rounded-lg" />
        ) : auditLog.length === 0 ? (
          <p className="font-mono text-[12px] text-muted-fg">// no log entries yet</p>
        ) : (
          <div className="logconsole max-h-80 overflow-y-auto border border-border rounded-lg p-2.5">
            {auditLog.map((a) => (
              <div key={a._id} className={cn(
                "flex gap-2 py-px whitespace-nowrap",
                a.severity === "warn" ? "text-yellow" : a.severity === "error" ? "text-red" : ""
              )}>
                <span className="text-[#3a5068] flex-shrink-0">{ts(a.timestamp_ms)}</span>
                <span className={cn("flex-shrink-0 min-w-[96px]", a.severity === "error" ? "text-red" : "text-green")}>{a.event_type}</span>
                {a.cycle_id && <span className="text-[#3a5068] flex-shrink-0">{String(a.cycle_id).slice(-8)}</span>}
                <span className={cn(
                  "overflow-hidden text-ellipsis",
                  a.severity === "warn" ? "text-yellow" : a.severity === "error" ? "text-red" : "text-[#7090aa]"
                )}>{a.payload}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
