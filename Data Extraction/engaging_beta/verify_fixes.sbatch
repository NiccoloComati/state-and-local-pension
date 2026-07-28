#!/bin/bash
# Scoped verification of the session-7 fixes. Boots vLLM once and re-runs ONLY
# the affected cells into a FIXED batch dir (_verify_s7) so a preempted job
# resumes where it stopped -- and so a LATER submission can APPEND more cells
# to the same dir (already-completed cells are skipped, not repeated).
#
# Under test (all already committed + pushed):
#   77bb513  chi_ff monthly-in-ratio: derive-level annualize + wage-floor guard
#   a4fc56e  interleaved-exhibit guard (count line + dollar line in one exhibit)
#
# Cells:
#   chi_ff  Age_Serv_Wage   monthly x12   expect ~1.0 (was 0.00)
#   bos     Age_Serv_Num    interleaved   expect scored (was CRASH)
#   bos     Age_Serv_Wage   interleaved   expect scored (was CRASH)
#   lax_gen Age_Serv_Wage   interleaved   expect scored (was CRASH)
#   REGRESSION SET - these already worked on the SAME interleaved layout, and
#   the guard changed the SYSTEM prompt globally, so they must not move:
#   lax_uty Age_Serv_Num    expect 1.0    lax_ffpol Age_Serv_Wage  expect ~0.92
#
# Submit:  sbatch --exclude=node4002,node5201 engaging_beta/verify_fixes.sbatch
# Watch:   tail -f /orcd/scratch/orcd/011/ncomati/verify_<jobid>.log
# Read:    runs/_verify_s7/summary.json
#
#SBATCH -J pension-verify
#SBATCH -p mit_preemptable
#SBATCH -N 1
#SBATCH --gres=gpu:h200:2
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 2:00:00
#SBATCH --requeue
#SBATCH -o /orcd/scratch/orcd/011/ncomati/verify_%j.log

set -uo pipefail
SCRATCH=/orcd/scratch/orcd/011/ncomati
REPO="$SCRATCH/state-and-local-pension"
BATCH=_verify_s7

echo "=== $(date) job $SLURM_JOB_ID on $(hostname), restart #${SLURM_RESTART_COUNT:-0} ==="
echo "=== repo HEAD: $(cd "$REPO" && git rev-parse --short HEAD) ==="
module load apptainer/1.4.2 miniforge/24.3.0-0

pkill -9 -u "$USER" -f "vllm serve" 2>/dev/null || true
sleep 5
trap 'pkill -9 -u "$USER" -f "vllm serve" 2>/dev/null || true' EXIT

apptainer exec --nv -B "$SCRATCH" --env CC=gcc --env CXX=g++ "$SCRATCH/containers/vllm_dir" vllm serve "$SCRATCH/models/qwen35-122b-fp8" --served-model-name qwen35-122b-fp8 --tensor-parallel-size 2 --max-model-len 262144 --gpu-memory-utilization 0.90 --port 8000 > "$SCRATCH/vllm_sbatch.log" 2>&1 &

python "$REPO/Data Extraction/engaging_beta/wait_health.py" \
  --url http://127.0.0.1:8000/health --timeout 900 || {
    echo "!! vLLM never healthy on $(hostname) after 900s - likely a bad node:"
    echo "   the TP=2 boot dies in CUDASymmetricMemory (custom all-reduce over"
    echo "   GPU peer/NVLink), a per-node hardware fault. Requeue onto a fresh node."
    echo "   If good nodes are scarce, a marginal node may still boot with"
    echo "   --disable-custom-all-reduce and NCCL_P2P_DISABLE=1 (slower, NCCL fallback)."
    echo "   see $SCRATCH/vllm_sbatch.log"
    scontrol requeue "$SLURM_JOB_ID"; sleep 120; exit 1; }

export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL=qwen35-122b-fp8
export OPENAI_API_KEY=dummy
export EXTRACT_DUMP_DIR="$SCRATCH/dumps"; mkdir -p "$EXTRACT_DUMP_DIR"

cd "$REPO/Data Extraction"
# fix 1 (derive-level annualize): the chi_ff monthly wage exhibit
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans chi_ff   --targets Age_Serv_Wage
# fix 2 (interleaved-exhibit guard): the 3 crashed Segal-template cells
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans bos      --targets Age_Serv_Num,Age_Serv_Wage
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans lax_gen  --targets Age_Serv_Wage
# regression set: same layout, already-working cells must not move
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans lax_uty   --targets Age_Serv_Num
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans lax_ffpol --targets Age_Serv_Wage
echo "=== verify finished ($(date)); summary in runs/$BATCH/ ==="
