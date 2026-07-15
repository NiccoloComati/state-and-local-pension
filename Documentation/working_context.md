# Working Context: State Pension Model

**Created:** 2026-06-01  
**Purpose:** Chat-level handoff memory for local Codex sessions. This file is separate from `project_context.md`: project context should track durable project/codebase facts, while this file should track what this chat did, what commands were run, what was learned, and where follow-up work should continue.

---

## Current Goal

Determine whether the repository already contains completed simulation results, or whether it mainly contains adapted main code files that still need to be run.

---

## Baseline Context Files Read

- `Documentation/project_context.md`
- `Documentation/variable_glossary.md`

Important baseline facts from those files:
- The model covers 40 top-level plan folders.
- Per-plan `Main_PensionModel_[PLAN].R` scripts run liability/cash-flow projections and save `.RData`.
- Full asset simulation is documented as `num_sim = 10000`; per-plan scripts commonly use quick `NMonte = 10` runs.
- `Results/` stores output plots and error summaries.

---

## Command Log And Findings

### Documentation discovery

- Ran `rg --files Documentation | rg '\.md$'`; it returned no files despite the folder existing.
- Ran `Get-ChildItem -Force` and `Get-ChildItem -Force -Directory | Where-Object { $_.Name -like '*Doc*' }`; confirmed `Documentation/` exists.
- Ran `Get-ChildItem -Force Documentation` and recursive file listing; found:
  - `Documentation/project_context.md`
  - `Documentation/variable_glossary.md`
- Read both files with `Get-Content -Raw`.

### Result artifact audit

- Ran recursive `.RData`/RDS scans and compact per-top-level grouping.
- Found many local `.RData` artifacts, but not uniform coverage across all 40 plan folders.
- Top-level plan folders with nested `.RData`: 25.
- Top-level plan folders without nested `.RData`:
  - `CA144`, `GA27`, `MA50`, `MA51`, `MI53`, `MO175`, `ND82`, `NJ73`, `NM74`, `NY83`, `OH88`, `OK134`, `OR91`, `PA92`, `SC99`
- Notable local `.RData` examples:
  - Many older/current plan files like `CA10/CA10_Compare_latest.RData`, `NY78/NY78_Compare_latest.RData`, `TX108/TX108_101723.RData`.
  - `PA93/Data/PA93_09252023.RData` and `PA93/Data/PA93_101723.RData`.
  - Testing scenario files under `testing/test_data/` and `cluster_082024/testing/test_data/`.

### Results folder audit

- Ran recursive listing of `Results/`.
- Found:
  - `Results/R Code/errors_all_plans.R`
  - `Results/R Code/fr_graph_all.R`
  - `Results/R Code/fr_graph_all_each.R`
  - `Results/Output/plan_errors.csv`
  - `Results/Output/plan_errors_2022.csv`
  - `Results/Output/Forecast_Plots/*.pdf` for the 2022-style plan list.
- `Results/R Code/fr_graph_all_each.R` loads files named `plan/plan_AssetSim.RData`.
- Search found no local files matching `*AssetSim*.RData`.
- Therefore the forecast PDFs exist locally, but the local input `.RData` files used by the graph script are missing.

### RData object inspection

- `Rscript` is not on PATH.
- Found R at `C:\Program Files\R\R-4.4.1`.
- Used `C:\Program Files\R\R-4.4.1\bin\Rscript.exe` to inspect plan `.RData` files.
- Local plan `.RData` files generally contain `Assets`, `AAL`, and `cash_outflows`.
- Most local plan results have dimensions `35 x 10` and `NMonte = 10`, consistent with quick per-plan simulations rather than full 10,000-run asset simulations.
- Exceptions observed:
  - `CA10/CA10_Compare_03062024_Adj.RData`: `Assets=35x1`, `AAL=35x1`, `NMonte=1`.
  - `SC100/SC100_09252023.RData` and `SC100/SC100_101723.RData`: `35x1`, `NMonte=1`.
  - `PA93/Data/PA93_09252023.RData` and `PA93/Data/PA93_101723.RData`: `35x100`, `NMonte=100`.
- None of the inspected local plan `.RData` files showed `num_sim = 10000`.

### Code status audit

- Every one of the 40 top-level plan folders has at least one `Main_PensionModel*.R` script.
- `PA93`, `RI96`, `SC100`, and `TX108` have `_2` variants.
- `cluster_code/` has 38 `Main_PensionModel_*.R` scripts; it excludes `MA51` and `MO64`.
- Most `cluster_code` scripts set `NMonte <- 1` and save `plan/plan_Compare_[date].RData`.
- Top-level plan scripts commonly set `NMonte <- 10`.
- `Common_Code/asset_simulation.R` sets `num_sim <- 10000` but is hard-coded for CA10 and does not save an output file.
- `cluster_082024/Common_Code/asset_simulation_all.R` and `asset_simulation_all_new.R` are batch/full asset simulation scripts that set `num_sim <- 10000` and save `plan/plan_AssetSim[date].RData`, but those resulting `AssetSim` files are not present locally.
- `Results/R Code/errors_all_plans.R` loads cluster path files named `plan/plan_Compare_02152024_best.RData`; those files are not present locally.

---

## Current Conclusion

The repository has adapted main code files for all 40 top-level plan folders and many partial/local `.RData` results from earlier quick or validation runs. It does not appear to contain the full 10,000-run asset simulation outputs locally. The missing evidence is the absence of `*_AssetSim*.RData` files and the fact that inspected local `.RData` files mostly use `NMonte = 10`, `1`, or `100`, not `num_sim = 10000`.

The `Results/Output/Forecast_Plots` PDFs and `plan_errors.csv` indicate that fuller runs likely happened on an external/cluster filesystem at some point, but the local repository does not include the corresponding full result `.RData` inputs.

---

## Recommended Next Step

Create a canonical run/output inventory:
- Decide the canonical plan set for the current project: all 40 folders vs. the 38-plan 2022/cluster list.
- Standardize output naming, probably:
  - liability/cash-flow result: `[PLAN]/[PLAN]_Compare_[date_or_tag].RData`
  - full asset simulation result: `[PLAN]/[PLAN]_AssetSim_[date_or_tag].RData`
- Add or update a batch runner that can regenerate missing full asset simulations locally or on cluster and write a machine-readable manifest.

---

## 2026-06-01 Follow-Up: `asset_simulation_all.R`

User asked to expand on the conclusion that full batch asset sim code exists but expected outputs are absent.

Commands run:
- Printed line-numbered contents of `cluster_082024/Common_Code/asset_simulation_all.R`.
- Searched recursively for `*AssetSim*.RData`; no files found.
- Searched recursively for `*Compare_02152024_best.RData`; no files found.

Relevant code facts:
- `asset_simulation_all.R` sets `current_dir <- "/nfs/sloanlab007/projects/pension_cf_model_proj/Pension_CF_Model/"`, so it is configured for a cluster/Linux path, not the local Windows workspace.
- It loops over 38 plans, not all 40 top-level local folders. The plan list excludes `MA51` and `MO64`.
- For each plan, it loads `plan/plan_Compare_02152024_best.RData`. Those expected input files are absent locally.
- It sets `num_sim <- 10000`, expands `Assets`, `AAL`, `cash_inflows`, and `cash_outflows` to 10,000 columns, simulates annual asset returns, updates `Assets`, and saves `plan/plan_AssetSim05312024_best.RData`.
- No `*AssetSim*.RData` files are present locally, so the saved full asset sim outputs from this batch script are missing from the local tree.

---

## 2026-06-01 Follow-Up: Asset Simulation In Main Scripts

User asked whether each plan's main script already runs assets.

Commands run:
- Printed representative line-numbered sections from:
  - `CA10/Main_PensionModel_CA10.R`
  - `NY78/Main_PensionModel_NY78.R`
  - `MA50/Main_PensionModel_MA50.R`
  - `cluster_code/Main_PensionModel_CA10.R`
- Searched representative plans for `save.image`, `for (n in 1:NMonte)`, and `Assets[t+1,n]`.
- Loaded representative `.RData` files with R and inspected whether saved `Assets` matrices have nonzero rows beyond row 1.

Findings:
- Many top-level plan scripts do include an asset-pool simulation loop near the bottom using `NMonte`, typically `NMonte <- 10`.
- In many scripts, `save.image()` occurs before the asset loop. Examples:
  - `CA10/Main_PensionModel_CA10.R`: saves at line 623, asset loop starts at line 635.
  - `NY78/Main_PensionModel_NY78.R`: saves at line 767, asset loop starts at line 779.
  - `TX108/Main_PensionModel_TX108.R`: saves at line 641, asset loop starts at line 651.
  - `MA50/Main_PensionModel_MA50.R`: saves at line 718, asset loop starts at line 728.
- Loaded local `.RData` files confirm this: for `CA10_Compare_latest`, `CA10_Compare_10dec`, `NY78_Compare_latest`, and `TX108_101723`, `Assets` has only row 1 nonzero; rows 2-35 are all zero. Thus these saved files contain initialized assets, not completed asset paths.
- `PA93/Main_PensionModel_PA93.R` is an exception: the asset loop comes before `save.image()`, and `PA93/Data/PA93_09252023.RData` has nonzero `Assets` in all rows with stochastic variation across 100 columns.
- Many `cluster_code/Main_PensionModel_*.R` scripts appear designed to save liability/cash-flow compare files only; they generally set `NMonte <- 1`. The separate `asset_simulation_all.R` then performs the full 10,000-path asset simulation afterward.

---

## 2026-06-01 Follow-Up: Global R Lintr Noise Reduction

User asked how to remove VS Code/lintr blue underline noise for style-only messages globally while keeping serious diagnostics.

Actions:
- Checked for workspace `.lintr` and `.vscode/settings.json`; neither exists on disk in the workspace from this shell.
- Checked for home `.lintr`; it did not exist.
- Confirmed installed `lintr` version is `3.2.0`.
- Created global `C:/Users/nicco/.lintr`.

Global `.lintr` now contains:

```text
linters: list(
  equals_na_linter = equals_na_linter(),
  object_usage_linter = object_usage_linter(),
  seq_linter = seq_linter(),
  vector_logic_linter = vector_logic_linter()
 )
```

Notes:
- The closing ` )` must be indented because `.lintr` is parsed as DCF-style config.
- This disables style-only defaults such as `line_length_linter`, `indentation_linter`, and `object_name_linter`.
- Verification command on `cluster_082024/Common_Code/asset_simulation_all.R` produced only one non-style warning: `seq_linter` for `c(1:length(plans))`, suggesting `seq_along(...)`.
- If a workspace-level `.lintr` is later added/saved, it may override the home config.

---

## 2026-06-01 Follow-Up: `asset_simulation_all.R` vs `asset_simulation_all_new.R`

User asked the difference between the two batch asset simulation scripts.

Commands run:
- Printed both files with line numbers.i want to run parallely the missing processes
- Ran a unified diff between:
  - `cluster_082024/Common_Code/asset_simulation_all.R`
  - `cluster_082024/Common_Code/asset_simulation_all_new.R`
- Searched for required new inputs:
  - `Returns/correlation_matrix.RData`: not found locally.
  - `*June2024.RData`: not found locally.

Summary:
- Both scripts are second-stage batch asset simulation scripts that load precomputed plan liability/cash-flow `.RData`, expand deterministic liabilities/cash flows to `num_sim <- 10000`, simulate asset paths, and save `AssetSim` `.RData`.
- `asset_simulation_all.R` is the older/simple two-asset version:
  - plan list has 38 plans, includes `NJ71`, excludes `MA51` and `MO64`.
  - loads `[PLAN]/[PLAN]_Compare_02152024_best.RData`.
  - output tag is `05312024_best`.
  - uses 2 assets, with expected returns `c(0.075 + Inflation, rf)` and vol `c(0.20, 0)`.
  - uses existing `AssetShare` from loaded compare file.
  - saves `[PLAN]/[PLAN]_AssetSim05312024_best.RData`.
- `asset_simulation_all_new.R` is a newer 5-asset/correlated-real-return version:
  - plan list has 37 plans; `NJ71` is omitted explicitly.
  - output/input tag is `June2024`.
  - loads `[PLAN]/[PLAN]June2024.RData`.
  - reads `Common_Data/ppd-data-latest.xlsx` to get 2017 plan inflation and asset allocation.
  - loads `Returns/correlation_matrix.RData`.
  - uses 5 asset classes: Equities, FI, Alternatives_PE, Cash, RE.
  - simulates correlated real returns with `MASS::mvrnorm`, converts to nominal with `(1 + AnnualRealRet) * (1 + Inflation_rate) - 1`.
  - stores `r_shocks`, `n_shocks`, and `all_shocks`.
  - saves `[PLAN]/[PLAN]_AssetSimJune2024.RData`.
- Potential bug in `asset_simulation_all_new.R`: it defines `Amortize_Period <- 30` but later references `Amotorize_Period`. This only matters if `Amortize <- TRUE`; with current `Amortize <- F`, that branch is skipped.

---

## 2026-06-01 Follow-Up: Project Context Update For Cluster Code

User asked whether the cluster code and code-version distinctions were documented in `project_context.md`.

Finding:
- Before this update, `project_context.md` only had a thin `cluster_code/` directory mention, a broad asset simulation execution-flow step, and a few variant bullets. It did not document the important distinction between compare files, embedded quick asset loops, and separate full batch asset simulation scripts.

Action:
- Updated `Documentation/project_context.md` to add:
  - `cluster_082024/` to the directory structure.
  - Revised execution flow distinguishing compare-file save, optional embedded quick asset loops, and separate full `num_sim = 10000` batch asset simulations.
  - New section `6.1 Code Versions, Cluster Scripts, and Asset Simulation Outputs`.
  - Durable notes on `cluster_code/`, `cluster_082024/`, `Common_Code/asset_simulation.R`, `asset_simulation_all.R`, `asset_simulation_all_new.R`, local missing full AssetSim outputs, and the `Amotorize_Period` typo.

---

## 2026-06-01 Follow-Up: Likely Cluster Workflows

User asked for the likely workflow and what the other cluster/new/old files do.

Commands run:
- Listed all files under `cluster_082024/`.
- Listed all files under `cluster_code/`.
- Searched cluster and results R files for paths, `date_run`, `save.image`, `load`, `num_sim`, `NMonte`, `AssetSim`, `Compare`, `June2024`, and `2022`.
- Listed file sizes/timestamps for `Common_Code`, `cluster_082024/Common_Code`, `Common_Data`, `cluster_082024/Common_Data`, and `cluster_082024/testing/test_code`.
- Inspected headers/line counts of asset simulation and result scripts.

Findings:
- `cluster_code/`: 38 2017 cluster plan scripts, configured for `/data/smithafe/Pension_CF_Model/`, `date_run <- "03062024_Adj"`, usually `NMonte <- 1`, saving `[PLAN]/[PLAN]_Compare_03062024_Adj.RData`.
- `cluster_082024/cluster_code_2022/`: 38 2022 update scripts, configured for `/nfs/sloanlab007/projects/pension_cf_model_proj/Pension_CF_Model/`, `date_run <- "2022_July2024"`, `plan_year <- 2022`, using `planchanges_main_2022_clean.xlsx`, usually `NMonte <- 1`, saving `[PLAN]/[PLAN]2022_July2024.RData`.
- `cluster_082024/Common_Code/asset_simulation.R`: old single-plan 2-asset asset simulation, hard-coded to CA10.
- `cluster_082024/Common_Code/asset_simulation_all.R`: old batch 2-asset asset simulation.
- `cluster_082024/Common_Code/asset_simulation_new.R`: new single-plan 5-asset correlated-real-return simulation, hard-coded to CA10.
- `cluster_082024/Common_Code/asset_simulation_all_new.R`: new batch 5-asset correlated-real-return simulation.
- `cluster_082024/Common_Data/`: cluster snapshot of common data, including 2022-specific files `inactive_supplement_2022.csv`, `planchanges_main_2022_clean.xlsx`, and `PPD_planlevel_main_updated.csv`.
- `cluster_082024/testing/`: copied tests, prototypes, and scenario outputs. Includes duplicated `testing/test_code/cluster_code_2022/` scripts, plus unit/prototype scripts such as `functions_cf_model_Test.R`, `testPVNC.R`, `UpdateEmployee_test.R`, and scenario files `NoGrowth*.RData`, `NoInflation.RData`.
- `Results/R Code/`: post-processing scripts. `errors_all_plans.R` summarizes validation errors from compare files; `fr_graph_all*.R` loads `AssetSim` files and plots funding-ratio forecasts.

Action:
- Added a "Likely full-run workflows" list to `Documentation/project_context.md` under section 6.1.

Correction:
- User objected that `project_context.md` should not contain speculative language such as "archived/staged" or "likely workflow."
- Updated `project_context.md` again to remove speculative wording and the "Likely full-run workflows" list.
- Current section 6.1 now documents only observed code locations and file conventions: top-level plan scripts, `cluster_code/`, `cluster_082024/cluster_code_2022/`, `asset_simulation_all.R`, `asset_simulation_all_new.R`, and `Results/R Code` post-processing scripts.

---

## 2026-06-01 Follow-Up: Deep 2017 vs 2022 Version Audit

User asked for a deeper check of the 2017 vs 2022 split across data, settings, scripts, and outputs before making a backup and reorganizing the work folder.

Actions:
- Created `Documentation/year_version_audit.md` as the main audit note. This file is intentionally separate from `Documentation/project_context.md` because it includes cleanup implications and interpretation.
- Created mechanical inventory files:
  - `Documentation/script_year_inventory.csv`
  - `Documentation/model_script_year_settings.csv`
  - `Documentation/data_artifact_inventory.csv`
  - `Documentation/rdata_inventory.csv`
- Ran R/readxl inspections of key workbook/csv inputs.
- Verified `Documentation/year_version_audit.md` exists and contains the audit summary.
- Attempted `git status --short` for the audit files; command failed because this workspace path is not inside a Git repository.

Key audit conclusions:
- There are at least three tracks:
  - 2017 baseline/local track: top-level plan scripts/folders, `plan_year <- 2017`, `[PLAN]_2017.xlsx`, root `Common_Data/PPD_planlevel_main.csv`, root `Common_Data/planchanges_main.xlsx`.
  - 2017 cluster track: `cluster_code/`, 38 plan scripts, `plan_year <- 2017`, `date_run` split between `02152024_best` and `03062024_Adj`, saves compare-style `.RData` files.
  - 2022 update track: `cluster_082024/cluster_code_2022/`, 38 plan scripts, `plan_year <- 2022`, `plan_start <- as.Date("2022-01-01")`, `plan_id <- paste0(plan, "_2022")`, `date_run <- "2022_July2024"`.
- Important hybrid finding: the 2022 scripts still read `fileName <- paste0(plan, "_2017.xlsx")`, so the 2022 track appears to combine 2022 common-data updates with 2017 plan-specific distribution workbooks.
- No `[PLAN]_2022.xlsx` files were found in the top-level plan folders.
- Root `Common_Data/ppd-data-latest.xlsx` covers selected plan IDs through 2021; `cluster_082024/Common_Data/ppd-data-latest.xlsx` covers selected plan IDs through 2023.
- `Common_Code/` and `cluster_082024/Common_Code/` are partly identical and partly substantively different. Do not merge them mechanically.
- Local search still found no full `*AssetSim*.RData`, no `*Compare_02152024_best.RData`, and no `*June2024.RData` outputs.
- Recommended cleanup direction from the audit: backup first, then separate the work folder by track before changing behavior: 2017 local, 2017 cluster, 2022 update, asset simulation/post-processing, source documentation, and tests/prototypes.

---

## 2026-06-01 Follow-Up: Local 2022 Deterministic and 2-Asset Test Runs

User decided to run only the 38 plans with 2022 update scripts for now, excluding `MA51` and `MO64`.

Actions:
- Patched the 38 scripts under `cluster_082024/cluster_code_2022/` for local relative paths:
  - hard-coded `/nfs/...` path removed.
  - scripts now set `current_dir` relative to their own location, so `cluster_082024/Common_Code` and `cluster_082024/Common_Data` are used.
  - `planFolder <- paste0("../", plan, "/")`, so top-level plan workbooks and outputs are used.
  - deterministic output name standardized to `[PLAN]/[PLAN]_detAL_2022_062026.RData`.
- Set `cluster_082024/cluster_code_2022/Main_PensionModel_MA50.R` from `NMonte <- 10` to `NMonte <- 1`.
- Ran a smoke test for CA10; output was created and validated as deterministic:
  - `CA10/CA10_detAL_2022_062026.RData`
  - `plan_year = 2022`
  - `NMonte = 1`
  - `Assets`, `AAL`, `cash_inflows`, and `cash_outflows` all `35 x 1`
  - `Assets` nonzero only in row 1 before asset simulation.
- Ran the 2022 deterministic scripts in parallel batches from a PowerShell terminal.

Current deterministic A/L status:
- 32 deterministic 2022 outputs exist:
  - `AZ06`, `AZ127`, `CA10`, `CA111`, `CA144`, `CA43`, `CA97`, `CA98`, `DC20`, `FL26`, `GA27`, `GA28`, `IL32`, `IL33`, `IL34`, `IN37`, `LA44`, `MA50`, `ME47`, `MO175`, `ND82`, `NJ73`, `NM74`, `NY83`, `OH88`, `OK134`, `OR91`, `PA93`, `RI96`, `SC100`, `SC99`, `TX108`.
- 6 deterministic 2022 scripts failed and have no `detAL` output:
  - `LA130`: initially diagnosed as `Calc_Inactive -> UpdateEmployeeCount`, subscript out of bounds. **Superseded 2026-06-08:** fetched Slurm logs show `Calc_Inactive` failed with `missing value where TRUE/FALSE needed`; a later June 5 rerun produced a valid detAL file.
  - `LA163`: initially diagnosed as `Calc_Inactive -> UpdateEmployeeCount`, subscript out of bounds. **Superseded 2026-06-08:** fetched Slurm logs show `Calc_Inactive` failed with `missing value where TRUE/FALSE needed`; a later June 5 rerun produced a valid detAL file.
  - `MI53`: non-numeric argument to binary operator.
  - `NJ71`: `ComputeAnnuity`, replacement has length zero.
  - `NY78`: `Main_Current`, missing value where TRUE/FALSE needed.
  - `PA92`: `Main_Current`, missing value where TRUE/FALSE needed.

Asset simulation script:
- Created `cluster_082024/Common_Code/asset_simulation_all_2022_062026.R`.
- It leaves the historical `asset_simulation_all.R` untouched.
- It auto-discovers `[PLAN]/[PLAN]_detAL_2022_062026.RData`.
- It writes `[PLAN]/[PLAN]_AssetSim_2022_2asset_062026.RData`.
- It computes 2-asset `AssetShare` from saved `planinfo` when `AssetShare` is absent:
  - risky assets = `COMDTotal_Actl + OtherTotal_Actl + PETotal_Actl + EQTotal_Actl + AltMiscTotal_Actl + HFTotal_Actl + RETotal_Actl`
  - bond share = `1 - risky share`.
- User manually set/kept `num_sim <- 100` for this test run; do not change it unless explicitly asked.
- The script now skips existing current outputs, skips invalid deterministic inputs, and logs skip reasons.

Current 2-asset simulation status:
- 24 asset simulation outputs exist with `num_sim = 100`, `Assets = 35 x 100`, `AAL = 35 x 100`, and populated asset rows `1:35`:
  - `AZ06`, `AZ127`, `CA10`, `CA111`, `CA43`, `CA97`, `DC20`, `FL26`, `GA27`, `GA28`, `IL32`, `IL33`, `IL34`, `ME47`, `MO175`, `ND82`, `NM74`, `OH88`, `OR91`, `PA93`, `RI96`, `SC100`, `SC99`, `TX108`.
- 7 existing deterministic outputs were skipped by asset simulation because `AAL` and/or cash-flow rows used by the asset loop contain `NA` or non-positive values:
  - `CA144`, `CA98`, `IN37`, `LA44`, `NJ73`, `NY83`, `OK134`.
- `MA50` was skipped by the current asset script because the saved deterministic output lacks `NormalCost`; its `AAL`, `Assets`, `cash_inflows`, and `cash_outflows` passed the asset-loop validity check. Since `Amortize <- FALSE`, `NormalCost` is not used in the current contribution rule, so a narrow future patch could require `NormalCost`/`discountrate` only when `Amortize <- TRUE`.

Important current limitation:
- The local 062026 run is only partially successful. It has 32 deterministic A/L outputs and 24 validated 2-asset simulation outputs, not full 38-plan coverage.

---

## 2026-06-02 Follow-Up: 062026 Run Output Folder

User asked to centralize run outputs instead of saving 062026 `.RData` files directly in each top-level plan folder.

Actions:
- Created canonical run folder `Results/Runs/062026/`.
- Created `Results/Runs/062026/_logs/`.
- Created one run subfolder for each of the 38 2022 plan scripts under `cluster_062026/cluster_code_2022/`.
- Copied existing top-level 062026 outputs into the new run folder without deleting the originals:
  - 32 deterministic A/L files copied to `Results/Runs/062026/[PLAN]/[PLAN]_detAL_2022_062026.RData`.
  - 24 2-asset simulation files copied to `Results/Runs/062026/[PLAN]/[PLAN]_AssetSim_2022_2asset_062026.RData`.
- Created `Results/Runs/062026/_manifest.csv` with one row per 38-plan 2022 script and current found/missing output status.
- Updated the 38 live A/L scripts in `cluster_062026/cluster_code_2022/` so future deterministic outputs save to `Results/Runs/062026/[PLAN]/`.
- Updated `cluster_062026/Common_Code/asset_simulation_all_2022_062026.R` so future asset simulations read deterministic inputs from `Results/Runs/062026/[PLAN]/`, write asset outputs beside them, and refresh `_manifest.csv`.
- Updated documentation references to the renamed folder `cluster_082024`.

Important guardrail:
- Do not modify `cluster_082024` code for the 062026 working-copy changes. The active current version is `cluster_062026`.

---

## 2026-06-02 Follow-Up: Python Results Analysis

User asked for Python analysis code with results shown in a notebook, covering the legacy R graph outputs and additional dynamics/distribution diagnostics.

Actions:
- Created `Results/Python Code/results_analysis.py`.
- Created display notebook `Results/Python Code/062026_results_analysis.ipynb`.
- The Python module reads canonical run files from `Results/Runs/062026/`.
- Initial implementation used local `Rscript` as a temporary bridge because Python RData readers were not installed yet. After installing `pyreadr` and `rdata`, the module now prefers clean `*_analysis.RData` companions and uses the Rscript bridge only as a fallback for full workspace files.
- The notebook includes:
  - run manifest/status tables,
  - average funding-ratio forecast like `fr_graph_all.R`,
  - per-plan funding-ratio forecast like `fr_graph_all_each.R`,
  - cash-flow dynamics,
  - terminal funding-ratio risk table,
  - terminal distribution plot,
  - probability of falling below funding-ratio thresholds,
  - plan-by-year heatmap,
  - asset and AAL dynamics.
- The Python plotting functions return figures and do not save output files.

Verification:
- Loaded one asset sim through the Python/R bridge and computed forecast/risk summaries.
- Rendered non-saving matplotlib smoke plots.
- Loaded two plans (`AZ06`, `CA10`) and rendered average forecast, threshold-risk, and heatmap plots.
- Notebook JSON opened successfully with `nbformat`.

2026-06-02 update:
- Installed Python packages `pyreadr==0.5.6` and `rdata==1.0.0`.
- Direct `pyreadr` loading failed on the existing full asset simulation `.RData` files because they are full `save.image()` workspaces containing unsupported objects/functions.
- Direct `rdata` conversion also failed on the full workspaces.
- A clean data-only `.RData` containing only matrices/scalars can be read by `pyreadr`.
- Updated `Results/Python Code/results_analysis.py` to prefer clean `*_analysis.RData` companion files and fall back to the Rscript bridge for full workspace files.
- Generated 24 clean analysis companion files under `Results/Runs/062026/[PLAN]/[PLAN]_AssetSim_2022_2asset_062026_analysis.RData`.
- Updated the notebook to call `prepare_analysis_exports()` before loading, so new asset sims can get clean companions automatically.

2026-06-02 update:
- Reorganized result post-processing code into language-specific folders.
- Moved legacy R result scripts to `Results/R Code/`:
  - `errors_all_plans.R`
  - `fr_graph_all.R`
  - `fr_graph_all_each.R`
- Moved Python analysis files together into `Results/Python Code/`:
  - `results_analysis.py`
  - `062026_results_analysis.ipynb`
- Removed the now-empty old split folders.
- Updated the notebook import-discovery cell so it works from either the project root or `Results/Python Code/`.

---

## 2026-06-02 Follow-Up: 38 to 24/25 Diagnostic

User asked why the 062026 run dropped from 38 active 2022 plans to 24 asset outputs and wanted a diagnostic/fix pass.

Current status after this pass:
- `Results/Runs/062026/_manifest.csv` now shows 25 asset outputs:
  - 24 existing outputs.
  - 1 newly saved output: `MA50`.
- 7 deterministic A/L files exist but are invalid for the asset loop:
  - `CA144`, `CA98`, `IN37`, `LA44`, `NJ73`, `NY83`, `OK134`.
- 6 deterministic A/L files are still missing and need rerunning:
  - `LA130`, `LA163`, `MI53`, `NJ71`, `NY78`, `PA92`.

Diagnosis:
- The 7 asset-stage invalid deterministic files all had missing 2022 `PayrollGrowthAssumption`, so `WageGrowth` became `NA` and propagated through active-member AAL/cash-flow arrays.
- `MA50` had valid deterministic `AAL`, `Assets`, `cash_inflows`, and `cash_outflows`, but the asset runner required `NormalCost` even though `Amortize <- FALSE`.
- `LA130` and `LA163` were initially diagnosed as failing because `Calc_Inactive` could exceed its 1,000-iteration workspace before convergence, producing `subscript out of bounds`. **Superseded 2026-06-08:** fetched Slurm logs show `Calc_Inactive` failed with `missing value where TRUE/FALSE needed`; later June 5 reruns produced valid detAL files.
- `MI53` failed because `MI53_2017.xlsx` has duplicated text headers in `retdist!B2` and `retdist!F2`; the old range included those as data.
- `NJ71` failed because it used `Inflation <- PPD$inflation`, but `PPD_planlevel_main_updated.csv` has no `inflation` column.
- `NY78` and `PA92` failed because 2022 `InactiveVestedMembers` is `NA` while `inactive_adj == 1`.

Fixes applied in `cluster_062026` only:
- Added numeric fallback helpers in `cluster_062026/Common_Code/functions_cf_model.R`:
  - `first_nonmissing_numeric()`
  - `get_legacy_ppd_value()`
  - `get_inactive_member_count()`
- Increased `Calc_Inactive()`'s fixed-point workspace from 1,000 to 5,000 iterations and added a max-iteration guard/warning in `cluster_062026/Common_Code/bucketfill_cf_model.R`.
- Updated affected wage-growth scripts to use:
  - `PayrollGrowthAssumption -> WageInflation -> legacy PPD wage_inf -> InflationAssumption_GASB`.
- Updated `NJ71` inflation to fall back to legacy PPD inflation and stop if both current and legacy inflation are missing.
- Updated `NY78` and `PA92` to fall back to legacy inactive counts:
  - `NY78 = 8,590`
  - `PA92 = 24,515`
- Updated `MI53` retiree ranges from `B1:B17`/`F1:F17` to `B2:B18`/`F2:F18`.
- Updated `cluster_062026/Common_Code/asset_simulation_all_2022_062026.R` so `NormalCost` and `discountrate` are required only when `Amortize <- TRUE`.
- Reran the asset script and saved `Results/Runs/062026/MA50/MA50_AssetSim_2022_2asset_062026.RData`.
- Regenerated clean Python analysis companion files for all 25 current asset outputs, including MA50.

Validation:
- Installed local R package `readxl` for R 4.5.3.
- Added and ran `Results/Runs/062026/_diagnostic_validation.R`.
- Validation log: `Results/Runs/062026/_diagnostic_validation.log`.
- Validation confirmed:
  - all edited R files parse,
  - all 11 missing-payroll-growth plans resolve to numeric `WageGrowth`,
  - `NJ71` resolves to numeric inflation,
  - `NY78` and `PA92` resolve to numeric inactive counts,
  - `MI53` corrected retiree ranges produce 16 numeric rows each.
- A local full `MI53` rerun passed the old type-error point but was stopped after about 8.5 minutes without producing deterministic output. Use the normal batch/cluster path for full deterministic reruns.

Remaining follow-up:
- Rerun deterministic A/L for:
  - `CA144`, `CA98`, `IN37`, `LA44`, `NJ73`, `NY83`, `OK134`,
  - `LA130`, `LA163`, `MI53`, `NJ71`, `NY78`, `PA92`.
- Then rerun `cluster_062026/Common_Code/asset_simulation_all_2022_062026.R`.
- If those A/L reruns pass, expected asset coverage is complete for the
  canonical plan list.

2026-06-02 update:
- Added Engaging/Slurm workflow scripts under `cluster_062026/slurm/`.
- Files:
  - `062026_rerun_plans.txt`: the 13 plans needing deterministic reruns.
  - `setup_r_packages_062026.R`: installs/checks `readxl` in the user's R library.
  - `run_detal_array_062026.sbatch`: Slurm array job for deterministic A/L reruns.
  - `run_asset_sim_062026.sbatch`: Slurm job for the 062026 asset simulation.
  - `submit_062026_workflow.sh`: submits the deterministic array and then submits the asset sim with an `afterok` dependency.
  - `README_062026_engaging.md`: cluster run instructions.
- Shell syntax checks passed locally via `bash -n`.
- Submit from the project root on Engaging with:
  - `bash cluster_062026/slurm/submit_062026_workflow.sh`
- Optional environment variables:
  - `PARTITION`, `ACCOUNT`, `QOS`
  - `MAX_PARALLEL` for the array concurrency
  - `R_MODULE` if Engaging requires loading a specific R module

---

## 2026-06-02 Update: 38-Plan 062026 Pipeline

User clarified that the 062026 workflow should be a polished pipeline for all
processes, not a one-off rerun only for the missing/problem plans.

Actions:
- Kept the active simulation code in `cluster_062026`; did not modify
  `cluster_082024`.
- Generalized wage-growth, inflation, and inactive-member scaling across all 38
  active `cluster_062026/cluster_code_2022/Main_PensionModel_*.R` scripts.
- Added common helpers in `cluster_062026/Common_Code/functions_cf_model.R`:
  - `get_wage_growth_assumption()`
  - `get_inflation_assumption()`
  - `scale_inactive_members()`
- These helpers are input guardrails, not a replacement for the simulation
  model. They centralize fallback choices that were previously missing or
  one-off in specific scripts.
- Added repeatable run-control files under `Pipeline/062026/`:
  - `plans_38.txt`: previous plan-list snapshot from the earlier active run boundary.
  - `run_062026_local.ps1`: local parallel deterministic runner with optional
    asset simulation and Python analysis export.
  - `setup_engaging_r.sh`: Engaging R package check/install helper.
  - `slurm_detal_array_062026.sh`: Engaging Slurm job array, one plan per task.
  - `slurm_asset_062026.sh`: dependent Engaging asset-simulation job.
  - `submit_062026_slurm.sh`: submits the deterministic array and dependent
    asset job.
  - `remote_062026.ps1`: local terminal wrapper for packaging, uploading,
    submitting, checking status, fetching results, and exporting analysis files.
  - `validate_062026_assumptions.R`: all-plan audit of actual assumption sources.
- Added `Documentation/062026_run_pipeline.md` with local and Engaging commands.
- Updated `Documentation/project_context.md` to document `Pipeline/062026/`,
  the common helpers, and the current 25-output asset status after MA50 was
  fixed.

Important use notes:
- Local dry run:
  - `.\Pipeline\062026\run_062026_local.ps1 -Plans all -Throttle 4 -RunAsset -ExportAnalysis -DryRun`
- Local full run:
  - `.\Pipeline\062026\run_062026_local.ps1 -Plans all -Throttle 4 -RunAsset -ExportAnalysis`
- Engaging submit from the remote project root:
  - `bash Pipeline/062026/submit_062026_slurm.sh`
- Local wrapper upload/submit/fetch examples are in
  `Documentation/062026_run_pipeline.md`.
- Assumption audit:
  - `Rscript Pipeline/062026/validate_062026_assumptions.R`
- Validation run completed locally:
  - PowerShell scripts parse.
  - Bash scripts pass `bash -n` (Git Bash emitted harmless local `/tmp` warnings).
  - `validate_062026_assumptions.R` parsed 41 R files and wrote
    `Results/Runs/062026/_diagnostic_assumption_audit.csv`.
  - All 38 plans have audit `status = ok`.
  - Current source counts: 27 wage-growth values from
    `PayrollGrowthAssumption`, 7 from `WageInflation`, 4 from legacy 2017
    `wage_inf`; 37 inflation values from current GASB inflation, 1 from legacy
    inflation (`NJ71`); inactive scaling uses 26 current inactive counts, 10
    `actives_tot * inactive_adj`, and 2 legacy inactive counts (`NY78`,
    `PA92`).
  - Local runner dry-run for `LA130,LA163` printed the expected deterministic,
    asset, and analysis-export commands.
  - `remote_062026.ps1 -Action package` completed and wrote a compact upload
    bundle to `Results/Runs/062026/_remote/state_pension_model_062026_bundle.tar.gz`.

Pipeline performance baseline:
- The current 062026 Engaging pipeline is intentionally conservative.
- Deterministic A/L runs as a Slurm array with one plan per task.
- Default concurrency is `MAX_PARALLEL=8`, so the 38-plan set runs in roughly
  five waves if all tasks start promptly.
- Each deterministic task requests 1 CPU, 8 GB memory, and 12 hours.
- Each deterministic task independently loads R, common code, PPD data, and the
  relevant plan workbook.
- The asset simulation is one dependent Slurm job after the deterministic array
  succeeds. It loops through plans sequentially in one R process.
- Current asset simulation setting is `num_sim <- 100`, not 10,000.
- Main tuning knob for the current workflow is `MAX_PARALLEL`; future runs could
  try 12 or 16 if queue policy and filesystem behavior are comfortable.
- Future optimization candidates: parallelize asset simulation by plan, rerun
  only missing/problem plans via `SKIP_EXISTING_DETAL=1` or a smaller plan list,
  increase `num_sim` only after the canonical plan workflow is stable, and
  consider reducing repeated data-read overhead only after the bigger workflow
  issues are settled.

2026-06-02 operational follow-up:
- User ran the 062026 workflow on Engaging with the Miniforge/conda R fallback.
- Initial Slurm array failed immediately because job scripts inferred
  `PROJECT_ROOT` from Slurm's copied/spooled script path, causing attempts to
  create `Results/` in an unwritable location.
- Patched `Pipeline/062026/slurm_detal_array_062026.sh` and
  `Pipeline/062026/slurm_asset_062026.sh` to prefer exported `PROJECT_ROOT` and
  `SLURM_SUBMIT_DIR`, and patched `submit_062026_slurm.sh` to export
  `PROJECT_ROOT` and `PIPELINE_DIR`.
- Added opt-in follow mode: set `FOLLOW=1 FOLLOW_INTERVAL=30` for
  `submit_062026_slurm.sh`, or use `remote_062026.ps1 -Follow -FollowInterval
  30`.
- Added `remote_062026.ps1 -Action inventory` to check server-side file counts
  without relying on local fetched files. Inventory distinguishes plan folders,
  detAL outputs, AssetSim outputs, and Python analysis companions.
- Fixed `remote_062026.ps1 -Action export-analysis` quoting so Python receives
  `Results/Python Code` and run tag `062026` as strings.
- Remote inventory after deterministic runs showed 36 detAL files and zero
  AssetSim files; the asset job had not produced logs or manifest because the
  earlier dependency-run asset job did not run successfully.
- User manually submitted the asset job with exported `PROJECT_ROOT` and
  `PIPELINE_DIR`; it produced 36 asset files and `_manifest.csv`.
- At that point in the timeline, the fetched/exported result set had incomplete
  detAL, AssetSim, and Python-analysis coverage, and `LA130`/`LA163` were
  reported as missing. **Superseded 2026-06-08:** later local inspection found
  deterministic files for those plans. Do not use this dated note for current
  output coverage; re-inventory the output folder or remote run.
- `Documentation/062026_run_pipeline.md` now documents the pipeline contract,
  uploaded contents, execution stages, follow mode, asset-stage behavior,
  inventory/fetch/export order, current output-status checks, and
  troubleshooting notes.

---

## 2026-06-03 Follow-Up: Notebook Expansion Against Lenney et al.

User asked to expand `Results/Python Code/062026_results_analysis.ipynb` using
the draft's list of Lenney et al. figures/tables to reproduce, modify, or mark
as future work.

Actions:
- Installed Python packages:
  - `pyreadr==0.5.6`
  - `pypdf==6.12.2`
- Did not modify `Results/Python Code/results_analysis.py` or any R simulation
  code.
- Used `pypdf` to inspect the attached Brookings PDF locally, including Table 1,
  Table 2, and figures around exhaustion/stabilization.
- Expanded `Results/Python Code/062026_results_analysis.ipynb` with notebook-only
  cells.
- Smoke-executed the notebook code path from Python. It loaded 36 plans, built
  the Table 1-style summary, and computed exhaustion rows without errors.

Notebook additions implemented:
- Lenney update roadmap table showing implemented/partly implemented/deferred
  status for each requested item.
- Table 1 analogue:
  - assets/liabilities,
  - unfunded liabilities/payroll,
  - total pension contributions/payroll,
  - active members/retired members,
  - projected active-member growth over 30 years using the current model's
    fixed `PopulationGrowth = 0.01`,
  - unweighted and denominator-weighted means/SDs,
  - loaded 062026 sample plus a 2022 PPD comparison where fields exist.
- Historical official GASB funded-ratio figure for the loaded 062026 plans,
  equal-weighted and liability-weighted.
- Aggregate assets, AAL, unfunded AAL, and aggregate funded-ratio dynamics.
- Liability-weighted asset-exhaustion timing:
  - expected liability share and dollar liability value in plans exhausting
    over 1-10, 11-20, 21-30, 31-35, and never-by-35-year bins.
- Plan-level exhaustion table with probabilities of exhausting by 10, 20, 30,
  and 35 years.
- Cross-sectional Figure 10 analogue:
  - 20-year exhaustion probability against official 2022 funded ratio,
  - bubble size by liabilities,
  - regression line,
  - labels for highest-risk plans.
- Model AAL vs CAFR AAL validation scatter and percent-difference histogram.

2026-06-03 wording cleanup:
- Revised the notebook's visible markdown and plot labels so the analysis reads
  stand-alone rather than assuming the reader has Lenney et al. open.
- Removed visible "Lenney", "analogue", and "loaded plans" wording from the
  notebook analysis sections.
- Expanded each section intro to state what the following table/figure shows.
- Clarified weighting in the summary-statistics section:
  liabilities for assets/liabilities, payroll for payroll ratios, retired
  members for active/retired, and active members for projected active-member
  growth.
- Replaced "loaded plans" phrasing with "36-plan 062026 analysis sample" or
  equivalent explicit wording.
- Smoke-executed the notebook again after the wording pass; it loaded 36 plans,
  produced 10 summary-stat rows, and produced 36 exhaustion-summary rows.

2026-06-03 run-agnostic wording cleanup:
- User clarified that the notebook should not treat `062026` as a substantive
  sample label; it is only a run-folder tag.
- Revised notebook visible markdown and labels again to remove date-run and
  fixed-count phrasing such as `062026 analysis sample` and `36-plan`.
- Notebook now refers generically to the selected run, the plans represented in
  that run, and the run manifest.
- Left `RUN_TAG = "062026"` only as the technical folder selector under
  `Results/Runs/`; users can change it for another run.
- Smoke-executed the notebook after this pass; it loaded 36 plans from the
  selected run, produced 10 summary-stat rows, and produced 36
  exhaustion-summary rows.

2026-06-03 summary-stat finite-ratio fix:
- User found `inf` values and a pandas `RuntimeWarning: invalid value
  encountered in subtract` in the notebook summary-statistics table.
- Cause: some broad PPD 2022 comparison rows have zero denominators such as
  zero payroll or zero retired-member counts, so raw division created infinite
  ratio values. The weighted stats already excluded nonfinite values, but the
  unweighted stats did not.
- Updated the notebook helper code only:
  - added finite numeric coercion,
  - added `safe_ratio()` to compute ratios only when denominators are positive
    and finite,
  - made unweighted summary stats count only finite values,
  - applied the same safe-ratio rule to historical official funded ratios.
- Updated the summary-statistics markdown to state that ratios with nonpositive
  or nonfinite denominators are treated as missing for the affected metric.
- Smoke execution confirmed:
  - no `inf` values in `table1_like`,
  - no pandas nanops subtract warning,
  - 10 summary-stat rows and 36 exhaustion-summary rows.

2026-06-03 summary-stat comparison removal:
- User clarified that the modeled plan universe should not be treated as a
  sample to compare against a broader PPD sample in the notebook. The simulated
  plans are intended to be all project plans with outputs; missing plans are
  operational failures to fix, not a sampling design.
- Removed the PPD 2022 comparison group from the summary-statistics table in
  `Results/Python Code/062026_results_analysis.ipynb`.
- Summary statistics now report only baseline characteristics of the modeled
  plans using GASB/PPD inputs saved with the result files.
- The PPD workbook remains used for historical official funded-ratio plots.
- Smoke execution confirmed:
  - baseline summary has 5 rows,
  - no `inf` values,
  - no pandas nanops subtract warning,
  - 36 exhaustion-summary rows.

2026-06-03 aggregate-summary terminal-year fix:
- User found warnings in the aggregate asset/AAL section:
  - `RuntimeWarning: Mean of empty slice`
  - `RuntimeWarning: All-NaN slice encountered`
- Diagnosis: the aggregate AAL matrix is positive through 2055, but the final
  2056 row has aggregate AAL equal to zero. This is an unpopulated/placeholder
  liability row, and including it makes funded ratios undefined and causes the
  final aggregate balance-sheet plot to show a misleading drop in AAL to zero.
- Updated notebook helper `aggregate_summary()` to drop years where aggregate
  AAL is not positive before computing funded-ratio means and quantiles.
- Updated the aggregate-section markdown to state that years with nonpositive
  aggregate AAL are excluded because the funded-ratio denominator is undefined.
- Smoke execution confirmed:
  - aggregate summary now has 34 rows,
  - year range is 2022 through 2055,
  - no mean-empty warnings,
  - no all-NaN quantile warnings.

Deferred/to-do items recorded in the notebook:
- AAA-discounted funded ratios need external AAA-discounted liability data or a
  liability revaluation workflow. Current artifacts support official GASB ratios
  only.
- Contribution-rate increases for 0.5%, 1%, and 3% shortfall-probability targets
  require new asset/counterfactual runs. Current `num_sim = 100` has a 1
  percentage-point probability grid, so a 0.5% target is not resolvable.
- Contribution counterfactuals should store return shocks or rerun simulations
  with explicit contribution-policy parameters; current saved asset outputs are
  not enough for paper-quality post-hoc stabilization scenarios.
- Alternative investment-strategy and waiting-period stabilization scenarios
  require new scenario runs.
- GDP-normalized figures require a GDP series and an agreed aggregation/scaling
  convention.
- Reform counterfactuals require no-new-tier/benefit-reform simulations and/or
  contribution-rate history since 2007.
- Final tables need whatever the current canonical run inventory says is
  complete; do not infer current coverage from this dated notebook note.

2026-06-03 added currently doable AAA/GDP/reform sections:
- Per user instruction, inserted new cells in
  `Results/Python Code/062026_results_analysis.ipynb` immediately above
  `## Items Requiring New Data Or New Runs`; existing notebook cells were left
  unchanged.
- Added `## AAA-Discounted Cash-Flow PV Funded Ratios`:
  - downloads FRED `AAA` and uses the base-year average AAA corporate yield,
  - discounts saved deterministic `cash_outflows` vectors over the model
    horizon,
  - reports aggregate and plan-level funded ratios using an exploratory
    projected-benefit-cash-flow PV denominator,
  - labels this clearly as not a full model-consistent AAA AAL revaluation.
- Added `## GDP-Normalized Aggregate Burden`:
  - downloads FRED `GDP`,
  - uses observed nominal GDP only through the model base year,
  - projects post-base-year nominal GDP with model-consistent growth
    `(1 + average model inflation) * (1 + 0.01 population growth) - 1`,
  - reports aggregate assets, AAL, and unfunded AAL as percent of projected GDP.
- Added `## Descriptive Reform And Tier Rule Summary`:
  - reads `cluster_062026/Common_Data/planchanges_main_2022_clean.xlsx`,
  - reshapes tier-rule columns into unique plan rules,
  - summarizes earliest-to-latest changes in benefit factor, COLA, retirement
    age, vesting, salary averaging, and contribution fields,
  - merges those descriptive rule changes with current exhaustion-risk metrics,
  - states that this is descriptive only, not a no-reform counterfactual.
- Focused smoke test passed:
  - AAA PV section produced 36 plan rows,
  - GDP-normalized section produced 34 valid projection-year rows,
  - reform section matched 36 modeled plans.

2026-06-03 FRED API switch:
- User requested official FRED API usage and said they will provide their key.
- Updated only the newly inserted FRED helper cell in
  `Results/Python Code/062026_results_analysis.ipynb`.
- Removed `fredgraph.csv` URL usage.
- Added `FRED_API_KEY` support:
  - first uses an existing notebook variable if set,
  - otherwise uses the `FRED_API_KEY` environment variable,
  - raises a clear error if no key is available.
- New helper calls
  `https://api.stlouisfed.org/fred/series/observations` with
  `file_type=json`.
- Updated the AAA and GDP markdown cells to state that FRED data come from the
  official API and that `FRED_API_KEY` must be set.
- Syntax check passed for the modified notebook code cells. The FRED API calls
  were not executed because no API key is available in the current session.

---

## 2026-06-05: R-to-Python Line-by-Line Verification, Generic Runner, and Folder Reorganization

### R-to-Python Verification

All functions in `Cluster Code/cluster_062026/Python Code/bucketfill_cf_model.py` and `functions_cf_model.py` were verified line-by-line against their R counterparts. Two bugs were found and fixed:

1. **`UpdateRetirementBenefit` (functions_cf_model.py):** Two-step in-place update (`-=` then `+=`) produced a different result from R's single RHS expression because the second operation used the already-modified value. Fixed: copy original array before assignment so both operations use the pre-step value.

2. **`Calc_Inactive` (bucketfill_cf_model.py):** `NyearFullBenefit_f` could be a float; Python slice requires int. Fixed: `nfb = int(NyearFullBenefit_f)`.

After these fixes, AZ06 Python output was validated as bit-identical to R across all 35 projection years (max_abs=0, max_rel=0.000000% on AAL, NormalCost, cash_outflows, cash_inflows).

### Generic Python Runner (`Main_PensionModel.py`)

Created `Cluster Code/cluster_062026/Python Code/Main_PensionModel.py` â€” a single generic runner for 37 standard plans (MA50 excluded). Key design:
- Accepts plan ID as a command-line argument: `python "Python Code/Main_PensionModel.py" AZ06`
- Embeds `AVAILABLE_DATA` dict (9-bool vector per plan) derived from R scripts
- Embeds `CONTRIB_RATE_NA_CHECK` set (7 plans where contribution rates may be NA): AZ127, CA144, CA98, IL32, IN37, LA130, LA44
- NA fallback for contribution rates uses `(contrib_EE_regular * 1000) / sum(active * BaseWage_2d)`, placed after `active` and `BaseWage` are constructed
- Outputs plan pkl file to `Results/Runs/062026/[PLAN]/[PLAN]_detAL_2022_062026.pkl`

MA50 excluded: different risk-free-rate formula, missing `*1000` asset multiplier, backward tier logic, `++` syntax error, no NormalCost output.

### Plans/ Folder Reorganization

Moved all 40 plan data folders (AZ06, AZ127, â€¦, TX108, MA51, MO64) from the project root into a new `Plans/` subfolder. Updated all code references:
- R scripts (`Cluster Code/cluster_062026/cluster_code_2022/Main_PensionModel_*.R`, 38 files): `../[PLAN]/` â†’ `../../Plans/[PLAN]/` for planFolder; `dirname(current_dir)` â†’ `dirname(dirname(current_dir))` for runFolder
- Python scripts (`Main_PensionModel.py`, `Main_PensionModel_AZ06.py`): plan_folder updated to `../../Plans/[PLAN]`; run_folder updated to go two levels up from cluster_062026
- `validate_az06.py`: ROOT updated to go three levels up from Python Code/

### Cluster Code/ Folder Reorganization

Moved `cluster_062026`, `cluster_082024`, and `cluster_code` from project root into a new `Cluster Code/` subfolder. Updated code references:
- Same 38 R scripts: runFolder depth already corrected by the Plans/ path changes above
- `validate_az06.py`: ROOT path already corrected

### Summary of Current Code Locations

| Item | Old path | New path |
|---|---|---|
| Plan data | `[PLAN]/` | `Plans/[PLAN]/` |
| Active R scripts | `cluster_062026/cluster_code_2022/` | `Cluster Code/cluster_062026/cluster_code_2022/` |
| Python scripts | `cluster_062026/Python Code/` | `Cluster Code/cluster_062026/Python Code/` |
| Common R helpers | `cluster_062026/Common_Code/` | `Cluster Code/cluster_062026/Common_Code/` |
| Archived cluster | `cluster_082024/` | `Cluster Code/cluster_082024/` |
| 2017 cluster | `cluster_code/` | `Cluster Code/cluster_code/` |

---

## 2026-06-08 Correction: LA130/LA163 062026 Status

The earlier timeline entries correctly identify `LA130` and `LA163` as the last
problem plans in the 062026 run, but the stated failure mode and current status
needed correction.

Correct historical Slurm error:
- The fetched Engaging logs
  `Results/Runs/062026/_logs/slurm_detal_15336656_17.out` and
  `Results/Runs/062026/_logs/slurm_detal_15336656_18.out` show both plans
  failing in `Calc_Inactive` with:
  `missing value where TRUE/FALSE needed`.
- Earlier diagnostic text saying `Calc_Inactive -> UpdateEmployeeCount` with
  `subscript out of bounds` should be treated as stale/incorrect for the fetched
  Slurm run.

Observed local state during the 2026-06-08 check:
- `LA130` and `LA163` now have deterministic A/L files dated 2026-06-05:
  - `Results/Runs/062026/LA130/LA130_detAL_2022_062026.RData`
  - `Results/Runs/062026/LA163/LA163_detAL_2022_062026.RData`
- Their June 5 deterministic logs completed after roughly 9-10 minutes each,
  with warnings but no fatal error.
- Direct R inspection confirmed both files contain `Assets`, `AAL`,
  `cash_inflows`, `cash_outflows`, and `NormalCost` as `35 x 1` objects with no
  `NA` or nonfinite values; both have `plan_year = 2022` and `NMonte = 1`.
- Local file inventory at that moment showed deterministic A/L files for all
  canonical plans, and fewer asset simulation / Python analysis companion files.
- This dated inventory must not be treated as durable project state. If the
  simulations or export pipeline are rerun, re-inventory the output folder
  rather than trusting this note.
- `Results/Runs/062026/_manifest.csv` should be treated as an asset-stage
  manifest that can lag deterministic outputs until the asset stage is rerun.

---

## 2026-06-08 Python Translation Next-Step Buildout

User clarified the Python priority is the precise R-to-Python simulation
translation track, ignoring MA50 for now.

Implemented code additions:
- Updated `Cluster Code/cluster_062026/Python Code/Main_PensionModel.py` and
  `Main_PensionModel_AZ06.py` so Python detAL `.pkl` outputs include the
  asset-stage inputs normally available from R `save.image()` workspaces:
  `Assets`, identifiers, `Nyear`, `NMonte`, `Inflation`, `rf`, `discountrate`,
  and `planinfo`.
- Added `Cluster Code/cluster_062026/Python Code/asset_simulation.py`,
  a line-by-line methodology translation of the active 2-asset R asset
  simulation. It loads Python detAL `.pkl` files, runs the same contribution and
  return loop, writes Python `.pkl` asset outputs, writes parquet bundles, and
  writes `_manifest_python.csv`.
- Added `Cluster Code/cluster_062026/Python Code/run_simulation.py`, a launcher
  that selects plans, stages (`detal`, `asset`, or `both`), parallel worker
  count, dry runs, skip-existing behavior, and asset `num_sim`. The launcher
  shells out to the translated scripts and does not implement model equations.
- Added `Cluster Code/cluster_062026/Python Code/compare_r_python.py`,
  a broader R-vs-Python comparison utility for top-level matrices, tier result
  lists, retiree result lists, and scalars.
- The Python code should treat `run_tag` as the output/run label. `plan_year`
  is model data selection and legacy R filename lookup, not a second Python
  output label.
- Extended `Results/Python Code/results_analysis.py` with parquet output
  discovery and `load_plan_result_parquet()`. Existing RData loading remains
  the default.
- Created `Results/Python Code/results_analysis_parquet.ipynb`, a
  cleared-output notebook copy that uses the same analysis flow but calls
  `load_run_results(..., source="parquet")`.

Validation performed:
- AST parse checks passed for the modified/new Python scripts.
- Launcher dry-run for `AZ06,CA10` with `--stage both --parallel 2 --num-sim 3`
  printed expected deterministic and asset commands.
- Synthetic asset-stage smoke test passed: a small deterministic `.pkl` produced
  Python asset `.pkl` and parquet bundle outputs with expected matrix shapes.
- Parquet loader smoke test passed on a tiny synthetic bundle.

Validation caveats:
- A full local `AZ06` deterministic rerun did not finish within a 3-minute
  command timeout, so current broad R-vs-Python validation still needs a normal
  longer run or cluster run.
- The existing `AZ06_detAL_2022_062026.pkl` is an older pre-patch pickle and
  does not unpickle cleanly in the current local pandas/numpy environment. It
  should be regenerated before using the new asset stage or comparison utility.
- Exact stochastic asset-path equality against R is not meaningful unless both
  sides use identical return shocks. The active R asset script calls `rnorm()`
  and does not save shocks; Python's RNG is not R's RNG. The translated asset
  script mirrors the equations and draw order, not R's RNG internals.

---

## 2026-06-08 Python Engaging Pipeline And Comparison Results

### Python Engaging pipeline

Added `Cluster Code/cluster_062026/Python Code/engaging/` with:
- `remote_python_run.ps1` â€” local wrapper (package/upload/upload-submit/submit/status/inventory/fetch) for running the Python pipeline on Engaging. Run tag is the full output label (e.g., `062026_py`). Python environment configured via `-PythonModule`, `-CondaModule`, `-CondaEnv`, or `-Venv`.
- `submit_slurm.sh` â€” submits a detAL Slurm array and a dependent asset Slurm array.
- `slurm_detal_array.sh` / `slurm_asset_array.sh` â€” Slurm array scripts, one plan per task.
- `engaging_python_env.sh` â€” Python environment activation helper sourced by Slurm scripts.

Slurm logs: `Results/Runs/[RUN_TAG]/_logs/slurm_py_detal_[jobid]_[taskid].out/err` and `slurm_py_asset_*`.

### Engaging pipeline bug fixes (2026-06-08, this session)

Three bugs found and fixed in the Slurm array scripts:

1. **Process substitution failure** (`slurm_detal_array.sh`, `slurm_asset_array.sh`): `exec > >(tee -a "${LOG_FILE}") 2>&1` fails silently on Engaging because `/dev/fd` process substitution is not available in the Slurm execution environment. With `set -euo pipefail` the script exited immediately with empty logs. Fixed to `exec >> "${LOG_FILE}" 2>&1`.

2. **Wrong CLUSTER_DIR path in Slurm jobs** (both scripts): `CLUSTER_DIR` was derived from `BASH_SOURCE[0]`, which in a Slurm job points to the job spool directory, not the project. Fixed to derive from `PROJECT_ROOT` (exported by `submit_slurm.sh`): `CLUSTER_DIR="${PROJECT_ROOT}/Cluster Code/cluster_062026"`.

3. **Missing Python packages** (`engaging_python_env.sh`): miniforge/24.3.0-0 base does not include `openpyxl` (needed for `pd.read_excel`) or `pyarrow` (needed for parquet output). Fixed by adding `"${PYTHON_BIN}" -m pip install --user --quiet openpyxl pyarrow` at the end of `setup_python_env()`.

Confirmed working environment on Engaging: `miniforge/24.3.0-0` â†’ Python 3.10. Use `-CondaModule "miniforge/24.3.0-0"` in submit commands.

**Current Engaging environment (confirmed working):** `miniforge/24.3.0-0` â†’ Python 3.10. Required packages `openpyxl` and `pyarrow` are not in the base environment; `engaging_python_env.sh` now installs them via `pip install --user` if not already present. `submit_slurm.sh` now calls `setup_python_env` once on the login node before submitting array jobs to avoid a race condition where parallel tasks install simultaneously and corrupt the pyarrow installation.

---

~~RESOLVED â€” see 2026-06-09 sections below~~

### Historical note: `py_retirefix` was a temporary test tag

`py_retirefix` and `062026_py` (6-plan subset) were intermediate debugging runs used during the translation validation phase. They are not canonical outputs. The canonical run tags are `062026` (R) and `062026_py` (Python, full 37 plans). Disregard any earlier references to `py_retirefix` as a production run.

---

## 2026-06-08 R-vs-Python Translation â€” Final 6-Plan Comparison And OH88 Fix

### `py_local` comparison results

Ran all 6 test plans locally (more powerful machine than Engaging) after `py_retirefix` changes, saving pkl files to `Results/Runs/py_local/`. Comparison stored in `Results/Runs/py_local/_compare_detal_vs_r.csv`.

Results:
- **AZ06**: all `ok`, max_rel ~1e-15 âœ“
- **CA10**: all `ok`, max_rel ~3-4e-15 âœ“ (previously 5â€“40% â€” resolved by py_retirefix)
- **CA144**: all `ok`, max_rel ~3-4e-15 âœ“ (previously wrong â€” resolved)
- **IL32**: all `ok`, max_rel ~2-4e-15 âœ“ (previously wrong â€” resolved)
- **MI53**: all `ok` except `Percent_difference` mismatch (max_abs=0.749, max_rel=2.44) â€” comparison artifact only; R's `CAFR_AAL` is `NA` for MI53, Python stores 0, causing division-by-zero in the ratio. All simulation matrices match.
- **OH88**: `MainRes_Tier2__1` through `__5` all `mismatch` with max_rel=1.0; aggregate `AAL`, `cash_inflows`, `cash_outflows`, `NormalCost` also mismatch ~0.05%. Tiers 1 and 3â€“6 match at floating-point precision.

### OH88 Tier 2 bug root cause

OH88 has 6 tiers with `tier_serivce = [59, 41, 41, 40, 39, 38]` (Python 0-based). Tiers 2 and 3 started only 6 months apart (1980-07-01 vs 1981-01-01); both round to 41 years of service by `plan_start = 2022-01-01`, giving `ts[1] == ts[2] == 41`.

Python's `CreateTiers` calls:
```python
g.active_t2 = _zero_outside(active, ts[2], ts[1])  # = _zero_outside(active, 41, 41)
```

`_zero_outside(active, 41, 41)` zeroed `[:41]` then `[41:]` = **all columns** â†’ Tier 2 = all zeros â†’ $0 AAL.

R's `active_t2[,-c((42):41)] <<- 0` = `active_t2[,-c(42, 41)] <<- 0` â€” R's `42:41` is a **descending 2-element sequence** `c(42, 41)`, NOT empty. R excludes only columns 41 and 42, keeping everything else â†’ Tier 2 produces ~$58M AAL.

### Fix applied

Added 2-line guard at the top of `_zero_outside` in `Cluster Code/cluster_062026/Python Code/bucketfill_cf_model.py`:

```python
if keep_from >= keep_to:
    keep_from, keep_to = keep_to - 1, keep_from + 1
```

When `keep_from == keep_to == 41`: new range is `[40:42]` = Python cols 40â€“41 = R-cols 41â€“42. Matches R's descending-sequence behavior exactly.

The fix is general: it also handles the `keep_from > keep_to` case (reversed boundaries) by expanding the range symmetrically, matching R's `a:b` spanning `{min(a,b)..max(a,b)}`.

### OH88 verification after fix

Ran `python "Python Code/Main_PensionModel.py" OH88` from `Cluster Code/cluster_062026/`. Output saved to `Results/Runs/062026/OH88/OH88_detAL_062026.pkl`.

Comparison via `compare_r_python.py --plans OH88 --kind detal --run-tag 062026`:
- All tiers (1â€“6): `ok`, max_rel ~1e-15 âœ“
- Aggregate AAL, NormalCost, cash_inflows, cash_outflows: `ok`, max_rel ~4e-15 âœ“
- `Percent_difference`: `mismatch` â€” cosmetic metadata artifact (same cause as MI53)
- `run_tag`: `mismatch` â€” script comparison-logic edge case for when both sides use the same tag string

**All simulation outputs now match R at floating-point precision for all 6 test plans.**

---

## 2026-06-09 Full 37-Plan Python Verification

### detal comparison (`062026_py` vs `062026`)

Ran `Main_PensionModel.py` for all 37 standard plans (MA50 excluded). Results in `Results/Runs/062026_py/`. Comparison run:
```
python compare_r_python.py --plans all --kind detal --r-run-tag 062026 --py-run-tag 062026_py --output Results/Runs/062026_py/_compare_detal_vs_r.csv
```

**Result: 37/37 plans pass. Zero simulation mismatches.**

The only non-`ok` rows in the CSV (1850 total rows):
- `run_tag`: every plan â€” expected artifact (different run tags)
- `Percent_difference`: 17 plans â€” formula/sign convention: R computes `(CAFR âˆ’ Model) / CAFR`, Python computes `(Model âˆ’ CAFR) / Model`. Neither is a simulation bug.

All simulation matrices (tier AAL, aggregate AAL, NormalCost, cash_inflows, cash_outflows, RetRes) agree at max_rel ~1e-15 (floating-point noise).

### asset comparison (`062026_py` vs `062026`)

Ran asset comparison after fixing `compare_r_python.py` to return `missing_r_output` rows instead of crashing on plans with no R asset output (LA130, LA163). Comparison run:
```
python compare_r_python.py --plans all --kind asset --r-run-tag 062026 --py-run-tag 062026_py --output Results/Runs/062026_py/_compare_assets_vs_r.csv
```

**Result: all deterministic components match; stochastic matrices not comparable (expected).**

| Status | Count | Cause |
|---|---|---|
| `ok` | 1523 | All tier/liability matrices â€” floating-point clean |
| `shape_mismatch` | 175 | R `num_sim=100` vs Python `num_sim=1000` on stochastic matrices |
| `num_sim` mismatch | 35 | Same: 100 vs 1000 |
| `missing_r_output` | 2 | LA130, LA163 â€” no R asset simulation was run for them |
| `Percent_difference` mismatch | 17 | Same sign/denominator convention artifact as detal |

Stochastic matrix comparison (Assets, AAL, cash_inflows, cash_outflows) is not meaningful: R and Python use different RNGs and different `num_sim`. All 1523 `ok` rows confirm the deterministic liability components carried into the asset pkl files are bit-identical to R.

### bug fix to compare_r_python.py

Added graceful handling for missing R or Python outputs in `compare_r_python.py`: instead of crashing on `FileNotFoundError`, the function now returns a single row with `status = missing_r_output` or `missing_py_output`. The main loop continues uninterrupted.

---

## 2026-06-09 R Asset Re-run to 1000 Sims + Distributional Comparison

### R asset simulation re-run at num_sim=1000

`asset_simulation_all_2022_062026.R` was already set to `num_sim <- 1000`. After fixing `root_dir` depth (`..", "..", ".."` instead of two levels), the script re-ran all 34 plans (excluding LA130, LA163, MA50, WA116). All 34 output files regenerated in `Results/Runs/062026/`.

### Asset comparison re-run (both at num_sim=1000)

Re-ran `compare_r_python.py --kind asset` after R outputs updated to 1000 sims.

`Results/Runs/062026_py/_compare_assets_vs_r.csv` (1887 rows total):

| Status | Count | Cause |
|---|---|---|
| `ok` | 1759 | All deterministic components â€” floating-point clean |
| `shape_mismatch` | 37 | `NormalCost` only: R saves 35Ã—1, Python saves 35Ã—1000 (structural) |
| `mismatch` | 91 | 37 `Assets` (different RNGs â€” expected), 37 `run_tag` (cosmetic), 17 `Percent_difference` (formula convention) |

No unexpected mismatches. All 1759 ok rows confirm deterministic liability components carried into asset pkl files are bit-identical to R.

### Distributional comparison (year-10 funded ratio and exhaustion probability)

`pyreadr` cannot load the R asset `.RData` files (they save a full environment). Extracted R distributional stats via `Cluster Code/cluster_062026/Common_Code/extract_asset_distrib.R` (Rscript). Python stats computed inline from pkl files. Both n=1000.

Output CSVs:
- `Results/Runs/062026/_asset_distrib_062026.csv` (R side)
- `Results/Runs/062026_py/_asset_distrib_062026_py.csv` (Python side)

| plan | FR10_mean_r | FR10_mean_py | dFR10 | exhaust_r% | exhaust_py% | d_ex_pp |
|---|---|---|---|---|---|---|
| AZ06 | 0.912 | 0.927 | 0.015 | 29.7 | 28.3 | 1.4 |
| AZ127 | 1.406 | 1.457 | 0.051 | 6.5 | 6.0 | 0.5 |
| CA10 | 1.034 | 0.999 | 0.035 | 32.7 | 32.6 | 0.1 |
| CA111 | 1.112 | 1.134 | 0.022 | 19.5 | 20.7 | 1.2 |
| CA43 | 1.169 | 1.173 | 0.004 | 29.7 | 29.4 | 0.3 |
| CA97 | 1.140 | 1.102 | 0.038 | 16.7 | 21.5 | 4.8 |
| CA98 | 1.521 | 1.482 | 0.039 | 21.9 | 24.4 | 2.5 |
| DC20 | 1.127 | 1.123 | 0.004 | 0.1 | 0.0 | 0.1 |
| FL26 | 1.049 | 1.116 | 0.067 | 39.7 | 37.6 | 2.1 |
| GA27 | 0.838 | 0.830 | 0.008 | 15.7 | 14.7 | 1.0 |
| GA28 | 0.814 | 0.815 | 0.001 | 21.7 | 22.2 | 0.5 |
| IL32 | 1.318 | 1.319 | 0.001 | 49.4 | 49.1 | 0.3 |
| IL33 | 0.705 | 0.708 | 0.003 | 18.9 | 19.1 | 0.2 |
| IL34 | 0.283 | 0.293 | 0.010 | 94.5 | 94.0 | 0.5 |
| IN37 | 0.261 | 0.279 | 0.018 | 97.1 | 95.0 | 2.1 |
| LA44 | 0.940 | 0.972 | 0.032 | 17.6 | 16.0 | 1.6 |
| ME47 | 1.084 | 1.077 | 0.007 | 28.6 | 28.9 | 0.3 |
| MI53 | 1.344 | 1.345 | 0.001 | 37.1 | 37.8 | 0.7 |
| MO175 | 1.347 | 1.348 | 0.001 | 61.7 | 61.0 | 0.7 |
| ND82 | 0.779 | 0.743 | 0.036 | 72.9 | 76.6 | 3.7 |
| NJ71 | 0.943 | 0.950 | 0.007 | 0.8 | 1.5 | 0.7 |
| NJ73 | 0.168 | 0.170 | 0.002 | 98.1 | 97.4 | 0.7 |
| NM74 | 0.733 | 0.733 | 0.000 | 50.7 | 53.1 | 2.4 |
| NY78 | 1.041 | 1.028 | 0.013 | 48.6 | 48.6 | 0.0 |
| NY83 | 1.368 | 1.337 | 0.031 | 16.2 | 15.3 | 0.9 |
| OH88 | 1.026 | 1.027 | 0.001 | 7.1 | 6.6 | 0.5 |
| OK134 | 0.415 | 0.418 | 0.003 | 86.1 | 87.4 | 1.3 |
| OR91 | 1.061 | 1.063 | 0.002 | 20.7 | 21.2 | 0.5 |
| PA92 | 0.845 | 0.855 | 0.010 | 3.6 | 4.9 | 1.3 |
| PA93 | 1.008 | 1.017 | 0.009 | 24.2 | 25.1 | 0.9 |
| RI96 | 1.206 | 1.236 | 0.030 | 20.6 | 20.9 | 0.3 |
| SC100 | 0.826 | 0.837 | 0.011 | 18.0 | 16.2 | 1.8 |
| SC99 | 1.002 | 1.000 | 0.002 | 3.4 | 2.7 | 0.7 |
| TX108 | 0.931 | 0.938 | 0.007 | 57.4 | 55.1 | 2.3 |

**Summary: mean |dFR10| = 0.015, max = 0.067; mean |d_exhaust| = 1.1 pp, max = 4.8 pp.**

All differences are consistent with independent Monte Carlo sampling at n=1000. The two implementations produce the same financial distributions â€” R and Python asset models verified equivalent.

---

## 2026-06-09 10000-Sim Asset Comparison

Both R and Python re-run at `num_sim = 10000` for all 37 plans (excluding MA50). R: changed `num_sim <- 10000` in `asset_simulation_all_2022_062026.R` and re-ran. Python: `asset_simulation.py --num-sim 10000 --run-tag 062026_py --overwrite`. Both completed in under 2 minutes.

LA130 and LA163 now have R asset outputs at 10000 sims (the R script ran them). All 37 plans compared.

| Plan | FR10_mean_r | FR10_mean_py | dFR10 | exhaust_r% | exhaust_py% | d_ex_pp |
|---|---|---|---|---|---|---|
| AZ06 | 0.923 | 0.943 | 0.020 | 29.3 | 29.4 | 0.1 |
| AZ127 | 1.404 | 1.408 | 0.004 | 5.7 | 5.7 | 0.0 |
| CA10 | 1.040 | 1.036 | 0.004 | 34.0 | 33.4 | 0.6 |
| CA111 | 1.135 | 1.129 | 0.006 | 19.4 | 19.5 | 0.1 |
| CA144 | 1.279 | 1.302 | 0.023 | 10.5 | 11.1 | 0.6 |
| CA43 | 1.161 | 1.162 | 0.001 | 28.1 | 28.4 | 0.3 |
| CA97 | 1.135 | 1.145 | 0.010 | 18.2 | 17.5 | 0.7 |
| CA98 | 1.496 | 1.514 | 0.018 | 22.1 | 22.1 | 0.0 |
| DC20 | 1.131 | 1.132 | 0.001 | 0.0 | 0.0 | 0.0 |
| FL26 | 1.085 | 1.086 | 0.001 | 37.4 | 37.6 | 0.3 |
| GA27 | 0.825 | 0.827 | 0.002 | 15.7 | 15.6 | 0.1 |
| GA28 | 0.811 | 0.809 | 0.002 | 22.4 | 22.1 | 0.3 |
| IL32 | 1.292 | 1.299 | 0.007 | 49.0 | 48.3 | 0.7 |
| IL33 | 0.714 | 0.714 | 0.000 | 19.0 | 18.4 | 0.6 |
| IL34 | 0.290 | 0.285 | 0.005 | 94.1 | 94.9 | 0.8 |
| IN37 | 0.271 | 0.271 | 0.000 | 96.1 | 96.1 | 0.0 |
| LA130 | 1.200 | 1.209 | 0.009 | 23.4 | 23.0 | 0.4 |
| LA163 | 0.752 | 0.747 | 0.005 | 63.5 | 63.4 | 0.1 |
| LA44 | 0.974 | 0.964 | 0.010 | 16.4 | 16.5 | 0.1 |
| ME47 | 1.053 | 1.055 | 0.002 | 30.7 | 30.0 | 0.7 |
| MI53 | 1.335 | 1.302 | 0.033 | 38.0 | 39.0 | 1.0 |
| MO175 | 1.364 | 1.359 | 0.005 | 58.8 | 59.4 | 0.6 |
| ND82 | 0.765 | 0.761 | 0.004 | 72.9 | 73.9 | 1.0 |
| NJ71 | 0.931 | 0.934 | 0.003 | 1.0 | 1.0 | 0.0 |
| NJ73 | 0.170 | 0.170 | 0.000 | 97.9 | 97.6 | 0.3 |
| NM74 | 0.737 | 0.741 | 0.004 | 51.9 | 51.7 | 0.2 |
| NY78 | 1.016 | 1.021 | 0.005 | 48.8 | 47.8 | 1.0 |
| NY83 | 1.369 | 1.357 | 0.012 | 15.7 | 15.9 | 0.2 |
| OH88 | 1.006 | 1.008 | 0.002 | 6.2 | 6.6 | 0.4 |
| OK134 | 0.424 | 0.427 | 0.003 | 85.6 | 86.1 | 0.5 |
| OR91 | 1.052 | 1.055 | 0.003 | 21.1 | 21.0 | 0.1 |
| PA92 | 0.859 | 0.860 | 0.001 | 3.5 | 3.8 | 0.3 |
| PA93 | 1.009 | 1.014 | 0.005 | 23.7 | 23.5 | 0.2 |
| RI96 | 1.204 | 1.219 | 0.015 | 22.2 | 20.3 | 1.9 |
| SC100 | 0.840 | 0.851 | 0.011 | 15.9 | 15.7 | 0.2 |
| SC99 | 0.994 | 0.991 | 0.003 | 3.5 | 3.3 | 0.2 |
| TX108 | 0.912 | 0.914 | 0.002 | 56.9 | 57.4 | 0.5 |

**Summary: mean |dFR10| = 0.007, max = 0.033; mean |d_exhaust| = 0.4 pp, max = 1.9 pp.**

At 10000 sims the distributions converge tightly. All differences are pure Monte Carlo noise. R and Python asset models confirmed equivalent.

### `asset_simulation.py` parquet fix

Added `ignore_errors=True` to `shutil.rmtree` in `write_parquet_bundle` to handle Windows/OneDrive file locking when overwriting existing parquet directories.

---

## *** RESOLVED (2026-06-09) ***

### Python translation: complete for all 37 plans (verified end-to-end)

All 37 plans (excluding MA50 structural outlier) verified:
- Deterministic liability components: floating-point precision (max_rel ~1e-15)
- Asset distributions at 10000 sims: mean |dFR10|=0.007, max=0.033; mean |d_exhaust|=0.4 pp, max=1.9 pp

Known non-simulation artifacts in comparison CSVs (do not need fixing):
- `run_tag` mismatch: every plan â€” different run tag strings
- `Percent_difference` mismatch: 17 plans â€” R and Python used different sign/denominator conventions. **Standardized in the session below.**
- `shape_mismatch` for `NormalCost`: R saves 35Ã—1, Python saves 35Ã—10000 (structural, not a bug)

---

## 2026-06-09 Percent_difference Standardization

Canonical formula everywhere: `Percent_difference = (Model_AAL - CAFR_AAL) / CAFR_AAL`.

- Bulk-fixed 21 R scripts under `Cluster Code/cluster_062026/cluster_code_2022/Main_PensionModel_*.R` that had the inverted formula `(CAFR_AAL - Model_AAL) / Model_AAL`: AZ06, AZ127, CA10, CA111, CA144, CA43, CA97, CA98, DC20, FL26, GA27, GA28, IL32, IL33, IL34, IN37, LA130, LA163, LA44, MA50, ME47.
- Created `Cluster Code/cluster_062026/Common_Code/patch_percent_difference.R` to patch existing `.RData` files in-place (no rerun needed). Already applied to all 37 plan RData outputs.
- Updated `validation/compare_r_python.py` to recompute `Percent_difference` on the fly from stored `Model_AAL`/`CAFR_AAL` rather than reading the stored value, preventing stale stored values from flagging spurious mismatches.
- Python `Main_PensionModel.py` already used the correct formula and was not changed.

---

## 2026-06-09 Python Code Directory Reorganization

Reorganized `Cluster Code/cluster_062026/Python Code/`:

- Created `validation/` subfolder with stable comparison tools:
  - `compare_r_python.py` (moved from root) â€” R vs Python comparison
  - `compare_fast_vs_orig.py` (new) â€” fast/ pkg vs original Python comparison
  - `README.md` â€” usage instructions with example commands
- Deleted stale/single-use files: `patch_percent_difference.py`, `Main_PensionModel_AZ06.py`, `validate_az06.py`, `export_az06_for_validation.R`
- `g.py` is legacy â€” still required by the original Python scripts (`Main_PensionModel.py`, `asset_simulation.py`, `liability_cf_model.py`, etc.) but NOT used by `fast/`. Until fast/ fully replaces the original, g.py must stay.

---

## 2026-06-09 Fast Python Track (`fast/` Package)

Created `Cluster Code/cluster_062026/Python Code/fast/` â€” optimized Python translation keeping identical methodology.

**Files:**
- `fast/sim_params.py` â€” `PlanParams` dataclass replacing g.py global state. All parameters explicitly threaded through function arguments.
- `fast/core.py` â€” optimized simulation functions:
  - `update_employees` / `l_update_employees`: vectorized diagonal numpy shift instead of double Python loops
  - `death_pay`: vectorized triangle-masked elementwise sum
  - `compute_annuity`: vectorized inner loop via `np.cumprod`
  - `pvnc_calc_fast`: parallel across 55 starting ages via `ThreadPoolExecutor`
  - `total_liabilities_current_fast`: parallel 2 paths via `ThreadPoolExecutor(max_workers=2)`
- `fast/Main_PensionModel.py` â€” fast runner for all 37 standard plans; CLI-compatible with original `Main_PensionModel.py` plus `--workers` for PVNC thread-pool size.
- `fast/__init__.py` â€” empty package marker.

**Key design decisions:**
- Absolute imports (`from fast.sim_params import ...`) because the file is run as a script directly, not as a module. `sys.path.insert(0, "Python Code/")` makes `fast` importable.
- `current_dir` path goes two levels up from `fast/` to reach `cluster_062026/`.
- Per-tier params set via `dataclasses.replace(base_params, COLA=..., BenefitFactor=..., ...)`.
- `main_ret_fast` uses `COLA_t[num_tiers]` / `BenefitFactor_t[num_tiers]` / `NyearFullBenefit_t[num_tiers]` (last tier's values), matching R's global-mutation behavior where `g.COLA` holds the last-set value after the tier loop.

**run_simulation.py changes:**
- Added `--fast` flag: uses `fast/Main_PensionModel.py` instead of `Main_PensionModel.py`
- Added `--workers` flag: PVNC thread-pool workers (fast mode only)
- Replaced rigid batch processing with single `ThreadPoolExecutor` pool as concurrency ceiling â€” plans start immediately when a slot frees; no round-robin batching
- Added per-plan and total timing to all simulation scripts (`Main_PensionModel.py`, `asset_simulation.py`)

**sim_commands.html updates:**
- Added local parameter reference table (16 params including `--fast`, `--workers`)
- Added "Run detal only (fast)" and "Run detal+assets (fast)" local commands with `run-tag 062026_fast`
- All Engaging submit actions changed to `upload-submit` (bare `submit` fails because it looks for `uploaded_plans.txt` from the upload step)

---

## 2026-06-09 Fast Run Results (run tag: `062026_fast`)

Ran `--fast` for all 37 plans on local machine. Results in `Results/Runs/062026_fast/`.

**A/L (detal): 37/37 succeeded.** All pkls present. Sample timing: AZ06 ~56 min total (3 tiers Ã— ~18 min + Main_Ret ~2 min).

**Assets: 37/37 succeeded.** All pkls present. The parquet bundle write failed after pkl save (Windows path-too-long, WinError 206 â€” full path ~252 chars, files inside would exceed 260). `asset_simulation.py` now wraps `write_parquet_bundle` in `try/except OSError` so this is a warning, not a crash. No data loss â€” pkl contains all simulation output.

---

## 2026-06-09 Fast vs Original Comparison and Bug Fix

### Comparison results

Ran `validation/compare_fast_vs_orig.py --orig 062026_py --fast 062026_fast`.

**26 plans â€” AAL matches at machine epsilon (~1e-16 relative):** AZ06, CA10, CA111, CA144, DC20, GA27, GA28, IN37, LA130, LA163, LA44, ME47, ND82, NJ71, NJ73, NM74, NY78, NY83, OH88, OK134, PA92, PA93, RI96, SC100, SC99, TX108.

**11 plans â€” real AAL mismatches (9%â€“198%):** AZ127, CA43, CA97, CA98, FL26, IL32, IL33, IL34, MI53, MO175, OR91.

NormalCost differs by ~1â€“7% across all 37 plans â€” expected, due to `ThreadPoolExecutor` parallel PVNC_Calc changing floating-point summation order. AAL (primary output) is not affected.

R comparison (ground truth) confirmed: the same 11 plans also diverge from R, confirming the fast code was wrong.

### Bug found and fixed in `fast/Main_PensionModel.py`

Root cause: `Main_Current` in original Python mutates `g.COLA = COLA_f` on every tier call. After the tier loop, `g.COLA` holds the **last tier's** COLA. `Main_Ret` then uses that `g.COLA`. The fast version incorrectly passed `COLA_t[1]` (tier 1) to `main_ret_fast` instead of `COLA_t[num_tiers]` (last tier). Same error for `BenefitFactor_t` and `NyearFullBenefit_t`.

Fix: changed all three to use `_t[num_tiers]` in the `main_ret_fast` call.

Plans affected: any multi-tier plan where COLA (or BenefitFactor) differs across tiers. Plans with 1 tier or uniform COLA across tiers are unaffected â€” those 26 plans were already correct.

---

## 2026-06-09 Notebook Cleanup And Reorganization

### Notebooks made identical (except two config lines)

Both analysis notebooks were refactored so they are identical except for `RUN_TAG` and `RESULT_SOURCE` in Cell 1:

| Notebook | `RUN_TAG` | `RESULT_SOURCE` |
|---|---|---|
| `062026_results_analysis.ipynb` | `"062026"` (R) | `"rdata"` |
| `results_analysis_parquet.ipynb` | `"062026_py"` (Python) | `"parquet"` |

Changes made to both notebooks:
- **Cell 1**: replaced stale `candidate_code_dirs` path-discovery loop with `sys.path.insert(0, str(Path.cwd()))` (results_analysis.py is co-located); added `RESULT_SOURCE` variable.
- **Cell 4** (markdown): updated wording to describe `RESULT_SOURCE` as the format selector; noted that `*_analysis.RData` companion creation only applies to `RESULT_SOURCE = "rdata"`.
- **Cell 5**: unified to `if RESULT_SOURCE == "rdata": ra.prepare_analysis_exports(...)` then `ra.load_run_results(..., source=RESULT_SOURCE)`. Identical in both notebooks.

### Notebooks and `results_analysis.py` moved to `Python Code/`

All analysis files now live in `Cluster Code/cluster_062026/Python Code/`:
- `results_analysis.py` (was already moved in a prior session)
- `062026_results_analysis.ipynb` (moved from `Results/Python Code/`)
- `results_analysis_parquet.ipynb` (moved from `Results/Python Code/`)

`Results/Python Code/` folder deleted. All run outputs remain under `Results/Runs/[run_tag]/` only â€” never under `Results/Python Code/`.

---

## 2026-06-09 NormalCost bug: root cause identified and fixed

### Root cause

The fast NC einsum in `fast/core.py` `main_current_fast` included cells (i_exp, j_exp) where `j_exp > i_exp` (service year > age index). `ConstantFill` with `enforce_service_limit=True` allows j_exp = i_exp + 1 (the superdiagonal: employees whose service equals age-19, e.g., started at 19). These cells have non-zero AN and BW, so the einsum over-counted NC.

The original NC loop uses `j in range(1, min(i, n_svc)+1)` (1-indexed), i.e., j_exp â‰¤ i_exp (0-indexed), which excludes the superdiagonal. PVNC_arr was unaffected (PVFS=0 at superdiagonal cells from the loop-constrained PVFS computation, so the einsum contribution is 0).

### Fix

`fast/core.py`, `main_current_fast`: added `_nc_mask = np.tril(np.ones((n_age, n_svc), dtype=bool))` and applied it to the NC einsum:

```python
NC[t-1, 0] = float(np.einsum('ij,i,ij->',
                               AN[:, :, t-1], NCxs,
                               np.where(_nc_mask, BW[:, :, t-1], 0.0)))
```

### Verification

AZ06 rerun: max |NC diff| = 1e-6 (floating point only), per-tier diff = 0 for all tiers/years. AAL/PVFB/PVNC_arr unchanged (still bit-identical to orig).

### Status

All 37 plans rerun 2026-06-09 with `--overwrite` (NC fix + COLA fix both applied). Validation pending.

```powershell
python "Cluster Code\cluster_062026\Python Code\validation\compare_fast_vs_orig.py" `
  --orig 062026_py --fast 062026_fast
```

Expected: all 37 plans all 4 matrix keys at machine epsilon (AAL, NormalCost, cash_outflows, cash_inflows).

## 2026-06-09 Validation: 062026_fast vs 062026_py â€” COMPLETE

`compare_fast_vs_orig.py --orig 062026_py --fast 062026_fast` result:

- **ok: 240, mismatch: 130** â€” but ALL 130 mismatches have `max_rel` â‰¤ 5Ã—10â»Â¹â¶ (machine epsilon, ~2 ULP).
- cash_inflows: 0 difference on all 37 plans (exactly ok).
- AAL, NormalCost, cash_outflows: floating point rounding noise only; no substantive differences.
- `062026_fast` is numerically equivalent to `062026_py` on all 4 matrix keys for all 37 plans.

The `compare_fast_vs_orig.py` "mismatch" status means `max_abs > 0.0 exactly`. This is expected from different code paths (vectorized numpy vs explicit loops, thread pool ordering). Not a bug.

**`062026_fast` is validated as production-equivalent to `062026_py` as of 2026-06-09.**

---

## *** OPEN *** 2026-06-10 Fast/ Speed Benchmarking

### Measured speedup

Timed both original and fast Python on OK134 (1 tier, smallest plan) run in isolation:

| Version | Time |
|---|---|
| `Main_PensionModel.py` (original) | 4m 54s |
| `fast/Main_PensionModel.py` (parallel PVNC, 22 workers) | 3m 20s |
| Speedup | ~1.5Ã— |

### Detal times for the 062026_fast batch run (all 37 plans)

The `062026_fast` batch ran 19 plans in parallel (user-corrected 2026-06-10; an earlier note here wrongly said 4). Per-plan detal times from logs (per-tier times sum to total; Main_Ret is separate). These times were measured under 19-way plan contention on a 22-core machine, so they overstate isolated per-plan runtimes:

| Plan | Total detal | Plan | Total detal |
|---|---|---|---|
| OK134 | 3m 20s | MO175 | 13m 45s |
| PA92 | 5m 47s | OR91 | 12m 22s |
| SC100 | 6m 06s | NM74 | 11m 29s |
| SC99 | 6m 04s | TX108 | 10m 31s |
| NY83 | 9m 39s | NY78 | 20m 13s |
| PA93 | 8m 46s | AZ127 | 20m 27s |
| GA28 | 7m 22s | NJ71 | 22m 43s |
| LA163 | 13m 10s | NJ73 | 22m 16s |
| FL26 | 15m 48s | LA44 | 22m 16s |
| IL32 | 16m 29s | CA98 | 22m 36s |
| RI96 | 16m 20s | CA111 | 22m 57s |
| DC20 | 17m 58s | MI53 | 24m 44s |
| CA10 | 17m 57s | ND82 | 24m 18s |
| GA27 | 18m 46s | ME47 | 25m 52s |
| OH88 | 19m 31s | AZ06 | 26m 25s |
| IN37 | 31m 56s | CA144 | 27m 57s |
| IL33 | 34m 13s | LA130 | 28m 50s |
| IL34 | 38m 17s | CA97 | 33m 38s |
| CA43 | 40m 21s | | |

Total sequential detal: 721m (sum of per-plan times under contention). Asset simulation: 1â€“2s per plan, negligible.

### Why speedup is modest (~1.5Ã—)

- PVNC is parallelized via `ThreadPoolExecutor(workers=cpu_count=22)`, but numpy releases the GIL so threads do run truly in parallel.
- However: running 19 plans simultaneously means 19 Ã— 22 = ~418 PVNC threads competing for 22 physical CPUs â€” heavy oversubscription that erodes per-plan gains.
- The tier loop is sequential (one tier at a time within a plan). Multi-tier plans (e.g., AZ06 = 3 tiers Ã— ~8.5 min each) get no inter-tier parallelism.
- `total_liabilities_current_fast` runs 2 paths in parallel but each path is very fast relative to PVNC; this barely moves the total.

### Open optimization questions

- **Optimal worker count**: `--workers 22` with 4-parallel-plan runs is oversubscribed. Test with `--workers = cpu_count // parallel_plans` (e.g., 22//4 = 5 or 6). Expected to improve wall-clock when many plans run together.
- **Inter-plan parallelism vs intra-plan**: Current design runs intra-plan threads (PVNC parallelism) inside plan-level parallelism (multiple plans at once). May be better to use fewer PVNC workers and run more plans simultaneously.
- **Original Python baseline for other plans**: Original timing only measured for OK134. Multi-tier original times are unknown; extrapolation from OK134 is unreliable.
- **Engaging speedup**: On Engaging (Slurm array, 1 plan per node), each plan gets all node CPUs for PVNC â€” no inter-plan contention. Speedup there should be larger than the 1.5Ã— measured locally. **Superseded by 2026-06-10 profiling below: PVNC threads are GIL-serialized, so per-node CPU count is irrelevant; Engaging will NOT be faster per plan.**

### 2026-06-10 py-spy profiling results (OK134, isolated)

Profiled `fast/Main_PensionModel.py OK134 --run-tag prof_OK134` with py-spy 0.4.2
(50 Hz, speedscope output). Artifacts in `Results/Runs/prof_OK134/`
(`profile_ok134_fast.speedscope.json`, `analyze_speedscope.py`).

Headline numbers:
- Isolated wall-clock: **2m 12s** (vs 3m 20s in the 19-parallel batch â€” batch
  times include heavy contention).
- Total active-thread sample weight: 145.7s over ~132s wall â†’ **effective
  parallelism â‰ˆ 1.1 threads**. The PVNC `ThreadPoolExecutor` (91 thread
  profiles) delivers essentially zero parallelism â€” the year-step update
  functions are Python-bytecode-bound and hold the GIL.
- ~84% of all time is inside thread-pool workers running `_pvnc_single_age`,
  `_liab_path`, and `total_liabilities_ret_fast` inner 80-year loops.

Where the time goes (self time):
- **`np.mean` machinery â‰ˆ 33%** â€” `float(np.mean(pw))` on tiny 1â€“5 element
  arrays inside the (i,j) double loops of `update_retirement_benefit`
  (core.py:212, 27% total) and `update_inactive_benefits` (core.py:146, 21%
  total). numpy dispatch overhead dwarfs the arithmetic at this size.
- **`past_wages` â‰ˆ 14%** â€” Python loop building tiny wage vectors per (i,j,t).
- Remaining double-loop bodies (`update_inactive_count`,
  `update_retirement_number`, `update_retirement_benefit`,
  `update_inactive_benefits`, `refund`) â‰ˆ 25%+.

Conclusion: runtime is dominated by per-call Python/numpy overhead on tiny
arrays inside the inner projection loops. More threads/cores cannot help.

Planned fixes (in impact order, validate each with `compare_fast_vs_orig.py`):
1. Replace `float(np.mean(pw))` with plain arithmetic (or fold the mean into
   the `past_wages` loop) â€” pure overhead removal. **DONE 2026-06-10, see below.**
2. Exploit geometric wage growth in `_pvnc_single_age`/`_liab_path`: there
   `L_BW[:,:,t] = W0 * (1+g)^t` exactly, so past-wage means have a closed form
   that can be precomputed once per path instead of per (i,j,t). **Superseded
   by zero-skip guards (below), which removed most mean calls outright; revisit
   only if more speed is needed (changes float rounding, so not bit-identical).**
3. Vectorize the (i,j) double loops with triangle masks (same approach already
   used in `death_pay`). **Still open.**
4. Remove the PVNC `ThreadPoolExecutor` (no benefit, adds oversubscription when
   plans run in parallel). **Still open.**

### 2026-06-10 Optimization pass 1 applied to `fast/core.py` â€” 4.9Ã— speedup, bit-identical

Changes (all designed to be IEEE-exact, no methodology change):
- Added `past_wages_mean()` â€” plain-Python sequential sum Ã· n replacing
  `float(np.mean(past_wages(...)))` in `update_inactive_benefits` and
  `update_retirement_benefit`. Bit-identical for period â‰¤ 8 because numpy's
  pairwise summation is sequential below its unroll block size.
- Zero-skip guards in `update_inactive_benefits` (`NewSep == 0 â†’ continue`),
  `update_retirement_benefit` (`prob == 0 â†’ continue`; per-term `!= 0` guards),
  and `update_retirement_number` (`prob == 0 â†’ continue`). Exact because the
  skipped terms are products with an exact 0.0 factor and `x += 0.0` is a
  no-op for the non-negative finite values involved. Huge effect in the
  80-year inner sims, where `_pvnc_single_age` simulates a single employee
  (matrices ~99% zeros) and `total_liabilities_ret_fast` passes all-zero
  active/inactive matrices.
- Hoisted `(1+rr)**arange` power vector out of `refund`'s inner loop
  (elementwise pow â†’ slicing a precomputed vector is value-identical).

Measured (isolated, local 22-core machine):
| Plan | Before pass 1 | After pass 1 | Original Python |
|---|---|---|---|
| OK134 (1 tier) | 2m 12s | **26.9s** (4.9Ã—) | 4m 54s (~11Ã—) |
| AZ06 (3 tiers) | n/a isolated (26m 25s in 19-way batch) | **1m 16s** | n/a |

Validation:
- OK134: new pkl vs pre-change pkl â€” all 37 arrays (Assets, AAL, NormalCost,
  cash flows, RetRes, all MainRes tier matrices) + Model_AAL/CAFR_AAL/
  Percent_difference **bit-identical** (max abs diff 0.0).
- AZ06: new pkl vs canonical `Results/Runs/062026_fast/AZ06/` pkl â€”
  all 37 arrays **bit-identical**.
- Because outputs are bit-identical, existing `062026_fast` outputs remain
  valid; no rerun of the 37-plan batch is required for correctness.

Artifacts: scratch run tag `prof_OK134` (`Results/Runs/prof_OK134/` â€” contains
profile JSON, `analyze_speedscope.py`, `compare_pkl_exact.py`, before/after
pkls). Scratch folder can be deleted once this section is closed.

Full production batch after pass 1 (2026-06-10, local, 19 parallel,
`--stage both --fast`, num_sim=10000 per `_manifest.csv`): **all 37 plans,
detal + assets, in ~8 minutes wall-clock** (vs ~3 hours pre-optimization;
~22Ã—). All 37 detAL pkls and 37 asset pkls verified fresh.

Run-folder consolidation (2026-06-10, user action): the run used the default
run tag `062026`, and the user then **deleted all other run outputs** â€” the R
`.RData` outputs, `062026_py/`, `062026_fast/`, and the `prof_OK134/` scratch
folder. `Results/Runs/062026/` is now the sole canonical run folder and
contains Python fast-package outputs only: 37 `[PLAN]_detAL_062026.pkl`, 37
`[PLAN]_AssetSim_2asset_062026.pkl` (num_sim=10000), 37 parquet bundles, and
the Python `_manifest.csv`. The old `062026`=R / `062026_*`=Python tag
convention is retired; Python `fast/` is the production engine. Râ†”Python
comparisons going forward require regenerating R outputs first.

`sim_commands.html` updated 2026-06-10: fast command cards now use
`--parallel 19 --workers 1`; `--fast` and `--workers` parameter descriptions
corrected (bit-identical results, GIL-serialized PVNC threads â†’ use
`--workers 1`).

### 2026-06-10 Analysis notebooks merged into one

`062026_results_analysis.ipynb` (rdata twin) and `results_analysis_parquet.ipynb`
were merged into a single **`results_analysis.ipynb`** (same folder,
`Cluster Code/cluster_062026/Python Code/`). The twins were verified identical
in all 48 cells except Cell 1 before the merge. Cell 1 now sets
`RESULT_SOURCE = "auto"`, resolved via the new
`results_analysis.detect_result_source(root, run_tag)` (returns "parquet" or
"rdata" from run-folder contents; prefers parquet with a printed note if both
exist; raises if neither). Explicit `"rdata"`/`"parquet"` still works. Smoke
test passed: auto-detected parquet on `Results/Runs/062026/` and loaded OK134
(35 years Ã— 10000 sims).

## 2026-06-10 Common Market Shocks In The Asset Simulation

Methodology change in `Cluster Code/cluster_062026/Python Code/asset_simulation.py`
(user-requested): all plans now share ONE standardized market shock matrix
`Z (Nyear-1 Ã— num_sim)` generated from a single market seed. Plan p's stock
return is `(0.075 + Inflation_p) + 0.20 * Z[t, n]`, so per-plan marginal
distributions are unchanged but simulation column n is the same market history
for every plan. Rationale: with independent per-plan draws, cross-plan
aggregation cancels shocks and understates aggregate tail risk by ~sqrt(37);
common shocks make aggregate distributional statistics (fans, tail
percentiles) meaningful. This intentionally differs from the R script (which
draws independent streams per plan).

Implementation details:
- `--seed` is now the market seed shared by ALL plans (was: seed+index per
  plan). If omitted, one seed is generated and printed.
- `run_simulation.py` passes the same base seed to every per-plan asset
  subprocess; if no seed is given for the asset stage it generates one so
  parallel subprocesses still agree.
- The Monte Carlo loop was vectorized across simulations (was per-path Python
  loops): ~3.8s/plan at num_sim=10000.
- Asset pkl payloads now store `market_seed` and `common_market_shocks: True`.
- `sim_commands.html` seed parameter descriptions updated (local + Engaging;
  on Engaging always pass an explicit seed since array tasks are separate
  processes).

Rerun + verification (2026-06-10): all 37 plans regenerated in
`Results/Runs/062026/` (num_sim=10000, market seed 123, 2m20s total).
Cross-plan check: standardized shocks implied from saved Assets matrices of
AZ06 and NJ73 match to 4e-15 with correlation exactly 1.0.

## 2026-06-10 results.ipynb Rebuilt (Stochastic-First)

`analysis/results.ipynb` fully rebuilt (47 cells; pre-rebuild copy saved as
`results.ipynb.bak`). Changes:
- Stale meta cells removed: hand-maintained "Analysis Coverage" roadmap
  DataFrame, duplicate "Items Requiring New Data" markdown (referenced
  num_sim=100), `ppd.head()` debug cell, empty trailing cell.
- **Bug fixed:** reform-workbook lookup pointed at the pre-reorganization path
  `root/cluster_062026/...` and silently fell back to the 2017
  `planchanges_main.xlsx`. Now prefers
  `Cluster Code/cluster_062026/Common_Data/planchanges_main_2022_clean.xlsx`
  and warns loudly on 2017 fallback.
- Reordered stochastic-first: Part 1 risk metrics (exhaustion bins, NEW
  exhaustion-year CDF + per-plan CDF table, NEW mean-years-insolvent severity,
  threshold risk over full horizon, funding-ratio distributions at 15y and
  full horizon, NEW P(FR<0.4) distress heatmap replacing the q50 heatmap,
  risk scatters), Part 2 aggregate dynamics (funded-ratio fan + unfunded-AAL
  fan using per-path aggregation, equal-plan average forecast, GDP-normalized
  unfunded-AAL FAN instead of mean lines), Part 3 per-plan detail (single-plan
  fan + cash flows, five-largest-plans fans, long-format export utility),
  Part 4 baseline/descriptive (summary stats, historical funded ratios, AAA
  PV, reform summary, validation), final future-work cell (updated to
  num_sim=10000 reality).
- FRED sections (GDP + AAA) now skip gracefully via `try_fetch_fred()` when
  `FRED_API_KEY` is missing; the rest of the notebook still runs.
- Load cell checks the `common_market_shocks` flag on every plan and warns if
  absent (aggregate bands would understate risk).
- `N_PROJ` (usable projection years, drops the zero-AAL placeholder final
  year) and `GRAPH_YEARS` (forecast-figure horizon) are explicit config.

Polish pass (same day, user feedback; 45 cells now):
- Average-forecast and single-plan-forecast cells restyled to the notebook's
  `plot_fan` aesthetic with historical overlay; the average forecast is now
  the **per-path equal-weighted cross-plan average** funding ratio (valid
  under common shocks), not the module's average-of-quantiles.
- 37-row table dumps replaced with figures: plan exhaustion probabilities â†’
  nested horizontal bars (P by 10/20/35y) + mean-years-insolvent panel;
  funding-ratio distributions at two horizons â†’ per-plan interval
  (5-95/20-80/median) charts, x-capped at 3. Underlying frames remain
  available as `exhaustion`, `terminal_short`, `terminal_long`.
- Descriptive reform/tier-rule section removed per user (computation deemed
  broken/not meaningful in that form); future-work cell notes the planned
  rework as a pre-change vs post-change tier comparison matched to the
  model's tier structure.

## 2026-06-10 Scenario Layer And Launcher Notebook

User requested a scenario "platform": marginal levers in the simulation layer
plus a notebook control panel replacing terminal launches. Implemented:

**Simulation-layer levers (all default to baseline; baseline verified
bit-identical after the refactor, max|diff| = 0.0 on AZ06 at 10000 sims):**
- `asset_simulation.py`:
  - `--detal-run-tag` â€” read detAL inputs from a baseline run while writing
    asset outputs under the scenario's own `--run-tag` (key architecture piece:
    asset-only scenarios reuse baseline deterministic outputs).
  - `--contrib-add` (pp of payroll; payroll reconstructed as
    `cash_inflows / (EE+ER rate)` from rates saved in detAL pkls),
    `--policy-start` (first projection year), `--contrib-always` (pay add-on
    even when FR > 1; base rule still contributes 0 when overfunded).
    Plans whose detAL pkl lacks the rate scalars are skipped with a clear
    manifest reason.
  - `--equity-share` (flat risky-share override), `--derisk-to` +
    `--derisk-years` (linear glidepath; weights become time-varying).
  - `--stock-premium` (default 0.075) and `--stock-vol` (default 0.20).
  - Scenario settings stored in payload (`scenario` dict + `scenario_json`)
    and in `_manifest.csv` (`scenario`, `detal_run_tag` columns).
- `fast/Main_PensionModel.py`: `--discount-override` (replaces the plan GASB
  discount rate in AAL/PVNC; for AAA/market-value scenarios); detAL pkls now
  also save `EmployeeContributionRate`, `EmployerContributionRate`, and
  `discount_override`.
- `run_simulation.py`: forwards `--discount-override` to the fast detal runner.

**Launcher (`Cluster Code/cluster_062026/Python Code/`):**
- `scenarios.py` â€” `Scenario` dataclass (defaults = baseline), grid helpers
  (`contribution_grid`, `equity_grid`), `build_commands`, `preview`,
  `launch(dry_run=...)` (sequential, logs to `Results/Runs/[tag]/_logs/`),
  `inventory`, `exhaustion_summary`, `compare_exhaustion`.
- `launcher.ipynb` â€” control-panel notebook: define SCENARIOS â†’ preview â†’
  launch (dry-run default) â†’ inventory/compare. Worked examples for the
  contribution grid, equity grid, glidepath, AAA override, and no-reform
  tier-file scenarios (the last needs the counterfactual workbook first).
- All scenarios default to market seed 123, so scenario runs are path-by-path
  comparable with the baseline and each other.

Validation (all passed 2026-06-10):
- Baseline defaults bit-identical (above).
- `--equity-share 0.0`: cross-sim std of year-10 assets ~1e-16 relative
  (deterministic bond-only path, as expected).
- Scenario provenance verified in output pkl.
- Baseline detal rerun (all 37 plans, ~13 min at 19-parallel): simulation
  arrays bit-identical to pre-rerun pkls (max|diff| = 0.0 on OK134/AZ06);
  only the 3 new keys added (`EmployeeContributionRate`,
  `EmployerContributionRate`, `discount_override`).
- End-to-end launcher demo (`scn_demo_c2s0`, +2pp always, AZ06+NJ73, 10000
  sims): P(exhaust by 35) fell 0.296â†’0.225 (AZ06) and 0.978â†’0.962 (NJ73).
- Path-by-path note (real economics, NOT a bug): with the threshold
  contribution rule, scenario assets are not always >= baseline. On 1646/10000
  AZ06 paths the scenario crossed FR>1 earlier, switching its BASE
  contribution off while the baseline (still underfunded) kept full inflows â€”
  verified as the explanation for 1646/1646 crossover paths.
- Demo run folder `Results/Runs/scn_demo_c2s0/` kept as a working example for
  the launcher's inventory/compare cells; smoke scratch tags deleted.

## 2026-06-10 Municipal (City) Data Audit

User raised the fundamental data question: where are the municipal/local plan
data, in what state, with what code. Parent folder
(`State and Local Pension/`) was added to this session's access and fully
audited. **Full findings in `Documentation/city_data_audit.md`** (canonical
locations, the Airtable documentation base, the 2022 collection system per
`Github/pensions-basecode/guidebook.md`, the unfinished 2023 migration bridge
to the state-model input format, code generations, stale duplicates, timeline,
gaps, and the recommended path to running cities through the current Python
pipeline). A `context_pointer.md` was placed in the parent folder so future
sessions there find the documentation. Headline: ~16 cities / ~30 plan
workbooks collected (FY2019) under `1. Pension Data/{city}_modeldata/`;
documentation lives ONLY in Airtable (export recommended); migration to our
model format exists for hou/chi/phx only; no city has ever been simulated.

Follow-up (2026-06-11): **`Documentation/data_sources_map.md`** created â€” the
source-document landscape across both tracks (PPD database / AV-CAFR PDFs /
websites three-layer supply chain; who did each extraction; heterogeneity
axes). Key verified facts: the 40 state `[PLAN]_2017.xlsx` workbooks were
INHERITED from Brookings' replication package (we hold their package incl.
source PDFs in 3 places; their extraction assumptions are undocumented in our
repo); the 2022 state update never re-extracted distributions (PPD-driven
refresh only); all 87 municipal ppd_ids are covered by ppd-data-latest
(fy 2001-2023) so the planinfo machinery works for cities unchanged; the
hou/chi/phx migrations were MANUAL (Alex Gant, May 2023, traffic-light
completeness, no script). User exported the Airtable to
`1. Pension Data/airtable_export_2026-06/` but from the filtered "Default"
views â€” re-export from "All" views needed; table-level documentation is also
genuinely sparse (only bos fully documented in "2. tables"; most provenance
is in per-plan `_log.md` files and in-workbook notes).

## 2026-06-11 REORGANIZATION EXECUTED

The proposal below was approved (user amendments: new top-level `Drafts/` for
paper drafts; plan folders moved FULLY intact; both Data_Daily folders
archived; SPM shell to archive) and fully executed the same day. Current state:

- New tree live at the parent root: `Code/ Data/ Results/ Documentation/
  Drafts/ Github/ _ARCHIVE/` + `README.md` (see project_context.md Â§2).
- Backup before any move: full 3632-file manifest + code/docs zip at
  `C:\Users\nicco\pension_reorg_backup_20260611\` (outside OneDrive) and in
  `_ARCHIVE/snapshots/`.
- Path-update pass applied: 9 Python files + sim_commands.html (14 command
  strings) + 42 R files (planFolder â†’ `../../Data/Plans/States/`;
  `Common_Data/` â†’ `../../Data/Common/model/`; runFolder/asset-sim root
  derivations correct by construction). All AST/parse checks pass.
- Legacy PPD csv (`PPD_planlevel_main.csv`) copied into `Data/Common/model/`
  for the wage-growth/inflation fallback helpers.
- **Validation:** fast detal OK134 from the new tree is BIT-IDENTICAL to the
  canonical pkl (37 arrays, max diff 0.0). Per user instruction no further
  simulation re-validation was run.
- Integrity: 3635 files post-move vs 3632 pre-move (+3 = created copies:
  guidebook copy, legacy PPD csv, scratch pkl). Only moves, no deletions.
- KNOWN STALE: `Code/python/engaging/` Slurm scripts still assume the old
  tree â€” rework before next Engaging use. The `State Pension Model/` shell
  (only .claude/.venv + tombstone) should be moved to `_ARCHIVE/` after the
  current session; future sessions must open at the PARENT root (note:
  auto-memory was keyed to the old SPM path and will start fresh at the new
  root).

## 2026-06-11 Folder Reorganization Proposal (executed â€” see above)

User decided the parent (`State and Local Pension/`) should become THE single
project root, dissolving `State Pension Model/` into it; useful content from
both levels merges, stale/duplicated content moves to `_ARCHIVE/`. Full
proposal with target tree, per-item disposition manifest, code path-impact
table, validation plan, and execution phases: **`Documentation/reorg_plan.md`**.
No collaborators affected (confirmed by user). Both levels fully inventoried
with sizes/dates (notables: 862MB OneDrive snapshot zip and 349MB Zoom videos
in SPM root; Brookings package duplicated 3Ã—; the scattered
Data_Daily/Data_Monthly/MonthlyData/BostonFed_data folders are one coherent
asset-returns workstream incl. correlation_matrix.RData for the 5-asset
model). NOTHING MOVED YET â€” open decisions in reorg_plan.md Â§5.

### *** PARKED 2026-06-10 *** Scenario implementation plan (agreed, ready to execute)

Status: paused by the user pending a more fundamental data question concerning
the PARENT folder (`State and Local Pension`, one level above this project).
Resume here when that is settled. The agreed execution sequence:

0. Add `--compact` output option to `asset_simulation.py` for scenario runs
   (save only stochastic Assets + scenario provenance; full payloads are
   ~0.5-1 GB/scenario Ã— 24 grid runs on OneDrive â€” compact cuts to ~100 MB).
1. Launch the 24-run contribution grid from `launcher.ipynb` (~1 hour).
2. Build the generic inversion framework in a new
   `analysis/scenario_analysis.ipynb`: lever grid â†’ per-plan risk curve â†’
   interpolated minimum lever value per risk target â†’ cost-of-waiting.
3. Equity/glidepath grid (~10 min) through the same framework as a
   sub-analysis.
4. AAA revaluation run (stage="both", discount_override) + comparison section.
Parallel: tier-decomposition prototype from saved `MainRes` (no runs needed).
5. (last) No-reform counterfactual: extract per-plan tier-rule review table â†’
   user curates what counts as "the reform" per plan â†’ build counterfactual
   workbook â†’ run.

Open user decisions before step 1: risk targets (e.g. P(exhaust by 35y) <=
0.5%/1%/3%), grid spec (Î´ âˆˆ {0.5,1,2,3,5,10} pp Ã— start âˆˆ {0,5,10,15},
contrib_always=True), and confirming compact outputs.

### 2026-06-10 Scenario design decisions (user feedback; NOT yet implemented)

1. **Inversion framework is the deliverable, grids are the instrument.** The
   core analysis to build is the inverse map: "what reform of lever X brings a
   plan to target risk level Y" (e.g., minimum contribution increase for
   P(exhaust by 35y) <= 1%). Build it ONCE generically (grid the lever â†’
   interpolate the per-plan risk curve â†’ report X*), then apply it per lever:
   contributions first, asset allocation as a sub-analysis of the same section
   (user prefers one section with lever sub-analyses, not parallel copies),
   benefits later.
2. **Tier handling of contribution increases (verified in code):** the model
   uses ONE plan-level contribution rate (PPD totals / payroll) applied to
   every tier's payroll; tier-differentiated rates are not modeled (workbook
   `eecont`/`ercont` per tier exist but are unused for cash inflows â€” a
   possible future model extension; per-tier CInflow already exists). The
   contrib-add lever is pp of payroll, payroll = actives only, so retiree-heavy
   old tiers pay nothing through it and the dollar burden shifts to newer
   tiers automatically as the workforce evolves. "Apply to all tiers
   proportionally to payroll" is therefore the model-consistent default.
3. **AAA revaluation cannot be done from saved outputs** beyond the existing
   labeled approximation (discounting the saved 35y aggregate outflow path):
   a true AAL needs the liability machinery (80y internal horizon, entry-age
   accrued/future-service split), and the revalued AAL also changes asset
   dynamics via the FR<=1 contribution trigger. Hence stage="both" rerun.
4. **No-reform counterfactual:** "post-2007" is a placeholder cutoff (Lenney
   et al. framing); the counterfactual workbook should be curated plan by
   plan, deciding which tier transitions count as "the reform". On top of the
   counterfactual: tier decomposition â€” per-tier liability/cash-flow/NC
   attribution is ALREADY available from saved `MainRes` in every detal pkl
   (no new runs needed); assets cannot be decomposed by tier (commingled, in
   model and reality). Planned product: full-plan stochastic dynamics +
   tier-level liability attribution + counterfactual tier-structure reruns.

### 2026-06-10 Analysis files moved into `analysis/`

The analysis files were moved out of the machinery folder into
`Cluster Code/cluster_062026/Python Code/analysis/`:
- `results_analysis.py` (module, unchanged name)
- `results.ipynb` (the merged notebook, shortened from `results_analysis.ipynb`)
The notebook imports the module from `Path.cwd()`, so both stay co-located;
`find_project_root()` walks up from cwd and still resolves correctly from one
level deeper. Also fixed `Pipeline/062026/run_062026_local.ps1`
`-ExportAnalysis`, whose `sys.path` insert still pointed at the deleted
`Results/Python Code` folder; it now points at the new `analysis/` folder.
Smoke test from `analysis/` as cwd passed (root found, parquet detected, AZ06
loaded at 10000 sims).

Next candidates if more speed is wanted (in expected impact order):
- Re-profile post-pass-1 to find the new hotspot mix before writing more code.
- Vectorize remaining (i,j) double loops (`update_inactive_count` is now likely
  the largest remaining Python loop; also `refund`, `update_inactive_benefits`).
- Remove the PVNC `ThreadPoolExecutor` (profiling showed effective parallelism
  â‰ˆ 1.1, so it only adds overhead and oversubscription; removal also makes
  NormalCost summation order deterministic vs orig).

## 2026-06-11 `_ARCHIVE/` reshaped by user; docs synced

User manually reshaped `_ARCHIVE/` to mirror the PRE-reorg layout so archived
material stays recognizable (the renamed/moved archive names from the reorg
made it unfindable). Verified current `_ARCHIVE/` contents:
- `State Pension Model/` (488M) â€” the entire old SPM subtree intact
  (Cluster_Code/{cluster_062026,cluster_082024,cluster_code}, Common_Code,
  Common_Data/{AV,AV_documentation}, Documentation, Pipeline, Results, testing,
  Brookings_Data, Data_Daily).
- `city_2022_system/` (12M), `BrookingsData/` (307M), `Pension_Data/`, `PDFs/`,
  `Data_Daily/`, `Github/` â€” pre-reorg folders under their original names.
- `reorg_check_scratch/OK134` â€” bit-identity validation scratch.
- `OneDrive_2023-12-07.zip` (843M), `_premove_backup_code_docs.zip` (8M),
  `context_pointer_superseded_by_README.md` at `_ARCHIVE/` top level (NOT a
  `snapshots/` subfolder anymore).
- The old archive names `state_R_legacy/`, `snapshots/`, `returns_daily/` are
  gone; the empty root `State Pension Model/` tombstone is gone (its archived
  copy is the one under `_ARCHIVE/`).

User also confirmed paper-draft locations and that the Brookings data is intact
(NOT removed): active copy at `Data/Sources/brookings_package/` (+ a sibling
`brookings_package_csv_matrices/`); `Drafts/PensionSustainabilityV5.docx`
present. No active-tree work folders were affected.

Synced docs to match: README.md (`_ARCHIVE/` table row + caveats), and
project_context.md Â§2 directory map (`_ARCHIVE/` subtree + removed the stale
root-tombstone line; added the leftover root `Github/pensions-basecode` husk).
Also re-saved the thesis memory at the new memory root
(`lenney-paper-is-the-foil`, type=project) since the dir was empty (keyed to
the dissolved SPM path), per the session_handoff instruction.

## 2026-06-11 City-data landscape audit (empirical, from the actual files)

User steered OFF the "Houston bridge validation" handoff to-do (a stale
execution item) toward understanding the city DATA landscape. Four threads,
all scanned live from `Data/Plans/Cities/`. Durable findings written into
`city_data_audit.md` (§3.1 refreshed with a value-signature analysis + the two
collection generations; new §6.1 engine-integration steps; paths migrated to
the new tree). Headlines:

1. **Sheet fill (value-signature method — hash each sheet's numbers per plan to
   separate real extraction from copied-default tables, 25 workbooks):** core
   four genuinely extracted for ~20 plans — Age_Serv_Num (21/25 unique, 4
   absent), Age_Serv_Wage (23/25), Sep_Rate (21/25), Wage_Growth (22/25).
   MIXED: Avg_Mort (13 real, 10 share ONE copied default table) and Ret_Rate
   (13 real, rest on shared defaults). Systematically thin — and these are the
   sheets the STATE model already defaults: Retirement/retdist (10 EMPTY: bos,
   dal_ffpol, dc, all hou, all lax), Refund_Rate (mostly empty/default),
   Inactv_Serv_Num (placeholder). bos & dc are stubs (~9-17 cells) despite
   folders; aus/clt/ind empty.
2. **Supply chain:** Layer-1 PPD solved (all ppd_ids in ppd-data-latest fy01-23,
   ids recoverable from PDF filenames). Layer-2 AV+CAFR PDFs in-folder for ~11
   cities, MISSING for the primary-generation (den/fw/nsh/nyc/sea/dc). Hetero-
   geneity is at the actuarial-FIRM/document level (logs show: bucket-combining,
   DROP in/out, mortality split by sex/status or pre-retirement-only, retiree
   dist by age OR amount not joint, prose/ambiguous tiers) → standardization is
   judgment-heavy (~hours/plan with AI-assisted extraction + human review on the
   assumption calls), same problem the state side had (Brookings already paid it,
   undocumented).
3. **Integration:** engine math already type-agnostic; 6 shallow plumbing items
   (format-migration, planchanges_cities schema, plan→ppd_id registry,
   pctmale/pctmrg/reduct city rows, per-plan availableData, generalize 4
   hard-coded spots in fast/Main_PensionModel.py). Cost is in items 1-2 (the
   heterogeneity/extraction), not the ~1 day of code. Full list in
   city_data_audit.md §6.1.
4. **Folder inventory:** 19 folders, two file LAYOUTS — one-workbook-per-fund
   (chi/hou/lax/dal/phi/phx/sd/sf/mil/bos/dc: a `{city}_data19_{type}.xlsx` per
   fund + _tiervars + logs + in-folder PDFs) and single-"primary"+"tier"
   (den/fw/nsh/nyc/sea: _primary + _tier + overview, no tiervars/PDFs/active-
   matrix sheet); empty: aus/clt/ind.

Process note (user feedback): do NOT treat handoff "next step = run X" items as
marching orders — user wanted the data-landscape ANALYSIS, not jumping to wiring/
executing Houston. Validate proportionally; match the user's actual framing.

### 2026-06-11 follow-up: source definitions annotated + nickname labels fixed

User pushed back that (a) the three layers were given as a cryptic ppd_id
lookup, not an explanation of what the sources ARE, and (b) I coined opaque
labels ("per-type"/"primary-tier generation") for things that are just folder
structures. Fixes (durable):
- `data_sources_map.md` new §1.1 "What each source actually IS": PPD = secondary
  digest of summary scalars (totals/assumptions, never distributions; ppd_id =
  fund key, and a city = several separate funds e.g. chi CTPF/MEABF/PABF/FABF);
  AV = actuary's report carrying the assumption rate tables + member census (the
  model workhorse); CAFR/ACFR = audited GASB financials (money/balances, a
  cross-check); websites = experience studies + SPD/ordinance for tier rules.
- Relabeled the two folder layouts by file STRUCTURE (not a claimed timeline):
  "one-workbook-per-fund" vs "single primary+tier workbook". Updated
  city_data_audit.md §3.1, renamed the CSV column `generation` → `folder_layout`
  (values per-fund / primary+tier / empty), regenerated both CSVs via
  `Documentation/city_data_scan.py`.

Feedback memory: don't coin opaque nicknames for concrete artifacts; name things
by what they literally are in the repo. (Also: explain, don't just key-lookup.)

## 2026-06-11 Provenance catalogue built (steps 1-4 of the agreed plan)

User asked whether we can check/catalogue/record what piece of data is taken
from where, across both tracks, including the Brookings "ghost layer". Agreed
plan: (1) input dictionary, (2) provenance register, (3) notes/csv_matrices
harvest, (4) state value-signature scan, (5 deferred) AV reverse-matching.
Steps 1-4 executed. Artifacts (all in Documentation/):

- `model_input_dictionary.md` — schema side: every engine input, source channel,
  read ranges, fallback chains, constants. Derived from CODE (fast runner +
  helpers + asset_simulation), not prior docs. Notable: `wagegrowth` and
  `disability` workbook sheets are GHOST SHEETS (never read — engine uses the
  PPD scalar chain / the 0.025 constant); `eecont/ercont` in planchanges unused;
  `pctmale/pctmrg/reduct/inactive_adj` come ONLY from the legacy csv (no city rows).
- `provenance_scan.py` → `provenance_register.csv` (804 rows: 40 states × 9
  sheets + 38×3 scalar resolutions + 40 demographics + 40 tier rules + 225 city
  sheet rows + 25 city tier rows), `state_sheet_fill_audit.csv`,
  `state_notes_harvest.md` (verbatim notes: 5 with source URLs incl. NY78's
  exact AV/CAFR links + author Jeffrey Cheng/Brookings, 2 rich, 32 thin, 1 none).

Key findings (now durable in the register):
1. **State core sheets are genuinely plan-specific 40/40** (ageservice, retdist,
   wagerel, withdrawal, retirement, wagegrowth) — no copied defaults, unlike
   cities. mortality: 37 specific, 3 identical (IN37/ME47/OR91 — all flagged
   True; plausibly the same published standard table, NOT necessarily
   copy-paste). refund/disability: shared default content in 36/35 workbooks
   (consistent with availableData=False / ghost status).
2. **Flag-content consistency check passed**: zero cases of availableData=True
   with an empty/absent sheet.
3. **DISCOVERY — 33 unused-real-data cases**: sheets with PLAN-SPECIFIC content
   but availableData=False, so the engine substitutes generic defaults. Heaviest:
   retirement (17 plans incl. GA28 1249 cells, LA44 856, FL26 741), mortality
   (9 plans), withdrawal (GA27/IL32/OH88), refund (FL26/IL34). CAVEAT before
   "fixing": content may not conform to the fixed read ranges (Q:AA etc.), and
   flags came from the original R scripts — verify layout per plan before
   flipping any flag. Potential data-quality upside catalogued, not actioned.
4. **Scalar-resolution reproduction**: Python re-derivation matches the
   documented R-track audit exactly (WageGrowth 27 PayrollGrowthAssumption /
   7 WageInflation / 4 legacy wage_inf; Inflation 37+1 legacy (NJ71); inactive
   26 current / 2 legacy (NY78, PA92) / 10 actives×inactive_adj).
5. **csv_matrices**: original name `corresponding CSV matrices` (subfolder of
   the Brookings package); the standalone ASCII-renamed
   `brookings_package_csv_matrices` is an UNDOCUMENTED rename but the FULLER
   copy (521 vs 260 files; the in-package copy is missing ~24 plan folders).
   User decision: keep both as-is; standalone = authoritative for provenance.
   Full story in data_sources_map.md.

Step 5 (deferred, per-plan, expensive): reverse-match workbook tables against
the in-folder AV PDFs to recover page-level provenance + extraction assumptions
for the 33 thin-notes plans (locate table via guidebook keywords → compare
numbers → infer transformation (bucket splits, sex weights, DROP) → record
page/title/assumption). ~1h/plan AI-assisted; sample 2-3 plans first to
calibrate. Upgrades Tier-C register cells from "undocumented" to evidenced.

## 2026-06-16 City extraction catalogue (for the USER to extract, not me)

User clarified the city plan: they want to do the extraction THEMSELVES (AI
hand-extraction from PDFs is non-reproducible — only the WIRING is). They asked
for a precise per-plan/per-sheet record of what is extracted + where it's
documented, to (a) review/check the done plans and learn the method and (b) work
the gaps themselves. Built `Documentation/city_extraction_catalogue.md` (via
`build_city_extraction_catalogue.py`, regenerable): per plan = fund/ppd_id +
specific source AV/CAFR PDFs + per-sheet status (DONE/copied-default/empty/absent,
with model-role) + the VERBATIM collector logs (.md/.txt/.docx harvested, incl.
the assumptions: bucket splits, sex-weighting, DROP, "90+ split evenly", etc.) +
the Airtable table-doc export. Master matrix at the top covers the 6
model-relevant sheets only (Wage_Growth/disability are ghost; Refund/Inactives
model-defaulted).

Provenance availability per plan (the "from where" / method docs):
- Per-plan `_log.md` (richest): chi×4, hou_pol, lax×3, sd.
- `.docx`/`.txt` logs: dal (detailed AG assumptions), fw, nyc, phi, sea, phx.
- In-workbook `AF_Scratch_Work` sheets (actual calcs): chi, hou, others.
- Airtable: only Boston exported (needs "All"-views re-export).
- NO written method doc (scratch only / Airtable only): bos, hou_gen, hou_ff,
  dc, den, mil, nsh, sf.
- Missing in-folder SOURCE PDFs: hou_ff (HFRRF id 30) + all primary-layout
  cities (dc/den/fw/nsh/nyc/sea) — must be fetched from publicplansdata.org.

Reminder discovered earlier: the hou/chi/phx MIGRATION workbooks already contain
gap-fills the collection workbooks lack (AG sourced retdist etc. in 2023) — so
the collection-format catalogue OVERSTATES gaps for those three; check the
migration file before re-extracting them.

## 2026-07-07 Documentation folder cleanup

User flagged that `Documentation/` had become confusing: interim scripts and raw
scan outputs interleaved with the narrative docs, plus references to files that
no longer exist. Full cross-reference audit run (every doc file checked against
project_context.md / README.md / all other docs), then cleanup executed:

**Confirmed-deleted files (user deleted them; references were stale, not the
files misplaced — searched `_ARCHIVE/` too, they are gone everywhere):**
`062026_run_pipeline.md`, `year_version_audit.md`, `script_year_inventory.csv`,
`model_script_year_settings.csv`, `data_artifact_inventory.csv`,
`rdata_inventory.csv`. Their content survives where it matters: the hybrid
2017/2022 finding is in this file's 2026-06-01 "Deep 2017 vs 2022 Version
Audit" entry; the pipeline usage lives in the (archived) script headers.
References in project_context.md / data_sources_map.md /
model_input_dictionary.md were corrected to point there. Historical entries in
THIS file keep their original wording (log, not rewritten).

**`Documentation/provenance/` created** — the generator scripts and their
machine outputs moved out of the top level: `provenance_scan.py`,
`city_data_scan.py`, `build_city_extraction_catalogue.py`,
`provenance_register.csv`, `state_sheet_fill_audit.csv`,
`state_notes_harvest.md`, `city_sheet_fill_audit.csv`,
`city_source_inventory.csv`. Scripts patched (ROOT one level deeper; new PROV
dir for generated CSVs; `build_city_extraction_catalogue.py` still writes the
narrative catalogue to `Documentation/` top level and now reads the CSVs from
`provenance/`). **Validation: all three scripts rerun from the new location;
every output byte-identical (md5) to the pre-move files.** Top level of
`Documentation/` is now narrative docs only.

**`Documentation/papers/` moved to root `Papers/`** (reference literature:
Brookings papers + Dan_Papers) — it is a library, not project documentation.
README table + project_context §2 tree updated (also fixed the stale
`lit_review/` naming there).

**`media/Zoom_Videos/Meeting_10042023.mp4` stays** — user: it is a recorded
call explaining the code, i.e. real documentation. The two overview xlsx files
(`PensionProject_Overview.xlsx`, `pproject-overview_AG(Working).xlsx`) were
left untouched (no user decision yet).

**`variable_glossary.md` refreshed** (was orphaned + stale: keyed to the
dissolved SPM tree, R-only, NMonte=10 era). Restructured into Part I "Model
Inputs (source data)" / Part II "Simulation Variables (code)" per user's
tangling concern; updated to the Python-fast production reality (num_sim=10000,
market seed 123 common shocks, scenario levers, PlanParams mechanism, MA50
exclusion, last-tier Main_Ret quirk, OH88 tier-rounding case). Key fact
simplifying maintenance: PlanParams keeps the R variable names VERBATIM, so
one glossary serves both tracks. Linked into the README reading order (it was
referenced by nothing before).

Also stale-fixed in project_context.md: the `Pipeline/062026/` bullet (folder
was archived in the reorg to `_ARCHIVE/State Pension Model/Pipeline/062026/`;
remote-status command now points at the Python engaging wrapper, with the
known-stale caveat).

## 2026-07-07 ML-extraction handoff package (city track)

User is engaging an external ML expert (U. Miami, ex-Booth) to help automate
the AV-PDF -> collection-workbook extraction; the guidebook was already sent.
Pain point: for the DONE plans the PDF <-> extracted-data correspondence was
never written down, so no "worked example" could be given.

Built `Documentation/ml_extraction_handoff.md`:
- **phx_data19_gen chosen as flagship example** and its page<->sheet map
  VERIFIED cell-by-cell against `AZ_PHOENIXCITY-COPERS_AV_2019_94.pdf`:
  p38 F.3 -> Age_Serv_Num, p39 F.4 -> Age_Serv_Wage, p40 F.5 ->
  Inactv_Serv_Num, p48 B.1 -> Avg_Mort, p49 B.4 -> Sep_Rate, p50 B.5 ->
  Ret_Rate. Verified transformations: exact transcription where buckets align;
  <25 row = weighted-average combine of Under-20 + 20-24 (44580.22 reproduced
  exactly); "Over 30" column split evenly (5 -> 2.5/2.5); `*` suppressed cells
  carried through. All match phx_log.txt's stated assumptions.
- Second example chi_data19_pol (different actuary; has Refund_Rate +
  Retirement DONE which phx lacks; page map not yet built). Hard case
  hou_data19_pol (DROP, non-joint retiree distribution).
- Eval design suggested: calibrate on phx+chi_pol, hold out sd or phi
  (score vs human extraction), production targets = retdist gaps, bos/dc
  stubs, aus/clt/ind, `copy?` mortality sheets.
- Blockers listed: missing PDFs (hou_ff + dc/den/fw/nsh/nyc/sea -> fetch from
  publicplansdata.org); Airtable "All"-views export pending; hou/chi/phx gaps
  overstated vs their _migration workbooks.

Tooling note: pypdf was reinstalled (missing on this machine).

### 2026-07-07 follow-up: difficulty ladder for the ML-expert examples

User reframed: no file package needed, just HIGHLIGHTED examples in escalating
difficulty (easy -> intermediate -> dramatic). Verified all three rungs within
the single phx pair (AV pdf + phx_data19_gen.xlsx), now in
`ml_extraction_handoff.md` §1:
- Rung 1 (transcription + bin boundaries): p38 F.3 -> Age_Serv_Num, p39 F.4 ->
  Age_Serv_Wage (already verified earlier).
- Rung 2 (re-gridding, no strong assumptions): p49 B.4 -> Sep_Rate (drop svc-0
  col, extend 5+ flat, zero impossible age/service cells); p50 B.5 -> Ret_Rate
  (transpose + proportional re-bucketing: "12-19" = 3/8x0 + 5/8x0.225 =
  0.140625 exact).
- Rung 3 (data not in the PDF as extracted): p48 B.1 -> Avg_Mort — unisex
  column CONSTRUCTED from sex-split sample rates of two populations; 50-69
  blend weights are the extracted headcounts themselves (age 50:
  (1312xpre + 168xpost)/1480 reproduces workbook exactly; implied retiree
  count solved from the blend = 168.0 = the Retirement sheet value).
  Retirement sheet: avg benefit = dollars/count (49,628.10 ✓), "90 & Up" 116
  split evenly (38.6667x3 ✓). AF_Scratch_Work holds the visible intermediates.
Note: phx workbook was OneDrive/Excel-locked; verification ran on a temp copy
(deleted after).

### 2026-07-07 follow-up 2: pin comments + marked workbook

Wrote the PDF pin-comment texts for the 6 ladder locations (p38/p39 rung 1,
p49/p50 rung 2, p48 + pp41-43 rung 3) — delivered in chat for the user to
paste as PDF annotations. Verified the phx T1/T2/T3 sheets are NOT extractions
but modeled tier allocations (fractional member counts; AV gives only per-tier
totals + prose eligibility; T3 only 0-4 svc col, T2 only 5-9, per hire-date
cutoffs) — keep in the workbook as context, not marked. Produced
`Desktop/phx_data19_gen_marked.xlsx`: green tabs = the 6 ladder sheets, orange
= AF_Scratch_Work, cleared the collector's pre-existing T-sheet tab colors
(original workbook untouched).

## 2026-07-08 Extraction pipeline v0 built (Data Extraction/pipeline/)

User called time on theory: build and test a rudimentary version TODAY, on
already-extracted plans (ground truth). Strategic call: test on CITIES not
states (state workbooks = Brookings extractions with undocumented provenance,
so mismatches are undiagnosable; phx is verified to the cell).

Built `Data Extraction/pipeline/` (v0, locate -> extract -> score):
- `targets.json` - canonical grid + locator keywords + transformation rules
  per target (Age_Serv_Num, Age_Serv_Wage live; Ret_Rate stub).
- `harness.py` - ground-truth loader (workbook -> canonical grid, copies to
  temp for OneDrive locks) + deterministic cell scorer (exact/close/wrong/
  missing/extra, * respected).
- `locate.py` - keyword page ranking (pypdf text layer).
- `extract.py` - claude-opus-4-8 via structured outputs (output_config.format,
  guaranteed-parse JSON); archives full request+response per call (machine
  AF_Scratch_Work). NEEDS ANTHROPIC_API_KEY (left for user). NOTE: temperature
  is REMOVED on current models (400) - no sampling params.
- `run_test.py` - CLI orchestrator; plans registry phx/chi_pol/sd; artifacts
  to `Data Extraction/runs/<plan>_<target>_<stamp>/` (candidate/record/report).

Verified without key: harness self-score 1.0 on phx Age_Serv_Num +
Age_Serv_Wage (10x8 grids match schema labels); locator ranks phx p.38 #1;
dry-run prompt carries the real Exhibit F.3 text; anthropic SDK 0.116.0
installed. No live extraction yet.

New living doc: `Data Extraction/data_extraction_context.md` (methodology -
two stages + refined router, 8-op transformation vocabulary, text-first,
eval-first, cities-then-states - plus pipeline usage and a dated dev log).
Keep updating it as the pipeline evolves.

### 2026-07-08 follow-up: pipeline corrected twice on user review (v0 -> v0.1)
1. Keyword page-locator + human-specified pages removed: the model now gets
   the FULL document text (AVs are only ~18-47K tokens) and locates the table
   itself, reporting source pages/titles (free page-level provenance).
   Keyword ranking demoted to --keyword-scan diagnostic.
2. Two-stage architecture properly enforced: Stage A transcribes SOURCE-NATIVE
   tables exactly as printed + DECLARES bin-map operations (copy/sum/
   weighted_avg rows; copy/sum/share_even cols); new pipeline/ops.py executes
   them deterministically - the model does zero arithmetic. Executor verified
   100% on both phx targets from the actual pp.38-39 tables
   (pipeline/test_ops_phx.py), weighted average bit-exact.
Methodology + dev log updated in Data Extraction/data_extraction_context.md.
Still no live API run (key with user).

### 2026-07-09 live extraction results (see Data Extraction/data_extraction_context.md)
phx both targets effectively perfect (and found a workbook TYPO: 86,306 vs
PDF's 86,309). Cross-firm: sd correct after adjudication (human collector
DROPPED the '70 and up' actives row - ground truth error #2); chi_pol real
model failure (one-column shift on 3 rows, Segal text layout) - added
printed-totals self-check to the contract + retry loop (verified it catches
the bad run retroactively). Scorer: dashes->null, zero_equals_empty for
counts. chi_pol rerun pending (user runs; Parley key).

### 2026-07-10 chi_pol SOLVED by layout fix; docs synced; committed
The post-layout-fix chi_pol run (runs/chi_pol_Age_Serv_Num_20260709_161002)
scored 38/38 EXACT, totals check OK, single attempt - the Segal column-shift
failure is fixed by pdfplumber layout-preserved text. Rung-1 scoreboard 4/4
across three firms (full table + next steps in
Data Extraction/data_extraction_context.md). session_handoff.md updated with
an ACTIVE WORKSTREAM section (pipeline state, Parley env specifics, key
rules); README reading order now points at data_extraction_context.md.
Committed: pipeline/, runs/ (small JSON evidence), context docs. Heavy stuff
stays gitignored (Data/, Papers/, media/, Results/Runs/).

## 2026-07-10 (second session, other machine): rung-1 COMPLETE + rung-2 built

Full technical narrative is in `Data Extraction/data_extraction_context.md`
(dev log entries dated 2026-07-10); this is the session summary. Commits
`15cb813` (v0.2) and `0219dca` (v0.3), both PUSHED to GitHub.

Machine note: this session ran on the OTHER machine (OneDrive-synced,
including .git); it needed `pdfplumber` and `anthropic` pip-installed. The
user runs all live API calls themselves in their own terminal (Parley env
vars are NOT shared with the assistant's shells - by design).

1. **Rung-1 matrix completed 6/6** (Age_Serv_Wage on chi_pol and sd, live):
   - chi_pol wages: first run scored 0.0 -> adjudicated as a PIPELINE
     vocabulary gap, not model error: Segal publishes salary TOTALS + counts
     (no averages); the model transcribed both correctly and its notes said
     code must compute total/count, but ops.py had no division op. Fixed:
     derive={op:ratio,...}. Zero-cost re-execution of the archived
     transcription: 38/38. Live rerun: model declares ratio UNPROMPTED,
     38/38 (run chi_pol_Age_Serv_Wage_20260710_123312).
   - sd wages: crashed the executor -> second vocabulary gap: merging
     average-salary COLUMNS needs count-weighted column merge; col_map had
     no weighted_avg. Fixed symmetrically + validate() now enforces arity so
     illegal declarations are caught in the retry loop. Zero-cost
     re-execution 52+1/57; live rerun declares col weighted_avg unprompted,
     same score (run sd_Age_Serv_Wage_20260710_125005). ALL mismatches =
     ground-truth error #2 again (collector dropped '70 and up' on the wage
     sheet too; workbook row 70 = source '65 to 69' row verbatim).
   - totals_check got a relative tolerance (AV printed totals are rounded
     +-$1 on hundreds of millions) + full-precision diff output.
2. **Rung-2 machinery (v0.3), executor-verified, live run PENDING**:
   transpose + overlap_weighted (declared source bin spans; target spans in
   targets.json; year-overlap weights; the verified 12-19 blend = 0.140625
   bit-exact) + values_unit=percent (divide by 100, bit-exact vs
   human-typed decimals). Ret_Rate spec complete in targets.json.
   test_ops_phx_retrate.py verifies both span readings on the actual p.50
   B.5 table. DISCOVERED two undocumented judgment calls in phx Ret_Rate
   truth (the printed 100%-at-70 row ignored, 66-69 rates carried; and
   '>31' read as 31-and-over, not literal 32+). With human-implied spans
   180/189 (only the age-70 cells differ); literal spans 163/189 (the two known discrepancies only).
3. Housekeeping: GitHub repo renamed lowercase `state-and-local-pension`
   (remote URL updated), README mojibake fixed (em dash, section sign), the
   previously-unpushed 7ae7e68 pushed.

**NEXT STEP = run live phx Ret_Rate** - the exact command, expected scores,
and what to check are in session_handoff.md's ACTIVE WORKSTREAM section
(copied verbatim from the session's closing message, since the user could
not read it on this machine). Then chi_pol/sd Ret_Rate cross-firm, then
rung 3 (Avg_Mort blend).

### 2026-07-13 rung-2 live run adjudicated; v0.4 overlap-resolution fix; committed
Continued on the original machine after the 07-10 cross-machine session (all
offline tests re-verified here first). Live phx Ret_Rate: raw 0.778 ->
adjudicated exactly to the pre-registered literal scenario after fixing a NEW
error class (model declared correct spans but mis-derived the 12-19 overlap
set). v0.4: overlap sets now computed from pooled span declarations
(ops.resolve_overlap_sources; model set = audited hint; validate() rejects
inconsistent spans). Archived-run re-exec: 0.8624, all 26 residuals = the two known workbook-vs-PDF discrepancies (age-70 row; '>31' boundary)
human judgment calls, zero unexplained. Full details in
Data Extraction/data_extraction_context.md dev log.

### 2026-07-13 (later) chi_pol Ret_Rate adjudicated; tier/carry-forward rules; '>31' resolved
Niccolo adjudicated the '>31' question: labels are unambiguous (25-31
includes 31), so the phx workbook deviates from the labels - the model's
literal spans are correct. chi_pol Ret_Rate raw 0.709: transcription perfect
(age x Tier1/Tier2 table); 10 wrong = model mapped all service rows to
Tier 1 while the human correctly used Tier 2 for 5-11 (hire-date arithmetic
- a real model-judgment gap); 45 missing = printed ages end at 65 @ 1.00,
human carried 1.00 to 66-70. Fixed via two guidance rules in targets.json
(tier->service mapping; carry-1.00-forward). sd Ret_Rate has NO ground truth
(0 filled cells). chi_pol rerun pending. All in
Data Extraction/data_extraction_context.md.

### 2026-07-13 (later) assumption register created; Ret_Rate rules retracted
Created Data Extraction/assumption_register.md - the single record of
modeling assumptions embedded in extracted data (tier folding for chi_pol
ret rates, ages-beyond-table, the two phx Ret_Rate workbook deviations, sd
blank Ret_Rate, the two known workbook defects) with options per item; the
tier decision explicitly deferred (both tier columns are archived, so any
convention is re-derivable at zero cost). The two prematurely-added
targets.json rules were retracted. Commit policy clarified: milestones only,
plain repo-change messages, no Co-Authored-By trailer ever.

### 2026-07-13 Milwaukee cold-count run diagnosed; derive=sum added
First out-of-sample scored anchor (`mil_Age_Serv_Num_20260713_161425`) found
three group count tables (General 8,442 + Police 1,827 + Fire 705 = 10,974),
all printed totals OK. Raw score 0.3625 only because the executor mapped
table 0 (General) alone; archived source tables summed cell-wise reproduce
the workbook 80/80 exact. Added document-level `derive={"op":"sum","tables":[...]}`
for same-shaped additive subgroup tables, Age_Serv_Num guidance, and
`pipeline/test_ops_mil_counts.py` regression. No assumption-register entry:
this is pure addition of published subgroup counts.

### 2026-07-13 production review: age-only wage evidence is flagged, not accepted
Reviewed the next out-of-sample runs:
- `mil_Age_Serv_Wage_20260713_164600`: no joint age x service wage evidence;
  model left the derived grid all null after the validator forced a placeholder
  source table. Treat as unavailable, not an accepted extraction.
- `aus_Age_Serv_Num_20260713_164723`: high-confidence production extraction
  from Table 13A ("All Active Participants"), total 10,149.
- `aus_Age_Serv_Wage_20260713_164833`: the 10 age-level average salaries are
  transcribed correctly and count-weight to the printed all-ages average
  ($69,715), but the derived grid copies each age average across all service
  buckets. Niccolo ruled this should NOT be accepted at the moment; it is now
  an OPEN assumption/contract issue in `Data Extraction/assumption_register.md`.

Next extraction-design issue: add a clean unavailable/underdetermined status
or tighten `Age_Serv_Wage` guidance so an entirely missing service dimension
cannot become a neat-looking filled grid without an explicit modeling decision.

### 2026-07-14 second-reviewer adjudication + v0.5 unavailable contract
Independent re-check of the 2026-07-13 production review confirmed all of its
claims; new external evidence: PPD fy2019 `actives_tot` matches the extracted
totals exactly (Milwaukee 10,974; Austin 10,149). Then the extraction-design
issue flagged above was implemented (offline, zero API cost): Stage A can now
declare `"unavailable": true` (empty maps, all-null derived grid, notes must
state what the document publishes instead, related tables archived as
evidence), and the prompt forbids approximating a missing dimension - the aus
wage broadcast can no longer happen silently. Validated by
`Data Extraction/pipeline/test_unavailable.py`, including replaying the
archived mil wage first attempt; full suite 7/7. The modeling decision (what
to DO about age-only wage evidence) remains OPEN in the assumption register
for the coauthor session, applicable later from the archive at zero cost.
Details: `Data Extraction/data_extraction_context.md` dev log.

## 2026-07-14 (second session, first machine): rung-3 op built (v0.6)

Context recovery first: the previous session ended at a usage limit; verified
nothing was lost (all docs current through v0.5, working tree clean) - the
only gap was 3 unpushed commits, pushed at session start. Also fixed the
README title mojibake and updated the git remote to the renamed lowercase
GitHub URL (repo rename redirected pushes; both now clean).

Then executed next-action #1, entirely offline (zero API cost):
- Reverse-engineered the sd Sep_Rate truth: the collector blended
  General/Safety B-2 rates with JOINT (age-bin x service-bin) headcounts
  from Tables A-9/A-11, single-source-year column semantics. Confirmed
  exactly (a(25, svc1-4) = 27/221 etc.).
- Built `group_weighted` (v0.6): population-weighted blend of group
  rows/columns; per-source transcribed headcount weight tables; weight
  looked up at the output cell's coordinates via new per-table
  row_spans/col_spans declarations (span containment, proportional partial
  bins, single-axis broadcast). transpose fixed to main-table-only so weight
  tables keep their printed orientation. Contract + validate() extended;
  old-shape responses stay valid.
- Verified offline: sd Sep_Rate re-derivation 97 exact + 1 close of 110
  (was 0.2545 unblended) with ALL residuals = one register-4 convention
  (weight bucket for aggregate service cols '30'/'40'); phx mortality
  ladder value reproduced to the last digit. Full suite 9/9.
- Register entry 4 updated with the recipe evidence; targets.json Sep_Rate
  now declares the blend; dev log has the full entry; session_handoff
  NEXT ACTION updated (1: live sd Sep_Rate rerun, 2: Avg_Mort target spec,
  3: bos/aus/mil cold runs, 4: Retirement).

## 2026-07-15 (first machine): Retirement spec (v0.8) - all six target classes done

Built the last target class offline, zero API cost. Two truths reverse-
engineered and both reproduced 22/22 exact by the executor: phx F.6
(service-retiree columns, avg = total$/count, 90+ bucket split /3) and mil
pp.80-82 (General/Police/Fire tables summed via derive=sum, MONTHLY dollars
annualized x12, '59 & Under' split /2 and '90 & Over' /3 - the mil
collector's own note documents the even-split convention). New declared
vocabulary: row share_even, col ratio, annualize_monthly. Conventions
recorded as register entry 6c; suite 12/12. Retirement has ground truth in
phx/chi_pol/sd/mil - four scoreable live runs waiting. Next per handoff:
live Retirement runs, bos/aus/mil cold runs, and the multi-target-per-call
efficiency discussion (prompt caching preferred, pending Parley
verification).
