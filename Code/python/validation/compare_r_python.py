"""
Compare R deterministic/asset outputs against Python translated outputs.

The deterministic comparison is intended to be exact up to numerical tolerance.
Asset-output path equality only makes sense if both runs used identical shocks;
the active R asset script does not save shocks and Python's RNG is not R's RNG.
"""

from __future__ import annotations

import argparse
import math
import pickle
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RUN_TAG = "062026"
DEFAULT_PLAN_YEAR = 2022
DETAL_MATRICES = ["Assets", "AAL", "NormalCost", "cash_outflows", "cash_inflows"]
ASSET_MATRICES = ["Assets", "AAL", "NormalCost", "cash_outflows", "cash_inflows"]
SCALARS = [
    "ppid", "plan", "plan_id", "plan_year", "Nyear", "NMonte", "num_sim",
    "run_tag", "Inflation", "rf", "discountrate", "Model_AAL",
    "CAFR_AAL", "Percent_difference",
]


R_EXPORT_SCRIPT = r"""
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: compare_export.R <rdata_path> <out_dir>")
}
rdata_path <- args[[1]]
out_dir <- args[[2]]
e <- new.env(parent = emptyenv())
load(rdata_path, envir = e)

write_matrix <- function(name) {
  if (!exists(name, envir = e, inherits = FALSE)) return(invisible(NULL))
  value <- get(name, envir = e, inherits = FALSE)
  if (!(is.vector(value) || is.matrix(value) || is.array(value) ||
        is.data.frame(value))) return(invisible(NULL))
  write.csv(as.matrix(value),
            file = file.path(out_dir, paste0(name, ".csv")),
            row.names = FALSE, na = "")
}

for (name in c("Assets", "AAL", "NormalCost", "cash_outflows", "cash_inflows")) {
  write_matrix(name)
}

write_list <- function(name) {
  if (!exists(name, envir = e, inherits = FALSE)) return(invisible(NULL))
  value <- get(name, envir = e, inherits = FALSE)
  if (!is.list(value)) return(invisible(NULL))
  for (i in seq_along(value)) {
    item <- value[[i]]
    if (is.vector(item) || is.matrix(item) || is.array(item) ||
        is.data.frame(item)) {
      write.csv(as.matrix(item),
                file = file.path(out_dir, paste0(name, "__", i, ".csv")),
                row.names = FALSE, na = "")
    }
  }
}

for (name in c(paste0("MainRes_Tier", 1:6), "RetRes")) {
  write_list(name)
}

scalar_df <- data.frame(name = character(), value = character())
for (name in c("ppid", "plan", "plan_id", "plan_year", "Nyear", "NMonte",
               "num_sim", "run_tag", "Inflation", "rf", "discountrate",
               "Model_AAL", "CAFR_AAL", "Percent_difference")) {
  if (exists(name, envir = e, inherits = FALSE)) {
    value <- get(name, envir = e, inherits = FALSE)
    if (length(value) > 0) {
      scalar_df <- rbind(
        scalar_df,
        data.frame(name = name,
                   value = paste(as.character(value), collapse = ";"),
                   stringsAsFactors = FALSE)
      )
    }
  }
}
write.csv(scalar_df, file = file.path(out_dir, "scalars.csv"),
          row.names = FALSE, na = "")
"""


def project_root() -> Path:
    # validation/ → Python Code/ → cluster_062026/ → Cluster Code/ → State Pension Model/
    return Path(__file__).resolve().parents[3]


ROOT = project_root()


def find_rscript() -> Path:
    found = shutil.which("Rscript")
    if found:
        return Path(found)
    candidates = sorted(Path("C:/Program Files/R").glob("R-*/bin/Rscript.exe"))
    candidates.extend(sorted(Path("C:/Program Files/R").glob("R-*/bin/x64/Rscript.exe")))
    if candidates:
        return candidates[-1]
    raise FileNotFoundError("Rscript was not found.")


def read_csv_matrix(path: Path) -> np.ndarray:
    return pd.read_csv(path).to_numpy(dtype=float)


def read_canonical_plans(plan_file: Path) -> list[str]:
    plans = []
    for line in plan_file.read_text().splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            plans.append(value)
    return plans


def default_plan_file(run_tag: str) -> Path:
    current_canonical = ROOT / "Code" / "python" / "config" / "plans_38.txt"
    if current_canonical.exists():
        return current_canonical
    raise FileNotFoundError(
        "No plan list found. Pass --plan-file explicitly."
    )


def parse_plans(value: str, plan_file: Path) -> list[str]:
    if value.lower() == "all":
        return [plan for plan in read_canonical_plans(plan_file) if plan != "MA50"]
    return [part.strip() for part in value.split(",") if part.strip()]


def coerce_scalar(text: object) -> object:
    if text is None or pd.isna(text):
        return None
    value = str(text)
    try:
        return float(value)
    except ValueError:
        return value


def export_rdata(rdata_path: Path, out_dir: Path, rscript: Path | None) -> None:
    r_bin = rscript or find_rscript()
    script_path = out_dir / "compare_export.R"
    script_path.write_text(R_EXPORT_SCRIPT, encoding="utf-8")
    subprocess.run(
        [str(r_bin), str(script_path), str(rdata_path), str(out_dir)],
        check=True,
        cwd=ROOT,
    )


def load_python_pickle(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as handle:
            return pickle.load(handle)
    except Exception as exc:
        raise RuntimeError(f"Could not load Python pickle {path}: {exc}") from exc


def python_matrix(py: dict[str, object], name: str) -> np.ndarray | None:
    if name in py:
        return np.asarray(py[name], dtype=float)
    if name.startswith("MainRes_Tier") and "MainRes" in py:
        tier_text, idx_text = name.replace("MainRes_Tier", "").split("__")
        tier = int(tier_text)
        idx = int(idx_text) - 1
        return np.asarray(py["MainRes"][tier][idx], dtype=float)
    if name.startswith("RetRes") and "RetRes" in py:
        idx = int(name.split("__")[-1]) - 1
        return np.asarray(py["RetRes"][idx], dtype=float)
    return None


def compare_arrays(
    label: str,
    r_arr: np.ndarray,
    py_arr: np.ndarray,
    tolerance: float,
    relative_tolerance: float,
) -> dict[str, object]:
    if r_arr.shape != py_arr.shape:
        return {
            "object": label,
            "status": "shape_mismatch",
            "r_shape": str(r_arr.shape),
            "py_shape": str(py_arr.shape),
            "max_abs": np.nan,
            "max_rel": np.nan,
        }
    diff = np.abs(r_arr - py_arr)
    denom = np.abs(r_arr) + 1e-12
    rel = diff / denom
    max_abs = float(np.nanmax(diff)) if diff.size else 0.0
    max_rel = float(np.nanmax(rel)) if rel.size else 0.0
    ok = max_abs <= tolerance or max_rel <= relative_tolerance
    return {
        "object": label,
        "status": "ok" if ok else "mismatch",
        "r_shape": str(r_arr.shape),
        "py_shape": str(py_arr.shape),
        "max_abs": max_abs,
        "max_rel": max_rel,
    }


def compare_plan(
    plan: str,
    kind: str,
    tolerance: float,
    relative_tolerance: float,
    rscript: Path | None,
    r_run_dir: Path,
    py_run_dir: Path,
    r_run_tag: str,
    py_run_tag: str,
    plan_year: int,
) -> pd.DataFrame:
    r_plan_dir = r_run_dir / plan
    py_plan_dir = py_run_dir / plan
    if kind == "detal":
        r_candidates = [
            r_plan_dir / f"{plan}_detAL_{r_run_tag}.RData",
            r_plan_dir / f"{plan}_detAL_{plan_year}_{r_run_tag}.RData",
        ]
        py_path = py_plan_dir / f"{plan}_detAL_{py_run_tag}.pkl"
    else:
        r_candidates = [
            r_plan_dir / f"{plan}_AssetSim_2asset_{r_run_tag}.RData",
            r_plan_dir / f"{plan}_AssetSim_{plan_year}_2asset_{r_run_tag}.RData",
        ]
        py_path = py_plan_dir / f"{plan}_AssetSim_2asset_{py_run_tag}.pkl"

    r_path = next((path for path in r_candidates if path.exists()), None)
    if r_path is None:
        missing_row = pd.DataFrame([{
            "plan": plan, "kind": kind, "object": "n/a",
            "status": "missing_r_output", "r_shape": "", "py_shape": "",
            "max_abs": float("nan"), "max_rel": float("nan"),
        }])
        return missing_row
    if not py_path.exists():
        missing_row = pd.DataFrame([{
            "plan": plan, "kind": kind, "object": "n/a",
            "status": "missing_py_output", "r_shape": "", "py_shape": "",
            "max_abs": float("nan"), "max_rel": float("nan"),
        }])
        return missing_row

    py = load_python_pickle(py_path)

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        export_rdata(r_path, temp_dir, rscript)

        matrix_files = sorted(path for path in temp_dir.glob("*.csv") if path.name != "scalars.csv")
        for matrix_file in matrix_files:
            label = matrix_file.stem
            r_arr = read_csv_matrix(matrix_file)
            py_arr = python_matrix(py, label)
            if py_arr is None:
                rows.append({
                    "object": label,
                    "status": "missing_python_object",
                    "r_shape": str(r_arr.shape),
                    "py_shape": "",
                    "max_abs": np.nan,
                    "max_rel": np.nan,
                })
                continue
            rows.append(compare_arrays(label, r_arr, py_arr, tolerance, relative_tolerance))

        scalars_path = temp_dir / "scalars.csv"
        if scalars_path.exists():
            r_scalars = pd.read_csv(scalars_path)
            for _, row in r_scalars.iterrows():
                name = row["name"]
                if name not in py:
                    continue
                r_value = coerce_scalar(row["value"])
                # Recompute Percent_difference from its components so the
                # comparison is independent of which formula version each
                # pkl/RData was saved with.
                if name == "Percent_difference":
                    r_model  = coerce_scalar(r_scalars.loc[r_scalars["name"] == "Model_AAL",  "value"].iloc[0]) if "Model_AAL"  in r_scalars["name"].values else None
                    r_cafr   = coerce_scalar(r_scalars.loc[r_scalars["name"] == "CAFR_AAL",   "value"].iloc[0]) if "CAFR_AAL"   in r_scalars["name"].values else None
                    py_model = py.get("Model_AAL"); py_cafr = py.get("CAFR_AAL")
                    if isinstance(py_model, np.generic): py_model = py_model.item()
                    if isinstance(py_cafr,  np.generic): py_cafr  = py_cafr.item()
                    def _pct(model, cafr):
                        if model is None or cafr is None: return None
                        if isinstance(model, float) and math.isnan(model): return float("nan")
                        if isinstance(cafr,  float) and math.isnan(cafr):  return float("nan")
                        cafr_f = float(cafr)
                        return (float(model) - cafr_f) / cafr_f if cafr_f != 0 else float("nan")
                    r_value  = _pct(r_model,  r_cafr)
                    py_value = _pct(py_model, py_cafr)
                else:
                    py_value = py[name]
                    if isinstance(py_value, np.generic):
                        py_value = py_value.item()
                r_missing = r_value is None or (isinstance(r_value, float) and math.isnan(r_value))
                py_missing = py_value is None or (isinstance(py_value, float) and math.isnan(py_value))
                if r_missing and py_missing:
                    rows.append({
                        "object": name, "status": "ok",
                        "r_shape": "scalar", "py_shape": "scalar",
                        "max_abs": np.nan, "max_rel": np.nan,
                    })
                    continue
                if isinstance(r_value, float) and isinstance(py_value, (float, int)):
                    diff = abs(r_value - float(py_value))
                    rel = diff / (abs(r_value) + 1e-12)
                    rows.append({
                        "object": name,
                        "status": "ok" if diff <= tolerance or rel <= relative_tolerance else "mismatch",
                        "r_shape": "scalar",
                        "py_shape": "scalar",
                        "max_abs": diff,
                        "max_rel": rel,
                    })
                else:
                    same_value = str(r_value) == str(py_value)
                    expected_run_tags = (
                        name == "run_tag"
                        and str(r_value) == r_run_tag
                        and str(py_value) == py_run_tag
                    )
                    rows.append({
                        "object": name,
                        "status": "ok" if same_value or expected_run_tags else "mismatch",
                        "r_shape": "scalar",
                        "py_shape": "scalar",
                        "max_abs": np.nan,
                        "max_rel": np.nan,
                    })

    out = pd.DataFrame(rows)
    out.insert(0, "plan", plan)
    out.insert(1, "kind", kind)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", required=True, help="Comma-separated plans")
    parser.add_argument("--kind", choices=["detal", "asset"], default="detal")
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--relative-tolerance", type=float, default=1e-10)
    parser.add_argument("--run-tag", default=DEFAULT_RUN_TAG)
    parser.add_argument("--r-run-tag", default=None)
    parser.add_argument("--py-run-tag", default=None)
    parser.add_argument("--plan-year", type=int, default=DEFAULT_PLAN_YEAR)
    parser.add_argument("--plan-file", default=None)
    parser.add_argument("--rscript", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    rscript = Path(args.rscript) if args.rscript else None
    r_run_tag = args.r_run_tag or args.run_tag
    py_run_tag = args.py_run_tag or args.run_tag
    r_run_dir = ROOT / "Results" / "Runs" / r_run_tag
    py_run_dir = ROOT / "Results" / "Runs" / py_run_tag
    plan_file = Path(args.plan_file) if args.plan_file else default_plan_file(py_run_tag)
    plans = parse_plans(args.plans, plan_file)

    pieces = []
    for plan in plans:
        pieces.append(
            compare_plan(
                plan=plan,
                kind=args.kind,
                tolerance=args.tolerance,
                relative_tolerance=args.relative_tolerance,
                rscript=rscript,
                r_run_dir=r_run_dir,
                py_run_dir=py_run_dir,
                r_run_tag=r_run_tag,
                py_run_tag=py_run_tag,
                plan_year=args.plan_year,
            )
        )
    result = pd.concat(pieces, ignore_index=True)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(args.output, index=False)
    print(result.to_string(index=False))

    bad = result[~result["status"].isin(["ok"])]
    return 1 if len(bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
