import { useAction, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useState, useEffect } from "react";
import { usd } from "../lib/formatters";

type TokenRow = { symbol: string; balance: string; usdValue: number; chain: string };

function parseHoldings(data: unknown): TokenRow[] {
  if (!data || typeof data !== "object") return [];
  const d = data as Record<string, unknown>;
  const chains = Array.isArray(d.chains) ? d.chains : [];
  const rows: TokenRow[] = [];
  for (const chain of chains) {
    const c = chain as Record<string, unknown>;
    const tokens = Array.isArray(c.tokens) ? c.tokens : [];
    for (const t of tokens) {
      const tok = t as Record<string, unknown>;
      rows.push({
        chain: String(c.name ?? ""),
        symbol: String(tok.symbol ?? ""),
        balance: String(tok.balance ?? "0"),
        usdValue: Number(tok.usdValue ?? 0),
      });
    }
  }
  return rows.sort((a, b) => b.usdValue - a.usdValue);
}

export function PortfolioView() {
  const walletState = useQuery(api.walletState.get);
  const fetchPortfolio = useAction(api.twak.getPortfolio);
  const [portfolio, setPortfolio] = useState<{ ok: boolean; data: unknown; error?: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { setPortfolio(await fetchPortfolio({})); }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const holdings = portfolio?.ok ? parseHoldings(portfolio.data) : [];
  const totalUsd = (portfolio?.data as Record<string, unknown>)?.totalUsd;

  return (
    <div className="max-w-[720px] mx-auto space-y-4">
      <div className="mb-2 flex items-end justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
            TWAK Self-Custody
          </div>
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Portfolio</h1>
        </div>
        <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text cursor-pointer"
          onClick={refresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </Button>
      </div>

      {/* Total */}
      <Panel label="Total Value" tick="green">
        {loading && !portfolio ? <Skeleton className="h-12 w-48 bg-elevated" /> : (
          <div className="py-2">
            <div className="font-mono text-[32px] font-bold text-text tabular-nums">
              {totalUsd != null ? usd(Number(totalUsd)) : walletState ? usd(walletState.total_usd) : "—"}
            </div>
            <div className="font-mono text-[11px] text-muted-fg mt-1">
              {portfolio?.ok ? "live from TWAK wallet" : "from last known wallet_state"}
            </div>
          </div>
        )}
      </Panel>

      {/* Holdings table */}
      <Panel label="Holdings">
        {loading && !portfolio ? (
          <div className="space-y-2">
            {[1,2,3].map(i => <Skeleton key={i} className="h-8 w-full bg-elevated" />)}
          </div>
        ) : holdings.length === 0 ? (
          <p className="font-mono text-[12px] text-muted-fg py-2">
            {portfolio?.error ? `Agent offline: ${portfolio.error}` : "No holdings found."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">Chain</th>
                  <th className="text-left font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">Token</th>
                  <th className="text-right font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">Balance</th>
                  <th className="text-right font-mono text-[10px] text-muted-fg pb-2 uppercase tracking-widest">USD Value</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((row, i) => (
                  <tr key={i} className="border-b border-border/40 hover:bg-elevated/40 transition-colors">
                    <td className="py-2 font-mono text-muted-fg text-[11px]">{row.chain}</td>
                    <td className="py-2 font-mono text-text font-semibold">{row.symbol}</td>
                    <td className="py-2 font-mono text-muted-fg text-right tabular-nums">{row.balance}</td>
                    <td className="py-2 font-mono text-text text-right tabular-nums">{usd(row.usdValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
