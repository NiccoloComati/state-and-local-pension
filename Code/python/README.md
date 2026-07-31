# Code/python — what each file is

The simulation engine. Analysis of the results lives in `Analysis/` at the project
root and shares no code with anything here.

Four folders, and the split is meant to be readable from the names alone:
`engine/` is the model, `settings/` is every decision that applies to one plan
rather than all of them, `reference/` is the older implementation kept for
verification, `validation/` is the scripts that do the comparing.

## `engine/` — the model

| File | Role |
|---|---|
| `run_plan.py` | **The production engine.** Deterministic liability and cash-flow projection for one plan: reads that plan's workbook, builds its population and benefit structure, projects 35 years. |
| `core.py` | The vectorised year-by-year simulation functions `run_plan.py` calls. |
| `params.py` | `PlanParams`, the per-plan parameter object handed to `core.py`. |
| `bucketfill.py` | `LinearFill` / `ConstantFill` — expanding data published in age and service BANDS into a full single-age × single-service-year matrix. **`LinearFill` was corrected 2026-07-30**; the inherited version is kept alongside as `LinearFill_incorrect` because `Code/R/cluster_code_2022/` still calls it. |
| `functions.py` | Shared helpers: the PPD fallback chains, workforce updates, benefit calculations. |
| `liability.py` | Liability functions used by the reference lineage, imported lazily from `functions.py`. |
| `state.py` | Module-level global state. **Not optional** — `bucketfill.py` and `functions.py` reference it heavily. Imported as `g` throughout, which is what it was called before. |

`asset_simulation.py` (one level up) is the stochastic stage: it takes the
deterministic cash flows and simulates asset returns, with **one shared market
shock matrix across all plans** so cross-plan aggregate distributions mean
something.

## `settings/` — every per-plan decision, in one place

`plan_settings.py` holds all six of them, each entry carrying its reason inline:

1. `AVAILABLE_DATA` — nine booleans per plan choosing, sheet by sheet, between the
   plan's own workbook data and the shared `default_assumptions.xlsx`.
2. `CONTRIB_RATE_NA_CHECK` — plans whose PPD contribution rate comes out missing.
3. `CONTRIB_RATE_MODEL_PAYROLL` — plans measured against the model's own payroll
   rather than PPD covered payroll. FL26 only, on documentary evidence.
4. `APPLY_DISABILITY_TERM` — the per-plan disability switch. All `True`.
5. `SALARY_OVERRIDE` — published values we replace, keyed by (plan, fiscal year).
   MI53's 2022 average salary only.
6. `RETDIST_SKIPROWS` — workbook read quirks.

These used to be scattered through the engine file, two of them buried mid-way
through executable code. **If you are adding a plan-specific rule, it goes here.**

`plans_40.txt` is the plan list behind `--plans all`; `plans_38.txt` is kept so the
earlier 37-plan selection can be reproduced.

## `reference/` — never run in production

`run_plan_original.py` is the pre-optimisation runner. The fast engine was verified
bit-identical against it, and it was verified against the R implementation. Still
reachable through `run_simulation.py` without `--fast`.

## `validation/` — checking a change did not break anything

`compare_fast_vs_orig.py` and `compare_r_python.py` compare saved outputs between
implementations.

**The standing bar for any engine change is bit-identity:** rerun one plan under a
scratch run tag and compare every array against the previous run; the maximum
difference must be 0.0. This applies to pure relocations too, and not as a
formality — moving files one level deeper on 2026-07-30 silently shifted MA51's
liability by 0.7% through a hardcoded relative path that returned NaN when it
failed, with no error raised anywhere.

## The scenario layer — built, parked

`scenarios.py` defines scenario variants (contribution policy, equity share and
glidepath, return assumptions, discount rate, benefit rules) and builds the
corresponding `run_simulation.py` commands. `scenario_launcher.ipynb` is a notebook
control panel over it.

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
- `--disability-rate 0` switches the disability term off for every plan at once,
  which is the sensitivity lever. It defaults to 0.025.
- What each existing run contains: `Results/Runs/README.md`.
