import { ReactNode } from "react";
import { SideNav, View } from "./SideNav";
import { LiveHeader } from "./LiveHeader";
import { AgentTicker } from "./AgentTicker";

type Props = {
  children: ReactNode;
  activeView: View;
  onViewChange: (v: View) => void;
  onCopilot: () => void;
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
};

export function AppShell({ children, activeView, onViewChange, onCopilot, halted, mode, onKillToggle }: Props) {
  return (
    <div className="app-shell">
      <LiveHeader halted={halted} mode={mode} onKillToggle={onKillToggle} />
      <div className="app-body">
        <SideNav active={activeView} onSelect={onViewChange} onCopilot={onCopilot} />
        <main className="app-main">{children}</main>
      </div>
      <AgentTicker />
    </div>
  );
}
