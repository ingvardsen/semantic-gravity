# Hook Patterns

Load this when designing hooks for unusual workflows, debugging hook behavior, or adapting the defaults in `assets/hooks.template.json`.

## The three default hooks

### 1. PreToolUse on Write|Edit — the deterministic gate

```json
{
  "matcher": "Write|Edit",
  "hooks": [{ "type": "command", "command": "python3 scripts/pre_write_check.py" }]
}
```

Fires before every file creation or edit. Reads the proposed file_path from stdin JSON, checks it against `.structure.yaml`, exits 0 (allow) or 2 (block with reason).

This is the only hook that can actually prevent drift. The others observe and report; this one enforces. Install this first, before anything else.

**Failure modes:**
- Missing `.structure.yaml` → hook no-ops (exit 0). Not an error; projects without a config aren't opted in.
- Malformed JSON on stdin → hook no-ops. Never block on parsing failure.
- Timeout (default 1.5s for hooks) → hook fails open. For projects with huge `.structure.yaml` files, raise the timeout in settings.

### 2. SessionStart — awareness injection

```json
{
  "hooks": [{ "type": "command", "command": "python3 scripts/session_start_report.py" }]
}
```

Fires once per session. Runs a full audit and injects a summary as `additionalContext`. The agent sees the current fitness score and top issues before writing any code — so structural debt is on-screen the moment it could influence a decision.

The key nuance: **don't dump all violations**. The hook shows only the top 3 penalty categories. More than that becomes noise and stops influencing behavior.

### 3. Stop — trend logging

```json
{
  "hooks": [{ "type": "command", "command": "python3 scripts/session_end_score.py", "async": true }]
}
```

Fires when the agent finishes. Runs the audit and appends the score to `.structure-log.txt`. Set `async: true` so the user doesn't wait for the audit to finish before the session closes.

The trend log is what makes evolution visible. A single score is just a number; `81, 83, 84, 85, 87` is a story.

## Optional patterns

### Post-write validator (opt-in, slow)

```json
{
  "matcher": "Write|Edit",
  "hooks": [{ "type": "command", "command": "python3 scripts/audit.py --json" }]
}
```

Runs the full audit after every file write. Gives the agent immediate feedback if its edit introduced drift. Only enable this if sessions are short or the codebase is small — it re-scans the entire tree on every edit.

### Git-branch-scoped rules

If different branches have different conventions (legacy code vs new modules), wrap the hook in a branch check:

```json
{
  "command": "[ \"$(git branch --show-current)\" = \"main\" ] && python3 scripts/pre_write_check.py || exit 0"
}
```

### Prompt-type hook for semantic evaluation

For subjective structural decisions (does this class belong in `service` or `handler`?), use a prompt-type hook that asks a fast model:

```json
{
  "matcher": "Write",
  "hooks": [{
    "type": "prompt",
    "prompt": "File being created: $ARGUMENTS\n\nDoes this file's content match its filename role? Services should contain business logic, not HTTP routing. Handlers should do routing, not business logic. Respond with decision: allow or decision: block and a short reason."
  }]
}
```

This is more expensive than a shell script but catches violations that pure naming can't detect.

## Hook composition order

When multiple hooks match the same event, they run in order and all must pass. The recommended order for Write/Edit:

1. `pre_write_check.py` — structure validation (block on violation)
2. Formatter (e.g., `ruff format`) — auto-fix style
3. Linter (e.g., `ruff check --fix`) — auto-fix obvious issues

Put structure first. A file that violates conventions isn't worth formatting.

## Debugging tips

- **Hook silently failing?** Run the hook script manually with a sample JSON payload on stdin: `echo '{"tool_input":{"file_path":"src/bad/bad.py"}}' | python3 scripts/pre_write_check.py`.
- **Hook always passing when it shouldn't?** Check that `.structure.yaml` is being found. Print `find_config()` from the script to verify.
- **Claude confused by hook messages?** Hook stderr is surfaced back to the agent. Keep messages short and actionable — one line per violation with the fix hint.

## When NOT to use hooks

Hooks are deterministic and deterministically-annoying. Don't add a hook for something you can enforce via code review or CI. Good hook candidates are rules that:

1. Must apply to every single write (not just PRs)
2. Have a clear right/wrong answer (no judgment calls)
3. Are cheap to check (sub-second)

Anything else belongs in the audit script (which runs on demand) or in CI (which runs on push).
