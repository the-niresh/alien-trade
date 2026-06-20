"""
Telegram two-way bot (Step 8.9 enhanced).

Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env.local.
Absent → complete no-op (no background thread, every call returns immediately).

Usage:
    bot = TelegramBot(bridge=convex_bridge)
    bot.register_command("equity", lambda args: "floor: $500")
    bot.start()                      # start background polling thread

    bot.send("Alert text")           # fire-and-forget notification
    bot.send_approval(               # message with inline buttons
        "Apply confidence 0.6?",
        on_approve=lambda: write_forecast(0.6),
        on_reject=None,
        timeout_s=300,
    )
    bot.stop()                       # graceful shutdown
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)

_warned_once = False


@dataclass
class _Pending:
    on_approve: Optional[Callable[[], None]]
    on_reject: Optional[Callable[[], None]]
    expires: float


class TelegramBot:
    """Send-only + long-polling Telegram bot. Never raises."""

    def __init__(self, bridge=None) -> None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if token and chat_id:
            self._base = f"https://api.telegram.org/bot{token}"
            self._chat_id = chat_id
            self._enabled = True
        else:
            self._enabled = False
            global _warned_once
            if not _warned_once:
                log.warning(
                    "TelegramBot: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"
                    " — alerts and commands disabled"
                )
                _warned_once = True

        self._bridge = bridge
        self._pending: dict[int, _Pending] = {}
        self._lock = threading.Lock()
        self._commands: dict[str, Callable[[str], Optional[str]]] = {}
        self._register_builtins()
        self._offset = 0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # ── properties ───────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background polling thread (idempotent)."""
        if not self._enabled or self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="telegram-poll"
        )
        self._thread.start()
        log.info("TelegramBot: polling started")

    def stop(self) -> None:
        self._stop.set()

    # ── public API ───────────────────────────────────────────────────────────

    def send(self, text: str, reply_markup: Optional[dict] = None) -> Optional[int]:
        """Send a plain or button message. Returns message_id or None on error."""
        if not self._enabled:
            return None
        payload: dict = {"chat_id": self._chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        return self._post("sendMessage", payload)

    def send_approval(
        self,
        text: str,
        on_approve: Optional[Callable[[], None]] = None,
        on_reject: Optional[Callable[[], None]] = None,
        timeout_s: float = 300.0,
        approve_label: str = "Approve",
        reject_label: str = "Reject",
    ) -> None:
        """Send a message with Approve / Reject inline buttons.
        on_approve / on_reject fire at most once when the user taps.
        After timeout_s with no response, on_reject fires (if set).
        Requires bot.start() to be called first for button callbacks to work.
        """
        if not self._enabled:
            return
        markup = {
            "inline_keyboard": [[
                {"text": f"✅ {approve_label}", "callback_data": "approve"},
                {"text": f"❌ {reject_label}",  "callback_data": "reject"},
            ]]
        }
        msg_id = self.send(text, reply_markup=markup)
        if msg_id is None:
            return
        with self._lock:
            self._pending[msg_id] = _Pending(
                on_approve=on_approve,
                on_reject=on_reject,
                expires=time.time() + timeout_s,
            )

    def register_command(
        self, cmd: str, handler: Callable[[str], Optional[str]]
    ) -> None:
        """Register a custom /slash command.
        handler(args: str) -> reply text (return None to send nothing).
        """
        self._commands[cmd.lower().lstrip("/")] = handler

    # ── built-in commands ────────────────────────────────────────────────────

    def _register_builtins(self) -> None:
        for name, fn in [
            ("start",  self._cmd_start),
            ("help",   self._cmd_help),
            ("status", self._cmd_status),
            ("halt",   self._cmd_halt),
            ("resume", self._cmd_resume),
            ("pause",  self._cmd_pause),
        ]:
            self._commands[name] = fn

    def _cmd_start(self, _: str) -> str:
        return "Alien-Trade bot connected. /help for commands."

    def _cmd_help(self, _: str) -> str:
        builtins = "/status  /halt  /resume  /pause  /help"
        custom = "  ".join(
            "/" + k for k in sorted(self._commands)
            if k not in {"start", "help", "status", "halt", "resume", "pause"}
        )
        return "Built-in: " + builtins + (("\nCustom: " + custom) if custom else "")

    def _cmd_status(self, _: str) -> str:
        if self._bridge is None:
            return "Status: bridge not wired."
        try:
            halted = self._bridge.is_halted()
            return (
                f"Agent status\n"
                f"Halted: {'YES' if halted else 'no'}"
            )
        except Exception:  # noqa: BLE001
            return "Status: error reading bridge."

    def _cmd_halt(self, _: str) -> str:
        if self._bridge is None:
            return "Halt: bridge not wired."
        try:
            self._bridge.set_halted(True)
            return "Kill switch activated. Agent halted."
        except Exception:  # noqa: BLE001
            return "Halt failed — bridge error."

    def _cmd_resume(self, _: str) -> str:
        if self._bridge is None:
            return "Resume: bridge not wired."
        try:
            self._bridge.set_halted(False)
            return "Kill switch cleared. Agent resuming."
        except Exception:  # noqa: BLE001
            return "Resume failed — bridge error."

    def _cmd_pause(self, _: str) -> str:
        if self._bridge is None:
            return "Pause: bridge not wired."
        try:
            self._bridge.set_agent_paused(True)
            return "Advisory agents paused."
        except Exception:  # noqa: BLE001
            return "Pause: bridge error or method not available."

    # ── polling internals ────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._expire_pending()
                updates = self._get_updates(poll_timeout=30)
                for upd in updates:
                    self._offset = upd["update_id"] + 1
                    try:
                        self._process_update(upd)
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                self._stop.wait(5)  # back off on persistent errors

    def _expire_pending(self) -> None:
        now = time.time()
        with self._lock:
            expired = [mid for mid, p in self._pending.items() if now > p.expires]
            for mid in expired:
                p = self._pending.pop(mid)
                if p.on_reject:
                    try:
                        p.on_reject()
                    except Exception:  # noqa: BLE001
                        pass

    def _process_update(self, upd: dict) -> None:
        if "message" in upd:
            self._handle_message(upd["message"])
        elif "callback_query" in upd:
            self._handle_callback(upd["callback_query"])

    def _is_authorized(self, msg_or_cb: dict) -> bool:
        """Only the configured operator chat may issue commands. Without this, ANY
        Telegram user who finds the bot could send /halt and stop the live agent."""
        chat = (msg_or_cb.get("chat") or (msg_or_cb.get("message") or {}).get("chat") or {})
        sender_chat_id = str(chat.get("id", "")).strip()
        return sender_chat_id != "" and sender_chat_id == str(self._chat_id).strip()

    def _handle_message(self, msg: dict) -> None:
        if not self._is_authorized(msg):
            return  # silently ignore commands from any non-operator chat
        text = (msg.get("text") or "").strip()
        if not text.startswith("/"):
            return
        parts = text.split()
        # strip @BotName suffix (e.g. /halt@MyBot)
        raw_cmd = parts[0].lstrip("/").split("@")[0].lower()
        args = " ".join(parts[1:])
        handler = self._commands.get(raw_cmd)
        if handler:
            try:
                reply = handler(args)
                if reply:
                    self.send(reply)
            except Exception:  # noqa: BLE001
                pass

    def _handle_callback(self, cq: dict) -> None:
        if not self._is_authorized(cq):
            return  # only the operator chat may approve/reject pending actions
        cq_id = cq.get("id", "")
        msg_id = (cq.get("message") or {}).get("message_id")
        data = (cq.get("data") or "").strip()
        self._answer_callback(cq_id)
        if msg_id is None:
            return
        with self._lock:
            pending = self._pending.pop(msg_id, None)
        if pending is None or time.time() > pending.expires:
            return
        fn = pending.on_approve if data == "approve" else pending.on_reject
        if fn:
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass

    # ── Telegram HTTP helpers ────────────────────────────────────────────────

    def _get_updates(self, poll_timeout: int = 30) -> list[dict]:
        payload = {
            "offset": self._offset,
            "timeout": poll_timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self._base}/getUpdates", data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=poll_timeout + 5) as resp:
            body = json.loads(resp.read().decode())
        return body.get("result") or []

    def _post(self, method: str, payload: dict) -> Optional[int]:
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self._base}/{method}", data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode())
            return (body.get("result") or {}).get("message_id")
        except Exception:  # noqa: BLE001
            return None

    def _answer_callback(self, cq_id: str) -> None:
        self._post("answerCallbackQuery", {"callback_query_id": cq_id})


# Backward-compat alias
TelegramNotifier = TelegramBot
