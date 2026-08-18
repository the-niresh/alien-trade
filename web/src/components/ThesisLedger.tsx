import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, { cls: string; label: string }> = {
  validated: { cls: "border-green/30 bg-green/10 text-green", label: "VALIDATED" },
  FALSIFIED: { cls: "border-red/30 bg-red/10 text-red",       label: "FALSIFIED" },
  untested:  { cls: "border-border bg-elevated text-muted-fg", label: "UNTESTED" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.untested;
  return (
    <span className={cn("font-mono text-[10px] font-bold tracking-[0.12em] px-2 py-0.5 rounded border flex-shrink-0", s.cls)}>
      {s.label}
    </span>
  );
}

function fmt(n: number | null | undefined, d = 3): string {
  return n === null || n === undefined ? "-" : n.toFixed(d);
}

export default function ThesisLedger() {
  const theses = useQuery(api.thesisLedger.recent, { limit: 12 });

  return (
    <Panel
      label={<>Thesis Ledger <span className="text-border-hi normal-case tracking-normal lowercase">· science in public</span></>}
      tick="cyan"
      className="mb-3"
    >
      {theses === undefined ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full bg-elevated rounded-xl" />
          ))}
        </div>
      ) : theses.length === 0 ? (
        <p className="font-mono text-[12px] text-muted-fg">// no theses tested yet - the loop logs every trial here</p>
      ) : (
        <div className="flex flex-col gap-2">
          {theses.map((t: any) => (
            <div key={t.thesis_id ?? t._id} className="bg-bg/50 border border-border rounded-xl px-3 py-2.5 hover:border-border-hi transition-colors">
              <div className="flex justify-between gap-2 mb-1.5">
                <span className="text-[13px] font-semibold text-text/90">{t.claim}</span>
                <StatusBadge status={t.status} />
              </div>
              <div className="flex gap-4 font-mono text-[11px] text-muted-fg">
                <span>obj <b className="text-text">{fmt(t.oos_objective)}</b></span>
                <span>DSR <b className="text-text">{fmt(t.deflated_sharpe, 2)}</b></span>
                {t.regime ? <span>regime <b className="text-text">{t.regime}</b></span> : null}
              </div>
              {t.source && (
                <div className="font-mono text-[10px] text-muted-fg mt-1">↳ {t.source}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
