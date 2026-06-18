import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, pct, elapsed, ts } from "../lib/formatters";

export function PortfolioView() {
  const wallet    = useQuery(api.walletState.get);
  const ledger    = useQuery(api.ledger.latest);
  const positions = useQuery(api.positions.open) ?? [];
  const trades    = useQuery(api.trades.recent, { limit: 20 }) ?? [];

  const pnlPos = (ledger?.cumulative_pnl_usd ?? 0) >= 0;

  return (
    <div className="max-w-[900px] mx-auto space-y-4">
      {/* Page header */}
      <div className="mb-2 flex items-end justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
            TWAK Self-Custody · Live
          </div>
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Portfolio</h1>
        </div>
        {wallet && (
          <span className="font-mono text-[10px] text-muted-fg">
            synced {elapsed(wallet.updated_ms)} ago
          </span>
        )}
      </div>

      {/* Total value + PnL side by side */}
      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <Panel label="Total Value" tick="green">
          {wallet === undefined ? (
            <Skeleton className="h-12 w-40 bg-elevated" />
          ) : wallet === null ? (
            <p className="font-mono text-[12px] text-muted-fg py-2">// awaiting first cycle</p>
          ) : (
            <div className="py-1">
              <div className="font-mono text-[32px] font-bold text-text tabular-nums leading-none">
                {usd(wallet.total_usd)}
              </div>
              <div className="font-mono text-[11px] text-muted-fg mt-1.5">
                updated {elapsed(wallet.updated_ms)} ago · auto-synced
              </div>
            </div>
          )}
        </Panel>

        <Panel label="Cumulative PnL" tick={pnlPos ? "green" : "red"}>
          {ledger === undefined ? (
            <Skeleton className="h-12 w-40 bg-elevated" />
          ) : (
            <div className="py-1">
              <div className={cn(
                "font-mono text-[32px] font-bold tabular-nums leading-none",
                pnlPos ? "text-green glow-green" : "text-red",
              )}>
                {usd(ledger?.cumulative_pnl_usd)}
              </div>
              <div className="font-mono text-[11px] text-muted-fg mt-1.5 flex gap-3">
                <span>drawdown {pct(ledger?.max_drawdown_pct)}</span>
                <span>{ledger?.n_trades ?? 0} trades</span>
              </div>
            </div>
          )}
        </Panel>
      </div>

      {/* Holdings breakdown */}
      <Panel label="Holdings" tick="cyan">
        {wallet === undefined ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-9 w-full bg-elevated rounded" />)}
          </div>
        ) : wallet === null ? (
          <p className="font-mono text-[12px] text-muted-fg py-2">
            // awaiting first cycle balance snapshot
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest">Token</th>
                  <th className="text-left font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest">Role</th>
                  <th className="text-right font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest">Balance</th>
                  <th className="text-right font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest">USD Value</th>
                </tr>
              </thead>
              <tbody>
                <HoldingRow
                  token="USDT"
                  role="dry powder"
                  balance={wallet.usdt.toFixed(2)}
                  usdValue={wallet.usdt}
                  warn={wallet.usdt < 1}
                  warnMsg="⚠ balance nearly depleted"
                />
                <HoldingRow
                  token="ETH"
                  role="open position"
                  balance={wallet.eth.toFixed(6)}
                  usdValue={wallet.total_usd - wallet.usdt - wallet.bnb_usd}
                  dim={wallet.eth === 0}
                />
                <HoldingRow
                  token="BNB"
                  role="gas reserve"
                  balance={wallet.bnb.toFixed(4)}
                  usdValue={wallet.bnb_usd}
                  warn={wallet.bnb < 0.003}
                  warnMsg="⚠ gas low — top up or swaps will fail"
                />
              </tbody>
              <tfoot>
                <tr className="border-t border-border">
                  <td colSpan={3} className="pt-3 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-fg">Total</td>
                  <td className="pt-3 text-right font-display text-[18px] font-bold text-green glow-green tabular-nums">
                    {usd(wallet.total_usd)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Panel>

      {/* Open positions */}
      {positions.length > 0 && (
        <Panel label="Open Positions" tick="cyan" action={
          <span className="font-mono text-[10px] text-muted-fg">{positions.length} active</span>
        }>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  {["Symbol", "Qty", "Entry", "Current", "Value", "Unrealised PnL"].map((h) => (
                    <th key={h} className={cn(
                      "font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest",
                      h === "Symbol" ? "text-left" : "text-right",
                    )}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => {
                  const pnlPos = p.unrealized_pnl_usd >= 0;
                  return (
                    <tr key={p._id} className="border-b border-border/40 hover:bg-elevated/40 transition-colors">
                      <td className="py-2.5 font-mono text-cyan font-bold">{p.symbol}</td>
                      <td className="py-2.5 font-mono text-text text-right tabular-nums">{p.quantity.toFixed(6)}</td>
                      <td className="py-2.5 font-mono text-muted-fg text-right tabular-nums">{usd(p.avg_entry_price)}</td>
                      <td className="py-2.5 font-mono text-text text-right tabular-nums">{usd(p.current_price)}</td>
                      <td className="py-2.5 font-mono text-text text-right tabular-nums">{usd(p.current_value_usd)}</td>
                      <td className={cn("py-2.5 font-mono font-bold text-right tabular-nums", pnlPos ? "text-green" : "text-red")}>
                        {pnlPos ? "+" : ""}{usd(p.unrealized_pnl_usd)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* Trade history */}
      <Panel label="Recent Trades" tick="cyan" action={
        <span className="font-mono text-[10px] text-muted-fg">{trades.length} shown</span>
      }>
        {trades.length === 0 ? (
          <p className="font-mono text-[12px] text-muted-fg py-2">// no trades recorded yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  {["Time", "Symbol", "Side", "Size", "Fill Price", "Fee + Gas"].map((h) => (
                    <th key={h} className={cn(
                      "font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest",
                      h === "Time" || h === "Symbol" || h === "Side" ? "text-left" : "text-right",
                    )}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t._id} className="border-b border-border/40 hover:bg-elevated/40 transition-colors">
                    <td className="py-2 font-mono text-[11px] text-muted-fg">{ts(t.timestamp_ms)}</td>
                    <td className="py-2 font-mono font-bold text-cyan">{t.symbol}</td>
                    <td className={cn("py-2 font-mono font-bold text-[11px] uppercase", t.side === "buy" ? "text-green" : "text-red")}>
                      {t.side}
                    </td>
                    <td className="py-2 font-mono text-text text-right tabular-nums">{usd(t.size_usd)}</td>
                    <td className="py-2 font-mono text-text text-right tabular-nums">{usd(t.fill_price)}</td>
                    <td className="py-2 font-mono text-muted-fg text-right tabular-nums">{usd(t.fee_usd + t.gas_usd)}</td>
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

function HoldingRow({
  token, role, balance, usdValue, warn = false, warnMsg, dim = false,
}: {
  token: string;
  role: string;
  balance: string;
  usdValue: number;
  warn?: boolean;
  warnMsg?: string;
  dim?: boolean;
}) {
  return (
    <>
      <tr className={cn("border-b border-border/40 hover:bg-elevated/40 transition-colors", dim && "opacity-50")}>
        <td className="py-2.5 font-mono font-bold text-text">{token}</td>
        <td className="py-2.5 font-mono text-[11px] text-muted-fg">{role}</td>
        <td className="py-2.5 font-mono text-muted-fg text-right tabular-nums">{balance}</td>
        <td className={cn("py-2.5 font-mono font-bold text-right tabular-nums", warn ? "text-red" : "text-text")}>
          {usd(usdValue)}
        </td>
      </tr>
      {warn && warnMsg && (
        <tr>
          <td colSpan={4} className="pb-2 font-mono text-[10px] text-red">{warnMsg}</td>
        </tr>
      )}
    </>
  );
}
