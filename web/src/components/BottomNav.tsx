import { LayoutDashboard, Activity, Users, Settings, LineChart } from "lucide-react";
import { cn } from "@/lib/utils";
import type { View } from "./SideNav";

const TABS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "trackers",  icon: Activity,        label: "Trackers" },
  { view: "chart",     icon: LineChart,       label: "Chart" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
];

type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
};

export function BottomNav({ active, onSelect }: Props) {
  return (
    <nav
      className="h-14 border-t border-border/60 flex items-stretch w-full flex-shrink-0 z-10"
      style={{
        background: "color-mix(in oklab, var(--surface) 88%, transparent)",
        backdropFilter: "blur(16px) saturate(1.2)",
        WebkitBackdropFilter: "blur(16px) saturate(1.2)",
      }}
    >
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = active === tab.view;
        return (
          <button
            key={tab.view}
            onClick={() => onSelect(tab.view)}
            className={cn(
              "relative flex-1 flex flex-col items-center justify-center gap-[3px] transition-all duration-200 cursor-pointer min-h-[44px]",
              isActive ? "text-green" : "text-muted-fg hover:text-text/70",
            )}
            aria-label={tab.label}
            aria-current={isActive ? "page" : undefined}
          >
            {/* Active indicator — full-width top bar with glow */}
            {isActive && (
              <span
                className="absolute top-0 left-2 right-2 h-[2.5px] rounded-full bg-green"
                style={{ boxShadow: "0 0 10px var(--green), 0 0 20px color-mix(in oklab, var(--green) 40%, transparent)" }}
              />
            )}

            {/* Active background wash */}
            {isActive && (
              <span className="absolute inset-x-1 inset-y-1 rounded-xl bg-green/6" />
            )}

            <Icon className={cn("relative z-10 transition-transform duration-200", isActive ? "w-[19px] h-[19px]" : "w-[18px] h-[18px]", isActive && "drop-shadow-[0_0_6px_var(--green)]")} />
            <span className={cn(
              "relative z-10 font-mono font-bold tracking-[0.08em] transition-all duration-200",
              isActive ? "text-[10px] text-green" : "text-[9px] text-muted-fg",
            )}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
