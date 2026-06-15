type Props = { regime?: string | null };

const CFG: Record<string, { color: string; bg: string; border: string; icon: string }> = {
  bull:     { color: "#00ff9d", bg: "#00ff9d18", border: "#00ff9d30", icon: "↑" },
  trend:    { color: "#00ff9d", bg: "#00ff9d18", border: "#00ff9d30", icon: "↑" },
  bear:     { color: "#ff3060", bg: "#ff306018", border: "#ff306030", icon: "↓" },
  crash:    { color: "#ff3060", bg: "#ff306030", border: "#ff306050", icon: "⚠" },
  chop:     { color: "#ffd60a", bg: "#ffd60a18", border: "#ffd60a30", icon: "↔" },
  high_vol: { color: "#ffd60a", bg: "#ffd60a18", border: "#ffd60a30", icon: "⚡" },
};
const DEFAULT = { color: "#6080a0", bg: "#6080a018", border: "#6080a030", icon: "?" };

export function RegimeBadge({ regime }: Props) {
  const key = (regime ?? "").toLowerCase().replace(/ /g, "_");
  const c = CFG[key] ?? DEFAULT;
  return (
    <span
      className="regime-badge"
      style={{ color: c.color, background: c.bg, border: `1px solid ${c.border}` }}
    >
      {c.icon} {(regime ?? "UNKNOWN").toUpperCase()}
    </span>
  );
}
