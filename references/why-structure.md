# Why Structure Matters for AI Agents

Load this when a user asks why semantic-gravity exists, why the conventions matter, or seems skeptical about the value of structural audits. Don't paste this whole file into chat — paraphrase based on what the user needs.

## The core problem

Claude Code has no persistent memory between sessions. Every new session starts from zero: load `CLAUDE.md`, load auto-memory, then reconstruct understanding of the project by reading the filesystem via `rg`, `glob`, and `read` calls.

This means the filesystem *is* the memory. Not metaphorically — structurally. Every file name, every directory choice, every import path is information the agent uses to orient itself. A well-structured codebase answers the agent's questions instantly. A poorly structured one forces it to read dozens of files to answer what a single glob pattern should have revealed.

## The cost of unstructured code

Three things break down in unstructured projects:

**Token waste.** A fresh session on a messy codebase spends thousands of tokens on exploration — reading `utils.py` just to see what's in it, grepping broad patterns because specific ones don't apply, opening files speculatively because naming doesn't tell the agent anything. That context is gone by the time the actual work starts.

**Wrong placement.** When the agent can't infer the convention from existing code, it invents one. Sometimes it invents the *same* convention that exists elsewhere (lucky). Sometimes it invents a different one (drift). Over many sessions, drift compounds — you end up with three naming styles and four directory layouts because no single session could see the big picture.

**Inconsistent work across sessions.** Session A decides to put validators in `src/auth/validators.py`. Session B, a week later, can't see that decision and puts them in `src/auth/auth_validators.py`. Neither is wrong, but now you have both, and the next session has to guess.

## What structure solves

Consistent, grep-friendly structure is persistent memory. When every domain looks like:

```
src/payment/
  __init__.py
  payment_service.py
  payment_types.py
  payment_test.py
```

...a fresh agent reads ONE domain and infers the pattern for all of them. Adding a new `refund` domain takes one prompt because the structure tells the agent exactly what files to create and where.

This is the difference between CLAUDE.md (explicit, limited to ~200 lines) and the codebase itself (implicit, unlimited). CLAUDE.md is the constitution. The codebase is the case law. Both matter.

## Selection pressure

There's a deeper pattern here: every session restart is a test of the structure. If a fresh session re-discovers the codebase easily, the structure survived — it's fit. If the session flounders, the structure failed.

This creates real evolutionary pressure. Structures that waste tokens get fixed because someone notices the waste. Structures that cause wrong placements get fixed because someone has to review and correct the output. Over time, the codebase evolves toward forms that are genuinely easier for agents to navigate.

semantic-gravity makes this pressure explicit and automated. The fitness score measures how well the codebase survives a cold start. The hooks apply pressure continuously, not just at review time. The trend log makes evolution visible.

## What it costs

Some users will ask: isn't this over-engineering? Couldn't you just write cleaner code?

The honest answer: yes, you could, and if you do, semantic-gravity's score will be high and it'll rarely block you. The tool doesn't impose structure on teams that already have it. It catches drift for teams that don't have time to police conventions manually — which is most teams working with AI agents that produce code faster than humans can review it.

The cost is:
- One `.structure.yaml` file (~50 lines)
- One script directory (~500 lines of Python)
- Three lifecycle hooks (~30 lines of JSON)

The return is:
- Every session starts oriented
- Every file creation is validated against conventions
- Every session ends with a measurable fitness score
- Drift is impossible to ignore

That's a reasonable trade for any codebase a team expects to work with for more than a month.

## How to talk about it

If a user is skeptical: concede that this only matters if they use AI agents regularly. For one-off scripts or solo weekend projects, don't bother.

If a user is enthusiastic: help them start small. Infer a config from their existing code (don't impose defaults), fix the top-penalty category only, and measure the score change. Momentum matters more than perfection.

If a user is frustrated by a blocking hook: remind them hooks can be disabled. The gate exists to catch drift; if the "drift" is actually a deliberate exception, edit `.structure.yaml` to permit it. Conventions should evolve with the project.
