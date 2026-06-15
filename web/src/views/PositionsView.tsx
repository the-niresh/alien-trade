import { AnimatePresence } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { PositionCard } from "../components/PositionCard";
import { Skeleton } from "@/components/ui/skeleton";

export function PositionsView() {
  const positions = useQuery(api.positions.open);

  if (positions === undefined) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-5">
          <h1 className="font-grotesk text-xl font-bold">Positions</h1>
          <Skeleton className="h-5 w-16 bg-elevated" />
        </div>
        <div className="grid grid-cols-3 gap-4 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full bg-surface border border-border rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-8 text-center gap-3">
        <div className="text-[52px]">👽</div>
        <h2 className="font-grotesk text-[18px] font-bold">Watching the market</h2>
        <p className="text-[14px] text-muted-fg max-w-xs">
          No open positions — the agent is flat and waiting for a high-conviction setup.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <h1 className="font-grotesk text-xl font-bold">Positions</h1>
        <span className="text-[13px] text-muted-fg">{positions.length} open</span>
      </div>
      <div className="grid grid-cols-3 gap-4 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
        <AnimatePresence>
          {positions.map((p) => <PositionCard key={p._id} position={p} />)}
        </AnimatePresence>
      </div>
    </div>
  );
}
