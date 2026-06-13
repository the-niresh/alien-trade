import numpy as np
import pandas as pd
import pytest

from strategy.dsl import DSLError, compile_rule


def _df(n=200):
    # gently rising close so EMAs/ROC are well-defined
    close = pd.Series(np.linspace(100, 200, n))
    return pd.DataFrame({
        "open": close, "high": close * 1.01, "low": close * 0.99,
        "close": close, "volume": pd.Series(np.full(n, 1000.0)),
    })


def test_compile_returns_position_series():
    rule = compile_rule({"entry": "close>ema100 and roc>0", "exit": "close<ema50"})
    pos = rule(_df())
    assert len(pos) == 200
    assert set(np.unique(pos.dropna().values)).issubset({0, 1})
    assert pos.sum() > 0          # a rising series should hold long sometimes


def test_unknown_identifier_raises():
    with pytest.raises(DSLError):
        compile_rule({"entry": "close>moon_phase", "exit": "close<ema50"})


def test_no_arbitrary_calls():
    # function calls / attribute access are not part of the grammar
    with pytest.raises(DSLError):
        compile_rule({"entry": "__import__('os').system('x')", "exit": "close<ema50"})


def test_exit_flattens_position():
    # entry always true, exit always true → never accumulates a held position
    rule = compile_rule({"entry": "close>0", "exit": "close>0"})
    pos = rule(_df(50))
    assert pos.max() == 0
