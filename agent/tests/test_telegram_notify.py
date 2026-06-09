"""TelegramBot — unit tests (send-only + polling + buttons)."""
from __future__ import annotations

import json
import threading
import time
from unittest.mock import MagicMock, call, patch

import pytest

from agent.notify import TelegramBot, TelegramNotifier


# ── disabled when no env ──────────────────────────────────────────────────────

def test_disabled_when_no_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    bot = TelegramBot()
    assert not bot.enabled


def test_enabled_when_both_set(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    bot = TelegramBot()
    assert bot.enabled


# ── TelegramNotifier is the same class ───────────────────────────────────────

def test_notifier_alias():
    assert TelegramNotifier is TelegramBot


# ── send ──────────────────────────────────────────────────────────────────────

def test_send_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    bot = TelegramBot()
    with patch("urllib.request.urlopen") as mock_open:
        bot.send("hello")
        mock_open.assert_not_called()


def test_send_posts_to_telegram(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mytoken")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    bot = TelegramBot()
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"result": {"message_id": 7}}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        mid = bot.send("test alert")
    assert mid == 7


def test_send_swallows_network_errors(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        result = bot.send("should not raise")
    assert result is None


# ── send_approval ─────────────────────────────────────────────────────────────

def test_send_approval_registers_pending(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"result": {"message_id": 99}}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    approved = []
    with patch("urllib.request.urlopen", return_value=mock_resp):
        bot.send_approval("Approve?", on_approve=lambda: approved.append(1))
    assert 99 in bot._pending


def test_send_approval_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    bot = TelegramBot()
    bot.send_approval("Approve?", on_approve=lambda: None)  # must not raise
    assert len(bot._pending) == 0


# ── callback handling ─────────────────────────────────────────────────────────

def _bot_with_pending(monkeypatch, msg_id: int):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    approved = []
    rejected = []
    from agent.notify import _Pending
    bot._pending[msg_id] = _Pending(
        on_approve=lambda: approved.append("yes"),
        on_reject=lambda: rejected.append("no"),
        expires=time.time() + 300,
    )
    return bot, approved, rejected


def test_approve_callback_fires_on_approve(monkeypatch):
    bot, approved, rejected = _bot_with_pending(monkeypatch, 55)
    with patch.object(bot, "_answer_callback"):
        bot._handle_callback({
            "id": "cq1", "data": "approve",
            "message": {"message_id": 55},
        })
    assert approved == ["yes"] and rejected == []


def test_reject_callback_fires_on_reject(monkeypatch):
    bot, approved, rejected = _bot_with_pending(monkeypatch, 66)
    with patch.object(bot, "_answer_callback"):
        bot._handle_callback({
            "id": "cq2", "data": "reject",
            "message": {"message_id": 66},
        })
    assert rejected == ["no"] and approved == []


def test_expired_pending_calls_on_reject(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    rejected = []
    from agent.notify import _Pending
    bot._pending[77] = _Pending(
        on_approve=None,
        on_reject=lambda: rejected.append("expired"),
        expires=time.time() - 1,   # already expired
    )
    bot._expire_pending()
    assert rejected == ["expired"]
    assert 77 not in bot._pending


# ── slash commands ────────────────────────────────────────────────────────────

def test_builtin_help_lists_commands(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    reply = bot._cmd_help("")
    assert "/status" in reply and "/halt" in reply


def test_custom_command_registration(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    bot.register_command("ping", lambda args: f"pong {args}")
    assert "ping" in bot._commands
    assert bot._commands["ping"]("world") == "pong world"


def test_custom_command_in_help(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    bot.register_command("equity", lambda _: "floor: $500")
    assert "equity" in bot._cmd_help("")


def test_halt_command_calls_bridge(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bridge = MagicMock()
    bot = TelegramBot(bridge=bridge)
    bot._cmd_halt("")
    bridge.set_halted.assert_called_once_with(True)


def test_resume_command_calls_bridge(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bridge = MagicMock()
    bot = TelegramBot(bridge=bridge)
    bot._cmd_resume("")
    bridge.set_halted.assert_called_once_with(False)


def test_pause_command_calls_bridge(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bridge = MagicMock()
    bot = TelegramBot(bridge=bridge)
    bot._cmd_pause("")
    bridge.set_agent_paused.assert_called_once_with(True)


def test_status_command_no_bridge(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    bot = TelegramBot()
    reply = bot._cmd_status("")
    assert "bridge" in reply.lower()


# ── loop integration ──────────────────────────────────────────────────────────

def test_loop_notifier_wired_on_equity_floor_halt(monkeypatch):
    """DecisionLoop calls notifier.send_approval on equity-floor halt."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    notifier = MagicMock()
    notifier.enabled = True

    bridge = MagicMock()
    bridge.is_halted.return_value = False
    bridge.get_equity_floor.return_value = 1_000.0
    bridge.get_forecast_state.return_value = None
    bridge.get_sentiment.return_value = None

    from agent.loop import DecisionLoop
    from backtest.engine import Bar
    from strategy.combined import StrategyParams

    bar = Bar(timestamp=0, open=100.0, high=105.0, low=95.0, close=100.0, volume=1e6)
    loop = DecisionLoop(
        feed=MagicMock(),
        strategy=lambda h: None,
        executor=MagicMock(),
        bridge=bridge,
        params=StrategyParams(),
        initial_capital=500.0,
        notifier=notifier,
    )
    loop.ledger = MagicMock()
    loop.ledger.mark.return_value = 500.0
    loop.ledger.roll_day.return_value = None
    loop.ledger.daily_loss_usd.return_value = 0.0
    loop.ledger.open_exposure.return_value = 0.0
    loop.ledger.drawdown_pct.return_value = 0.0
    loop.ledger.peak_equity = 1000.0
    loop.ledger.consecutive_losses = 0
    loop.ledger.realized_pnl_total = 0.0

    loop.run_cycle([bar])

    # send_approval is preferred; plain send is the fallback
    called = notifier.send_approval.called or notifier.send.called
    assert called
