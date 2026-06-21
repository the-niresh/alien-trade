import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { cn } from "@/lib/utils";

const SPONSOR_COLOR: Record<string, string> = {
  CMC:     "text-yellow-400 border-yellow-400/25 bg-yellow-400/10",
  TWAK:    "text-purple-400 border-purple-400/25 bg-purple-400/10",
  BNB_SDK: "text-amber-400 border-amber-400/25 bg-amber-400/10",
};

const SPONSOR_DESC: Record<string, string> = {
  CMC:     "CoinMarketCap — market data + x402 micropayments",
  TWAK:    "Trust Wallet Agent Kit — self-custody signing",
  BNB_SDK: "BNB AI Agent SDK — on-chain execution",
};

function SponsorBadge({ sponsor }: { sponsor: string }) {
  return (
    <span className={cn(
      "font-mono text-[9px] border rounded px-1.5 py-0.5 uppercase tracking-widest flex-shrink-0",
      SPONSOR_COLOR[sponsor] ?? "text-muted-foreground border-muted-foreground/20 bg-muted-foreground/10",
    )}>{sponsor}</span>
  );
}

type SummaryRow = {
  sponsor: string;
  calls: number;
  errors: number;
  cost_usd_total: number;
  last_ts: number | null;
};

type FeedRow = {
  _id: string;
  sponsor: string;
  kind: string;
  endpoint: string;
  status: string;
  latency_ms: number;
  cost_usd?: number;
  tx_hash?: string;
  ts_ms: number;
};

export function IntelligenceView() {
  const rows    = (useQuery(api.sponsorCalls.recent, { limit: 50 }) ?? []) as FeedRow[];
  const summary = (useQuery(api.sponsorCalls.summary) ?? []) as SummaryRow[];

  return (
    <div className="max-w-[960px] mx-auto space-y-5">
      {/* Header */}
      <div className="mb-1">
        <div className="font-mono text-[10px] text-muted-foreground tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green-400 rounded-full inline-block" />
          Sponsor Stack &amp; Intelligence
        </div>
        <h1 className="text-[22px] font-bold tracking-wide">Intelligence</h1>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-1">
        {summary.map((s) => (
          <div key={s.sponsor} className="rounded-lg border border-border/40 bg-card/60 p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <SponsorBadge sponsor={s.sponsor} />
              {s.errors > 0 && (
                <span className="font-mono text-[9px] text-red-400 border border-red-400/25 bg-red-400/10 rounded px-1.5 py-0.5">{s.errors} err</span>
              )}
            </div>
            <p className="font-mono text-[10px] text-muted-foreground/70 leading-snug">{SPONSOR_DESC[s.sponsor]}</p>
            <div className="flex items-center justify-between border-t border-border/30 pt-2">
              <span className="font-mono text-[10px] text-muted-foreground/50 uppercase tracking-widest">Calls</span>
              <span className="font-mono text-[13px] font-bold">{s.calls}</span>
            </div>
            {s.cost_usd_total > 0 && (
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-muted-foreground/50 uppercase tracking-widest">x402 spent</span>
                <span className="font-mono text-[13px] font-bold text-yellow-400">${s.cost_usd_total.toFixed(4)}</span>
              </div>
            )}
            {s.last_ts != null && (
              <p className="font-mono text-[10px] text-muted-foreground/40">
                Last: {new Date(s.last_ts).toLocaleTimeString()}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Live feed */}
      <div>
        <div className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest mb-3">Live Sponsor Feed</div>
        {rows.length === 0 ? (
          <div className="rounded-lg border border-border/40 bg-card/60 p-8 text-center font-mono text-[12px] text-muted-foreground/60">
            No sponsor calls yet — agent idle.
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {rows.map((r) => (
              <div key={r._id} className="rounded-lg border border-border/40 bg-card/60 px-3 py-2.5 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <SponsorBadge sponsor={r.sponsor} />
                  <span className="font-mono text-[11px] truncate">{r.endpoint}</span>
                  <span className="font-mono text-[9px] text-muted-foreground/60 border border-border/30 rounded px-1.5 py-0.5">{r.kind}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {r.cost_usd != null && r.cost_usd > 0 && (
                    <span className="font-mono text-[10px] text-yellow-400">${r.cost_usd.toFixed(4)}</span>
                  )}
                  <span className="font-mono text-[10px] text-muted-foreground/50">{r.latency_ms.toFixed(0)}ms</span>
                  {r.tx_hash && (
                    <a
                      href={`https://bscscan.com/tx/${r.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[9px] text-purple-400 border border-purple-400/25 rounded px-1.5 py-0.5 hover:bg-purple-400/10 transition-colors"
                    >bscscan ↗</a>
                  )}
                  <span className={cn(
                    "font-mono text-[9px] border rounded px-1.5 py-0.5 uppercase tracking-widest",
                    r.status === "ok"
                      ? "text-green-400 border-green-400/25 bg-green-400/10"
                      : "text-red-400 border-red-400/25 bg-red-400/10",
                  )}>{r.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
