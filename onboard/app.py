"""Alien-Trade onboarding wizard (Textual TUI).

A full-screen branded device-flow: welcome → dependency check → API keys (with live
red/green probes) → trading mode → risk caps → Telegram → pairing token + QR → launch.
The pairing token is the shared secret (cockpit gate + Convex control guard). On Launch
the wizard merges everything into .env.local and prints the start commands.

Run: `python -m onboard` (install.sh hands off here after installing deps).
"""
from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from onboard.art import ALIEN_ART
from onboard.credentials import ensure_pairing_token
from onboard.envfile import upsert_env
from onboard.probes import probe_anthropic, probe_convex, probe_telegram

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env.local"


def _probe_badge(ok: bool, detail: str) -> str:
    return f"[green]✓ {detail}[/]" if ok else f"[red]✗ {detail}[/]"


class WelcomeScreen(Screen):
    BINDINGS = [("enter", "start", "Start")]

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="welcome-box"):
                yield Static(ALIEN_ART, id="alien")
                yield Static("👽  ALIEN-TRADE", id="brand")
                yield Static("Autonomous BSC trading agent — onboarding")
                yield Static("")
                yield Static("Press [b]Enter[/] (or click Start) to begin.")
                yield Button("Start", variant="primary", id="start")

    def action_start(self) -> None:
        self.app.push_screen(DepCheckScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.action_start()


class DepCheckScreen(Screen):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[b]Dependency check[/]")
            for mod in ("textual", "httpx", "qrcode", "pandas", "numpy"):
                ok = _mod_present(mod)
                yield Static(f"  {mod:<10} {_probe_badge(ok, 'installed' if ok else 'missing')}")
            yield Button("Next", variant="primary", id="next")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            self.app.push_screen(KeysScreen())


class KeysScreen(Screen):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[b]API keys[/] — fill what you have, then Test")
            yield Input(placeholder="CONVEX_URL", id="convex_url")
            yield Input(placeholder="ANTHROPIC_API_KEY", password=True, id="anthropic")
            yield Static("", id="keys_status")
            yield Button("Test", id="test")
            yield Button("Next", variant="primary", id="next")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test":
            cu = self.query_one("#convex_url", Input).value
            ak = self.query_one("#anthropic", Input).value
            rc, ra = probe_convex(cu), probe_anthropic(ak)
            self.query_one("#keys_status", Static).update(
                f"Convex {_probe_badge(rc.ok, rc.detail)}   Anthropic {_probe_badge(ra.ok, ra.detail)}"
            )
        elif event.button.id == "next":
            self.app.cfg["CONVEX_URL"] = self.query_one("#convex_url", Input).value.strip()
            self.app.cfg["ANTHROPIC_API_KEY"] = self.query_one("#anthropic", Input).value.strip()
            self.app.push_screen(TradingModeScreen())


class TradingModeScreen(Screen):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[b]Trading mode[/]")
            with RadioSet(id="mode"):
                yield RadioButton("paper (simulated, safe)", value=True, id="paper")
                yield RadioButton("testnet", id="testnet")
                yield RadioButton("mainnet (REAL FUNDS)", id="mainnet")
            yield Static("", id="mode_warn")
            yield Button("Next", variant="primary", id="next")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "next":
            return
        rs = self.query_one("#mode", RadioSet)
        mode = (rs.pressed_button.id if rs.pressed_button else "paper")
        if mode == "mainnet" and not getattr(self, "_confirmed", False):
            self._confirmed = True
            self.query_one("#mode_warn", Static).update(
                "[red]MAINNET trades real funds. Click Next again to confirm.[/]"
            )
            return
        self.app.cfg["TRADING_MODE"] = mode
        self.app.push_screen(RiskCapsScreen())


class RiskCapsScreen(Screen):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[b]Risk caps[/]")
            yield Input(value="2000", placeholder="max_position_usd", id="max_position_usd")
            yield Input(value="500", placeholder="daily_loss_limit_usd", id="daily_loss_limit_usd")
            yield Input(value="0.15", placeholder="max_drawdown_pct", id="max_drawdown_pct")
            yield Input(value="", placeholder="equity_floor (0 = off)", id="equity_floor")
            yield Button("Next", variant="primary", id="next")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            for k in ("max_position_usd", "daily_loss_limit_usd", "max_drawdown_pct", "equity_floor"):
                self.app.cfg[k.upper()] = self.query_one(f"#{k}", Input).value.strip()
            self.app.push_screen(TelegramScreen())


class TelegramScreen(Screen):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[b]Telegram alerts[/] (optional)")
            yield Input(placeholder="TELEGRAM_BOT_TOKEN", password=True, id="tg_token")
            yield Input(placeholder="TELEGRAM_CHAT_ID", id="tg_chat")
            yield Static("", id="tg_status")
            yield Button("Test", id="test")
            yield Button("Next", variant="primary", id="next")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        tok = self.query_one("#tg_token", Input).value
        chat = self.query_one("#tg_chat", Input).value
        if event.button.id == "test":
            r = probe_telegram(tok, chat)
            self.query_one("#tg_status", Static).update(_probe_badge(r.ok, r.detail))
        elif event.button.id == "next":
            self.app.cfg["TELEGRAM_BOT_TOKEN"] = tok.strip()
            self.app.cfg["TELEGRAM_CHAT_ID"] = chat.strip()
            self.app.push_screen(PairingScreen())


class PairingScreen(Screen):
    def compose(self) -> ComposeResult:
        from agent.qr import qr_string, resolve_url

        token = ensure_pairing_token()
        self.app.cfg["CONTROL_TOKEN"] = token
        pwa = resolve_url(self.app.cfg.get("PWA_URL", ""))
        link = f"{pwa}/#t={token}"
        with VerticalScroll():
            yield Static("[b]Pair your phone[/] — scan to open the cockpit, already paired")
            yield Static(qr_string(link), id="qr")
            yield Static(f"[dim]{link}[/]")
            yield Button("Next", variant="primary", id="next")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            self.app.push_screen(LaunchScreen())


class LaunchScreen(Screen):
    def compose(self) -> ComposeResult:
        upsert_env(ENV_PATH, self.app.cfg)
        with VerticalScroll():
            yield Static("[b][green]✓ Setup complete[/][/]")
            yield Static(f"Wrote {len(self.app.cfg)} settings to .env.local")
            yield Static("")
            yield Static("Start the agent:   [b]systemctl restart alien-trade[/]")
            yield Static("Open the cockpit:  [b]http://localhost:4173[/]")
            yield Label("")
            yield Button("Finish", variant="primary", id="finish")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "finish":
            self.app.exit()


class OnboardApp(App):
    TITLE = "Alien-Trade Onboarding"
    CSS = """
    #welcome-box { width: 44; padding: 1 2; align-horizontal: center; }
    #alien { width: auto; margin-bottom: 1; }
    #brand { text-style: bold; color: $accent; text-align: center; width: 100%; }
    Button { margin: 1 0; }
    Input { margin: 1 0; }
    """

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.cfg: dict[str, str] = {}

    def on_mount(self) -> None:
        self.push_screen(WelcomeScreen())


def _mod_present(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None
