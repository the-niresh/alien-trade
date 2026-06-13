from pathlib import Path

from onboard.credentials import ensure_pairing_token, load_token


def test_token_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    t1 = ensure_pairing_token()
    assert len(t1) >= 32
    assert load_token() == t1                    # idempotent
    assert ensure_pairing_token() == t1          # does not regenerate
    cred = Path(tmp_path) / ".alien-trade" / "credentials.json"
    assert oct(cred.stat().st_mode)[-3:] == "600"


def test_load_token_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert load_token() is None                  # nothing stored yet
