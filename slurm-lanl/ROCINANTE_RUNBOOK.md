# Rocinante runbook — η full-grid campaign, step by step

Written for the transfer bundle (`exclurad_rocinante_bundle_*.zip`). Debugging
is **interactive-first** (steps 3–4), then a batch calibration, then the real
submit. Nothing in steps 1–5 costs meaningful allocation.

Bundle contents: `exclurad/` (η source + EtaMAID-2023 table, no build),
`inputs_remaining/` (73,418 preflight-validated input files = 734,180 points;
grid W 1.487–1.999 ×30, Q² 0.3–4.893 ×37 [October design + 7-value extension,
capped under the table edge 5.0], cos ±0.9 ×30, φ 0–348° ×30; October's
26,482 already-done file-equivalents excluded), `slurm-lanl/` scripts,
this runbook.

## 0. Get it onto Rocinante

```bash
# from the LANL laptop (local terminal, PIN each time):
scp exclurad_rocinante_bundle_*.zip <cluster-frontend>:$PROJECT_DIR/
ssh <cluster-frontend>
cd $PROJECT_DIR && unzip -q exclurad_rocinante_bundle_*.zip -d exclurad-run
cd exclurad-run
```

## 1. Build

```bash
gfortran --version || module avail gcc     # find a compiler if not on PATH
cd exclurad && make && cd ..
ls exclurad/build/exclurad                 # must exist and be executable
```

## 2. Index + smoke slice

```bash
find "$PWD/inputs_remaining" -name '*.dat' | LC_ALL=C sort > inputs.index
wc -l inputs.index                         # expect 73418
head -20 inputs.index > smoke.index
```

## 3. INTERACTIVE first — one file by hand

```bash
salloc -A <account> -p debug -q debug -N 1 -t 00:30:00
# (all of the below runs inside the allocation, on the compute node)
mkdir -p /tmp/$USER/hand && cd /tmp/$USER/hand
ln -sf $PROJECT_DIR/exclurad-run/exclurad/build/exclurad .
ln -sf $PROJECT_DIR/exclurad-run/exclurad/*.tbl .
cp "$(head -1 $PROJECT_DIR/exclurad-run/inputs.index)" input.dat
time ./exclurad | tail -20
# EXPECT: 'tai:' lines in stdout; radtot.dat etc. appear; wall time very
# roughly ~4 min for a 10-point file (Izzy's Mac: 243 s single-core).
ls *.dat
```

If that looks right, still inside the same salloc:

## 4. INTERACTIVE — the parallel driver on a small slice

```bash
cd $PROJECT_DIR/exclurad-run
nproc                                      # note the core count -> N below
INDEX_FILE=smoke.index WORK_SRC=./exclurad RESULTS_ROOT=./results_smoke \
  WORKERS=20 TIMEOUT_SEC=900 bash slurm-lanl/exclurad_node_task.sh
# EXPECT: "shard 0/1: 20 files, 20 workers"; finishes in ~one file-time
# (~4-5 min) since 20 files / 20 workers; results_smoke/radtot has 20 files;
# skipped_files.log empty. Note seconds-per-file for step 6's math.
exit                                       # leave the salloc
```

## 5. Batch calibration (debug partition, one full node)

```bash
head -300 inputs.index > calib.index       # ~3 waves on a ~112-core node
sbatch -p debug -q debug -t 01:00:00 \
  --export=ALL,INDEX_FILE=calib.index,WORK_SRC=./exclurad,RESULTS_ROOT=./results \
  slurm-lanl/exclurad_node_parallel.sbatch
squeue --me                                # wait; then read exclu_*.out
# The log's "shard done in Xs" over 300 files gives the real node rate:
#   files_per_node_hour = 300 / (X / 3600)
```

## 6. Production submit

```bash
# node-hours needed = 73418 / files_per_node_hour   (Mac estimate: ~44)
# with 12 h MaxWall (qos standard): shards = ceil(node_hours / 12) -> likely 4-5
sbatch --array=0-4 \
  --export=ALL,INDEX_FILE=inputs.index,SHARD_COUNT=5,WORK_SRC=./exclurad,RESULTS_ROOT=./results \
  slurm-lanl/exclurad_node_parallel.sbatch
squeue --me
```

Monitoring: `squeue --me`, `sacct -j <jobid>`, `tail -f exclu_*_0.out`,
`wc -l results/skipped_files.log` (a few near-threshold TIMEOUTs are normal;
>10% is not). All shards share `results/` — that's by design.

## 7. If a shard hits the 12 h wall

Resubmit the SAME command (same shard count). `RESUME=1` (the default) skips
every file whose radtot output exists, so only the tail re-runs.

## 8. Pull results back and check coverage

```bash
# from the LANL laptop:
scp -r <cluster-frontend>:$PROJECT_DIR/exclurad-run/results ./results_rocinante
```

Then locally with exclurad-mcp: `map_failures(results_dir=...)` for the W–Q²
coverage heatmap (expect green everywhere except genuine silent-N/A cells),
`map_failures(skip_log=results/skipped_files.log)` for failure reasons, and
`parse_output(..., csv_out=...)` to merge with the October data for plotting.

## Gotchas already hit once (don't rediscover)

- salloc needs **matching account+partition+qos**: `-A <account> -p debug -q debug`.
  Bare `--qos=debug` fails ("Invalid qos specification").
- The driver needs GNU `timeout` (standard on Linux; it exits early if absent).
- exclurad is cwd-based; never run two instances in one directory. The driver
  isolates workers — that's its whole job.
- Q² stops at 4.893 because the EtaMAID-2023 table ends at 5.0. Q² = 6 means
  new tables from Victor first; preflight will FAIL it until then.
- W row 1 (1.487) is 0.9 MeV above threshold: expect some TIMEOUT/NO_TAI skips
  there. That's physics, not a bug — the skip log maps them for diagnosis.
