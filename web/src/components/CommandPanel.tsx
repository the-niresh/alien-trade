import { useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { withToken } from "../lib/control";
import type { SponsorControl } from "../lib/sponsorRegistry";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const BADGE: Record<string, string> = {
  scored:   "bg-green/12 text-green border-green/25",
  neutral:  "bg-border/40 text-muted-fg border-border",
  operator: "bg-yellow/12 text-yellow border-yellow/25",
};

const BADGE_LABEL: Record<string, string> = {
  scored: "SCORED", neutral: "READ", operator: "OPERATOR",
};

type Props = { control: SponsorControl };

export function ControlCard({ control }: Props) {
  const enqueue = useMutation(api.agentCommands.enqueue);
  const recentCmds = useQuery(api.agentCommands.list, { limit: 5 });
  const lastCmd = recentCmds?.find((c) => c.command_type === control.commandType);

  const statusColor: Record<string, string> = {
    queued: "text-cyan", running: "text-yellow", done: "text-green", failed: "text-red",
  };

  const fire = async (params: Record<string, unknown>) => {
    await enqueue(withToken({ command_type: control.commandType!, params: JSON.stringify(params) }));
  };

  return (
    <div className="panel p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-display text-[13px] font-bold text-text">{control.label}</span>
            <span className={cn("font-mono text-[9px] border rounded px-1.5 py-0.5 uppercase tracking-widest", BADGE[control.scoringImpact])}>
              {BADGE_LABEL[control.scoringImpact]}
            </span>
            <span className="font-mono text-[9px] text-muted-fg/60 border border-border/30 rounded px-1.5 py-0.5">{control.sponsor}</span>
          </div>
          <p className="font-mono text-[11px] text-muted-fg leading-relaxed line-clamp-2">{control.description}</p>
        </div>
      </div>

      {control.transport === "imperative" && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="outline" className="border-yellow/30 text-yellow bg-yellow/5 hover:bg-yellow/10 cursor-pointer w-full">
              Run
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="panel border-border">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-text font-display">{control.label}</AlertDialogTitle>
              <AlertDialogDescription className="text-muted-fg text-[13px] leading-relaxed">
                {control.description}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-yellow text-black font-bold hover:bg-yellow/80"
                onClick={() => fire({})}
              >
                Queue Command
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {lastCmd && (
        <div className="flex items-center gap-2 pt-1">
          <span className="font-mono text-[10px] text-muted-fg">Last:</span>
          <span className={cn("font-mono text-[10px]", statusColor[lastCmd.status] ?? "text-muted-fg")}>
            {lastCmd.status}
          </span>
          {lastCmd.error && (
            <span className="font-mono text-[10px] text-red/70 truncate">{lastCmd.error.slice(0, 40)}</span>
          )}
        </div>
      )}
    </div>
  );
}
