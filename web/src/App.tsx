import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";

const usd = (n: number | undefined) =>
  n === undefined ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const pct = (n: number | undefined) => (n === undefined ? "—" : `${(n * 100).toFixed(2)}%`);

export default function App() {
  const ledger = useQuery(api.ledger.latest);
  const risk = useQuery(api.riskState.get);
  const config = useQuery(api.config.get);
  const decisions = useQuery(api.decisions.recent, { limit: 12 });
  const setHalted = useMutation(api.config.setHalted);
  const setTradingMode = useMutation(api.config.setTradingMode);

  const mode = config?.trading_mode;
  const onModeClick = (next: "testnet" | "paper" | "mainnet") => {
    if (next === mode) return;
    // mainnet moves real funds — make the judge confirm the irreversible switch.
    if (next === "mainnet" &&
        !window.confirm("Switch to LIVE (mainnet)? This trades real funds via self-custody signing.")) {
      return;
    }
    setTradingMode({ trading_mode: next });
  };

  const halted = config?.halted ?? false;
  const pnl = ledger?.cumulative_pnl_usd;
  const dd = risk?.current_drawdown_pct;

  return (
    <div className="wrap">
      <div className="title">👽 ALIEN-TRADE</div>
      <div className="sub">
        Autonomous BSC agent · live state via Convex
      </div>

      <div className="kill">
        <div>
          <div style={{ fontWeight: 700 }}>Trading mode</div>
          <div className="sub">Testnet & paper are risk-free · Live trades real funds</div>
        </div>
        <div className="seg" role="group" aria-label="Trading mode">
          {(["testnet", "paper", "mainnet"] as const).map((m) => (
            <button
              key={m}
              className={`seg-btn ${mode === m ? `seg-on seg-${m}` : ""}`}
              aria-pressed={mode === m}
              onClick={() => onModeClick(m)}
              disabled={config === undefined}
            >
              {m === "mainnet" ? "LIVE" : m}
            </button>
          ))}
        </div>
      </div>

      <div className="kill">
        <div>
          <div style={{ fontWeight: 700 }}>Kill switch</div>
          <div className="sub">Halts the agent within one decision cycle</div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span className={`badge ${halted ? "badge-on" : "badge-off"}`}>
            {halted ? "HALTED" : "RUNNING"}
          </span>
          <button
            className={`btn ${halted ? "btn-resume" : "btn-halt"}`}
            onClick={() => setHalted({ halted: !halted })}
          >
            {halted ? "Resume" : "Halt"}
          </button>
        </div>
      </div>

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

      <div className="card">
        <div className="label" style={{ marginBottom: 8 }}>Recent decisions</div>
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th>
            </tr>
          </thead>
          <tbody>
            {(decisions ?? []).map((d) => (
              <tr key={d._id}>
                <td>{new Date(d.timestamp_ms).toLocaleTimeString()}</td>
                <td>{d.symbol}</td>
                <td>{d.regime}</td>
                <td><span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span></td>
                <td>{usd(d.final_size_usd)}</td>
              </tr>
            ))}
            {decisions && decisions.length === 0 && (
              <tr><td colSpan={5} className="sub">No decisions yet — start the agent.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
