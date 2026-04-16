# semantic-gravity

A Claude Code skill that keeps your codebase honest about intent.

## What this is

Code is no longer just the output of a mental model. In augmented-AI development, code *is* the shared mental model — because the agent has no other place to find it, and you can't hold the whole thing in your head either. Your understanding ages. Conversations are gone when the session ends. The filesystem is the only thing that doesn't forget.

`semantic-gravity` is the force that pulls naming and structure toward the concepts they represent. When you work with a coding agent, every name you choose is a contract between your intent in the moment you wrote it and every future session — yours or the agent's — that has to act on that intent. When names and structure drift from what you meant, the contract breaks silently. The agent keeps running, but it's running on a stale understanding of your goals.

This skill keeps the gravity strong.

## The problem it solves

Teams used to solve this by meeting, arguing, and agreeing on vocabulary before writing code. Small teams and solo developers working with AI agents don't have that room of stakeholders anymore. The synchronization problem didn't disappear — it moved. The endpoints are now:

- **You now** ↔ **you in three months**
- **You** ↔ **the agent in its next session**
- **Your intent** ↔ **what the code actually encodes**

The weakest point in this system is human memory and clarification. You forget what you meant. You rephrase things inconsistently. You clarify something in chat, the chat ends, and the clarification is gone. Every unclarified drift is technical debt until it's written into the code or the config.

The agent doesn't have these problems — because the agent has nothing at all. Every session starts from the filesystem. If the filesystem still reflects your intent, the agent reconstructs it. If the filesystem has drifted, the agent acts on stale meaning and produces work that technically runs but violates the implicit rules that used to live in your head.

## What the skill does

`semantic-gravity` enforces three things:

1. **Names carry meaning.** Files are prefixed with their domain. Functions use the project's real vocabulary. Error messages include domain-scoped codes that trace from log to source. A fresh session reading a filename should know what's inside before opening it.

2. **Structure mirrors intent.** The directory layout reflects how you actually think about the problem, not how some framework says code should be organized. Changes to one concept touch one place. The import graph is a readable map of how concepts depend on each other.

3. **Drift is measurable.** Every session records a fitness score — not a code-quality score in the old sense, but a measurement of whether the codebase is still honest. If the score drops, something in your head diverged from something on disk, and the filesystem is the one that will still be here tomorrow.

## How it works

Three modes, all driven by a single `.structure.yaml` at the project root.

- **Scaffold** — create new modules with names and structure that match your existing vocabulary, so new code extends the gravitational field instead of fighting it.
- **Audit** — score the codebase's fitness and surface the specific places where naming and structure have drifted. Lead with the biggest drift, not the longest list.
- **Evolve** — install lifecycle hooks that apply pressure continuously. A pre-write hook blocks file creations that would weaken the naming field. A session-start hook shows the current fitness score as the first thing the agent sees. A session-end hook appends the score to a trend log so evolution is visible across sessions.

The config is yours to define. `semantic-gravity` doesn't prescribe a single way to organize code — it gives you a place to encode your conventions once, then holds you and the agent to them every session thereafter.

## The deeper claim

Every session restart is a test of whether the code is still the truth. An agent with no memory of your conversations has to reconstruct intent from the filesystem alone. If it can, your code is still a faithful record of what you meant. If it can't, the code has started lying — quietly, in ways you may not notice until something breaks in production.

Naming is the highest-leverage decision in the whole stack. Phil Karlton's famous quip — "there are only two hard things in computer science: cache invalidation and naming things" — has been repeated for decades because it lands as both funny and true. What his colleagues eventually noticed is that both halves are hard for the same reason: they require predicting the future. A cache entry is correct only if you know what data will change later. A name is good only if it survives into contexts you haven't encountered yet.

That framing explains exactly what `semantic-gravity` is doing. Every name you write is a contract with future sessions you haven't had — yours, the agent's, a collaborator's. A well-named file is a contract that holds. A badly named file is a Rorschach test, and the agent will project whatever interpretation is plausible — not necessarily yours.

`semantic-gravity` is the discipline of refusing to let that happen.

## When to use it

Use it when:
- You work with a coding agent regularly and want your code to survive the amnesia between sessions
- Your codebase will outlive any single session, pairing session, or sprint
- You care more about being understood correctly six months from now than about moving fast today

Skip it when:
- You're prototyping something you'll throw away
- The domain is still being discovered and conventions don't exist yet
- You're the only reader, working in a single session, and you remember everything

## Install

1. Move `semantic-gravity.skill` into `.claude/skills/` (project-scoped) or `~/.claude/skills/` (all projects).
2. Restart Claude Code.
3. In a Python project, ask: *"Help me set up naming conventions for this project"*, or *"how's my codebase holding up?"*, or *"set up hooks to keep my structure honest"*.

The skill triggers on language about naming, structure, drift, conventions, and code discoverability. You shouldn't need to invoke it manually.

## Requirements

- Python 3.8+
- PyYAML (`pip install pyyaml`)

## License

Use it, change it, share it. The ideas matter more than the implementation.