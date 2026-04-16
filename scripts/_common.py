"""Shared helpers for semantic-gravity scripts.

Handles config loading, path resolution, and common regex patterns.
All scripts import from here rather than duplicating logic.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


CONFIG_FILENAME = ".structure.yaml"


@dataclass
class Config:
    """Parsed .structure.yaml with defaults filled in."""

    source_root: str = "src"
    organization: str = "domain"
    max_depth: int = 3
    ignore: list[str] = field(default_factory=lambda: ["__pycache__", ".venv"])

    file_case: str = "snake_case"
    domain_prefix: bool = True
    class_case: str = "PascalCase"
    function_case: str = "snake_case"
    constant_case: str = "SCREAMING_SNAKE_CASE"
    constant_domain_prefix: bool = True

    required_roles: list[str] = field(default_factory=list)
    recommended_roles: list[str] = field(default_factory=list)
    optional_roles: list[str] = field(default_factory=list)

    generic_filenames: list[str] = field(default_factory=list)
    star_imports_in_init: bool = True

    require_domain_code: bool = False
    code_pattern: str = r"[A-Z]{2,5}_\d{3}"

    weights: dict[str, int] = field(default_factory=dict)
    thresholds: dict[str, int] = field(default_factory=dict)

    hooks_enabled: dict[str, bool] = field(default_factory=dict)

    # Path to the config file itself, so scripts can resolve source_root relative to it.
    config_path: Path | None = None

    @property
    def project_root(self) -> Path:
        """Directory containing .structure.yaml."""
        if self.config_path is None:
            return Path.cwd()
        return self.config_path.parent

    @property
    def source_path(self) -> Path:
        return self.project_root / self.source_root


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) looking for .structure.yaml."""
    current = (start or Path.cwd()).resolve()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def load_config(path: Path | None = None) -> Config:
    """Load .structure.yaml, filling in defaults for missing fields."""
    config_path = path or find_config()
    if config_path is None:
        raise FileNotFoundError(
            f"No {CONFIG_FILENAME} found. Run semantic-gravity in scaffold or "
            f"audit mode with --init to create one."
        )

    with config_path.open() as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    layout = raw.get("layout") or {}
    naming = raw.get("naming") or {}
    roles = raw.get("roles") or {}
    forbidden = raw.get("forbidden") or {}
    errors = raw.get("errors") or {}
    scoring = raw.get("scoring") or {}
    hooks = raw.get("hooks") or {}

    return Config(
        config_path=config_path,
        source_root=layout.get("source_root", "src"),
        organization=layout.get("organization", "domain"),
        max_depth=int(layout.get("max_depth", 3)),
        ignore=list(layout.get("ignore") or ["__pycache__", ".venv"]),
        file_case=naming.get("file_case", "snake_case"),
        domain_prefix=bool(naming.get("domain_prefix", True)),
        class_case=naming.get("class_case", "PascalCase"),
        function_case=naming.get("function_case", "snake_case"),
        constant_case=naming.get("constant_case", "SCREAMING_SNAKE_CASE"),
        constant_domain_prefix=bool(naming.get("constant_domain_prefix", True)),
        required_roles=list(roles.get("required") or []),
        recommended_roles=list(roles.get("recommended") or []),
        optional_roles=list(roles.get("optional") or []),
        generic_filenames=list(forbidden.get("generic_filenames") or []),
        star_imports_in_init=bool(forbidden.get("star_imports_in_init", True)),
        require_domain_code=bool(errors.get("require_domain_code", False)),
        code_pattern=errors.get("code_pattern", r"[A-Z]{2,5}_\d{3}"),
        weights=dict(scoring.get("weights") or {}),
        thresholds=dict(
            scoring.get("thresholds")
            or {"excellent": 90, "good": 75, "fair": 60, "poor": 40}
        ),
        hooks_enabled=dict(hooks or {}),
    )


def iter_python_files(config: Config) -> list[Path]:
    """All .py files under source_root, honoring ignore patterns."""
    if not config.source_path.exists():
        return []

    ignore_patterns = set(config.ignore)
    results: list[Path] = []
    for path in config.source_path.rglob("*.py"):
        if any(part in ignore_patterns for part in path.parts):
            continue
        if any(path.match(pattern) for pattern in ignore_patterns):
            continue
        results.append(path)
    return sorted(results)


def iter_domains(config: Config) -> list[Path]:
    """Top-level directories inside source_root — one per domain."""
    if not config.source_path.exists():
        return []
    return sorted(
        p
        for p in config.source_path.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in config.ignore
    )


def domain_name(path: Path, config: Config) -> str | None:
    """Extract the domain name for a given file path."""
    try:
        rel = path.relative_to(config.source_path)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:  # file directly in source_root has no domain
        return None
    return parts[0]


# Case conversion helpers for naming audits
SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
KEBAB_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PASCAL_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
SCREAMING_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")


def matches_case(name: str, case: str) -> bool:
    """Check whether `name` follows the given case convention."""
    name_stem = name.rsplit(".", 1)[0]  # strip extension if present
    if case == "snake_case":
        return bool(SNAKE_RE.match(name_stem))
    if case == "kebab-case":
        return bool(KEBAB_RE.match(name_stem))
    if case == "PascalCase":
        return bool(PASCAL_RE.match(name_stem))
    if case == "SCREAMING_SNAKE_CASE":
        return bool(SCREAMING_RE.match(name_stem))
    if case == "camelCase":
        return bool(CAMEL_RE.match(name_stem))
    return True  # unknown case = permissive
