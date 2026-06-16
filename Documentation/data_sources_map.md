# Data Sources Map: State And Municipal Pension Plans

**Created:** 2026-06-11
**Purpose:** Where the model's input data actually comes from, for both the implemented state track and the planned municipal track: which source documents, how heterogeneous, who did the extraction, what this implies for adding plans, updating over time, and documentation standards. Companion to `city_data_audit.md`.

**Reproducible evidence (2026-06-11):** the empirical scans behind this doc and
`city_data_audit.md` §3.1 are saved as data, regenerable via
`Documentation/city_data_scan.py` and `Documentation/provenance_scan.py`:
- `Documentation/city_sheet_fill_audit.csv` — per plan-workbook × canonical sheet:
  numeric cell count, value-signature, and status (`plan_specific` /
  `shared_default` = copied default table / `empty` / `absent`). 25 plans × 9 sheets.
- `Documentation/city_source_inventory.csv` — per plan: city, folder layout,
  city-level ppd_ids, and AV/CAFR/tiervars/log presence.
- `Documentation/model_input_dictionary.md` — the SCHEMA side of provenance: every
  input element the engine consumes, its source channel, fallback chain, constants.
- `Documentation/provenance_register.csv` — the INSTANCE side: 804 rows, one per
  plan × input element across BOTH tracks (40 states + 25 city workbooks), with
  source channel, vintage, specificity, extractor, evidence, confidence.
- `Documentation/state_sheet_fill_audit.csv` — the value-signature audit run on the
  40 STATE workbooks (same method as cities).
- `Documentation/state_notes_harvest.md` — verbatim dump of every state workbook's
  `notes` sheet (the only in-repo Brookings provenance: 5 with exact source URLs,
  2 rich, 32 thin, 1 none).

**The `corresponding CSV matrices` story (provenance of the granular layer).** The
Brookings package contains a subfolder originally named `corresponding CSV
matrices` — the INTERMEDIATE extraction layer between source PDFs and the final
workbooks (more granular than the workbooks: `mortalityact`/`mortalityret`,
`withdrawalf`/`withdrawalm`, `retirementn`/`retiremento`, `retbenrel`, plus
package-level `Fimprove`/`Mimprove` mortality-improvement scales and `COLA
details.xlsx`). The two pre-reorg package unzips carried UNEQUAL copies, and the
tree now holds both: `Data/Sources/brookings_package/corresponding CSV matrices/`
(260 files, incomplete — missing ~24 per-plan folders) and the standalone
`Data/Sources/brookings_package_csv_matrices/` (**521 files, strict superset — the
authoritative copy**, incl. TX105 and VA115, plans outside our 40). The standalone's
flattened name is an undocumented rename (not in `reorg_plan.md`; origin
unrecorded). Decision 2026-06-11: keep both as-is; **use the standalone (fuller)
copy for provenance work.**

---

## 1. The Three-Layer Supply Chain (same for states and cities)

| Layer | What it provides | Form | Heterogeneity | Update cadence |
|---|---|---|---|---|
| **1. PPD database** (Boston College CRR, `ppd-data-latest.xlsx`) | Plan-level annual variables: assets, GASB liabilities, discount/inflation assumptions, payroll, membership counts, contributions, asset allocation | One standardized machine-readable panel, ~200 largest US plans, fy 2001–2023 | **None** — uniform columns across all plans | Annual, free |
| **2. Per-plan AVs + CAFRs/ACFRs** | Distribution tables: age×service actives matrix, retiree age distribution, mortality/separation/retirement rate tables, refund counts, inactive members; tier provisions | PDFs, one or more per plan-year (PPD hosts a download repository for both states and cities) | **Very high** — see §3 | Annual PDFs, but extraction is manual |
| **3. Plan/city websites** | Gap-filler for what AV/CAFR lack | Ad hoc | Total | Ad hoc |

The model consumes layer 1 directly (`planinfo` via `ppd_id`) and layer 2 only after a **manual extraction step** into the standardized 7–9-sheet workbook (`[PLAN]_2017.xlsx` for states; `{city}_data19_{type}.xlsx` for cities). **All the pain, all the assumptions, and all the documentation needs live in that extraction step.**

**Key coverage fact (verified 2026-06-11):** all **87** municipal plan `ppd_id`s in the project's city universe tracker are present in `ppd-data-latest.xlsx` (fy 2001–2023). Layer 1 works for cities exactly as it does for states, including annual updates.

### 1.1 What each source actually IS (not just what it provides)

**Layer 1 — the PPD database (`ppd-data-latest.xlsx`).** Maintained by the Center
for Retirement Research at Boston College. It is itself a **secondary digest**: CRR
staff read each plan's AV/CAFR and transcribe a fixed set of **summary scalars**
into one uniform table — one row per plan per fiscal year, ~200 plans, free. It
gives **plan totals and assumptions, never distributions**: actuarial assets, the
GASB discount/return assumption, inflation assumption, payroll, active/inactive/
retiree head-COUNTS, EE/ER contribution dollars, asset-allocation shares. In the
model this row is `planinfo` (looked up by `ppd_id` + `fy`); it sets initial
assets, contribution rates, discount rate, allocation, and the member counts used
to scale the distributions. It tells you a fund has 11,507 actives and a 7%
assumption — not how those actives spread across age and service. That gap is why
Layer 2 exists.

`ppd_id` is just PPD's primary key for a fund, and it is the link between "a city"
and "the funds you must model." A city's pensions are usually **several legally
separate systems**, each its own PPD entry and its own AV — which is why a city
has multiple plan workbooks. Example: Chicago = CTPF (teachers, id 11), MEABF
(municipal/general, 145), PABF (police, 146), FABF (fire, 206); the four
`chi_data19_{edu/gen/pol/ff}.xlsx` workbooks map one-to-one onto those funds.

**Layer 2a — the AV (Actuarial Valuation).** The annual report the plan's
consulting **actuary** (GRS, Cheiron, Segal, Milliman, Cavanaugh Macdonald,
Bolton…) writes for the board to value liabilities and set the contribution. To do
that it must publish (a) the **assumption rate tables** — mortality, retirement,
termination/withdrawal, salary-increase by age/service — and (b) the **member
census** — actives by age × service, their salaries, retirees by age/benefit,
inactive members. **This is the workhorse for the model:** essentially every model
sheet (`Avg_Mort, Sep_Rate, Ret_Rate, Wage_Growth, Age_Serv_Num, Age_Serv_Wage,
Retirement, Inactv_Serv_Num`) is lifted from the AV. The guidebook's per-sheet
keyword lists (e.g. "Distribution of Active Members and Payroll by Age and Years
of Service") are literally AV table titles.

**Layer 2b — the CAFR / ACFR (Comprehensive / Annual Comprehensive Financial
Report).** The government's **audited GASB financial statements**, in which the
pension is one reporting unit. It is an **accounting** document: market value of
assets, additions/deductions (contributions in, benefits/refunds out, investment
income), the Net Pension Liability and GASB 67/68 disclosures, asset allocation,
and a statistical section. **AV vs CAFR in one line: the CAFR is money (audited
balances and flows); the AV is actuarial (assumptions + member demographics +
liability mechanics).** They overlap on financial totals — which PPD has usually
already harvested — so for the model the CAFR is mainly a **cross-check and
backstop** (it sometimes carries the only retiree/membership table when the AV
omits it). Both are PDFs on publicplansdata.org's repository and plan websites;
many plans renamed CAFR→ACFR ~2021.

**Layer 3 — plan/city websites (gap-filler), concretely.** Used when the AV and
CAFR between them lack a needed item. Three specific things: (a) **Experience
Studies** — periodic (3–5 yr) actuarial reviews of assumptions, often with the
fullest mortality/retirement/termination tables; (b) **Summary Plan Descriptions /
member handbooks / municipal code or ordinances** — the **tier benefit rules**
(benefit multiplier, COLA formula, vesting, normal/early retirement ages,
final-average-salary window, contribution rates) that fill `_tiervars` and are
frequently NOT spelled out in the AV/CAFR; (c) standalone assumption documents. So
"gap-filler" specifically means the tier-provision and assumption detail the two
financial PDFs don't fully state.

## 2. Who Did The Extraction

| Track | Extractor | When | Provenance documentation |
|---|---|---|---|
| **States, FY2017 (the 40 plans)** | **Brookings / Lenney et al.** — we inherited their replication package (`Data/Sources/brookings_package/`: `[PLAN]_2017.xlsx` + source AV/CAFR PDFs + sibling `brookings_package_csv_matrices/`). The live model copies are at `Data/Plans/States/[PLAN]/`; pre-reorg duplicates (`BrookingsData/`, `1. Pension Data/`) are now under `_ARCHIVE/`. | ~2019–2021 | **Essentially none in our repo.** Brookings' assumptions are not documented beyond what is visible in the workbooks; `planchanges` carries their COLA fields (`our_cola`). |
| **Cities, FY2019 (~16 cities)** | **In-house (Amy Fan, Alex Gant)**, explicitly replicating Brookings' method/template | Feb–Sep 2022 | Per-plan `_log.md` files + Airtable base (availability, source doc, page, keywords, assumptions per table) + in-workbook screenshots/scratch sheets ("AF_Scratch_Work"). |
| **State FY2022 update (current canonical run)** | **Nobody re-extracted.** The 2022 scripts still read the 2017 distribution workbooks; only plan-level drivers were refreshed (updated PPD + `planchanges_main_2022_clean.xlsx` + 2022-specific common data). | 2024 | See `year_version_audit.md` (the "hybrid" finding). |

That last row is the project's existing answer to "how do you update over time": **distributions are treated as slow-moving; annual updates refresh levels and assumptions from PPD (cheap, automatic); re-extraction from PDFs is reserved for when distributions genuinely change** (major reforms, big demographic shifts) — or never, accepting staleness as an assumption.

## 3. How Heterogeneous Is Layer 2 (the PDFs)?

Heterogeneity follows the **actuarial firm**, not the plan type — which is why the Airtable tracks the firm per plan (GRS, Cheiron, Segal, Bolton, Cavanaugh Macdonald, …). The guidebook's per-sheet keyword lists are an empirical catalog of the variation. Main axes:

1. **Table availability:** refund counts and inactive-member distributions are frequently absent (the model's `availableData` flags + `default_assumptions.xlsx` fallback exist for exactly this). Disability is almost never available (fixed default in the model).
2. **Bucket conventions:** age and service bucket widths differ per firm/plan and must be split/combined to the model's grid (the most common "minor assumption").
3. **Splits:** mortality by sex and/or pre/post-retirement; separation by service-only or age-only instead of joint; retirement rates sometimes by tier.
4. **Joint vs marginal:** retiree distributions often reported by age AND by benefit amount but not jointly.
5. **DROP:** included or excluded from active counts, plan by plan.
6. **Tier reporting:** tier membership tables sometimes present, often not; tier provisions described in prose.
7. **Document structure:** which of AV vs CAFR contains which table varies; page-level provenance matters.

**Concrete evidence — from the city `_log.md` files (Amy Fan, 2022), verified 2026-06-11.** The axes above are not hypothetical; the collector's own notes name them per plan:
- **Bucket-combining** (axis 2): "Combined age and service buckets" — chi_gen, lax_gen, sd_gen, chi_edu; sd "computed wage growth for 1-4 years by taking weighted average of general and safety."
- **DROP in/out** (axis 5): hou_pol "Age_Serv_Num includes DROP participants … Unclear if DROP membership is needed, but I included it."
- **Mortality splits** (axis 3): lax_gen "only given for pre-retirement"; hou_pol "broken out by male and female and by active/retired/disabled, unclear on the numbers"; sd "assumed 50/50 male/female, took average and spread across age buckets."
- **Retiree dist by age OR amount, not joint** (axis 4): hou_pol "distribution by age and by pension amount, but not joint"; lax_gen "reported by number and average benefit, but not broken out by age" → these are exactly the plans whose `Retirement`/`retdist` sheet is EMPTY in the fill audit.
- **Separation marginal not joint** (axis 3): chi_gen "No information on age, assume constant"; lax "assumed constant across age/service years, no one started before 20."
- **Tier ambiguity** (axis 6): lax "6 tiers in the plan, 8 tiers on the sheet"; sd "membership for General and Safety … I don't think these are tiers as we define them … no information for these tiers on the AV/CAFR."

**States vs cities:** same document types, same extraction problem, same heterogeneity axes. State plans tend to have richer AVs (bigger plans, more disclosure); several city plans needed more aggressive assumptions (see `_log.md` examples for sd, hou). There is no structural difference in kind — only in disclosure quality. **Standardization is therefore judgment-heavy, not a mechanical parse:** the firm/document variation above has to be resolved by a human decision per plan-table (which is why the value-signature audit finds mortality and retirement-rates half-real / half-default-copied — those are the tables collectors most often fell back on).

## 4. Implications

### (a) Implementing the collected cities
Extraction (the hard 90%) is already done for ~16 cities/FY2019. Remaining work is mechanical reshape into the model template (exemplars: hou/chi/phx migrations + `planchanges_hougen-ag.xlsx`) + per-city review against the `_log.md` assumptions + PPD `planinfo` wiring (coverage confirmed). See `city_data_audit.md` §6.

### (b) Adding NEW plans (state or city)
Cost = layer-2 extraction: locate AV/CAFR on PPD's repository → extract 7–9 tables + tier provisions → document. The 2022 team needed days per plan fully manually; with AI-assisted PDF extraction guided by the guidebook's keyword catalog, realistic estimate is hours per plan-year, with human review concentrated on the assumption decisions (bucket splits, sex weights, DROP). Layer 1 is free (PPD covers ~200 plans).

### (c) Updating existing plans over time
Two tiers of effort:
- **Cheap annual refresh** (the implemented 2022 precedent): new PPD vintage + planchanges review; distributions frozen. Hours for the whole panel.
- **Full re-extraction** of distributions: same cost as (b) per plan-year. Reserve for plans with major reforms or when distribution drift becomes a named limitation.

### (d) Documentation standard (recommended)
The Airtable "2. tables" schema is the right unit of provenance — per plan-table: *{complete? | source document | page # | keywords found | what was given | assumptions made}*. Recommendations:
1. Adopt that schema as a **per-plan provenance file stored in-repo next to the workbook** (CSV or markdown — the `_log.md` files are a prose version of this), so provenance is versioned and platform-independent. Airtable can stay as the collection UI; the repo copy is canonical.
2. **Backfill the 40 state plans** with a minimal provenance file: "extracted by Brookings; source PDFs in folder; assumptions undocumented" + anything recoverable from the workbooks — making the documentation gap explicit instead of silent.
3. Generate the provenance file as a mandatory artifact of any future extraction (new plans or updates).
4. Airtable export caveat: **CSV export captures only the current view.** The "Default" views are filtered (form-input views); export from the **"All"** views. The 2026-06 export in `Data/Sources/airtable_export/` captured 20 plans but only Boston's table documentation — re-export needed, and note the table-level documentation is genuinely sparse for most plans (much of it lives in `_log.md` + in-workbook notes instead).

---

*Verified facts behind this document: Brookings replication package contents (3 locations); state plan folder contents (workbook + AV/CAFR PDFs per plan); migration template lineage note ("TEMPLATE FROM BROOKINGS DATASET, TX-2017"); guidebook.md data-source instructions; 87/87 PPD coverage of municipal ppd_ids at fy 2001–2023; Airtable export row counts; year_version_audit.md hybrid finding (2022 scripts read `[PLAN]_2017.xlsx`).*
