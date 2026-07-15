#!/bin/bash
# Self-contained Engaging job: serve vLLM, wait for health, run the scored
# fidelity battery, shut down. One artifact dir per run = preemption-safe.
# Usage: sbatch serve_and_run.sbatch   (edit MODEL/REPO paths first)
#SBATCH -J pension-extract-beta
#SBATCH -p mit_normal_gpu
#SBATCH -G h200:2
#SBATCH -c 30
#SBATCH --mem=400G
#SBATCH -t 06:00:00
#SBATCH -o logs/%x-%j.out

set -euo pipefail
module load apptainer

MODEL_DIR="$SCRATCH/models/qwen35-122b-fp8"
SERVED_NAME="qwen35-122b-fp8"
IMAGE="$HOME/vllm.sif"                       # pinned tag, pulled on login node
REPO="$HOME/state-and-local-pension"

apptainer exec --nv -B "$SCRATCH" "$IMAGE" \
  vllm serve "$MODEL_DIR" \
    --served-model-name "$SERVED_NAME" \
    --tensor-parallel-size 2 \
    --max-model-len 262144 \
    --language-model-only \
    --gpu-memory-utilization 0.92 \
    --enable-prefix-caching \
    --max-num-seqs 2 \
    --seed 0 --port 8000 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

python "$REPO/Data Extraction/engaging_beta/wait_health.py" \
  --url http://127.0.0.1:8000/health --timeout 1800

export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL="$SERVED_NAME"

cd "$REPO/Data Extraction"
# the fidelity battery: hardest case first; each call scores itself against
# the archived human truth and writes a full artifact dir under runs/
for spec in "mil Age_Serv_Num" "phx Age_Serv_Num" "phx Age_Serv_Wage" \
            "phx Retirement" "chi_pol Age_Serv_Num" "sd Age_Serv_Num"; do
  set -- $spec
  echo "=== $1 / $2 ==="
  python pipeline/run_test.py --plan "$1" --target "$2" || echo "!! $1/$2 FAILED"
done
