import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, { colorClass: string; label: string }> = {
  validated: { colorClass: "border-green/30 bg-green/10 text-green", label: "VALIDATED" },
  FALSIFIED: { colorClass: "border-red/30 bg-red/10 text-red",       label: "FALSIFIED" },
  untested:  { colorClass: "border-border bg-elevated text-muted-fg", label: "untested" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.untested;
  return (
    <Badge variant="outline" className={cn("text-[11px] font-bold flex-shrink-0", s.colorClass)}>
      {s.label}
    </Badge>
  );
}

function fmt(n: number | null | undefined, d = 3): string {
  return n === null || n === undefined ? "—" : n.toFixed(d);
}

export default function ThesisLedger() {
  const theses = useQuery(api.thesisLedger.recent, { limit: 12 });

  return (
    <Card className="bg-surface border-border mb-3">
      <CardHeader className="pb-3">
        <h2 className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">
          Thesis ledger{" "}
          <span className="opacity-50 font-normal normal-case tracking-normal">· science in public</span>
        </h2>
      </CardHeader>
      <CardContent>
        {theses === undefined ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full bg-elevated rounded-xl" />
            ))}
          </div>
        ) : theses.length === 0 ? (
          <p className="text-muted-fg text-[13px]">
            No theses tested yet — the loop logs every trial here.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {theses.map((t: any) => (
              <div key={t.thesis_id ?? t._id} className="bg-elevated border border-border rounded-xl px-3 py-2.5">
                <div className="flex justify-between gap-2 mb-1.5">
                  <span className="text-[13px] font-semibold">{t.claim}</span>
                  <StatusBadge status={t.status} />
                </div>
                <div className="flex gap-4 text-[12px] text-text/80">
                  <span>obj <b>{fmt(t.oos_objective)}</b></span>
                  <span>DSR <b>{fmt(t.deflated_sharpe, 2)}</b></span>
                  {t.regime ? <span>regime <b>{t.regime}</b></span> : null}
                </div>
                {t.source && (
                  <div className="text-[11px] text-muted-fg mt-1">↳ {t.source}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
