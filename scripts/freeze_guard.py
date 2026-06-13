#!/usr/bin/env python3
"""PreToolUse hook: enforce the frozen allowlist + block irreversible commands.

Reads the hook event JSON on stdin, decides allow/deny. On deny: exit 2 with the
reason on stderr (Claude Code hook protocol). This is the ONLY hard guarantee while
the ralph loop runs under --dangerously-skip-permissions: a prompt-injected thesis or
a model slip cannot edit outside docs/FROZEN_ALLOWLIST.txt, push, restart the live
agent, or touch money/mainnet.
"""
import fnmatch
import json
import re
import sys
from pathlib import Path

ALLOWLIST_FILE = Path(__file__).resolve().parent.parent / "docs" / "FROZEN_ALLOWLIST.txt"
BLOCK_CMD = re.compile(r"\b(git\s+push|systemctl|twak\s+(swap|compete)|bunx\s+convex\s+deploy)\b")


def _globs() -> list[str]:
    if not ALLOWLIST_FILE.exists():
        return []
    return [l.strip() for l in ALLOWLIST_FILE.read_text().splitlines()
            if l.strip() and not l.startswith("#")]


def decide(path: str, globs: list[str], tool: str, cmd: str = "") -> dict:
    if tool == "Bash":
        if BLOCK_CMD.search(cmd):
            return {"permission": "deny", "reason": f"blocked command (loop is gated): {cmd[:80]}"}
        return {"permission": "allow"}
    if tool in ("Edit", "Write", "NotebookEdit"):
        if any(fnmatch.fnmatch(path, g) for g in globs):
            return {"permission": "allow"}
        return {"permission": "deny",
                "reason": f"{path} is outside docs/FROZEN_ALLOWLIST.txt — request approval (AT-REQ)"}
    return {"permission": "allow"}


def main() -> None:
    ev = json.load(sys.stdin)
    tool = ev.get("tool_name", "")
    ti = ev.get("tool_input", {})
    path = ti.get("file_path", "") or ti.get("notebook_path", "")
    try:  # normalize to repo-relative
        path = str(Path(path).resolve().relative_to(Path.cwd()))
    except Exception:
        pass
    out = decide(path, _globs(), tool, cmd=ti.get("command", ""))
    if out["permission"] == "deny":
        sys.stderr.write(out["reason"])
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
