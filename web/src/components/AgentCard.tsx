import { motion } from "framer-motion";
import { ts } from "../lib/formatters";

export type AgentDef = {
  name: string;
  label: string;
  color: string;
  bg: string;
  role: string;
};

export const AGENT_DEFS: AgentDef[] = [
  { name: "CoPilot",    label: "CP", color: "var(--cyan)",   bg: "#00d4ff18", role: "Answers your questions about the market, regime and trades." },
  { name: "Historian",  label: "HI", color: "var(--yellow)", bg: "#ffd60a18", role: "Queries the Second Brain for institutional memory before each trade." },
  { name: "Researcher", label: "RE", color: "var(--purple)", bg: "#a855f718", role: "Auto-researches market anomalies and builds the research digest." },
  { name: "Reflector",  label: "RF", color: "var(--red)",    bg: "#ff306018", role: "Writes structured reflections after every trade for Hermes learning." },
];

type LastEvent = { ts_ms: number; kind: string; headline: string };
type Props = { def: AgentDef; lastEvent?: LastEvent; onClick: () => void };

export function AgentCard({ def, lastEvent, onClick }: Props) {
  const now = Date.now();
  const ageSec = lastEvent ? (now - lastEvent.ts_ms) / 1000 : Infinity;
  const isActive = ageSec < 60;
  const isRecent = ageSec < 300;
  const dotColor = isActive ? "var(--green)" : isRecent ? "var(--yellow)" : "var(--border-hi)";

  return (
    <div className="agent-card" onClick={onClick}>
      <div className="agent-card__header">
        <motion.div
          className="agent-card__avatar"
          style={{ color: def.color, background: def.bg, border: `1.5px solid ${def.color}40` }}
          animate={isActive
            ? { boxShadow: [`0 0 8px ${def.color}40`, `0 0 20px ${def.color}80`, `0 0 8px ${def.color}40`] }
            : { scale: [1, 1.03, 1] }}
          transition={{ duration: isActive ? 1.5 : 4, repeat: Infinity, ease: "easeInOut" }}
        >
          {def.label}
        </motion.div>
        <div style={{ flex: 1 }}>
          <div className="agent-card__name" style={{ color: def.color }}>{def.name}</div>
          <div className="agent-card__role">{def.role}</div>
        </div>
        <motion.div
          className="status-dot"
          style={{ background: dotColor }}
          animate={isActive ? { opacity: [1, 0.4, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        />
      </div>
      {lastEvent ? (
        <>
          <div className="agent-card__last">{lastEvent.headline}</div>
          <div className="agent-card__meta">{ts(lastEvent.ts_ms)} · {lastEvent.kind}</div>
        </>
      ) : (
        <div className="agent-card__last" style={{ color: "var(--muted)", fontStyle: "italic" }}>
          No activity yet
        </div>
      )}
    </div>
  );
}
