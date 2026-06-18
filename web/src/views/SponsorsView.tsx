import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { usd } from "../lib/formatters";

export function SponsorsView() {
  const trades = useQuery(api.trades.recent, { limit: 1 });
  const wallet = useQuery(api.walletState.get, {});
  const last = trades?.[0];
  const tx = last?.tx_hash ? `https://bscscan.com/tx/${last.tx_hash}` : null;

  return (
    <div className="p-3 sm:p-4 grid gap-3 sm:grid-cols-3">
      <Panel label="CMC — Data & Signals" tick="cyan">
        <p className="font-mono text-[12px] text-text leading-relaxed">
          S1–S4 from CMC OHLCV · funding/OI · social · flow. x402 micropayments per
          metered call. Live KOL ingest feeds S3.
        </p>
      </Panel>

      <Panel label="TWAK — Self-Custody" tick="green">
        <p className="font-mono text-[12px] text-text leading-relaxed">
          Every swap signed via Trust Wallet Agent Kit. Keys never in code.
        </p>
        {wallet && (
          <p className="font-mono text-[11px] text-muted-fg mt-2">
            Wallet: {usd(wallet.total_usd ?? 0)} managed
          </p>
        )}
      </Panel>

      <Panel label="BNB SDK — Execution" tick="yellow">
        <p className="font-mono text-[12px] text-text leading-relaxed">
          Spot longs as <code>twak swap</code>; on-chain receipt is ledger truth.
        </p>
        {last ? (
          <div className="font-mono text-[11px] text-muted-fg mt-2">
            Last fill: {last.side} {last.symbol} @ {usd(last.fill_price)}
            {tx && (
              <a href={tx} target="_blank" rel="noopener noreferrer"
                 className="block text-green/70 hover:text-green mt-1">
                TX ↗ BscScan
              </a>
            )}
          </div>
        ) : (
          <p className="font-mono text-[11px] text-muted-fg mt-2">// no fills yet</p>
        )}
      </Panel>
    </div>
  );
}
