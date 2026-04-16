#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit calls that violate structural conventions.

Claude Code pipes JSON to stdin on PreToolUse for Write and Edit tools. We parse
the file_path, check it against .structure.yaml, and exit:
  0 — allow the write
  2 — block the write and surface the reason back to Claude

This is a deterministic gate. The agent can't silently drift away from conventions
because every file creation passes through here first.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONFIG_FILENAME, load_config, matches_case


def check_path(file_path: Path) -> tuple[bool, str]:
    """Return (allowed, reason). `reason` is empty when allowed."""
    try:
        config = load_config()
    except FileNotFoundError:
        # No config = no enforcement. Don't block.
        return True, ""

    # Only enforce inside source_root
    try:
        rel = file_path.resolve().relative_to(config.source_path.resolve())
    except ValueError:
        return True, ""

    # Only care about .py files
    if file_path.suffix != ".py":
        return True, ""

    # Test files and __init__ bypass domain prefix check but not case check
    stem = file_path.stem
    if stem == "__init__":
        return True, ""

    # Generic filename check
    if file_path.name in config.generic_filenames:
        return False, (
            f"Filename '{file_path.name}' is in the forbidden-generic list "
            f"(see {CONFIG_FILENAME}). Rename to describe its purpose, "
            f"e.g., {rel.parts[0] if len(rel.parts) > 1 else 'domain'}_<role>.py"
        )

    # Case check
    if not matches_case(stem, config.file_case):
        return False, (
            f"Filename '{file_path.name}' does not match "
            f"{config.file_case} convention required by {CONFIG_FILENAME}."
        )

    # Domain prefix check (only when file lives inside a domain directory)
    if config.domain_prefix and len(rel.parts) >= 2:
        domain = rel.parts[0]
        if not stem.startswith(f"{domain}_") and stem != domain:
            separator = "-" if config.file_case == "kebab-case" else "_"
            return False, (
                f"File '{rel}' is in domain '{domain}' but lacks the domain prefix. "
                f"Rename to '{domain}{separator}{file_path.name}' to stay discoverable via "
                f"`rg --files | rg {domain}{separator}`."
            )

    # Depth check
    depth = len(rel.parts)
    if depth > config.max_depth:
        return False, (
            f"File '{rel}' is at depth {depth}, exceeding max_depth={config.max_depth}. "
            f"Flatten by moving closer to {config.source_root}/ or splitting the domain."
        )

    return True, ""


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        # Malformed input — don't block, just warn.
        return 0

    tool_input = payload.get("tool_input", {})
    file_path_str = tool_input.get("file_path", "")
    if not file_path_str:
        return 0

    file_path = Path(file_path_str)
    allowed, reason = check_path(file_path)
    if allowed:
        return 0

    # Exit code 2 blocks the tool call. The reason goes to stderr, which Claude sees.
    print(f"semantic-gravity: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
