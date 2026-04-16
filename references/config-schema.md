# .structure.yaml Schema Reference

Load this file when writing, editing, or validating `.structure.yaml`. The defaults live in `assets/structure.template.yaml`; this file explains each field and its valid values.

## Top-level sections

The config has six top-level sections. All are optional — missing sections fall back to Python defaults.

```yaml
layout: {...}       # where code lives and how deep it can nest
naming: {...}       # casing conventions for files, classes, functions, constants
roles: {...}        # what files each domain must/should/may contain
forbidden: {...}    # patterns that always lose fitness points
errors: {...}       # domain-prefixed error code enforcement
scoring: {...}      # penalty weights and grade thresholds
hooks: {...}        # which lifecycle events to wire up
```

## `layout`

Defines the physical shape of the codebase.

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `source_root` | string | `"src"` | Directory containing the source tree. All audits are scoped here. |
| `organization` | `"domain"` \| `"layer"` | `"domain"` | How to group files. `domain` means `src/<domain>/` holds all files for that domain. `layer` means `src/services/`, `src/models/` etc. Layer-based is not recommended for AI agents — it forces them to stitch scattered files together. |
| `max_depth` | int | `3` | Max directory depth from `source_root`. Depth 3 = `src/domain/subgroup/file.py`. Going deeper is heavily penalized. |
| `ignore` | list[string] | see template | Glob-ish patterns skipped during audits. Paths matching any entry in their parts or full path are excluded. |

## `naming`

Casing conventions. Each field accepts a fixed vocabulary.

| Field | Valid values | Default | Meaning |
| --- | --- | --- | --- |
| `file_case` | `snake_case`, `kebab-case` | `snake_case` | For Python, always `snake_case`. |
| `domain_prefix` | bool | `true` | Whether files inside a domain directory must start with the domain name, e.g., `payment_service.py` instead of `service.py`. |
| `class_case` | `PascalCase`, `snake_case` | `PascalCase` | Python convention is PascalCase. |
| `function_case` | `snake_case`, `camelCase` | `snake_case` | PEP 8 requires snake_case. |
| `constant_case` | `SCREAMING_SNAKE_CASE`, `PascalCase` | `SCREAMING_SNAKE_CASE` | PEP 8 convention. |
| `constant_domain_prefix` | bool | `true` | Whether constants must be prefixed with the domain abbreviation, e.g., `PAYMENT_TIMEOUT_MS`. |

## `roles`

A "role" is a file's purpose within a domain, expressed as a filename template. Use `{domain}` as a placeholder for the domain name.

```yaml
roles:
  required:
    - "{domain}_service.py"
    - "__init__.py"
  recommended:
    - "{domain}_types.py"
    - "{domain}_test.py"
  optional:
    - "{domain}_repository.py"
    - "{domain}_handlers.py"
```

- **required** — every domain must have these. Missing files are a high-severity violation.
- **recommended** — every domain should have these. Missing files lose fewer points.
- **optional** — listed so `scaffold.py --include` can create them on request. Not penalized if absent.

The scaffold script generates bodies for well-known role keywords: `service`, `types`, `test`, `repository`, `handlers`, `validators`, `errors`. Custom role keywords get a placeholder body.

## `forbidden`

Patterns that are always wrong, regardless of domain or role.

```yaml
forbidden:
  generic_filenames:
    - utils.py
    - helpers.py
    - common.py
    - misc.py
  star_imports_in_init: true
```

- **generic_filenames** — files with these exact names trigger the `generic_file` penalty. They become dumping grounds and are invisible to domain-scoped search.
- **star_imports_in_init** — if true, `from .x import *` in any `__init__.py` triggers the `star_import_in_init` penalty. Star imports hide the public contract from grep.

## `errors`

Optional enforcement of domain-prefixed error codes.

```yaml
errors:
  require_domain_code: true
  code_pattern: "[A-Z]{2,5}_\\d{3}"
```

- **require_domain_code** — when true, the audit samples `raise` statements and flags any whose message doesn't contain a matching code.
- **code_pattern** — the regex a valid error code must match. The default matches codes like `PAY_001`, `AUTH_003`, `ORDER_042`.

## `scoring`

Controls the fitness score calculation.

```yaml
scoring:
  weights:
    generic_file: 10
    missing_required_role: 8
    naming_inconsistency: 6
    missing_recommended_role: 3
    deep_nesting: 4
    star_import_in_init: 5
    missing_error_code: 2
  thresholds:
    excellent: 90
    good: 75
    fair: 60
    poor: 40
```

- **weights** — points deducted per violation in each category. Tune these to reflect what your team cares about.
- **thresholds** — score cutoffs for human-readable grades. Scores below `poor` are graded `critical`.

The score starts at 100 and each violation subtracts its weight. The minimum is 0. There is no cap on the number of violations, so a codebase with 20 generic files is capped at score 0 — deliberately. Once you're at zero, the exact number is noise; what matters is reducing categories.

## `hooks`

Booleans controlling which hooks the "evolve" mode installs.

| Field | Default | Effect |
| --- | --- | --- |
| `pre_write_check` | `true` | Blocks file writes that violate conventions (PreToolUse). |
| `session_start_report` | `true` | Injects fitness summary into session context (SessionStart). |
| `session_end_score` | `true` | Appends score to `.structure-log.txt` (Stop). |
| `post_write_validate` | `false` | Re-runs audit after every file edit. Slow — opt in only. |

## Minimal config

If you want the smallest valid config, this is it:

```yaml
layout:
  source_root: src
```

Everything else falls back to defaults. Start here and add specificity as drift appears.
