import { useEffect, useState } from "react";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { withToken } from "@/lib/control";
import { ArrowDownUp, Check, AlertTriangle } from "lucide-react";

type Token = "BNB" | "USDT" | "ETH";
type Step = "form" | "confirm" | "done";

const TOKENS: Token[] = ["BNB", "USDT", "ETH"];
const GAS_BUFFER_BNB = 0.005;
const USDT_BUFFER = 0.5;
const TOKEN_DOT: Record<Token, string> = {
  BNB: "var(--yellow)", USDT: "var(--green)", ETH: "var(--cyan)",
};

type WalletFields = { usdt: number; eth: number; bnb: number };

function balanceOf(t: Token, w: WalletFields | null): number {
  if (!w) return 0;
  return t === "USDT" ? w.usdt : t === "ETH" ? w.eth : w.bnb;
}

// Max spendable in token units, leaving the required buffer.
function maxOf(t: Token, w: WalletFields | null): number {
  const bal = balanceOf(t, w);
  if (t === "BNB") return Math.max(0, bal - GAS_BUFFER_BNB);
  if (t === "USDT") return Math.max(0, bal - USDT_BUFFER);
  return bal; // ETH: no gas reservation
}

function TokenPill({ value, onChange }: { value: Token; onChange: (t: Token) => void }) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v as Token)}>
      <SelectTrigger className="w-auto gap-2 bg-elevated border-border rounded-full px-3 py-1.5 font-mono text-[13px] font-bold text-text focus:ring-cyan">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: TOKEN_DOT[value] }} />
          <SelectValue />
        </span>
      </SelectTrigger>
      <SelectContent className="bg-elevated border-border">
        {TOKENS.map((t) => (
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

export function ConvertPanel() {
  const wallet  = useQuery(api.walletState.get) as WalletFields | null;
  const enqueue = useMutation(api.agentCommands.enqueue);
  const quote   = useAction(api.twak.convertQuote);

  const [from, setFrom]               = useState<Token>("BNB");
  const [to, setTo]                   = useState<Token>("USDT");
  const [amount, setAmount]           = useState("");
  const [fromPrice, setFromPrice]     = useState(0);
  const [toPrice, setToPrice]         = useState(0);
  const [rateLoading, setRateLoading] = useState(false);
  const [rateAge, setRateAge] = useState(0); // seconds since last rate fetch
  const [step, setStep]               = useState<Step>("form");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");

  // Fetch spot prices whenever the pair changes (depends on tokens, not amount).
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
      .finally(() => {
        if (!cancelled) {
          setRateLoading(false);
          setRateAge(0); // reset age when fetch completes
        }
      });
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

  const flip = () => { setFrom(to); setTo(from); setAmount(""); };
  const pickFrom = (t: Token) => { setAmount(""); if (t === to) setTo(from); setFrom(t); };
  const pickTo   = (t: Token) => { if (t === from) setFrom(to); setTo(t); };

  const submit = () => {
    if (!amtValid || from === to) return;
    setError("");
    setStep("confirm");
  };

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
            Convert queued. The agent quotes it, checks price impact, then executes via TWAK in the next command cycle.
          </p>
          <p className="font-mono text-[11px] text-muted-fg text-center">
            Check the Trackers view to see its status.
          </p>
          <Button
            variant="outline"
            className="border-border text-muted-fg mt-2 cursor-pointer"
            onClick={() => { setStep("form"); setAmount(""); }}
          >
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
            The agent runs a live quote first and aborts if price impact exceeds 5%. On-chain swaps are irreversible.
          </p>
          {rateAge > 60 && (
            <p className="font-mono text-[10px] text-yellow">
              Rate fetched {Math.floor(rateAge / 60)}m {rateAge % 60}s ago — price may have shifted.
            </p>
          )}
          {error && <p className="font-mono text-[11px] text-red">{error}</p>}
          <div className="flex gap-2">
            <Button
              onClick={confirm}
              disabled={loading}
              className="flex-1 bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowDownUp className="w-4 h-4" />
              {loading ? "Queuing…" : "Yes, convert"}
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
    <Panel label="Convert" tick="cyan">
      <div className="space-y-1.5">
        {/* Converting (From) card */}
        <div className="bg-bg border border-border rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-muted-fg">Converting</span>
            <button
              onClick={() => setAmount(maxFrom > 0 ? String(maxFrom) : "")}
              className="font-mono text-[11px] text-muted-fg hover:text-cyan cursor-pointer"
            >
              Balance: {balanceOf(from, wallet).toFixed(4)} {from}
            </button>
          </div>
          <div className="flex items-center gap-3">
            <Input
              type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0" min="0" step="any"
              className="border-0 bg-transparent px-0 h-auto text-[28px] font-bold font-display text-text shadow-none focus-visible:ring-0"
            />
            <TokenPill value={from} onChange={pickFrom} />
          </div>
          <p className="font-mono text-[11px] text-muted-fg">
            {fromPrice > 0 ? `($${usdValue.toFixed(2)})` : "(—)"}
          </p>
        </div>

        {/* Flip button straddling the two cards */}
        <div className="relative flex justify-center" style={{ height: 0 }}>
          <button
            onClick={flip}
            aria-label="Flip tokens"
            className="absolute -top-4 z-10 h-9 w-9 rounded-full bg-elevated border border-border flex items-center justify-center text-muted-fg hover:text-cyan hover:border-cyan/40 transition-colors cursor-pointer"
          >
            <ArrowDownUp className="w-4 h-4" />
          </button>
        </div>

        {/* Gaining (To) card */}
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

        {/* Rate */}
        <p className="font-mono text-[11px] text-muted-fg pt-2 px-1">
          {rateLoading ? "Fetching rate…"
            : rate > 0 ? `1 ${from} = ${rate.toFixed(6)} ${to}`
            : "Rate unavailable"}
        </p>

        {error && <p className="font-mono text-[11px] text-red px-1">{error}</p>}

        <Button
          onClick={submit}
          disabled={!amtValid || from === to}
          className="w-full mt-2 bg-cyan text-[#040e14] font-bold hover:bg-cyan/80 cursor-pointer disabled:opacity-50"
        >
          Confirm
        </Button>
      </div>
    </Panel>
  );
}
