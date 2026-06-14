"""Thin CLI to test one thesis and print its trial-registry row (AWAKE_SPRINT §4.4).

The loop (or a human) runs this to turn a DSL rule into a reproducible THESIS_LEDGER
row. Print-only by design — no live state is mutated; paste the row into
docs/THESIS_LEDGER.md. All evaluation logic lives in (and is tested via)
research/evaluate.py.

    python -m research.run_thesis --id T-006 \
        --entry "close>ema100*1.05 and regime>0" --exit "close<ema100*0.90" \
        --claim "regime-gated deep-hysteresis trend" --source "..." --n-trials 6
"""
from __future__ import annotations

import argparse

from research.evaluate import LEDGER_HEADER, evaluate_thesis, format_ledger_row


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Evaluate one thesis → ledger row")
    ap.add_argument("--id", required=True)
    ap.add_argument("--entry", required=True, help="DSL entry expression")
    ap.add_argument("--exit", required=True, dest="exit_", help="DSL exit expression")
    ap.add_argument("--claim", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--threshold", type=float, default=0.0, help="objective bar (cash=0.0)")
    ap.add_argument("--min-beat", type=int, default=4)
    ap.add_argument("--n-trials", type=int, default=1,
                    help="total theses tried so far (multiplicity → Deflated Sharpe)")
    ap.add_argument("--header", action="store_true", help="also print the table header")
    args = ap.parse_args(argv)

    rule = {"entry": args.entry, "exit": args.exit_}
    ev = evaluate_thesis(rule, threshold=args.threshold, min_beat=args.min_beat,
                         n_trials=args.n_trials)

    if args.header:
        print(LEDGER_HEADER)
    print(format_ledger_row(args.id, args.claim, args.source, ev))

    # Per-asset detail to stderr-free stdout footer (for the loop's evidence capture).
    for r in ev.per_asset:
        print(f"#   {r.asset:5} obj={r.objective:+.4f} sortino={r.sortino:+.4f} "
              f"ret={r.total_return:+.4%} maxDD={r.max_drawdown:+.4%} fills={r.n_fills}")
    if ev.holdout:
        print(f"#   HOLDOUT obj={ev.holdout['objective']:+.4f} "
              f"beat_cash={ev.holdout['n_beat_cash']}/5  DSR={ev.deflated_sharpe:.3f}")


if __name__ == "__main__":
    main()
