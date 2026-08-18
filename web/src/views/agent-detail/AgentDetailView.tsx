import { useState } from "react";
import { useMutation } from "convex/react";
import { toast } from "sonner";
import { api } from "../../../../convex/_generated/api";
import { withToken } from "@/lib/control";
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

const headerBtn = "font-mono text-[11px] border rounded px-3 py-1 transition-colors flex-shrink-0";

export function AgentDetailView({ agent, onBack, onOpenChat }: Props) {
  const [section, setSection] = useState<DetailSection>("dashboard");
  const setStatus = useMutation(api.spawnedAgents.setStatus);

  const isSpawned = agent.kind === "spawned" && !!agent.id;
  const isActive = agent.status === "active";

  async function changeStatus(status: "active" | "idle" | "archived", label: string) {
    if (!agent.id) return;
    try {
      await setStatus(withToken({ id: agent.id, status }));
      toast.success(label);
      if (status === "archived") onBack();
    } catch (e) {
      toast.error(`Failed - ${String(e).includes("token") ? "pair the cockpit first" : String(e)}`);
    }
  }

  return (
    <div className="max-w-[1180px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="font-mono text-[11px] text-muted-fg hover:text-text border border-border/40 rounded px-2 py-1 transition-colors"
          >← Agents</button>
          <span className={cn(
            "w-2.5 h-2.5 rounded-full flex-shrink-0",
            isActive ? "bg-green" : "bg-muted-fg/30",
          )} style={isActive ? { boxShadow: "0 0 6px var(--green)" } : {}} />
          <h1 className="font-display text-[20px] font-bold text-text truncate">{agent.name}</h1>
          <span className={cn(
            "font-mono text-[9px] rounded px-1.5 py-0.5 uppercase tracking-widest border",
            isActive ? "text-green border-green/30 bg-green/10" : "text-muted-fg border-border/40",
          )}>{isActive ? "Active" : agent.status}</span>
          {agent.kind === "primary" && (
            <span className="font-mono text-[9px] text-green border border-green/30 bg-green/10 rounded px-1.5 py-0.5 uppercase tracking-widest">Live trader</span>
          )}
          {agent.mode && (
            <span className="font-mono text-[9px] text-muted-fg border border-border/40 rounded px-1.5 py-0.5 uppercase tracking-widest">{agent.mode}</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setSection("configure")}
            className={cn(headerBtn, "text-muted-fg border-border/40 hover:text-text hover:border-border/60")}
          >Configure</button>
          {isSpawned && (isActive ? (
            <button
              onClick={() => changeStatus("idle", "Agent paused")}
              className={cn(headerBtn, "text-yellow-400 border-yellow-400/30 hover:bg-yellow-400/10")}
            >Pause</button>
          ) : (
            <button
              onClick={() => changeStatus("active", "Agent resumed")}
              className={cn(headerBtn, "text-green border-green/30 hover:bg-green/10")}
            >Resume</button>
          ))}
          {isSpawned && (
            <button
              onClick={() => changeStatus("archived", "Agent terminated")}
              className={cn(headerBtn, "text-red border-red/30 hover:bg-red/10")}
            >Terminate</button>
          )}
          <button
            onClick={onOpenChat}
            className={cn(headerBtn, "text-purple border-purple/30 hover:bg-purple/10")}
          >Open Chat →</button>
        </div>
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
