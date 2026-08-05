"""Scenario definition and launch layer over the simulation pipeline.

Used by scenario_launcher.ipynb. A Scenario is a declarative parameter set; this module
turns it into the exact run_simulation.py / asset_simulation.py commands,
launches them, and reports status. It does not implement model equations.

Conventions:
  - Every scenario reuses the baseline market seed by default, so simulation
    column n is the same market history in every scenario and runs can be
    compared path-by-path.
  - Asset-only scenarios read detAL inputs from the baseline run
    (detal_run_tag) and write outputs under their own run_tag.
  - Scenario provenance is stored in each output pkl ("scenario") and in the
    run folder's _manifest.csv.
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, fields
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent                  # Code/python/
ROOT = SCRIPT_DIR.parent.parent                               # project root
RUNS = ROOT / "Results" / "Runs"
# The baseline scenarios derive their deterministic inputs from. Was pinned to
# 062026, which silently went two generations stale. Set this deliberately when
# running scenarios; None means "use the newest run".
BASELINE_RUN_TAG = None
BASELINE_SEED = 123
PYTHON = sys.executable

RUN_SIMULATION = SCRIPT_DIR / "run_simulation.py"
ASSET_SIMULATION = SCRIPT_DIR / "asset_simulation.py"


def _default_parallel() -> int:
    """How many plan processes to run at once, derived from THIS machine.

    Governs both stages: the detal ceiling passed to run_simulation.py, and the
    asset-stage pool in launch().

    It used to be hardcoded at 19, with a comment describing it as the detal
    ceiling. That number came from the 37-plan desktop era, and on 2026-08-04 it
    launched 19 concurrent asset processes on a 12-thread laptop with about 3 GB
    of memory free. A constant tuned for one machine does not belong in shared
    code, so it is now half the logical cores: 6 on that laptop, which is the
    figure the baseline runs were measured at, and proportionally more on a
    bigger machine. Override per scenario with `parallel=N` when you know better.
    """
    return max(1, (os.cpu_count() or 4) // 2)


@dataclass
class Scenario:
    """One simulation scenario. Defaults reproduce the baseline run."""
    name: str                              # human label
    run_tag: str                           # output folder under Results/Runs/
    stage: str = "asset"                   # "asset" | "detal" | "both"
    plans: str = "all"
    num_sim: int = 10000
    seed: int = BASELINE_SEED              # common market shock seed
    detal_run_tag: str = BASELINE_RUN_TAG  # where the asset stage reads detAL inputs
    # --- contribution policy (asset stage) ---
    contrib_add: float = 0.0               # permanent increase, pp of payroll
    policy_start: int = 0                  # first projection year it applies
    contrib_always: bool = False           # pay add-on even when FR > 1
    # --- investment strategy (asset stage) ---
    equity_share: float | None = None      # flat override of risky share
    derisk_to: float | None = None         # glidepath target risky share
    derisk_years: int | None = None        # glidepath length
    # --- return assumptions (asset stage) ---
    stock_premium: float | None = None     # None -> script default 0.075
    stock_vol: float | None = None         # None -> script default 0.20
    # --- liability stage (detal/both only) ---
    discount_override: float | None = None # e.g. AAA yield
    tier_file: str | None = None           # e.g. no-reform counterfactual workbook
    plan_year: int = 2022
    # --- execution ---
    parallel: int = field(default_factory=lambda: _default_parallel())
    workers: int = 1                       # PVNC threads per detal process
    overwrite: bool = True
    notes: str = ""

    def asset_levers(self) -> dict:
        levers = {}
        if self.contrib_add:
            levers["contrib_add"] = self.contrib_add
            levers["policy_start"] = self.policy_start
            levers["contrib_always"] = self.contrib_always
        if self.equity_share is not None:
            levers["equity_share"] = self.equity_share
        if self.derisk_to is not None:
            levers["derisk_to"] = self.derisk_to
            levers["derisk_years"] = self.derisk_years
        if self.stock_premium is not None:
            levers["stock_premium"] = self.stock_premium
        if self.stock_vol is not None:
            levers["stock_vol"] = self.stock_vol
        return levers


def _fmt_num(x: float) -> str:
    return f"{x:g}".replace(".", "p").replace("-", "m")


def contribution_grid(
    deltas=(0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
    starts=(0, 5, 10, 15),
    contrib_always: bool = True,
    tag_prefix: str = "scn_c",
    **kwargs,
) -> list[Scenario]:
    """Contribution-policy grid: permanent +delta pp of payroll from year start."""
    out = []
    for delta in deltas:
        for start in starts:
            tag = f"{tag_prefix}{_fmt_num(delta)}s{start}"
            out.append(Scenario(
                name=f"contrib +{delta}pp from year {start}",
                run_tag=tag,
                contrib_add=delta,
                policy_start=start,
                contrib_always=contrib_always,
                **kwargs,
            ))
    return out


def equity_grid(shares=(0.5, 0.3, 0.0), tag_prefix: str = "scn_eq", **kwargs) -> list[Scenario]:
    """Flat risky-share overrides."""
    return [
        Scenario(name=f"equity share {share:.0%}",
                 run_tag=f"{tag_prefix}{_fmt_num(share)}",
                 equity_share=share, **kwargs)
        for share in shares
    ]


def build_commands(s: Scenario) -> list[tuple[str, list[str]]]:
    """Return the exact (label, command) pairs a scenario will execute."""
    commands: list[tuple[str, list[str]]] = []

    if s.stage in {"detal", "both"}:
        cmd = [PYTHON, str(RUN_SIMULATION),
               "--plans", s.plans, "--stage", "detal",
               "--parallel", str(s.parallel), "--workers", str(s.workers),
               "--run-tag", s.run_tag, "--plan-year", str(s.plan_year), "--fast"]
        if s.tier_file:
            cmd.extend(["--tier-file", s.tier_file])
        if s.discount_override is not None:
            cmd.extend(["--discount-override", str(s.discount_override)])
        if s.overwrite:
            cmd.append("--overwrite")
        commands.append((f"{s.run_tag}:detal", cmd))

    if s.stage in {"asset", "both"}:
        # "both" runs detal under the scenario tag, so assets read from there
        detal_tag = s.run_tag if s.stage == "both" else s.detal_run_tag
        cmd = [PYTHON, str(ASSET_SIMULATION),
               "--plans", s.plans, "--num-sim", str(s.num_sim),
               "--run-tag", s.run_tag, "--seed", str(s.seed),
               "--detal-run-tag", detal_tag]
        levers = s.asset_levers()
        if "contrib_add" in levers:
            cmd.extend(["--contrib-add", str(levers["contrib_add"]),
                        "--policy-start", str(levers["policy_start"])])
            if levers["contrib_always"]:
                cmd.append("--contrib-always")
        if "equity_share" in levers:
            cmd.extend(["--equity-share", str(levers["equity_share"])])
        if "derisk_to" in levers:
            cmd.extend(["--derisk-to", str(levers["derisk_to"])])
            if levers.get("derisk_years"):
                cmd.extend(["--derisk-years", str(levers["derisk_years"])])
        if "stock_premium" in levers:
            cmd.extend(["--stock-premium", str(levers["stock_premium"])])
        if "stock_vol" in levers:
            cmd.extend(["--stock-vol", str(levers["stock_vol"])])
        if s.overwrite:
            cmd.append("--overwrite")
        commands.append((f"{s.run_tag}:asset", cmd))

    return commands


def preview(scenarios: list[Scenario]) -> pd.DataFrame:
    """One row per scenario: active settings plus the exact commands."""
    rows = []
    for s in scenarios:
        active = {f.name: getattr(s, f.name) for f in fields(s)
                  if getattr(s, f.name) != f.default and f.name not in {"name", "run_tag", "notes"}}
        rows.append({
            "name": s.name,
            "run_tag": s.run_tag,
            "stage": s.stage,
            "active_settings": json.dumps(active, default=str),
            "commands": " && ".join(" ".join(cmd) for _, cmd in build_commands(s)),
        })
    return pd.DataFrame(rows)


def _plan_list(plans_arg: str) -> list[str]:
    """Resolve the --plans argument to explicit plan ids."""
    if plans_arg.strip().lower() != "all":
        return [p.strip() for p in plans_arg.split(",") if p.strip()]
    plan_file = SCRIPT_DIR / "settings" / "plans_40.txt"
    return [ln.strip() for ln in plan_file.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def _split_by_plan(cmd: list[str], plans_arg: str) -> list[tuple[str, list[str]]]:
    """Turn one all-plans asset command into one command per plan.

    `asset_simulation.py` contains NO parallelism of its own - no pool, no
    subprocesses - so invoking it once with `--plans all` walks 40 plans
    sequentially at roughly 30 seconds each, about 21 minutes a scenario. The
    baseline path does the same work in about 4 minutes because
    `run_simulation.py` fans the per-plan invocations out across a thread pool.
    This reproduces that here, which was the only reason scenario runs were
    five times slower than they needed to be.

    The market seed is passed unchanged to every plan, which is what preserves
    the common shock matrix - each invocation regenerates the same draws from
    the same seed. That is exactly how `run_simulation.py` does it, so splitting
    by plan cannot desynchronise the shocks.
    """
    out = []
    for plan in _plan_list(plans_arg):
        per = list(cmd)
        per[per.index("--plans") + 1] = plan
        out.append((plan, per))
    return out


def launch(scenarios: list[Scenario], dry_run: bool = True, stop_on_error: bool = True) -> pd.DataFrame:
    """Run scenarios in order. dry_run=True (default) only prints commands.

    Within a scenario the asset stage is fanned out across `Scenario.parallel`
    worker slots; the detal stage already parallelises inside run_simulation.py.
    """
    rows = []
    for s in scenarios:
        for label, cmd in build_commands(s):
            if dry_run:
                print(f"[dry-run] {label}:\n  {' '.join(cmd)}")
                rows.append({"scenario": s.name, "step": label, "status": "dry-run",
                             "elapsed_s": 0.0, "log": ""})
                continue

            log_dir = RUNS / s.run_tag / "_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
            t0 = time.perf_counter()

            # The detal step is already parallel inside run_simulation.py; the
            # asset step is not, so fan it out per plan here.
            if label.endswith(":asset"):
                tasks = _split_by_plan(cmd, s.plans)
                print(f"[start] {label}: {len(tasks)} plan(s), max parallel={s.parallel}")
                failed = []
                with ThreadPoolExecutor(max_workers=max(1, s.parallel)) as pool:
                    futures = {}
                    for plan, per_cmd in tasks:
                        lp = log_dir / f"launcher_asset_{plan}_{stamp}.log"
                        futures[pool.submit(_run_logged, per_cmd, lp)] = (plan, lp)
                    for fut in as_completed(futures):
                        plan, lp = futures[fut]
                        code = fut.result()
                        if code != 0:
                            failed.append(plan)
                            print(f"  [FAILED] asset {plan} (exit {code}) -> {lp.name}")
                elapsed = time.perf_counter() - t0
                status = "ok" if not failed else f"FAILED ({len(failed)} plan(s): {failed[:5]})"
                print(f"[done]  {label}: {status}  ({elapsed:.0f}s)")
                rows.append({"scenario": s.name, "step": label, "status": status,
                             "elapsed_s": round(elapsed, 1), "log": str(log_dir)})
                if failed and stop_on_error:
                    print("[stop]  aborting remaining scenarios (stop_on_error=True)")
                    return pd.DataFrame(rows)
                continue

            log_path = log_dir / f"launcher_{label.replace(':', '_')}_{stamp}.log"
            print(f"[start] {label} -> {log_path.name}")
            code = _run_logged(cmd, log_path)
            elapsed = time.perf_counter() - t0
            status = "ok" if code == 0 else f"FAILED (exit {code})"
            print(f"[done]  {label}: {status}  ({elapsed:.0f}s)")
            rows.append({"scenario": s.name, "step": label, "status": status,
                         "elapsed_s": round(elapsed, 1), "log": str(log_path)})
            if code != 0 and stop_on_error:
                print("[stop]  aborting remaining scenarios (stop_on_error=True)")
                return pd.DataFrame(rows)
    return pd.DataFrame(rows)


def _run_logged(cmd: list[str], log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
    return proc.returncode


def inventory(run_tags: list[str] | None = None) -> pd.DataFrame:
    """Output counts per run folder, with scenario provenance from the manifest."""
    if run_tags is None:
        run_tags = sorted(p.name for p in RUNS.iterdir() if p.is_dir())
    rows = []
    for tag in run_tags:
        run_dir = RUNS / tag
        detal = len(list(run_dir.glob("*/*_detAL_*.pkl")))
        asset = len(list(run_dir.glob("*/*_AssetSim_*.pkl")))
        scenario_desc, num_sim = "", None
        manifest_path = run_dir / "_manifest.csv"
        if manifest_path.exists():
            try:
                manifest = pd.read_csv(manifest_path)
                if "scenario" in manifest.columns:
                    vals = manifest["scenario"].dropna().astype(str)
                    vals = vals[vals != ""]
                    if not vals.empty:
                        scenario_desc = vals.iloc[0]
                if "num_sim" in manifest.columns and not manifest.empty:
                    num_sim = int(manifest["num_sim"].iloc[0])
            except Exception:
                pass
        rows.append({"run_tag": tag, "detal_pkls": detal, "asset_pkls": asset,
                     "num_sim": num_sim, "scenario": scenario_desc})
    return pd.DataFrame(rows)


def _first_exhaustion(assets: np.ndarray) -> np.ndarray:
    zero = assets[1:, :] <= 0
    any_hit = zero.any(axis=0)
    first_hit = zero.argmax(axis=0) + 1.0
    return np.where(any_hit, first_hit, np.nan)


def exhaustion_summary(run_tag: str, horizons=(10, 20, 35)) -> pd.DataFrame:
    """Per-plan exhaustion probabilities for one run, straight from the pkls."""
    rows = []
    for pkl in sorted(RUNS.joinpath(run_tag).glob("*/*_AssetSim_*.pkl")):
        with pkl.open("rb") as fh:
            data = pickle.load(fh)
        offsets = _first_exhaustion(np.asarray(data["Assets"], dtype=float))
        row = {"plan": pkl.parent.name, "run_tag": run_tag}
        for h in horizons:
            row[f"prob_exhaust_{h}"] = float(np.nanmean(offsets <= h))
        rows.append(row)
    return pd.DataFrame(rows)


def compare_exhaustion(run_tags: list[str], horizon: int = 35) -> pd.DataFrame:
    """Plans x run_tags table of P(exhaust by horizon) for quick scenario reads."""
    pieces = []
    for tag in run_tags:
        summary = exhaustion_summary(tag, horizons=(horizon,))
        if summary.empty:
            continue
        pieces.append(summary.set_index("plan")[f"prob_exhaust_{horizon}"].rename(tag))
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, axis=1)
