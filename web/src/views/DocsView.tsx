import { SPONSOR_CONTROLS } from "../lib/sponsorRegistry";
import { Panel } from "../components/Panel";
import { cn } from "@/lib/utils";

const SPONSOR_COLOR: Record<string, string> = {
  TWAK: "text-cyan", CMC: "text-yellow", BNB_SDK: "text-green", agent: "text-muted-fg",
};

export function DocsView() {
  const grouped = ["TWAK", "CMC", "BNB_SDK", "agent"].map((s) => ({
    sponsor: s,
    controls: SPONSOR_CONTROLS.filter((c) => c.sponsor === s),
  })).filter((g) => g.controls.length > 0);

  return (
    <div className="max-w-[720px] mx-auto space-y-6">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Reference
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">What every control does</h1>
        <p className="text-[13px] text-muted-fg mt-2 leading-relaxed">
          Each row is one action the operator can take, grouped by the service that
          carries it out - <span className="text-text">TWAK</span> signs transactions,{" "}
          <span className="text-text">CMC</span> supplies market data,{" "}
          <span className="text-text">BNB_SDK</span> talks to the chain, and{" "}
          <span className="text-text">agent</span> is the bot itself. In read-only mode you
          can read all of them; running them needs the operator&apos;s control token.
        </p>
      </div>
      {grouped.map(({ sponsor, controls }) => (
        <Panel key={sponsor} label={<span className={cn("font-mono font-bold", SPONSOR_COLOR[sponsor])}>{sponsor}</span>}>
          <div className="space-y-4">
            {controls.map((c) => (
              <div key={c.id} className="border-b border-border/40 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-display text-[14px] font-bold text-text">{c.label}</span>
                  <span className="font-mono text-[9px] border border-border rounded px-1.5 py-0.5 text-muted-fg uppercase tracking-widest">{c.transport}</span>
                  <span className={cn("font-mono text-[9px] uppercase tracking-widest", {
                    "text-green": c.scoringImpact === "scored",
                    "text-yellow": c.scoringImpact === "operator",
                    "text-muted-fg": c.scoringImpact === "neutral",
                  })}>{c.scoringImpact}</span>
                </div>
                <p className="font-mono text-[12px] text-muted-fg leading-relaxed">{c.description}</p>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}
