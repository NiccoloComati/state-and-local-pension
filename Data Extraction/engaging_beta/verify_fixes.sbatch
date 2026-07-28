#!/bin/bash
# Scoped verification of the session-7 fixes. Boots vLLM once and runs ONLY the
# affected cells into a FIXED batch dir (_verify_s8) so a preempted job resumes
# where it stopped, and a later submission can APPEND cells to the same dir
# (already-completed cells are skipped, not repeated).
#
# Round 1 (_verify_s7, job 19074242) CONFIRMED the interleaved-exhibit guard:
#   bos ASN crash -> production, bos ASW crash -> production,
#   lax_gen ASW crash -> 1.0; regression set held (lax_uty ASN 1.0,
#   lax_ffpol ASW 0.92 -> 1.0). chi_ff ASW still crashed, on a DIFFERENT fault
#   (the printed Total line transcribed into cells), now guarded.
#
# Under test here:
#   1daa786  ratio split numerator/denominator + dollars-over-dollars guard
#            + unknown-key guard on map entries
#   4b15f89  group_weighted weights_tables guidance (repeat-an-index + example)
#   6df52f8  +1 printed-total row guard; totals-driven correction retry on the
#            local backend; SIDE-BY-SIDE TABLES prompt paragraph
#
# Cells (14):
#   chi_ff  Age_Serv_Wage  +1 Total row, THEN the monthly x12 - never yet executed
#   chi_edu Age_Serv_Wage  column shift; expect the totals retry to fix it (was 0.00)
#   chi_pol Age_Serv_Wage  ratio-completeness (margins-only numerator, was 0.00)
#   chi_ff/chi_gen/sf/sd/phi Retirement   the ratio gap: 4 wrong + 1 crash
#   chi_gen/sd Avg_Mort    group_weighted weights_tables (were CRASH)
#   sd      Ret_Rate       side-by-side 3-table page (was a decoding LOOP)
#   REGRESSION SET - the prompt changed globally, these must not move:
#   mil Retirement (1.0)   lax_gen Age_Serv_Wage (1.0)   chi_gen Age_Serv_Wage (0.9831)
#
# Submit:  sbatch --exclude=node4002,node5201 engaging_beta/verify_fixes.sbatch
# Watch:   tail -f /orcd/scratch/orcd/011/ncomati/verify_<jobid>.log
# Read:    runs/_verify_s8/summary.csv
#
#SBATCH -J pension-verify
#SBATCH -p mit_preemptable
#SBATCH -N 1
#SBATCH --gres=gpu:h200:2
#SBATCH -c 8
#SBATCH --mem=96G
#SBATCH -t 4:00:00
#SBATCH --requeue
#SBATCH -o /orcd/scratch/orcd/011/ncomati/verify_%j.log

set -uo pipefail
SCRATCH=/orcd/scratch/orcd/011/ncomati
REPO="$SCRATCH/state-and-local-pension"
BATCH=_verify_s8

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
# transcription guards (+1 Total row, totals-driven correction retry)
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans chi_ff,chi_edu,chi_pol --targets Age_Serv_Wage
# the ratio gap: 4 silently-wrong cells + phi's crash
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans chi_ff,chi_gen,sf,sd,phi --targets Retirement
# group_weighted weights_tables guidance
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans chi_gen,sd --targets Avg_Mort
# side-by-side page guidance (the decoding loop)
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans sd --targets Ret_Rate
# regression set: known-good cells the global prompt change must not disturb
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans mil --targets Retirement
python pipeline/run_batch.py --batch-dir "$BATCH" --quiet --plans lax_gen,chi_gen --targets Age_Serv_Wage
echo "=== verify finished ($(date)); summary in runs/$BATCH/ ==="
