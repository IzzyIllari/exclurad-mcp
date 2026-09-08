# Leg D run protocol

How an agent-accuracy run is conducted so that different models and
conditions are comparable. The suite is `tasks.json` (versioned; results
must record the suite version). Scoring is `../score_agent_run.py` —
deterministic checks only, no LLM judges.

## Conditions

Each model runs the full suite under two conditions:

- **with-server** — the agent has the exclurad MCP server registered and is
  told to use it.
- **baseline** — the agent has no server; it gets the EXCLURAD Fortran
  source, the repository README, and file-writing ability. Nothing else.

Same prompts, same order, one task per fresh conversation (no learning
across tasks). Temperature and model ID recorded per run.

## Prompt template

Each task's conversation starts with exactly:

> You are helping a nuclear physicist run the EXCLURAD radiative-corrections
> code. Request: {request}
>
> When you are done, write an `outcome.json` in the working directory:
> `{"action": "generate" | "fix_and_generate" | "generate_with_warning" |
> "refuse", "input_files": [...], "flags": [...], "explanation": "..."}`.
> Write any EXCLURAD input files you produce next to it. If the request is
> physically impossible, refuse and say why. If it needs a correction or
> carries a known risk, apply or flag it and explain.

`{request}` is the task's `request` field, verbatim.

## Collecting a run

One directory per run: `<run>/<task-id>/outcome.json` plus any input files.
Score with:

```bash
PYTHONPATH=src python3 benchmarks/score_agent_run.py \
    --suite benchmarks/agent_tasks/tasks.json \
    --run-dir <run> --json <run>/scores.json
```

A task passes only if the direction (proceed/refuse), the file validity
(parseable, ≤10 points/file, correct header, preflight-clean), the required
fixes/flags, and the required explanation facts all check out.

## Reference runs

Two synthetic runs pin the scorer's dynamic range (regenerate with
`../make_reference_runs.py <outdir>`; re-checked 2026-09-08 under the
amended scorer):

- a **perfect** protocol-following run scores 15/15;
- a **naive** run that proceeds verbatim on every request scores 5/15
  (all well-posed pass; every fixable and ill-posed task fails with the
  physics reason named). This is the expected shape of a no-server baseline
  that never validates.

## Ground truth hygiene

`../verify_task_ground_truth.py` re-derives every task label from
`validators.py` (exit 0 = consistent). Run it whenever the suite or the
validators change. Suite task ip-04 exists because designing it exposed a
real validator gap: before 2026-07-22, a negative-Q² request passed every
preflight gate except the table-coverage warning (`check_q2_positive` was
added, with tests, as a result).

## What the study reports

Per model × condition: pass rate overall and by class, plus the ill-posed
catch rate (the safety-critical number: fraction of impossible requests
refused with the physics stated). The claim under test: with the server,
pass rates converge across models; without it, they diverge — correctness
lives in the tooling, not the model.

## Amendments of 2026-09-08 (first agent runs; `../run_leg_d.py`)

Fixed before the pilot was scored and applied identically to both
conditions. Anything below that changes what "pass" means is listed so a
reader can judge it.

### Harness

- **Agent**: Claude Code CLI in headless mode (`claude -p`), one task per
  fresh conversation, `--output-format stream-json` captured whole as
  `transcript.jsonl`. Prompt delivered over stdin (`prompt.txt`), built
  from the template above with the task's `request` substituted verbatim.
- **Isolation**: every conversation runs in its own fresh working
  directory under `~/.cache/exclurad-mcp-leg-d/<run>/…`, outside any git
  repository, so no project `CLAUDE.md` and no project memory can load.
  `--strict-mcp-config` hides every personally registered MCP server;
  `--no-session-persistence` keeps the runs out of the session store.
  `--restricted` confines the file tools to the working directory and
  skips user/project settings; a probe conversation confirmed that under
  it the global `~/.claude/CLAUDE.md` does not load either.
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` turns off the CLI's auto-memory:
  in a first pilot (discarded, see the report) 6 of 30 conversations
  spent turns writing memory notes about the user into their per-cwd
  memory directory. **Remaining known leak**: the CLI puts the account
  email address and the date into the model's context. Nothing in
  context mentions EXCLURAD or physics.
- **Tool gates**: built-in tools are restricted with `--tools` to
  `Read, Write, Glob, Grep` in both conditions. No Bash, no web tools, no
  subagents. `Write` cannot leave the working directory. Permission mode `dontAsk` with `--allowedTools` covering
  exactly those tools (plus `mcp__exclurad__*` in with-server), so nothing
  can prompt or hang.
- **with-server**: `--mcp-config` registers `exclurad-mcp` (absolute path;
  Claude Code spawns MCP servers outside any conda env) with
  `EXCLURAD_WORK_DIR_ETA` set. `run_exclurad` and `smoke_test` are
  removed with `--disallowedTools`. Rationale: the outcome contract asks
  for input files and a decision, not results; a 33 s/point Fortran run
  would make the two conditions incomparable on time and cost; and the
  pion channel has no built checkout on this machine, so allowing runs
  would have made two tasks channel-asymmetric. The eight remaining tools
  (`list_channels`, `resolve_tables`, `preflight_check`, `generate_input`,
  `map_failures`, `describe_outputs`, `parse_output`,
  `describe_build_slots`, `generate_build`) stay available.
- **baseline**: empty `--mcp-config`. The working directory holds
  read-only copies of both source trees, `./eta` (the IzzyIllari fork:
  `exclurad.F`, `fint.F`, `mpintp.inc`, `spp.inc`, `Makefile`, the
  template `input.dat`, `examples/`, and the repository `README.md`) and
  `./pion` (JeffersonLab upstream: the same files minus `examples/`).
  Excluded on purpose: `build/`, the `.tbl` tables, `slurm/`, SCons
  files, and the fork's `scripts/` (its grid generator encodes the same
  conventions the server does and would leak them). The second pilot
  used the η tree only, and the sonnet baseline refused the π⁺ task
  wp-03 on the reasonable grounds that the checkout could not run pions;
  both conditions have been channel-symmetric since (the server gets
  `EXCLURAD_WORK_DIR_PIPLUS` pointing at the same upstream checkout).
- **Condition framing**: one sentence is appended to the system prompt
  (`--append-system-prompt`), so the user turn stays identical across
  conditions:
  - with-server: *"An MCP server named `exclurad` is registered in this
    session; use its tools to validate kinematics and generate input
    files."*
  - baseline: *"The EXCLURAD Fortran source trees are in the working
    directory, read-only: ./eta (eta configuration, IzzyIllari fork) and
    ./pion (pi+ configuration, JeffersonLab upstream), each with
    exclurad.F, fint.F, *.inc, Makefile, README.md and a template
    input.dat. There is no compiler or shell available; you cannot build
    or run the code."*
- **Caps**: `--max-turns 25` and a 900 s wall-clock timeout per
  conversation (the process group is killed; whatever was written is
  scored as is). A conversation that ends in a rate-limit rejection or an
  API error is not an outcome: the runner pauses all workers until the
  reported reset time and reruns it from a fresh directory (up to 3
  attempts; the failed attempt's transcript is kept as
  `<task>.attemptN/`). Hitting `--max-turns` is an outcome and is scored. Model effort is the CLI default; temperature is not
  user-settable in Claude Code and is recorded as "default".
- **Repeats**: k = 3 per (model, condition, task); pass@1 is the mean pass
  rate over all conversations, pass^k the fraction of tasks passed in all
  k reps.
- **Cost** is the CLI's own `total_cost_usd` (list price) per
  conversation; the runs were made on a subscription, so it is an
  equivalent, not a bill.

### Scorer

- `parse_input_file` now emulates the Fortran list-directed reader
  (`read(5,*)`) instead of keying on the comment text `no. of points`:
  blank records are skipped, the rest of a record is discarded once a
  read has its items, a non-numeric token where a value is due is a
  parse failure. Files the Fortran would read are parseable; files it
  would reject are not. The old parser rejected a valid one-point file
  because its comment said `number of points`.
- `manifest.csv`, the companion file `generate_input` writes, is ignored
  when an agent lists it under `input_files`. It is not an input and the
  outcome contract never asked for it.
- The two reference runs (perfect 15/15, naive 5/15) are unaffected: the
  server-generated files they contain parse identically under both
  parsers.
- A `required_flag` (`near_threshold`, `vcut_negative`) counts as raised
  when the exact name appears in `flags`, or the agent chose the
  flag-carrying action `generate_with_warning`, or any flag it wrote
  contains the concept keyword (`threshold`; `vcut`/`negative`). The
  prompt never states the suite's flag vocabulary, and in the pilot every
  agent that warned correctly wrote its own name for the flag
  (`near_threshold_integrator_risk`, `vcut = -0.1 is negative`). The
  explanation must still state the physics (`must_mention_any`), and the
  naive reference run (plain `generate`, no flags) still fails both tasks.

### Suite wording noted, not changed

Task wp-04 says "25 points … phi* from 0 to 345 in 25 steps", which the
ground truth reads as 25 points at a 14.375° step. Agents sometimes read
it as the 15° sweep (24 points) and say so. The suite is versioned and
was not edited mid-study; the effect is symmetric across conditions and
is called out in the report's per-task table.
- An `outcome.json` written one directory below the working directory
  (inside `./eta` or `./pion`, which only the baseline has) is accepted,
  with declared input paths resolved relative to either location. Two
  sonnet baseline conversations in the main run wrote a correct outcome
  beside the source tree they had been reading; the misplacement exists
  only because the baseline layout has subdirectories, so penalising it
  would have been a harness artefact. The scorer records the location as
  a note. Absolute declared paths are taken as given (none occurred).
- `must_mention_any` facts are searched in `explanation` and in the
  `flags` strings together. Two with-server agents on fx-04 put the
  whole physics statement ("negative vcut switches EXCLURAD to its
  'v' interpretation; default 0.166") in the flag text and only a
  summary in `explanation`. The reason was stated in the outcome; where
  in the outcome is not a physics criterion.

## Harnesses (added 2026-09-08 for the cross-vendor study)

The agent loop is a treatment variable too, so every result directory
records `harness` in `provenance.json` and every conversation records it
in `result.json`. Rows from different harnesses are never pooled; the
report shows them side by side.

| harness | command | shell off | file tools confined to cwd | step cap | cost recorded | run_exclurad removable |
|---|---|---|---|---|---|---|
| `claude` (Claude Code) | `claude -p --restricted …` | yes | yes | `--max-turns` | yes (list price) | yes |
| `opencode` (OpenCode) | `opencode run --format json --pure --agent legd` with a per-conversation `opencode.json` | yes (`tools.bash=false`, `permission.bash=deny`) | yes (`permission.external_directory=deny`) | `agent.legd.maxSteps` | yes (from the provider's declared price table) | yes (`tools.exclurad_run_exclurad=false`; to be confirmed by a probe conversation) |
| `codex` (Codex CLI) | `codex exec --json --sandbox workspace-write --ignore-user-config -c max_turns=N` | **no** (shell stays; writes confined to cwd) | writes yes, reads no | `max_turns` | no (tokens only) | **no** |

OpenCode is the primary harness for the cross-vendor comparison because it
is the only one of the three that reaches models from several vendors
through one route (the LANL gateway) *and* enforces the protocol's tool
policy. Codex cells are a labelled replication with two deviations
(shell available; `run_exclurad` reachable), and its baseline framing
sentence says "Do not build or run the code; produce input files and
outcome.json only" instead of denying that a shell exists. The condition
framing is delivered through OpenCode's `instructions` file
(`LEGD_CONDITION.md`) and Codex's `AGENTS.md`; the user turn is identical
everywhere.

Before any scored OpenCode or Codex run, a probe conversation on the run
machine must confirm: the advertised tool list under the `legd` agent
(no bash, no edit/apply_patch, `exclurad_run_exclurad` absent or denied),
that the MCP server connects, that a write outside the working directory
is refused, and whether any global instructions file (`AGENTS.md`) is
loaded. Record the probe transcript beside `provenance.json`.
