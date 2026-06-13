from scripts.freeze_guard import decide

ALLOW = ["core/strategy/**", "docs/AUTONOMY.md", "agent/tests/**"]


def test_inside_allowed():
    assert decide("core/strategy/combined.py", ALLOW, "Edit")["permission"] == "allow"


def test_nested_glob_allowed():
    assert decide("agent/tests/test_x.py", ALLOW, "Write")["permission"] == "allow"


def test_outside_blocked():
    assert decide("convex/config.ts", ALLOW, "Edit")["permission"] == "deny"


def test_exact_file_allowed():
    assert decide("docs/AUTONOMY.md", ALLOW, "Edit")["permission"] == "allow"


def test_push_blocked():
    assert decide("", ALLOW, "Bash", cmd="git push origin main")["permission"] == "deny"


def test_systemctl_blocked():
    assert decide("", ALLOW, "Bash", cmd="systemctl restart alien-trade")["permission"] == "deny"


def test_twak_blocked():
    assert decide("", ALLOW, "Bash", cmd="twak swap --token ETH")["permission"] == "deny"


def test_convex_deploy_blocked():
    assert decide("", ALLOW, "Bash", cmd="bunx convex deploy")["permission"] == "deny"


def test_harmless_bash_allowed():
    assert decide("", ALLOW, "Bash", cmd="pytest core/tests -q")["permission"] == "allow"
