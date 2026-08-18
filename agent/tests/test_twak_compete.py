"""
twak on-chain agent registration - pin the exact CLI args. Registration is a
one-shot on-chain action; wrong args fail silently, so the command shape is worth
locking down. No real `twak` binary needed (we stub `_run`).
"""
from __future__ import annotations

from agent.twak_cli import TwakCli


def test_compete_register_and_status_args(monkeypatch):
    calls = []
    cli = TwakCli(chain="bsc", binary="/fake/twak")
    monkeypatch.setattr(cli, "_run", lambda *a, **k: calls.append(a) or {"ok": True})

    # NOTE: `twak compete` does NOT accept --chain (unlike wallet/swap). Passing it
    # is rejected by the CLI, so compete_register/status must omit it.
    cli.compete_register()
    assert calls[-1] == ("compete", "register", "--json")

    cli.compete_status()
    assert calls[-1] == ("compete", "status", "--json")
