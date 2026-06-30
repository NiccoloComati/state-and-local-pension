# Municipal (City) Pension Data Audit

**Created:** 2026-06-10
**Updated:** 2026-06-11 — paths migrated to the reorganized tree (canonical city data is now
`Data/Plans/Cities/{city}_modeldata/`, bridge at `Data/Plans/Cities/_migration/`, city commons at
`Data/Common/municipal/`); §3.1 sheet-fill refreshed with a value-signature analysis (filled vs
copied-default vs empty), and the two collection generations are now distinguished. NOTE: §3.3–§3.7
still cite some PRE-reorg parent-folder paths (`pproject-overview_AG`, `4. Database/`, `BrookingsData/...`,
`2. Code/`); those source folders now live under `_ARCHIVE/` (see README / project_context §2).
**Scope:** Locate, characterize, and rank all municipal/local pension plan data and code. Companion to `project_context.md` (state track) and `data_sources_map.md`.

---

## 1. Bottom Line

A substantial municipal pension data-collection effort ran **Feb–Sep 2022** (data collectors: Amy Fan "AF", Alex Gant "AG", and others), covering **~16 cities, FY2019, ~30 plan workbooks**, with full provenance documentation in an **Airtable base**. A **modeling bridge to the State Pension Model input format was started in May–Jun 2023** (template + 3 city migrations: hou, chi, phx) and then stalled. **No city plan has ever been run through the simulation model.** The city-specific model code that exists is an early-2022 generation, superseded by the current `cluster_062026` (now Python) model.

**Canonical data now lives in `Data/Plans/Cities/{city}_modeldata/`. Everything else is documentation, derived exports, an unfinished bridge, or stale duplicates (the latter now under `_ARCHIVE/`).**

---

## 2. The System (as designed, per `Github/pensions-basecode/guidebook.md`, Jul 2022)

- **Plan ID convention:** `{city}_data{yy}_{plantype}`, e.g. `bos_data19_gen`. Plan types: `gen`, `ff`, `pol`, `edu`, `uty`, combos like `ffpol`.
- **Data sources:** AVs/CAFRs from publicplansdata.org + PPD database + city websites.
- **Collected per plan (Excel workbook, 9 sheets):** Wage_Growth, Refund_Rate, Avg_Mort, Sep_Rate, Ret_Rate, Retirement, Age_Serv_Num, Age_Serv_Wage, Inactv_Serv_Num — plus per-tier sheets (`T{n}_Age_Serv_Num`, `T{n}_Inactv_Serv_Num`) and a separate `*_tiervars.xlsx` (benefit factor, COLA, retirement ages, vesting, salary averaging, contributions per tier — same fields as the state model's planchanges workbook).
- **Documentation:** the **Airtable base "Pensions documentation"** (tables: `1. plans`, `1a. checklist`, `2. tables`, `3. tiers`, `4. plan details`) records, per plan and per table, what was available, source document + page, and assumptions made; AV/CAFR PDFs are attached to plan records. Per-plan `_log.md` files in the data folders carry the same kind of notes (examples: sd gen, hou pol).
- **Intended end state:** reshape sheets → import into a SQL database (never reached production; see §5).

## 3. Where Everything Is (ranked)

### 3.1 CANONICAL — `Data/Plans/Cities/{city}_modeldata/`
The collected raw data: plan workbooks + tiervars + logs + source AV/CAFR PDFs. Newest file Sep 2022. Coverage (plan workbooks, FY2019):

| City | Plans collected | Tiervars |
|---|---|---|
| chi | edu, ff, gen, pol | 4 |
| hou | ff, gen, pol | 3 |
| lax | ffpol, gen, uty | 3 |
| phx | gen (+3 tier files) | 1 |
| phi | gen (+9 tier files) | 1 |
| dal | ffpol (+ tier/AF variants) | 2 |
| dc | ffpol | 1 |
| den, fw, nsh, nyc, sea | "primary" | partial |
| bos, mil, sd, sf | gen | partial |
| aus, clt, ind | (folders empty) | 0 |

Also in `Data/Common/municipal/`: `default_assumptions.xlsx` (city analogue of the state model's default assumptions) + `variablesdb_v2.csv`. (The Brookings state replication package, the empty `sql_dbimport/`, `testdata/`, and old `Archive/` folders are now under `_ARCHIVE/`.)

**Two folder layouts** (distinguished by file structure, not a verified timeline;
matters for migration effort):
- **One-workbook-per-fund:** a separate `{city}_data19_{type}.xlsx` per employee
  group (gen/ff/pol/edu/uty/ffpol) — because each group is usually its own fund
  with its own AV/ppd_id (e.g. chi = CTPF 11 / MEABF 145 / PABF 146 / FABF 206) —
  each with a `_tiervars.xlsx`, usually a `_log.md`, and the source AV/CAFR PDFs
  saved in-folder. Cities: chi(4), hou(3), lax(3), dal(2), phi, phx, sd, sf, mil
  (bos, dc are thin stubs in this same shape).
- **Single "primary"+"tier" workbook:** one `{city}_data*_primary.xlsx` + a
  `{city}_data*_tier.xlsx` + `planlevel_overview.xlsx`; NO per-fund split, NO
  `_tiervars`, usually NO `_log.md`, NO in-folder PDFs, and NO separate
  active-matrix sheet (Age_Serv_Num absent). Consistently thinner. Cities:
  den(fy18+fy19), fw, nsh(fy20), nyc(fy20), sea.
- **Empty/placeholder:** clt (nothing), aus + ind (only blank `dataYY_*` template stubs).

**Sheet-level fill status — VALUE-SIGNATURE analysis (2026-06-11).** Method:
hash each sheet's numeric content per plan, so a genuine extraction (unique
signature) is separable from a COPIED DEFAULT table (identical signature reused
across plans) — going beyond cell-counts, which only reveal layout. 25 plan
workbooks. Verdict by sheet (→ state-model input):

| Collection sheet → state input | Verdict |
|---|---|
| **Age_Serv_Num → `ageservice`** | Genuinely extracted: 21/25 unique, 4 absent (den18/den19/nyc/sea), bos(9 cells)/dc(17) thin |
| **Age_Serv_Wage → `wagerel`** | Genuinely extracted: 23/25 unique; only dc/mil thin |
| **Sep_Rate → `withdrawal`** | Genuinely extracted: 21/25 unique |
| **Wage_Growth → `wagegrowth`** | Genuinely extracted: 22/25 unique; bos/dal_ffpol/dc share a thin 24-cell placeholder |
| **Avg_Mort → `mortality`** | MIXED: 13 plan-specific; **10 plans share ONE identical copied default table** (bos, all chi, dc, all lax, mil); 2 share another |
| **Ret_Rate → `retirement`** | MIXED: 13 plan-specific; rest on shared default tables (7 share one, 3 another) |
| **Retirement → `retdist`** | Systematically EMPTY for 10 (bos, dal_ffpol, dc, all 3 hou, all 3 lax); 15 present |
| **Refund_Rate → `refund`** | Mostly absent: 16 empty, 5 default-copied, only 4 real (chi_ff/chi_pol/nsh/sea) |
| **Inactv_Serv_Num** | Not extracted: 10 absent, 11 share a 9-cell placeholder, 4 real |

Key reading: the bottom three rows (retdist, refund, inactives) are **exactly the
sheets the state model already defaults** (`availableData=FALSE` →
`default_assumptions.xlsx`; inactives scaled from PPD counts), so city extraction
is missing precisely what the engine is built to fill. The **core four**
(actives, wages, withdrawal, wage-growth) are genuinely present for ~20 plans.
Mortality and retirement-RATES are the honest grey zone (about half real, half
default-copied). **bos and dc are essentially uncollected** (thin stubs
everywhere) despite having folders — bos is the one plan fully documented in
Airtable, so documentation ≠ extraction.

Per-tier membership sheets (`T{n}_...`): none anywhere; separate tier WORKBOOKS
exist only for dal(2), phx(3), phi(9). Not blocking — the model partitions the
aggregate age-service matrix by tier start dates from tiervars/planchanges.

**Effort assessment:** the core distribution data is genuinely extracted for the
~13 per-type cities; the gaps are model-defaulted sheets; bos/dc are stubs;
aus/clt/ind are empty. The remaining cost is finishing format-migration +
tier-params (see §6 / `data_sources_map.md`), not new extraction for most cities.

### 3.2 DOCUMENTATION — Airtable base "Pensions documentation"
URL seen: airtable.com/appIYfZmGwsaMmRAg. ~20 plan records (matches the workbook inventory). Holds the assumptions/provenance documentation and AV/CAFR attachments. **Not exported anywhere locally — single point of failure; should be exported to CSV and archived in the repo.** Join link in guidebook.md.

### 3.3 MASTER UNIVERSE TRACKER — `pproject-overview_AG(Working).xlsx` (parent root)
Plan-level overview of the broader municipal universe: dozens of cities × FY 2018/2019/2020 with PPD ids, liabilities, assets, inflation/discount assumptions. This is the selection/tracking sheet (the universe is much larger than the 16 collected cities). CSV copy in `ARCHIVE/`. Sheets: overview, Plan Overviews, Variable Sources.

### 3.4 THE BRIDGE (unfinished) — `BrookingsData/local pensions data migration/`
May–Jun 2023 effort to convert city workbooks into the **State Pension Model input format**: `modeldata_template.xlsx` has exactly the state model's sheets (`ageservice`, `wagerel`, `wagegrowth`, `mortality`, `withdrawal`, `retdist`, `retirement`). Completed: `hou19_migration.xlsx` (+ `-ds` variant), `chi19_migration.xlsx`, `phx19_migration.xlsx`. Companion: **`planchanges_hougen-ag.xlsx`** (parent root) = Houston-general tier parameters in state-model planchanges format. This was the last municipal activity; nothing after Jun 2023.

### 3.5 DERIVED EXPORTS — `4. Database/`
Reshaped CSVs for DB import (`{city}_asy19.csv`, `{city}_asytiers19.csv`, `{city}_refundrate19.csv`) for chi, dal, hou, lax, mil, phi, phx; den sits in `NON-IMPORTED/`. `variablesdb_v2.csv` = variable dictionary. The SQL import itself never happened (`sql_dbimport/` empty). Derived from §3.1 — regenerate rather than trust if in doubt.

### 3.6 CODE (all superseded generations)
- `2. Code/Basecode/` — `M_Code/` (Jan-Feb 2022, `MainPensionTiers_0122-DS.R`) and `S_Code/` (Feb 2022: `s_basecode.R`, `pm_functions.R`, `pm_liability_tiers.R`, `bucketfill.R`) — early generation of the same model family as the state track's `Common_Code`.
- `2. Code/CityCode/` — same shared R files + 12 per-city folders, of which only bos/dal/sea contain (unadapted) copies; per-city adaptation never completed. `readme_code.xlsx` is empty.
- `Github/pensions-basecode/` — git repo, active Mar–May 2022: basedata reshaping, database tests, an AAL calc ("Dan"), `guidebook.md` (the system manual), `meta_documentation.md` (outdated, superseded by guidebook).
- **No city simulation outputs exist anywhere** (no result RData/pkl for any city plan).

### 3.7 STALE DUPLICATES / ARCHIVES (do not use)
- `Individual Folders/Archival/Alex Gant/Data/Pension Data/CityData/` — predecessor copy of the modeldata folders, newest Feb 2022, strictly older than §3.1 (e.g. chi: 5 files vs 23).
- `ARCHIVE/CityData122ARCHIVE/` — Dec 2022 snapshot of early city model-code folders (Boston/Chicago/Dallas/Denver/Detroit/Nashville/NY/Seattle) + `Texas/`, `Templates/`.
- `ARCHIVE/CodeFile(ARCHIVE-NSH)/`, `1. Pension Data/Archive/`, `4. Database/Archive|BACKUPS/`.
- `BrookingsData/public pensions data(.zip)` — PPD raw dump; same 314 MB zip also sits in `State Pension Model/Brookings_Data/`.
- `PDFs/Municipal|State/` — nearly empty (2 files); the real source PDFs live inside each `{city}_modeldata/` folder.
- Parent loose files `planchanges_main-ag.xlsx` / `planchanges_hougen-ag.xlsx`: the `main-ag` one is an AG variant of the state planchanges; treat the state model's `planchanges_main_2022_clean.xlsx` as canonical for states.

## 4. Timeline

| Period | Activity |
|---|---|
| ~Jan–Feb 2022 | First-generation city model code (M_Code, per-city ModelCode folders now in ARCHIVE; AG CityData copies) |
| Mar–May 2022 | Github repo: reshaping + database pipeline + AAL calc experiments |
| Feb–Sep 2022 | Main data collection: ~16 cities FY2019, workbooks + Airtable documentation; guidebook written Jul 2022 |
| Jul 2022 | DB-import CSVs produced for 7 cities (den never imported) |
| May–Jun 2023 | Migration to State-Pension-Model input format: template + hou/chi/phx; Houston planchanges workbook. **Last activity.** |
| 2023–present | Dormant |

## 5. Gaps And Risks

1. **No city has ever been simulated.** The model-ready bridge exists for only 3 of ~16 collected cities, and even those migrations are unvalidated against the current (Python) pipeline.
2. **Airtable is the only home of the assumptions/provenance documentation** and is not exported locally.
3. Tier parameters: `_tiervars.xlsx` exist per plan, but only Houston has a state-model-format planchanges workbook.
4. Collection standardized on FY2019; the overview tracker contemplates FY18/20 too but they were not collected.
5. den CSVs never imported; aus/clt/ind folders empty; the SQL database leg of the original design was abandoned.
6. Heavy duplication across AG archival folder, ARCHIVE, and the live folders — easy to grab a stale copy by accident.

**To actually work the extraction:** `Documentation/city_extraction_catalogue.md`
(regenerable via `build_city_extraction_catalogue.py`) gives, per plan, the
per-sheet status + specific source AV/CAFR PDFs + the verbatim collector logs
(method + assumptions) + Airtable docs — the working document for reviewing the
done plans and extracting the remaining gaps by hand.

## 6. Recommended Path To "Cities In The Model"

1. **Freeze and label**: treat `Data/Plans/Cities/` as canonical raw; never work from `_ARCHIVE/` copies.
2. **Export the Airtable** (all 5 tables, from the "All" views) to CSV into this repo for preservation.
3. **Complete migrations** for the remaining per-type cities using `_migration/modeldata_template.xlsx`, and build a `planchanges_cities` workbook from the `_tiervars.xlsx` files (Houston is the worked example).
4. Cities then run through the **same 062026 Python pipeline** — fast runner, common-shock asset simulation, scenario layer, and analysis notebook all apply unchanged.

### 6.1 Engine-integration steps (what makes a city run identically to a state)

Verified against `Code/python/fast/Main_PensionModel.py` (2026-06-11). **The engine
math is already plan-type-agnostic; everything state-specific is shallow data
plumbing.** The barriers and the work:

1. **Format conversion (the only real per-plan work).** City workbooks use
   different sheet names/cell layouts than the state template
   (`Age_Serv_Num` vs `ageservice`, etc.); the `_migration/` bridge reshapes them
   into `modeldata_template.xlsx`'s state sheets (`ageservice, wagerel,
   wagegrowth, mortality, withdrawal, retdist, retirement`). **Done: hou, chi,
   phx only.** Per-type cities have the content to migrate; the primary-generation
   cities (den/fw/nsh/nyc/sea) need more reshaping (no separate active-matrix
   sheet, no tiervars).
2. **`planchanges_cities` workbook** in the STATE schema — sheet `in`, key
   `planid = {plan}_{plan_year}`, columns
   `startdate{i}/benefitfactor{i}/vesting{i}/maxsal{i}/yrsal{i}/nr{i}/er{i}/cola{i}`
   for i=1..6 — built from `_tiervars.xlsx`. Only Houston exists, and even it is
   in the wrong schema (`planchanges_hougen-ag.xlsx` uses sheet `planchanges_main`,
   key `HOU_Muni19`) → needs reshaping.
3. **Plan→ppd_id registry.** The runner derives `ppid = int(digits(plan_name))`,
   which breaks for cities (multiple plans per city). Needs an explicit
   `{plan_code: (ppd_id, fy)}` map. ppd_ids are recoverable from source-PDF
   filenames / `planlevel_overview.xlsx` (e.g. chi 11/145/146/206, lax
   139/140/141, hou 204/208, phx 94, sf 98, phi 152, sd 144, mil 151, dal 201,
   bos 148, aus 12). Layer-1 PPD coverage is confirmed (all municipal ppd_ids in
   `ppd-data-latest`, fy 2001–2023).
4. **Demographic ratios** `pctmale/pctmrg/reduct` — read from
   `PPD_planlevel_main_updated.csv`, which contains the 40 STATE plans only. Add
   city rows (from the AV) or default them.
5. **Per-plan `availableData` flags** — set directly from the §3.1 signature
   verdict (which sheets are real vs default per plan).
6. **Generalize 4 hard-coded spots** in `fast/Main_PensionModel.py`:
   `AVAILABLE_DATA` dict, `plan_folder = Data/Plans/States/{plan}` +
   `file_name = {plan}_2017.xlsx`, the demographic-CSV lookup, and the tier-file
   key — to accept a city via the registry. ~a day of code.

Once 1–6 exist a city is "just another plan" at `plan_year=2019`: identical fast
detal → common-shock asset sim → scenario layer → analysis notebook. **Cost is
concentrated in 1–2 (the §2 heterogeneity problem); the code (3–6) is trivial.**

---

*Sources inspected: parent folder tree; `guidebook.md` and `meta_documentation.md` + git log of `Github/pensions-basecode`; per-city modeldata listings; `2. Code` tree; `4. Database` tree; migration workbook sheet structures; `pproject-overview_AG(Working).xlsx`; Alex Gant archival CityData; CityData122ARCHIVE; Airtable screenshot provided by user.*
