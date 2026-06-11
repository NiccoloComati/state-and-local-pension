#!/usr/bin/env bash
#SBATCH --job-name=spm_py_asset
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:?Neither PROJECT_ROOT nor SLURM_SUBMIT_DIR is set}}"
CLUSTER_DIR="${PROJECT_ROOT}/Cluster Code/cluster_062026"
SCRIPT_DIR="${CLUSTER_DIR}/Python Code/engaging"

PLAN_FILE="${PLAN_FILE:?PLAN_FILE must be set by submit_slurm.sh}"
TASK_ID="${SLURM_ARRAY_TASK_ID:-1}"
RUN_TAG="${RUN_TAG:-python_run}"
NUM_SIM="${NUM_SIM:-1000}"

cd "${PROJECT_ROOT}"
mkdir -p "Results/Runs/${RUN_TAG}/_logs"

PLAN="$(sed -n "${TASK_ID}p" "${PLAN_FILE}")"
if [[ -z "${PLAN}" ]]; then
  echo "No plan found for task ${TASK_ID} in ${PLAN_FILE}" >&2
  exit 1
fi

OUTPUT_FILE="Results/Runs/${RUN_TAG}/${PLAN}/${PLAN}_AssetSim_2asset_${RUN_TAG}.pkl"
if [[ "${SKIP_EXISTING_ASSET:-0}" == "1" && "${OVERWRITE:-0}" != "1" && -s "${OUTPUT_FILE}" ]]; then
  echo "[$(date)] Skipping ${PLAN}; asset output already exists: ${OUTPUT_FILE}"
  exit 0
fi

LOG_FILE="Results/Runs/${RUN_TAG}/_logs/python_asset_${PLAN}_${RUN_TAG}.log"
exec >> "${LOG_FILE}" 2>&1

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/engaging_python_env.sh"
setup_python_env

COMMAND=(
  "${PYTHON_BIN}"
  "${CLUSTER_DIR}/Python Code/asset_simulation.py"
  "--plans" "${PLAN}"
  "--num-sim" "${NUM_SIM}"
  "--run-tag" "${RUN_TAG}"
)
if [[ -n "${SEED:-}" ]]; then
  COMMAND+=("--seed" "$((SEED + TASK_ID - 1))")
fi
if [[ "${OVERWRITE:-0}" == "1" ]]; then
  COMMAND+=("--overwrite")
fi

echo "[$(date)] Starting Python asset simulation for ${PLAN}"
echo "Project root: ${PROJECT_ROOT}"
echo "Command: ${COMMAND[*]}"
"${COMMAND[@]}"
echo "[$(date)] Finished Python asset simulation for ${PLAN}"
