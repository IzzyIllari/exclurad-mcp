#!/bin/bash
# ============================================================================
# exclurad_node_task.sh -- node-parallel EXCLURAD driver (LANL Rocinante).
#
# Fills a whole node with independent exclurad processes. exclurad is
# cwd-based (reads ./input.dat, ./maid*.tbl; writes ./radtot.dat etc.), so
# each worker gets an ISOLATED scratch workdir with symlinked exe + tables --
# that is the whole trick that makes single-node parallelism safe.
#
# Per-file outcome classification mirrors exclurad-mcp's runner taxonomy
# (and run_exclurad_skip_unphys.sh): TIMEOUT / EXIT_NONZERO / NO_TAI (silent
# N/A) / NO_OUTPUT / OK. Skips are logged, never fatal.
#
# Config (env vars, all overridable on the sbatch --export line):
#   INDEX_FILE    sorted list of absolute input-file paths   [inputs.index]
#   WORK_SRC      dir with build/exclurad + *.tbl            [./exclurad]
#   RESULTS_ROOT  where results land                         [./results]
#   WORKERS       parallel processes                         [nproc]
#   TIMEOUT_SEC   per-file kill timer                        [900]
#   SHARD / SHARD_COUNT  this task's slice of the index
#                 [SLURM_ARRAY_TASK_ID or 0] / [array size or 1]
#   RESUME        1 = skip files whose radtot output exists  [1]
# ============================================================================
set -uo pipefail

INDEX_FILE="${INDEX_FILE:-inputs.index}"
WORK_SRC="${WORK_SRC:-./exclurad}"
RESULTS_ROOT="${RESULTS_ROOT:-./results}"
WORKERS="${WORKERS:-$(nproc)}"
TIMEOUT_SEC="${TIMEOUT_SEC:-900}"
SHARD="${SHARD:-${SLURM_ARRAY_TASK_ID:-0}}"
SHARD_COUNT="${SHARD_COUNT:-${SLURM_ARRAY_TASK_COUNT:-1}}"
RESUME="${RESUME:-1}"

EXE="$WORK_SRC/build/exclurad"
[[ -x "$EXE" ]] || EXE="$WORK_SRC/build/exclurad.exe"

# GNU timeout is standard on Linux; macOS needs coreutils (timeout/gtimeout).
if command -v timeout >/dev/null; then TIMEOUT_BIN=timeout
elif command -v gtimeout >/dev/null; then TIMEOUT_BIN=gtimeout
else echo "ERROR: no timeout binary; unphysical kinematics would hang forever" >&2; exit 1
fi
OUT_KEYS=(all allu radasm radcor radsigmi radsigpl radtot)
SCRATCH="${SLURM_TMPDIR:-/tmp/$USER}/exclu_${SLURM_JOB_ID:-manual}_${SHARD}"

ts() { date +"%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] $*"; }

[[ -f "$INDEX_FILE" ]] || { echo "no index file: $INDEX_FILE" >&2; exit 1; }
[[ -x "$EXE" ]] || { echo "no executable under $WORK_SRC/build/" >&2; exit 1; }

mkdir -p "$RESULTS_ROOT"/{all,allu,radasm,radcor,radsigmi,radsigpl,radtot,inputs,logs}
SKIP_LOG="$RESULTS_ROOT/skipped_files.log"; touch "$SKIP_LOG"

# ---- this shard's slice of the index (line i goes to shard i % SHARD_COUNT)
mapfile -t MY_FILES < <(awk -v s="$SHARD" -v n="$SHARD_COUNT" 'NR % n == s' "$INDEX_FILE")
TOTAL=${#MY_FILES[@]}
log "shard $SHARD/$SHARD_COUNT: $TOTAL files, $WORKERS workers, timeout ${TIMEOUT_SEC}s"
log "exe: $EXE   scratch: $SCRATCH   results: $RESULTS_ROOT"
[[ $TOTAL -gt 0 ]] || { log "nothing to do"; exit 0; }

# ---- per-worker isolated workdirs: symlink exe + every lookup table
for ((w = 0; w < WORKERS; w++)); do
  wd="$SCRATCH/w$w"
  mkdir -p "$wd"
  ln -sf "$(readlink -f "$EXE")" "$wd/exclurad"
  for tbl in "$WORK_SRC"/*.tbl; do
    [[ -e "$tbl" ]] && ln -sf "$(readlink -f "$tbl")" "$wd/$(basename "$tbl")"
  done
done

run_one() {  # $1 = worker id, $2 = input path
  local wd="$SCRATCH/w$1" input_path="$2"
  local base; base="$(basename "$input_path" .dat)"

  if [[ "$RESUME" == "1" && -f "$RESULTS_ROOT/radtot/${base}.dat" ]]; then
    return 0
  fi

  rm -f "$wd"/{all,allu,radasm,radcor,radsigmi,radsigpl,radtot,input}.dat
  cp -f "$input_path" "$wd/input.dat"
  local logfile="$RESULTS_ROOT/logs/${base}.txt"

  ( cd "$wd" && "$TIMEOUT_BIN" "$TIMEOUT_SEC" ./exclurad ) > "$logfile" 2>&1
  local rc=$?

  if [[ $rc -eq 124 ]]; then
    echo "$(date -Iseconds) TIMEOUT     $base" >> "$SKIP_LOG"; return 0
  elif [[ $rc -ne 0 ]]; then
    echo "$(date -Iseconds) EXIT=$rc  $base" >> "$SKIP_LOG"; return 0
  elif ! grep -q "tai:" "$logfile" 2>/dev/null; then
    echo "$(date -Iseconds) NO_TAI      $base" >> "$SKIP_LOG"; return 0
  fi

  local moved=0 key
  for key in "${OUT_KEYS[@]}"; do
    [[ -f "$wd/${key}.dat" ]] && mv -f "$wd/${key}.dat" "$RESULTS_ROOT/$key/${base}.dat" && moved=1
  done
  if [[ $moved -eq 1 ]]; then
    cp -f "$input_path" "$RESULTS_ROOT/inputs/${base}.dat"
  else
    echo "$(date -Iseconds) NO_OUTPUT   $base" >> "$SKIP_LOG"
  fi
}

worker_loop() {  # $1 = worker id; takes lines i where i % WORKERS == id
  local id=$1 i
  for ((i = id; i < TOTAL; i += WORKERS)); do
    run_one "$id" "${MY_FILES[$i]}"
  done
}

start=$SECONDS
for ((w = 0; w < WORKERS; w++)); do worker_loop "$w" & done
wait
elapsed=$((SECONDS - start))

DONE=$(ls "$RESULTS_ROOT/radtot" 2>/dev/null | wc -l)
SKIPPED=$(wc -l < "$SKIP_LOG")
log "shard done in ${elapsed}s: radtot outputs now $DONE (all shards), skips logged $SKIPPED"
log "skip log: $SKIP_LOG  (feed to exclurad-mcp map_failures for the reason/coverage map)"
rm -rf "$SCRATCH"
