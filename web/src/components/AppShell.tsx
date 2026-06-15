import { ReactNode } from "react";
import { SideNav, type View } from "./SideNav";
import { LiveHeader } from "./LiveHeader";
import { AgentTicker } from "./AgentTicker";
import { BottomNav } from "./BottomNav";

type Props = {
  children: ReactNode;
  activeView: View;
  onViewChange: (v: View) => void;
  onCopilot: () => void;
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
  selectedSymbol?: string;
  onSymbolChange?: (s: string) => void;
};

export function AppShell({ children, activeView, onViewChange, onCopilot, halted, mode, onKillToggle, selectedSymbol, onSymbolChange }: Props) {
  return (
    <div className="flex flex-col h-screen">
      <LiveHeader halted={halted} mode={mode} onKillToggle={onKillToggle} selectedSymbol={selectedSymbol} onSymbolChange={onSymbolChange} />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — hidden on mobile */}
        <div className="hidden sm:flex">
          <SideNav active={activeView} onSelect={onViewChange} onCopilot={onCopilot} />
        </div>
        <main className="flex-1 overflow-y-auto px-6 py-5 pb-12">
          {children}
        </main>
      </div>
      <AgentTicker />
      {/* Bottom nav — mobile only */}
      <div className="flex sm:hidden">
        <BottomNav active={activeView} onSelect={onViewChange} onCopilot={onCopilot} />
      </div>
    </div>
  );
}
