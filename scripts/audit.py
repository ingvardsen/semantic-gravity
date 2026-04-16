#!/usr/bin/env python3
"""semantic-gravity audit: score the codebase and list violations.

Usage:
    python scripts/audit.py                # human-readable output
    python scripts/audit.py --json         # machine-readable for hooks
    python scripts/audit.py --fix generic  # interactive fix for a category

Exit codes:
    0 = score >= fair threshold
    1 = score below fair threshold (for CI gating)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Allow running as `python scripts/audit.py` from project root
sys.path.insert(0, str(Path(__file__).parent))
from _common import (
    Config,
    domain_name,
    iter_domains,
    iter_python_files,
    load_config,
    matches_case,
)


@dataclass
class Violation:
    category: str
    severity: int  # score penalty
    path: str
    message: str
    fix_hint: str = ""


@dataclass
class AuditReport:
    score: int = 100
    grade: str = "excellent"
    domains_found: int = 0
    files_scanned: int = 0
    violations: list[Violation] = field(default_factory=list)

    def by_category(self) -> dict[str, list[Violation]]:
        grouped: dict[str, list[Violation]] = {}
        for v in self.violations:
            grouped.setdefault(v.category, []).append(v)
        return grouped

    def penalties_by_category(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for v in self.violations:
            totals[v.category] = totals.get(v.category, 0) + v.severity
        return totals


# --- Individual checks ---------------------------------------------------


def check_generic_files(config: Config) -> list[Violation]:
    """Find files with generic names like utils.py, helpers.py."""
    weight = config.weights.get("generic_file", 10)
    violations: list[Violation] = []
    for path in iter_python_files(config):
        if path.name in config.generic_filenames:
            violations.append(
                Violation(
                    category="generic_file",
                    severity=weight,
                    path=str(path),
                    message=f"Generic filename '{path.name}' — this becomes a dumping ground.",
                    fix_hint=f"Rename to describe its purpose, e.g., {path.parent.name}_<role>.py",
                )
            )
    return violations


def check_required_roles(config: Config) -> list[Violation]:
    """Each domain must have all required role files."""
    weight = config.weights.get("missing_required_role", 8)
    violations: list[Violation] = []
    for domain_dir in iter_domains(config):
        existing = {p.name for p in domain_dir.iterdir() if p.is_file()}
        for role_template in config.required_roles:
            expected = role_template.replace("{domain}", domain_dir.name)
            if expected not in existing:
                violations.append(
                    Violation(
                        category="missing_required_role",
                        severity=weight,
                        path=str(domain_dir),
                        message=f"Domain '{domain_dir.name}' missing required file: {expected}",
                        fix_hint=f"Create {domain_dir}/{expected}",
                    )
                )
    return violations


def check_recommended_roles(config: Config) -> list[Violation]:
    """Recommended files are softer — lower penalty but still tracked."""
    weight = config.weights.get("missing_recommended_role", 3)
    violations: list[Violation] = []
    for domain_dir in iter_domains(config):
        existing = {p.name for p in domain_dir.iterdir() if p.is_file()}
        for role_template in config.recommended_roles:
            expected = role_template.replace("{domain}", domain_dir.name)
            if expected not in existing:
                violations.append(
                    Violation(
                        category="missing_recommended_role",
                        severity=weight,
                        path=str(domain_dir),
                        message=f"Domain '{domain_dir.name}' missing recommended file: {expected}",
                        fix_hint=f"Consider creating {domain_dir}/{expected}",
                    )
                )
    return violations


def check_naming_convention(config: Config) -> list[Violation]:
    """File names must match file_case, and (optionally) have domain prefix."""
    weight = config.weights.get("naming_inconsistency", 6)
    violations: list[Violation] = []
    for path in iter_python_files(config):
        stem = path.stem
        if stem == "__init__":
            continue
        if not matches_case(stem, config.file_case):
            violations.append(
                Violation(
                    category="naming_inconsistency",
                    severity=weight,
                    path=str(path),
                    message=f"Filename '{path.name}' does not match {config.file_case} convention.",
                    fix_hint=f"Rename to {config.file_case} style",
                )
            )
            continue

        if config.domain_prefix:
            domain = domain_name(path, config)
            if domain and not stem.startswith(f"{domain}_") and stem != domain:
                violations.append(
                    Violation(
                        category="naming_inconsistency",
                        severity=weight,
                        path=str(path),
                        message=f"File '{path.name}' in domain '{domain}' lacks domain prefix.",
                        fix_hint=f"Rename to {domain}_{path.name}",
                    )
                )
    return violations


def check_deep_nesting(config: Config) -> list[Violation]:
    weight = config.weights.get("deep_nesting", 4)
    violations: list[Violation] = []
    for path in iter_python_files(config):
        try:
            rel = path.relative_to(config.source_path)
        except ValueError:
            continue
        depth = len(rel.parts)  # file counts as one level
        if depth > config.max_depth:
            violations.append(
                Violation(
                    category="deep_nesting",
                    severity=weight,
                    path=str(path),
                    message=f"File is {depth} levels deep (max: {config.max_depth}).",
                    fix_hint="Flatten by moving closer to the source root, or split domains.",
                )
            )
    return violations


def check_star_imports(config: Config) -> list[Violation]:
    """Find `from X import *` in __init__.py files."""
    if not config.star_imports_in_init:
        return []
    weight = config.weights.get("star_import_in_init", 5)
    violations: list[Violation] = []
    star_re = re.compile(r"^\s*from\s+\S+\s+import\s+\*", re.MULTILINE)
    for path in iter_python_files(config):
        if path.name != "__init__.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if star_re.search(text):
            violations.append(
                Violation(
                    category="star_import_in_init",
                    severity=weight,
                    path=str(path),
                    message="__init__.py uses `from X import *` — makes exports invisible to grep.",
                    fix_hint="Replace with explicit re-exports: `from .x_service import specific_name`",
                )
            )
    return violations


def check_error_codes(config: Config) -> list[Violation]:
    """Sample a few raise-statement messages for domain-prefixed codes."""
    if not config.require_domain_code:
        return []
    weight = config.weights.get("missing_error_code", 2)
    violations: list[Violation] = []
    code_re = re.compile(config.code_pattern)
    raise_re = re.compile(r"""raise\s+\w+\s*\(\s*["']([^"']+)""")
    for path in iter_python_files(config):
        if path.name == "__init__.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in raise_re.finditer(text):
            message = match.group(1)
            if not code_re.search(message):
                violations.append(
                    Violation(
                        category="missing_error_code",
                        severity=weight,
                        path=str(path),
                        message=f"Error message '{message[:40]}...' has no domain code.",
                        fix_hint=f"Prefix with a code like 'PAY_001: {message[:30]}'",
                    )
                )
                break  # one per file is enough to flag
    return violations


# --- Report assembly -----------------------------------------------------


def run_audit(config: Config) -> AuditReport:
    report = AuditReport()
    report.domains_found = len(iter_domains(config))
    report.files_scanned = len(iter_python_files(config))

    checks = [
        check_generic_files,
        check_required_roles,
        check_recommended_roles,
        check_naming_convention,
        check_deep_nesting,
        check_star_imports,
        check_error_codes,
    ]
    for check in checks:
        report.violations.extend(check(config))

    total_penalty = sum(v.severity for v in report.violations)
    report.score = max(0, 100 - total_penalty)
    report.grade = grade_for(report.score, config)
    return report


def grade_for(score: int, config: Config) -> str:
    thresholds = config.thresholds
    if score >= thresholds.get("excellent", 90):
        return "excellent"
    if score >= thresholds.get("good", 75):
        return "good"
    if score >= thresholds.get("fair", 60):
        return "fair"
    if score >= thresholds.get("poor", 40):
        return "poor"
    return "critical"


# --- Output formatting ---------------------------------------------------


def print_human(report: AuditReport) -> None:
    print(f"\nStructure fitness: {report.score}/100 — {report.grade}")
    print(f"Scanned {report.files_scanned} files across {report.domains_found} domains.\n")

    if not report.violations:
        print("No violations found. Codebase is fit for fresh-session re-discovery.")
        return

    by_cat = report.by_category()
    penalties = report.penalties_by_category()

    # Order categories by total penalty descending — biggest problems first
    ordered = sorted(by_cat.items(), key=lambda kv: -penalties[kv[0]])
    for category, items in ordered:
        total = penalties[category]
        print(f"\n[{category}] — {len(items)} issue(s), -{total} points")
        for v in items[:5]:  # cap at 5 per category to keep output scannable
            print(f"  {v.path}")
            print(f"    {v.message}")
            if v.fix_hint:
                print(f"    fix: {v.fix_hint}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")


def print_json(report: AuditReport) -> None:
    payload = {
        "score": report.score,
        "grade": report.grade,
        "domains_found": report.domains_found,
        "files_scanned": report.files_scanned,
        "penalties_by_category": report.penalties_by_category(),
        "violations": [asdict(v) for v in report.violations],
    }
    print(json.dumps(payload, indent=2))


# --- CLI -----------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit project structure fitness.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to .structure.yaml (default: walk up from cwd).",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    report = run_audit(config)

    if args.json:
        print_json(report)
    else:
        print_human(report)

    # Exit code for CI: fail if below "fair"
    fair_threshold = config.thresholds.get("fair", 60)
    return 0 if report.score >= fair_threshold else 1


if __name__ == "__main__":
    sys.exit(main())
