import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
import { ViewError } from "./components/ViewError";
import { ErrorBoundary } from "react-error-boundary";
import { Toaster, toast } from "sonner";
import QRCode from "qrcode";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { View } from "./components/SideNav";

// ── Pairing wizard ────────────────────────────────────────────────────────────

type PairingStep = "welcome" | "pair" | "done";

function PairingScreen({ onPaired }: { onPaired: (t: string) => void }) {
  const [step, setStep]     = useState<PairingStep>("welcome");
  const [val, setVal]       = useState("");
  const [error, setError]   = useState("");
  const [checking, setChecking] = useState(false);
  const canvasRef           = useRef<HTMLCanvasElement>(null);
  const pingMutation        = useMutation(api.ping.ping);

  useEffect(() => {
    if (step === "pair" && canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, window.location.href, {
        width: 160,
        color: { dark: "#000000", light: "#ffffff" },
        errorCorrectionLevel: "M",
      }).catch(() => {/* ignore render errors */});
    }
  }, [step]);

  const submit = async () => {
    const t = val.trim();
    if (!t) return;
    setError("");
    setChecking(true);
    try {
      await pingMutation({ control_token: t });
      setChecking(false);
      setStep("done");
      setTimeout(() => onPaired(t), 1200);
    } catch {
      setChecking(false);
      setError("Wrong token — check your .env.local CONTROL_TOKEN.");
    }
  };

  const STEPS: PairingStep[] = ["welcome", "pair", "done"];

  return (
    <div className="grid place-items-center h-screen overflow-auto">
      <Dialog open modal>
        <DialogContent
          className="panel border-border max-w-sm w-[90%] rounded-2xl p-0 overflow-hidden"
          onInteractOutside={(e) => e.preventDefault()}
        >
          {/* Step indicators */}
          <div className="flex gap-1.5 px-6 pt-5">
            {STEPS.map((s, i) => (
              <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${
                s === step ? "bg-green" :
                STEPS.indexOf(step) > i ? "bg-green/40" : "bg-border"
              }`} />
            ))}
          </div>

          {step === "welcome" && (
            <div className="px-6 py-5 text-center">
              <DialogHeader>
                <div className="font-display text-[28px] font-bold text-green glow-green tracking-[0.16em] mb-1">
                  ALIEN<span className="text-text/40">·</span>TRADE
                </div>
                <DialogTitle className="text-[16px] font-semibold text-text">
                  Autonomous trading cockpit
                </DialogTitle>
                <DialogDescription className="text-muted-fg text-[13px] mt-2 leading-relaxed">
                  Pair this cockpit to your running agent to see live PnL, control the kill switch, and chat with the co-pilot.
                </DialogDescription>
              </DialogHeader>
              <Button
                className="mt-6 w-full bg-green text-[#04140c] font-bold hover:bg-green/80 cursor-pointer"
                onClick={() => setStep("pair")}
              >
                Connect your agent →
              </Button>
            </div>
          )}

          {step === "pair" && (
            <div className="px-6 py-5">
              <DialogHeader>
                <DialogTitle className="text-[12px] font-bold text-muted-fg uppercase tracking-widest mb-3">
                  Step 2 of 3 — Pair device
                </DialogTitle>
              </DialogHeader>
              <div className="flex flex-col items-center mb-4 gap-2">
                <canvas ref={canvasRef} className="rounded-lg" />
                <p className="text-[11px] text-muted-fg">Scan to open on mobile</p>
              </div>
              <div className="flex items-center gap-2 my-3">
                <div className="flex-1 h-px bg-border" />
                <span className="text-[11px] text-muted-fg">or paste token</span>
                <div className="flex-1 h-px bg-border" />
              </div>
              <Input
                type="password"
                value={val}
                placeholder="control token"
                onChange={(e) => { setVal(e.target.value); setError(""); }}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                className="w-full bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-green mb-2"
              />
              {error && (
                <p className="font-mono text-[11px] text-red mb-2">{error}</p>
              )}
              <Button
                className="w-full bg-green text-[#04140c] font-bold hover:bg-green/80 cursor-pointer disabled:opacity-50"
                onClick={submit}
                disabled={!val.trim() || checking}
              >
                {checking ? "Verifying…" : "Pair cockpit →"}
              </Button>
            </div>
          )}

          {step === "done" && (
            <div className="px-6 py-8 text-center">
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
                className="text-5xl mb-4"
              >
                ✓
              </motion.div>
              <DialogTitle className="font-grotesk text-lg font-bold text-green mb-2">
                Cockpit paired
              </DialogTitle>
              <DialogDescription className="text-muted-fg text-[13px]">
                You're in. Loading your agent…
              </DialogDescription>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Main app ──────────────────────────────────────────────────────────────────

export default function App() {
  const config = useQuery(api.config.get);
  const events = useQuery(api.agentEvents.recent, { limit: 5 });

  const _setHalted  = useMutation(api.config.setHalted);
  const _setControl = useMutation(api.agentControl.set);
  const setHalted   = (a: Parameters<typeof _setHalted>[0])  => _setHalted(withToken(a));
  const setControl  = (a: Parameters<typeof _setControl>[0]) => _setControl(withToken(a));

  const [token, setTokenState]              = useState<string | null>(loadToken());
  const [view, setView]                     = useState<View>("overview");
  const [copilotOpen, setCopilotOpen]       = useState(false);
  const [copilotPrefill, setCopilotPrefill] = useState("");
  const [lastFloorHalt, setLastFloorHalt]   = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState("ALL");

  const halted = config?.halted ?? false;
  const mode   = config?.trading_mode;

  // Equity floor toast — fires once per unique event
  useEffect(() => {
    const floorHalt = (events ?? []).find(
      (e) => e.agent === "RiskGuard" && e.kind === "control" &&
        typeof e.headline === "string" && e.headline.includes("floor hit"),
    );
    if (floorHalt && floorHalt._id !== lastFloorHalt) {
      setLastFloorHalt(floorHalt._id);
      toast.error("Equity floor hit", {
        description: "Agent has been halted. Fund wallet or raise floor.",
        duration: Infinity,
      });
    }
  }, [events, lastFloorHalt]);

  const onKillToggle = () => {
    const willHalt = !halted;
    setHalted({ halted: willHalt });
    setControl({ trading_halted: willHalt, updated_by: "user" });
    if (willHalt) {
      toast.error("Trading halted", { description: "Hold the kill switch again to resume.", duration: 6000 });
    } else {
      toast.success("Trading resumed", { duration: 3000 });
    }
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
        selectedSymbol={selectedSymbol}
        onSymbolChange={setSelectedSymbol}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
          >
            <ErrorBoundary FallbackComponent={ViewError} resetKeys={[view]}>
              {renderView()}
            </ErrorBoundary>
          </motion.div>
        </AnimatePresence>
      </AppShell>

      <CoPilotDrawer
        isOpen={copilotOpen}
        onClose={() => { setCopilotOpen(false); setCopilotPrefill(""); }}
        prefill={copilotPrefill}
      />

      <Toaster position="bottom-right" theme="dark" richColors />
    </>
  );
}
