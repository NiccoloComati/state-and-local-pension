# Project Context: State & Local Pension Sustainability Model

**Created:** 2026-05-27 
**Last Updated:** 2026-06-09 (session 2)
**Author**: Niccolo Comati
**Working Directory:** `...\Research and Education\Projects\State and Local Pension\State Pension Model\`

---

## 1. Plans Covered

40 state & local pension plans selected by Lenney et al. (2021) as highly representative of the universe of U.S. plans. Base year: **2017** (with updates to 2021 for key drivers).

| Code   | Plan Name / State                              | # Tiers |
|--------|------------------------------------------------|---------|
| AZ06   | Arizona (plan 6)                               | ?       |
| AZ127  | Arizona (plan 127)                             | ?       |
| CA10   | CalPERS (SCAL or similar)                      | 2       |
| CA43   | California (plan 43)                           | ?       |
| CA97   | California (plan 97)                           | ?       |
| CA98   | California (plan 98)                           | ?       |
| CA111  | California (plan 111)                          | ?       |
| CA144  | California (plan 144)                          | ?       |
| DC20   | Washington D.C. (plan 20)                      | ?       |
| FL26   | Florida (plan 26)                              | ?       |
| GA27   | Georgia (plan 27)                              | ?       |
| GA28   | Georgia (plan 28)                              | ?       |
| IL32   | Illinois (plan 32)                             | 2       |
| IL33   | Illinois (plan 33)                             | ?       |
| IL34   | Illinois (plan 34)                             | ?       |
| IN37   | Indiana (plan 37)                              | ?       |
| LA44   | Louisiana (plan 44)                            | ?       |
| LA130  | Louisiana (plan 130)                           | ?       |
| LA163  | Louisiana (plan 163)                           | ?       |
| MA50   | Massachusetts PERC (plan 50)                   | 2       |
| MA51   | Massachusetts (plan 51)                        | ?       |
| ME47   | Maine (plan 47)                                | ?       |
| MI53   | Michigan (plan 53)                             | ?       |
| MO64   | Missouri (plan 64)                             | ?       |
| MO175  | Missouri (plan 175)                            | ?       |
| ND82   | North Dakota (plan 82)                         | ?       |
| NJ71   | New Jersey (plan 71)                           | ?       |
| NJ73   | New Jersey (plan 73)                           | ?       |
| NM74   | New Mexico (plan 74)                           | ?       |
| NY78   | New York (plan 78) Ã¢â‚¬â€ template plan in XX.R     | 6       |
| NY83   | New York (plan 83)                             | ?       |
| OH88   | Ohio (plan 88)                                 | 6       |
| OK134  | Oklahoma (plan 134)                            | ?       |
| OR91   | Oregon (plan 91)                               | ?       |
| PA92   | Pennsylvania (plan 92)                         | ?       |
| PA93   | Pennsylvania (plan 93) Ã¢â‚¬â€ has OneTier variant   | ?       |
| RI96   | Rhode Island (plan 96)                         | ?       |
| SC99   | South Carolina (plan 99)                       | ?       |
| SC100  | South Carolina (plan 100)                      | ?       |
| TX108  | Texas (plan 108)                               | ?       |

Plan IDs correspond to the Public Plans Database (PPD) identifier (`ppid`).

---

## 2. Directory Structure

**REORGANIZED 2026-06-11:** the project root is now the parent folder `State and Local Pension/`; the former `State Pension Model/` subfolder was dissolved into it (see `Documentation/reorg_plan.md` for the executed manifest).

```
State and Local Pension/          <- PROJECT ROOT
+-- Code/
|   +-- python/                   # THE production engine
|   |   +-- fast/                 # Optimized package (PlanParams, vectorized core)
|   |   +-- analysis/             # results_analysis.py + results.ipynb
|   |   +-- validation/           # compare_r_python.py, compare_fast_vs_orig.py
|   |   +-- engaging/             # Slurm scripts (STALE paths post-reorg; rework before next cluster use)
|   |   +-- config/               # plans_38.txt canonical plan list
|   |   +-- Main_PensionModel.py, asset_simulation.py, run_simulation.py,
|   |   +-- scenarios.py, launcher.ipynb, sim_commands.html, g.py, ...
|   +-- R/                        # Verified reference implementation
|       +-- cluster_code_2022/    # 38 plan scripts (paths updated for new tree)
|       +-- Common_Code/          # shared R functions + asset_simulation_all_2022_062026.R
+-- Data/
|   +-- Plans/
|   |   +-- States/[PLAN]/        # 40 plan folders, fully intact (workbook, AV/CAFR PDFs, legacy RData)
|   |   +-- Cities/{city}_modeldata/  # canonical municipal collection (FY2019)
|   |   +-- Cities/_migration/    # state-model-format bridge (template, hou/chi/phx, planchanges_hougen-ag)
|   +-- Common/
|   |   +-- states/               # active state-track common data (ppd-data-latest [covers both tracks], planchanges_2022_clean, defaults, legacy PPD csvs)
|   |   +-- municipal/            # city-collection commons (city default_assumptions, variablesdb) - not yet wired into the model
|   +-- Returns/                  # asset-class series (monthly_series, monthly_matrix incl. correlation_matrix.RData, bostonfed)
|   +-- Sources/                  # brookings_package (replication data), airtable_export, collection_templates
+-- Results/
|   +-- Runs/062026/              # canonical run (Python fast outputs, 37 plans) + scenario run folders
|   +-- R Code/  Output/          # legacy post-processing + old outputs
+-- Documentation/                # this file + working_context, session_handoff, city/provenance narrative docs,
|   |                             #   guidebook copy, variable_glossary, media/ (incl. recorded code-walkthrough call)
|   +-- provenance/               # generator scripts (provenance_scan.py, city_data_scan.py,
|   |                             #   build_city_extraction_catalogue.py) + their generated CSVs/harvest
+-- Papers/                       # reference literature (Brookings papers, Dan_Papers) — moved out of Documentation 2026-07-07
+-- Drafts/                       # paper drafts (PensionSustainabilityV5.docx)
+-- Backup/                       # pre-reorg backup (file manifest + code/docs zip)
+-- Github/                       # leftover pensions-basecode husk at root (safe to delete when OneDrive unlocks it)
+-- _ARCHIVE/                     # everything superseded, reshaped 2026-06-11 to MIRROR the pre-reorg layout for legibility:
|   +-- State Pension Model/      #   the entire old SPM subtree intact (Cluster_Code/{cluster_062026,cluster_082024,cluster_code}, Common_Code/, Common_Data/{AV,AV_documentation}, Documentation/, Pipeline/, Results/, testing/, Brookings_Data/, Data_Daily/)
|   +-- city_2022_system/         #   2022 municipal collection system (Code/, Database/, Github_pensions-basecode/, old_ARCHIVE/)
|   +-- BrookingsData/ Pension_Data/ PDFs/ Data_Daily/ Github/   # pre-reorg source/data folders under their ORIGINAL names
|   +-- reorg_check_scratch/      #   bit-identity validation scratch (OK134)
|   +-- OneDrive_2023-12-07.zip, _premove_backup_code_docs.zip   # snapshot zips (no longer under a snapshots/ subfolder)
```
The former empty `State Pension Model/` root tombstone is gone; the pre-reorg SPM tree now lives only at `_ARCHIVE/State Pension Model/`. The old archive names `state_R_legacy/`, `snapshots/`, and `returns_daily/` no longer exist.
## 3. Data Sources

**Provenance catalogue (2026-06-11):** what each input IS and where every piece comes from is catalogued in `Documentation/model_input_dictionary.md` (schema: input → source channel → fallback chain → constants) and `Documentation/provenance/provenance_register.csv` (instance: 804 rows, plan × element, both tracks, with specificity/evidence/confidence; regenerate via `Documentation/provenance/provenance_scan.py`). Source-document landscape: `Documentation/data_sources_map.md`. Notable engine facts recorded there: the `wagegrowth` and `disability` workbook sheets are never read (wage growth comes from a PPD scalar fallback chain; disability is a constant), and 33 plan-sheets contain plan-specific data that `availableData=False` causes the engine to ignore (verify layout before flipping flags).

### Plan-Level Data (Common_Data/)
- **Public Plans Database (PPD):** `ppd-data-latest.xlsx` Ã¢â‚¬â€ comprehensive annual data on ~200 U.S. S&L plans, covering assets, liabilities, demographics, contribution rates, and benefit parameters. The model uses only the 40 selected plans.
- **Tier Parameter File:** `planchanges_main.xlsx` Ã¢â‚¬â€ hand-curated benefit parameters for up to 6 tiers per plan (benefit factors, COLA, vesting, retirement ages, salary averaging rules).
- **Default Assumptions:** `default_assumptions.xlsx` Ã¢â‚¬â€ actuarial tables used when plan-specific data is unavailable (mortality, separation, retirement, wage growth, etc.).

### Plan-Specific Data ([PLAN]/[PLAN]_2017.xlsx)
Each Excel file has up to 9 sheets:
1. **ageservice** Ã¢â‚¬â€ Age Ãƒâ€” service bucketed matrix of active employee counts
2. **retdist** Ã¢â‚¬â€ Age distribution of current retirees
3. **wagerel** Ã¢â‚¬â€ Relative wage by age and service (salary relativities)
4. **mortality** Ã¢â‚¬â€ Mortality rates by age (and sometimes gender)
5. **wagegrowth** Ã¢â‚¬â€ Wage growth assumptions
6. **withdrawal** Ã¢â‚¬â€ Separation/turnover rates by age and service
7. **retirement** Ã¢â‚¬â€ Retirement propensity rates by age and service
8. **refund** Ã¢â‚¬â€ Refund rates upon separation
9. **disability** Ã¢â‚¬â€ Disability benefit rates (rarely available; code uses a default rate)

Data availability varies by plan. Each script has an `availableData` vector (9 booleans) flagging which sheets are populated. When `availableData[i] = FALSE`, the corresponding sheet from `default_assumptions.xlsx` is used.

### Asset Data
Asset allocation weights come from PPD fields: `EQTotal_Actl`, `FITotal_Actl`, `PETotal_Actl`, `AltMiscTotal_Actl`, `HFTotal_Actl`, `RETotal_Actl`, `COMDTotal_Actl`, `OtherTotal_Actl`.

---

## 4. Model Overview

### 4.1 Simulation Structure
- **Base year:** 2017 (initializes all variables to observed/imputed values)
- **Horizon:** 35 years forward (`Nyear = 35`)
- **Monte Carlo:** 10,000 asset return simulations (`num_sim = 10000`; each plan script runs `NMonte = 10` for quick testing)
- **Seed:** `set.seed(54848631)` for replicability

### 4.2 Liability Projection (Deterministic)
Liabilities evolve deterministically year-by-year:
1. The age-service matrix of active employees is updated: workers age +1 year, accumulate +1 year service; some separate (withdrawal rates), some retire (retirement rates), some die (mortality); new hires refill to maintain workforce size.
2. Inactive (vested, not yet retired) members age and eventually draw benefits at `InactiveRetirement = 65`.
3. Retirees age and die; their benefits grow by COLA.
4. Cash outflows = retirement benefits + refunds to separators + death benefits + disability payments.
5. Cash inflows = employee contributions + employer contributions.
6. AAL = discounted present value of future benefit payments attributable to past service.

### 4.3 Asset Simulation (Stochastic)
- Asset returns modeled as a weighted portfolio of stocks (expected return 7.5% + inflation, SD 20%) and bonds (risk-free rate, SD 0%).
- Each year: `Assets[t+1] = Assets[t] Ãƒâ€” (1 + AnnualReturn) Ã¢Ë†â€™ CashOutflows[t] + Contributions[t]`
- Contribution rule: if funded, contribute scheduled amount; if underfunded, contribute cash inflows or amortized UAAL payment.
- If assets hit zero, they stay at zero (no bailout assumption).

### 4.4 Multi-Tier Handling
Most plans have 2Ã¢â‚¬â€œ6 tiers reflecting legislative changes in benefit generosity over time. Each tier has its own:
- Benefit factor, COLA, vesting period, normal retirement age, early retirement age, salary-averaging window, and benefit cap.
- Service years since tier start are computed from `tier_service = round(difftime(plan_start, tier_startdate, unit="weeks")/52.25)`.
- The active employee matrix is partitioned across tiers; each tier runs through `Main_Current()` independently; results are summed.

---

## 5. Key Model Functions (Common_Code/)

| Function | File | Purpose |
|---|---|---|
| `LinearFill()` | bucketfill_cf_model.R | Expands bucketed age-service data to full matrix |
| `ConstantFill()` | bucketfill_cf_model.R | Expands retirement distribution to matrix |
| `MortTable()` | bucketfill_cf_model.R | Creates mortality rate matrix by age & gender |
| `PastWages()` | functions_cf_model.R | Retrieves past wage vector for benefit calc |
| `Refund()` | functions_cf_model.R | Calculates refunds to separating employees |
| `DeathPay()` | functions_cf_model.R | Calculates death benefit payouts |
| `UpdateEmployeeCount()` | functions_cf_model.R | Ages workforce, removes leavers, adds hires |
| `UpdateInactiveCount()` | functions_cf_model.R | Updates inactive/vested member count |
| `UpdateInactiveBenefits()` | functions_cf_model.R | Updates accrued benefits for inactive members |
| `UpdateRetirementNumber()` | functions_cf_model.R | Moves members from active/inactive to retired |
| `UpdateRetirementBenefit()` | functions_cf_model.R | Updates retiree benefit amounts |
| `ComputeAnnuity()` | functions_cf_model.R | Computes annuity price vector by age |
| `Main_Current()` | functions_cf_model.R | Master loop: runs a single tier's full projection |
| `Main_Ret()` | functions_cf_model.R | Projects already-retired members' liabilities |
| `PVNC_Calc()` | liability_cf_model.R | Calculates Present Value of Normal Cost |
| `TotalLiabilities_Current()` | liability_cf_model.R | Total AAL for active & inactive members |
| `TotalLiabilities_Ret()` | liability_cf_model.R | Total AAL for retired members |

---

## 6. Execution Flow (Per Plan)

Each `Main_PensionModel_[PLAN].R` script follows this sequence:

1. **Source** common code files from `Common_Code/`
2. **Load** plan-specific Excel data ([PLAN]_2017.xlsx, 9 sheets)
3. **Load** master PPD database and extract plan row (`ppd-data-latest.xlsx`)
4. **Load** tier parameters (`planchanges_main.xlsx`)
5. **Set** simulation parameters (Nyear, NMonte, economic assumptions, discount rate)
6. **Expand** data: run `LinearFill()`, `ConstantFill()`, `MortTable()` to build full matrices
7. **Partition** active employees across tiers (active_t1 Ã¢â‚¬Â¦ active_t6)
8. **Run** `Main_Current()` for each tier Ã¢â€ â€™ produces (AAL, CashOutflow, CashInflow, PVFB, NormalCost)
9. **Run** `Main_Ret()` for already-retired members Ã¢â€ â€™ produces (AAL, CashOutflow)
10. **Aggregate** across tiers
11. **Save** liability/cash-flow comparison output as a `.RData` file in the plan folder
12. **Optionally run** an embedded quick asset loop in some top-level plan scripts (`NMonte` is usually 10, sometimes 1 or 100)
13. **Run** separate batch asset simulation scripts for full stochastic funding ratio paths (`num_sim = 10000`)
14. **Compare** model AAL vs. CAFR-reported AAL (`Percent_difference`)

---

### 6.1 Code Versions, Cluster Scripts, and Asset Simulation Outputs

Observed code locations and file conventions:

- **Top-level plan scripts (`[PLAN]/Main_PensionModel_[PLAN].R`)** exist for all 40 plan folders. Some top-level plan scripts contain asset loops after `save.image()`; inspect save order before assuming a saved `*_Compare*.RData` contains projected asset paths.
- **`Cluster Code/cluster_code/`** contains 38 cluster plan scripts. This local set excludes `MA51` and `MO64`. These scripts are configured with `/data/smithafe/Pension_CF_Model/`, commonly use `date_run <- "03062024_Adj"` and `NMonte <- 1`, and save compare-style files such as `[PLAN]/[PLAN]_Compare_03062024_Adj.RData`.
- **`Cluster Code/cluster_082024/cluster_code_2022/`** contains 38 plan scripts with `plan_year <- 2022`, `date_run <- "2022_July2024"`, and `plan_start <- as.Date("2022-01-01")`. These scripts use 2022-specific common data files such as `planchanges_main_2022_clean.xlsx`.
- **`Cluster Code/cluster_062026/cluster_code_2022/`** is the active local working copy for the 062026 2022 run. Its deterministic A/L scripts save to `Results/Runs/062026/[PLAN]/[PLAN]_detAL_2022_062026.RData`. These scripts now centralize wage-growth, inflation, and inactive-scaling fallback behavior through common helpers in `Cluster Code/cluster_062026/Common_Code/functions_cf_model.R`.
- **`Cluster Code/cluster_082024/Common_Code/asset_simulation_all.R`** is a batch asset simulation script. It loads `[PLAN]/[PLAN]_Compare_02152024_best.RData`, sets `num_sim <- 10000`, uses a 2-asset nominal return model, and saves `[PLAN]/[PLAN]_AssetSim05312024_best.RData`.
- **`Cluster Code/cluster_082024/Common_Code/asset_simulation_all_new.R`** is a batch asset simulation script using five asset classes and correlated real returns. It loads `[PLAN]/[PLAN]June2024.RData`, reads plan inflation and asset allocation from `ppd-data-latest.xlsx`, requires `Returns/correlation_matrix.RData`, and saves `[PLAN]/[PLAN]_AssetSimJune2024.RData`. `NJ71` is explicitly omitted in this script.
- **`Cluster Code/cluster_062026/Common_Code/asset_simulation_all_2022_062026.R`** is the active local dated 2-asset asset simulation script for the 062026 workflow. It auto-discovers `Results/Runs/062026/[PLAN]/[PLAN]_detAL_2022_062026.RData`, computes 2-asset allocation from saved `planinfo` when `AssetShare` is absent, writes `Results/Runs/062026/[PLAN]/[PLAN]_AssetSim_2022_2asset_062026.RData`, and updates `Results/Runs/062026/_manifest.csv`. It currently has `num_sim <- 10000`.
- **`Results/R Code/errors_all_plans.R`** loads compare files and writes validation error summaries. **`Results/R Code/fr_graph_all.R`** and **`Results/R Code/fr_graph_all_each.R`** load `AssetSim` files and generate funding-ratio forecast plots.
- **`Cluster Code/cluster_062026/Python Code/analysis/results_analysis.py`** is the Python analysis module for canonical run outputs. It uses clean `*_analysis.RData` companion files when available so Python can load results directly with `pyreadr`, and falls back to Rscript for full `save.image()` workspaces. It also discovers parquet bundles via `available_parquet_outputs()` and loads them via `load_plan_result_parquet()`. **`Cluster Code/cluster_062026/Python Code/analysis/results.ipynb`** is the single analysis notebook (the former rdata/parquet twin notebooks were merged 2026-06-10, then moved into `analysis/` and renamed). Cell 1 sets `RUN_TAG` and `RESULT_SOURCE = "auto"`, which detects R `.RData` vs Python parquet outputs from the run-folder contents via `results_analysis.detect_result_source()`; set it to `"rdata"` or `"parquet"` explicitly to override (auto prefers parquet when a folder contains both). The notebook imports `results_analysis.py` from its own directory (`Path.cwd()`), so run it with the working directory set to `analysis/` (Jupyter's default when opening the notebook). Rebuilt 2026-06-10 in stochastic-first order: Part 1 risk metrics (liability-weighted exhaustion timing, exhaustion-year CDFs, mean-years-insolvent severity, threshold-risk-over-time, funding-ratio distributions at two horizons, P(FR<0.4) distress heatmap, exhaustion-risk scatters), Part 2 aggregate dynamics (per-path aggregate funded-ratio and unfunded-AAL fans — valid because of common market shocks, equal-plan average forecast, GDP-normalized unfunded-AAL fan), Part 3 per-plan detail (forecast fans, cash flows, long-format export), Part 4 baseline/descriptive (summary statistics, historical funded ratios, AAA cash-flow PV funded ratios, model-vs-CAFR validation; the descriptive reform/tier-rule section was removed 2026-06-10 pending a rework as a pre-change vs post-change tier comparison). FRED-dependent sections (GDP, AAA) skip gracefully without `FRED_API_KEY`. The load cell verifies the `common_market_shocks` flag and warns if aggregate bands would understate risk.
- The former **`Pipeline/062026/`** R-track run-control workflow (38-plan list, local PowerShell runner, Engaging Slurm scripts, remote wrapper, assumption audit) was archived in the 2026-06-11 reorg to `_ARCHIVE/State Pension Model/Pipeline/062026/`; its standalone doc (`062026_run_pipeline.md`) was deleted. Current run control is the Python side: `run_simulation.py` / `launcher.ipynb` / `sim_commands.html`.

062026 output status should be treated as runtime state, not durable project
context:

- Canonical 062026 outputs are organized under `Results/Runs/062026/`, with one subfolder per plan and run metadata in `_manifest.csv`.
- As of 2026-06-10 the folder contains Python `fast/` outputs only:
  `[PLAN]_detAL_062026.pkl`, `[PLAN]_AssetSim_2asset_062026.pkl`,
  `[PLAN]_AssetSim_2asset_062026_parquet/`, and the Python `_manifest.csv`
  (per-plan detal/asset status, num_sim, timing).
- If the R track is rerun, its scripts write `[PLAN]_detAL_2022_062026.RData`,
  `[PLAN]_AssetSim_2022_2asset_062026.RData`, and analysis companions
  `[PLAN]_AssetSim_2022_2asset_062026_analysis.RData` into the same folder.
- Do not hardcode current detAL/AssetSim/analysis counts in this file. Reruns can change them without documentation edits.
- Check current local status by inventorying `Results/Runs/062026/`; for remote (Engaging) status use the Python wrapper `Code/python/engaging/remote_python_run.ps1 -Action inventory` (note: the engaging scripts are stale post-reorg — rework before next cluster use).
- `MA50` is excluded from the Python runner (structural outlier); on the R side, `asset_simulation_all_2022_062026.R` only requires `NormalCost` and `discountrate` when `Amortize <- TRUE`.

---


### 6.2 Python Translation

A Python translation track exists under `Cluster Code/cluster_062026/Python Code/`. The deterministic A/L functions were translated line-by-line from R. As of the 2026-06-08 buildout, Python can run both the deterministic A/L stage and the 2-asset stochastic simulation end-to-end for the standard 37 plans (MA50 excluded), writing `.pkl` detAL outputs and `.pkl`/`.parquet` asset outputs rather than R `.RData` files. **As of 2026-06-10, the Python `fast/` package is the production engine**: it was verified bit-identical to the original Python translation (which was itself verified against R at floating-point precision), then optimized to ~10× the original Python speed (full 37-plan detal+asset batch in ~8 minutes locally at 19-way parallelism), and the canonical `Results/Runs/062026/` outputs were regenerated with it at num_sim=10000. The R code remains in place as the verified reference implementation but no longer has canonical outputs. All 37 standard plans (MA50 excluded) have been verified against R outputs as of 2026-06-09. All simulation matrices (tier AAL, aggregate AAL, cash flows, NormalCost) agree at floating-point precision (max_rel ~1e-15) across both the deterministic A/L stage and the liability components of the asset stage. Cosmetic metadata mismatches (`run_tag` for all plans; `Percent_difference` for 17 plans due to sign/denominator convention difference between R and Python) are not simulation bugs. LA130 and LA163 have Python asset outputs but no R asset simulation counterpart.

**Files (`Cluster Code/cluster_062026/Python Code/`):**
- `g.py` — shared global state module (R global environment → Python module-level variables). **Legacy**: used only by the original Python scripts (`Main_PensionModel.py`, `liability_cf_model.py`, etc.); the `fast/` package replaces it with `PlanParams`. Keep until `fast/` fully supersedes the original.
- `bucketfill_cf_model.py` — Python translation of `Common_Code/bucketfill_cf_model.R`
- `functions_cf_model.py` — Python translation of `Common_Code/functions_cf_model.R`
- `liability_cf_model.py` — Python translation of `Common_Code/liability_cf_model.R`
- `Main_PensionModel.py` — generic Python deterministic A/L runner for 37 standard plans (MA50 excluded). Call: `python "Python Code/Main_PensionModel.py" <PLAN_ID>`
- `asset_simulation.py` — Python 2-asset asset simulation with **common market shocks** (2026-06-10): all plans share one standardized shock matrix `Z` from a single market seed (`--seed`); plan p's stock return is `(0.075 + Inflation_p) + 0.20*Z[t,n]`, so simulation column n is the same market history for every plan and aggregate cross-plan distributions are meaningful. Per-plan marginals are unchanged; this intentionally differs from the R script (independent per-plan draws). The Monte Carlo loop is vectorized across simulations (~4s/plan at num_sim=10000). Payloads store `market_seed` and `common_market_shocks`. Loads Python detAL `.pkl` outputs, writes `.pkl` asset outputs and parquet bundles. `run_tag` is the output label; `plan_year` is model data selection only.
- `run_simulation.py` — launcher/orchestrator: plan selection, detal/asset/both stage, `--parallel` ceiling (single `ThreadPoolExecutor` pool, not rigid batches), `--fast` flag (uses `fast/Main_PensionModel.py`), `--workers` (PVNC thread-pool, fast only), `--discount-override` pass-through, dry-run, skip-existing. Does not implement model equations.
- `scenarios.py` — scenario layer (2026-06-10): `Scenario` dataclass whose defaults reproduce the baseline; levers for contribution policy (`contrib_add` pp of payroll, `policy_start`, `contrib_always`), investment strategy (`equity_share`, `derisk_to`/`derisk_years` glidepath), return assumptions (`stock_premium`, `stock_vol`), liability valuation (`discount_override`), and benefit rules (`tier_file`). Grid helpers (`contribution_grid`, `equity_grid`), `preview`, `launch(dry_run=...)`, `inventory`, `compare_exhaustion`. Asset-only scenarios read baseline detAL inputs via `--detal-run-tag` and write under their own run tag; all scenarios share market seed 123 by default for path-by-path comparability. Scenario provenance is stored in output pkls (`scenario`) and `_manifest.csv`.
- `launcher.ipynb` — notebook control panel over `scenarios.py`: define scenarios declaratively, preview exact commands, launch (dry-run by default), inventory outputs, quick cross-scenario exhaustion comparison. Preferred way to run sensitivities/scenarios instead of the terminal.
- `sim_commands.html` — browser-based command reference for all local and Engaging run variants. Includes `--fast` and `--workers` parameter documentation.

**`fast/` package (`Cluster Code/cluster_062026/Python Code/fast/`):**
- `fast/sim_params.py` — `PlanParams` dataclass replacing g.py global state.
- `fast/core.py` — optimized simulation functions: vectorized `update_employees`/`l_update_employees` (numpy diagonal shift), vectorized `death_pay` (triangle mask), vectorized `compute_annuity` (`np.cumprod`), parallel `pvnc_calc_fast` (`ThreadPoolExecutor` over 55 ages), parallel `total_liabilities_current_fast` (2 paths in parallel).
- `fast/Main_PensionModel.py` — fast runner for all 37 standard plans; same CLI as original plus `--workers` and `--discount-override` (scenario lever: replaces the plan GASB discount rate in AAL/PVNC). Saves `EmployeeContributionRate`/`EmployerContributionRate` scalars in the detAL pkl (needed by contribution-policy scenarios) and `discount_override` provenance. Uses absolute imports (`from fast.sim_params import ...`) because it is run as a script directly. `main_ret_fast` receives `COLA_t[num_tiers]` / `BenefitFactor_t[num_tiers]` / `NyearFullBenefit_t[num_tiers]` (last tier's values), matching R's global-mutation behavior.

**`validation/` folder (`Cluster Code/cluster_062026/Python Code/validation/`):**
- `compare_r_python.py` — R vs Python comparison for detal and asset outputs. Recomputes `Percent_difference` on the fly from stored `Model_AAL`/`CAFR_AAL` to avoid stale stored values.
- `compare_fast_vs_orig.py` — fast vs original Python comparison. Expected clean result: all 4 matrix keys (AAL, NormalCost, cash_outflows, cash_inflows) at max_abs=0 after NC bug fix (2026-06-09).
- `README.md` — example commands.

**Engaging pipeline (`Cluster Code/cluster_062026/Python Code/engaging/`):**
- `remote_python_run.ps1` — local wrapper (package/upload/upload-submit/submit/status/inventory/fetch). Always use `-Action upload-submit` (not bare `submit`). Confirmed working: `-CondaModule "miniforge/24.3.0-0"` (Python 3.10); `openpyxl` and `pyarrow` auto-installed by `engaging_python_env.sh`.
- `submit_slurm.sh` — submits detAL Slurm array and dependent asset array on Engaging. Calls `setup_python_env` once on the login node before submitting to avoid pip race conditions.
- `slurm_detal_array.sh` / `slurm_asset_array.sh` — Slurm array scripts (one plan per task). Derive `CLUSTER_DIR` from exported `PROJECT_ROOT`, not `BASH_SOURCE` (which points to the spool dir in Slurm). Log via `exec >> "${LOG_FILE}" 2>&1` (process substitution unavailable on Engaging).
- `engaging_python_env.sh` — Python env activation helper; auto-installs `openpyxl` and `pyarrow` if missing.

**Canonical run tag:** `062026`. As of 2026-06-10, `Results/Runs/062026/` contains Python `fast/` outputs only (37 plans, detal pkl + asset pkl + parquet bundles, num_sim=10000); the earlier R `.RData` outputs and the `062026_py`/`062026_fast` folders were deleted after Python was verified equivalent. The old `062026`=R / `062026_*`=Python tag convention is retired.

**Python output naming:** detAL: `[PLAN]_detAL_[run_tag].pkl`; asset: `[PLAN]_AssetSim_2asset_[run_tag].pkl`. No `_2022_` separator (unlike R).

**`Percent_difference` formula:** standardized everywhere to `(Model_AAL - CAFR_AAL) / CAFR_AAL`. All 21 affected R scripts patched; existing RData files patched in-place via `Common_Code/patch_percent_difference.R`; Python already used correct formula.

**Bugs found and fixed during line-by-line verification:**
1. `UpdateRetirementBenefit` in `functions_cf_model.py`: two-step in-place update used the already-modified value; fixed to copy-before-assign matching R's single RHS expression.
2. `Calc_Inactive` in `bucketfill_cf_model.py`: missing `int()` cast on `NyearFullBenefit_f` before slice indexing.
3. `_zero_outside` in `bucketfill_cf_model.py` (`CreateTiers`): when two adjacent tier boundaries round to the same service year (e.g., OH88 Tiers 2–3 both = 41), Python's empty slice zeroed the entire tier. R's `a:b` for `a >= b` generates a descending sequence spanning both endpoints. Fixed: `keep_from, keep_to = keep_to - 1, keep_from + 1` when `keep_from >= keep_to`.
4. `fast/Main_PensionModel.py` — `main_ret_fast` called with `COLA_t[1]` instead of `COLA_t[num_tiers]` (and same for `BenefitFactor_t`, `NyearFullBenefit_t`). Caused wrong retired-population AAL for multi-tier plans with different COLA across tiers. Fixed to use `_t[num_tiers]`.

**MA50 excluded from generic runner:** MA50 uses a different risk-free-rate formula, is missing the `*1000` asset multiplier, has backward tier logic, contains a `++` syntax error, and produces no `NormalCost` output.
## 7. Known Issues / Notes

- **Disability data:** Sheet 9 is almost never populated (`availableData[9] = F`). The model uses a fixed `DisabilityPayoutRate = 0.025` (2.5% of payroll) as default; some plans compute it from actual data (e.g., MA50: ratio of disability payroll to total payroll).
- **Retirement and refund rates:** Sheets 7 and 8 are often missing (`availableData[7:8] = F`). The code falls back to `default_assumptions.xlsx`.
- **Withdrawal data (IL32):** `availableData[6] = F` for Illinois plans Ã¢â‚¬â€ no plan-specific separation rates.
- **Inactive member scaling:** Some plans (e.g., MA50) scale the inactive member matrix differently: `inactive * planinfo$InactiveVestedMembers` rather than `PPD$inactive`.
- **Discount rate source varies:** Most plans use `PPD$discount`; some (e.g., MA50) use `planinfo$InvestmentReturnAssumption_GASB` directly.
- **PA93** has a special `PA93_OneTier_PensionModel.R` variant.
- **TX108, SC100, RI96** have `_2` variant scripts.
- **Batch asset simulation typo:** `asset_simulation_all_new.R` defines `Amortize_Period <- 30` but references `Amotorize_Period` inside the amortization branch. This only matters if `Amortize <- TRUE`; the current script sets `Amortize <- F`.
- **Model AAL vs CAFR AAL:** The `Percent_difference` diagnostic is a key validation check. Differences arise because the model uses a standardized actuarial approach (entry-age normal), while plans may use different methods.

---

## 8. External References

- **Lenney et al. (2021):** Brookings paper Ã¢â‚¬â€ source of the 40-plan selection and a data reference, files in `Brookings_Data/`. Methodologically it is **the paper this project critiques**: its sustainability analysis reasons in means/deterministic terms, and this project's thesis is that pension sustainability must be assessed through stochastic outcome distributions (exhaustion probabilities, tail risk, distribution fans). Where the analysis notebook reproduces Lenney-style figures/tables, the intent is to redo them "the correct way" — distributionally — not to emulate their framing.
- **PPD (Public Plans Database):** Maintained by Boston College Center for Retirement Research. Annual data on ~200 U.S. public pension plans.
