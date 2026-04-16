---
name: agent-readable
description: Scaffold, audit, and evolve Python project structure so it stays grep-friendly and fresh-session-readable. Use this skill whenever the user wants to create new modules or features, check how discoverable their codebase is, fix naming drift, find structural debt, score a project's "fitness" for AI agents, set up hooks to enforce conventions, or any time they mention project structure, directory layout, naming conventions, file placement, refactoring for clarity, domain-driven organization, or making a codebase "AI-friendly" / "agent-readable". Also trigger proactively when a user asks you to create new Python files or modules in a project that already has a `.structure.yaml` — consult the config first and follow its rules.
---

# Agent Readable

Project structure is memory. Every session, a fresh Claude Code instance reconstructs understanding from the filesystem via Grep, Glob, and Read. Structures that are easy to re-discover are "fit"; structures that require extensive exploration waste tokens and produce wrong guesses. This skill keeps the codebase fit.

The skill has three modes — **scaffold**, **audit**, and **evolve** — all driven by a single `.structure.yaml` config at the project root. Pick the mode that matches the user's intent; the config stays the same across all three.

## Step 1: Find or create the config

Before doing anything else, locate `.structure.yaml` at the project root. If it exists, read it — it's the source of truth for conventions. If it doesn't exist, bootstrap one:

- For a **new project**: create `.structure.yaml` from `assets/structure.template.yaml` and ask the user to confirm or edit the conventions.
- For an **existing project**: run `scripts/infer_conventions.py` to detect the patterns already in use, then draft a `.structure.yaml` for the user to review before writing it to disk.

The config schema is in `references/config-schema.md`. Read it when unsure about a field.

## Step 2: Pick the mode

### Scaffold mode
**Triggers**: "create a new feature/module/domain", "add a new X component", "start a new service"

Workflow:
1. Read `.structure.yaml` to know the domain layout and file roles required (e.g., every feature needs `*_service.py`, `*_types.py`, `*_test.py`, `__init__.py`).
2. Ask the user for the **domain name** (e.g., `payment`, `auth`) if it's not obvious from the request.
3. Run `scripts/scaffold.py <domain>` — this creates the directory, all role files from templates, and the `__init__.py` with appropriate exports.
4. Show the user the tree that was created and list any next steps implied by their request.

Never scaffold a feature that duplicates an existing domain. Always `ls` the target parent directory first.

### Audit mode
**Triggers**: "check structure", "how's my project looking", "find naming inconsistencies", "structural debt", "fitness score"

Workflow:
1. Run `scripts/audit.py` — this produces a fitness score (0-100) and a list of specific violations grouped by severity.
2. Present the score first (one number, with trend if `.structure-log.txt` exists), then the top three most-fixable issues.
3. Offer to fix issues interactively, one category at a time. Don't batch-fix silently — each category needs confirmation.

The scoring rubric is in `references/fitness-rubric.md`. Explain scores in plain language, not jargon.

### Evolve mode
**Triggers**: "set up hooks", "enforce conventions automatically", "make structure self-maintaining", "refactor drift", "self-heal"

Workflow:
1. Check whether the project has `.claude/settings.json` with structure hooks configured. If not, offer to install them from `assets/hooks.template.json`.
2. Install `scripts/pre_write_check.py` as a `PreToolUse` hook on `Write` and `Edit` — it blocks file creation that violates conventions before it happens.
3. Install `scripts/session_start_report.py` as a `SessionStart` hook — it injects a structure health summary into every new session.
4. Install `scripts/session_end_score.py` as a `Stop` hook — it appends the fitness score to `.structure-log.txt` so trends are visible across sessions.

After installing hooks, run `scripts/audit.py` once to establish a baseline score.

## The core principle

All three modes serve one goal: **make the codebase re-discoverable by a fresh session using ripgrep and glob patterns alone**. The config encodes what "discoverable" means for this project. The scripts measure and enforce it. Never make a structural decision that you couldn't explain as "a fresh session would find this faster."

If the user's request conflicts with the config, surface the conflict. Don't silently override `.structure.yaml` — it's the contract.

## When to consult references

- **Writing or modifying `.structure.yaml`** → read `references/config-schema.md` first
- **Explaining a low fitness score** → read `references/fitness-rubric.md`
- **Designing hooks for an unusual workflow** → read `references/hook-patterns.md`
- **Answering "why does this matter for AI agents?"** → read `references/why-structure.md`

## Interaction style

Users who reach this skill generally care about code quality but may not want long lectures. Lead with concrete actions (scores, commands, file paths) and offer to explain the reasoning only when they ask. If the user seems new to the concept, read `references/why-structure.md` yourself and paraphrase — don't dump the whole file into chat.

For Python-specific conventions (PEP 8 naming, `snake_case` files, `__init__.py` exports), the defaults in `assets/structure.template.yaml` follow community norms. The user can override any of them in their own config.
