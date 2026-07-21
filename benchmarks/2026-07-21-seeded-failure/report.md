# Seeded failure detection — run of 2026-07-21

Benchmark leg C of [docs/benchmark-plan.md](../../docs/benchmark-plan.md).
No LLM anywhere in the loop; scoring is fully deterministic.

## Provenance

| | |
|---|---|
| Date | 2026-07-21 |
| Harness | `benchmarks/seeded_failure_detection.py`, seed 20260721 (committed alongside this report) |
| Package state | commit containing this report (parent: 684a3a3) |
| Source data | `results_Oct2025/outputs/first` — 12,539 real η radtot chunk files from the hand-validated October 2025 CLAS12 campaign |
| Machine | macOS 15.6.1, x86_64, Python 3.13.12 |

## Method

1,500 chunk files (15,000 kinematic points) sampled from the real October
tree into a scratch tree. Known damage seeded with a recorded RNG seed:

- 40 whole chunk files deleted (400 points),
- 60 single data rows deleted,
- 60 NaN values injected into the δ column, half spelled `NaN` and half
  lowercase `nan` (the Fortran writes lowercase; a case-sensitive check
  misses all of them),
- 20 files truncated mid-row (20 points lost plus a corrupt partial line).

Detection ran `collect_results` over the damaged tree and scored three
channels differentially against the pristine baseline: multiset point
difference (missing points), newly non-finite δ (NaN), and newly flagged
parse problems (truncation). Differential scoring matters because the
source data is real: it already contains genuine holes and genuine NaN.

## Results

| Damage channel | Seeded | Detected | Recall | Precision |
|---|---|---|---|---|
| Missing points (file + row + truncation) | 480 | 480 | 1.00 | 1.00 |
| Injected NaN (both spellings) | 60 | 60 | 1.00 | 1.00 |
| Truncated-file flags | 20 | 20 | 1.00 | 1.00 |

Zero false positives and zero false negatives on every channel. A
repeatability check with an independent seed (42) reproduced 1.00/1.00 on
all three channels.

Full machine-readable output: [results.json](results.json).

## Footnote: the benchmark tripped over the real bug

The 1,500-file sample carried **135 genuine NaN points (0.9%)** from the
unguarded-square-root defect in the 2002 integrator described in the
README — consistent with the 1.1% rate measured across the full October
campaign. The detection channel found them all; the differential scoring
exists precisely so that real damage in the source does not pollute the
seeded-damage score. This is the production failure mode this leg was
designed to model, showing up unprompted inside the benchmark of it.
