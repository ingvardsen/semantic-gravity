#!/usr/bin/env python3
"""Stop hook: append current fitness score to .structure-log.txt.

Runs when Claude finishes responding. Creates a trend line so the next
SessionStart hook can show whether structure is improving or decaying.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import find_config


def main() -> int:
    config_path = find_config()
    if config_path is None:
        return 0

    project_root = config_path.parent
    audit_script = Path(__file__).parent / "audit.py"

    try:
        result = subprocess.run(
            [sys.executable, str(audit_script), "--json", "--config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=project_root,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    if result.returncode not in (0, 1):
        return 0

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return 0

    score = report.get("score", 0)
    grade = report.get("grade", "unknown")

    log_path = project_root / ".structure-log.txt"
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    entry = f"{timestamp} score={score} grade={grade}\n"

    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
