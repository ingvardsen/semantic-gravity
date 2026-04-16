# Fitness Rubric

Load this when explaining a score to the user or deciding which violations to surface first. Scores aren't just numbers — they encode how easily a fresh Claude Code session can navigate the codebase.

## What "fitness" actually means

Every session, a fresh agent rediscovers the codebase via `rg`, `glob`, and `read`. A fit codebase lets the agent correctly infer:

1. Where to place a new file
2. What naming convention to use
3. Which modules depend on which
4. What the project's public API surface is

Unfit codebases force the agent into discovery spirals — reading 20 files to answer a question 3 files should have answered. That's wasted tokens and wrong guesses.

## Grade bands (defaults)

| Score | Grade | What it feels like to the agent |
| --- | --- | --- |
| 90-100 | excellent | Agent orients in a few tool calls. New files land in the right place without instruction. |
| 75-89 | good | Minor drift. Agent occasionally needs a hint but usually gets it right. |
| 60-74 | fair | Noticeable friction. Naming is inconsistent enough that the agent sometimes invents new patterns instead of following existing ones. |
| 40-59 | poor | Significant drift. Agent reads many files before making decisions and produces inconsistent work across sessions. |
| 0-39 | critical | Structure is actively misleading. Agent can't rely on conventions and falls back to guessing every time. |

## Violation categories, explained

### `generic_file` (highest default weight)

Files named `utils.py`, `helpers.py`, `common.py`, `misc.py`. These are black holes — they accumulate unrelated code from every domain, and the agent has to read the entire file to know what's inside. A fresh session cannot predict what's in `utils.py`; it can predict what's in `payment_validators.py` from the name alone.

**How to fix**: Open the file, group its contents by domain or role, and split. A function that formats payment amounts goes into `payment_utils.py` or (better) `payment_formatting.py` inside the payment domain.

### `missing_required_role`

A domain is missing one of the files listed in `roles.required`. Most commonly: a domain with no `__init__.py` (can't be imported cleanly) or no service file (where's the business logic?).

**How to fix**: Run `scripts/scaffold.py <domain>` to generate stubs, or create the files manually following the template.

### `naming_inconsistency`

File doesn't match `file_case`, or lives in a domain directory but lacks the domain prefix. Mixed styles force the agent to write two regexes where one should work.

**How to fix**: Rename with `git mv`. Update imports as you go — a rename without import fixes is worse than the inconsistency. Do one file at a time so tests keep passing.

### `missing_recommended_role`

A domain is missing `_types.py` or `_test.py`. Lower severity because the code still works, but:
- No types file = type definitions scattered inside implementation files, hard to find
- No test file = agent has no documentation of intended behavior to read on a fresh session

**How to fix**: Lower priority than the items above. Tackle when you have time, or create empty stubs and backfill over time.

### `deep_nesting`

File is more levels deep than `max_depth` allows. Every extra level multiplies the number of `find` or `glob` patterns the agent must try.

**How to fix**: Either flatten by moving files closer to the source root, or split the over-nested domain into siblings. If `src/payment/webhooks/providers/stripe/handlers.py` is too deep, promote `providers/` to a top-level domain: `src/payment_providers/stripe_handlers.py`.

### `star_import_in_init`

`from .service import *` in an `__init__.py`. The public contract becomes invisible — grep can't tell you what's exported without reading every module the star-import touches.

**How to fix**: Replace with explicit re-exports. Takes 5 minutes per file and makes `rg 'from project.domain import' -l` actually meaningful.

### `missing_error_code` (opt-in)

A `raise SomethingError("plain message")` without a domain-prefixed code. When production logs show an error, the agent can't trace from log to source without fuzzy searching.

**How to fix**: Adopt a code scheme (`PAY_001`, `AUTH_003`) and prefix every error message. This also makes error handling testable: `assert "PAY_007" in exc.message`.

## How to present scores to users

When asked "how's my structure looking?", lead with the headline, then top three categories by penalty — not by count. If `generic_file` costs 30 points and `missing_recommended_role` costs 18 points spread across 6 domains, generic files matter more even though there are fewer instances.

Bad framing:
> "You have 6 missing test files, 3 generic files, 2 star imports..."

Good framing:
> "Score: 67/100 (fair). Your biggest penalty is from generic files (30 points, 3 files) — those are the ones to fix first. Want me to walk through them?"

Offer one fix at a time. Agents get better at fixing structure when they have a narrow target; users stay engaged when each step is reviewable.
