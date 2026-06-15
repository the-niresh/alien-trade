import { useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { loadToken, setToken, withToken } from "./lib/control";
import { AppShell } from "./components/AppShell";
import { CoPilotDrawer } from "./components/CoPilotDrawer";
import { OverviewView } from "./views/OverviewView";
import { PositionsView } from "./views/PositionsView";
import { AgentsView } from "./views/AgentsView";
import { ControlsView } from "./views/ControlsView";
import { LogsView } from "./views/LogsView";
import type { View } from "./components/SideNav";

function PairingScreen({ onPaired }: { onPaired: (t: string) => void }) {
  const [val, setVal] = useState("");
  const submit = () => { const t = val.trim(); if (t) onPaired(t); };
  return (
    <div className="pairing-screen">
      <div className="pairing-card">
        <div className="pairing-title">ALIEN-TRADE</div>
        <div className="pairing-sub">
          Pair this cockpit to control the agent. Scan the onboarding QR or paste your control token below.
        </div>
        <input
          type="password"
          value={val}
          placeholder="control token"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          className="num-input"
          style={{ width: "100%", marginBottom: 12 }}
        />
        <button
          className="btn btn--primary"
          onClick={submit}
          disabled={!val.trim()}
          style={{ width: "100%" }}
        >
          Pair cockpit
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const config = useQuery(api.config.get);

  const _setHalted  = useMutation(api.config.setHalted);
  const _setControl = useMutation(api.agentControl.set);
  const setHalted   = (a: Parameters<typeof _setHalted>[0])  => _setHalted(withToken(a));
  const setControl  = (a: Parameters<typeof _setControl>[0]) => _setControl(withToken(a));

  const [token, setTokenState]       = useState<string | null>(loadToken());
  const [view, setView]              = useState<View>("overview");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotPrefill, setCopilotPrefill] = useState("");

  const halted = config?.halted ?? false;
  const mode   = config?.trading_mode;

  const onKillToggle = () => {
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };

  const onAgentClick = (name: string) => {
    setCopilotPrefill(`What is ${name} currently doing?`);
    setCopilotOpen(true);
  };

  if (!token) {
    return <PairingScreen onPaired={(t) => { setToken(t); setTokenState(t); }} />;
  }

  const renderView = () => {
    switch (view) {
      case "overview":  return <OverviewView  onAgentClick={onAgentClick} />;
      case "positions": return <PositionsView />;
      case "agents":    return <AgentsView    onAgentClick={onAgentClick} />;
      case "controls":  return <ControlsView />;
      case "logs":      return <LogsView />;
    }
  };

  return (
    <>
      <AppShell
        activeView={view}
        onViewChange={setView}
        onCopilot={() => setCopilotOpen(true)}
        halted={halted}
        mode={mode}
        onKillToggle={onKillToggle}
      >
        {renderView()}
      </AppShell>
      <CoPilotDrawer
        isOpen={copilotOpen}
        onClose={() => { setCopilotOpen(false); setCopilotPrefill(""); }}
        prefill={copilotPrefill}
      />
    </>
  );
}
