import { AnimatePresence } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { PositionCard } from "../components/PositionCard";

export function PositionsView() {
  const positions = useQuery(api.positions.open) ?? [];

  if (positions.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">👽</div>
        <div className="empty-state__title">Watching the market</div>
        <div className="empty-state__sub">
          No open positions — the agent is flat and waiting for a high-conviction setup.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700 }}>
          Positions
        </span>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>{positions.length} open</span>
      </div>
      <div className="positions-grid">
        <AnimatePresence>
          {positions.map((p) => <PositionCard key={p._id} position={p} />)}
        </AnimatePresence>
      </div>
    </div>
  );
}
