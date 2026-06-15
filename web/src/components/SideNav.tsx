import { useState } from "react";
import { toggleTheme, getTheme } from "../lib/theme";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { LayoutDashboard, List, Users, Settings, FileText, Bot, Sun, Moon } from "lucide-react";

export type View = "overview" | "positions" | "agents" | "controls" | "logs";

const NAV_ITEMS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "positions", icon: List,            label: "Positions" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
  { view: "logs",      icon: FileText,        label: "Logs" },
];

type Props = { active: View; onSelect: (v: View) => void; onCopilot: () => void };

export function SideNav({ active, onSelect, onCopilot }: Props) {
  const [theme, setTheme] = useState(getTheme);

  const handleThemeToggle = () => {
    const next = toggleTheme();
    setTheme(next);
  };

  return (
    <TooltipProvider delayDuration={300}>
      <nav className="w-[52px] bg-surface border-r border-border flex flex-col items-center py-3 gap-1 flex-shrink-0">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <Tooltip key={item.view}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => onSelect(item.view)}
                  className={cn(
                    "w-10 h-10 rounded-[10px] flex items-center justify-center transition-colors",
                    active === item.view
                      ? "bg-elevated text-cyan"
                      : "text-muted-fg hover:bg-elevated hover:text-text"
                  )}
                  aria-label={item.label}
                >
                  <Icon className="w-[18px] h-[18px]" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          );
        })}

        <div className="flex-1" />

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={onCopilot}
              className="w-10 h-10 rounded-[10px] flex items-center justify-center text-purple hover:bg-elevated transition-colors"
              aria-label="Co-Pilot"
            >
              <Bot className="w-[18px] h-[18px]" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">Co-Pilot</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={handleThemeToggle}
              className="w-10 h-10 rounded-[10px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors"
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </TooltipContent>
        </Tooltip>
      </nav>
    </TooltipProvider>
  );
}
