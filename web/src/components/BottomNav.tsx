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
    <nav className="h-11 bg-surface border-t border-border flex items-stretch w-full flex-shrink-0">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = active === tab.view;
        return (
          <button
            key={tab.view}
            onClick={() => onSelect(tab.view)}
            className={cn(
              "flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors",
              isActive ? "text-cyan" : "text-muted-fg"
            )}
            aria-label={tab.label}
          >
            <Icon className="w-[18px] h-[18px]" />
            <span className={cn("text-[9px] font-bold", isActive ? "text-cyan" : "text-muted-fg")}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
