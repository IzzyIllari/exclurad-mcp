# Leg D, Codex arm — gpt-5.6-terra replication on a second machine (server v0.1.1)

90 conversations: 1 model × 2 conditions × 3 reps × 15 tasks. Codex CLI
0.153.4 (`--expect-harness-version 0.153.4`), ChatGPT login, exclurad-mcp
**v0.1.1**, started 2026-09-09T23:48:15Z.

**This is a replication, not new data.** It re-runs the `gpt-5.6-terra` cells
of `../2026-09-09-agent-accuracy-codex/` (commit `c197248`) on a different
machine, under a different Codex account, against the same server version
(0.1.1), the same harness binary (sha256 `b973d440acac501f…`) and the same
task suite (`suite_sha256 21ee515822f1c51b…`, identical in both runs). Nothing
here is pooled with the original; it exists to say whether that arm's terra
findings hold when the machine and the account change.

## Result: they hold

| | office Mac (`c197248`) | this laptop | |
|---|---|---|---|
| with-server | 93% (42/45) [82–98] | 91% (41/45) [79–96] | overlapping |
| baseline | 78% (35/45) [64–87] | 82% (37/45) [69–91] | overlapping |
| ill-posed caught, with-server | 83% (15/18) | 83% (15/18) | identical |
| ill-posed caught, baseline | 83% (15/18) | 83% (15/18) | identical |
| false refusal of a well-posed request | 0/15 both conditions | 0/15 both conditions | identical |

The with-server gain is +15 points on the office Mac and +9 here. Both
confidence intervals overlap heavily in both conditions, so the two runs
disagree about the size of the gain and agree about its direction.

**13 of the 15 tasks reproduce exactly, in both conditions**, including both
findings the original arm rests on:

- **`ip-04` fails 0/3 in both conditions**, exactly as on the office Mac. This
  is the `q2_positive` suggestion string being read as an instruction: the
  agent calls `preflight_check` on Q² = −0.5, gets a FAIL whose suggestion
  reads "Use a positive Q2 …", and generates at +0.5 with a "sign convention
  corrected" flag. Reproducing this on a second machine and account rules out
  a one-machine artefact. (Fixed later in server v0.1.2 — see `79cd42d` and
  `2236ab5`, where ip-04 goes 0/18 → 17/18. This directory is the v0.1.1
  behaviour it was fixed from.)
- **`wp-04` baseline fails 0/3**, again matching exactly.

The two tasks that differ are `fx-01` (office 3/3 with-server, 0/3 baseline;
here 2/3 and 1/3) and `wp-05` baseline (2/3 there, 3/3 here) — single-rep
differences at k=3, which is the run-to-run noise this design has.

## Run integrity

90/90 scored, 0 timeouts, 0 missing `outcome.json`, 0 bypass attempts
(`skip_preflight=true` never requested; `run_exclurad`/`smoke_test` never
attempted). Codex records tokens only, so the cost columns read n/a. Median
wall 41 s with-server, 44 s baseline.

**Outcomes emitted as chat text, per condition: 0 and 0.** Every conversation
wrote `outcome.json` to disk, so the chat-text delivery failure that dominates
some OpenCode models does not arise here. Note that this run predates
`de511e4` (the runner's final-text fallback), so `result.json.final_text` is
null throughout and `chat_text_outcome()` could not have detected it anyway —
but with zero missing outcomes there is nothing for it to detect.

## Why only terra: sol and luna were destroyed by a quota limit

The run covered all three models. The `gpt-5.6-sol` and `gpt-5.6-luna`
directories were **deleted rather than reported**, because the ChatGPT
subscription quota expired mid-run and killed most of their conversations:

| model | condition | usable | killed by quota |
|---|---|---|---|
| gpt-5.6-terra | with-server | 45 | 0 |
| gpt-5.6-terra | baseline | 45 | 0 |
| gpt-5.6-sol | with-server | 23 | 22 |
| gpt-5.6-sol | baseline | 8 | 37 |
| gpt-5.6-luna | with-server | 28 | 17 |
| gpt-5.6-luna | baseline | 0 | 45 |

121 of the run's 270 conversations died on
`"You've hit your usage limit. Try again at Sep 10th, 2026 2:24 AM."`,
between 2026-09-10T00:03:14Z and 07:36:43Z. Terra ran first and finished
before the limit was reached. There were no other failures in the run.

A quota kill ends a conversation in about 2 s with `num_turns=1` and no
output, so **an affected cell scores 0 while looking like a fast, confident
model failure.** All 121 were originally labelled `terminal_reason: null`.
This run is why `("hit your usage limit", "provider_quota_exhausted")` was
added to `TERMINAL_SIGNATURES` in `run_leg_d.py`; the labels here are
backfilled with it.

sol and luna were not re-run: clean k=3 cells for both already exist in
`../2026-09-09-agent-accuracy-codex/`.

## Provenance

`provenance.json` records `harness_version: codex-cli 0.153.4`,
`harness_binary.sha256: b973d440acac501f…`, `server_installed.version: 0.1.1`,
`max_turns: 25`, `timeout: 900 s`, `parallel: 2`, `max_attempts: 3`.
Per PROTOCOL.md "Harnesses", the Codex shell stays available in both
conditions (workspace-write sandbox) and `run_exclurad` cannot be removed per
tool, so Codex rows are a labelled replication and are never pooled with the
OpenCode or Claude Code rows.
