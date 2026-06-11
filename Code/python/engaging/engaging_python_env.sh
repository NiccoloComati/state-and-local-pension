#!/usr/bin/env bash

setup_python_env() {
  if [[ -n "${PYTHON_MODULE:-}" ]]; then
    if ! command -v module >/dev/null 2>&1; then
      echo "PYTHON_MODULE was set, but the module command is unavailable." >&2
      return 1
    fi
    module load "${PYTHON_MODULE}"
  fi

  if [[ -n "${CONDA_MODULE:-}" ]]; then
    if ! command -v module >/dev/null 2>&1; then
      echo "CONDA_MODULE was set, but the module command is unavailable." >&2
      return 1
    fi
    module load "${CONDA_MODULE}"
  fi

  if [[ -n "${CONDA_ENV:-}" ]]; then
    if ! command -v conda >/dev/null 2>&1; then
      echo "CONDA_ENV was set, but conda is unavailable." >&2
      return 1
    fi
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV}"
  fi

  if [[ -n "${VENV:-}" ]]; then
    # shellcheck disable=SC1091
    source "${VENV}/bin/activate"
  fi

  export PYTHON_BIN="${PYTHON_BIN:-python}"
  if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Python not found. Set PYTHON_BIN, PYTHON_MODULE, CONDA_ENV, or VENV." >&2
    return 1
  fi

  "${PYTHON_BIN}" -c "import openpyxl, pyarrow" 2>/dev/null || \
    "${PYTHON_BIN}" -m pip install --user --quiet openpyxl pyarrow
}
