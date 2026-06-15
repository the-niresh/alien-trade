import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { StatCard } from "../components/StatCard";
import { EquityChart } from "../components/EquityChart";
import { AgentCard, AGENT_DEFS } from "../components/AgentCard";
import { PositionCard } from "../components/PositionCard";
import { usd, pct, ts } from "../lib/formatters";

type Props = { onAgentClick: (name: string) => void };

export function OverviewView({ onAgentClick }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const risk      = useQuery(api.riskState.get);
  const decisions = useQuery(api.decisions.recent, { limit: 3 });
  const roster    = useQuery(api.agentEvents.latestPerAgent);
  const positions = useQuery(api.positions.open) ?? [];
  const events    = useQuery(api.agentEvents.recent, { limit: 30 });

  const pnl = ledger?.cumulative_pnl_usd;
  const dd  = risk?.current_drawdown_pct;

  const floorHalt = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("floor hit"),
  );
  const floorWarn = !floorHalt && (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("approaching floor"),
  );

  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div>
      <AnimatePresence>
        {floorHalt && (
          <motion.div className="alert-banner alert-banner--halt"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            Trading HALTED — equity floor hit. Fund wallet or raise floor, then Resume.
          </motion.div>
        )}
        {floorWarn && (
          <motion.div className="alert-banner alert-banner--warn"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            Portfolio approaching equity floor. Consider adding capital.
          </motion.div>
        )}
      </AnimatePresence>

      <div className="overview-stats">
        <StatCard label="Cumulative PnL" value={usd(pnl)}
          tone={(pnl ?? 0) >= 0 ? "positive" : "negative"} animKey={pnl ?? 0} />
        <StatCard label="Max Drawdown" value={pct(dd)}
          tone={(dd ?? 0) > 0.05 ? "negative" : (dd ?? 0) > 0 ? "warn" : "positive"} />
        <StatCard label="Open Exposure" value={usd(risk?.open_exposure_usd)} />
        <StatCard label="Circuit Breaker"
          value={risk?.circuit_breaker_active ? "TRIPPED" : "OK"}
          tone={risk?.circuit_breaker_active ? "negative" : "positive"} />
      </div>

      <div className="panel">
        <div className="panel-title">Equity &amp; Drawdown</div>
        <EquityChart />
      </div>

      {positions.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 14, fontWeight: 700,
            color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.6px", marginBottom: 12 }}>
            Open Positions
          </div>
          <div className="positions-grid">
            {positions.slice(0, 3).map((p) => <PositionCard key={p._id} position={p} />)}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-title">Agent Team</div>
        <div className="agents-grid">
          {AGENT_DEFS.map((def) => (
            <AgentCard key={def.name} def={def}
              lastEvent={rosterMap.get(def.name)}
              onClick={() => onAgentClick(def.name)} />
          ))}
        </div>
      </div>

      {(decisions ?? []).length > 0 && (
        <div className="panel">
          <div className="panel-title">Recent Decisions</div>
          <table>
            <thead>
              <tr><th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th></tr>
            </thead>
            <tbody>
              {(decisions ?? []).map((d) => (
                <tr key={d._id}>
                  <td style={{ color: "var(--muted)" }}>{ts(d.timestamp_ms)}</td>
                  <td style={{ color: "var(--cyan)", fontWeight: 700 }}>{d.symbol}</td>
                  <td>{d.regime}</td>
                  <td><span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span></td>
                  <td>{usd(d.final_size_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
