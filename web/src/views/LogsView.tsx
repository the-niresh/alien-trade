import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { motion } from "framer-motion";
import { ts, usd } from "../lib/formatters";
import { AGENT_DEFS } from "../components/AgentCard";

const KIND_COLOR: Record<string, string> = {
  observation: "tag-observe", analysis: "tag-analysis", verdict: "tag-verdict",
  action: "tag-action", handoff: "tag-handoff", control: "tag-control",
};

export function LogsView() {
  const decisions      = useQuery(api.decisions.recent, { limit: 20 });
  const auditLog       = useQuery(api.audit.recent, { limit: 60 });
  const events         = useQuery(api.agentEvents.recent, { limit: 40 });
  const wins           = useQuery(api.reflections.wins, { limit: 5 });
  const recordFeedback = useMutation(api.feedback.record);

  return (
    <div>
      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 20 }}>
        Logs
      </div>

      <div className="panel">
        <div className="panel-title">Decision History</div>
        <table>
          <thead>
            <tr><th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th><th>Rate</th></tr>
          </thead>
          <tbody>
            {(decisions ?? []).map((d) => (
              <tr key={d._id}>
                <td style={{ color: "var(--muted)" }}>{ts(d.timestamp_ms)}</td>
                <td style={{ color: "var(--cyan)", fontWeight: 700 }}>{d.symbol}</td>
                <td>{d.regime}</td>
                <td><span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span></td>
                <td>{usd(d.final_size_usd)}</td>
                <td>
                  {d.setup_key ? (
                    <span style={{ display: "inline-flex", gap: 4 }}>
                      <button className="btn-rate"
                        onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "good" })}>👍</button>
                      <button className="btn-rate"
                        onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "bad" })}>👎</button>
                    </span>
                  ) : <span style={{ color: "var(--muted)" }}>—</span>}
                </td>
              </tr>
            ))}
            {decisions?.length === 0 && (
              <tr><td colSpan={6} style={{ color: "var(--muted)" }}>No decisions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {(wins ?? []).length > 0 && (
        <div className="panel">
          <div className="panel-title">Winning Trades</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(wins ?? []).map((w) => (
              <motion.div key={w._id} className="win-card"
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span className="tag tag-allow">WIN</span>
                  <span style={{ color: "var(--green)", fontWeight: 700 }}>+{usd(w.outcome_pnl_usd)}</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>{w.regime} · {ts(w.timestamp_ms)}</div>
                {w.lesson && (
                  <div style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", marginTop: 4 }}>
                    "{w.lesson}"
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-title">Agent Activity Channel</div>
        {(events ?? []).length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>No activity yet.</div>
        ) : (
          <div className="channel">
            {(events ?? []).map((e) => {
              const def = AGENT_DEFS.find((a) => a.name === e.agent);
              return (
                <div key={e._id} className="evt">
                  <div className="evt-meta">
                    <span className="evt-agent" style={{ color: def?.color ?? "var(--cyan)" }}>{e.agent}</span>
                    <span className={`tag ${KIND_COLOR[e.kind] ?? "tag-observe"}`}>{e.kind}</span>
                    <span className="evt-time">{ts(e.ts_ms)}</span>
                    {e.cycle_id && <span className="evt-cycle">{String(e.cycle_id).slice(-8)}</span>}
                  </div>
                  <div className="evt-headline">{e.headline}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-title">Live Log Console</div>
        {(auditLog ?? []).length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>No log entries yet.</div>
        ) : (
          <div className="logconsole">
            {(auditLog ?? []).map((a) => (
              <div key={a._id} className={`logline log-${a.severity}`}>
                <span className="log-time">{ts(a.timestamp_ms)}</span>
                <span className="log-type">{a.event_type}</span>
                {a.cycle_id && <span className="log-cycle">{String(a.cycle_id).slice(-8)}</span>}
                <span className="log-payload">{a.payload}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
