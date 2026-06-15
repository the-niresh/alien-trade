import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "./KillSwitch";
import { RegimeBadge } from "./RegimeBadge";
import { usd } from "../lib/formatters";

type Props = { halted: boolean; mode?: string; onKillToggle: () => void };

export function LiveHeader({ halted, mode, onKillToggle }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const decisions = useQuery(api.decisions.recent, { limit: 1 });

  const pnl    = ledger?.cumulative_pnl_usd;
  const regime = decisions?.[0]?.regime ?? null;
  const pnlPos = (pnl ?? 0) >= 0;

  return (
    <header className="live-header">
      <span className="header-logo">ALIEN-TRADE</span>
      <div className="header-sep" />

      {regime && <RegimeBadge regime={regime} />}

      {mode && (
        <span className={`mode-badge mode-badge--${mode}`}>
          {mode === "mainnet" ? "LIVE" : mode.toUpperCase()}
        </span>
      )}

      {pnl != null && (
        <>
          <div className="header-sep" />
          <span className="header-equity" style={{ color: pnlPos ? "var(--green)" : "var(--red)" }}>
            {usd(pnl)}
          </span>
        </>
      )}

      <div className="header-spacer" />

      {halted && (
        <span style={{
          fontSize: 12, fontWeight: 700, color: "var(--red)",
          background: "#ff306018", padding: "3px 10px", borderRadius: 6,
        }}>
          HALTED
        </span>
      )}

      <KillSwitch halted={halted} onToggle={onKillToggle} />
    </header>
  );
}
