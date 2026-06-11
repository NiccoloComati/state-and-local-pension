#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
if [[ -z "${PROJECT_ROOT:-}" ]]; then
  if [[ "$(basename "$(dirname "${CLUSTER_DIR}")")" == "Cluster Code" ]]; then
    PROJECT_ROOT="$(cd "${CLUSTER_DIR}/../.." && pwd)"
  else
    PROJECT_ROOT="$(cd "${CLUSTER_DIR}/.." && pwd)"
  fi
fi

RUN_TAG="${RUN_TAG:-python_run}"
STAGE="${STAGE:-both}"
MAX_PARALLEL="${MAX_PARALLEL:-8}"
NUM_SIM="${NUM_SIM:-1000}"
PLAN_YEAR="${PLAN_YEAR:-2022}"
DEPENDENCY_TYPE="${DEPENDENCY_TYPE:-afterok}"
UPLOADED_PLAN_FILE="${PLAN_FILE:-${PROJECT_ROOT}/Results/Runs/${RUN_TAG}/_remote/uploaded_plans.txt}"
PLANS="${PLANS:-all}"

case "${STAGE}" in
  detal|asset|both) ;;
  *)
    echo "STAGE must be one of: detal, asset, both" >&2
    exit 1
    ;;
esac

cd "${PROJECT_ROOT}"
mkdir -p "Results/Runs/${RUN_TAG}/_logs" "Results/Runs/${RUN_TAG}/_slurm"

# Install required packages once on the login node before jobs start
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/engaging_python_env.sh"
setup_python_env

EFFECTIVE_PLAN_FILE="Results/Runs/${RUN_TAG}/_slurm/plans.txt"
if [[ ! -f "${UPLOADED_PLAN_FILE}" ]]; then
  echo "Uploaded plan file not found: ${UPLOADED_PLAN_FILE}" >&2
  echo "Run upload first, or set PLAN_FILE to the uploaded plan list." >&2
  exit 1
fi

AVAILABLE_PLAN_FILE="Results/Runs/${RUN_TAG}/_slurm/uploaded_plans_clean.txt"
grep -v '^[[:space:]]*$' "${UPLOADED_PLAN_FILE}" |
  tr -d '\r' |
  grep -v '^[[:space:]]*#' |
  awk '$0 != "MA50"' > "${AVAILABLE_PLAN_FILE}"

if [[ -n "${PLANS}" && "${PLANS}" != "all" ]]; then
  : > "${EFFECTIVE_PLAN_FILE}"
  IFS=',' read -r -a REQUESTED_PLANS <<< "${PLANS}"
  missing=()
  for raw_plan in "${REQUESTED_PLANS[@]}"; do
    plan="$(printf '%s' "${raw_plan}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    [[ -n "${plan}" ]] || continue
    [[ "${plan}" == "MA50" ]] && continue
    if grep -Fxq "${plan}" "${AVAILABLE_PLAN_FILE}"; then
      printf '%s\n' "${plan}" >> "${EFFECTIVE_PLAN_FILE}"
    else
      missing+=("${plan}")
    fi
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "Requested plan(s) not uploaded: ${missing[*]}" >&2
    echo "Upload them first, or upload with UploadPlans=all." >&2
    exit 1
  fi
else
  cp "${AVAILABLE_PLAN_FILE}" "${EFFECTIVE_PLAN_FILE}"
fi
PLAN_FILE="$(cd "$(dirname "${EFFECTIVE_PLAN_FILE}")" && pwd)/$(basename "${EFFECTIVE_PLAN_FILE}")"

N_PLANS="$(wc -l < "${PLAN_FILE}" | tr -d ' ')"
if [[ "${N_PLANS}" -lt 1 ]]; then
  echo "No plans to run after excluding blanks/comments/MA50." >&2
  exit 1
fi

SBATCH_OPTS=()
if [[ -n "${PARTITION:-}" ]]; then
  SBATCH_OPTS+=(--partition="${PARTITION}")
fi
if [[ -n "${ACCOUNT:-}" ]]; then
  SBATCH_OPTS+=(--account="${ACCOUNT}")
fi
if [[ -n "${QOS:-}" ]]; then
  SBATCH_OPTS+=(--qos="${QOS}")
fi

export PROJECT_ROOT PLAN_FILE RUN_TAG STAGE MAX_PARALLEL NUM_SIM PLAN_YEAR
export TIER_FILE="${TIER_FILE:-planchanges_main_2022_clean.xlsx}"
export DATE_RUN="${DATE_RUN:-}"
export SEED="${SEED:-}"
export PYTHON_BIN="${PYTHON_BIN:-}"
export PYTHON_MODULE="${PYTHON_MODULE:-}"
export CONDA_MODULE="${CONDA_MODULE:-}"
export CONDA_ENV="${CONDA_ENV:-}"
export VENV="${VENV:-}"
export SKIP_EXISTING_DETAL="${SKIP_EXISTING_DETAL:-0}"
export SKIP_EXISTING_ASSET="${SKIP_EXISTING_ASSET:-0}"
export OVERWRITE="${OVERWRITE:-0}"

submit_job() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    echo "[dry-run] sbatch $*" >&2
    echo "0"
  else
    sbatch --parsable "$@"
  fi
}

DETAIL_JOB_ID=""
ASSET_JOB_ID=""

if [[ "${STAGE}" == "detal" || "${STAGE}" == "both" ]]; then
  DETAIL_JOB_ID="$(
    submit_job \
      "${SBATCH_OPTS[@]}" \
      --export=ALL \
      --array="1-${N_PLANS}%${MAX_PARALLEL}" \
      --output="Results/Runs/${RUN_TAG}/_logs/slurm_py_detal_%A_%a.out" \
      --error="Results/Runs/${RUN_TAG}/_logs/slurm_py_detal_%A_%a.err" \
      "${SCRIPT_DIR}/slurm_detal_array.sh"
  )"
fi

if [[ "${STAGE}" == "asset" || "${STAGE}" == "both" ]]; then
  ASSET_ARGS=(
    "${SBATCH_OPTS[@]}"
    --export=ALL
    --array="1-${N_PLANS}%${MAX_PARALLEL}"
    --output="Results/Runs/${RUN_TAG}/_logs/slurm_py_asset_%A_%a.out"
    --error="Results/Runs/${RUN_TAG}/_logs/slurm_py_asset_%A_%a.err"
  )
  if [[ -n "${DETAIL_JOB_ID}" ]]; then
    ASSET_ARGS+=(--dependency="${DEPENDENCY_TYPE}:${DETAIL_JOB_ID}")
  fi
  ASSET_ARGS+=("${SCRIPT_DIR}/slurm_asset_array.sh")
  ASSET_JOB_ID="$(submit_job "${ASSET_ARGS[@]}")"
fi

cat <<EOF
Submitted Python workflow.

Run tag:      ${RUN_TAG}
Stage:        ${STAGE}
Uploaded file: ${UPLOADED_PLAN_FILE}
Run plan file: ${PLAN_FILE}
Plans:        ${N_PLANS}
Max parallel: ${MAX_PARALLEL}
Num sim:      ${NUM_SIM}

Deterministic array job: ${DETAIL_JOB_ID:-not submitted}
Asset array job:         ${ASSET_JOB_ID:-not submitted}

Monitor:
  squeue --me
  sacct -j <job_id> --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS

Logs:
  Results/Runs/${RUN_TAG}/_logs/
EOF
