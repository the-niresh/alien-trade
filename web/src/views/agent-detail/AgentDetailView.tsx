import { useState } from "react";
import { cn } from "@/lib/utils";
import { SECTION_ORDER, sectionLabel, type DetailAgent, type DetailSection } from "./types";
import { DashboardSection } from "./DashboardSection";
import { TradesSection } from "./TradesSection";
import { ScanningSection } from "./ScanningSection";
import { LivePositionsSection } from "./LivePositionsSection";
import { ConfigureSection } from "./ConfigureSection";

type Props = {
  agent: DetailAgent;
  onBack: () => void;
  onOpenChat: () => void;
};

export function AgentDetailView({ agent, onBack, onOpenChat }: Props) {
  const [section, setSection] = useState<DetailSection>("dashboard");

  return (
    <div className="max-w-[1180px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="font-mono text-[11px] text-muted-fg hover:text-text border border-border/40 rounded px-2 py-1 transition-colors"
          >← Agents</button>
          <span className={cn(
            "w-2.5 h-2.5 rounded-full flex-shrink-0",
            agent.status === "active" ? "bg-green" : "bg-muted-fg/30",
          )} style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}} />
          <h1 className="font-display text-[20px] font-bold text-text truncate">{agent.name}</h1>
          {agent.kind === "primary" && (
            <span className="font-mono text-[9px] text-green border border-green/30 bg-green/10 rounded px-1.5 py-0.5 uppercase tracking-widest">Live trader</span>
          )}
          {agent.mode && (
            <span className="font-mono text-[9px] text-muted-fg border border-border/40 rounded px-1.5 py-0.5 uppercase tracking-widest">{agent.mode}</span>
          )}
        </div>
        <button
          onClick={onOpenChat}
          className="font-mono text-[11px] text-purple border border-purple/30 rounded px-3 py-1 hover:bg-purple/10 transition-colors flex-shrink-0"
        >Open Chat →</button>
      </div>

      <div className="flex gap-5 max-md:flex-col">
        {/* Left sub-nav */}
        <nav className="flex md:flex-col gap-1 md:w-[160px] flex-shrink-0 max-md:flex-wrap">
          {SECTION_ORDER.map((s) => (
            <button
              key={s}
              onClick={() => setSection(s)}
              className={cn(
                "font-mono text-[11px] text-left rounded px-3 py-2 transition-colors uppercase tracking-widest",
                section === s
                  ? "bg-green/12 text-green border border-green/25"
                  : "text-muted-fg border border-transparent hover:text-text hover:border-border/40",
              )}
            >{sectionLabel(s)}</button>
          ))}
        </nav>

        {/* Section outlet */}
        <div className="flex-1 min-w-0">
          {section === "dashboard" && <DashboardSection agent={agent} />}
          {section === "trades"    && <TradesSection agent={agent} />}
          {section === "scanning"  && <ScanningSection agent={agent} />}
          {section === "positions" && <LivePositionsSection agent={agent} />}
          {section === "configure" && <ConfigureSection agent={agent} />}
        </div>
      </div>
    </div>
  );
}
