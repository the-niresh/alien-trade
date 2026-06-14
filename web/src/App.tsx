import { useRef, useState } from "react";
import { useAction, useMutation, useQuery } from "convex/react";
import { loadToken, setToken, withToken } from "./lib/control";
import ThesisLedger from "./components/ThesisLedger";
import { AnimatePresence, motion } from "framer-motion";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../convex/_generated/api";

// ── Formatters ──────────────────────────────────────────────────────────────
const usd = (n?: number) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const pct = (n?: number) => (n == null ? "—" : `${(n * 100).toFixed(2)}%`);
const ts  = (ms: number)  => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const tsShort = (ms: number) => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

// ── Agent definitions ────────────────────────────────────────────────────────
const AGENTS = [
  { name: "CoPilot",    label: "CP", color: "#34d399", bg: "#0a1f14" },
  { name: "Historian",  label: "HI", color: "#fbbf24", bg: "#1a1500" },
  { name: "Researcher", label: "RE", color: "#a78bfa", bg: "#130f1e" },
  { name: "Reflector",  label: "RF", color: "#f87171", bg: "#1e0a0a" },
];
// Positions around CORE (110,110) at radius=88
const ORBIT_R = 88;
const agentPos = (i: number) => {
  const a = ((i * 90) - 90) * (Math.PI / 180);
  return { x: 110 + ORBIT_R * Math.cos(a) - 18, y: 110 + ORBIT_R * Math.sin(a) - 18 };
};

const KIND_COLOR: Record<string, string> = {
  observation: "tag-observe", analysis: "tag-analysis", verdict: "tag-verdict",
  action: "tag-action", handoff: "tag-handoff", control: "tag-control",
};

// ── Sub-components ───────────────────────────────────────────────────────────

function AgentRoster({
  rosterMap,
  onAgentClick,
}: {
  rosterMap: Map<string, { ts_ms: number; kind: string }>;
  onAgentClick: (name: string) => void;
}) {
  const now = Date.now();
  return (
    <div style={{ position: "relative", width: 220, height: 220, margin: "0 auto" }}>
      {/* Orbit ring */}
      <div style={{
        position: "absolute", inset: 0, borderRadius: "50%",
        border: "1px solid rgba(125,211,252,0.08)",
      }} />
      {/* Connector lines */}
      <svg style={{ position: "absolute", inset: 0 }} width={220} height={220}>
        {AGENTS.map((a, i) => {
          const { x, y } = agentPos(i);
          return (
            <line key={a.name}
              x1={110} y1={110} x2={x + 18} y2={y + 18}
              stroke={a.color} strokeOpacity={0.12} strokeWidth={1} />
          );
        })}
      </svg>
      {/* CORE */}
      <motion.div
        style={{
          position: "absolute", top: "50%", left: "50%",
          width: 52, height: 52, borderRadius: "50%",
          background: "#131a26", border: "2px solid #7dd3fc",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 9, fontWeight: 900, color: "#7dd3fc", letterSpacing: 1,
          zIndex: 10, cursor: "default",
          transform: "translate(-50%, -50%)",
        }}
        animate={{ boxShadow: ["0 0 6px #7dd3fc30", "0 0 18px #7dd3fc60", "0 0 6px #7dd3fc30"] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        title="CORE — the deterministic /core strategy engine"
      >
        CORE
      </motion.div>
      {/* Orbiting agents */}
      {AGENTS.map((agent, i) => {
        const { x, y } = agentPos(i);
        const last = rosterMap.get(agent.name);
        const ageSec = last ? (now - last.ts_ms) / 1000 : Infinity;
        const isActive = ageSec < 60;
        const isRecent = ageSec < 300;
        return (
          <motion.div
            key={agent.name}
            title={`${agent.name}${last ? ` — ${tsShort(last.ts_ms)}` : " — idle"}`}
            style={{
              position: "absolute", left: x, top: y,
              width: 36, height: 36, borderRadius: "50%",
              background: agent.bg, border: `1.5px solid ${agent.color}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 10, fontWeight: 700, color: agent.color,
              cursor: "pointer", userSelect: "none",
            }}
            animate={
              isActive
                ? { boxShadow: [`0 0 6px ${agent.color}40`, `0 0 22px ${agent.color}90`, `0 0 6px ${agent.color}40`] }
                : isRecent
                ? { scale: [1, 1.05, 1] }
                : { scale: [1, 1.02, 1], opacity: [0.7, 0.9, 0.7] }
            }
            transition={{ duration: isActive ? 1.5 : 4, repeat: Infinity, ease: "easeInOut" }}
            onClick={() => onAgentClick(agent.name)}
          >
            {agent.label}
          </motion.div>
        );
      })}
    </div>
  );
}

function CoPilotChat({
  prefill,
  onPrefillUsed,
}: {
  prefill: string;
  onPrefillUsed: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const msgs = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const addMessage = useMutation(api.copilot.addMessage);
  const ask = useAction(api.copilot.ask);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Accept prefill from AgentRoster click
  if (prefill && question !== prefill) {
    setQuestion(prefill);
    onPrefillUsed();
  }

  const send = async () => {
    const q = question.trim();
    if (!q || loading) return;
    setQuestion("");
    setLoading(true);
    try {
      await addMessage({ role: "user", content: q, sources_json: "[]" });
      const res = await ask({ question: q });
      await addMessage({
        role: "assistant",
        content: res.answer,
        sources_json: JSON.stringify(res.sources),
      });
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 240 }}>
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column",
        gap: 8, padding: "4px 0", maxHeight: 280 }}>
        {msgs.length === 0 && (
          <div className="sub" style={{ fontStyle: "italic", padding: "8px 0" }}>
            Ask the co-pilot anything — regime, last trade, risk state…
          </div>
        )}
        <AnimatePresence initial={false}>
          {msgs.map((m) => (
            <motion.div
              key={m._id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                padding: "8px 12px", borderRadius: 10,
                background: m.role === "user" ? "#1a2537" : "#0e1c14",
                border: `1px solid ${m.role === "user" ? "#2a3a54" : "#1a3020"}`,
                fontSize: 13, lineHeight: 1.5,
                alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "90%",
              }}
            >
              <div style={{ fontSize: 10, fontWeight: 700, marginBottom: 3,
                color: m.role === "user" ? "#7dd3fc" : "#34d399" }}>
                {m.role === "user" ? "You" : "CoPilot"}
              </div>
              <div style={{ color: "#c9d1d9" }}>{m.content}</div>
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ padding: "8px 12px", borderRadius: 10, background: "#0e1c14",
              border: "1px solid #1a3020", fontSize: 13, color: "#34d39980",
              alignSelf: "flex-start" }}
          >
            <motion.span
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            >
              thinking…
            </motion.span>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        <input
          className="floor-input"
          style={{ flex: 1, width: "auto" }}
          placeholder="Ask the co-pilot…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={loading}
        />
        <button className="btn btn-set" onClick={send} disabled={loading || !question.trim()}>
          {loading ? "…" : "Ask"}
        </button>
      </div>
    </div>
  );
}

function EquityChart() {
  const raw = useQuery(api.ledger.history, { limit: 100 }) ?? [];
  const data = [...raw].reverse().map((r) => ({
    t: r.timestamp_ms,
    pnl: Number(r.cumulative_pnl_usd.toFixed(2)),
    dd: Number((r.current_drawdown_pct * 100).toFixed(2)),
  }));

  if (data.length === 0) {
    return (
      <div className="sub" style={{ textAlign: "center", padding: "32px 0" }}>
        No trade history yet — start the agent to see the equity curve.
      </div>
    );
  }

  const fmtTime = (ms: number) =>
    new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <ResponsiveContainer width="100%" height={180}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2737" vertical={false} />
        <XAxis dataKey="t" tickFormatter={fmtTime} tick={{ fontSize: 10, fill: "#4a5a6a" }}
          tickLine={false} axisLine={false} />
        <YAxis yAxisId="pnl" tick={{ fontSize: 10, fill: "#4a5a6a" }}
          tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} width={44} />
        <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 10, fill: "#4a5a6a" }}
          tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} width={36}
          domain={[0, "auto"]} reversed />
        <Tooltip
          contentStyle={{ background: "#131a26", border: "1px solid #1e2937", borderRadius: 8, fontSize: 12 }}
          labelFormatter={(label) => fmtTime(Number(label))}
          formatter={(val, name) => {
            const n = Number(val);
            return name === "Equity" ? [`$${n.toFixed(2)}`, name] : [`${n.toFixed(2)}%`, name];
          }}
        />
        <Area yAxisId="dd" type="monotone" dataKey="dd" name="Drawdown"
          stroke="#f87171" fill="#f8717118" strokeWidth={1} />
        <Line yAxisId="pnl" type="monotone" dataKey="pnl" name="Equity"
          stroke="#34d399" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// ── Pairing gate ─────────────────────────────────────────────────────────────
// Shown until a control token is present. Normally the onboarding QR deep-links
// here with `#t=<token>` (auto-captured by loadToken); this is the manual fallback.
function PairingScreen({ onPaired }: { onPaired: (t: string) => void }) {
  const [val, setVal] = useState("");
  const submit = () => { const t = val.trim(); if (t) onPaired(t); };
  return (
    <div className="wrap" style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <div style={{ maxWidth: 420, textAlign: "center", padding: 24 }}>
        <h1 style={{ marginBottom: 8 }}>Alien-Trade</h1>
        <p style={{ opacity: 0.7, marginBottom: 20 }}>
          Pair this cockpit to control the agent. Scan the QR from onboarding, or paste
          your control token below.
        </p>
        <input
          type="password"
          value={val}
          placeholder="control token"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          style={{ width: "100%", padding: "10px 12px", marginBottom: 12,
                   background: "#111", color: "#eee", border: "1px solid #333", borderRadius: 8 }}
        />
        <button className="btn" onClick={submit} disabled={!val.trim()}
                style={{ width: "100%" }}>Pair cockpit</button>
      </div>
    </div>
  );
}

// ── Main cockpit ─────────────────────────────────────────────────────────────

export default function App() {
  const ledger    = useQuery(api.ledger.latest);
  const risk      = useQuery(api.riskState.get);
  const config    = useQuery(api.config.get);
  const decisions = useQuery(api.decisions.recent, { limit: 6 });
  const auditLog  = useQuery(api.audit.recent, { limit: 40 });
  const events    = useQuery(api.agentEvents.recent, { limit: 30 });
  const roster    = useQuery(api.agentEvents.latestPerAgent);
  const control   = useQuery(api.agentControl.get);
  const wins      = useQuery(api.reflections.wins, { limit: 5 });

  // Guarded control mutations — wrapped so the shared control token is attached at
  // the definition site. No call site can forget it; new ones are covered for free.
  const _setHalted      = useMutation(api.config.setHalted);
  const _setTradingMode = useMutation(api.config.setTradingMode);
  const _updateLimits   = useMutation(api.config.updateLimits);
  const _setControl     = useMutation(api.agentControl.set);
  const _setStrategy    = useMutation(api.config.setStrategy);
  const _setAutopilot   = useMutation(api.config.setAutopilot);
  const setHalted      = (a: Parameters<typeof _setHalted>[0]) => _setHalted(withToken(a));
  const setTradingMode = (a: Parameters<typeof _setTradingMode>[0]) => _setTradingMode(withToken(a));
  const updateLimits   = (a: Parameters<typeof _updateLimits>[0]) => _updateLimits(withToken(a));
  const setControl     = (a: Parameters<typeof _setControl>[0]) => _setControl(withToken(a));
  const setStrategy    = (a: Parameters<typeof _setStrategy>[0]) => _setStrategy(withToken(a));
  const setAutopilot   = (a: Parameters<typeof _setAutopilot>[0]) => _setAutopilot(withToken(a));
  const recordFeedback = useMutation(api.feedback.record); // not a control mutation — ungated

  const [floorInput, setFloorInput]       = useState("");
  const [copilotPrefill, setCopilotPrefill] = useState("");
  const [showSliders, setShowSliders]     = useState(false);
  // Pairing: the control token arrives via the onboarding QR deep-link (#t=…) or is
  // pasted on the gate below. Read-only queries render regardless; controls need it.
  const [token, setTokenState] = useState<string | null>(loadToken());

  const mode   = config?.trading_mode;
  const halted = config?.halted ?? false;
  const floor  = config?.equity_floor ?? 0;
  const paused = control?.agents_paused ?? false;
  const pnl    = ledger?.cumulative_pnl_usd;
  const dd     = risk?.current_drawdown_pct;

  // Roster map: agent name → latest event info
  const rosterMap = new Map<string, { ts_ms: number; kind: string }>(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string }) => [
      e.agent, { ts_ms: e.ts_ms, kind: e.kind },
    ]),
  );

  const floorHalt = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      (e.headline as string).includes("floor hit"),
  );
  const floorWarn = !floorHalt && (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      (e.headline as string).includes("approaching floor"),
  );

  const onModeClick = (next: "testnet" | "paper" | "mainnet") => {
    if (next === mode) return;
    if (next === "mainnet" &&
        !window.confirm("Switch to LIVE mainnet? This trades real funds via self-custody signing."))
      return;
    setTradingMode({ trading_mode: next });
  };
  const onKillSwitch = () => {
    if (!halted && !window.confirm("Halt the agent? Trading stops within one cycle.")) return;
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };
  const onPauseAgents = () => {
    if (!paused && !window.confirm("Pause advisory agents? Trading continues unaffected.")) return;
    setControl({ agents_paused: !paused, updated_by: "user" });
  };
  const onSetFloor = () => {
    const val = parseFloat(floorInput);
    if (isNaN(val) || val < 0) return;
    updateLimits({ equity_floor: val });
    setFloorInput("");
  };

  if (!token) {
    return <PairingScreen onPaired={(t) => { setToken(t); setTokenState(t); }} />;
  }

  return (
    <div className="wrap">
      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <div className="title">ALIEN-TRADE</div>
        <motion.span
          className={`badge ${halted ? "badge-on" : "badge-off"}`}
          animate={halted
            ? { opacity: [1, 0.5, 1] }
            : { opacity: 1 }}
          transition={{ duration: 1, repeat: halted ? Infinity : 0 }}
        >
          {halted ? "HALTED" : "RUNNING"}
        </motion.span>
        {mode && (
          <span className={`badge ${mode === "mainnet" ? "badge-on" : mode === "paper" ? "badge-warn" : ""}`}
            style={{ fontSize: 11 }}>
            {mode === "mainnet" ? "LIVE" : mode}
          </span>
        )}
        <div className="sub" style={{ marginLeft: "auto" }}>
          Autonomous BSC agent · Convex live state
        </div>
      </div>

      {/* ── Alerts ── */}
      <AnimatePresence>
        {floorHalt && (
          <motion.div className="alert alert-halt"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}>
            Trading HALTED — equity floor hit. Fund wallet or raise floor, then Resume.
          </motion.div>
        )}
        {floorWarn && (
          <motion.div className="alert alert-warn"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}>
            Portfolio approaching equity floor (${floor.toFixed(0)}). Consider adding capital.
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main 3-panel grid ── */}
      <div className="cockpit-grid">

        {/* ── LEFT: Agent Roster + Co-pilot ── */}
        <div className="cockpit-left">
          <div className="panel" style={{ marginBottom: 12 }}>
            <div className="panel-title" style={{ marginBottom: 10 }}>Agent team</div>
            <AgentRoster
              rosterMap={rosterMap}
              onAgentClick={(name) =>
                setCopilotPrefill(`What is ${name} currently doing?`)
              }
            />
            <div className="sub" style={{ textAlign: "center", marginTop: 8 }}>
              Click an agent to ask the co-pilot about them
            </div>
          </div>
          <ThesisLedger />
          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-title" style={{ marginBottom: 8 }}>Co-pilot</div>
            <CoPilotChat
              prefill={copilotPrefill}
              onPrefillUsed={() => setCopilotPrefill("")}
            />
          </div>
        </div>

        {/* ── CENTER: Stats + Chart + Decisions + Wins ── */}
        <div className="cockpit-center">
          {/* Stats row */}
          <div className="grid" style={{ marginBottom: 12 }}>
            <div className="card">
              <div className="label">Cumulative PnL</div>
              <motion.div
                className={`value ${(pnl ?? 0) >= 0 ? "pos" : "neg"}`}
                key={pnl}
                initial={{ scale: 1.1 }}
                animate={{ scale: 1 }}
              >
                {usd(pnl)}
              </motion.div>
            </div>
            <div className="card">
              <div className="label">Max Drawdown</div>
              <div className={`value ${(dd ?? 0) > 0.05 ? "neg" : (dd ?? 0) > 0 ? "" : "pos"}`}>
                {pct(dd)}
              </div>
            </div>
            <div className="card">
              <div className="label">Open exposure</div>
              <div className="value">{usd(risk?.open_exposure_usd)}</div>
            </div>
            <div className="card">
              <div className="label">Circuit breaker</div>
              <div className={`value ${risk?.circuit_breaker_active ? "neg" : "pos"}`}
                style={{ fontSize: 16 }}>
                {risk?.circuit_breaker_active ? "TRIPPED" : "OK"}
              </div>
            </div>
          </div>

          {/* Equity/Drawdown chart */}
          <div className="panel" style={{ marginBottom: 12 }}>
            <div className="panel-title" style={{ marginBottom: 8 }}>Equity &amp; Drawdown</div>
            <div className="sub" style={{ marginBottom: 10 }}>
              Green = cumulative PnL · Red area = drawdown (right axis, inverted)
            </div>
            <EquityChart />
          </div>

          {/* Recent decisions */}
          <div className="card" style={{ marginBottom: 12 }}>
            <div className="label" style={{ marginBottom: 8 }}>Recent decisions</div>
            <table>
              <thead>
                <tr><th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th><th>Rate</th></tr>
              </thead>
              <tbody>
                {(decisions ?? []).map((d) => (
                  <tr key={d._id}>
                    <td>{ts(d.timestamp_ms)}</td>
                    <td>{d.symbol}</td>
                    <td style={{ color: "#7dd3fc" }}>{d.regime}</td>
                    <td>
                      <span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span>
                    </td>
                    <td>{usd(d.final_size_usd)}</td>
                    <td>
                      {d.setup_key ? (
                        <span style={{ display: "inline-flex", gap: 4 }}>
                          <button className="btn-rate" title={`Good setup (${d.setup_key})`}
                            onClick={() => recordFeedback({
                              cycle_id: d.cycle_id, setup_key: d.setup_key!,
                              symbol: d.symbol, label: "good" })}>👍</button>
                          <button className="btn-rate" title={`Bad setup (${d.setup_key}) — agent will avoid it`}
                            onClick={() => recordFeedback({
                              cycle_id: d.cycle_id, setup_key: d.setup_key!,
                              symbol: d.symbol, label: "bad" })}>👎</button>
                        </span>
                      ) : <span className="sub">—</span>}
                    </td>
                  </tr>
                ))}
                {decisions?.length === 0 && (
                  <tr><td colSpan={6} className="sub">No decisions yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Wins feed */}
          {(wins ?? []).length > 0 && (
            <div className="panel">
              <div className="panel-title" style={{ marginBottom: 8 }}>
                 Winning trades
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(wins ?? []).map((w) => (
                  <motion.div
                    key={w._id}
                    className="win-card"
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between",
                      alignItems: "center", marginBottom: 4 }}>
                      <span className="tag tag-allow">WIN</span>
                      <span style={{ color: "#34d399", fontWeight: 700 }}>
                        +{usd(w.outcome_pnl_usd)}
                      </span>
                    </div>
                    <div className="sub" style={{ marginBottom: 2 }}>
                      {w.regime} · {ts(w.timestamp_ms)}
                    </div>
                    {w.lesson && (
                      <div style={{ fontSize: 12, color: "#8b98a5", fontStyle: "italic" }}>
                        "{w.lesson}"
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT: Controls + Sliders + Signal health + Floor ── */}
        <div className="cockpit-right">
          {/* Kill switch + pause + stop */}
          <div className="panel" style={{ marginBottom: 12 }}>
            <div className="panel-title" style={{ marginBottom: 10 }}>Controls</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <button
                  className={`btn ${halted ? "btn-resume" : "btn-halt"}`}
                  style={{ width: "100%" }}
                  onClick={onKillSwitch}
                >
                  {halted ? "Resume Trading" : "Kill Switch"}
                </button>
                <div className="sub" style={{ marginTop: 3 }}>
                  Halts within one cycle · self-custody remains secure
                </div>
              </div>
              <button
                className="btn btn-pause"
                style={{ width: "100%" }}
                onClick={onPauseAgents}
              >
                {paused ? "Resume Agents" : "Pause Advisory Agents"}
              </button>
              <button className="btn btn-stop" style={{ width: "100%" }} onClick={() => {
                if (!window.confirm("Cancel the current in-flight agent action?")) return;
                setControl({ stop_response_id: String(Date.now()), updated_by: "user" });
              }}>
                Stop Response
              </button>
            </div>
          </div>

          {/* Trading mode */}
          <div className="panel" style={{ marginBottom: 12 }}>
            <div className="panel-title" style={{ marginBottom: 8 }}>Trading mode</div>
            <div className="seg" role="group" style={{ width: "100%", justifyContent: "stretch" }}>
              {(["testnet", "paper", "mainnet"] as const).map((m) => (
                <button
                  key={m}
                  className={`seg-btn ${mode === m ? `seg-on seg-${m}` : ""}`}
                  style={{ flex: 1 }}
                  aria-pressed={mode === m}
                  onClick={() => onModeClick(m)}
                  disabled={config === undefined}
                >
                  {m === "mainnet" ? "LIVE" : m}
                </button>
              ))}
            </div>
          </div>

          {/* Signal health */}
          <div className="panel" style={{ marginBottom: 12 }}>
            <div className="panel-title" style={{ marginBottom: 8 }}>Signal health</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {(["forecast", "sentiment"] as const).map((src) => {
                const related = (events ?? []).filter(
                  (e) => e.agent === "RiskGuard" && e.kind === "observation" &&
                         typeof e.headline === "string" && e.headline.toLowerCase().includes(src),
                );
                const stale = related.length > 0 && related[0].headline.startsWith("STALE");
                return (
                  <div key={src} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <motion.div
                      style={{ width: 10, height: 10, borderRadius: "50%",
                        background: stale ? "#f59e0b" : "#22c55e", flexShrink: 0 }}
                      animate={stale
                        ? { opacity: [1, 0.4, 1] }
                        : { boxShadow: ["0 0 4px #22c55e60", "0 0 10px #22c55ea0", "0 0 4px #22c55e60"] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                    <span className="sub">{src === "forecast" ? "Forecast (4h)" : "Sentiment (2h)"}</span>
                    {stale && <span className="tag tag-control" style={{ fontSize: 10 }}>stale</span>}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Equity floor */}
          <div className="panel" style={{ marginBottom: 12 }}>
            <div className="panel-title">Equity floor</div>
            <div className="sub" style={{ marginBottom: 8 }}>
              {floor > 0 ? <strong>Floor: {usd(floor)}</strong> : "Disabled"}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <input className="floor-input" style={{ flex: 1, minWidth: 80 }}
                type="number" min="0" placeholder="e.g. 50"
                value={floorInput} onChange={(e) => setFloorInput(e.target.value)} />
              <button className="btn btn-set" onClick={onSetFloor} disabled={floorInput === ""}>
                Set
              </button>
              {floor > 0 && (
                <button className="btn btn-stop" onClick={() => updateLimits({ equity_floor: 0 })}>
                  Off
                </button>
              )}
            </div>
          </div>

          {/* Strategy + Autopilot */}
          <StrategyAutopilotPanel
            config={config}
            setStrategy={setStrategy}
            setAutopilot={setAutopilot}
          />

          {/* Risk cap sliders */}
          <div className="panel">
            <div style={{ display: "flex", justifyContent: "space-between",
              alignItems: "center", marginBottom: showSliders ? 12 : 0 }}>
              <div className="panel-title">Risk caps</div>
              <button className="btn btn-stop" style={{ padding: "4px 10px", fontSize: 11 }}
                onClick={() => setShowSliders(!showSliders)}>
                {showSliders ? "Hide" : "Edit"}
              </button>
            </div>
            <AnimatePresence>
              {showSliders && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  style={{ overflow: "hidden" }}
                >
                  <RiskSliders config={config} updateLimits={updateLimits} />
                </motion.div>
              )}
            </AnimatePresence>
            {!showSliders && config && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div className="sub">
                  Max position: <strong style={{ color: "#e6edf3" }}>{usd(config.max_position_usd)}</strong>
                </div>
                <div className="sub">
                  Daily loss limit: <strong style={{ color: "#e6edf3" }}>{usd(config.daily_loss_limit_usd)}</strong>
                </div>
                <div className="sub">
                  Max drawdown: <strong style={{ color: "#e6edf3" }}>{pct(config.max_drawdown_pct)}</strong>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Agent activity channel ── */}
      <div className="card" style={{ marginTop: 12 }}>
        <div className="label" style={{ marginBottom: 8 }}>Agent activity channel</div>
        {(events ?? []).length === 0 ? (
          <div className="sub">No activity yet — start the agent to see the team's live reasoning.</div>
        ) : (
          <div className="channel">
            {(events ?? []).map((e) => (
              <div key={e._id} className="evt">
                <div className="evt-meta">
                  <span className="evt-agent" style={{
                    color: AGENTS.find((a) => a.name === e.agent)?.color ?? "#7dd3fc",
                  }}>
                    {e.agent}
                  </span>
                  <span className={`tag ${KIND_COLOR[e.kind] ?? "tag-observe"}`}>{e.kind}</span>
                  <span className="evt-time">{ts(e.ts_ms)}</span>
                  {e.cycle_id && (
                    <span className="evt-cycle">{String(e.cycle_id).slice(-8)}</span>
                  )}
                </div>
                <div className="evt-headline">{e.headline}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Live log console (spectate the agent) ── */}
      <div className="card" style={{ marginTop: 12 }}>
        <div className="label" style={{ marginBottom: 8 }}>Live log console</div>
        {(auditLog ?? []).length === 0 ? (
          <div className="sub">No log entries yet — the agent writes one row per event.</div>
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

// ── Strategy picker + Autopilot capital manager ───────────────────────────────

const STRATEGIES = [
  { name: "momentum",   label: "Momentum",   blurb: "Rides confirmed uptrends." },
  { name: "contrarian", label: "Contrarian", blurb: "Buys fear, trims greed. Best in down/choppy markets." },
  { name: "balanced",   label: "Balanced",   blurb: "Momentum + derivatives + fear." },
  { name: "defensive",  label: "Defensive",  blurb: "Rare high-conviction longs. Minimises drawdown." },
];

type AutopilotCfg = {
  enabled: boolean;
  profit_target_pct?: number;
  profit_target_abs?: number;
  protect_principal?: boolean;
  trailing_giveback_pct?: number;
  daily_profit_target_pct?: number;
  min_recycle_confidence?: number;
  recycle_blocked_regimes?: string[];
  loss_cooldown_hours?: number;
};

function StrategyAutopilotPanel({
  config,
  setStrategy,
  setAutopilot,
}: {
  config: { strategy_name?: string; autopilot?: AutopilotCfg } | null | undefined;
  setStrategy: (args: { strategy_name: string }) => void;
  setAutopilot: (args: { autopilot: AutopilotCfg }) => void;
}) {
  const ap = config?.autopilot;
  const active = config?.strategy_name ?? "balanced";
  // Local draft for the numeric target fields (commit on blur).
  const [pct, setPct]   = useState("");
  const [abs, setAbs]   = useState("");
  const [trail, setTrail] = useState("");
  const [daily, setDaily] = useState("");

  const num = (s: string) => (s.trim() === "" ? undefined : Number(s));
  const patch = (over: Partial<AutopilotCfg>) =>
    setAutopilot({
      autopilot: {
        enabled: ap?.enabled ?? false,
        profit_target_pct: ap?.profit_target_pct,
        profit_target_abs: ap?.profit_target_abs,
        protect_principal: ap?.protect_principal ?? true,
        trailing_giveback_pct: ap?.trailing_giveback_pct,
        daily_profit_target_pct: ap?.daily_profit_target_pct,
        min_recycle_confidence: ap?.min_recycle_confidence,
        recycle_blocked_regimes: ap?.recycle_blocked_regimes ?? ["crash", "high_vol"],
        loss_cooldown_hours: ap?.loss_cooldown_hours,
        ...over,
      },
    });

  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <div className="panel-title" style={{ marginBottom: 8 }}>Strategy</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 6 }}>
        {STRATEGIES.map((s) => (
          <button key={s.name}
            className={`btn ${active === s.name ? "btn-set" : "btn-stop"}`}
            style={{ padding: "6px 8px", fontSize: 12 }}
            title={s.blurb}
            onClick={() => setStrategy({ strategy_name: s.name })}>
            {s.label}
          </button>
        ))}
      </div>
      <div className="sub" style={{ marginBottom: 12 }}>
        {STRATEGIES.find((s) => s.name === active)?.blurb}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div className="panel-title">Autopilot</div>
        <button
          className={`btn ${ap?.enabled ? "btn-set" : "btn-stop"}`}
          style={{ padding: "4px 12px", fontSize: 11 }}
          onClick={() => patch({ enabled: !(ap?.enabled ?? false) })}>
          {ap?.enabled ? "ON" : "OFF"}
        </button>
      </div>

      {ap?.enabled && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <APRow label="Take profit %" placeholder={pctStr(ap?.profit_target_pct)}
            value={pct} onChange={setPct}
            onCommit={() => patch({ profit_target_pct: num(pct) === undefined ? undefined : Number(pct) / 100 })} />
          <APRow label="Take profit $" placeholder={ap?.profit_target_abs?.toString() ?? "—"}
            value={abs} onChange={setAbs}
            onCommit={() => patch({ profit_target_abs: num(abs) })} />
          <APRow label="Trailing give-back %" placeholder={pctStr(ap?.trailing_giveback_pct)}
            value={trail} onChange={setTrail}
            onCommit={() => patch({ trailing_giveback_pct: num(trail) === undefined ? undefined : Number(trail) / 100 })} />
          <APRow label="Daily target %" placeholder={pctStr(ap?.daily_profit_target_pct)}
            value={daily} onChange={setDaily}
            onCommit={() => patch({ daily_profit_target_pct: num(daily) === undefined ? undefined : Number(daily) / 100 })} />
          <label className="sub" style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
            <input type="checkbox" checked={ap?.protect_principal ?? true}
              onChange={(e) => patch({ protect_principal: e.target.checked })} />
            Protect principal (ratchet the whole balance, not just profit)
          </label>
        </div>
      )}
    </div>
  );
}

function pctStr(v?: number) {
  return v === undefined ? "—" : `${(v * 100).toFixed(1)}`;
}

function APRow({
  label, value, placeholder, onChange, onCommit,
}: {
  label: string; value: string; placeholder: string;
  onChange: (v: string) => void; onCommit: () => void;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
      <span className="sub">{label}</span>
      <input className="floor-input" style={{ width: 70 }} type="number" min="0"
        placeholder={placeholder} value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onCommit} />
    </div>
  );
}

// ── Risk sliders ──────────────────────────────────────────────────────────────

function RiskSliders({
  config,
  updateLimits,
}: {
  config: { max_position_usd: number; daily_loss_limit_usd: number; max_drawdown_pct: number } | null | undefined;
  updateLimits: (args: Record<string, unknown>) => void;
}) {
  const [pos,  setPos]  = useState<number | null>(null);
  const [loss, setLoss] = useState<number | null>(null);
  const [dd,   setDd]   = useState<number | null>(null);

  if (!config) return <div className="sub">Loading caps…</div>;

  const posVal  = pos  ?? config.max_position_usd;
  const lossVal = loss ?? config.daily_loss_limit_usd;
  const ddVal   = dd   ?? Math.round(config.max_drawdown_pct * 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <SliderRow label="Max position" value={posVal} min={100} max={10000} step={100}
        fmt={usd} onChange={setPos}
        onCommit={(v) => updateLimits({ max_position_usd: v })} />
      <SliderRow label="Daily loss limit" value={lossVal} min={50} max={2000} step={50}
        fmt={usd} onChange={setLoss}
        onCommit={(v) => updateLimits({ daily_loss_limit_usd: v })} />
      <SliderRow label="Max drawdown" value={ddVal} min={1} max={50} step={1}
        fmt={(v) => `${v}%`} onChange={setDd}
        onCommit={(v) => updateLimits({ max_drawdown_pct: v / 100 })} />
    </div>
  );
}

function SliderRow({
  label, value, min, max, step, fmt, onChange, onCommit,
}: {
  label: string; value: number; min: number; max: number; step: number;
  fmt: (v: number) => string;
  onChange: (v: number) => void;
  onCommit: (v: number) => void;
}) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between",
        marginBottom: 4, fontSize: 12 }}>
        <span className="sub">{label}</span>
        <span style={{ color: "#e6edf3", fontWeight: 600 }}>{fmt(value)}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        style={{ width: "100%", accentColor: "#7dd3fc", cursor: "pointer" }}
        onChange={(e) => onChange(Number(e.target.value))}
        onMouseUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
        onTouchEnd={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
      />
    </div>
  );
}
