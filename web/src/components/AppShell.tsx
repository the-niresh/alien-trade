import { ReactNode } from "react";
import { SideNav, type View } from "./SideNav";
import { LiveHeader } from "./LiveHeader";
import { AgentTicker } from "./AgentTicker";
import { BottomNav } from "./BottomNav";
import { KillSwitch } from "./KillSwitch";

type Props = {
  children: ReactNode;
  activeView: View;
  onViewChange: (v: View) => void;
  onCopilot: () => void;
  onTour: () => void;
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
  selectedSymbol?: string;
  onSymbolChange?: (s: string) => void;
  onDeposit?: () => void;
  onAgentOpen?: (threadId: string) => void;
  onSpawnAgent?: () => void;
};

export function AppShell({
  children,
  activeView,
  onViewChange,
  onCopilot,
  onTour,
  halted,
  mode,
  onKillToggle,
  selectedSymbol,
  onSymbolChange,
  onDeposit,
  onAgentOpen,
  onSpawnAgent,
}: Props) {
  return (
    <div className="flex flex-col h-screen">
      <LiveHeader
        halted={halted}
        mode={mode}
        onKillToggle={onKillToggle}
        selectedSymbol={selectedSymbol}
        onSymbolChange={onSymbolChange}
        onDeposit={onDeposit}
      />
      <AgentTicker />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — hidden on mobile */}
        <div className="hidden sm:flex">
          <SideNav
            active={activeView}
            onSelect={onViewChange}
            onCopilot={onCopilot}
            onTour={onTour}
            onAgentOpen={onAgentOpen}
            onSpawnAgent={onSpawnAgent}
          />
        </div>
        <main className="flex-1 overflow-y-auto px-6 py-5 pb-12">
          {children}
        </main>
      </div>
      {/* Kill switch FAB — mobile only, floats above the bottom nav */}
      <div className="fixed bottom-[60px] right-6 sm:hidden z-30">
        <KillSwitch halted={halted} onToggle={onKillToggle} size="md" />
      </div>
      {/* Bottom nav — mobile only */}
      <div className="flex sm:hidden">
        <BottomNav
          active={activeView}
          onSelect={onViewChange}
          onCopilot={onCopilot}
        />
      </div>
    </div>
  );
}
