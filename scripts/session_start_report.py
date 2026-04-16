#!/usr/bin/env python3
"""SessionStart hook: inject structural fitness summary into Claude's context.

Fires once per session. Outputs JSON with `additionalContext` so Claude sees
the current fitness score and top issues before writing any code. Also reads
.structure-log.txt to report the trend across recent sessions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import find_config


def read_trend(log_path: Path, n: int = 5) -> list[int]:
    """Read the last n scores from the trend log."""
    if not log_path.exists():
        return []
    scores: list[int] = []
    try:
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []
    for line in lines[-n:]:
        # Format: "2026-04-16T12:00:00 score=83"
        if "score=" in line:
            try:
                scores.append(int(line.split("score=")[1].split()[0]))
            except (ValueError, IndexError):
                continue
    return scores


def format_trend(scores: list[int]) -> str:
    if len(scores) < 2:
        return ""
    direction = "↑" if scores[-1] > scores[0] else "↓" if scores[-1] < scores[0] else "→"
    return f"Trend (last {len(scores)} sessions): {scores[0]} {direction} {scores[-1]}"


def main() -> int:
    config_path = find_config()
    if config_path is None:
        # No config, nothing to inject.
        return 0

    project_root = config_path.parent
    audit_script = Path(__file__).parent / "audit.py"

    # Run audit in JSON mode
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

    if result.returncode not in (0, 1):  # audit returns 1 for low scores, still valid
        return 0

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return 0

    score = report.get("score", 0)
    grade = report.get("grade", "unknown")
    penalties = report.get("penalties_by_category", {})
    top_3 = sorted(penalties.items(), key=lambda kv: -kv[1])[:3]

    # Trend from the log
    log_path = project_root / ".structure-log.txt"
    trend_scores = read_trend(log_path)
    trend_line = format_trend(trend_scores)

    lines = [
        f"Structure fitness: {score}/100 ({grade})",
    ]
    if trend_line:
        lines.append(trend_line)

    if top_3:
        lines.append("")
        lines.append("Biggest penalties:")
        for category, penalty in top_3:
            lines.append(f"  - {category}: -{penalty} points")
        lines.append("")
        lines.append(
            "Run `python scripts/audit.py` for details. When creating files, "
            "follow the conventions in .structure.yaml."
        )

    message = "\n".join(lines)
    output = {"additionalContext": message}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
