#!/bin/bash
# ROUND 3 - full-corpus sweep on the EXPANDED corpus (31 funds x 6 sheets = 186
# cells). Preemption-proof: boots vLLM, runs the RESUMABLE batch into a fixed
# dir, and --requeue lets SLURM resubmit the whole job after a preemption; the
# resumed job re-boots and continues where summary.json left off.
#
# Submit:  sbatch --exclude=node4002,node5201 engaging_beta/round3_sweep.sbatch
#          (node4002/node5201 fail the TP=2 vLLM boot - see SESSION_HANDOFF 0e)
# Watch:   tail -f /orcd/scratch/orcd/011/ncomati/round3_<jobid>.log
#          progress: runs/_batch_round3/summary.json (written after every run)
#
# What this round tests, in one job:
#   1. the Sep_Rate `broadcast` op (service-only faithful fill / age-only
#      assumption) - 12 plans whose grids were previously empty
#   2. the label-existence guard - the 17 cells it converts from silent-empty
#      into a loud contract violation
#   3. the _verify_s8 leftovers - mil Retirement regression, chi_pol ASW and
#      sf Retirement crashes, chi_gen Avg_Mort flat blend
#   4. 15 NEWLY ADDED funds (90 cells) that have never been extracted at all
#
#SBATCH -J pension-round3
#SBATCH -p mit_preemptable
#SBATCH -N 1
#SBATCH --gres=gpu:h200:2
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 12:00:00
#SBATCH --requeue
#SBATCH -o /orcd/scratch/orcd/011/ncomati/round3_%j.log

set -uo pipefail
SCRATCH=/orcd/scratch/orcd/011/ncomati
REPO="$SCRATCH/state-and-local-pension"
BATCH=_batch_round3             # NEW dir - resuming _batch_resumable would skip
                                # every cell the previous sweep completed
# scope it here if needed, e.g. PLANS="--plans den,sea,nsh"
PLANS=""
TARGETS=""

echo "=== $(date) job $SLURM_JOB_ID on $(hostname), restart #${SLURM_RESTART_COUNT:-0} ==="
module load apptainer/1.4.2 miniforge/24.3.0-0

# a requeued job lands on a fresh node, but clear any stray worker just in case
pkill -9 -u "$USER" -f "vllm serve" 2>/dev/null || true
sleep 5
# kill the server when this job ends (normal exit OR SLURM's pre-preemption TERM)
trap 'pkill -9 -u "$USER" -f "vllm serve" 2>/dev/null || true' EXIT

# boot vLLM in the background (ONE line - no backslashes, paste/exec safe)
apptainer exec --nv -B "$SCRATCH" --env CC=gcc --env CXX=g++ "$SCRATCH/containers/vllm_dir" vllm serve "$SCRATCH/models/qwen35-122b-fp8" --served-model-name qwen35-122b-fp8 --tensor-parallel-size 2 --max-model-len 262144 --gpu-memory-utilization 0.90 --port 8000 > "$SCRATCH/vllm_sbatch.log" 2>&1 &

# wait for the server (boot + kernel compile can take ~6-15 min)
python "$REPO/Data Extraction/engaging_beta/wait_health.py" \
  --url http://127.0.0.1:8000/health --timeout 1500 || {
    echo "!! vLLM never became healthy - see $SCRATCH/vllm_sbatch.log"; exit 1; }

export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL=qwen35-122b-fp8
export OPENAI_API_KEY=dummy
export EXTRACT_DUMP_DIR="$SCRATCH/dumps"; mkdir -p "$EXTRACT_DUMP_DIR"

cd "$REPO/Data Extraction"
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet $PLANS $TARGETS
echo "=== round 3 finished cleanly ($(date)); summary in runs/$BATCH/ ==="

# PDF-independent output audit over every derived grid (run after every sweep).
# It discovers the NEWEST run per cell by itself, which after this job is the
# round-3 run - no batch argument needed.
python pipeline/audit_derived.py --csv "runs/$BATCH/audit_findings.csv" \
  > "$SCRATCH/round3_audit.txt" 2>&1 || true
echo "=== audit written to $SCRATCH/round3_audit.txt ==="
