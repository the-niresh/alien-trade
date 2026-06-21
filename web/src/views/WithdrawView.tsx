import { useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";
import { AlertTriangle, ArrowUpFromLine, Check } from "lucide-react";

type Step = "form" | "confirm" | "done";

const GAS_BUFFER_BNB = 0.005;
const USDT_BUFFER    = 0.5;

type WalletToken = { symbol: string; balance: number };
type WalletFields = { usdt: number; eth: number; bnb: number; tokens?: WalletToken[] };

const STATIC_FALLBACK: WalletToken[] = [
  { symbol: "BNB",  balance: 0 },
  { symbol: "USDT", balance: 0 },
  { symbol: "ETH",  balance: 0 },
];

function resolveTokens(w: WalletFields | null | undefined): WalletToken[] {
  if (!w) return STATIC_FALLBACK;
  if (w.tokens && w.tokens.length > 0) return w.tokens;
  const list: WalletToken[] = [
    { symbol: "BNB",  balance: w.bnb },
    { symbol: "USDT", balance: w.usdt },
    { symbol: "ETH",  balance: w.eth },
  ];
  return list.some(t => t.balance > 0) ? list : STATIC_FALLBACK;
}

function maxOf(symbol: string, tokens: WalletToken[]): number {
  const bal = tokens.find(t => t.symbol === symbol)?.balance ?? 0;
  if (symbol === "BNB")  return Math.max(0, bal - GAS_BUFFER_BNB);
  if (symbol === "USDT") return Math.max(0, bal - USDT_BUFFER);
  return bal;
}

export function WithdrawView() {
  const wallet  = useQuery(api.walletState.get);
  const enqueue = useMutation(api.agentCommands.enqueue);

  const tokens = resolveTokens(wallet as WalletFields | null | undefined);

  const [token, setToken]     = useState(tokens[0]?.symbol ?? "USDT");
  const [amount, setAmount]   = useState("");
  const [toAddr, setToAddr]   = useState("");
  const [step, setStep]       = useState<Step>("form");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const maxAmount = maxOf(token, tokens);
  const addrValid = /^0x[0-9a-fA-F]{40}$/.test(toAddr.trim());
  const amtNum    = parseFloat(amount) || 0;
  const amtValid  = amtNum > 0 && amtNum <= maxAmount;

  const submit = () => {
    if (!addrValid || !amtValid) return;
    setStep("confirm");
    setError("");
  };

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

  return (
    <div className="max-w-[520px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-purple rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--purple)" }} />
          TWAK Self-Custody · BSC
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Withdraw</h1>
      </div>

      {step === "done" ? (
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
      ) : step === "confirm" ? (
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
      ) : (
        <Panel label="Withdrawal Form" tick="purple">
          <div className="space-y-4">
            {/* Token selector */}
            <div>
              <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest block mb-1.5">
                Token
              </label>
              <div className="flex flex-wrap gap-2">
                {tokens.map((t) => (
                  <button
                    key={t.symbol}
                    onClick={() => { setToken(t.symbol); setAmount(""); }}
                    className={cn(
                      "px-3 font-mono text-[12px] font-bold py-1.5 rounded-lg border transition-colors cursor-pointer",
                      token === t.symbol
                        ? "bg-purple/15 border-purple/40 text-purple"
                        : "border-border text-muted-fg hover:text-text",
                    )}
                  >
                    {t.symbol}
                  </button>
                ))}
              </div>
            </div>

            {/* Balance display */}
            {wallet && (
              <p className="font-mono text-[11px] text-muted-fg">
                Available:{" "}
                <span className="text-text font-bold">{maxAmount.toFixed(6)} {token}</span>
                {token === "USDT" && (
                  <span className="text-muted-fg"> (keeping $0.50 buffer)</span>
                )}
                {token === "BNB" && (
                  <span className="text-yellow"> (keeping 0.005 for gas)</span>
                )}
              </p>
            )}

            {/* Amount */}
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

            {/* Destination address */}
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
              onClick={submit}
              disabled={!addrValid || !amtValid}
              className="w-full bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowUpFromLine className="w-4 h-4" />
              Review Withdrawal
            </Button>
          </div>
        </Panel>
      )}
    </div>
  );
}
