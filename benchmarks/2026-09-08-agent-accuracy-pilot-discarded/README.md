# Leg D pilot 1 (discarded) — 2026-09-08

Sonnet 5, both conditions, k = 1, 30 conversations, $4.82 list price.
Scored 14/15 with-server, 12/15 baseline under the amended scorer.

**Discarded, kept for the record.** Inspection of the transcripts showed
that 6 of the 30 child sessions (5 baseline, 1 with-server) spent turns
writing Claude Code auto-memory notes about the user into their per-cwd
memory directories under `~/.claude/projects` (each conversation had a
unique cwd, so nothing crossed between conversations, but the turns and
cost were contaminated and the global `~/.claude/CLAUDE.md` was in
context). The harness was fixed (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`,
`--restricted`, which also stops the global CLAUDE.md from loading) and
the pilot rerun. Recorded here because silently discarding failed
benchmark runs is how benchmarks stop being trustworthy.

This pilot also drove three scorer amendments listed in
`../agent_tasks/PROTOCOL.md` (list-directed parser, `manifest.csv`,
flag vocabulary).
