# LANL Rocinante scripts: full η kinematic range, node-parallel

Completes the CLAS12 η grid that the October 2025 JLab campaign only
partially submitted (local data stops at W = 1.646 GeV; see
`demo/failure-map/`).

**The JLab → LANL difference these scripts encode:** JLab farm jobs got a
memory slice of a shared node, so the fork's `slurm/` scripts ran 1-cpu array
tasks each processing files *sequentially*, parallelizing only across nodes.
On Rocinante **a job gets the whole node**, so here one job = one node
saturated with independent exclurad processes (`exclurad_node_task.sh` gives
each worker an isolated scratch dir with symlinked exe + tables, because the
Fortran is cwd-based). Specs live in the sbatch, work lives in the bash
driver — same pattern as `lanl-slurm/jobs/stage2.sbatch`.

## Target kinematics (η, per Izzy 2026-07-04)

- W: 1.487 → **2.0 GeV** (η+p threshold is 1.4861; EtaMAID-2023 table covers
  to 6.0, so 2.0 is safely inside)
- Q²: 0.3 → **5.0 GeV²** — the table's hard edge. **Q² = 6 would extrapolate
  the hadronic model** (table scan: Q² grid stops at 5.0); preflight_check
  FAILs it. If 6 GeV² is truly wanted, that's a new-tables conversation with
  Victor, not a submission flag.
- cos θ*: −0.9 → 0.9 (30), φ*: 0 → 360° (30), bmom 6.53, vcut 0.166 —
  matching the October grid so old + new merge into one dataset.

## Sizing (measured, not guessed)

One 10-point file = **243 s single-core** on Izzy's Intel Mac (2026-07-04,
mid-grid W=1.66, Q²=1.5, cos-varying file). Planning number: **~4 min/file,
~24 s/point**; calibrate on Rocinante with the debug job below before the
big submit.

Full 30⁴ grid = 810k points = 81k files ≈ 5,400 core-h.
Remaining after October (~265k points done) ≈ 545k points ≈ **3,600 core-h ≈
33 node-h** at ~112 cores/node → **4 single-node array tasks × 12 h**
(QoS `standard`, MaxWall 12:00:00) with margin. `RESUME=1` (default) makes
resubmission after a wall-clock kill cheap: done files are skipped.

## Walkthrough

```bash
# 0. LOCALLY: generate the remaining inputs with preflight guarantees
#    (exclurad-mcp generate_input, or the fork's rcgrid_inputgen.py with
#    --w-min 1.487 --w-max 2.0 --n-w 30 ... and drop already-done W bins).

# 1. ship everything to the workspace (from the LOCAL terminal; PIN each time)
scp -r inputs_remaining exclurad slurm-lanl/exclurad_node_*.{sbatch,sh} \
    <cluster-frontend>:$PROJECT_DIR/exclurad-run/

# 2. on the cluster front-end: build (gfortran available on the front-end or via module)
cd $PROJECT_DIR/exclurad-run/exclurad && make && cd ..
find inputs_remaining -name '*.dat' | LC_ALL=C sort > inputs.index

# 3. calibration smoke test: ~20 files on the debug partition
head -20 inputs.index > smoke.index
sbatch -p debug -q debug -t 00:30:00 \
  --export=ALL,INDEX_FILE=smoke.index,WORK_SRC=./exclurad,RESULTS_ROOT=./results \
  exclurad_node_parallel.sbatch
# then check: seconds/file from exclu_*.out, results/skipped_files.log empty?

# 4. real campaign: 4 nodes, one shard each
sbatch --array=0-3 \
  --export=ALL,INDEX_FILE=inputs.index,SHARD_COUNT=4,WORK_SRC=./exclurad,RESULTS_ROOT=./results \
  exclurad_node_parallel.sbatch
squeue --me

# 5. after: pull results down and map coverage/failures locally
scp -r <cluster-frontend>:$PROJECT_DIR/exclurad-run/results ~/…
#    exclurad-mcp: map_failures(results_dir=...) -> heatmap;
#                  map_failures(skip_log=results/skipped_files.log) -> reasons.
```

## Notes

- All shards share one `RESULTS_ROOT` (per-file outputs are collision-free by
  basename; the skip log is append-only). One results tree at the end.
- Compute-node egress doesn't matter here — jobs are pure Fortran, no model
  calls.
- `MaxArraySize=1001` on Rocinante — irrelevant at 4 shards, but don't try
  JLab-style 6,250-task arrays.
- If a node count other than 4 is used, `SHARD_COUNT` must equal the array
  size (`--array=0-(N-1)` + `SHARD_COUNT=N`).
