# Ablation protocol: which part of the server carries the gain?

Leg D shows that agents with the server are more accurate than agents
reading the Fortran, by +16 to +18 points on frontier models and up to +60
on open models. It does not say **why**. The server offers four distinct
things and the study has so far treated them as one:

| | what it supplies |
|---|---|
| `list_channels`, `resolve_tables` | the channel narrative: thresholds, quirks, which table is really loaded, defaults |
| `preflight_check` | validation: a verdict per point, a message, and a suggestion |
| `generate_input` | a correctly formatted file: header, chunking, blank lines, trailer |
| `run_exclurad`, `parse_output` | execution and output reading (leg E only) |

Anyone building an MCP server for their own legacy code needs to know which
of these to build first. That is what this ablation answers.

## Arms

All arms are **with-server only** at k=3 on the full 15-task suite, server
v0.1.2. Baseline is never re-run: it does not touch the server. The control
is the existing v0.1.2 with-server data, so no control run is needed.

| arm | how | server change |
|---|---|---|
| **A — control** | full server | none (existing data) |
| **B — no validation** | withhold `preflight_check` | none: harness tool gate |
| **C — no channel knowledge** | withhold `list_channels`, `resolve_tables`, `describe_build_slots` | none: harness tool gate |
| **D — file writer only** | withhold everything except `generate_input` | none: harness tool gate |
| **E — validation without advice** | `preflight_check` returns verdict + message, `suggestion` blanked | env switch, see below |

Arms B, C and D need **no server code change at all** — they are the same
tool gates the protocol already uses to withhold `run_exclurad` in leg D:

- Claude Code: `--disallowedTools mcp__exclurad__preflight_check,...`
- OpenCode: `tools` map entries `exclurad_preflight_check: false`
- Codex: drop the names from `mcp_servers.exclurad.enabled_tools`

Arm E needs one env-gated switch in the server, `EXCLURAD_ABLATE_SUGGESTIONS=1`,
which empties `CheckResult.suggestion` in the preflight report and changes
nothing else. It must not alter default behaviour, and provenance must record
the variable. Add it in a commit of its own, before the run, with a test that
the default path is unchanged.

## Models

Chosen for headroom, not for coverage. A model already at 45/45 can only
lose points, which is informative; a model at 40% baseline shows where the
gain lives.

| model | harness | why |
|---|---|---|
| NVIDIA Nemotron 3 Super 120B | OpenCode | largest measured gain (+60) |
| gpt-oss-120b | OpenCode | large gain (+31), different failure profile |
| gpt-5.6-terra | Codex | frontier reference; the harness where suggestion strings demonstrably drive behaviour |

Arms B, C, D on all three: 3 arms x 3 models x 3 reps x 15 tasks = **405
conversations**. Arm E on the three Codex models only (sol, terra, luna),
since that is the only harness where ip-04 compliance moved with the
wording: **135 conversations**. Everything is free on the LANL gateway and
on Codex auth.

## What each result would mean

- **B collapses to near baseline** → the validator is the product; the file
  writer is a convenience. This is the expected result and the one the
  leg D failure taxonomy predicts (the fixable-class failures are all
  things preflight catches).
- **B holds up** → the channel knowledge in `list_channels` is doing the
  work, and a much smaller server would have sufficed.
- **D alone recovers most of the gain** → the format is the hard part, not
  the physics, and the lesson for others is "write the file generator".
- **E ≈ A** → the suggestion strings are decoration and the verdict is what
  matters. **E ≈ B** → the advice text is the mechanism, which would make
  the three v0.1.1/v0.1.2 wording defects the central finding of the study
  rather than a side note.

Arm E is the sharpest test of the study's own recurring theme: three
separate times, wording inside a FAIL result decided what the agent did.

## Reporting

`report_leg_d.py` per arm; the combined report gains an `arm` column
alongside `harness` and `server`. Two standing rules from
`LEG_D_RESULTS.md` apply: never pool Codex with the other harnesses, and
state the denominator and the condition on every ratio.
