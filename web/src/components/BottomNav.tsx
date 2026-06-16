import { LayoutDashboard, List, Users, Settings, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { View } from "./SideNav";

const TABS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "positions", icon: List,            label: "Positions" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
  { view: "logs",      icon: FileText,        label: "Logs" },
];

type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
};

export function BottomNav({ active, onSelect }: Props) {
  return (
    <nav className="chrome h-12 border-t border-border flex items-stretch w-full flex-shrink-0 z-10">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = active === tab.view;
        return (
          <button
            key={tab.view}
            onClick={() => onSelect(tab.view)}
            className={cn(
              "relative flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors cursor-pointer",
              isActive ? "text-green" : "text-muted-fg"
            )}
            aria-label={tab.label}
            aria-current={isActive ? "page" : undefined}
          >
            {isActive && (
              <span className="absolute top-0 h-[2px] w-8 rounded-full bg-green" style={{ boxShadow: "0 0 8px var(--green)" }} />
            )}
            <Icon className="w-[18px] h-[18px]" />
            <span className={cn("font-mono text-[9px] font-bold tracking-wide", isActive ? "text-green" : "text-muted-fg")}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
