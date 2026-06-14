import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";

// "Science in public" feed (AWAKE_SPRINT §4.6): every thesis the loop distills/tests,
// with its status, OOS objective, deflated Sharpe, and exact source citation. The
// falsification log is the differentiator — FALSIFIED cards are shown, not hidden.

const STATUS_STYLE: Record<string, { bg: string; fg: string; label: string }> = {
  validated: { bg: "#0f3d2e", fg: "#34d399", label: "VALIDATED" },
  FALSIFIED: { bg: "#3d0f14", fg: "#f87171", label: "FALSIFIED" },
  untested:  { bg: "#23262e", fg: "#9ca3af", label: "untested" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.untested;
  return (
    <span style={{ background: s.bg, color: s.fg, fontSize: 11, fontWeight: 700,
      padding: "2px 8px", borderRadius: 6, letterSpacing: 0.4 }}>{s.label}</span>
  );
}

function fmt(n: number | null | undefined, d = 3): string {
  return n === null || n === undefined ? "—" : n.toFixed(d);
}

export default function ThesisLedger() {
  const theses = useQuery(api.thesisLedger.recent, { limit: 12 });
  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <h2 className="panel-title" style={{ marginBottom: 10 }}>
        Thesis ledger <span style={{ opacity: 0.5, fontWeight: 400 }}>· science in public</span>
      </h2>
      {theses === undefined ? (
        <div style={{ opacity: 0.5, fontSize: 13 }}>loading…</div>
      ) : theses.length === 0 ? (
        <div style={{ opacity: 0.5, fontSize: 13 }}>
          No theses tested yet — the loop logs every trial here.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {theses.map((t: any) => (
            <div key={t.thesis_id ?? t._id} className="card" style={{ padding: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{t.claim}</span>
                <StatusBadge status={t.status} />
              </div>
              <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 12, opacity: 0.8 }}>
                <span>obj <b>{fmt(t.oos_objective)}</b></span>
                <span>DSR <b>{fmt(t.deflated_sharpe, 2)}</b></span>
                {t.regime ? <span>regime <b>{t.regime}</b></span> : null}
              </div>
              {t.source ? (
                <div style={{ fontSize: 11, opacity: 0.55, marginTop: 4 }}>↳ {t.source}</div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
