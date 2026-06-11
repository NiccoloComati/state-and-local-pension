# Municipal (City) Pension Data Audit

**Created:** 2026-06-10
**Scope:** Locate, characterize, and rank all municipal/local pension plan data and code under the parent folder `State and Local Pension/` and related locations. Companion to `project_context.md` (state track).

---

## 1. Bottom Line

A substantial municipal pension data-collection effort ran **Feb–Sep 2022** (data collectors: Amy Fan "AF", Alex Gant "AG", and others), covering **~16 cities, FY2019, ~30 plan workbooks**, with full provenance documentation in an **Airtable base**. A **modeling bridge to the State Pension Model input format was started in May–Jun 2023** (template + 3 city migrations: hou, chi, phx) and then stalled. **No city plan has ever been run through the simulation model.** The city-specific model code that exists is an early-2022 generation, superseded by the current `cluster_062026` (now Python) model.

**Canonical data lives in `State and Local Pension/1. Pension Data/{city}_modeldata/`. Everything else is documentation, derived exports, an unfinished bridge, or stale duplicates.**

---

## 2. The System (as designed, per `Github/pensions-basecode/guidebook.md`, Jul 2022)

- **Plan ID convention:** `{city}_data{yy}_{plantype}`, e.g. `bos_data19_gen`. Plan types: `gen`, `ff`, `pol`, `edu`, `uty`, combos like `ffpol`.
- **Data sources:** AVs/CAFRs from publicplansdata.org + PPD database + city websites.
- **Collected per plan (Excel workbook, 9 sheets):** Wage_Growth, Refund_Rate, Avg_Mort, Sep_Rate, Ret_Rate, Retirement, Age_Serv_Num, Age_Serv_Wage, Inactv_Serv_Num — plus per-tier sheets (`T{n}_Age_Serv_Num`, `T{n}_Inactv_Serv_Num`) and a separate `*_tiervars.xlsx` (benefit factor, COLA, retirement ages, vesting, salary averaging, contributions per tier — same fields as the state model's planchanges workbook).
- **Documentation:** the **Airtable base "Pensions documentation"** (tables: `1. plans`, `1a. checklist`, `2. tables`, `3. tiers`, `4. plan details`) records, per plan and per table, what was available, source document + page, and assumptions made; AV/CAFR PDFs are attached to plan records. Per-plan `_log.md` files in the data folders carry the same kind of notes (examples: sd gen, hou pol).
- **Intended end state:** reshape sheets → import into a SQL database (never reached production; see §5).

## 3. Where Everything Is (ranked)

### 3.1 CANONICAL — `1. Pension Data/{city}_modeldata/`
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

Also in `1. Pension Data/`: `default_assumptions.xlsx` (city analogue of the state model's default assumptions), `public pensions data/` (the Brookings state replication package), `sql_dbimport/` (empty), `testdata/`, `Archive/`.

**Sheet-level fill status (verified empirically 2026-06-11** by counting numeric
cells per expected sheet in every plan workbook**):**

- **Genuinely extracted core** (Wage_Growth, Avg_Mort, Sep_Rate, Ret_Rate,
  Age_Serv_Num, Age_Serv_Wage): filled with plan-specific data in ~20
  workbooks across ~14 cities — chi (edu/ff/gen/pol), hou (ff/gen/pol),
  lax (ffpol/gen/uty), dal (ffpol), phx (gen), phi (gen), sf, sd, mil,
  den (fy18+fy19), fw, nsh (fy20), nyc (fy20), sea. Verified not template
  defaults (values differ across cities; uniform cell counts reflect uniform
  sheet layouts only).
- **Placeholder-thin, NOT usable as-is:** bos (age-service matrices ~9 numeric
  cells) and dc (~17) — despite bos being the one plan fully documented in
  Airtable's "2. tables".
- **Systematic gaps across plans (model fallbacks exist but matter):**
  - `Retirement` (retiree age distribution → model `retdist`): EMPTY for all
    hou and lax plans, dal, dc, bos; small (~22-cell) age-bucket vectors
    elsewhere. The model's default-assumptions fallback covers this
    (`availableData` flag) but retiree distributions drive `Main_Ret`, so the
    default is quality-relevant.
  - `Refund_Rate`: empty in most workbooks (chi_pol, den, nyc, sea have
    content) — normal; same fallback the state model uses.
  - `Inactv_Serv_Num`: mostly absent/~9 cells — normal; the model scales
    inactives from PPD counts.
  - Embedded per-tier membership sheets (`T{n}_...`): none anywhere; separate
    tier WORKBOOKS exist only for dal (2), phx (3), phi (9). **Not blocking:**
    the model's tier mechanism partitions the aggregate age-service matrix by
    tier start dates (from tiervars/planchanges); per-tier membership tables
    are not required inputs.
- Filename quirks: `fw_dataYY_primary.xlsx` (placeholder year), nsh/nyc are
  fy2020 not fy2019, den has both fy18 and fy19.

**Corrected effort assessment:** extraction is 70–90% complete for ~12-14
cities (gaps concentrated in retiree distributions), essentially not started
for bos/dc, and the 9 collected-but-empty sheets per plan are the same ones
the state model already defaults (refunds, inactives, disability).

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

## 6. Recommended Path To "Cities In The Model"

1. **Freeze and label**: treat `1. Pension Data` as canonical raw; never work from AG/ARCHIVE copies.
2. **Export the Airtable** (all 5 tables) to CSV into this repo for preservation.
3. **Validate the bridge**: try loading `hou19_migration.xlsx` + `planchanges_hougen-ag.xlsx` through the current Python pipeline (a city is just another plan folder + planchanges row once in the right format; `plan_year` would be 2019).
4. If (3) works: **complete migrations** for the remaining collected cities using `modeldata_template.xlsx`, and build a `planchanges_cities` workbook from the `_tiervars.xlsx` files (Houston is the worked example).
5. Cities then run through the **same 062026 Python pipeline** — fast runner, common-shock asset simulation, scenario layer, and analysis notebook all apply unchanged.

---

*Sources inspected: parent folder tree; `guidebook.md` and `meta_documentation.md` + git log of `Github/pensions-basecode`; per-city modeldata listings; `2. Code` tree; `4. Database` tree; migration workbook sheet structures; `pproject-overview_AG(Working).xlsx`; Alex Gant archival CityData; CityData122ARCHIVE; Airtable screenshot provided by user.*
