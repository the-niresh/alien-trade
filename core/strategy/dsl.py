"""Declarative rule DSL (AWAKE_SPRINT §4.3) — the loop's throughput lever and the
SAFE compile target for distilled thesis cards (§4.2). A thesis's `proposed_rule` is
compiled here, NEVER eval'd: only a whitelisted grammar over known indicator
primitives is allowed, so prompt-injected corpus text cannot run arbitrary code.

Grammar: comparisons (>, <, >=, <=, ==), boolean and/or/not, arithmetic (+ - * /),
numeric constants, and whitelisted identifiers:
  close open high low volume        — raw columns
  ema<N> sma<N>                      — moving averages of close, period N
  roc / roc<N>                       — rate of change (default 10)
  atr<N>                             — average true range (default 14)
  funding sentiment regime          — optional columns (0.0 if absent)
"""
from __future__ import annotations

import ast
import re
from typing import Callable

import numpy as np
import pandas as pd


class DSLError(ValueError):
    """Raised on any identifier or syntax outside the whitelisted grammar."""


_RAW_COLUMNS = {"close", "open", "high", "low", "volume"}
_OPTIONAL_COLUMNS = {"funding", "sentiment", "regime"}
_EMA = re.compile(r"^ema(\d+)$")
_SMA = re.compile(r"^sma(\d+)$")
_ROC = re.compile(r"^roc(\d*)$")
_ATR = re.compile(r"^atr(\d+)$")


def _resolve(name: str, df: pd.DataFrame) -> pd.Series:
    if name in _RAW_COLUMNS:
        return df[name].astype(float)
    if name in _OPTIONAL_COLUMNS:
        return df[name].astype(float) if name in df.columns else pd.Series(
            np.zeros(len(df)), index=df.index
        )
    if m := _EMA.match(name):
        return df["close"].ewm(span=int(m.group(1)), adjust=False).mean()
    if m := _SMA.match(name):
        return df["close"].rolling(int(m.group(1)), min_periods=1).mean()
    if m := _ROC.match(name):
        period = int(m.group(1)) if m.group(1) else 10
        return df["close"].pct_change(period).fillna(0.0)
    if m := _ATR.match(name):
        period = int(m.group(1))
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()
    raise DSLError(f"unknown identifier: {name!r}")


_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Compare,
    ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq,
    ast.Name, ast.Load, ast.Constant,
)


def _valid_name(name: str) -> bool:
    return (
        name in _RAW_COLUMNS or name in _OPTIONAL_COLUMNS
        or bool(_EMA.match(name) or _SMA.match(name) or _ROC.match(name) or _ATR.match(name))
    )


def _validate(tree: ast.AST) -> None:
    """Static pass: reject disallowed nodes + unknown identifiers at compile time."""
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise DSLError(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and not _valid_name(node.id):
            raise DSLError(f"unknown identifier: {node.id!r}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise DSLError("only numeric constants allowed")


def _eval(node: ast.AST, df: pd.DataFrame):
    if not isinstance(node, _ALLOWED_NODES):
        raise DSLError(f"disallowed syntax: {type(node).__name__}")
    if isinstance(node, ast.Expression):
        return _eval(node.body, df)
    if isinstance(node, ast.Name):
        return _resolve(node.id, df)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise DSLError("only numeric constants allowed")
        return node.value
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, df) for v in node.values]
        out = vals[0]
        for v in vals[1:]:
            out = (out & v) if isinstance(node.op, ast.And) else (out | v)
        return out
    if isinstance(node, ast.UnaryOp):
        v = _eval(node.operand, df)
        return (~v) if isinstance(node.op, ast.Not) else (-v)
    if isinstance(node, ast.BinOp):
        l, r = _eval(node.left, df), _eval(node.right, df)
        op = node.op
        if isinstance(op, ast.Add):
            return l + r
        if isinstance(op, ast.Sub):
            return l - r
        if isinstance(op, ast.Mult):
            return l * r
        if isinstance(op, ast.Div):
            return l / r
    if isinstance(node, ast.Compare):
        if len(node.ops) != 1:
            raise DSLError("chained comparisons not supported")
        l, r = _eval(node.left, df), _eval(node.comparators[0], df)
        op = node.ops[0]
        if isinstance(op, ast.Gt):
            return l > r
        if isinstance(op, ast.Lt):
            return l < r
        if isinstance(op, ast.GtE):
            return l >= r
        if isinstance(op, ast.LtE):
            return l <= r
        if isinstance(op, ast.Eq):
            return l == r
        if isinstance(op, ast.NotEq):
            return l != r
    raise DSLError(f"disallowed syntax: {type(node).__name__}")


def _compile_expr(src: str) -> Callable[[pd.DataFrame], pd.Series]:
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise DSLError(f"parse error: {e}") from e
    _validate(tree)
    return lambda df: _eval(tree, df)


def compile_rule(rule: dict) -> Callable[[pd.DataFrame], pd.Series]:
    """Compile {'entry': expr, 'exit': expr} into f(df) -> position Series (0/1).
    Long-only: enter (→1) when flat and entry is true; exit (→0) when exit is true."""
    entry_fn = _compile_expr(rule["entry"])
    exit_fn = _compile_expr(rule["exit"])

    def run(df: pd.DataFrame) -> pd.Series:
        entry = np.asarray(entry_fn(df)).astype(bool)
        exit_ = np.asarray(exit_fn(df)).astype(bool)
        pos = np.zeros(len(df), dtype=int)
        held = 0
        for i in range(len(df)):
            if held and exit_[i]:
                held = 0
            elif not held and entry[i] and not exit_[i]:
                held = 1
            pos[i] = held
        return pd.Series(pos, index=df.index)

    return run
