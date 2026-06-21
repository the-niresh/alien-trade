import { cn } from "@/lib/utils";

type Props = { regime?: string | null };

const CFG: Record<string, { cls: string; icon: string }> = {
  bull:     { cls: "border-green/30 bg-green/10 text-green",    icon: "▲" },
  trend:    { cls: "border-green/30 bg-green/10 text-green",    icon: "▲" },
  bear:     { cls: "border-red/30 bg-red/10 text-red",          icon: "▼" },
  crash:    { cls: "border-red/50 bg-red/20 text-red",          icon: "⚠" },
  chop:     { cls: "border-yellow/30 bg-yellow/10 text-yellow", icon: "↔" },
  high_vol: { cls: "border-yellow/30 bg-yellow/10 text-yellow", icon: "⚡" },
};
const DEFAULT = { cls: "border-border bg-elevated text-muted-fg", icon: "?" };

export function RegimeBadge({ regime }: Props) {
  const key = (regime ?? "").toLowerCase().replace(/ /g, "_");
  const c = CFG[key] ?? DEFAULT;
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 font-mono text-[10px] font-bold tracking-[0.16em] uppercase",
      c.cls,
    )}>
      <span className="text-[11px] leading-none">{c.icon}</span>
      {(regime ?? "UNKNOWN").toUpperCase()}
    </span>
  );
}
