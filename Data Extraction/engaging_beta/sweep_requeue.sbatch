#!/bin/bash
# Preemption-proof corpus sweep. Boots vLLM, runs the RESUMABLE batch into a
# fixed dir, and --requeue lets SLURM resubmit the whole job after a preemption;
# the resumed job re-boots and continues where the summary.json left off
# (completed runs are skipped). No babysitting, no lost work.
#
# Submit once:   sbatch engaging_beta/sweep_requeue.sbatch
# Watch:         tail -f /orcd/scratch/orcd/011/ncomati/sweep_<jobid>.log
#                (or the resumable summary: runs/_batch_resumable/summary.json)
# Edit PLANS/TARGETS below to scope it (default = whole corpus).
#
#SBATCH -J pension-sweep
#SBATCH -p mit_preemptable
#SBATCH -N 1
#SBATCH --gres=gpu:h200:2
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 8:00:00
#SBATCH --requeue
#SBATCH -o /orcd/scratch/orcd/011/ncomati/sweep_%j.log

set -uo pipefail
SCRATCH=/orcd/scratch/orcd/011/ncomati
REPO="$SCRATCH/state-and-local-pension"
BATCH=_batch_resumable          # fixed name -> a requeued job resumes it
# PLANS/TARGETS: leave empty for the full corpus, or scope like:
#   PLANS="--plans mil,dal,phx,sd,lax_uty,chi_pol,chi_ff"
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
echo "=== sweep finished cleanly ($(date)); summary in runs/$BATCH/ ==="
