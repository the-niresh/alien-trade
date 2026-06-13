from onboard.envfile import upsert_env


def test_upsert_updates_and_appends(tmp_path):
    p = tmp_path / ".env.local"
    p.write_text("EXISTING=keep\nMODE=paper\n# comment\n")
    upsert_env(p, {"MODE": "mainnet", "NEW_KEY": "val", "EMPTY": ""})
    out = p.read_text()
    assert "EXISTING=keep" in out          # untouched
    assert "MODE=mainnet" in out           # updated in place
    assert "MODE=paper" not in out
    assert "NEW_KEY=val" in out            # appended
    assert "EMPTY" not in out              # empty values skipped
    assert "# comment" in out              # comments preserved
    assert oct(p.stat().st_mode)[-3:] == "600"


def test_upsert_creates_missing(tmp_path):
    p = tmp_path / ".env.local"
    upsert_env(p, {"A": "1"})
    assert p.read_text().strip() == "A=1"
