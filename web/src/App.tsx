import { useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";

const usd = (n: number | undefined) =>
  n === undefined ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const pct = (n: number | undefined) => (n === undefined ? "—" : `${(n * 100).toFixed(2)}%`);
const ts = (ms: number) => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const KIND_COLOR: Record<string, string> = {
  observation: "tag-observe", analysis: "tag-analysis", verdict: "tag-verdict",
  action: "tag-action", handoff: "tag-handoff", control: "tag-control",
};

export default function App() {
  const ledger    = useQuery(api.ledger.latest);
  const risk      = useQuery(api.riskState.get);
  const config    = useQuery(api.config.get);
  const decisions = useQuery(api.decisions.recent, { limit: 8 });
  const events    = useQuery(api.agentEvents.recent, { limit: 30 });
  const control   = useQuery(api.agentControl.get);

  const setHalted      = useMutation(api.config.setHalted);
  const setTradingMode = useMutation(api.config.setTradingMode);
  const updateLimits   = useMutation(api.config.updateLimits);
  const setControl     = useMutation(api.agentControl.set);

  const [floorInput, setFloorInput] = useState("");

  const mode    = config?.trading_mode;
  const halted  = config?.halted ?? false;
  const floor   = config?.equity_floor ?? 0;
  const paused  = control?.agents_paused ?? false;
  const pnl     = ledger?.cumulative_pnl_usd;
  const dd      = risk?.current_drawdown_pct;

  // Floor warning: look for a RiskGuard control event in recent events
  const floorWarn = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      (e.headline as string).includes("approaching floor"),
  );
  const floorHalt = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      (e.headline as string).includes("floor hit"),
  );

  const onModeClick = (next: "testnet" | "paper" | "mainnet") => {
    if (next === mode) return;
    if (next === "mainnet" &&
        !window.confirm("Switch to LIVE (mainnet)? This trades real funds via self-custody signing."))
      return;
    setTradingMode({ trading_mode: next });
  };

  const onKillSwitch = () => {
    if (!halted && !window.confirm("Halt the agent? It will stop trading within one cycle.")) return;
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };

  const onPauseAgents = () => {
    if (!paused && !window.confirm("Pause the advisory agent team? Trading continues unaffected.")) return;
    setControl({ agents_paused: !paused, updated_by: "user" });
  };

  const onStopResponse = () => {
    if (!window.confirm("Cancel the current in-flight agent action?")) return;
    setControl({ stop_response_id: String(Date.now()), updated_by: "user" });
  };

  const onSetFloor = () => {
    const val = parseFloat(floorInput);
    if (isNaN(val) || val < 0) return;
    updateLimits({ equity_floor: val });
    setFloorInput("");
  };

  return (
    <div className="wrap">
      <div className="title">ALIEN-TRADE</div>
      <div className="sub">Autonomous BSC agent · live state via Convex</div>

      {/* ── Floor alerts ── */}
      {floorHalt && (
        <div className="alert alert-halt">
          Trading HALTED — equity floor hit. Fund wallet or raise floor, then Resume.
        </div>
      )}
      {!floorHalt && floorWarn && (
        <div className="alert alert-warn">
          Portfolio approaching equity floor (${floor.toFixed(0)}). Consider adding capital.
        </div>
      )}

      {/* ── Trading mode ── */}
      <div className="panel">
        <div>
          <div className="panel-title">Trading mode</div>
          <div className="sub">Testnet &amp; paper are risk-free · Live trades real funds</div>
        </div>
        <div className="seg" role="group">
          {(["testnet", "paper", "mainnet"] as const).map((m) => (
            <button key={m} className={`seg-btn ${mode === m ? `seg-on seg-${m}` : ""}`}
              aria-pressed={mode === m} onClick={() => onModeClick(m)} disabled={config === undefined}>
              {m === "mainnet" ? "LIVE" : m}
            </button>
          ))}
        </div>
      </div>

      {/* ── Agent controls ── */}
      <div className="panel">
        <div className="panel-title" style={{ marginBottom: 10 }}>Agent controls</div>
        <div className="controls-row">
          <div className="control-item">
            <span className={`badge ${halted ? "badge-on" : "badge-off"}`}>
              {halted ? "HALTED" : "RUNNING"}
            </span>
            <button className={`btn ${halted ? "btn-resume" : "btn-halt"}`} onClick={onKillSwitch}>
              {halted ? "Resume" : "Kill Switch"}
            </button>
            <div className="sub">Halts trading within one cycle</div>
          </div>
          <div className="control-item">
            <span className={`badge ${paused ? "badge-warn" : "badge-off"}`}>
              {paused ? "PAUSED" : "ACTIVE"}
            </span>
            <button className="btn btn-pause" onClick={onPauseAgents}>
              {paused ? "Resume Agents" : "Pause Agents"}
            </button>
            <div className="sub">Quiets advisory team; trading unaffected</div>
          </div>
          <div className="control-item">
            <button className="btn btn-stop" onClick={onStopResponse}>Stop Response</button>
            <div className="sub">Cancel one in-flight agent action</div>
          </div>
        </div>
      </div>

      {/* ── Stats grid ── */}
      <div className="grid">
        <div className="card">
          <div className="label">Cumulative PnL</div>
          <div className={`value ${(pnl ?? 0) >= 0 ? "pos" : "neg"}`}>{usd(pnl)}</div>
        </div>
        <div className="card">
          <div className="label">Drawdown</div>
          <div className={`value ${(dd ?? 0) < 0 ? "neg" : ""}`}>{pct(dd)}</div>
        </div>
        <div className="card">
          <div className="label">Open exposure</div>
          <div className="value">{usd(risk?.open_exposure_usd)}</div>
        </div>
        <div className="card">
          <div className="label">Circuit breaker</div>
          <div className={`value ${risk?.circuit_breaker_active ? "neg" : "pos"}`}>
            {risk?.circuit_breaker_active ? "TRIPPED" : "OK"}
          </div>
        </div>
      </div>

      {/* ── Equity floor settings ── */}
      <div className="panel">
        <div className="panel-title">Equity floor</div>
        <div className="sub" style={{ marginBottom: 10 }}>
          Halt trading if portfolio drops below this amount.&nbsp;
          {floor > 0 ? <strong>Current floor: {usd(floor)}</strong> : "Currently disabled (0)."}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input className="floor-input" type="number" min="0" placeholder="e.g. 50"
            value={floorInput} onChange={(e) => setFloorInput(e.target.value)} />
          <button className="btn btn-set" onClick={onSetFloor} disabled={floorInput === ""}>
            Set floor
          </button>
          {floor > 0 && (
            <button className="btn btn-set" onClick={() => updateLimits({ equity_floor: 0 })}>
              Disable
            </button>
          )}
        </div>
      </div>

      {/* ── Signal health (8.11) ── */}
      <div className="panel">
        <div className="panel-title">Signal health</div>
        <div className="sub" style={{ marginBottom: 10 }}>
          Advisory signals feeding size decisions — amber means stale data
        </div>
        <div className="controls-row">
          {(["forecast", "sentiment"] as const).map((src) => {
            const related = (events ?? []).filter(
              (e) => e.agent === "RiskGuard" && e.kind === "observation" &&
                     typeof e.headline === "string" && e.headline.toLowerCase().includes(src),
            );
            const stale = related.length > 0 &&
              (related[0].headline as string).startsWith("STALE");
            const dot = stale ? "#f59e0b" : "#22c55e";
            const label = src === "forecast" ? "Forecast (4h)" : "Sentiment (2h)";
            return (
              <div key={src} className="control-item" style={{ gap: 6, flexDirection: "row", alignItems: "center" }}>
                <span style={{
                  width: 10, height: 10, borderRadius: "50%",
                  background: dot, display: "inline-block", flexShrink: 0,
                }} />
                <span className="sub">{label}</span>
                {stale && <span className="tag tag-control" style={{ fontSize: 10 }}>stale</span>}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Recent decisions ── */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="label" style={{ marginBottom: 8 }}>Recent decisions</div>
        <table>
          <thead>
            <tr><th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th></tr>
          </thead>
          <tbody>
            {(decisions ?? []).map((d) => (
              <tr key={d._id}>
                <td>{ts(d.timestamp_ms)}</td>
                <td>{d.symbol}</td>
                <td>{d.regime}</td>
                <td><span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span></td>
                <td>{usd(d.final_size_usd)}</td>
              </tr>
            ))}
            {decisions?.length === 0 && (
              <tr><td colSpan={5} className="sub">No decisions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Agent activity channel ── */}
      <div className="card">
        <div className="label" style={{ marginBottom: 8 }}>Agent activity</div>
        {(events ?? []).length === 0 ? (
          <div className="sub">No agent activity yet — start the agent to see the team's reasoning.</div>
        ) : (
          <div className="channel">
            {(events ?? []).map((e) => (
              <div key={e._id} className="evt">
                <div className="evt-meta">
                  <span className="evt-agent">{e.agent}</span>
                  <span className={`tag ${KIND_COLOR[e.kind] ?? "tag-observe"}`}>{e.kind}</span>
                  <span className="evt-time">{ts(e.ts_ms)}</span>
                  {e.cycle_id && <span className="evt-cycle">{String(e.cycle_id).slice(-8)}</span>}
                </div>
                <div className="evt-headline">{e.headline}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
