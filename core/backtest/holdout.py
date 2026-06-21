"""Final untouched holdout (AWAKE_SPRINT §4.4).

Reserve the most-recent ~45–60 days, used EXACTLY ONCE at the very end on survivors,
never tuned against. `use_once()` raises on a second call so the discipline is
mechanical, not a promise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class HoldoutSplit:
    train: pd.DataFrame
    holdout: pd.DataFrame
    _used: bool = field(default=False, init=False)

    def use_once(self) -> pd.DataFrame:
        if self._used:
            raise RuntimeError(
                "holdout already used once — re-using it defeats the anti-snooping guard"
            )
        self._used = True
        return self.holdout


def holdout_split(df: pd.DataFrame, holdout_days: int = 50, bars_per_day: int = 1) -> HoldoutSplit:
    """Split into (train, holdout) reserving the final `holdout_days` of bars as the tail."""
    n_hold = min(holdout_days * bars_per_day, len(df))
    cut = len(df) - n_hold
    train = df.iloc[:cut].reset_index(drop=True)
    holdout = df.iloc[cut:].reset_index(drop=True)
    return HoldoutSplit(train=train, holdout=holdout)
