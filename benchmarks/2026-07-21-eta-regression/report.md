# η regression — run of 2026-07-21

Benchmark leg A of [docs/benchmark-plan.md](../../docs/benchmark-plan.md).
No LLM anywhere in the loop; scoring is fully deterministic.

## Provenance

| | |
|---|---|
| Date | 2026-07-21 (run started ~16:30 EDT, ~9.2 core-hours) |
| Harness | `benchmarks/eta_regression.py`, seed 20260721 (committed alongside this report) |
| Reference data | `results_Oct2025/outputs/first` — hand-validated October 2025 CLAS12 η campaign, computed on the JLab farm (Linux, gfortran 11.5) |
| Rerun platform | macOS 15.6.1, x86_64, conda-forge gfortran 15.2.0, η fork checkout, GNU make build |
| Sample | 50 chunks (500 points), one per distinct (W, Q²) cell; W 1.487–1.646 (the full W range present in this source group), Q² 0.3–4.0 |

Chunks containing recorded NaN were excluded from sampling (575 of 12,539
in this group — the integrator defect described in the README; those points
are exercised by the seeded-failure leg instead).

## Method

For each sampled chunk, the original preserved input file was parsed back to
its ten kinematic points, regenerated through the server's `render_input`,
checked for Fortran-level equivalence against the original (token-wise float
equality of everything the reader consumes — the original generator wrote
cosmetic quirks such as a duplicated W line, so byte identity is not the
right test), then run through the server's runner in an isolated per-chunk
work directory with the original chunk grouping preserved, and the resulting
`radtot` compared row-by-row against the recorded output.

## Results

| Gate | Result |
|---|---|
| Runs completing OK | 50 / 50 |
| Regenerated inputs Fortran-equivalent to originals | 50 / 50 |
| Kinematic echo columns exact | 50 / 50 (all 500 rows) |
| Within numeric tolerance (all columns) | 50 / 50 |
| Bit-identical rows | 0 / 500 (expected: cross-platform rerun) |

Maximum absolute deviations across all 500 points, against ceilings:

| Column | Max observed | Ceiling | Integrator's own tolerance |
|---|---|---|---|
| δ (RC factor) | 1.7e-7 (median 4.8e-8) | 5e-7 | ot = 1e-3 |
| σ_Born | 4.2e-9 | 1e-7 | |
| A_obs [%] | 2.6e-7 | 1e-4 | |
| A_Born [%] | 2.0e-7 | 1e-4 | |
| A_RC ratio [%] | 2.0e-3 | 1e-2 | ratio-amplified; skipped at φ = 0/180/360 (60 rows) where the schema documents it as meaningless (A_Born ≈ 0) |

The observed δ agreement sits nearly four orders of magnitude below the
integrator's own convergence setting. Bit identity is a same-platform
property: the farm and this Mac differ in libm at the ulp level, which
propagates to ~1e-9 per evaluation and at most 1.7e-7 through the tail
integration. A same-platform rerun is expected to be bit-identical (the
NaN-investigation reruns of July 9 reproduced farm chunks exactly at
matched grouping); rerunning this leg on a Linux/farm machine to close that
tier remains open.

Full machine-readable output: [results.json](results.json).

## Notes for reproduction

- Chunk grouping must be held fixed: the build's `-fno-automatic` static
  locals make δ depend on how points are grouped into an `input.dat` at the
  ~1e-9 level.
- A first attempt of this run was discarded for a harness defect (shared
  work directories raced under the thread pool, clobbering outputs; and
  zero-row comparisons scored as vacuous passes). The committed harness uses
  one work directory per chunk and gates tolerance on a complete row-count
  match. Recorded here because silently discarding failed benchmark runs is
  how benchmarks stop being trustworthy.
