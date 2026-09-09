# OpenCode shakedown, 2026-09-09 — harness artefact, not a result

**No data in this directory is used in any table, figure or reported number.**
It is the second harness-development shakedown, kept for the same reason as
`../2026-09-08-agent-accuracy-opencode-shakedown/`. The scored OpenCode results
are in `../2026-09-09-agent-accuracy-opencode-priced/` (stage 1) and
`../2026-09-09-agent-accuracy-opencode-unpriced/` (stage 2).

Shape: `aiportal/aws-gov.gpt-5.6-luna`, tasks `wp-01` and `ip-04`, both
conditions, 1 rep. 7 `result.json` files including retry directories.

## What it shows

Partial improvement over 2026-09-08, not a clean run. Both with-server
conversations parsed normally (`success`, 4 turns each), and baseline `ip-04`
now parses too (`success`, 5 turns) where on 09-08 it did not. Baseline
`wp-01` still fails on all three attempts with
`subtype: error_during_execution, num_turns: null`, while again having
`exit_code: 0`, `outcome_json_present: true`, and real artefacts on disk
(`input.dat` and `outcome.json` after 18 tool calls).

So the same result-capture failure as 09-08 persisted here for one of the two
baseline tasks: the transcript is intact — 42 lines, all parseable, ending
cleanly on a `step_finish` — but carries only `step_start`, `tool_use`, `text`
and `step_finish` events with no terminating result event.

**The 64 KiB explanation does not apply to this directory.** Baseline `wp-01`'s
transcript is 115514 bytes, well past the pipe buffer, and is not truncated.
Whatever ended the capture here is not the boundary that fits the 09-08 case.
It was not diagnosed further, because the runner was subsequently reworked and
the scored runs show no such failures: stage 1 captured results for 360/360
conversations, and stage 2 is running clean.

Anyone citing this directory should treat "post-fix, clean" as **not
established by it**. What establishes the fix is stage 1's 360/360 capture rate
with no `opencode_server_errors.log` and no agent fallbacks.

## Provenance gap

`provenance.json` records `harness_version: 1.18.28` but has no
`server_installed.version` and no `harness_binary.sha256`. Like the 09-08
directory it predates `6b006d9`, so it cannot be tied to a specific server
build, which by itself disqualifies it from any reported table.
