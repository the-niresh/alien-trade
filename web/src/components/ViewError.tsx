import { Button } from "@/components/ui/button";

type Props = { error: Error; resetErrorBoundary: () => void };

export function ViewError({ error, resetErrorBoundary }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center gap-4">
      <div className="text-4xl">⚠️</div>
      <h2 className="font-grotesk text-lg font-bold text-red">View crashed</h2>
      <p className="text-[13px] text-muted-fg max-w-xs font-mono">{error.message}</p>
      <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text"
        onClick={resetErrorBoundary}>
        Reload view
      </Button>
    </div>
  );
}
