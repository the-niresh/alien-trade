"""Deflated Sharpe Ratio (López de Prado) — AWAKE_SPRINT §4.4.

Adjusts an observed Sharpe for the number of trials (multiplicity), the sample
length, and the return distribution's skew/kurtosis. A survivor of 100 trials may be
luck; DSR counts the trials. Stdlib only (statistics.NormalDist) — no new dependency.

A thesis ships only if it clears DSR AND the >=4/5-asset objective gate.
"""
from __future__ import annotations

import math
from statistics import NormalDist

_N = NormalDist()
_EULER = 0.5772156649015329  # Euler–Mascheroni


def expected_max_sharpe(n_trials: int, n_obs: int) -> float:
    """Expected maximum Sharpe across `n_trials` independent strategies under the
    null (each SR ~ N(0, 1/n_obs)). Rises with n_trials → the bar a real edge must clear."""
    n_trials = max(int(n_trials), 1)
    sigma = 1.0 / math.sqrt(max(n_obs, 2))
    if n_trials == 1:
        return 0.0
    a = _N.inv_cdf(1.0 - 1.0 / n_trials)
    b = _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return sigma * ((1.0 - _EULER) * a + _EULER * b)


def deflated_sharpe(sr: float, n_trials: int, n_obs: int, skew: float = 0.0,
                    kurt: float = 3.0) -> float:
    """Probability the observed Sharpe `sr` is real (not the best of `n_trials` flukes).
    Returns a value in [0, 1]; drops as n_trials rises."""
    sr0 = expected_max_sharpe(n_trials, n_obs)
    denom = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr
    if denom <= 0:
        denom = 1e-9
    z = (sr - sr0) * math.sqrt(max(n_obs - 1, 1)) / math.sqrt(denom)
    return min(1.0, max(0.0, _N.cdf(z)))
