# Data Sources Map: State And Municipal Pension Plans

**Created:** 2026-06-11
**Purpose:** Where the model's input data actually comes from, for both the implemented state track and the planned municipal track: which source documents, how heterogeneous, who did the extraction, what this implies for adding plans, updating over time, and documentation standards. Companion to `city_data_audit.md`.

---

## 1. The Three-Layer Supply Chain (same for states and cities)

| Layer | What it provides | Form | Heterogeneity | Update cadence |
|---|---|---|---|---|
| **1. PPD database** (Boston College CRR, `ppd-data-latest.xlsx`) | Plan-level annual variables: assets, GASB liabilities, discount/inflation assumptions, payroll, membership counts, contributions, asset allocation | One standardized machine-readable panel, ~200 largest US plans, fy 2001–2023 | **None** — uniform columns across all plans | Annual, free |
| **2. Per-plan AVs + CAFRs/ACFRs** | Distribution tables: age×service actives matrix, retiree age distribution, mortality/separation/retirement rate tables, refund counts, inactive members; tier provisions | PDFs, one or more per plan-year (PPD hosts a download repository for both states and cities) | **Very high** — see §3 | Annual PDFs, but extraction is manual |
| **3. Plan/city websites** | Gap-filler for what AV/CAFR lack | Ad hoc | Total | Ad hoc |

The model consumes layer 1 directly (`planinfo` via `ppd_id`) and layer 2 only after a **manual extraction step** into the standardized 7–9-sheet workbook (`[PLAN]_2017.xlsx` for states; `{city}_data19_{type}.xlsx` for cities). **All the pain, all the assumptions, and all the documentation needs live in that extraction step.**

**Key coverage fact (verified 2026-06-11):** all **87** municipal plan `ppd_id`s in the project's city universe tracker are present in `ppd-data-latest.xlsx` (fy 2001–2023). Layer 1 works for cities exactly as it does for states, including annual updates.

## 2. Who Did The Extraction

| Track | Extractor | When | Provenance documentation |
|---|---|---|---|
| **States, FY2017 (the 40 plans)** | **Brookings / Lenney et al.** — we inherited their replication package (`public pensions data/`: `[PLAN]_2017.xlsx` + source AV/CAFR PDFs + "corresponding CSV matrices"). Copies exist in `State Pension Model/Plans/[PLAN]/`, `BrookingsData/`, and `1. Pension Data/`. | ~2019–2021 | **Essentially none in our repo.** Brookings' assumptions are not documented beyond what is visible in the workbooks; `planchanges` carries their COLA fields (`our_cola`). |
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

**States vs cities:** same document types, same extraction problem, same heterogeneity axes. State plans tend to have richer AVs (bigger plans, more disclosure); several city plans needed more aggressive assumptions (see `_log.md` examples for sd, hou). There is no structural difference in kind — only in disclosure quality.

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
4. Airtable export caveat: **CSV export captures only the current view.** The "Default" views are filtered (form-input views); export from the **"All"** views. The 2026-06 export in `1. Pension Data/airtable_export_2026-06/` captured 20 plans but only Boston's table documentation — re-export needed, and note the table-level documentation is genuinely sparse for most plans (much of it lives in `_log.md` + in-workbook notes instead).

---

*Verified facts behind this document: Brookings replication package contents (3 locations); state plan folder contents (workbook + AV/CAFR PDFs per plan); migration template lineage note ("TEMPLATE FROM BROOKINGS DATASET, TX-2017"); guidebook.md data-source instructions; 87/87 PPD coverage of municipal ppd_ids at fy 2001–2023; Airtable export row counts; year_version_audit.md hybrid finding (2022 scripts read `[PLAN]_2017.xlsx`).*
