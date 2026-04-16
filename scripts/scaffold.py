#!/usr/bin/env python3
"""agent-readable scaffold: create a new domain with all required files.

Usage:
    python scripts/scaffold.py payment
    python scripts/scaffold.py auth --include repository handlers
    python scripts/scaffold.py --dry-run billing

Creates, for domain `payment`:
    src/payment/
      __init__.py              (with explicit re-exports)
      payment_service.py       (required)
      payment_types.py         (recommended)
      payment_test.py          (recommended)
      payment_repository.py    (if --include repository)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import Config, iter_domains, load_config, matches_case


@dataclass
class ScaffoldPlan:
    domain: str
    target_dir: Path
    files_to_create: list[tuple[Path, str]]  # (path, content)


# --- Templates -----------------------------------------------------------


def tpl_service(domain: str) -> str:
    return f'''"""{domain.capitalize()} service — business logic for the {domain} domain."""

from __future__ import annotations


# Add service functions here. Remember:
# - Prefix public functions with the domain name or keep them domain-scoped via imports.
# - Raise errors with domain-prefixed codes: raise {domain.capitalize()}Error("{domain.upper()[:3]}_001: ...")
# - Co-locate tests in {domain}_test.py.
'''


def tpl_types(domain: str) -> str:
    return f'''"""{domain.capitalize()} types — dataclasses, TypedDicts, and protocols."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class {domain.capitalize()}Input:
    """Input payload for {domain} operations."""

    # Replace with actual fields
    placeholder: str


@dataclass
class {domain.capitalize()}Result:
    """Result of a {domain} operation."""

    success: bool
    # Replace with actual fields
'''


def tpl_test(domain: str) -> str:
    return f'''"""Tests for the {domain} domain, co-located with source."""

from __future__ import annotations


def test_{domain}_placeholder() -> None:
    """Replace with real tests."""
    assert True
'''


def tpl_repository(domain: str) -> str:
    return f'''"""{domain.capitalize()} repository — data access layer."""

from __future__ import annotations


class {domain.capitalize()}Repository:
    """Encapsulates {domain} data access."""

    def __init__(self) -> None:
        pass
'''


def tpl_handlers(domain: str) -> str:
    return f'''"""{domain.capitalize()} handlers — HTTP and event handlers."""

from __future__ import annotations


# Handler functions go here, prefixed with the domain name.
# Example:
#   def {domain}_create_handler(request): ...
'''


def tpl_validators(domain: str) -> str:
    return f'''"""{domain.capitalize()} validators — input validation."""

from __future__ import annotations


# Validation functions go here.
# Example:
#   def {domain}_validate_input(payload: dict) -> bool: ...
'''


def tpl_errors(domain: str) -> str:
    code = domain.upper()[:3]
    return f'''"""{domain.capitalize()} errors — domain-specific exceptions."""

from __future__ import annotations


class {domain.capitalize()}Error(Exception):
    """Base exception for the {domain} domain.

    Always raise with a domain-prefixed code:
        raise {domain.capitalize()}Error("{code}_001: descriptive message")
    """
'''


def tpl_init(domain: str, role_files: list[str]) -> str:
    """Generate an __init__.py with explicit re-exports from each role file."""
    lines = [
        f'"""Public API for the {domain} domain.',
        "",
        "This file re-exports the domain's public surface. Every name exposed here",
        "should be importable as `from project.{domain} import X`. Avoid star imports —",
        "they make the public contract invisible to grep.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    # Include a commented-out example re-export for each role file
    for fname in sorted(role_files):
        stem = fname.replace(".py", "")
        if stem == "__init__":
            continue
        lines.append(f"# from .{stem} import <names>")

    lines.append("")
    lines.append("__all__: list[str] = [")
    lines.append("    # Add public names here as you export them.")
    lines.append("]")
    return "\n".join(lines) + "\n"


TEMPLATES = {
    "service": tpl_service,
    "types": tpl_types,
    "test": tpl_test,
    "repository": tpl_repository,
    "handlers": tpl_handlers,
    "validators": tpl_validators,
    "errors": tpl_errors,
}


def role_to_template_key(role_template: str, domain: str) -> str | None:
    """Map a role filename (e.g., 'payment_service.py') to a template key ('service')."""
    filename = role_template.replace("{domain}", domain)
    if filename == "__init__.py":
        return "init"
    # Expect "{domain}_<role>.py"
    prefix = f"{domain}_"
    if filename.startswith(prefix) and filename.endswith(".py"):
        return filename[len(prefix) : -3]
    return None


# --- Plan and execute ----------------------------------------------------


def build_plan(
    config: Config, domain: str, include_optional: list[str]
) -> ScaffoldPlan:
    """Compute what files would be created, without touching the filesystem."""
    if not matches_case(domain, config.file_case):
        raise ValueError(
            f"Domain name '{domain}' does not match {config.file_case} convention."
        )

    target_dir = config.source_path / domain
    files: list[tuple[Path, str]] = []
    role_files: list[str] = []

    # Required + recommended roles are always included
    for role_template in list(config.required_roles) + list(config.recommended_roles):
        filename = role_template.replace("{domain}", domain)
        role_files.append(filename)

    # Optional roles: first try matching config, then fall back to built-in templates.
    # This lets --include work out-of-the-box on projects where the user hasn't
    # pre-declared every optional role in .structure.yaml.
    for opt in include_optional:
        matching = [
            r.replace("{domain}", domain)
            for r in config.optional_roles
            if opt in r
        ]
        if matching:
            role_files.extend(matching)
        elif opt in TEMPLATES:
            # Fall back: generate from built-in template if keyword matches.
            role_files.append(f"{domain}_{opt}.py")
        else:
            print(
                f"warning: --include '{opt}' doesn't match any configured optional "
                f"role or built-in template. Known templates: {sorted(TEMPLATES.keys())}",
                file=sys.stderr,
            )

    # Generate content for each file
    seen: set[str] = set()
    for filename in role_files:
        if filename in seen:
            continue
        seen.add(filename)

        if filename == "__init__.py":
            content = tpl_init(domain, role_files)
        else:
            key = filename[len(f"{domain}_") : -3] if filename.startswith(f"{domain}_") else ""
            template_fn = TEMPLATES.get(key)
            if template_fn is None:
                content = f'"""Auto-generated placeholder for {filename}."""\n'
            else:
                content = template_fn(domain)

        files.append((target_dir / filename, content))

    # Make sure __init__.py is in the plan even if not in the config
    init_path = target_dir / "__init__.py"
    if not any(p == init_path for p, _ in files):
        files.append((init_path, tpl_init(domain, role_files)))

    return ScaffoldPlan(domain=domain, target_dir=target_dir, files_to_create=files)


def execute_plan(plan: ScaffoldPlan) -> None:
    plan.target_dir.mkdir(parents=True, exist_ok=True)
    for path, content in plan.files_to_create:
        if path.exists():
            print(f"  skip   {path}  (already exists)")
            continue
        path.write_text(content, encoding="utf-8")
        print(f"  create {path}")


def print_plan(plan: ScaffoldPlan) -> None:
    print(f"\nScaffold plan for domain '{plan.domain}':")
    print(f"  target: {plan.target_dir}/")
    for path, _ in plan.files_to_create:
        marker = "exists" if path.exists() else "create"
        print(f"  [{marker}] {path.name}")
    print()


# --- CLI -----------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new Python domain.")
    parser.add_argument("domain", help="Domain name (snake_case).")
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        help="Optional role keywords to include (e.g., repository handlers).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the plan without creating files."
    )
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    existing_domains = {d.name for d in iter_domains(config)}
    if args.domain in existing_domains and not args.dry_run:
        print(
            f"error: domain '{args.domain}' already exists. "
            f"Use --dry-run to preview, or choose a different name.",
            file=sys.stderr,
        )
        return 1

    try:
        plan = build_plan(config, args.domain, args.include)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print_plan(plan)
    if args.dry_run:
        print("(dry run — no files created)")
        return 0

    execute_plan(plan)
    print(f"\nDone. Run `python scripts/audit.py` to verify fitness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
