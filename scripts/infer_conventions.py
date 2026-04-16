#!/usr/bin/env python3
"""agent-readable infer_conventions: draft a .structure.yaml from an existing codebase.

Usage:
    python scripts/infer_conventions.py           # print suggested config to stdout
    python scripts/infer_conventions.py --write   # write .structure.yaml if absent

Reads the source tree and detects:
  - source_root (src/ vs flat)
  - max_depth actually in use
  - file naming convention (snake_case dominates? domain-prefix?)
  - common role suffixes (_service.py, _test.py, etc.)

The output is a best-guess — the user should review before committing.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import CONFIG_FILENAME, SNAKE_RE


COMMON_IGNORES = ["__pycache__", ".venv", "venv", "build", "dist", "tests"]


def detect_source_root(project_root: Path) -> str:
    """Pick source_root, preferring named dirs (src, lib, app) over project root.

    The rule: if a conventional source dir exists and contains at least a few
    .py files, prefer it. Only fall back to "." when no named source dir has
    meaningful content. This avoids counting top-level scripts (setup.py,
    conftest.py) and picking "." just because it's the parent.
    """
    MIN_FILES_FOR_NAMED_DIR = 2
    # Check named source dirs first, in priority order
    for candidate in ["src", "lib", "app"]:
        path = project_root / candidate
        if not path.exists() or not path.is_dir():
            continue
        count = sum(1 for p in path.rglob("*.py") if "__pycache__" not in p.parts)
        if count >= MIN_FILES_FOR_NAMED_DIR:
            return candidate

    # Fall back to "." — but only if there are .py files at the top level
    top_level_py = [
        p for p in project_root.glob("*.py") if "__pycache__" not in p.parts
    ]
    if top_level_py:
        return "."

    # Last resort: pick whichever subdir has the most .py files
    best = "."
    best_count = 0
    for sub in project_root.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        count = sum(1 for p in sub.rglob("*.py") if "__pycache__" not in p.parts)
        if count > best_count:
            best = sub.name
            best_count = count
    return best


def detect_max_depth(source_path: Path) -> int:
    max_depth = 0
    for p in source_path.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            rel = p.relative_to(source_path)
        except ValueError:
            continue
        max_depth = max(max_depth, len(rel.parts))
    return max(max_depth, 2)


def detect_file_case(source_path: Path) -> str:
    snake = 0
    other = 0
    for p in source_path.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        stem = p.stem
        if stem.startswith("_"):
            continue
        if SNAKE_RE.match(stem):
            snake += 1
        else:
            other += 1
    # Python convention is snake_case; only report otherwise if overwhelmingly not
    if snake >= other:
        return "snake_case"
    return "snake_case"  # Still default — Python community standard.


def detect_domain_prefix(source_path: Path) -> bool:
    """Heuristic: should the project enforce domain-prefix naming?

    Bias toward `true` (the recommended convention) unless the existing
    codebase clearly rejects it. Rationale: inferring from a messy codebase
    should give guidance that fixes the mess, not codifies it. Only turn off
    when fewer than 20% of files in domain dirs use the prefix — that means
    the team has made a deliberate choice against it.
    """
    prefix_hits = 0
    total = 0
    for p in source_path.rglob("*.py"):
        if "__pycache__" in p.parts or p.stem.startswith("_"):
            continue
        try:
            rel = p.relative_to(source_path)
        except ValueError:
            continue
        if len(rel.parts) < 2:
            continue
        parent = rel.parts[0]
        total += 1
        if p.stem.startswith(f"{parent}_") or p.stem == parent:
            prefix_hits += 1
    if total == 0:
        return True  # no domain dirs yet — recommend the convention
    ratio = prefix_hits / total
    # Threshold at 20%: above that, assume drift toward the good convention;
    # below that, assume deliberate choice against it.
    return ratio >= 0.20


def detect_role_suffixes(source_path: Path) -> list[str]:
    """Find the most common role suffixes in use, like _service, _test, _types."""
    suffix_re = re.compile(r"_([a-z]+)$")
    counter: Counter[str] = Counter()
    for p in source_path.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        stem = p.stem
        if stem.startswith("_"):
            continue
        match = suffix_re.search(stem)
        if match:
            counter[match.group(1)] += 1
    # Return suffixes appearing at least 2 times
    return [suffix for suffix, count in counter.most_common() if count >= 2]


def render_yaml(
    source_root: str,
    max_depth: int,
    file_case: str,
    domain_prefix: bool,
    suffixes: list[str],
) -> str:
    """Render a .structure.yaml based on inferred values."""
    # Map common suffixes into roles, with sensible defaults for anything unknown
    required = ["{domain}_service.py", "__init__.py"]
    recommended = []
    optional = []

    known_required = {"service"}
    known_recommended = {"test", "types"}
    known_optional = {"repository", "handlers", "validators", "errors", "model"}

    for s in suffixes:
        filename = f"{{domain}}_{s}.py"
        if s in known_required and filename not in required:
            required.append(filename)
        elif s in known_recommended and filename not in recommended:
            recommended.append(filename)
        elif s in known_optional and filename not in optional:
            optional.append(filename)
        # Unknown suffixes go to recommended (they're clearly used, just not canonical)
        elif filename not in required + recommended + optional:
            recommended.append(filename)

    # Ensure test and types are always recommended
    for default in ["{domain}_test.py", "{domain}_types.py"]:
        if default not in recommended and default not in required:
            recommended.append(default)

    yaml_lines = [
        "# .structure.yaml — inferred from existing codebase. Review before committing.",
        "",
        "layout:",
        f"  source_root: {source_root}",
        "  organization: domain",
        f"  max_depth: {max(max_depth, 3)}",
        "  ignore:",
    ]
    for ig in COMMON_IGNORES:
        yaml_lines.append(f"    - {ig}")

    yaml_lines.extend(
        [
            "",
            "naming:",
            f"  file_case: {file_case}",
            f"  domain_prefix: {str(domain_prefix).lower()}",
            "  class_case: PascalCase",
            "  function_case: snake_case",
            "  constant_case: SCREAMING_SNAKE_CASE",
            "  constant_domain_prefix: true",
            "",
            "roles:",
            "  required:",
        ]
    )
    for r in required:
        yaml_lines.append(f'    - "{r}"')
    yaml_lines.append("  recommended:")
    for r in recommended:
        yaml_lines.append(f'    - "{r}"')
    yaml_lines.append("  optional:")
    for r in optional:
        yaml_lines.append(f'    - "{r}"')

    yaml_lines.extend(
        [
            "",
            "forbidden:",
            "  generic_filenames:",
            "    - utils.py",
            "    - helpers.py",
            "    - common.py",
            "    - misc.py",
            "  star_imports_in_init: true",
            "",
            "errors:",
            "  require_domain_code: false  # turn on once you adopt error codes",
            '  code_pattern: "[A-Z]{2,5}_\\\\d{3}"',
            "",
            "scoring:",
            "  weights:",
            "    generic_file: 10",
            "    missing_required_role: 8",
            "    naming_inconsistency: 6",
            "    missing_recommended_role: 3",
            "    deep_nesting: 4",
            "    star_import_in_init: 5",
            "    missing_error_code: 2",
            "  thresholds:",
            "    excellent: 90",
            "    good: 75",
            "    fair: 60",
            "    poor: 40",
            "",
            "hooks:",
            "  pre_write_check: true",
            "  session_start_report: true",
            "  session_end_score: true",
            "  post_write_validate: false",
            "",
        ]
    )
    return "\n".join(yaml_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Infer structure conventions.")
    parser.add_argument(
        "--write",
        action="store_true",
        help=f"Write to {CONFIG_FILENAME} if it doesn't exist (won't overwrite).",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root to analyze (default: cwd).",
    )
    args = parser.parse_args()

    root = args.project_root.resolve()
    source_root_name = detect_source_root(root)
    source_path = root / source_root_name if source_root_name != "." else root

    max_depth = detect_max_depth(source_path)
    file_case = detect_file_case(source_path)
    domain_prefix = detect_domain_prefix(source_path)
    suffixes = detect_role_suffixes(source_path)

    yaml_text = render_yaml(source_root_name, max_depth, file_case, domain_prefix, suffixes)

    target = root / CONFIG_FILENAME
    if args.write:
        if target.exists():
            print(f"error: {target} already exists; refusing to overwrite.", file=sys.stderr)
            return 1
        target.write_text(yaml_text, encoding="utf-8")
        print(f"wrote {target}")
        print("Review the file and adjust before committing.")
    else:
        print(yaml_text)

    print(
        f"\n# Inferred: source_root={source_root_name}, max_depth={max_depth}, "
        f"domain_prefix={domain_prefix}, role_suffixes={suffixes}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
