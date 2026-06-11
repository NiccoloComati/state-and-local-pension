"""
Python second-stage two-asset asset simulation with common market shocks.

Loads deterministic A/L outputs written by Main_PensionModel.py, expands
deterministic matrices to ``num_sim`` columns, runs the two-asset
nominal-return loop, and writes Python-native pickle plus parquet outputs.

Market shock structure (2026-06-10 methodology change):
    All plans share ONE standardized market shock matrix Z of shape
    (Nyear-1, num_sim), generated from a single market seed. Plan p's stock
    return in year t, simulation n is

        r_stock[t, n] = (0.075 + Inflation_p) + 0.20 * Z[t, n]

    so per-plan marginal return distributions are unchanged, but simulation
    column n is the SAME market history for every plan. This makes aggregate
    (cross-plan) distributional statistics meaningful: without common shocks,
    independent per-plan draws cancel in aggregation and understate aggregate
    tail risk by roughly sqrt(n_plans).

    This intentionally differs from the R script, which draws an independent
    return stream per plan. Per-plan results are statistically equivalent;
    only cross-plan correlation differs.

Scenario levers (2026-06-10; all default to baseline behavior):
    --detal-run-tag   read detAL inputs from a different (baseline) run folder
                      while writing asset outputs under --run-tag
    --contrib-add     permanent contribution increase in percentage points of
                      payroll (payroll reconstructed as cash_inflows / total
                      contribution rate saved in the detAL pkl)
    --policy-start    first projection year the increase applies (0 = now)
    --contrib-always  pay the add-on even when funded ratio > 1 (the base rule
                      contributes zero when overfunded)
    --equity-share    override every plan's risky-asset share with [w, 1-w]
    --derisk-to/--derisk-years  linear glidepath of the risky share
    --stock-premium/--stock-vol  return-assumption sensitivities
    Scenario settings are stored in the output payload under "scenario".
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import shutil
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RUN_TAG = "062026"
PY_MANIFEST = "_manifest.csv"


def project_root() -> Path:
    script_dir = Path(__file__).resolve().parent   # Code/python/
    return script_dir.parent.parent                # project root


# Amortize payments or constant percent of wages
AMORTIZE = False

# Period over which to amortize. The name keeps the active R typo.
AMOTorize_PERIOD = 30

NASSET = 2

# Number of asset simulations to run
NUM_SIM = 1000

REQUIRED_OBJECTS = [
    "Assets",
    "AAL",
    "cash_inflows",
    "cash_outflows",
    "Inflation",
    "rf",
    "planinfo",
    "Nyear",
]
if AMORTIZE:
    REQUIRED_OBJECTS.extend(["NormalCost", "discountrate"])


def parse_plans(value: str | None) -> list[str] | None:
    if value is None or value.strip().lower() == "all":
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def detal_suffix(run_tag: str) -> str:
    return f"_detAL_{run_tag}.pkl"


def asset_suffix(run_tag: str) -> str:
    return f"_AssetSim_2asset_{run_tag}.pkl"


def parquet_suffix(run_tag: str) -> str:
    return f"_AssetSim_2asset_{run_tag}_parquet"


def discover_plans(
    run_dir: Path,
    selected: list[str] | None,
    input_suffix: str,
) -> list[str]:
    if selected is not None:
        return sorted(selected)

    plan_dirs = [
        path.name for path in run_dir.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    ] if run_dir.exists() else []
    input_plans = [
        path.parent.name for path in run_dir.glob(f"*/*{input_suffix}")
    ] if run_dir.exists() else []
    plans = sorted(set(plan_dirs + input_plans))
    if not plans:
        raise FileNotFoundError(
            f"No run plan folders or deterministic A/L input files found under: {run_dir}"
        )
    return plans


def get_asset_share_2asset(planinfo: pd.DataFrame) -> np.ndarray:
    risky_asset_cols = [
        "COMDTotal_Actl",
        "OtherTotal_Actl",
        "PETotal_Actl",
        "EQTotal_Actl",
        "AltMiscTotal_Actl",
        "HFTotal_Actl",
        "RETotal_Actl",
    ]

    missing_cols = [col for col in risky_asset_cols if col not in planinfo.columns]
    if missing_cols:
        raise ValueError(
            "planinfo is missing asset allocation columns: "
            + ", ".join(missing_cols)
        )

    asset_share_stocks = (
        pd.to_numeric(planinfo.loc[planinfo.index[0], risky_asset_cols],
                      errors="coerce")
        .fillna(0.0)
        .sum()
    )
    return np.array([float(asset_share_stocks), 1.0 - float(asset_share_stocks)])


def r_matrix_recycle(value: object, nrow: int, ncol: int) -> np.ndarray:
    """R-like ``matrix(value, nrow=nrow, ncol=ncol)`` recycling, by column."""
    arr = np.asarray(value, dtype=float)
    flat = arr.reshape(-1, order="F")
    total = nrow * ncol
    if flat.size == 0:
        flat = np.zeros(1)
    recycled = np.resize(flat, total)
    return recycled.reshape((nrow, ncol), order="F")


def output_matches_num_sim(output_file: Path, expected_num_sim: int) -> bool:
    if not output_file.exists():
        return False
    with output_file.open("rb") as handle:
        output = pickle.load(handle)
    assets = output.get("Assets")
    actual_num_sim = output.get("num_sim")
    return (
        assets is not None
        and int(actual_num_sim) == int(expected_num_sim)
        and np.asarray(assets).shape[1] == expected_num_sim
    )


def invalid_detal_reason(run_env: dict[str, object]) -> str | None:
    nyear = int(run_env["Nyear"])
    loop_rows = slice(0, nyear - 1)

    checks = {
        "AAL": np.asarray(run_env["AAL"], dtype=float)[loop_rows, :],
        "Assets": np.asarray(run_env["Assets"], dtype=float)[loop_rows, :],
        "cash_inflows": np.asarray(run_env["cash_inflows"], dtype=float)[loop_rows, :],
        "cash_outflows": np.asarray(run_env["cash_outflows"], dtype=float)[loop_rows, :],
    }

    problems: list[str] = []
    if np.any(np.isnan(checks["AAL"]) | (checks["AAL"] <= 0)):
        problems.append("AAL has NA or non-positive values in asset-loop rows")
    if np.any(np.isnan(checks["Assets"])):
        problems.append("Assets has NA values in asset-loop rows")
    if np.any(np.isnan(checks["cash_inflows"])):
        problems.append("cash_inflows has NA values in asset-loop rows")
    if np.any(np.isnan(checks["cash_outflows"])):
        problems.append("cash_outflows has NA values in asset-loop rows")

    return "; ".join(problems) if problems else None


def scalar(value: object) -> float:
    arr = np.asarray(value)
    return float(arr.reshape(-1)[0])


def write_parquet_bundle(output_dir: Path, payload: dict[str, object]) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    matrix_names = ["Assets", "AAL", "cash_inflows", "cash_outflows", "NormalCost"]
    for name in matrix_names:
        if name in payload:
            pd.DataFrame(np.asarray(payload[name])).to_parquet(output_dir / f"{name}.parquet")

    scalar_rows = []
    for key, value in payload.items():
        if key in matrix_names or key in {"planinfo", "AssetShare"}:
            continue
        if isinstance(value, (str, int, float, bool, np.integer, np.floating)):
            scalar_rows.append({"name": key, "value": str(value)})
    pd.DataFrame(scalar_rows).to_parquet(output_dir / "scalars.parquet", index=False)

    if "planinfo" in payload and isinstance(payload["planinfo"], pd.DataFrame):
        payload["planinfo"].to_parquet(output_dir / "planinfo.parquet", index=False)

    if "AssetShare" in payload:
        pd.DataFrame({"value": np.asarray(payload["AssetShare"], dtype=float)}).to_parquet(
            output_dir / "AssetShare.parquet", index=False
        )


DEFAULT_SCENARIO = {
    "contrib_add": 0.0,      # percentage points of payroll
    "policy_start": 0,       # first projection year the add-on applies
    "contrib_always": False, # pay add-on even when funded ratio > 1
    "equity_share": None,    # override risky-asset share [w, 1-w]
    "derisk_to": None,       # glidepath target risky share
    "derisk_years": None,    # glidepath length in years
    "stock_premium": 0.075,  # stock expected return = premium + Inflation
    "stock_vol": 0.20,
    "detal_run_tag": None,   # set by main(); provenance only
}


def run_asset_simulation(
    plan: str,
    input_file: Path,
    output_file: Path,
    parquet_dir: Path,
    num_sim: int,
    amortize: bool,
    seed: int | None,
    overwrite: bool,
    run_tag: str,
    scenario: dict[str, object] | None = None,
) -> dict[str, object]:
    sp = dict(DEFAULT_SCENARIO)
    if scenario:
        sp.update(scenario)
    if output_file.exists() and not overwrite and output_matches_num_sim(output_file, num_sim):
        return {
            "plan": plan,
            "detal_status": "found",
            "asset_status": "existing",
            "skip_reason": "",
            "detAL_file": str(input_file),
            "asset_file": str(output_file),
        }

    if not input_file.exists():
        return {
            "plan": plan,
            "detal_status": "missing",
            "asset_status": "skipped",
            "skip_reason": "deterministic A/L input not found",
            "detAL_file": str(input_file),
            "asset_file": str(output_file),
        }

    try:
        with input_file.open("rb") as handle:
            run_env = pickle.load(handle)
    except Exception as exc:
        return {
            "plan": plan,
            "detal_status": "invalid",
            "asset_status": "skipped",
            "skip_reason": f"could not load deterministic pickle: {exc}",
            "detAL_file": str(input_file),
            "asset_file": str(output_file),
        }

    missing_objects = [name for name in REQUIRED_OBJECTS if name not in run_env]
    if missing_objects:
        return {
            "plan": plan,
            "detal_status": "invalid",
            "asset_status": "skipped",
            "skip_reason": "missing objects: " + ", ".join(missing_objects),
            "detAL_file": str(input_file),
            "asset_file": str(output_file),
        }

    invalid_reason = invalid_detal_reason(run_env)
    if invalid_reason is not None:
        return {
            "plan": plan,
            "detal_status": "invalid",
            "asset_status": "skipped",
            "skip_reason": invalid_reason,
            "detAL_file": str(input_file),
            "asset_file": str(output_file),
        }

    nyear = int(run_env["Nyear"])
    assets = r_matrix_recycle(run_env["Assets"], np.asarray(run_env["Assets"]).shape[0], num_sim)
    aal = r_matrix_recycle(run_env["AAL"], np.asarray(run_env["AAL"]).shape[0], num_sim)
    cash_inflows = r_matrix_recycle(
        run_env["cash_inflows"], np.asarray(run_env["cash_inflows"]).shape[0], num_sim
    )
    cash_outflows = r_matrix_recycle(
        run_env["cash_outflows"], np.asarray(run_env["cash_outflows"]).shape[0], num_sim
    )
    normal_cost = (
        r_matrix_recycle(
            run_env["NormalCost"], np.asarray(run_env["NormalCost"]).shape[0], num_sim
        )
        if "NormalCost" in run_env else None
    )

    # (STATIC) Nominal expected returns for stocks, bonds
    exp_ret = np.array([float(sp["stock_premium"]) + scalar(run_env["Inflation"]), scalar(run_env["rf"])])

    # (STATIC) Standard deviations (volatility) for stocks, bonds
    sd = np.array([float(sp["stock_vol"]), 0.0])

    asset_share = np.asarray(
        run_env.get("AssetShare", get_asset_share_2asset(run_env["planinfo"])),
        dtype=float,
    )
    if len(asset_share) < NASSET:
        raise ValueError(f"{plan} has fewer than {NASSET} AssetShare entries.")

    # Risky-share path: plan allocation by default; flat override via
    # equity_share; linear glidepath to derisk_to over derisk_years.
    base_share = float(asset_share[0]) if sp["equity_share"] is None else float(sp["equity_share"])
    if sp["derisk_to"] is None:
        w_path = np.full(nyear - 1, base_share)
    else:
        k = int(sp["derisk_years"]) if sp["derisk_years"] else (nyear - 1)
        steps = np.arange(nyear - 1, dtype=float)
        w_path = base_share + (float(sp["derisk_to"]) - base_share) * np.minimum(steps / k, 1.0)

    # Contribution add-on: contrib_add percentage points of payroll, where
    # payroll[t] = cash_inflows[t] / (EE + ER contribution rate). The rates
    # are saved in detAL pkls (fast runner, 2026-06-10); older pkls without
    # them cannot run contribution scenarios.
    contrib_add = float(sp["contrib_add"])
    add_on_full = None
    if contrib_add:
        rate_parts = [run_env.get("EmployeeContributionRate"), run_env.get("EmployerContributionRate")]
        if any(part is None for part in rate_parts):
            return {
                "plan": plan,
                "detal_status": "invalid",
                "asset_status": "skipped",
                "skip_reason": "contrib-add requires EmployeeContributionRate/EmployerContributionRate "
                               "in the detAL pkl; rerun the detal stage with the current fast runner",
                "detAL_file": str(input_file),
                "asset_file": str(output_file),
            }
        rate_total = sum(float(np.asarray(part).reshape(-1)[0]) for part in rate_parts)
        if not math.isfinite(rate_total) or rate_total <= 0:
            return {
                "plan": plan,
                "detal_status": "invalid",
                "asset_status": "skipped",
                "skip_reason": f"non-positive total contribution rate ({rate_total}); cannot apply contrib-add",
                "detAL_file": str(input_file),
                "asset_file": str(output_file),
            }
        add_on_full = (contrib_add / 100.0) * cash_inflows / rate_total

    # Common standardized market shocks: the SAME matrix for every plan in a
    # run (same seed, same shape), so simulation column n is one shared market
    # history. Plan-specific expected returns are applied on top of Z.
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((nyear - 1, num_sim))

    stock_returns = exp_ret[0] + sd[0] * z              # (nyear-1, num_sim)
    bond_return = exp_ret[1]                            # deterministic (sd=0)
    annual_ret = w_path[:, None] * stock_returns + (1.0 - w_path)[:, None] * bond_return

    policy_start = int(sp["policy_start"])

    # Monte Carlo loop: vectorized across simulations, sequential in years
    for t in range(nyear - 1):
        funding_ratio = assets[t, :] / aal[t, :]
        if amortize:
            uaal = aal[t, :] - assets[t, :]
            discountrate = scalar(run_env["discountrate"])
            amort_payment = normal_cost[t, 0] + np.maximum(
                0.0,
                uaal * (
                    discountrate * (1 + discountrate) ** AMOTorize_PERIOD
                ) / (((1 + discountrate) ** AMOTorize_PERIOD) - 1),
            )
            contribution = np.where(funding_ratio > 1, 0.0, amort_payment)
        else:
            contribution = np.where(funding_ratio > 1, 0.0, cash_inflows[t, :])

        if add_on_full is not None and t >= policy_start:
            if sp["contrib_always"]:
                contribution = contribution + add_on_full[t, :]
            else:
                contribution = contribution + np.where(funding_ratio > 1, 0.0, add_on_full[t, :])

        assets[t + 1, :] = np.maximum(
            assets[t, :] * (1 + annual_ret[t, :])
            - cash_outflows[t, :]
            + contribution,
            0.0,
        )

    payload = dict(run_env)
    payload.update({
        "Assets": assets,
        "AAL": aal,
        "cash_inflows": cash_inflows,
        "cash_outflows": cash_outflows,
        "AssetShare": asset_share,
        "Amortize": amortize,
        "Amotorize_Period": AMOTorize_PERIOD,
        "Nasset": NASSET,
        "num_sim": num_sim,
        "asset_run_tag": run_tag,
        "market_seed": int(seed),
        "common_market_shocks": True,
        "scenario": sp,
        "scenario_json": json.dumps(sp),
    })
    if normal_cost is not None:
        payload["NormalCost"] = normal_cost

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("wb") as handle:
        pickle.dump(payload, handle)
    try:
        write_parquet_bundle(parquet_dir, payload)
    except OSError as exc:
        print(f"  [warn] parquet bundle skipped: {exc}")

    return {
        "plan": plan,
        "detal_status": "valid",
        "asset_status": "saved",
        "skip_reason": "",
        "detAL_file": str(input_file),
        "asset_file": str(output_file),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", default="all", help="Comma-separated plans or all")
    parser.add_argument("--num-sim", type=int, default=NUM_SIM)
    parser.add_argument("--run-tag", default=DEFAULT_RUN_TAG)
    parser.add_argument("--seed", type=int, default=None,
                        help="Market shock seed, shared by ALL plans (common shocks). "
                             "If omitted, one seed is generated and printed.")
    parser.add_argument("--overwrite", action="store_true")
    # Scenario levers (defaults = baseline behavior)
    parser.add_argument("--detal-run-tag", default=None,
                        help="Run tag to READ detAL inputs from (default: --run-tag). "
                             "Lets scenario runs reuse baseline deterministic outputs.")
    parser.add_argument("--contrib-add", type=float, default=0.0,
                        help="Permanent contribution increase, percentage points of payroll.")
    parser.add_argument("--policy-start", type=int, default=0,
                        help="First projection year the contribution add-on applies (0 = immediately).")
    parser.add_argument("--contrib-always", action="store_true",
                        help="Pay the add-on even when funded ratio > 1.")
    parser.add_argument("--equity-share", type=float, default=None,
                        help="Override every plan's risky-asset share with [w, 1-w].")
    parser.add_argument("--derisk-to", type=float, default=None,
                        help="Glidepath target risky share (linear from starting share).")
    parser.add_argument("--derisk-years", type=int, default=None,
                        help="Glidepath length in years (default: full horizon).")
    parser.add_argument("--stock-premium", type=float, default=0.075,
                        help="Stock expected return premium over plan inflation (default 0.075).")
    parser.add_argument("--stock-vol", type=float, default=0.20,
                        help="Stock return volatility (default 0.20).")
    args = parser.parse_args()

    market_seed = args.seed
    if market_seed is None:
        market_seed = int(np.random.SeedSequence().entropy % (2**31))
    print(f"Common market shock seed: {market_seed} "
          "(simulation column n is the same market history for every plan)")

    root_dir = project_root()
    detal_tag = args.detal_run_tag or args.run_tag
    detal_dir = root_dir / "Results" / "Runs" / detal_tag      # inputs
    run_dir = root_dir / "Results" / "Runs" / args.run_tag     # outputs
    log_dir = run_dir / "_logs"
    input_suffix = detal_suffix(detal_tag)
    output_suffix = asset_suffix(args.run_tag)
    parquet_dir_suffix = parquet_suffix(args.run_tag)

    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    scenario = {
        "contrib_add": args.contrib_add,
        "policy_start": args.policy_start,
        "contrib_always": args.contrib_always,
        "equity_share": args.equity_share,
        "derisk_to": args.derisk_to,
        "derisk_years": args.derisk_years,
        "stock_premium": args.stock_premium,
        "stock_vol": args.stock_vol,
        "detal_run_tag": detal_tag,
    }
    active_levers = {k: v for k, v in scenario.items()
                     if k != "detal_run_tag" and v not in (DEFAULT_SCENARIO.get(k), None, False)}
    if detal_tag != args.run_tag:
        print(f"Reading detAL inputs from run '{detal_tag}'; writing asset outputs to run '{args.run_tag}'")
    if active_levers:
        print(f"Scenario levers active: {active_levers}")

    def _fmt(s: float) -> str:
        return f"{int(s // 60)}m {s % 60:.1f}s" if s >= 60 else f"{s:.1f}s"

    plans = discover_plans(detal_dir, parse_plans(args.plans), input_suffix)
    manifest_rows: list[dict[str, object]] = []
    _t0 = time.perf_counter()

    for i_loop, plan in enumerate(plans, start=1):
        plan_run_dir = run_dir / plan
        input_file = detal_dir / plan / f"{plan}{input_suffix}"
        output_file = plan_run_dir / f"{plan}{output_suffix}"
        parquet_dir = plan_run_dir / f"{plan}{parquet_dir_suffix}"

        print(f"[{i_loop}/{len(plans)}] {plan}: asset simulation ...")
        _tp = time.perf_counter()
        row = run_asset_simulation(
            plan=plan,
            input_file=input_file,
            output_file=output_file,
            parquet_dir=parquet_dir,
            num_sim=args.num_sim,
            amortize=AMORTIZE,
            seed=market_seed,
            overwrite=args.overwrite,
            run_tag=args.run_tag,
            scenario=scenario,
        )
        _plan_time = time.perf_counter() - _tp
        row.update({
            "run_tag": args.run_tag,
            "detal_run_tag": detal_tag,
            "num_sim": args.num_sim,
            "scenario": json.dumps(active_levers) if active_levers else "",
            "parquet_dir": str(parquet_dir),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_s": round(_plan_time, 2),
        })
        manifest_rows.append(row)
        print(f"[{i_loop}/{len(plans)}] {plan}: {row['asset_status']}  ({_fmt(_plan_time)})")

    pd.DataFrame(manifest_rows).to_csv(run_dir / PY_MANIFEST, index=False)
    print(f"Total time: {_fmt(time.perf_counter() - _t0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
