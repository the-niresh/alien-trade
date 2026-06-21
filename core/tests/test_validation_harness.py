import numpy as np
import pandas as pd
import pytest

from backtest.deflated_sharpe import deflated_sharpe
from backtest.holdout import holdout_split
from backtest.score_sim import score_sim


def test_deflated_sharpe_in_unit_interval():
    p = deflated_sharpe(sr=0.15, n_trials=10, n_obs=500, skew=0.0, kurt=3.0)
    assert 0.0 <= p <= 1.0


def test_deflated_sharpe_drops_with_more_trials():
    few = deflated_sharpe(sr=0.15, n_trials=2, n_obs=500, skew=0.0, kurt=3.0)
    many = deflated_sharpe(sr=0.15, n_trials=1000, n_obs=500, skew=0.0, kurt=3.0)
    assert many < few          # more trials → harder to clear → lower probability


def test_score_sim_returns_distribution():
    rng = np.random.default_rng(0)
    equity = pd.Series(10000 * np.cumprod(1 + rng.normal(0.0005, 0.01, 120)))
    dist = score_sim(equity, window_days=7, n_boot=200, bars_per_day=1)
    assert len(dist) == 200
    assert np.isfinite(dist).all()


def test_holdout_reserves_tail_and_use_once():
    df = pd.DataFrame({"close": np.arange(200.0), "ts": np.arange(200)})
    split = holdout_split(df, holdout_days=50, bars_per_day=1)
    assert len(split.train) == 150 and len(split.holdout) == 50
    # holdout is the TAIL
    assert split.holdout["close"].iloc[0] == 150.0
    _ = split.use_once()              # first use ok
    with pytest.raises(RuntimeError):
        split.use_once()              # second use forbidden (anti-snooping)
