#!/bin/bash
# ============================================================================
# exclurad_node_parallel.sbatch -- SPECS ONLY. All work is in
# exclurad_node_task.sh (the sbatch-calls-a-bash-driver pattern).
#
# LANL Rocinante model: requesting a node gives you the WHOLE node, so one
# job = one node running many exclurad processes in parallel (this is the
# opposite of the JLab scripts, which ran 1-cpu array tasks sequentially).
#
# scp to the workspace (flat), e.g. $PROJECT_DIR/exclurad/:
#   exclurad_node_parallel.sbatch  exclurad_node_task.sh
#   + the built exclurad work dir (build/exclurad + *.tbl)
#   + the input .dat files + inputs.index
#
# SUBMIT:
#   # smoke test on the debug partition first (1 node, 30 min, small index):
#   sbatch -p debug -q debug -t 00:30:00 --export=ALL,INDEX_FILE=smoke.index \
#          exclurad_node_parallel.sbatch
#
#   # real campaign: shard the index across an array, one node per shard
#   # (SHARD_COUNT must equal the array size):
#   sbatch --array=0-3 --export=ALL,INDEX_FILE=inputs.index,SHARD_COUNT=4 \
#          exclurad_node_parallel.sbatch
# ============================================================================
#SBATCH --job-name=exclu-node
#SBATCH --account=<account>
#SBATCH --partition=standard
#SBATCH --qos=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=12:00:00              # QoS standard MaxWall; shorter backfills sooner
#SBATCH --output=exclu_%A_%a.out     # flat, in the submit dir
#SBATCH --mail-type=FAIL,END

cd "$SLURM_SUBMIT_DIR"
bash exclurad_node_task.sh
