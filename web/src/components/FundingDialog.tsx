import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useAction } from "convex/react";
import { api } from "../../../convex/_generated/api";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Panel } from "./Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";
import {
  Copy, Check, ExternalLink, AlertTriangle, ArrowUpFromLine, ArrowDownUp,
} from "lucide-react";
import QRCode from "qrcode";

export type FundingTab = "deposit" | "buy" | "convert" | "withdraw";

const TABS: { id: FundingTab; label: string }[] = [
  { id: "deposit",  label: "Deposit"  },
  { id: "buy",      label: "Buy"      },
  { id: "convert",  label: "Convert"  },
  { id: "withdraw", label: "Withdraw" },
];

// ── Shared types ──────────────────────────────────────────────────────────────

type WalletFields = { usdt: number; eth: number; bnb: number };
type ConvertToken  = "BNB" | "USDT" | "ETH";
type WithdrawToken = "USDT" | "ETH" | "BNB";
type Step          = "form" | "confirm" | "done";

// ── Convert helpers ───────────────────────────────────────────────────────────

const CONVERT_TOKENS: ConvertToken[] = ["BNB", "USDT", "ETH"];
const TOKEN_DOT: Record<ConvertToken, string> = {
  BNB: "var(--yellow)", USDT: "var(--green)", ETH: "var(--cyan)",
};

function balanceOf(t: ConvertToken, w: WalletFields | null): number {
  if (!w) return 0;
  return t === "USDT" ? w.usdt : t === "ETH" ? w.eth : w.bnb;
}
function maxOf(t: ConvertToken, w: WalletFields | null): number {
  const bal = balanceOf(t, w);
  if (t === "BNB")  return Math.max(0, bal - 0.005);
  if (t === "USDT") return Math.max(0, bal - 0.5);
  return bal;
}

function TokenPill({ value, onChange }: { value: ConvertToken; onChange: (t: ConvertToken) => void }) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v as ConvertToken)}>
      <SelectTrigger className="w-auto gap-2 bg-elevated border-border rounded-full px-3 py-1.5 font-mono text-[13px] font-bold text-text focus:ring-cyan">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: TOKEN_DOT[value] }} />
          <SelectValue />
        </span>
      </SelectTrigger>
      <SelectContent className="bg-elevated border-border">
        {CONVERT_TOKENS.map((t) => (
          <SelectItem key={t} value={t} className="font-mono text-[13px]">
            <span className="inline-flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: TOKEN_DOT[t] }} />
              {t}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// ── Withdraw tab ──────────────────────────────────────────────────────────────

const WITHDRAW_MAX: Record<WithdrawToken, (w: WalletFields) => number> = {
  USDT: (w) => Math.max(0, w.usdt - 0.5),
  ETH:  (w) => w.eth,
  BNB:  (w) => Math.max(0, w.bnb - 0.005),
};

function WithdrawTab() {
  const wallet  = useQuery(api.walletState.get);
  const enqueue = useMutation(api.agentCommands.enqueue);

  const [token, setToken]     = useState<WithdrawToken>("USDT");
  const [amount, setAmount]   = useState("");
  const [toAddr, setToAddr]   = useState("");
  const [step, setStep]       = useState<Step>("form");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const maxAmount = wallet ? WITHDRAW_MAX[token](wallet as WalletFields) : 0;
  const addrValid = /^0x[0-9a-fA-F]{40}$/.test(toAddr.trim());
  const amtNum    = parseFloat(amount) || 0;
  const amtValid  = amtNum > 0 && amtNum <= maxAmount;

  const confirm = async () => {
    setLoading(true);
    try {
      await enqueue(withToken({
        command_type: "withdraw",
        params: JSON.stringify({ to_address: toAddr.trim(), amount: amtNum, token }),
        queued_by: "user",
      }));
      setStep("done");
    } catch (e) {
      setError(`Failed: ${String(e)}`);
      setStep("form");
    } finally {
      setLoading(false);
    }
  };

  if (step === "done") {
    return (
      <Panel label="Withdrawal Queued" tick="green">
        <div className="flex flex-col items-center gap-3 py-6">
          <div className="w-12 h-12 rounded-full bg-green/15 border border-green/30 flex items-center justify-center">
            <Check className="w-6 h-6 text-green" />
          </div>
          <p className="font-mono text-[13px] text-text text-center">
            Withdrawal queued. The agent will execute it in the next command cycle.
          </p>
          <p className="font-mono text-[11px] text-muted-fg text-center">
            Check the Trackers view to see its status.
          </p>
          <Button
            variant="outline"
            className="border-border text-muted-fg mt-2 cursor-pointer"
            onClick={() => { setStep("form"); setAmount(""); setToAddr(""); }}
          >
            New withdrawal
          </Button>
        </div>
      </Panel>
    );
  }

  if (step === "confirm") {
    return (
      <Panel label="Confirm Withdrawal" tick="yellow">
        <div className="space-y-4">
          <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow/8 border border-yellow/25">
            <AlertTriangle className="w-4 h-4 text-yellow flex-shrink-0 mt-0.5" />
            <p className="font-mono text-[11px] text-text leading-relaxed">
              Sending <span className="font-bold text-yellow">{amtNum} {token}</span> to:
            </p>
          </div>
          <div className="bg-bg border border-border rounded-lg px-3 py-2.5">
            <p className="font-mono text-[12px] text-text break-all">{toAddr.trim()}</p>
          </div>
          <p className="font-mono text-[10px] text-muted-fg">
            Verify the address above. Blockchain transactions are irreversible.
          </p>
          {error && <p className="font-mono text-[11px] text-red">{error}</p>}
          <div className="flex gap-2">
            <Button
              onClick={confirm}
              disabled={loading}
              className="flex-1 bg-yellow text-[#0d0900] font-bold hover:bg-yellow/80 cursor-pointer disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowUpFromLine className="w-4 h-4" />
              {loading ? "Queuing…" : "Yes, withdraw"}
            </Button>
            <Button
              variant="outline"
              onClick={() => setStep("form")}
              disabled={loading}
              className="flex-1 border-border text-muted-fg hover:text-text cursor-pointer"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <Panel label="Withdrawal Form" tick="purple">
      <div className="space-y-4">
        <div>
          <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">
            Token
          </label>
          <div className="flex gap-2">
            {(["USDT", "ETH", "BNB"] as WithdrawToken[]).map((t) => (
              <button
                key={t}
                onClick={() => { setToken(t); setAmount(""); }}
                className={cn(
                  "flex-1 font-mono text-[12px] font-bold py-1.5 rounded-lg border transition-colors cursor-pointer",
                  token === t
                    ? "bg-purple/15 border-purple/40 text-purple"
                    : "border-border text-muted-fg hover:text-text",
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {wallet && (
          <p className="font-mono text-[11px] text-muted-fg">
            Available:{" "}
            <span className="text-text font-bold">{maxAmount.toFixed(6)} {token}</span>
            {token === "USDT" && <span className="text-muted-fg"> (keeping $0.50 buffer)</span>}
            {token === "BNB"  && <span className="text-yellow"> (keeping 0.005 for gas)</span>}
          </p>
        )}

        <div>
          <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">
            Amount
          </label>
          <div className="flex gap-2">
            <Input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              min="0"
              step="any"
              className="bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-purple"
            />
            <Button
              variant="outline"
              className="border-border text-muted-fg cursor-pointer text-[11px] font-mono"
              onClick={() => setAmount(maxAmount.toFixed(6))}
            >
              Max
            </Button>
          </div>
        </div>

        <div>
          <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">
            Destination Address (BSC)
          </label>
          <Input
            value={toAddr}
            onChange={(e) => setToAddr(e.target.value)}
            placeholder="0x..."
            className={cn(
              "bg-bg border-border text-text font-mono text-[12px] focus-visible:ring-purple",
              toAddr && !addrValid ? "border-red/50" : "",
            )}
          />
          {toAddr && !addrValid && (
            <p className="font-mono text-[10px] text-red mt-1">
              Invalid BSC address (must be 0x + 40 hex chars)
            </p>
          )}
        </div>

        {error && <p className="font-mono text-[11px] text-red">{error}</p>}

        <Button
          onClick={() => { if (!addrValid || !amtValid) return; setError(""); setStep("confirm"); }}
          disabled={!addrValid || !amtValid}
          className="w-full bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer disabled:opacity-50 flex items-center gap-2"
        >
          <ArrowUpFromLine className="w-4 h-4" />
          Review Withdrawal
        </Button>
      </div>
    </Panel>
  );
}

// ── Convert tab ───────────────────────────────────────────────────────────────

function ConvertTab() {
  const wallet  = useQuery(api.walletState.get) as WalletFields | null;
  const enqueue = useMutation(api.agentCommands.enqueue);
  const quote   = useAction(api.twak.convertQuote);

  const [from, setFrom]               = useState<ConvertToken>("BNB");
  const [to, setTo]                   = useState<ConvertToken>("USDT");
  const [amount, setAmount]           = useState("");
  const [fromPrice, setFromPrice]     = useState(0);
  const [toPrice, setToPrice]         = useState(0);
  const [rateLoading, setRateLoading] = useState(false);
  const [rateAge, setRateAge]         = useState(0);
  const [step, setStep]               = useState<Step>("form");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");

  useEffect(() => {
    let cancelled = false;
    setRateLoading(true);
    quote({ from, to })
      .then((r) => {
        if (cancelled) return;
        setFromPrice(r.ok ? r.fromPrice : 0);
        setToPrice(r.ok ? r.toPrice : 0);
      })
      .catch(() => { if (!cancelled) { setFromPrice(0); setToPrice(0); } })
      .finally(() => { if (!cancelled) { setRateLoading(false); setRateAge(0); } });
    return () => { cancelled = true; };
  }, [from, to, quote]);

  useEffect(() => {
    if (rateLoading) return;
    const id = setInterval(() => setRateAge((a) => a + 1), 1000);
    return () => clearInterval(id);
  }, [rateLoading]);

  const amtNum   = parseFloat(amount) || 0;
  const maxFrom  = maxOf(from, wallet);
  const usdValue = amtNum * fromPrice;
  const gaining  = toPrice > 0 ? usdValue / toPrice : 0;
  const rate     = toPrice > 0 ? fromPrice / toPrice : 0;
  const amtValid = amtNum > 0 && amtNum <= maxFrom && fromPrice > 0;

  const flip     = () => { setFrom(to); setTo(from); setAmount(""); };
  const pickFrom = (t: ConvertToken) => { setAmount(""); if (t === to) setTo(from); setFrom(t); };
  const pickTo   = (t: ConvertToken) => { if (t === from) setFrom(to); setTo(t); };

  const confirm = async () => {
    setLoading(true);
    try {
      await enqueue(withToken({
        command_type: "convert",
        params: JSON.stringify({ from_token: from, to_token: to, usd: usdValue }),
        queued_by: "user",
      }));
      setStep("done");
    } catch (e) {
      setError(`Failed: ${String(e)}`);
      setStep("form");
    } finally {
      setLoading(false);
    }
  };

  if (step === "done") {
    return (
      <Panel label="Conversion Queued" tick="green">
        <div className="flex flex-col items-center gap-3 py-6">
          <div className="w-12 h-12 rounded-full bg-green/15 border border-green/30 flex items-center justify-center">
            <Check className="w-6 h-6 text-green" />
          </div>
          <p className="font-mono text-[13px] text-text text-center">
            Convert queued. The agent quotes it, checks price impact, then executes via TWAK.
          </p>
          <p className="font-mono text-[11px] text-muted-fg text-center">
            Check the Trackers view to see its status.
          </p>
          <Button variant="outline" className="border-border text-muted-fg mt-2 cursor-pointer"
            onClick={() => { setStep("form"); setAmount(""); }}>
            New conversion
          </Button>
        </div>
      </Panel>
    );
  }

  if (step === "confirm") {
    return (
      <Panel label="Confirm Conversion" tick="yellow">
        <div className="space-y-4">
          <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow/8 border border-yellow/25">
            <AlertTriangle className="w-4 h-4 text-yellow flex-shrink-0 mt-0.5" />
            <p className="font-mono text-[11px] text-text leading-relaxed">
              Converting <span className="font-bold text-yellow">{amtNum} {from}</span>
              {" "}(~${usdValue.toFixed(2)}) into <span className="font-bold text-yellow">{to}</span>
              {gaining > 0 && <> — expected ~{gaining.toFixed(6)} {to}</>}.
            </p>
          </div>
          <p className="font-mono text-[10px] text-muted-fg">
            Agent runs a live quote first and aborts if price impact exceeds 5%. On-chain swaps are irreversible.
          </p>
          {rateAge > 60 && (
            <p className="font-mono text-[10px] text-yellow">
              Rate fetched {Math.floor(rateAge / 60)}m {rateAge % 60}s ago — price may have shifted.
            </p>
          )}
          {error && <p className="font-mono text-[11px] text-red">{error}</p>}
          <div className="flex gap-2">
            <Button onClick={confirm} disabled={loading}
              className="flex-1 bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer disabled:opacity-50 flex items-center gap-2">
              <ArrowDownUp className="w-4 h-4" />
              {loading ? "Queuing…" : "Yes, convert"}
            </Button>
            <Button variant="outline" onClick={() => setStep("form")} disabled={loading}
              className="flex-1 border-border text-muted-fg hover:text-text cursor-pointer">
              Cancel
            </Button>
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <Panel label="Convert" tick="cyan">
      <div className="space-y-1.5">
        <div className="bg-bg border border-border rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-muted-fg">Converting</span>
            <button onClick={() => setAmount(maxFrom > 0 ? String(maxFrom) : "")}
              className="font-mono text-[11px] text-muted-fg hover:text-cyan cursor-pointer">
              Balance: {balanceOf(from, wallet).toFixed(4)} {from}
            </button>
          </div>
          <div className="flex items-center gap-3">
            <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0" min="0" step="any"
              className="border-0 bg-transparent px-0 h-auto text-[28px] font-bold font-display text-text shadow-none focus-visible:ring-0" />
            <TokenPill value={from} onChange={pickFrom} />
          </div>
          <p className="font-mono text-[11px] text-muted-fg">
            {fromPrice > 0 ? `($${usdValue.toFixed(2)})` : "(—)"}
          </p>
        </div>

        <div className="relative flex justify-center" style={{ height: 0 }}>
          <button onClick={flip} aria-label="Flip tokens"
            className="absolute -top-4 z-10 h-9 w-9 rounded-full bg-elevated border border-border flex items-center justify-center text-muted-fg hover:text-cyan hover:border-cyan/40 transition-colors cursor-pointer">
            <ArrowDownUp className="w-4 h-4" />
          </button>
        </div>

        <div className="bg-bg border border-border rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-muted-fg">Gaining</span>
            <span className="font-mono text-[11px] text-muted-fg">
              Balance: {balanceOf(to, wallet).toFixed(4)} {to}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex-1 text-[28px] font-bold font-display text-text truncate">
              {gaining > 0 ? gaining.toFixed(6) : "0.0"}
            </span>
            <TokenPill value={to} onChange={pickTo} />
          </div>
        </div>

        <p className="font-mono text-[11px] text-muted-fg pt-2 px-1">
          {rateLoading ? "Fetching rate…"
            : rate > 0 ? `1 ${from} = ${rate.toFixed(6)} ${to}`
            : "Rate unavailable"}
        </p>

        {error && <p className="font-mono text-[11px] text-red px-1">{error}</p>}

        <Button onClick={() => { if (!amtValid || from === to) return; setError(""); setStep("confirm"); }}
          disabled={!amtValid || from === to}
          className="w-full mt-2 bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer disabled:opacity-50">
          Confirm
        </Button>
      </div>
    </Panel>
  );
}

// ── Deposit QR ───────────────────────────────────────────────────────────────
// Separate component so useEffect fires after THIS element mounts — the ref is
// always set by the time the effect runs, avoiding the portal timing race.

function DepositQR({ address }: { address: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, address, {
      width: 160,
      color: { dark: "#000000", light: "#ffffff" },
      errorCorrectionLevel: "M",
    }).catch(() => {});
  }, [address]);

  return <canvas ref={canvasRef} className="rounded-xl" />;
}

// ── Main dialog ───────────────────────────────────────────────────────────────

type Props = {
  open: boolean;
  onClose: () => void;
  initialTab?: FundingTab;
};

export function FundingDialog({ open, onClose, initialTab = "deposit" }: Props) {
  const [tab, setTab] = useState<FundingTab>(initialTab);
  const [copied, setCopied] = useState(false);

  const address = useQuery(api.walletState.getAddress) ?? "";

  // Reset to initialTab when dialog opens
  useEffect(() => {
    if (open) setTab(initialTab);
  }, [open, initialTab]);

  const copy = () => {
    if (!address) return;
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="panel border-border sm:max-w-[520px] w-[95vw] max-h-[90vh] overflow-y-auto rounded-2xl p-0">
        {/* Header */}
        <DialogHeader className="px-5 pt-5 pb-0">
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
            TWAK Self-Custody · BSC
          </div>
          <DialogTitle className="font-display text-[20px] font-bold tracking-wide text-text">
            Wallet
          </DialogTitle>
        </DialogHeader>

        <div className="px-5 pb-5 space-y-4">
          {/* Tab bar */}
          <div className="flex gap-1 p-1 bg-elevated rounded-xl border border-border">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={cn(
                  "flex-1 font-mono text-[11px] font-bold py-1.5 rounded-lg transition-colors cursor-pointer",
                  tab === id
                    ? "bg-bg text-text border border-border shadow-sm"
                    : "text-muted-fg hover:text-text",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Deposit tab */}
          {tab === "deposit" && (
            <Panel label="BSC Deposit Address" tick="green">
              {!address ? (
                <p className="font-mono text-[12px] text-muted-fg py-4 text-center">
                  Address loads after first agent cycle…
                </p>
              ) : (
                <div className="space-y-4">
                  <p className="font-mono text-[11px] text-muted-fg">
                    Send USDT (BEP-20) or BNB directly to this address.{" "}
                    <span className="text-yellow font-bold">BSC chain only — do not send from Ethereum mainnet.</span>
                  </p>
                  <div className="flex justify-center">
                    <DepositQR address={address} />
                  </div>
                  <div className="bg-bg border border-border rounded-lg px-3 py-2 flex items-center gap-2">
                    <span className="font-mono text-[11px] text-text truncate flex-1">{address}</span>
                    <button onClick={copy} className="flex-shrink-0 text-muted-fg hover:text-green transition-colors cursor-pointer">
                      {copied ? <Check className="w-4 h-4 text-green" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                  <Button onClick={copy} className="w-full bg-green text-[#04140c] font-bold hover:bg-green/80 cursor-pointer flex items-center gap-2">
                    {copied ? <><Check className="w-4 h-4" /> Copied!</> : <><Copy className="w-4 h-4" /> Copy Address</>}
                  </Button>
                  <div className="font-mono text-[10px] text-muted-fg space-y-1">
                    <div className="flex items-center justify-between">
                      <span>USDT (BEP-20)</span><span className="text-text">Trading capital</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>BNB</span><span className="text-yellow">Gas — keep ≥ 0.005</span>
                    </div>
                  </div>
                </div>
              )}
            </Panel>
          )}

          {/* Buy tab */}
          {tab === "buy" && (
            <Panel label="Buy Crypto with Card" tick="cyan">
              <div className="space-y-4 py-2">
                <p className="font-mono text-[12px] text-muted-fg leading-relaxed">
                  Purchase USDT or BNB directly to your self-custody wallet using a credit card or bank transfer via Onramper.
                </p>
                <div className="bg-elevated border border-border rounded-xl p-4 space-y-2">
                  <p className="font-mono text-[11px] text-muted-fg">Your wallet address:</p>
                  <p className="font-mono text-[12px] text-text break-all">{address || "Loading…"}</p>
                </div>
                <Button
                  className="w-full bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer flex items-center gap-2"
                  onClick={() =>
                    window.open(
                      `https://onramper.com/?wallets=BSC:${address}&defaultCrypto=USDT_BSC`,
                      "_blank",
                      "noopener,noreferrer",
                    )
                  }
                  disabled={!address}
                >
                  <ExternalLink className="w-4 h-4" />
                  Buy via Onramper →
                </Button>
                <p className="font-mono text-[10px] text-muted-fg text-center">
                  Onramper supports 150+ payment methods in 180+ countries. KYC may be required.
                </p>
              </div>
            </Panel>
          )}

          {/* Convert tab */}
          {tab === "convert" && <ConvertTab />}

          {/* Withdraw tab */}
          {tab === "withdraw" && <WithdrawTab />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
