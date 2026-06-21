"""
pytest bootstrap for the agent runtime tests.

Puts the repo root (so `import agent` works) and `core/` (so `from backtest…`
works) on sys.path. Run from repo root with the core venv:

    core/.venv/Scripts/python.exe -m pytest agent/tests -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core"
for p in (str(_ROOT), str(_CORE)):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(autouse=True)
def _no_real_twak_subprocess(monkeypatch):
    """Never spawn the real `twak` CLI during tests.

    `DecisionLoop._finalise()` takes a best-effort wallet snapshot that constructs
    a real `TwakCli()` and shells out (default subprocess timeout 120s). In the full
    suite that call hangs on the network — fast in isolation, but stacking 60-120s
    stalls across every loop test. We stub the subprocess seam so any un-mocked twak
    call fails fast; the snapshot block already swallows the error ("wallet balance
    is display-only; never block the cycle"). Tests that exercise twak directly mock
    `TwakCli._run`, so the subprocess is never reached and they are unaffected.
    """
    import agent.twak_cli as _twak_mod

    def _blocked(*_a, **_k):
        raise FileNotFoundError("twak subprocess disabled in tests")

    monkeypatch.setattr(_twak_mod.subprocess, "run", _blocked)
