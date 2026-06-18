import { useEffect, useRef, useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Copy, Check, ExternalLink } from "lucide-react";
import QRCode from "qrcode";

type Tab = "deposit" | "buy";

export function DepositView() {
  const wallet  = useQuery(api.walletState.get);
  const address = wallet?.address ?? "";
  const [tab, setTab]       = useState<Tab>("deposit");
  const [copied, setCopied] = useState(false);
  const canvasRef           = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (tab === "deposit" && address && canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, address, {
        width: 180,
        color: { dark: "#000000", light: "#ffffff" },
        errorCorrectionLevel: "M",
      }).catch(() => {/* ignore */});
    }
  }, [tab, address]);

  const copy = () => {
    if (!address) return;
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-[520px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          TWAK Self-Custody · BSC
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Fund Wallet</h1>
      </div>

      {/* Tab selector */}
      <div className="flex gap-1 p-1 bg-elevated rounded-xl border border-border">
        {(["deposit", "buy"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={cn(
              "flex-1 font-mono text-[12px] font-bold py-1.5 rounded-lg transition-colors cursor-pointer capitalize",
              tab === t ? "bg-bg text-text border border-border shadow-sm" : "text-muted-fg hover:text-text",
            )}>
            {t === "deposit" ? "Deposit" : "Buy Crypto"}
          </button>
        ))}
      </div>

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
                <canvas ref={canvasRef} className="rounded-xl" />
              </div>
              <div className="bg-bg border border-border rounded-lg px-3 py-2 flex items-center gap-2">
                <span className="font-mono text-[11px] text-text truncate flex-1">{address}</span>
                <button onClick={copy}
                  className="flex-shrink-0 text-muted-fg hover:text-green transition-colors cursor-pointer">
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
                  "noopener,noreferrer"
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
    </div>
  );
}
