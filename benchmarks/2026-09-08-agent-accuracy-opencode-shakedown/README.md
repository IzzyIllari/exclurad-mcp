# OpenCode shakedown, 2026-09-08 — harness artefact, not a result

**No data in this directory is used in any table, figure or reported number.**
It is kept as the record of a harness bug and its symptom. The scored OpenCode
results are in `../2026-09-09-agent-accuracy-opencode-priced/` (stage 1) and
`../2026-09-09-agent-accuracy-opencode-unpriced/` (stage 2).

Shape: `aiportal/aws-gov.gpt-5.6-luna`, tasks `wp-01` and `ip-04`, both
conditions, 1 rep. 8 `result.json` files including retry directories.

## What it shows

The four baseline conversations are recorded as
`subtype: error_during_execution, num_turns: null` while having `exit_code: 0`,
`outcome_json_present: true`, and real artefacts on disk — `wp-01` wrote
`eta_input_W1.6_Q2_1.0_costh0.5_phi90.dat` and `outcome.json` after 11 tool
calls. **The agent did the work; the runner could not capture the result.**

The transcripts are intact — 29 lines, all parseable JSON, ending cleanly on a
`step_finish`. They contain only `step_start`, `tool_use`, `text` and
`step_finish` events, with no terminating result event, and the baseline
conversations have no `session_export.json`. With nothing to parse a result
from, the runner fell back to `error_during_execution`. The two with-server
conversations in the same run parsed normally (`success`, 3 and 5 turns).

`transcript.jsonl` for baseline `wp-01` is 65301 bytes, just under the 65536
byte (64 KiB) pipe buffer. That is consistent with the `opencode export`
truncation the runner later fixed by writing the export to a file rather than
reading it through a pipe (see the comment in `probes/run_probes.py`:
"file, never a pipe (64 KiB truncation)"). The proximity is suggestive rather
than proven — the transcript itself is not truncated, and this README does not
claim more than the bytes support.

## Provenance gap

`provenance.json` records `harness_version: 1.18.28` but has no
`server_installed.version` and no `harness_binary.sha256`. It predates the
provenance hardening in `6b006d9`, so this run cannot be tied to a specific
server build. That alone disqualifies it from any reported table.
