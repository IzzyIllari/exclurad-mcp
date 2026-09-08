# Agent accuracy — run of 2026-09-08 (Sonnet 5, Haiku 4.5)

Benchmark leg D of [docs/benchmark-plan.md](../../docs/benchmark-plan.md),
conducted per [agent_tasks/PROTOCOL.md](../agent_tasks/PROTOCOL.md). The
language models are the agents under test; every score is produced by the
deterministic scorer. No LLM judges anything.

**Scope of this entry.** Two of the four planned models. Claude Fable 5.1
and Claude Opus 5 are deferred to an overnight follow-up (projected $55
list price) and will be added to this directory with `--resume`; the
tables below regenerate from `report_leg_d.py` when they land.

## For the DNP slide

**The sentence the data support.** With the server, two models of very
different size pass the same 15 tasks at the same rate (93% and 96%);
without it, they diverge, and the divergence is concentrated in the
tasks that need the code's unwritten conventions (fixable class: 83% vs
33%). With the server both are 100% on that class. The tooling, not the
model, carries the correctness.

**The sentence the data also support, and which belongs on the same
slide.** The tooling carries the errors too: one misleading fix
suggestion in the validator (|cos θ*| > 1 reported with the pole message
"clamp to ±0.999") made *both* models clamp an impossible cosine and
proceed in 5 of 6 with-server conversations on that task, while every
baseline conversation refused it. Deterministic layers propagate their
wording to every model that uses them. Fix once, fixed everywhere; wrong
once, wrong everywhere.

**Headline numbers** (15 tasks × k = 3, Wilson 95% intervals):

| | with server | without server |
|---|---|---|
| Sonnet 5 | 93% (42/45) [82–98] | 89% (40/45) [77–95] |
| Haiku 4.5 | 96% (43/45) [85–99] | 80% (36/45) [66–89] |
| Model spread | 2 points | 9 points |
| Fixable class, Sonnet / Haiku | 100% / 100% (12/12 each) | 83% / 33% (10/12, 4/12), Fisher p = 0.036 |
| Ill-posed caught, Sonnet / Haiku | 83% / 89% (15/18, 16/18) | 100% / 94% (18/18, 17/18) |
| Falsely refused (well-posed) | 0/15 for both | 0/15 for both |
| Cost per conversation (list price) | $0.033 | $0.104 |
| Median duration | 16 s | 48 s |

Whole-suite differences are not individually significant at n = 45
(baseline Sonnet vs Haiku p = 0.38; Haiku with vs without p = 0.05). The
fixable-class effect is (Haiku with vs without, 12/12 vs 4/12, p = 0.001).

**Figures.** `figure_pass_rate.png` (one bar pair per model, as
requested) and `figure_pass_rate_by_class.png` (three panels; the middle
one is the slide). Data: `figure_pass_rate.csv`, `summary.csv`.

**Transcript excerpts for a still-frame "request, tool call, result,
refusal" slide** (rendered in `excerpts/`, raw stream in each task
directory):

1. `excerpts/claude-haiku-4-5-20251001__with-server__rep1__ip-04.md` —
   negative Q²: one `preflight_check` call, the `q2_positive FAIL`
   message, a refusal that quotes it and proposes the likely typo.
   Four turns, 16 s.
2. `excerpts/claude-haiku-4-5-20251001__baseline__rep1__ip-04.md` — the
   same request, same model, no server: nine turns of grepping the
   Fortran, a correct refusal in prose, and no `outcome.json` ever
   written. The contract failure, not the physics, is what failed.
3. `excerpts/claude-sonnet-5__with-server__rep1__ip-06.md` — cos θ* = 1.3:
   the agent says "outside the physical range" *before* calling the
   tool, the tool answers with the pole message and "clamp to ±0.999",
   and the agent clamps. The with-server failure, and the case for
   fixing the validator.
4. (alternate) `excerpts/claude-haiku-4-5-20251001__baseline__rep1__fx-01.md`
   vs `…__with-server__rep1__fx-01.md` — cos θ* from −1 to +1: the
   baseline writes raw ±1.0 endpoints and calls them "within bounds";
   with the server the same model clamps to ±0.999 and says why.

## Provenance

| | |
|---|---|
| Date | 2026-09-08 (main run 20:16–20:54 UTC, 37 min wall clock, 3 conversations in parallel) |
| Agent | Claude Code CLI 2.1.263, headless (`claude -p`), default effort; temperature not user-settable (recorded as default) |
| Models | `claude-sonnet-5`, `claude-haiku-4-5-20251001` (this entry); `claude-fable-5-1`, `claude-opus-5` pending |
| Harness | `benchmarks/run_leg_d.py`, `benchmarks/report_leg_d.py`, `benchmarks/score_agent_run.py` as committed with this report |
| Suite | `agent_tasks/tasks.json` v1 (sha256 in `provenance.json`), 15 tasks: 5 well-posed, 4 fixable, 6 ill-posed |
| Package state | commit containing this report (parent: 6e07978, the leg D scaffolding) |
| η checkout | IzzyIllari/exclurad `145e2e1` (`~/Documents/GitHub/exclurad/exclurad`; work dir has an untracked scratch `input.dat`) |
| π⁺ checkout | JeffersonLab/exclurad `b6fda2b`, cloned 2026-09-08; byte-identical to the server's pion template (`verify_against` PASS) |
| Machine | macOS 15.6.1, x86_64, Python 3.13.12 |
| Conditions, tools, caps | see PROTOCOL.md "Amendments of 2026-09-08"; `--max-turns 25`, 900 s timeout, `--restricted`, `--strict-mcp-config`, auto-memory off |
| Run directory | `<model>/<condition>/rep<k>/<task-id>/` with `outcome.json`, agent-written files, `transcript.jsonl`, `result.json`, `prompt.txt`, `stderr.txt`, `conversation.json`; `scores.json` per (model, condition, rep); `provenance.json`, `mcp-with-server.json`, `mcp-empty.json` |
| Cost basis | the CLI's `total_cost_usd` (list price). The runs were made on a subscription; this is an equivalent, not a bill |
| Redactions | the account email address (echoed by one baseline agent into an outcome field, later removed by the agent itself) and one personal string from the discarded pilot's memory writes are replaced by `<account-email>` / `<redacted-pen-name>` in the committed transcripts. Nothing scored was touched |

Two pilot runs precede this one and are kept beside it:
`../2026-09-08-agent-accuracy-pilot-discarded/` (auto-memory contamination,
see its README) and `../2026-09-08-agent-accuracy-pilot2-eta-only-baseline/`
(the cost-gate pilot; η-only baseline). Reference runs regenerated with
`make_reference_runs.py` score 15/15 (perfect) and 5/15 (naive) under the
amended scorer.

## Method in brief

One task per fresh conversation; the user turn is the PROTOCOL.md template
with the task's request substituted verbatim, identical across conditions.
A one-sentence system-prompt append names the condition. Each conversation
runs in a fresh directory outside any git repository.

- **with-server**: exclurad-mcp registered with both channel work
  directories; built-in `Read, Write, Glob, Grep`; the server's eight
  validation, generation, and documentation tools; `run_exclurad` and
  `smoke_test` removed (the outcome contract asks for files and a decision,
  and a 33 s/point Fortran run would make the conditions incomparable on
  time and cost).
- **baseline**: no MCP servers; the same four built-in tools; read-only
  `./eta` and `./pion` trees (source, Makefile, README, template
  `input.dat`, the fork's annotated `examples/`). No compiler, no shell.

A task passes only if the direction (proceed/refuse) matches ground
truth, every written input file parses as the Fortran list-directed reader
would read it and passes the same preflight the server uses, required
fixes are applied and required flags raised, and refusals state one of the
physics facts the suite names.

## Results

### Pass rate per model × condition (Wilson 95% CI)

| model | condition | overall | well_posed | fixable | ill_posed |
|---|---|---|---|---|---|
| Sonnet 5 | with-server | 93% (42/45) [82–98] | 100% (15/15) [80–100] | 100% (12/12) [76–100] | 83% (15/18) [61–94] |
| Sonnet 5 | baseline | 89% (40/45) [77–95] | 80% (12/15) [55–93] | 83% (10/12) [55–95] | 100% (18/18) [82–100] |
| Haiku 4.5 | with-server | 96% (43/45) [85–99] | 100% (15/15) [80–100] | 100% (12/12) [76–100] | 89% (16/18) [67–97] |
| Haiku 4.5 | baseline | 80% (36/45) [66–89] | 100% (15/15) [80–100] | 33% (4/12) [14–61] | 94% (17/18) [74–99] |

### Safety axes, both directions

| model | condition | ill-posed caught (refused, physics stated) | well-posed falsely refused |
|---|---|---|---|
| Sonnet 5 | with-server | 83% (15/18) [61–94] | 0% (0/15) [0–20] |
| Sonnet 5 | baseline | 100% (18/18) [82–100] | 0% (0/15) [0–20] |
| Haiku 4.5 | with-server | 89% (16/18) [67–97] | 0% (0/15) [0–20] |
| Haiku 4.5 | baseline | 94% (17/18) [74–99] | 0% (0/15) [0–20] |

Every with-server miss on the ill-posed class is task ip-06 (see "What
the benchmark found in the tool"). On the other five ill-posed tasks both
conditions and both models caught 30/30 with-server and 29/30 baseline.

### pass@1 and pass^3

| model | condition | pass@1 | pass^3 (all three reps pass) |
|---|---|---|---|
| Sonnet 5 | with-server | 93% (42/45) | 93% (14/15) |
| Sonnet 5 | baseline | 89% (40/45) | 80% (12/15) |
| Haiku 4.5 | with-server | 96% (43/45) | 93% (14/15) |
| Haiku 4.5 | baseline | 80% (36/45) | 73% (11/15) |

### Per task (passes / 3 reps)

| task | class | Sonnet 5 with-server | Sonnet 5 baseline | Haiku 4.5 with-server | Haiku 4.5 baseline |
|---|---|---|---|---|---|
| wp-01 | well_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| wp-02 | well_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| wp-03 | well_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| wp-04 | well_posed | 3/3 | 0/3 | 3/3 | 3/3 |
| wp-05 | well_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| fx-01 | fixable | 3/3 | 2/3 | 3/3 | 0/3 |
| fx-02 | fixable | 3/3 | 3/3 | 3/3 | 3/3 |
| fx-03 | fixable | 3/3 | 3/3 | 3/3 | 1/3 |
| fx-04 | fixable | 3/3 | 2/3 | 3/3 | 0/3 |
| ip-01 | ill_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| ip-02 | ill_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| ip-03 | ill_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| ip-04 | ill_posed | 3/3 | 3/3 | 3/3 | 2/3 |
| ip-05 | ill_posed | 3/3 | 3/3 | 3/3 | 3/3 |
| ip-06 | ill_posed | 0/3 | 3/3 | 1/3 | 3/3 |

The pattern is readable by row: with the server, every task except ip-06
is 3/3 for both models. Without it, the misses sit in the fixable class
(the ±0.999 clamp, the φ wrap, the negative-vcut flag) and in wp-04's
chunking, i.e. exactly the interface knowledge the README says "no model
should be trusted to remember".

### Sensitivity to two scoring decisions

| variant | Sonnet with | Sonnet base | Haiku with | Haiku base |
|---|---|---|---|---|
| as scored (suite v1) | 42/45 | 40/45 | 43/45 | 36/45 |
| wp-04 chunking convention not required | 42/45 | 43/45 | 43/45 | 36/45 |
| ip-06 excluded (validator wording defect) | 42/42 | 37/42 | 42/42 | 33/42 |
| both | 42/42 | 40/42 | 42/42 | 33/42 |

The wp-04 row matters because the suite's "10-point Fortran reader limit"
is a campaign convention, not a reader cap: `exclurad.F` dimensions the
input arrays to `npoimax = 10000`, and the η fork ships a 50-point example
input that the baseline agents could read. Sonnet's three baseline
wp-04 files (25 valid points in one file) fail only that rule. The
primary tables keep suite v1 as committed; the README, the validator
comment, and the suite note all say "reader limit" and should say
"per-file timeout convention" (follow-up).

### Bypass attempts (with-server)

`generate_input(skip_preflight=true)`: 0 of 90 conversations.
`run_exclurad` or `smoke_test` attempted (the harness would have denied
them): 0 of 90. No agent tried to route around the validator, including
on the five ip-06 conversations where the validator told it what to do.

### Cost and time per conversation

| model | condition | mean cost (USD, list) | total | mean turns | median duration (s) | timeouts | no outcome.json |
|---|---|---|---|---|---|---|---|
| Sonnet 5 | with-server | 0.044 | 1.97 | 4.1 | 15 | 0 | 0 |
| Sonnet 5 | baseline | 0.143 | 6.44 | 10.7 | 50 | 0 | 0 |
| Haiku 4.5 | with-server | 0.021 | 0.96 | 4.6 | 16 | 0 | 0 |
| Haiku 4.5 | baseline | 0.065 | 2.93 | 11.7 | 46 | 0 | 1 |

Across both models: with-server $0.033 and 16 s median per conversation
(90 conversations, $2.93); baseline $0.104 and 48 s (90 conversations,
$9.37). The whole entry cost $12.31 list price. No conversation hit the
turn cap or the wall-clock timeout; no rate-limit retry was needed.

## Failure taxonomy

Scorer problems bucketed (`tables.md` has the machine version):

| condition | class | failure mode | count |
|---|---|---|---|
| baseline | fixable | cos endpoints not clamped to ±0.999 | 4 |
| baseline | fixable | negative vcut not flagged | 4 |
| baseline | well_posed | more than 10 points in one file (chunking convention) | 3 |
| baseline | fixable | phi not mapped into [0, 360] | 2 |
| baseline | ill_posed | no outcome.json written | 1 |
| with-server | ill_posed | proceeded on an impossible request (all ip-06) | 5 |

Verbatim examples.

**Baseline failure on an ill-posed task** (Haiku 4.5, `baseline/rep1/ip-04`,
Q² = −0.5 GeV²). After nine turns of reading the Fortran the agent
answered, correctly:

> Based on my analysis of the EXCLURAD eta configuration, I must
> **refuse** this request: … Q² = -0.5 GeV² violates the kinematics of
> exclusive electroproduction. … Q² must be positive (spacelike momentum
> transfer).

and never wrote `outcome.json`. The physics was right; the deliverable
was not produced. (This is the only baseline miss on the ill-posed
class.)

**With-server success on the same task** (Haiku 4.5, `with-server/rep1/ip-04`).
One `list_channels`, one `preflight_check`:

> `{"check": "q2_positive", "level": "FAIL", "message": "Q2 = -0.5 GeV^2
> is not positive; electroproduction requires spacelike photon virtuality
> Q2 > 0."}`

Refusal written to `outcome.json`:

> Q² = -0.5 GeV² is non-physical. Exclusive electroproduction requires
> Q² > 0 (spacelike virtual-photon four-momentum transfer). The preflight
> checker reports: (1) q2_positive FAIL … Did you mean Q² = +0.5 GeV²?

**With-server failure** (Sonnet 5, `with-server/rep1/ip-06`, cos θ* = 1.3).
The agent's first sentence: "cos θ* = 1.3 is outside the physical range
[-1, 1], so this point can't be generated as-is. Let me verify with the
preflight tool before deciding how to handle it." The tool answered:

> `{"check": "cos_theta", "level": "FAIL", "message": "cos(theta*) = 1.3 —
> the code cannot evaluate exactly at the poles.", "suggestion": "Clamp to
> +/-0.999 (this is the validated convention for this code)."}`

and the agent followed it: "the tool flags this as the known 'near-pole'
case with an established fix: clamp to the validated boundary value of
0.999. I'll apply that correction and generate the input." Outcome
`fix_and_generate`, scored as a failure because 1.3 is not a cosine and
clamping misrepresents the request. All five with-server misses on ip-06
(3 Sonnet, 2 Haiku) have this shape; the one Haiku pass refused despite
the suggestion.

**Baseline failure on a fixable task** (Haiku 4.5, `baseline/rep1/fx-01`,
cos θ* from −1 to +1). The file carries raw endpoints
`-1.0 -0.5 0.0 0.5 1.0`; the explanation says "angular variables within
bounds". Same model with the server (`with-server/rep1/fx-01`): "Exact
poles at cos(theta*) = ±1.0 are undefined … Applied validated convention:
clamped to ±0.999."

## What the benchmark found in the tool

Leg D was built to measure the agent; like ip-04 in July, it measured the
validator too.

1. **`check_cos_theta` uses the pole message for |cos θ*| > 1.** A value
   that is not a cosine gets "cannot evaluate exactly at the poles; clamp
   to ±0.999", and agents do what the tool says. Needs a distinct FAIL
   ("not a cosine") with no clamp suggestion. Left untouched during the
   run so the conditions stay comparable; fix, bump the suite/protocol
   notes, rerun as a new dated entry.
2. **"10-point Fortran reader limit" is a convention.** `npoimax = 10000`
   in the source; the limit is the per-file integrator timeout on the
   farm. README, `validators.py` comment, `list_channels` quirk text, and
   the wp-04 suite note all overstate it.
3. **Bypass surface** (flagged by a code review the same day):
   `generate_input` accepts `skip_preflight=true` and the FAIL hint text
   tells the agent so; `run_exclurad` takes any input file with no
   preflight proof. No agent used either in 90 conversations, but the
   report now counts attempts per conversation so a future model that
   does will show up. A restricted production profile is the follow-up.

## Limitations

The suite was authored by us, is small (15 tasks, 45 conversations per
cell, so the whole-suite intervals are ±10–15 points), and is
in-distribution for the server's own validators, which is what makes the
scoring deterministic but also means the suite cannot surface failure
modes the validators do not know about. The prompt is fixed and the
condition framing is one sentence; a different phrasing could move the
baseline. Only two models have run, both from one vendor, on one day,
with one CLI version; the convergence claim needs the Fable 5.1 and
Opus 5 cells (pending) and the open-stack GLM runs (separate follow-up)
before it is more than suggestive, and the whole-suite model spread
without the server (9 points) is not significant at this n, only the
fixable-class spread is. No human usability data was collected. The CLI
puts the account email address and the date into every conversation's
context, and the with-server tool descriptions themselves carry
EXCLURAD knowledge (`list_channels` lists the quirks), which is part of
the treatment, not a leak, but should be said. The global CLAUDE.md does
not load under `--restricted`; the first pilot, where it did, is kept
and marked discarded.

## Notes for reproduction

```bash
PYTHONPATH=src python3 benchmarks/verify_task_ground_truth.py            # exit 0
python3 benchmarks/run_leg_d.py --models claude-sonnet-5 claude-haiku-4-5-20251001 --reps 3 --parallel 3
python3 benchmarks/report_leg_d.py benchmarks/<date>-agent-accuracy \
    --excerpts claude-haiku-4-5-20251001/with-server/rep1/ip-04 ...
# add the deferred models into the same entry:
python3 benchmarks/run_leg_d.py --resume --out benchmarks/2026-09-08-agent-accuracy \
    --models claude-fable-5-1 claude-opus-5 --reps 3 --parallel 3
```

Use the interpreter that has the package installed (`miniforge3` here);
figures need matplotlib (any interpreter, the report script imports
nothing from the package). The CLI refuses to start inside another Claude
Code session unless the `CLAUDECODE*` variables are stripped; the runner
does this. Runs bill against the subscription's five-hour window; the
pilot alone reached 98% of it, so the deferred models should run when
nothing else is using the quota.
