import { AnimatePresence } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { PositionCard } from "../components/PositionCard";
import { RecentTrades } from "../components/RecentTrades";
import { Skeleton } from "@/components/ui/skeleton";

function ViewHeading({ title, meta }: { title: string; meta?: string }) {
  return (
    <div className="flex items-baseline gap-3 mb-5">
      <h1 className="font-display text-[20px] font-bold tracking-wide">{title}</h1>
      {meta && <span className="font-mono text-[11px] text-muted-fg">{meta}</span>}
    </div>
  );
}

export function PositionsView() {
  const positions = useQuery(api.positions.open);

  if (positions === undefined) {
    return (
      <div className="max-w-[1180px] mx-auto">
        <ViewHeading title="Positions" />
        <div className="grid grid-cols-3 gap-4 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full bg-surface border border-border rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="max-w-[1180px] mx-auto space-y-8">
        <div className="flex flex-col items-center py-12 px-8 text-center gap-5">
          <div className="radar" aria-hidden />
          <div className="space-y-2">
            <h2 className="font-display text-[19px] font-bold tracking-wide">Scanning the market</h2>
            <p className="text-[14px] text-muted-fg max-w-xs leading-relaxed">
              Flat — no open positions. The agent is waiting for a high-conviction setup before deploying capital.
            </p>
            <p className="font-mono text-[11px] text-green/70 tracking-[0.16em] uppercase pt-1">
              <span className="animate-pulse">▮</span> standing by
            </p>
          </div>
        </div>
        <RecentTrades />
      </div>
    );
  }

  return (
    <div className="max-w-[1180px] mx-auto space-y-8">
      <div>
        <ViewHeading title="Positions" meta={`${positions.length} open`} />
        <div className="grid grid-cols-3 gap-4 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
          <AnimatePresence>
            {positions.map((p) => <PositionCard key={p._id} position={p} />)}
          </AnimatePresence>
        </div>
      </div>
      <RecentTrades />
    </div>
  );
}
