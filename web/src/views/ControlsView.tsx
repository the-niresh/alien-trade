import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "../components/KillSwitch";
import { withToken } from "../lib/control";
import { usd, pct } from "../lib/formatters";

const STRATEGIES = [
  { name: "momentum",   label: "Momentum",   blurb: "Rides confirmed uptrends." },
  { name: "contrarian", label: "Contrarian", blurb: "Buys fear, trims greed. Best in down/choppy markets." },
  { name: "balanced",   label: "Balanced",   blurb: "Momentum + derivatives + fear." },
  { name: "defensive",  label: "Defensive",  blurb: "Rare high-conviction longs. Minimises drawdown." },
];

export function ControlsView() {
  const config  = useQuery(api.config.get);
  const control = useQuery(api.agentControl.get);
  const [floorInput, setFloorInput] = useState("");
  const [showSliders, setShowSliders] = useState(false);

  const _setHalted      = useMutation(api.config.setHalted);
  const _setTradingMode = useMutation(api.config.setTradingMode);
  const _updateLimits   = useMutation(api.config.updateLimits);
  const _setControl     = useMutation(api.agentControl.set);
  const _setStrategy    = useMutation(api.config.setStrategy);
  const _setAutopilot   = useMutation(api.config.setAutopilot);
  const setHalted      = (a: Parameters<typeof _setHalted>[0])      => _setHalted(withToken(a));
  const setTradingMode = (a: Parameters<typeof _setTradingMode>[0]) => _setTradingMode(withToken(a));
  const updateLimits   = (a: Parameters<typeof _updateLimits>[0])   => _updateLimits(withToken(a));
  const setControl     = (a: Parameters<typeof _setControl>[0])     => _setControl(withToken(a));
  const setStrategy    = (a: Parameters<typeof _setStrategy>[0])    => _setStrategy(withToken(a));
  const setAutopilot   = (a: Parameters<typeof _setAutopilot>[0])   => _setAutopilot(withToken(a));

  const halted = config?.halted ?? false;
  const paused = control?.agents_paused ?? false;
  const mode   = config?.trading_mode;
  const floor  = config?.equity_floor ?? 0;
  const active = config?.strategy_name ?? "balanced";
  const ap     = config?.autopilot;

  const onKillToggle = () => {
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };
  const onSetFloor = () => {
    const v = parseFloat(floorInput);
    if (!isNaN(v) && v >= 0) { updateLimits({ equity_floor: v }); setFloorInput(""); }
  };

  return (
    <div style={{ maxWidth: 680, margin: "0 auto" }}>
      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 24 }}>
        Controls
      </div>

      {/* Kill switch */}
      <div className="panel" style={{ textAlign: "center" }}>
        <div className="panel-title">Emergency Stop</div>
        <KillSwitch halted={halted} onToggle={onKillToggle} hero />
        <div style={{ marginTop: 12, fontSize: 13, color: "var(--muted)" }}>
          {halted ? "Agent is HALTED. Hold to resume trading." : "Hold for 1.5s to halt all trading."}
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 8, justifyContent: "center" }}>
          <button className="btn btn--ghost btn--sm" onClick={() => {
            if (!paused && !window.confirm("Pause advisory agents? Trading continues.")) return;
            setControl({ agents_paused: !paused, updated_by: "user" });
          }}>
            {paused ? "Resume Agents" : "Pause Agents"}
          </button>
          <button className="btn btn--danger btn--sm" onClick={() => {
            if (!window.confirm("Cancel the current in-flight agent action?")) return;
            setControl({ stop_response_id: String(Date.now()), updated_by: "user" });
          }}>
            Stop Response
          </button>
        </div>
      </div>

      {/* Trading mode */}
      <div className="panel">
        <div className="panel-title">Trading Mode</div>
        <div className="seg">
          {(["testnet", "paper", "mainnet"] as const).map((m) => (
            <button key={m}
              className={`seg-btn ${mode === m ? `seg-btn--active seg-btn--${m}` : ""}`}
              onClick={() => {
                if (m === mode) return;
                if (m === "mainnet" && !window.confirm("Switch to LIVE mainnet? This trades real funds.")) return;
                setTradingMode({ trading_mode: m });
              }}
              disabled={config === undefined}
            >
              {m === "mainnet" ? "LIVE" : m}
            </button>
          ))}
        </div>
      </div>

      {/* Strategy */}
      <div className="panel">
        <div className="panel-title">Strategy</div>
        <div className="strategy-grid">
          {STRATEGIES.map((s) => (
            <button key={s.name}
              className={`strategy-card ${active === s.name ? "strategy-card--active" : ""}`}
              onClick={() => setStrategy({ strategy_name: s.name })}
            >
              <div className="strategy-card__name">{s.label}</div>
              <div className="strategy-card__blurb">{s.blurb}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Equity floor */}
      <div className="panel">
        <div className="panel-title">Equity Floor</div>
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
          {floor > 0
            ? <strong style={{ color: "var(--text)" }}>Floor: {usd(floor)}</strong>
            : "Disabled — agent trades until manually halted."}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input className="num-input" type="number" min="0" placeholder="e.g. 50"
            value={floorInput} onChange={(e) => setFloorInput(e.target.value)} />
          <button className="btn btn--primary btn--sm" onClick={onSetFloor} disabled={!floorInput}>Set</button>
          {floor > 0 && (
            <button className="btn btn--ghost btn--sm" onClick={() => updateLimits({ equity_floor: 0 })}>Remove</button>
          )}
        </div>
      </div>

      {/* Autopilot */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: ap?.enabled ? 14 : 0 }}>
          <div className="panel-title" style={{ margin: 0 }}>Autopilot</div>
          <button
            className={`btn btn--sm ${ap?.enabled ? "btn--primary" : "btn--ghost"}`}
            onClick={() => setAutopilot({ autopilot: { ...(ap ?? {}), enabled: !(ap?.enabled ?? false) } as Parameters<typeof setAutopilot>[0]["autopilot"] })}
          >
            {ap?.enabled ? "ON" : "OFF"}
          </button>
        </div>
        {ap?.enabled && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[
              { label: "Take profit %",        key: "profit_target_pct" },
              { label: "Trailing give-back %", key: "trailing_giveback_pct" },
              { label: "Daily target %",       key: "daily_profit_target_pct" },
            ].map(({ label, key }) => (
              <div key={key} className="ap-row">
                <span>{label}</span>
                <input className="num-input" type="number" min="0" style={{ width: 80 }}
                  placeholder="—"
                  defaultValue={(ap as unknown as Record<string, number | undefined>)[key] != null
                    ? (((ap as unknown as Record<string, number | undefined>)[key] as number) * 100).toFixed(1) : ""}
                  onBlur={(e) => {
                    const v = parseFloat(e.target.value);
                    setAutopilot({ autopilot: { ...ap, [key]: isNaN(v) ? undefined : v / 100 } as Parameters<typeof setAutopilot>[0]["autopilot"] });
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Risk caps */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: showSliders ? 14 : 0 }}>
          <div className="panel-title" style={{ margin: 0 }}>Risk Caps</div>
          <button className="btn btn--ghost btn--sm" onClick={() => setShowSliders(!showSliders)}>
            {showSliders ? "Hide" : "Edit"}
          </button>
        </div>
        <AnimatePresence>
          {showSliders && config && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }} style={{ overflow: "hidden" }}>
              {[
                { label: "Max position",      key: "max_position_usd",     min: 100,  max: 10000, step: 100, fmt: usd },
                { label: "Daily loss limit",  key: "daily_loss_limit_usd", min: 50,   max: 2000,  step: 50,  fmt: usd },
              ].map(({ label, key, min, max, step, fmt }) => (
                <div key={key} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: "var(--muted)" }}>{label}</span>
                    <span style={{ fontWeight: 600 }}>{fmt((config as unknown as Record<string, number>)[key])}</span>
                  </div>
                  <input type="range" min={min} max={max} step={step}
                    defaultValue={(config as unknown as Record<string, number>)[key]}
                    style={{ width: "100%", accentColor: "var(--cyan)", cursor: "pointer" }}
                    onMouseUp={(e) => updateLimits({ [key]: Number((e.target as HTMLInputElement).value) })}
                    onTouchEnd={(e) => updateLimits({ [key]: Number((e.target as HTMLInputElement).value) })}
                  />
                </div>
              ))}
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: "var(--muted)" }}>Max drawdown</span>
                  <span style={{ fontWeight: 600 }}>{pct(config.max_drawdown_pct)}</span>
                </div>
                <input type="range" min={1} max={50} step={1}
                  defaultValue={Math.round(config.max_drawdown_pct * 100)}
                  style={{ width: "100%", accentColor: "var(--red)", cursor: "pointer" }}
                  onMouseUp={(e) => updateLimits({ max_drawdown_pct: Number((e.target as HTMLInputElement).value) / 100 })}
                  onTouchEnd={(e) => updateLimits({ max_drawdown_pct: Number((e.target as HTMLInputElement).value) / 100 })}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        {!showSliders && config && (
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Max position: <strong style={{ color: "var(--text)" }}>{usd(config.max_position_usd)}</strong></div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Daily loss limit: <strong style={{ color: "var(--text)" }}>{usd(config.daily_loss_limit_usd)}</strong></div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Max drawdown: <strong style={{ color: "var(--text)" }}>{pct(config.max_drawdown_pct)}</strong></div>
          </div>
        )}
      </div>
    </div>
  );
}
