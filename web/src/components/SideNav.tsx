import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { toggleTheme, getTheme } from "../lib/theme";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { eventSeverity } from "../lib/eventSeverity";
import { Bot, Sun, Moon, GraduationCap } from "lucide-react";
import { NAV_ITEMS } from "../lib/nav";
import type { View } from "../lib/nav";

// Re-exported so the many `import type { View } from ".../SideNav"` sites keep working.
// The definition itself lives in lib/nav.ts alongside the icons and labels.
export type { View };

type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
  onTour: () => void;
  onAgentOpen?: (threadId: string) => void;
  onSpawnAgent?: () => void;
};

// `onAgentOpen` / `onSpawnAgent` stay on Props because AppShell passes them, but the
// rail never wired them to anything — they are accepted and dropped. Left in place
// rather than removed from the interface so the caller keeps compiling; if the rail is
// meant to open an agent, that is the hook to use.
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
      <nav aria-label="Main navigation" className="chrome w-[62px] border-r border-border flex flex-col items-center py-3 gap-2 flex-shrink-0 z-10">
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
                    "relative w-11 h-11 rounded-[11px] flex items-center justify-center transition-colors cursor-pointer",
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
              <TooltipContent side="right" className="max-w-[220px]">
                <span className="font-semibold">
                  {item.label}{showBadge ? ` (${badgeCount} recent)` : ""}
                </span>
                <span className="block text-[11px] opacity-70 mt-0.5 leading-snug">
                  {item.blurb}
                </span>
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
              className="w-11 h-11 rounded-[11px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors cursor-pointer"
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
              className="w-11 h-11 rounded-[11px] flex items-center justify-center text-purple hover:bg-purple/10 transition-colors cursor-pointer"
              aria-label="Co-Pilot"
            >
              <Bot className="w-[18px] h-[18px]" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            <span className="flex items-center gap-2">
              Co-Pilot
              <kbd className="font-mono text-[10px] rounded px-1 py-0.5" style={{ background: "var(--border)", border: "1px solid var(--cyan)", color: "var(--cyan)", boxShadow: "0 0 6px color-mix(in oklab, var(--cyan) 40%, transparent)" }}>⌃K</kbd>
            </span>
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={handleThemeToggle}
              className="w-11 h-11 rounded-[11px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors cursor-pointer"
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
