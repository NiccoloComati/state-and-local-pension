"""Python analysis helpers for pension model run outputs.

The functions here read run artifacts from ``Results/Runs/<run_tag>/`` and
return pandas tables or matplotlib figures. They do not save plots.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

try:
    import pyreadr
except ImportError:  # pragma: no cover - optional dependency
    pyreadr = None


DEFAULT_RUN_TAG = "062026"
DEFAULT_PLAN_YEAR = 2022
ANALYSIS_EXPORT_SUFFIX = "_analysis.RData"
PARQUET_EXPORT_SUFFIX = "_parquet"
DEFAULT_QUANTILES = (0.05, 0.20, 0.50, 0.80, 0.95)
RDATA_MATRIX_OBJECTS = (
    "Assets",
    "AAL",
    "cash_inflows",
    "cash_outflows",
    "NormalCost",
)
RDATA_SCALAR_OBJECTS = (
    "ppid",
    "plan",
    "plan_id",
    "plan_year",
    "Nyear",
    "num_sim",
    "run_tag",
    "Inflation",
    "rf",
    "discountrate",
    "Model_AAL",
    "CAFR_AAL",
    "Percent_difference",
)

R_EXTRACT_SCRIPT = r"""
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: extract_rdata.R <rdata_path> <out_dir>")
}

rdata_path <- args[[1]]
out_dir <- args[[2]]
load(rdata_path)

write_matrix <- function(name) {
  if (!exists(name, envir = .GlobalEnv, inherits = FALSE)) {
    return(invisible(NULL))
  }
  value <- get(name, envir = .GlobalEnv, inherits = FALSE)
  if (!(is.vector(value) || is.matrix(value) || is.array(value) ||
        is.data.frame(value))) {
    return(invisible(NULL))
  }
  write.csv(as.matrix(value),
            file = file.path(out_dir, paste0(name, ".csv")),
            row.names = FALSE,
            na = "")
}

matrix_objects <- c(
  "Assets",
  "AAL",
  "cash_inflows",
  "cash_outflows",
  "NormalCost"
)
invisible(lapply(matrix_objects, write_matrix))

scalar_objects <- c(
  "ppid",
  "plan",
  "plan_id",
  "plan_year",
  "Nyear",
  "num_sim",
  "run_tag",
  "Inflation",
  "rf",
  "discountrate",
  "Model_AAL",
  "CAFR_AAL",
  "Percent_difference"
)
scalar_df <- data.frame(name = character(), value = character())
for (name in scalar_objects) {
  if (exists(name, envir = .GlobalEnv, inherits = FALSE)) {
    value <- get(name, envir = .GlobalEnv, inherits = FALSE)
    if (length(value) > 0) {
      scalar_df <- rbind(
        scalar_df,
        data.frame(
          name = name,
          value = paste(as.character(value), collapse = ";"),
          stringsAsFactors = FALSE
        )
      )
    }
  }
}
write.csv(scalar_df, file = file.path(out_dir, "scalars.csv"),
          row.names = FALSE, na = "")

if (exists("planinfo", envir = .GlobalEnv, inherits = FALSE)) {
  write.csv(as.data.frame(planinfo),
            file = file.path(out_dir, "planinfo.csv"),
            row.names = FALSE,
            na = "")
}

if (exists("AssetShare", envir = .GlobalEnv, inherits = FALSE)) {
  write.csv(data.frame(value = as.numeric(AssetShare)),
            file = file.path(out_dir, "AssetShare.csv"),
            row.names = FALSE,
            na = "")
}
"""


@dataclass
class PlanResult:
    """Loaded asset simulation output for one plan."""

    plan: str
    file_path: Path
    matrices: Mapping[str, pd.DataFrame]
    scalars: Mapping[str, object]
    planinfo: pd.DataFrame | None = None
    asset_share: pd.Series | None = None

    @property
    def ppid(self) -> int | None:
        value = self.scalars.get("ppid")
        if value is None or pd.isna(value):
            return None
        return int(float(value))

    @property
    def plan_year(self) -> int:
        value = self.scalars.get("plan_year", 2022)
        return int(float(value))

    @property
    def n_years(self) -> int:
        return int(self.matrices["Assets"].shape[0])

    @property
    def n_simulations(self) -> int:
        return int(self.matrices["Assets"].shape[1])

    def years(self, graph_years: int | None = None) -> np.ndarray:
        n_years = self.n_years if graph_years is None else min(graph_years, self.n_years)
        return np.arange(self.plan_year, self.plan_year + n_years)

    def matrix(self, name: str) -> pd.DataFrame:
        if name not in self.matrices:
            raise KeyError(f"{self.plan} does not contain matrix {name!r}.")
        return self.matrices[name]

    def funding_ratio(self) -> pd.DataFrame:
        aal = self.matrix("AAL").replace(0, np.nan)
        return self.matrix("Assets") / aal


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the model project root from a notebook or script location."""

    current = Path.cwd() if start is None else Path(start)
    current = current.resolve()
    if current.is_file():
        current = current.parent

    for path in (current, *current.parents):
        if (path / "Results").exists() and (
            (path / "Data").exists() or (path / "Code").exists()
        ):
            return path
    raise FileNotFoundError("Could not find project root containing Results/ and data folders.")


def find_rscript() -> Path:
    """Locate Rscript for the temporary .RData extraction bridge."""

    found = shutil.which("Rscript")
    if found:
        return Path(found)

    candidates = sorted(Path("C:/Program Files/R").glob("R-*/bin/Rscript.exe"))
    candidates.extend(sorted(Path("C:/Program Files/R").glob("R-*/bin/x64/Rscript.exe")))
    if candidates:
        return candidates[-1]
    raise FileNotFoundError("Rscript was not found. Install R or add Rscript to PATH.")


def run_dir(root: str | Path | None = None, run_tag: str = DEFAULT_RUN_TAG) -> Path:
    root_path = find_project_root(root)
    return root_path / "Results" / "Runs" / run_tag


def load_manifest(root: str | Path | None = None, run_tag: str = DEFAULT_RUN_TAG) -> pd.DataFrame:
    path = run_dir(root, run_tag) / "_manifest.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def available_asset_files(
    root: str | Path | None = None,
    run_tag: str = DEFAULT_RUN_TAG,
    plans: Sequence[str] | None = None,
    prefer_analysis_exports: bool = True,
    plan_year: int = DEFAULT_PLAN_YEAR,
) -> dict[str, Path]:
    """Return existing asset simulation files in the canonical run folder."""

    base = run_dir(root, run_tag)
    if plans is None:
        manifest = load_manifest(root, run_tag)
        plan_list = sorted(manifest["plan"].dropna().unique())
    else:
        plan_list = sorted(plans)

    out: dict[str, Path] = {}
    for plan in plan_list:
        candidates = [
            base / plan / f"{plan}_AssetSim_2asset_{run_tag}.RData",
            base / plan / f"{plan}_AssetSim_{plan_year}_2asset_{run_tag}.RData",
        ]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is not None:
            analysis_path = analysis_export_path(path)
            out[plan] = analysis_path if prefer_analysis_exports and analysis_path.exists() else path
    return out


def analysis_export_path(asset_file: str | Path) -> Path:
    """Return the clean data-only companion path for a full asset output."""

    asset_file = Path(asset_file)
    return asset_file.with_name(f"{asset_file.stem}{ANALYSIS_EXPORT_SUFFIX}")


def parquet_export_path(
    root: str | Path | None,
    run_tag: str,
    plan: str,
) -> Path:
    """Return the Python parquet asset-output directory for one plan."""

    base = run_dir(root, run_tag)
    return base / plan / f"{plan}_AssetSim_2asset_{run_tag}{PARQUET_EXPORT_SUFFIX}"


def available_parquet_outputs(
    root: str | Path | None = None,
    run_tag: str = DEFAULT_RUN_TAG,
    plans: Sequence[str] | None = None,
) -> dict[str, Path]:
    """Return existing Python parquet asset outputs in the canonical run folder."""

    base = run_dir(root, run_tag)
    if plans is None:
        plan_list = sorted(
            path.name for path in base.iterdir()
            if path.is_dir() and not path.name.startswith("_")
        )
    else:
        plan_list = sorted(plans)

    out: dict[str, Path] = {}
    for plan in plan_list:
        path = parquet_export_path(root, run_tag, plan)
        if path.exists():
            out[plan] = path
    return out


def detect_result_source(
    root: str | Path | None = None,
    run_tag: str = DEFAULT_RUN_TAG,
    plans: Sequence[str] | None = None,
) -> str:
    """Detect whether a run folder holds Python parquet or R RData asset outputs.

    Returns "parquet" or "rdata". If a run folder contains both, prefers
    "parquet" and prints a note; pass an explicit source to override.
    Raises FileNotFoundError if neither format is present.
    """

    parquet = available_parquet_outputs(root, run_tag, plans=plans)
    try:
        rdata = available_asset_files(root, run_tag, plans=plans)
    except FileNotFoundError:
        rdata = {}
    if parquet and rdata:
        print(
            f"detect_result_source: run '{run_tag}' has both parquet "
            f"({len(parquet)} plans) and RData ({len(rdata)} plans) outputs; "
            "using 'parquet'. Set RESULT_SOURCE explicitly to override."
        )
        return "parquet"
    if parquet:
        return "parquet"
    if rdata:
        return "rdata"
    raise FileNotFoundError(
        f"No parquet or RData asset outputs found under {run_dir(root, run_tag)}"
    )


def _coerce_scalar(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    text = str(value)
    if ";" in text:
        return text
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return int(number)
    return number


def _read_numeric_csv(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    return data.apply(pd.to_numeric, errors="coerce")


def _frame_to_matrix(value: pd.DataFrame | pd.Series) -> pd.DataFrame:
    if isinstance(value, pd.Series):
        value = value.to_frame()
    return value.apply(pd.to_numeric, errors="coerce")


def _frame_to_scalar(value: pd.DataFrame | pd.Series) -> object:
    if isinstance(value, pd.DataFrame):
        if value.empty:
            return None
        raw = value.iloc[0, 0]
    elif isinstance(value, pd.Series):
        if value.empty:
            return None
        raw = value.iloc[0]
    else:
        raw = value
    return _coerce_scalar(raw)


def load_plan_result_pyreadr(rdata_path: str | Path) -> PlanResult:
    """Load one clean data-only RData file with pyreadr."""

    if pyreadr is None:
        raise ImportError("pyreadr is not installed.")

    rdata_path = Path(rdata_path).resolve()
    loaded = pyreadr.read_r(str(rdata_path))

    matrices = {
        name: _frame_to_matrix(loaded[name])
        for name in RDATA_MATRIX_OBJECTS
        if name in loaded
    }
    if "Assets" not in matrices or "AAL" not in matrices:
        raise ValueError(f"{rdata_path} does not contain Assets and AAL.")

    scalars = {
        name: _frame_to_scalar(loaded[name])
        for name in RDATA_SCALAR_OBJECTS
        if name in loaded
    }
    planinfo = loaded.get("planinfo")
    asset_share = None
    if "AssetShare" in loaded:
        asset_share = _frame_to_matrix(loaded["AssetShare"]).iloc[:, 0]

    plan = str(scalars.get("plan") or rdata_path.parent.name)
    return PlanResult(
        plan=plan,
        file_path=rdata_path,
        matrices=matrices,
        scalars=scalars,
        planinfo=planinfo,
        asset_share=asset_share,
    )


def load_plan_result_parquet(parquet_dir: str | Path) -> PlanResult:
    """Load one Python parquet asset-output directory."""

    parquet_dir = Path(parquet_dir).resolve()
    if not parquet_dir.exists():
        raise FileNotFoundError(parquet_dir)

    matrices = {
        name: pd.read_parquet(parquet_dir / f"{name}.parquet")
        for name in RDATA_MATRIX_OBJECTS
        if (parquet_dir / f"{name}.parquet").exists()
    }
    if "Assets" not in matrices or "AAL" not in matrices:
        raise ValueError(f"{parquet_dir} does not contain Assets and AAL.")

    scalars: dict[str, object] = {}
    scalars_path = parquet_dir / "scalars.parquet"
    if scalars_path.exists():
        scalar_df = pd.read_parquet(scalars_path)
        for _, row in scalar_df.iterrows():
            scalars[str(row["name"])] = _coerce_scalar(row["value"])

    planinfo = None
    planinfo_path = parquet_dir / "planinfo.parquet"
    if planinfo_path.exists():
        planinfo = pd.read_parquet(planinfo_path)

    asset_share = None
    asset_share_path = parquet_dir / "AssetShare.parquet"
    if asset_share_path.exists():
        asset_share = pd.read_parquet(asset_share_path)["value"]

    plan = str(scalars.get("plan") or parquet_dir.name.split("_AssetSim_")[0])
    return PlanResult(
        plan=plan,
        file_path=parquet_dir,
        matrices=matrices,
        scalars=scalars,
        planinfo=planinfo,
        asset_share=asset_share,
    )


def load_plan_result_rscript(rdata_path: str | Path, rscript: str | Path | None = None) -> PlanResult:
    """Load one full workspace RData file using a temporary Rscript bridge."""

    rdata_path = Path(rdata_path).resolve()
    if not rdata_path.exists():
        raise FileNotFoundError(rdata_path)

    rscript_path = Path(rscript) if rscript is not None else find_rscript()

    with tempfile.TemporaryDirectory(prefix="pension_rdata_") as tmp:
        tmp_dir = Path(tmp)
        extractor = tmp_dir / "extract_rdata.R"
        extractor.write_text(R_EXTRACT_SCRIPT, encoding="utf-8")
        subprocess.run(
            [str(rscript_path), str(extractor), str(rdata_path), str(tmp_dir)],
            check=True,
            capture_output=True,
            text=True,
        )

        matrices = {
            name: _read_numeric_csv(tmp_dir / f"{name}.csv")
            for name in RDATA_MATRIX_OBJECTS
            if (tmp_dir / f"{name}.csv").exists()
        }
        scalars_path = tmp_dir / "scalars.csv"
        scalars: dict[str, object] = {}
        if scalars_path.exists():
            scalars_df = pd.read_csv(scalars_path)
            scalars = {
                row["name"]: _coerce_scalar(row["value"])
                for _, row in scalars_df.iterrows()
            }

        planinfo_path = tmp_dir / "planinfo.csv"
        planinfo = pd.read_csv(planinfo_path) if planinfo_path.exists() else None

        asset_share_path = tmp_dir / "AssetShare.csv"
        asset_share = None
        if asset_share_path.exists():
            asset_share = pd.read_csv(asset_share_path)["value"]

    if "Assets" not in matrices or "AAL" not in matrices:
        raise ValueError(f"{rdata_path} does not contain Assets and AAL.")

    plan = str(scalars.get("plan") or rdata_path.parent.name)
    return PlanResult(
        plan=plan,
        file_path=rdata_path,
        matrices=matrices,
        scalars=scalars,
        planinfo=planinfo,
        asset_share=asset_share,
    )


def load_plan_result(
    rdata_path: str | Path,
    rscript: str | Path | None = None,
    method: str = "auto",
) -> PlanResult:
    """Load one plan result.

    ``method="auto"`` uses native ``pyreadr`` for clean ``*_analysis.RData``
    files and falls back to Rscript for full ``save.image()`` workspaces.
    ``method="parquet"`` loads a Python parquet asset-output directory.
    """

    rdata_path = Path(rdata_path).resolve()
    if method not in {"auto", "pyreadr", "rscript", "parquet"}:
        raise ValueError("method must be one of: auto, pyreadr, rscript, parquet")

    if method == "parquet":
        return load_plan_result_parquet(rdata_path)
    if method == "pyreadr" or (
        method == "auto" and rdata_path.name.endswith(ANALYSIS_EXPORT_SUFFIX)
    ):
        return load_plan_result_pyreadr(rdata_path)

    return load_plan_result_rscript(rdata_path, rscript=rscript)


def create_analysis_export(
    asset_file: str | Path,
    output_file: str | Path | None = None,
    overwrite: bool = False,
    rscript: str | Path | None = None,
) -> Path:
    """Create a clean data-only RData companion readable by pyreadr."""

    asset_file = Path(asset_file).resolve()
    if output_file is None:
        output_file = analysis_export_path(asset_file)
    output_file = Path(output_file).resolve()

    if output_file.exists() and not overwrite:
        return output_file

    output_file.parent.mkdir(parents=True, exist_ok=True)
    rscript_path = Path(rscript) if rscript is not None else find_rscript()
    asset_posix = asset_file.as_posix()
    output_posix = output_file.as_posix()

    code = f"""
run_env <- new.env(parent = emptyenv())
load({asset_posix!r}, envir = run_env)
objects <- c({', '.join(repr(x) for x in (*RDATA_MATRIX_OBJECTS, *RDATA_SCALAR_OBJECTS, 'planinfo', 'AssetShare'))})
objects <- objects[vapply(objects, exists, logical(1), envir = run_env, inherits = FALSE)]
save(list = objects, file = {output_posix!r}, envir = run_env)
"""
    subprocess.run([str(rscript_path), "-e", code], check=True, capture_output=True, text=True)
    return output_file


def prepare_analysis_exports(
    root: str | Path | None = None,
    run_tag: str = DEFAULT_RUN_TAG,
    plans: Sequence[str] | None = None,
    overwrite: bool = False,
    progress: bool = True,
    plan_year: int = DEFAULT_PLAN_YEAR,
) -> dict[str, Path]:
    """Create clean pyreadr-friendly RData companions for available asset files."""

    files = available_asset_files(
        root,
        run_tag,
        plans=plans,
        prefer_analysis_exports=False,
        plan_year=plan_year,
    )
    rscript = find_rscript()
    exports: dict[str, Path] = {}
    for i, (plan, path) in enumerate(files.items(), start=1):
        if progress:
            print(f"[{i}/{len(files)}] exporting {plan}")
        exports[plan] = create_analysis_export(
            path,
            overwrite=overwrite,
            rscript=rscript,
        )
    return exports


def load_run_results(
    root: str | Path | None = None,
    run_tag: str = DEFAULT_RUN_TAG,
    plans: Sequence[str] | None = None,
    progress: bool = True,
    method: str = "auto",
    source: str = "rdata",
    plan_year: int = DEFAULT_PLAN_YEAR,
) -> dict[str, PlanResult]:
    """Load all available asset simulations for a run."""

    if source not in {"rdata", "parquet"}:
        raise ValueError("source must be one of: rdata, parquet")

    files = (
        available_parquet_outputs(root, run_tag, plans)
        if source == "parquet"
        else available_asset_files(root, run_tag, plans, plan_year=plan_year)
    )
    load_method = "parquet" if source == "parquet" else method
    rscript = None if source == "parquet" else find_rscript()
    results: dict[str, PlanResult] = {}
    for i, (plan, path) in enumerate(files.items(), start=1):
        if progress:
            print(f"[{i}/{len(files)}] loading {plan}")
        results[plan] = load_plan_result(path, rscript=rscript, method=load_method)
    return results


def load_ppd(
    root: str | Path | None = None,
    source: str = "cluster_062026",
    sheet_name: str = "ppd-data-latest",
) -> pd.DataFrame:
    """Load the PPD workbook used for historical actual funded ratios."""

    root_path = find_project_root(root)
    candidate = root_path / "Data" / "Common" / "states" / "ppd-data-latest.xlsx"
    if not candidate.exists():
        candidate = root_path / source / "Common_Data" / "ppd-data-latest.xlsx"
    return pd.read_excel(candidate, sheet_name=sheet_name)


def actual_funding_ratio(ppd: pd.DataFrame, ppid: int | None) -> pd.DataFrame:
    if ppid is None:
        return pd.DataFrame(columns=["fy", "funding_ratio"])
    required = ["ppd_id", "fy", "ActAssets_GASB", "ActLiabilities_GASB"]
    missing = [col for col in required if col not in ppd.columns]
    if missing:
        raise KeyError(f"PPD data is missing columns: {missing}")

    data = ppd.loc[ppd["ppd_id"].astype("Int64") == int(ppid), required].copy()
    data["funding_ratio"] = data["ActAssets_GASB"] / data["ActLiabilities_GASB"]
    return data.sort_values("fy")


def actual_funding_by_plan(
    results: Mapping[str, PlanResult],
    ppd: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for plan, result in results.items():
        data = actual_funding_ratio(ppd, result.ppid)
        data = data.assign(plan=plan)
        rows.append(data)
    if not rows:
        return pd.DataFrame(columns=["plan", "fy", "funding_ratio"])
    return pd.concat(rows, ignore_index=True)


def _qname(q: float) -> str:
    return f"q{int(round(q * 100)):02d}"


def forecast_summary(
    result: PlanResult,
    graph_years: int | None = 15,
    quantiles: Sequence[float] = DEFAULT_QUANTILES,
) -> pd.DataFrame:
    ratios = result.funding_ratio()
    n_years = ratios.shape[0] if graph_years is None else min(graph_years, ratios.shape[0])
    arr = ratios.iloc[:n_years].to_numpy(dtype=float)

    summary = pd.DataFrame(
        {
            "plan": result.plan,
            "year": result.years(n_years),
            "mean": np.nanmean(arr, axis=1),
            "std": np.nanstd(arr, axis=1),
        }
    )
    for q in quantiles:
        summary[_qname(q)] = np.nanquantile(arr, q, axis=1)
    return summary


def average_forecast_summary(
    results: Mapping[str, PlanResult],
    graph_years: int | None = 15,
    quantiles: Sequence[float] = DEFAULT_QUANTILES,
) -> pd.DataFrame:
    pieces = [forecast_summary(result, graph_years, quantiles) for result in results.values()]
    if not pieces:
        return pd.DataFrame()
    data = pd.concat(pieces, ignore_index=True)
    numeric_cols = [col for col in data.columns if col not in {"plan", "year"}]
    return data.groupby("year", as_index=False)[numeric_cols].mean()


def long_funding_ratios(
    results: Mapping[str, PlanResult],
    graph_years: int | None = None,
) -> pd.DataFrame:
    pieces = []
    for plan, result in results.items():
        ratios = result.funding_ratio()
        n_years = ratios.shape[0] if graph_years is None else min(graph_years, ratios.shape[0])
        data = ratios.iloc[:n_years].copy()
        data["year"] = result.years(n_years)
        long = data.melt(id_vars="year", var_name="simulation", value_name="funding_ratio")
        long["plan"] = plan
        pieces.append(long)
    if not pieces:
        return pd.DataFrame(columns=["plan", "year", "simulation", "funding_ratio"])
    return pd.concat(pieces, ignore_index=True)


def terminal_risk_table(
    results: Mapping[str, PlanResult],
    year_offset: int = 14,
    thresholds: Sequence[float] = (0.4, 0.6, 0.8, 1.0),
) -> pd.DataFrame:
    rows = []
    for plan, result in results.items():
        ratios = result.funding_ratio()
        idx = min(year_offset, ratios.shape[0] - 1)
        values = ratios.iloc[idx].to_numpy(dtype=float)
        row = {
            "plan": plan,
            "year": int(result.years()[idx]),
            "mean": np.nanmean(values),
            "median": np.nanmedian(values),
            "q05": np.nanquantile(values, 0.05),
            "q20": np.nanquantile(values, 0.20),
            "q80": np.nanquantile(values, 0.80),
            "q95": np.nanquantile(values, 0.95),
            "prob_depleted": np.nanmean(values <= 0),
        }
        for threshold in thresholds:
            row[f"prob_below_{threshold:g}"] = np.nanmean(values < threshold)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("median")


def threshold_risk_over_time(
    results: Mapping[str, PlanResult],
    thresholds: Sequence[float] = (0.4, 0.6, 0.8, 1.0),
    graph_years: int | None = 15,
) -> pd.DataFrame:
    rows = []
    for plan, result in results.items():
        ratios = result.funding_ratio()
        n_years = ratios.shape[0] if graph_years is None else min(graph_years, ratios.shape[0])
        arr = ratios.iloc[:n_years].to_numpy(dtype=float)
        for i, year in enumerate(result.years(n_years)):
            for threshold in thresholds:
                rows.append(
                    {
                        "plan": plan,
                        "year": int(year),
                        "threshold": threshold,
                        "probability": np.nanmean(arr[i, :] < threshold),
                    }
                )
    return pd.DataFrame(rows)


def mean_matrix_summary(
    results: Mapping[str, PlanResult],
    matrix_name: str,
    graph_years: int | None = 15,
) -> pd.DataFrame:
    rows = []
    for plan, result in results.items():
        matrix = result.matrix(matrix_name)
        n_years = matrix.shape[0] if graph_years is None else min(graph_years, matrix.shape[0])
        arr = matrix.iloc[:n_years].to_numpy(dtype=float)
        rows.append(
            pd.DataFrame(
                {
                    "plan": plan,
                    "year": result.years(n_years),
                    "mean": np.nanmean(arr, axis=1),
                    "q05": np.nanquantile(arr, 0.05, axis=1),
                    "q50": np.nanquantile(arr, 0.50, axis=1),
                    "q95": np.nanquantile(arr, 0.95, axis=1),
                }
            )
        )
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _figure_ax(ax=None, figsize=(10, 6)):
    if ax is not None:
        return ax.figure, ax
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def plot_plan_forecast(
    result: PlanResult,
    ppd: pd.DataFrame | None = None,
    graph_years: int = 15,
    ax=None,
):
    fig, ax = _figure_ax(ax)
    summary = forecast_summary(result, graph_years)

    if ppd is not None:
        actual = actual_funding_ratio(ppd, result.ppid)
        if not actual.empty:
            ax.plot(actual["fy"], actual["funding_ratio"], color="black", label="Actual")

    x = summary["year"].to_numpy()
    ax.fill_between(x, summary["q05"], summary["q95"], alpha=0.12, label="5-95 pct")
    ax.fill_between(x, summary["q20"], summary["q80"], alpha=0.22, label="20-80 pct")
    ax.plot(x, summary["mean"], color="tab:blue", label="Forecast mean")
    ax.axhline(1.0, color="0.4", linewidth=1, linestyle="--")
    ax.set_title(f"Funding ratio forecast: {result.plan}")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Funding ratio")
    ax.legend()
    return fig, ax


def plot_average_forecast(
    results: Mapping[str, PlanResult],
    ppd: pd.DataFrame | None = None,
    graph_years: int = 15,
    ax=None,
):
    fig, ax = _figure_ax(ax)
    summary = average_forecast_summary(results, graph_years)

    if ppd is not None:
        actual = actual_funding_by_plan(results, ppd)
        if not actual.empty:
            actual_avg = actual.groupby("fy", as_index=False)["funding_ratio"].mean()
            ax.plot(actual_avg["fy"], actual_avg["funding_ratio"], color="black", label="Actual avg")

    x = summary["year"].to_numpy()
    ax.fill_between(x, summary["q05"], summary["q95"], alpha=0.12, label="5-95 pct")
    ax.fill_between(x, summary["q20"], summary["q80"], alpha=0.22, label="20-80 pct")
    ax.plot(x, summary["mean"], color="tab:blue", label="Forecast avg")
    ax.axhline(1.0, color="0.4", linewidth=1, linestyle="--")
    ax.set_title(f"Average funding ratio forecast ({len(results)} plans)")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Funding ratio")
    ax.legend()
    return fig, ax


def plot_terminal_distribution(
    results: Mapping[str, PlanResult],
    year_offset: int = 14,
    ax=None,
):
    fig, ax = _figure_ax(ax)
    values = []
    terminal_years = []
    for result in results.values():
        ratios = result.funding_ratio()
        idx = min(year_offset, ratios.shape[0] - 1)
        values.append(ratios.iloc[idx].to_numpy(dtype=float))
        terminal_years.append(int(result.years()[idx]))
    pooled = np.concatenate(values) if values else np.array([])
    pooled = pooled[np.isfinite(pooled)]
    ax.hist(pooled, bins=150, density=True, alpha=0.45, color="tab:blue")
    # if len(pooled) > 1:
    #     sns.kdeplot(pooled, ax=ax, color="tab:blue", linewidth=2)
    ax.axvline(1.0, color="0.4", linewidth=1, linestyle="--")
    year_label = max(set(terminal_years), key=terminal_years.count) if terminal_years else ""
    ax.set_title(f"Terminal funding ratio distribution ({year_label})")
    ax.set_xlabel("Funding ratio")
    ax.set_ylabel("Density")
    return fig, ax


def plot_threshold_risk(
    results: Mapping[str, PlanResult],
    thresholds: Sequence[float] = (0.4, 0.6, 0.8, 1.0),
    graph_years: int = 15,
    ax=None,
):
    fig, ax = _figure_ax(ax)
    risk = threshold_risk_over_time(results, thresholds, graph_years)
    avg = risk.groupby(["year", "threshold"], as_index=False)["probability"].mean()
    for threshold, data in avg.groupby("threshold"):
        ax.plot(data["year"], data["probability"], marker="o", label=f"< {threshold:g}")
    ax.set_title("Average probability below funding-ratio thresholds")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Probability")
    ax.set_ylim(0, 1)
    ax.legend(title="Threshold")
    return fig, ax


def plot_plan_heatmap(
    results: Mapping[str, PlanResult],
    graph_years: int = 15,
    statistic: str = "q50",
    ax=None,
):
    fig, ax = _figure_ax(ax, figsize=(12, max(6, len(results) * 0.28)))
    rows = []
    for result in results.values():
        summary = forecast_summary(result, graph_years)
        rows.append(summary.set_index("year")[statistic].rename(result.plan))
    heatmap_data = pd.concat(rows, axis=1).T.sort_index()
    sns.heatmap(
        heatmap_data,
        ax=ax,
        cmap="RdYlGn",
        center=1.0,
        cbar_kws={"label": f"Funding ratio ({statistic})"},
    )
    ax.set_title(f"Plan funding-ratio dynamics ({statistic})")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Plan")
    return fig, ax


def plot_metric_dynamics(
    results: Mapping[str, PlanResult],
    matrix_name: str,
    plans: Sequence[str] | None = None,
    graph_years: int = 15,
    ax=None,
):
    fig, ax = _figure_ax(ax)
    selected = results if plans is None else {plan: results[plan] for plan in plans if plan in results}
    data = mean_matrix_summary(selected, matrix_name, graph_years)
    for plan, plan_data in data.groupby("plan"):
        ax.plot(plan_data["year"], plan_data["mean"], label=plan)
    ax.set_title(f"Mean {matrix_name} dynamics")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel(matrix_name)
    ax.legend()
    return fig, ax


def plot_cashflow_dynamics(
    result: PlanResult,
    graph_years: int = 15,
    ax=None,
):
    fig, ax = _figure_ax(ax)
    n_years = min(graph_years, result.n_years)
    years = result.years(n_years)
    for matrix_name, label in [("cash_inflows", "Cash inflows"), ("cash_outflows", "Cash outflows")]:
        if matrix_name in result.matrices:
            arr = result.matrix(matrix_name).iloc[:n_years].to_numpy(dtype=float)
            ax.plot(years, np.nanmean(arr, axis=1), marker="o", label=label)
    ax.set_title(f"Cash-flow dynamics: {result.plan}")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Dollars")
    ax.legend()
    return fig, ax
