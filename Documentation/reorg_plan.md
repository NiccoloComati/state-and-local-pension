# Reorganization Plan: One Project Root

**Created:** 2026-06-11 â€” **STATUS: EXECUTED 2026-06-11** (with user amendments: Drafts/ folder added; plan folders moved fully intact; Data_Daily archived; see working_context.md for the execution record).
**Principle:** `State and Local Pension/` becomes THE single project root. The useful content of both levels merges into one clean tree; everything stale/duplicated moves (never copies) into `_ARCHIVE/`. No collaborators affected (confirmed). Moves stay within the same OneDrive library (cheap, version history preserved).

---

## 1. Target Tree

```
State and Local Pension/
â”œâ”€â”€ Code/
â”‚   â”œâ”€â”€ python/                  # THE production engine (from Cluster Code/cluster_062026/Python Code/)
â”‚   â”‚   â”œâ”€â”€ fast/  analysis/  validation/  engaging/
â”‚   â”‚   â”œâ”€â”€ Main_PensionModel.py, asset_simulation.py, run_simulation.py,
â”‚   â”‚   â”œâ”€â”€ scenarios.py, scenario_launcher.ipynb, sim_commands.html, g.py, ...
â”‚   â”‚   â””â”€â”€ config/              # plans_38.txt (from Pipeline/062026/)
â”‚   â””â”€â”€ R/                       # verified reference implementation
â”‚       â”œâ”€â”€ cluster_code_2022/   # 38 plan scripts (from cluster_062026/)
â”‚       â””â”€â”€ Common_Code/         # shared R functions (from cluster_062026/)
â”œâ”€â”€ Data/
â”‚   â”œâ”€â”€ Plans/
â”‚   â”‚   â”œâ”€â”€ States/              # 40 plan folders (from State Pension Model/Plans/)
â”‚   â”‚   â”‚   â””â”€â”€ [PLAN]/          # [PLAN]_2017.xlsx + AV/CAFR PDFs (old per-plan RData â†’ archive)
â”‚   â”‚   â””â”€â”€ Cities/              # canonical city collection (from 1. Pension Data/{city}_modeldata/)
â”‚   â”‚       â”œâ”€â”€ {city}/          # workbooks, tiervars, _log.md, source PDFs
â”‚   â”‚       â””â”€â”€ _migration/      # modeldata_template + hou/chi/phx migrations + planchanges_hougen-ag
â”‚   â”œâ”€â”€ Common/                  # active common data (from cluster_062026/Common_Data/):
â”‚   â”‚                            # ppd-data-latest, planchanges_main_2022_clean, default_assumptions,
â”‚   â”‚                            # inactive_supplement_2022, PPD_planlevel csvs, city default_assumptions
â”‚   â”œâ”€â”€ Returns/                 # asset-class return series + correlation matrices
â”‚   â”‚   â”œâ”€â”€ daily/  monthly/     # (from Data_Daily, Data_Monthly, MonthlyData â€” dedup by date)
â”‚   â”‚   â””â”€â”€ bostonfed/           # (from BostonFed_data)
â”‚   â””â”€â”€ Sources/                 # raw upstream material, single copies
â”‚       â”œâ”€â”€ brookings_package/   # ONE unzipped copy of the replication package (workbooks + PDFs)
â”‚       â”œâ”€â”€ airtable_export/     # (from 1. Pension Data/airtable_export_2026-06/)
â”‚       â””â”€â”€ collection_templates/# 3. Templates content + guidebook.md copy
â”œâ”€â”€ Results/                     # moved as-is (from State Pension Model/Results/)
â”‚   â””â”€â”€ Runs/062026/...          # canonical run + scenario folders
â”œâ”€â”€ Documentation/               # from State Pension Model/Documentation/ +
â”‚   â”‚                            # guidebook.md, overview trackers (pproject-overview_AG, PensionProject_Overview),
â”‚   â”‚                            # PensionSustainabilityV5.docx, readme_code, meeting notes
â”‚   â”œâ”€â”€ lit_review/              # (from Lit_Review/)
â”‚   â””â”€â”€ media/                   # Zoom_Videos
â””â”€â”€ _ARCHIVE/                    # everything superseded, moved not copied (see Â§3)
```

Naming note: `Plans`, `Results`, `Common*` anchor names are kept recognizable; the deep "Cluster Code/cluster_062026" nesting disappears.

## 2. Path Impact On Code (the only risky part â€” fully enumerable)

The Python engine derives paths from `__file__`/cwd. Required mechanical updates after the move (one scripted pass + validation):

| File | Current assumption | Change |
|---|---|---|
| `fast/Main_PensionModel.py` | root = `cluster_062026/../..`; plans at `ROOT/Plans/[PLAN]`; Common_Data at `cluster_062026/Common_Data` | root = `Code/../`; plans at `ROOT/Data/Plans/States/[PLAN]`; common at `ROOT/Data/Common` |
| `Main_PensionModel.py` (original) | same pattern | same change (kept runnable as reference) |
| `asset_simulation.py` | `project_root()` = 3 levels up | 2 levels up (`Code/python/..`) |
| `run_simulation.py` | ROOT + `Pipeline/062026/plans_38.txt` | ROOT + `Code/python/config/plans_38.txt` |
| `scenarios.py` | ROOT = 3 levels up | 2 levels up |
| `analysis/results_analysis.py` | `find_project_root()` looks for `Results/` + (`Common_Data` or `cluster_062026`) | look for `Results/` + `Data` (or `Code`) |
| `engaging/*.sh`, `remote_python_run.ps1` | `CLUSTER_DIR = ROOT/"Cluster Code/cluster_062026"` | `ROOT/Code/python` (+ upload list paths) |
| R `cluster_code_2022/*.R` (38 files) | `planFolder ../../Plans/`, runFolder depth | scripted path pass (done twice before; same technique) |
| Notebooks (`launcher`, `results`) | co-located imports â€” unaffected | none |

**Validation after the move (already built):** rerun fast detal OK134 â†’ must be bit-identical to the existing pkl; launcher demo asset run; `results.ipynb` smoke execution. These three checks prove the relocation end-to-end.

## 3. Disposition Manifest

### KEEP â†’ new home (move)
| Item | From | To | Size |
|---|---|---|---|
| Python Code (all) | `SPM/Cluster Code/cluster_062026/Python Code/` | `Code/python/` | small |
| R 2022 scripts + Common_Code | `SPM/Cluster Code/cluster_062026/` | `Code/R/` | small |
| plans_38.txt | `SPM/Pipeline/062026/` | `Code/python/config/` | tiny |
| State plan folders (workbook+PDFs) | `SPM/Plans/` | `Data/Plans/States/` | ~250 MB |
| City collection | `1. Pension Data/{city}_modeldata/` | `Data/Plans/Cities/{city}/` | ~1.5 GB (PDF-heavy) |
| Migration bridge | `BrookingsData/local pensions data migration/` + `planchanges_hougen-ag.xlsx` | `Data/Plans/Cities/_migration/` | small |
| Active common data | `SPM/Cluster Code/cluster_062026/Common_Data/` | `Data/Common/` | ~50 MB |
| City default_assumptions + variablesdb | `1. Pension Data/`, `4. Database/variablesdb_v2.csv` | `Data/Common/` | tiny |
| Returns workstream | `Data_Daily` (parent+SPM, dedupâ†’newest), `Data_Monthly`, `MonthlyData`, `BostonFed_data` | `Data/Returns/` | ~10 MB |
| Brookings package (unzipped, ONE copy) | `BrookingsData/public pensions data/` | `Data/Sources/brookings_package/` | ~600 MB |
| Airtable export | `1. Pension Data/airtable_export_2026-06/` | `Data/Sources/airtable_export/` | tiny |
| Collection templates + guidebook copy | `3. Templates/`, `Github/.../guidebook.md` | `Data/Sources/collection_templates/` + `Documentation/` | tiny |
| Results | `SPM/Results/` | `Results/` | ~2 GB |
| Documentation + paper + trackers | `SPM/Documentation/`, `PensionSustainabilityV5.docx`, `pproject-overview_AG(Working).xlsx`, `PensionProject_Overview.xlsx` | `Documentation/` | small |
| Lit review | `Lit_Review/` | `Documentation/lit_review/` | 56 MB |
| Zoom videos | `SPM/Zoom_Videos/` | `Documentation/media/` | 349 MB |

### ARCHIVE â†’ `_ARCHIVE/` (move; grouped by era)
| Group | Items |
|---|---|
| `_ARCHIVE/state_R_legacy/` | `SPM/Common_Code/` (root copy), `SPM/Common_Data/` (2017 baseline, 111 MB), `SPM/Cluster Code/cluster_082024/`, `SPM/Cluster Code/cluster_code/`, `SPM/Pipeline/` (rest), `SPM/testing/`, per-plan legacy `.RData`/csvs inside plan folders, SPM root strays (`.RData`, `.Rhistory`, logs, `LA130_2017.xlsx` stray, `NY78_Asset_Sim.csv`, `PlanAccuracy.*`), old R result scripts if any remain |
| `_ARCHIVE/city_2022_system/` | `2. Code/`, `4. Database/` (minus variablesdb), parent `asset_simulation.R`, `planchanges_main-ag.xlsx`, existing `ARCHIVE/` contents fold in |
| `_ARCHIVE/snapshots/` | `SPM/OneDrive_2023-12-07.zip` (862 MB), `SPM/Brookings_Data/` zip (309 MB), `BrookingsData/public pensions data.zip` (314 MB), `1. Pension Data/Archive`, `1. Pension Data/public pensions data` (duplicate unzip), `1. Pension Data/sql_dbimport|testdata`, `PDFs/` |
| Keep in place | `Github/pensions-basecode` (it's a git repo; add README pointing to new docs). `Individual Folders/.../Alex Gant/` (not ours to move). |

### DELETE â€” nothing. Everything moves; deletion decisions can come later once the new tree is proven.

## 4. Execution Phases (each reviewable)

1. **Phase 0 (this doc):** approve manifest; decide open names (Â§5).
2. **Phase 1 â€” data & docs** (no code dependencies): create skeleton, move `Data/*`, `Documentation/*`, archive sweep of snapshots/legacy data. OneDrive settles overnight if needed.
3. **Phase 2 â€” code & results:** move `Code/` + `Results/`, scripted path updates (table Â§2), then the three validation checks (bit-identity OK134, launcher demo, notebook smoke).
4. **Phase 3 â€” cleanup:** SPM folder should now be empty except archived remainders â†’ its residue moves to `_ARCHIVE/`, the empty `State Pension Model/` folder is removed (or kept as empty tombstone with a pointer note).
5. **Phase 4 â€” docs refresh:** update `project_context.md` Â§2 tree, `context_pointer.md` â†’ root-level `README.md`, memory note.

## 5. Open Decisions For User

1. Approve target tree names (`Code/Data/Results/Documentation/_ARCHIVE` â€” or different naming taste).
2. City raw data: move the heavy source PDFs (~1.5 GB) into `Data/Plans/Cities/` too, or leave PDFs in `_ARCHIVE/` and move only workbooks/logs/tiervars? (Recommend moving them â€” they are the provenance.)
3. `State Pension Model/` end state: delete the empty folder or keep a tombstone pointer?
4. Returns dedup: parent `Data_Daily` (2024) vs SPM `Data_Daily` (2026-05) â€” keep newest as canonical, older to archive? (Recommend yes.)
