import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { usd, elapsed } from "../lib/formatters";
import { cn } from "@/lib/utils";

export function WalletBalance() {
  const wallet = useQuery(api.walletState.get);

  return (
    <Panel
      label="Wallet Balance"
      tick="cyan"
      action={
        wallet ? (
          <span className="font-mono text-[10px] text-muted-fg">
            updated {elapsed(wallet.updated_ms)} ago
          </span>
        ) : undefined
      }
    >
      {wallet === undefined ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-7 w-full bg-elevated rounded" />
          ))}
        </div>
      ) : wallet === null ? (
        <p className="font-mono text-[12px] text-muted-fg py-1">
          // awaiting first cycle balance snapshot
        </p>
      ) : (
        <div className="flex flex-col gap-1">
          {/* USDT - dry powder */}
          <Row
            label="USDT"
            sub="dry powder"
            value={usd(wallet.usdt)}
            tone={wallet.usdt < 1 ? "warn" : "positive"}
          />
          {/* ETH - open position value */}
          <Row
            label="ETH"
            sub={wallet.eth > 0 ? `${wallet.eth.toFixed(6)} ETH` : "none held"}
            value={wallet.eth > 0 ? usd(wallet.eth * (wallet.total_usd - wallet.usdt - wallet.bnb_usd > 0 ? (wallet.total_usd - wallet.usdt - wallet.bnb_usd) / wallet.eth : 0)) : "$0.00"}
            tone={wallet.eth > 0 ? "neutral" : "neutral"}
          />
          {/* BNB - gas */}
          <Row
            label="BNB"
            sub="gas reserve"
            value={`${wallet.bnb.toFixed(4)} (${usd(wallet.bnb_usd)})`}
            tone={wallet.bnb < 0.003 ? "negative" : "neutral"}
          />
          {/* Divider + total */}
          <div className="mt-1 pt-2 border-t border-border flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-fg">
              Total
            </span>
            <span className={cn(
              "font-display text-[18px] font-bold tabular-nums",
              wallet.total_usd >= 5 ? "text-green glow-green" : "text-yellow",
            )}>
              {usd(wallet.total_usd)}
            </span>
          </div>
          {wallet.bnb < 0.003 && (
            <p className="font-mono text-[10px] text-red mt-1">
              ⚠ BNB low - add gas or swaps will fail
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}

function Row({
  label,
  sub,
  value,
  tone,
}: {
  label: string;
  sub: string;
  value: string;
  tone: "positive" | "negative" | "warn" | "neutral";
}) {
  const color = {
    positive: "text-green",
    negative: "text-red",
    warn: "text-yellow",
    neutral: "text-text",
  }[tone];

  return (
    <div className="flex items-center justify-between py-1">
      <div>
        <span className="font-mono text-[12px] font-bold text-text">{label}</span>
        <span className="font-mono text-[10px] text-muted-fg ml-2">{sub}</span>
      </div>
      <span className={cn("font-mono text-[12px] tabular-nums", color)}>{value}</span>
    </div>
  );
}
