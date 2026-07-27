#!/bin/bash
# Scoped verification of the 2026-07-27 solve-now fixes (offline commits
# 88a12da wage-ratio guard, 0a3e963 duplicate-label guard). Boots vLLM and
# re-runs ONLY the affected cells into a FRESH batch dir (_verify_fixes) so the
# already-0.00 cells in _batch_resumable are not skipped. Same preemption-proof
# shape as sweep_requeue.sbatch.
#
# Submit:  sbatch engaging_beta/verify_fixes.sbatch
# Watch:   tail -f /orcd/scratch/orcd/011/ncomati/verify_<jobid>.log
# Read:    runs/_verify_fixes/summary.json  (expect chi_* Age_Serv_Wage ~1.0,
#          mil Retirement ~1.0)
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
BATCH=_verify_fixes

echo "=== $(date) job $SLURM_JOB_ID on $(hostname), restart #${SLURM_RESTART_COUNT:-0} ==="
module load apptainer/1.4.2 miniforge/24.3.0-0

pkill -9 -u "$USER" -f "vllm serve" 2>/dev/null || true
sleep 5
trap 'pkill -9 -u "$USER" -f "vllm serve" 2>/dev/null || true' EXIT

apptainer exec --nv -B "$SCRATCH" --env CC=gcc --env CXX=g++ "$SCRATCH/containers/vllm_dir" vllm serve "$SCRATCH/models/qwen35-122b-fp8" --served-model-name qwen35-122b-fp8 --tensor-parallel-size 2 --max-model-len 262144 --gpu-memory-utilization 0.90 --port 8000 > "$SCRATCH/vllm_sbatch.log" 2>&1 &

python "$REPO/Data Extraction/engaging_beta/wait_health.py" \
  --url http://127.0.0.1:8000/health --timeout 900 || {
    echo "!! vLLM never healthy on $(hostname) after 900s (likely a bad node:"
    echo "   the qwen_gdn_linear_attn TP=2 boot crash) - requeueing onto a fresh node."
    echo "   see $SCRATCH/vllm_sbatch.log"
    scontrol requeue "$SLURM_JOB_ID"; sleep 120; exit 1; }

export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL=qwen35-122b-fp8
export OPENAI_API_KEY=dummy
export EXTRACT_DUMP_DIR="$SCRATCH/dumps"; mkdir -p "$EXTRACT_DUMP_DIR"

cd "$REPO/Data Extraction"
# fix 1 (wage totals-as-averages guard): the 4 chi wage 0.00s
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans chi_edu,chi_ff,chi_gen,chi_pol --targets Age_Serv_Wage
# fix 2 (duplicate-label guard): mil Retirement
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans mil --targets Retirement
echo "=== verify finished ($(date)); summary in runs/$BATCH/ ==="
