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

**Status.** Task suite not yet written; everything else about the harness is
buildable now.

## Current status summary

| Leg | Needs LLM | Blocked on anything? |
|---|---|---|
| A: η regression | no | no (patched-build addendum waits on guard sign-off) |
| B: π⁺ closure | no | no (needs one-time plot digitization) |
| C: seeded failure detection | no | no |
| D: agent accuracy | yes | task suite authoring |
