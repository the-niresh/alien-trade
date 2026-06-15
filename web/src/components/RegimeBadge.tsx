import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Props = { regime?: string | null };

const CFG: Record<string, { colorClass: string; icon: string }> = {
  bull:     { colorClass: "border-green/30 bg-green/10 text-green",    icon: "↑" },
  trend:    { colorClass: "border-green/30 bg-green/10 text-green",    icon: "↑" },
  bear:     { colorClass: "border-red/30 bg-red/10 text-red",          icon: "↓" },
  crash:    { colorClass: "border-red/50 bg-red/20 text-red",          icon: "⚠" },
  chop:     { colorClass: "border-yellow/30 bg-yellow/10 text-yellow", icon: "↔" },
  high_vol: { colorClass: "border-yellow/30 bg-yellow/10 text-yellow", icon: "⚡" },
};
const DEFAULT = { colorClass: "border-border bg-elevated text-muted-fg", icon: "?" };

export function RegimeBadge({ regime }: Props) {
  const key = (regime ?? "").toLowerCase().replace(/ /g, "_");
  const c = CFG[key] ?? DEFAULT;
  return (
    <Badge variant="outline" className={cn("text-[11px] font-bold tracking-wide px-2.5 py-0.5", c.colorClass)}>
      {c.icon} {(regime ?? "UNKNOWN").toUpperCase()}
    </Badge>
  );
}
