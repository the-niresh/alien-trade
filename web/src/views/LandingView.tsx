import { SPONSOR_CONTROLS } from "../lib/sponsorRegistry";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SPONSOR_COLOR: Record<string, string> = {
  TWAK: "text-cyan border-cyan/20 bg-cyan/5",
  CMC:  "text-yellow border-yellow/20 bg-yellow/5",
  BNB_SDK: "text-green border-green/20 bg-green/5",
  agent: "text-muted-fg border-border bg-elevated",
};

export function LandingView({ onConnect }: { onConnect: () => void }) {
  const operatorControls = SPONSOR_CONTROLS.filter((c) => c.transport !== "policy");
  return (
    <div className="min-h-screen bg-[#000000] flex flex-col">
      {/* Hero */}
      <div className="flex flex-col items-center justify-center pt-24 pb-16 px-6 text-center">
        <div className="font-display text-[48px] font-bold text-green tracking-[0.12em] mb-2"
          style={{ textShadow: "0 0 40px rgba(74,222,128,0.4)" }}>
          ALIEN·TRADE
        </div>
        <p className="font-mono text-[15px] text-text/80 max-w-lg leading-relaxed mb-2">
          Autonomous BSC trading agent. Deterministic signals. Self-custody execution via Trust Wallet. Real-time operator console.
        </p>
        <p className="font-mono text-[12px] text-muted-fg max-w-md mb-8">
          Track-1: live 7-day risk-adjusted PnL · TWAK self-custody · CMC x402 · BNB AI Agent SDK
        </p>
        <Button
          className="bg-green text-[#04140c] font-bold text-[15px] px-8 py-3 h-auto hover:bg-green/80 cursor-pointer"
          onClick={onConnect}
        >
          Connect Agent →
        </Button>
      </div>

      {/* Capabilities */}
      <div className="max-w-4xl mx-auto px-6 pb-24 w-full">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-6 text-center">
          Full Sponsor Surface — {operatorControls.length} controls
        </div>
        <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          {operatorControls.map((c) => (
            <div key={c.id} className={cn("border rounded-xl p-4", SPONSOR_COLOR[c.sponsor])}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="font-display text-[13px] font-bold">{c.label}</span>
              </div>
              <p className="font-mono text-[11px] opacity-70 leading-relaxed line-clamp-3">{c.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
