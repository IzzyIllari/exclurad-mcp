# Failure map: W–Q² coverage heatmap (2026-07-04)

`map_failures(results_dir=...)` → `coverage_map` → plotwright heatmap, on the
October 2025 CLAS12 η grid (the same 264,897-point aggregation as
`demo/plotwright-chain/`).

**Numbers:** 330 (W, Q²) cells expected (11 W × 30 Q²), each planned for
900 points (30 cos θ* × 30 φ*). **64 cells are incomplete, 31 of them
completely dead (zero output), 32,103 points missing** of 297,000.

**Reading the figure** (`plotwright_heatmap.png`):
- The **entire W = 1.6639 column is dead** except one partially-filled cell,
  and W = 1.6459 dies at Q² = 1.9586 and 4.0 — per Izzy (2026-07-04): these
  points were **never submitted** (local copy holds a partial submission;
  the full 1.487–1.999 range is planned for the LANL Slurm farm). Not a
  failure — but note the map alone can't distinguish "never submitted" from
  "submitted and died"; comparing against the `inputs/` manifests would
  (future map_failures mode).
- The **scattered interior cells** (e.g. W = 1.5929 at Q² = 2.0862/2.9793,
  the Q² = 0.4276 stripe at W = 1.5223, losses of ~100–240 points each) are
  the physically interesting ones — silent N/A regions to diagnose with
  coworkers (`smoke_test` those corners and look at which cos θ*/φ* rows
  vanish) — assuming those cells were in the submitted set; check the
  inputs manifests first.

Regenerate: `conda activate plotwright && python demo/failure-map/failure_heatmap.py`
(or the standalone `plotwright_heatmap_regen.py`).

Note: `coverage_map` rasterizes the full cartesian (W, Q²) grid precisely so
dead cells show up — cells with zero output never appear in the parsed
records, and an earlier draft silently hid all 31 of them.
