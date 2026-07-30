# Code/python — what each file is

The simulation engine. Analysis of the results lives in `Analysis/` at the project
root, and shares no code with anything here.

## The live path — every run touches these

| File | Role |
|---|---|
| `run_simulation.py` | The orchestrator you call. Plan selection, parallelism, run tags, stage control. Launches the files below as subprocesses; contains no model equations. |
| `fast/Main_PensionModel.py` | **The production engine.** Deterministic liability and cash-flow projection for one plan. |
| `fast/core.py` | Vectorised simulation functions. |
| `fast/sim_params.py` | `PlanParams`, the per-plan parameter object. |
| `bucketfill_cf_model.py` | `LinearFill` / `ConstantFill` — spreading bucketed data over single ages and service years. |
| `functions_cf_model.py` | Shared helpers: fallback chains, workforce updates, benefit calculations. |
| `g.py` | Module-level global state. **Not optional** — `bucketfill_cf_model` and `functions_cf_model` reference it heavily, so the fast engine pulls it in. |
| `asset_simulation.py` | The stochastic stage. One shared market shock matrix across all plans. |
| `config/plans_40.txt` | The plan list used by `--plans all`. |
| `config/plans_38.txt` | Kept so the earlier 37-plan selection can be reproduced. |

## Reference lineage — never run

| File | Why it is here |
|---|---|
| `Main_PensionModel_original.py` | The pre-optimisation runner. `fast/` was verified bit-identical against it, and it was verified against R. Renamed from `Main_PensionModel.py` on 2026-07-30 because sharing a filename with the engine was confusing. Still reachable via `run_simulation.py` without `--fast`. |
| `liability_cf_model.py` | Liability functions used by that original lineage, imported lazily inside `functions_cf_model`. |

## Checking a change did not break anything

`validation/compare_fast_vs_orig.py` and `validation/compare_r_python.py` compare
saved outputs between implementations. The standing bar for any engine change is
bit-identity: rerun one plan under a scratch run tag and compare every array
against the previous run; the maximum difference must be 0.0.

## The scenario layer — built, parked

`scenarios.py` defines scenario variants (contribution policy, equity share and
glidepath, return assumptions, discount rate, benefit rules) and builds the
corresponding `run_simulation.py` commands. `scenario_scenario_launcher.ipynb` is a notebook control
panel over it.

**This is not an alternative way to launch a baseline run.** Baseline runs go
through `run_simulation.py` from the terminal. The launcher is for defining and
comparing scenario variants, which is work that has not started.

## Running

```powershell
python run_simulation.py --plans all --stage both --fast --num-sim 10000 --run-tag YYYYMMDD_N --parallel 20 --workers 1 --seed 123
```

- `--run-tag` follows `YYYYMMDD_N`. Omit it and the next free tag is minted and
  printed. The runner refuses to write into an existing non-empty run folder
  unless `--overwrite` or a `--skip-existing-*` flag is passed.
- `--workers 1` is deliberate. The PVNC thread pool is GIL-bound; raising it slows
  the run down.
- `--seed 123` is the canonical market seed. Every plan in a run must share one
  seed or cross-plan aggregates become meaningless.
- What each existing run contains: `Results/Runs/README.md`.
