import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { toggleTheme, getTheme } from "../lib/theme";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { eventSeverity } from "../lib/eventSeverity";
import { LayoutDashboard, List, Users, Settings, FileText, Bot, Sun, Moon, Bell, Activity, BookOpen, LineChart, GraduationCap, ArrowDownToLine, ArrowUpFromLine, PieChart } from "lucide-react";

export type View = "overview" | "trackers" | "deposit" | "withdraw" | "chart" | "positions" | "agents" | "controls" | "pipeline" | "portfolio" | "logs" | "notifications" | "docs";

const NAV_ITEMS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",      icon: LayoutDashboard, label: "Overview" },
  { view: "trackers",      icon: Activity,        label: "Trackers" },
  { view: "chart",         icon: LineChart,       label: "Chart" },
  { view: "portfolio",     icon: PieChart,        label: "Portfolio" },
  { view: "deposit",       icon: ArrowDownToLine,  label: "Deposit" },
  { view: "withdraw",      icon: ArrowUpFromLine,  label: "Withdraw" },
  { view: "pipeline",      icon: Activity,        label: "Pipeline" },
  { view: "positions",     icon: List,            label: "Positions" },
  { view: "agents",        icon: Users,           label: "Agents" },
  { view: "controls",      icon: Settings,        label: "Controls" },
  { view: "logs",          icon: FileText,        label: "Logs" },
  { view: "notifications", icon: Bell,            label: "Alerts" },
  { view: "docs",          icon: BookOpen,        label: "Docs" },
];

type Props = { active: View; onSelect: (v: View) => void; onCopilot: () => void; onTour: () => void };

export function SideNav({ active, onSelect, onCopilot, onTour }: Props) {
  const [theme, setTheme] = useState(getTheme);
  const events = useQuery(api.agentEvents.recent, { limit: 20 }) ?? [];

  // Count events in the last 30 minutes that are non-info
  const BADGE_WINDOW_MS = 30 * 60 * 1000;
  const now = Date.now();
  const badgeCount = events.filter(
    (e) => now - e.ts_ms < BADGE_WINDOW_MS && eventSeverity(e) !== "info"
  ).length;

  const handleThemeToggle = () => setTheme(toggleTheme());

  return (
    <TooltipProvider delayDuration={300}>
      <nav className="chrome w-[58px] border-r border-border flex flex-col items-center py-3 gap-1.5 flex-shrink-0 z-10">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.view;
          const showBadge = item.view === "notifications" && badgeCount > 0 && !isActive;
          return (
            <Tooltip key={item.view}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => onSelect(item.view)}
                  className={cn(
                    "relative w-10 h-10 rounded-[11px] flex items-center justify-center transition-colors cursor-pointer",
                    isActive
                      ? "text-green"
                      : "text-muted-fg hover:bg-elevated hover:text-text"
                  )}
                  aria-label={item.label}
                  aria-current={isActive ? "page" : undefined}
                  data-tour={`nav-${item.view}`}
                >
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-[11px] bg-green/10 border border-green/25"
                      style={{ boxShadow: "0 0 18px color-mix(in oklab, var(--green) 28%, transparent)" }}
                      transition={{ type: "spring", stiffness: 500, damping: 34 }}
                    />
                  )}
                  {isActive && (
                    <motion.span
                      layoutId="nav-rail"
                      className="absolute -left-3 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-full bg-green"
                      style={{ boxShadow: "0 0 10px var(--green)" }}
                      transition={{ type: "spring", stiffness: 500, damping: 34 }}
                    />
                  )}
                  <Icon className="w-[18px] h-[18px] relative z-10" />
                  {showBadge && (
                    <span className="absolute top-1 right-1 w-[7px] h-[7px] rounded-full bg-red z-20 animate-pulse"
                      style={{ boxShadow: "0 0 6px var(--red)" }} />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                {item.label}{showBadge ? ` (${badgeCount} recent)` : ""}
              </TooltipContent>
            </Tooltip>
          );
        })}

        <div className="flex-1" />

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={onTour}
              data-tour="nav-tour"
              className="w-10 h-10 rounded-[11px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors cursor-pointer"
              aria-label="Start tour"
            >
              <GraduationCap className="w-[18px] h-[18px]" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">Start tour</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={onCopilot}
              data-tour="nav-copilot"
              className="w-10 h-10 rounded-[11px] flex items-center justify-center text-purple hover:bg-purple/10 transition-colors cursor-pointer"
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
              className="w-10 h-10 rounded-[11px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors cursor-pointer"
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
