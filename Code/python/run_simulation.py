"""
Python launcher for the translated deterministic and asset-simulation scripts.

This file only orchestrates existing scripts. It does not implement pension
model logic or change simulation methodology.
"""

from __future__ import annotations

import argparse
import math
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# No default run tag. Defaulting to a real run tag meant a forgotten --run-tag
# silently overwrote it; 062026 sat here for months. If --run-tag is omitted the
# runner now mints the next free YYYYMMDD_N instead (see next_run_tag).
DEFAULT_RUN_TAG = None
DEFAULT_PLAN_YEAR = 2022
DEFAULT_TIER_FILE = "planchanges_main_2022_clean.xlsx"


def project_root() -> Path:
    script_dir = Path(__file__).resolve().parent   # Code/python/
    return script_dir.parent.parent                # project root


ROOT = project_root()
SCRIPT_DIR   = Path(__file__).resolve().parent
DETAL_SCRIPT      = SCRIPT_DIR / "Main_PensionModel_original.py"
DETAL_SCRIPT_FAST = SCRIPT_DIR / "fast" / "Main_PensionModel.py"
# Experimental variant, see Code/python/beta/README.md. Never the default.
DETAL_SCRIPT_BETA = SCRIPT_DIR / "beta" / "Main_PensionModel_payrollbeta.py"
ASSET_SCRIPT = SCRIPT_DIR / "asset_simulation.py"


def read_canonical_plans(plan_file: Path) -> list[str]:
    plans = []
    for line in plan_file.read_text().splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            plans.append(value)
    return plans


def engine_known_plans() -> set[str]:
    """Plan ids the fast engine accepts, read from its AVAILABLE_DATA table.

    Parsed from the source rather than imported, because the runner module executes
    argparse at import time. Returns an empty set if it cannot be read, in which
    case the caller skips the pre-flight check and the engine reports per plan.
    """
    import ast
    try:
        tree = ast.parse((SCRIPT_DIR / "fast" / "Main_PensionModel.py").read_text(encoding="utf-8"))
    except Exception:
        return set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "AVAILABLE_DATA" for t in node.targets
        ):
            if isinstance(node.value, ast.Dict):
                return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    return set()


def next_run_tag(root: "Path", when=None) -> str:
    """Next free run tag in the YYYYMMDD_N convention (adopted 2026-07-30).

    Folder names identify a run; they deliberately do NOT describe it, because a
    descriptive label stops meaning anything after a few weeks. What a run IS
    lives in Results/Runs/README.md.
    """
    from datetime import date as _date
    day = (when or _date.today()).strftime("%Y%m%d")
    runs = Path(root) / "Results" / "Runs"
    n = 1
    while (runs / f"{day}_{n}").exists():
        n += 1
    return f"{day}_{n}"


def default_plan_file(run_tag: str) -> Path:
    # plans_40.txt (2026-07-30) supersedes plans_38.txt: MA51 and MO64 were never
    # in the older list, and MA50 used to be filtered out below. All three now run.
    for name in ("plans_40.txt", "plans_38.txt"):
        candidate = SCRIPT_DIR / "config" / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No plan list found. Pass --plan-file explicitly."
    )


def parse_plans(value: str, plan_file: Path) -> list[str]:
    # The hard-coded `plan != "MA50"` exclusion was removed 2026-07-30. MA50 runs
    # normally now (its liability lands 4.3% from reported); see
    # Documentation/states_track_context.md. To reproduce the earlier 37-plan
    # selection, pass --plan-file config/plans_38.txt and drop MA50 explicitly.
    if value.lower() == "all":
        return read_canonical_plans(plan_file)
    return [part.strip() for part in value.split(",") if part.strip()]



def run_command(name: str, command: list[str], log_path: Path, dry_run: bool) -> tuple[str, int]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    text = " ".join(command)
    if dry_run:
        print(f"[dry-run] {name}: {text}")
        return name, 0

    print(f"[start] {name} -> {log_path}")
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    print(f"[done]  {name}: exit={proc.returncode}")
    return name, proc.returncode


def run_stage(
    plans: list[str],
    stage: str,
    parallel: int,
    num_sim: int,
    seed: int | None,
    run_dir: Path,
    log_dir: Path,
    run_tag: str,
    plan_year: int,
    tier_file: str,
    date_run: str | None,
    overwrite: bool,
    skip_existing_detal: bool,
    skip_existing_asset: bool,
    dry_run: bool,
    fast: bool = False,
    beta_payroll: bool = False,
    workers: int | None = None,
    discount_override: float | None = None,
) -> int:
    failures: list[tuple[str, int]] = []
    # Asset stage: ALL plans must share one market seed so simulation column n
    # is the same market history across plans (common shocks). If no seed was
    # given, generate one here so parallel per-plan subprocesses still agree.
    if stage == "asset" and seed is None:
        seed = random.randrange(2**31)
        print(f"asset: no --seed given; using generated common market seed {seed}")
    print(f"{stage}: {len(plans)} plan(s), max parallel={parallel}")

    # Build the full task list first, skipping plans that already have outputs
    tasks: list[tuple[str, list[str], Path]] = []
    for plan in plans:
        plan_dir = run_dir / plan
        if stage == "detal":
            output_file = plan_dir / f"{plan}_detAL_{run_tag}.pkl"
            if skip_existing_detal and output_file.exists():
                print(f"[skip]  detal {plan}: existing {output_file}")
                continue
            detal_script = (DETAL_SCRIPT_BETA if beta_payroll else
                            DETAL_SCRIPT_FAST if fast else DETAL_SCRIPT)
            command = [
                sys.executable, str(detal_script), plan,
                "--run-tag", run_tag,
                "--plan-year", str(plan_year),
                "--tier-file", tier_file,
            ]
            if date_run is not None:
                command.extend(["--date-run", date_run])
            if fast and workers is not None:
                command.extend(["--workers", str(workers)])
            if fast and discount_override is not None:
                command.extend(["--discount-override", str(discount_override)])
            log_path = log_dir / f"python_detal_{plan}_{run_tag}.log"
            tasks.append((f"detal {plan}", command, log_path))
        else:
            output_file = plan_dir / f"{plan}_AssetSim_2asset_{run_tag}.pkl"
            if skip_existing_asset and output_file.exists() and not overwrite:
                print(f"[skip]  asset {plan}: existing {output_file}")
                continue
            command = [
                sys.executable, str(ASSET_SCRIPT),
                "--plans", plan,
                "--num-sim", str(num_sim),
                "--run-tag", run_tag,
            ]
            if seed is not None:
                command.extend(["--seed", str(seed)])
            if overwrite:
                command.append("--overwrite")
            log_path = log_dir / f"python_asset_{plan}_{run_tag}.log"
            tasks.append((f"asset {plan}", command, log_path))

    # Submit all tasks to a single pool; max_workers acts as the concurrency ceiling
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        future_to_name = {
            pool.submit(run_command, name, cmd, log, dry_run): name
            for name, cmd, log in tasks
        }
        done = 0
        for future in as_completed(future_to_name):
            name, code = future.result()
            done += 1
            status = "done" if code == 0 else f"FAILED (exit {code})"
            print(f"[{done}/{len(tasks)}] {name}: {status}")
            if code != 0:
                failures.append((name, code))

    if failures:
        for name, code in failures:
            print(f"[fail] {name}: exit={code}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", default="all", help="all or comma-separated plan ids")
    parser.add_argument("--stage", choices=["detal", "asset", "both"], default="both")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--num-sim", type=int, default=1000)
    parser.add_argument("--run-tag", default=DEFAULT_RUN_TAG)
    parser.add_argument("--plan-year", type=int, default=DEFAULT_PLAN_YEAR)
    parser.add_argument("--tier-file", default=DEFAULT_TIER_FILE)
    parser.add_argument("--date-run", default=None)
    parser.add_argument("--plan-file", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-existing-detal", action="store_true")
    parser.add_argument("--skip-existing-asset", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--beta-payroll", action="store_true",
                        help="BETA: measure contribution rates against the model's own "
                             "payroll instead of PPD covered payroll. Implies --fast. "
                             "See Code/python/beta/README.md.")
    parser.add_argument("--fast", action="store_true",
                        help="Use optimized Main_PensionModel_fast.py for detal stage")
    parser.add_argument("--workers", type=int, default=None,
                        help="PVNC thread-pool workers (fast mode only)")
    parser.add_argument("--discount-override", type=float, default=None,
                        help="Forwarded to the fast detal runner: replace the plan GASB discount rate")
    args = parser.parse_args()

    if args.parallel < 1:
        raise ValueError("--parallel must be >= 1")

    if args.run_tag is None:
        args.run_tag = next_run_tag(ROOT)
        print(f"no --run-tag given; using {args.run_tag}")
    plan_file = Path(args.plan_file) if args.plan_file else default_plan_file(args.run_tag)
    plans = parse_plans(args.plans, plan_file)
    # A hard MA50 block used to sit here (2026-07-30: removed). It dated from the
    # old R script's idiosyncrasies, most of which turned out not to survive
    # checking; MA50 runs normally through the generic runner now.
    known = engine_known_plans()
    unknown = [p for p in plans if known and p not in known]
    if unknown:
        raise ValueError(
            f"Plans not in the engine's AVAILABLE_DATA table: {', '.join(unknown)}. "
            f"Add a 9-boolean row in Code/python/fast/Main_PensionModel.py first."
        )

    run_dir = ROOT / "Results" / "Runs" / args.run_tag
    if run_dir.exists() and any(run_dir.iterdir()) and not (
            args.overwrite or args.skip_existing_detal or args.skip_existing_asset):
        raise SystemExit(
            f"Run folder {args.run_tag} already exists and is not empty.\n"
            f"Pick a new --run-tag, or pass --overwrite / --skip-existing-detal / "
            f"--skip-existing-asset if you really mean to write into it.")
    log_dir = run_dir / "_logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.stage in {"detal", "both"}:
        code = run_stage(
            plans, "detal", args.parallel, args.num_sim, args.seed,
            run_dir, log_dir, args.run_tag,
            args.plan_year, args.tier_file, args.date_run,
            args.overwrite, args.skip_existing_detal, args.skip_existing_asset,
            args.dry_run, fast=args.fast or args.beta_payroll,
            beta_payroll=args.beta_payroll, workers=args.workers,
            discount_override=args.discount_override,
        )
        if code != 0:
            return code

    if args.stage in {"asset", "both"}:
        code = run_stage(
            plans, "asset", args.parallel, args.num_sim, args.seed,
            run_dir, log_dir, args.run_tag,
            args.plan_year, args.tier_file, args.date_run,
            args.overwrite, args.skip_existing_detal, args.skip_existing_asset,
            args.dry_run,
        )
        if code != 0:
            return code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
