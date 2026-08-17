"""
Accounting integrity — the backtest may never invent money.

These pin a bug that made every "risk engine ON" number in this repo wrong, in the
flattering direction, for months.

What happened: `RiskEngine` ran sell orders through the volatility-targeted *entry*
sizer, so an exit was sized from equity and volatility instead of from the position
actually held. The resulting sell was almost always larger than the position. The
backtest engine then credited the full requested proceeds to cash while flooring the
position at zero — so each oversized exit minted the difference. On 540 days of hourly
ETH data that added $46,814 of imaginary cash and turned a −16% strategy into a
reported +452% with a 0.45% max drawdown.

Nothing failed. No test broke, no exception was raised, and the equity curve looked
excellent. That is the shape of the worst class of bug in a measurement tool: it is
silent, and it lies in the direction you were hoping for.

Two invariants below, one per layer:
  1. The engine never creates cash on an oversized sell, whatever it is handed.
  2. The risk engine never asks to sell more than it holds.
"""
from __future__ import annotations

from backtest.engine import Bar, Order, run_backtest
from risk.engine import make_risk_strategy
from risk.guardrails import RiskConfig
from strategy.combined import make_strategy
from strategy.registry import STRATEGIES

_HOUR_MS = 3_600_000


def _bars(n: int, start: float = 100.0, step: float = 0.5) -> list[Bar]:
    """Gently rising bars — enough for ATR and EMA windows to warm up."""
    out = []
    for i in range(n):
        close = start + i * step
        out.append(Bar(timestamp=i * _HOUR_MS, open=close, high=close * 1.01,
                       low=close * 0.99, close=close, volume=1_000.0))
    return out


# ── 1. The engine cannot be talked into creating cash ─────────────────────────

def test_oversized_sell_does_not_create_cash():
    """Buy $1,000, then demand a $100,000 sell. Only $1,000-worth may be sold."""
    bars = _bars(6)
    calls = {"n": 0}

    def greedy(history: list[Bar]) -> Order | None:
        calls["n"] += 1
        bar = history[-1]
        if calls["n"] == 2:
            return Order(side="buy", size_usd=1_000.0, symbol="ETH", timestamp=bar.timestamp)
        if calls["n"] == 4:
            return Order(side="sell", size_usd=100_000.0, symbol="ETH", timestamp=bar.timestamp)
        return None

    res = run_backtest(bars, greedy, initial_capital=10_000.0)

    # The violation is recorded, not absorbed.
    assert res.oversized_sells == 1
    assert res.oversized_sell_usd > 90_000.0

    # Equity must be bounded by a long-only strategy on a rising market: it cannot
    # exceed starting capital plus the gain on the $1,000 that was actually at risk.
    assert res.equity_curve[-1] < 10_200.0, (
        f"engine minted cash: final equity {res.equity_curve[-1]:.2f}"
    )
    # And the position is flat, not negative.
    assert res.metrics["n_trades"] == 1


def test_buy_cannot_spend_cash_the_account_does_not_have():
    """
    Spot, long only, unlevered: a buy is bounded by settled cash.

    Without this the engine let cash go negative, so an over-trading strategy reported
    losses past 100%. The `contrarian` preset came out at −470% on real ETH history —
    not a bad result, an impossible one. Any number below −100% on a long-only account
    is a bug report, and the engine should be the thing that refuses it.
    """
    bars = _bars(30)

    def always_buy(history: list[Bar]) -> Order | None:
        bar = history[-1]
        return Order(side="buy", size_usd=5_000.0, symbol="ETH", timestamp=bar.timestamp)

    res = run_backtest(bars, always_buy, initial_capital=10_000.0)

    assert res.underfunded_buys > 0, "test is vacuous unless the account ran out of cash"
    # Long-only on a rising series: equity can grow, but it can never go negative and a
    # loss can never exceed the capital put in.
    assert min(res.equity_curve) >= 0.0, (
        f"equity went negative (min {min(res.equity_curve):.2f}) — the account borrowed"
    )
    assert res.metrics["total_return"] > -1.0, (
        f"reported {res.metrics['total_return'] * 100:.1f}% on a long-only account"
    )


def test_sell_with_no_position_is_a_noop():
    """A sell with nothing held must not fill, and must not fabricate a trade."""
    bars = _bars(5)

    def sell_only(history: list[Bar]) -> Order | None:
        bar = history[-1]
        return Order(side="sell", size_usd=500.0, symbol="ETH", timestamp=bar.timestamp)

    res = run_backtest(bars, sell_only, initial_capital=10_000.0)

    assert res.fills == []
    assert res.trades == []
    assert res.oversized_sells == len(bars)
    assert res.equity_curve[-1] == 10_000.0


def test_exact_size_sell_is_not_flagged():
    """Selling precisely what is held is legitimate and must not trip the counter."""
    bars = _bars(6)
    state: dict = {"n": 0, "units": 0.0}

    def exact(history: list[Bar]) -> Order | None:
        state["n"] += 1
        bar = history[-1]
        if state["n"] == 2:
            state["units"] = 1_000.0 / bar.close
            return Order(side="buy", size_usd=1_000.0, symbol="ETH", timestamp=bar.timestamp)
        if state["n"] == 4:
            # Sell strictly less than held so the slippage-adjusted fill price cannot
            # push the request marginally over the line.
            return Order(side="sell", size_usd=state["units"] * bar.close * 0.9,
                         symbol="ETH", timestamp=bar.timestamp)
        return None

    res = run_backtest(bars, exact, initial_capital=10_000.0)
    assert res.oversized_sells == 0


# ── 2. The risk engine sizes exits from the position, not from the vol target ──

def test_risk_engine_sizes_exits_from_the_position_not_the_vol_target():
    """
    The regression that started all this.

    Pre-fix, `RiskEngine` ran sell orders through `compute_position_size` — the
    volatility-targeted *entry* sizer — and emitted that number as the exit size. The
    result had no relationship to the position held. On 540 days of hourly ETH it made
    180 of 180 sells oversized and $46,814 of requested-but-unheld notional.

    This drives the risk engine directly with a stub inner strategy rather than the real
    one. The contract under test belongs to the risk engine, and a real strategy would
    only add the question of whether it happened to signal on this particular series.
    """
    cfg = RiskConfig()
    bars = _bars(40)
    calls = {"n": 0}

    def stub(history: list[Bar]) -> Order | None:
        """One entry, then keep asking to exit for the rest of the run."""
        calls["n"] += 1
        bar = history[-1]
        if calls["n"] == 20:
            return Order(side="buy", size_usd=200.0, symbol="ETH", timestamp=bar.timestamp)
        if calls["n"] >= 25:
            return Order(side="sell", size_usd=1e9, symbol="ETH", timestamp=bar.timestamp)
        return None

    engine = make_risk_strategy(stub, cfg, 10_000.0)
    emitted = [o for i in range(len(bars)) if (o := engine(bars[: i + 1])) is not None]

    buys = [o for o in emitted if o.side == "buy"]
    sells = [o for o in emitted if o.side == "sell"]
    assert buys, "test is vacuous unless an entry was emitted"
    assert sells, "test is vacuous unless an exit was emitted"

    # A single long entry can be closed exactly once. Pre-fix the exit size came from
    # the entry sizer, which never consults the position, so the engine happily emitted
    # a full-size sell on every remaining bar — selling a position it no longer had.
    assert len(sells) == 1, (
        f"{len(sells)} exits emitted for one entry — the engine is selling while flat "
        f"because exit size comes from the entry sizer, not the position"
    )

    # And the one real exit is bounded by the position, marked to market.
    total_bought_units = sum(o.size_usd for o in buys) / bars[19].close
    assert sells[0].size_usd <= total_bought_units * max(b.close for b in bars) + 1e-6


def test_risk_engine_does_not_veto_an_exit():
    """
    Guardrails gate entries, never exits. A rule that can block a sell is a rule that
    can trap capital in a losing position, which is the opposite of risk control.

    Pinned because the fix above moved `check_guardrails` and the $10 minimum notional
    inside the buy branch, and the reason for that needs to survive a future refactor.
    """
    cfg = RiskConfig()
    bars = _bars(40)
    calls = {"n": 0}

    def stub(history: list[Bar]) -> Order | None:
        calls["n"] += 1
        bar = history[-1]
        if calls["n"] == 20:
            return Order(side="buy", size_usd=200.0, symbol="ETH", timestamp=bar.timestamp)
        if calls["n"] >= 30:
            # A tiny exit — below the $10 minimum that gates entries.
            return Order(side="sell", size_usd=1.0, symbol="ETH", timestamp=bar.timestamp)
        return None

    engine = make_risk_strategy(stub, cfg, 10_000.0)
    emitted = [o for i in range(len(bars)) if (o := engine(bars[: i + 1])) is not None]

    assert any(o.side == "sell" for o in emitted), (
        "a small exit was vetoed — the entry minimum is gating sells"
    )
