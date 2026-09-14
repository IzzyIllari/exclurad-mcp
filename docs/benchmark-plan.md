# Benchmark plan

How we intend to measure, scientifically and reproducibly, whether this
server does what it claims. The claims under test:

1. Agent-driven pipelines reproduce hand-validated physics results.
2. The build/templating system reproduces the published pion physics.
3. The coverage accounting catches silent data loss that humans miss.
4. Correctness comes from the deterministic tooling, not from whichever
   language model happens to be driving it.

Three of the four legs involve no language model at all. Every leg is scored
by deterministic checks; no LLM ever judges an LLM.

## Provenance rules (all legs)

Every benchmark run records: date, git commit of this package, git commit of
the EXCLURAD checkout(s), compiler version, machine, and (for leg D) the
exact model ID and agent version. Results land in `benchmarks/` as
machine-readable CSV or JSON plus a short dated report. Runs are never
overwritten; a rerun is a new dated entry.

## Leg A: η regression (no LLM)

**Question.** Does the server pipeline (`generate_input` → `run_exclurad` →
`parse_output`) reproduce the hand-validated October 2025 η grids?

**Method.** Stratified sample of recorded chunks across (W, Q²). Re-run each
through the server with the original chunk grouping preserved, then diff
δ, σ_Born, and the asymmetries against the recorded values.

**Pass criteria.** Two tiers, scored separately. Bit equality holds only
when reference and rerun share platform and compiler; the October reference
is a JLab-farm Linux build, so a macOS rerun scores on the second tier:
numeric agreement within per-column ceilings (δ and σ_Born within 1e-7,
asymmetry percentages within 1e-4 to 1e-3), all sitting orders of magnitude
below the integrator's own `ot = 1e-3` tolerance. Kinematic echo columns
must be exact. Chunk grouping is always held fixed: the build's static
locals (`-fno-automatic`) make results depend on point grouping at the
~1e-9 level.

**Cost.** ~243 s per 10-point chunk single-core on an M-series Mac; a
50-chunk sample is an overnight run.

**Status.** Runnable now against the pristine build, excluding the ~1% of
points known to be NaN from the integrator defect described in the README.
Addendum once the phase-space guard is signed off: rerun the sample under
the patched build and confirm bit equality on all previously-good points.

## Leg B: π⁺ closure (no LLM)

**Question.** Does a pion executable built entirely from `generate_build`
templates reproduce the published pion-channel physics of
[Phys. Rev. D 66, 074004 (2002)](https://arxiv.org/abs/hep-ph/0208183)?

**Method.** Generate the pion sources from the slot registry, compile, run
the paper's kinematics, compare against the published curves.

**Already established.** Generated sources are byte-identical to the
JeffersonLab upstream, and a generated-source executable produced
byte-identical outputs (all seven files) to an upstream-source build on
upstream's own `input.dat`. Closure against the paper adds the physics-level
check on top of the byte-level one.

**Open work item.** The 2002 results are published as figures, so the
reference values must be digitized from the plots. One-time effort.

**Status.** Runnable now.

## Leg C: seeded failure detection (no LLM)

**Question.** Does the coverage accounting (`map_failures`, `parse_output`)
find silent data loss with quantifiable recall and precision?

**Method.** Start from a complete results tree. Seed known damage: delete
whole chunks, delete single points, inject NaN rows, truncate files. Run the
coverage tools and score detected-vs-seeded as a recall/precision matrix per
damage type.

**Why this leg exists.** This is the controlled version of what happened in
production: the coverage accounting surfaced ~1% NaN loss in every η grid
ever produced, a defect that had gone unnoticed in the published code for
two decades. The benchmark turns that anecdote into a measured detection
rate.

**Status.** Runnable now; needs no external data.

## Leg D: agent accuracy (the only LLM leg)

**Question.** Given natural-language physics requests, how often does an
agent produce valid, running inputs with this server versus without it, and
does the answer depend on which model is driving?

**Method.** A fixed, versioned task suite in three classes:

- well-posed ("η at CLAS12 kinematics, this W × Q² grid"),
- fixable ("cos θ* from −1 to 1", which must be clamped with an explanation),
- ill-posed ("η production at W = 1.2 GeV", which must be refused with the
  threshold stated).

Each task runs under two conditions (agent with this server; agent with only
the Fortran source and README) and under multiple models. Scoring is
deterministic: preflight verdict matches ground truth, generated files pass
byte validation, refusals happen where physics demands them.

**The claim being tested.** If validity rates converge across models with
the server and diverge without it, correctness lives in the tooling, not
the model.

**Status (2026-09-14).** Suite v1 (15 tasks, `suite_sha256
21ee515822f1c51b…`) and harness done. **2,520 scored leg D conversations**
across three harnesses (Claude Code, OpenCode, Codex), 15 models and three
server versions, plus 270 leg E (end-to-end) conversations. The combined
cross-harness report, the slide figures and the "For the DNP slide" section
are in **`benchmarks/2026-09-14-combined-report/README.md`**; the arm-by-arm
map with per-arm caveats is **`benchmarks/LEG_D_RESULTS.md`**.

The headline: **the tools raised scored task completion in every harness
tested**. On OpenCode, the primary cross-vendor comparison, 59% → 80%
(348/585 → 469/585) over 13 models; on Claude Code 84% → 100% (76/90 → 90/90);
on Codex, a labelled replication that keeps its shell, 84% → 99% (114/135 →
133/135). Harness rows are never pooled. The largest gains were for two
open-weight models with low baseline scores: NVIDIA Nemotron 3 Nano 30B 31% →
89% and Nemotron 3 Super 120B 40% → 96%; frontier models gained +11 to +20.
That matters because most people who would run this server do not have
frontier API access. No well-posed request was falsely refused with the
server (0/270 across the harnesses). The `skip_preflight` override was used in
13 of 810 with-server conversations (12 OpenCode, 1 Claude Code, 0 Codex); it
is available to any agent.

Two results qualify what the study can claim. The v0.1.2 fix to the
`q2_positive` validator suggestion took ip-04 from 0/9 to 8/9 with-server
**on Codex only** — under OpenCode the same task was already at 11/12
(frontier) and 18/27 (open) on v0.1.1 and does not move, so that fix repaired
a harness × wording interaction rather than a general defect. And some models'
scores are dominated by delivery rather than physics: Lightning 30B's failures
are 32-of-32 outcomes printed as chat text instead of written, and Muse
Glimmer 30B's 4% is 84-of-90 cells failing JSON parsing with correct-looking
physics inside the file.

Earlier runs remain on record: the first (2026-09-08, Sonnet 5 and Haiku 4.5,
k = 3, `benchmarks/2026-09-08-agent-accuracy/`) gave 93%/96% with the server
against 89%/80% without, the divergence concentrated in the fixable class, and
surfaced the first validator wording defect (|cos θ*| > 1 reported with the
pole message) that made both models clamp an impossible cosine. That defect
and the `q2_positive` one are the same failure mode, found twice.

## Leg E: end-to-end (agent runs the code)

**Question.** Leg D stops at the input file. Leg E asks whether an agent can
run EXCLURAD on a point and report the numbers a recorded October-2025
campaign row contains: δ, σ_Born, and the right behaviour at a NaN point and
at a below-threshold point. Protocol: `benchmarks/agent_tasks/PROTOCOL-E.md`;
suite `tasks_e2e.json` (6 η tasks); scorer `score_e2e_run.py`.

**Status (2026-09-14).** 270 conversations, five models on two harnesses,
servers v0.1.1 and v0.1.2. On v0.1.2 the five models score 89/90 with the
server under the amended scorer (60/60 well-posed, 15/15 threshold trap,
14/15 NaN trap; the one miss reported "could not run" without executing and
was scored as a NaN observation until the 2026-09-14 amendment). Both with-server failure modes seen on v0.1.1 were interface
defects, and both were measured to disappear when the tool interface stopped
inviting them: Haiku 4.5 assumed a 10.6 GeV beam (3 → 0 once `generate_input`
echoed its settings and named the campaign energies) and gpt-5.6-luna passed
`rc_mode=1`, the leading-log approximation, when asked for an exact
correction (11 → 0 once the parameter took `"full"`/`"leading_log"` instead of
0/1). The leading-log substitution is a 7% error in δ on the reference point
(0.8493 vs 0.9160) and removes the radiative correction to the beam-spin
asymmetry entirely. Baseline agents that succeed do so at 3–4× the cost and
2–5× the wall time; their failures are reading the wrong output column or
rounding the reported number.

## Current status summary

| Leg | Needs LLM | Blocked on anything? |
|---|---|---|
| A: η regression | no | no (patched-build addendum waits on guard sign-off) |
| B: π⁺ closure | no | no (needs one-time plot digitization) |
| C: seeded failure detection | no | no |
| D: agent accuracy | yes | no (2,520 conversations; combined report in `benchmarks/2026-09-14-combined-report/`; ablation specified in `PROTOCOL-ABLATION.md`, not run) |
| E: end-to-end | yes | no (270 conversations; 89/90 on server v0.1.2 after the 2026-09-14 scorer amendment; report in the same combined directory) |
