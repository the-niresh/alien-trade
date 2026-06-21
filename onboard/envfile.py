"""Merge updates into a dotenv file in place (never clobber unrelated keys)."""
import os
import stat
from pathlib import Path


def upsert_env(path: str | Path, updates: dict[str, str]) -> None:
    """Update or append KEY=value lines in `path`, preserving everything else.
    Creates the file (chmod 600) if missing. Skips keys whose value is empty."""
    p = Path(path)
    updates = {k: v for k, v in updates.items() if v not in (None, "")}
    lines = p.read_text().splitlines() if p.exists() else []
    seen: set[str] = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}"
                seen.add(key)
    for key, val in updates.items():
        if key not in seen:
            lines.append(f"{key}={val}")
    p.write_text("\n".join(lines) + "\n")
    p.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
