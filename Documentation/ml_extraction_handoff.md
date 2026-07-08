# ML Extraction Handoff — What To Send As Worked Examples

**Created:** 2026-07-07
**Purpose:** package for the external ML expert (U. Miami) who will help automate the AV-PDF → collection-workbook extraction for the city plans. Identifies the best "done" examples (where the PDF ↔ extracted-data correspondence is demonstrable), one fully verified page↔sheet map, the heterogeneity he must design for, and a sensible evaluation design.

---

## 1. The flagship worked example: Phoenix (`phx_data19_gen`, COPERS, ppd_id 94)

**Why this one:** 8/9 sheets DONE (only `Refund_Rate` empty — and that sheet is model-defaulted anyway), both source PDFs sit in the folder, the collector log states every judgment call, and the workbook's `AF_Scratch_Work` sheet shows the intermediate calculations. It is also one of the 3 cities (hou/chi/phx) with a completed migration workbook to the model format.

**Files** (all in `Data/Plans/Cities/phx_modeldata/`):
- `AZ_PHOENIXCITY-COPERS_AV_2019_94.pdf` — the source actuarial valuation (54 pp.)
- `AZ_PHOENIXCITY-COPERS_CAFR_2019_94.pdf` — the audited financial report (cross-check only)
- `phx_data19_gen.xlsx` — the extracted collection workbook (the target format)
- `phx_log.txt` — the collector's method log (assumptions per sheet)

**Verified page ↔ sheet map** (checked cell-by-cell 2026-07-07):

| AV page | Source table | Workbook sheet |
|---|---|---|
| p. 38 (Exhibit F.3) | Active Member Counts by Age and Service | `Age_Serv_Num` |
| p. 39 (Exhibit F.4) | Active Member Average Salary by Age and Service | `Age_Serv_Wage` |
| p. 40 (Exhibit F.5) | Summary of Inactive Vested Members (by age, count + monthly benefit) | `Inactv_Serv_Num` |
| p. 48 (§B.1) | Mortality assumption (sex-distinct CalPERS base tables + adjustment factors, MP-2015 generational projection) | `Avg_Mort` |
| p. 49 (§B.4, continues p. 50) | Termination rates | `Sep_Rate` |
| p. 50 (§B.5) | Probability of Retirement, age × service buckets (<15 / 15–24 / 25–31 / >31) | `Ret_Rate` |
| pp. 41–43 (Exhibits F.6 area) | Retiree/beneficiary distribution | `Retirement` (retdist) |

**The difficulty ladder (all verified to the decimal, 2026-07-07, all within this ONE document pair)** — demonstrates that extraction is *table transcription + documented judgment*, not OCR. Present these in order:

**Rung 1 — straightforward (transcription + bin-boundary changes):**
- p. 38 F.3 → `Age_Serv_Num`: mostly cell-for-cell transcription (414, 26, 2 / 429, 90, 117, 6 / …); the PDF's "Under 20" + "20–24" rows merged into one `<25` row (4+150=154); the single "Over 30" column split evenly across two model columns (5 → 2.5/2.5).
- p. 39 F.4 → `Age_Serv_Wage`: same reshape, one weighted average from the row merge: (4×41,626 + 150×44,659)/154 = 44,580.22 — exactly the workbook value. `*`-suppressed cells (<4 members) carried through.

**Rung 2 — intermediate (re-gridding, structural rules, no strong assumptions):**
- p. 49 §B.4 → `Sep_Rate`: PDF gives termination rates for ages 20–60 × service {0,1,2,3,4,5+}. Workbook drops the service-0 column, extends the "5+" rate flat across all higher service columns, and zeroes every impossible cell (service > age−20, per "no one starts before 20").
- p. 50 §B.5 → `Ret_Rate`: transposed (PDF: age rows × service columns; workbook: service rows × age columns) AND re-gridded across non-aligned buckets with proportional weights — the workbook's "12–19" service row spans the PDF's "<15" (years 12–14, rate 0) and "15–24" (years 15–19, rate 22.5%): 3/8×0 + 5/8×0.225 = **0.140625**, exactly the workbook value.

**Rung 3 — dramatic (the extracted data exists nowhere in the PDF):**
- p. 48 §B.1 → `Avg_Mort`: the PDF has NO unisex mortality column. It names published tables (CalPERS employee/annuitant + MP-2015 generational projection, with sex-specific adjustment factors) and prints sex-split SAMPLE rates for three separate populations (pre-retirement / post-retirement / post-disability). The extracted single column was **constructed**: male/female simple average; ages 20–49 from the pre-retirement table only; 70+ from the post-retirement table only; **50–69 a headcount-weighted blend of the two, where the weights are the actives and retirees counts the collector had already extracted** (e.g. age 50: (1312×0.001105 + 168×0.004225)/(1312+168) = 0.00145916… — reproduces the workbook value exactly; 1312 = actives 50-54 from F.3, 168 = retirees 50-54 from the retiree table); held constant within 5-year bands.
- pp. 41–43 retiree distribution → `Retirement`: average benefit manually computed as total annuity dollars ÷ count (8,337,520/168 = 49,628.10 ✓); the "90 & Up" bucket (116 members) split evenly across 90-94/95-99/100+ (38.6667 each ✓).

All judgment calls are stated in `phx_log.txt`, and the workbook's `AF_Scratch_Work` sheet shows the intermediate calculations (the sample-rate tables, the age totals, the retiree table) — the human's visible "working".

## 2. Second example (different actuary/format): Chicago Police (`chi_data19_pol`, PABF, ppd_id 146)

8/9 DONE **including** `Refund_Rate` and `Retirement` (the two sheets phx lacks), AV PDF in folder (`IL_CHICAGOCITY-PABF_AV_2019_146.pdf`), rich log (`chi_data19_pol_log.md`), `AF_Scratch_Work` sheet. Shows tier-attribution judgment ("5–11 years of experience all Tier 2, everyone else Tier 1") and male/female combining. Page↔sheet map not yet built (same method as §1 applies). The chi folder holds 4 funds (edu/ff/gen/pol) — the same city under one actuary, useful for testing generalization across sibling documents.

## 3. Hard-case example: Houston Police (`hou_data19_pol`, HPOPS, ppd_id 208)

Demonstrates the pain points the automation must survive: DROP participants in/out of the active matrix, mortality split by sex AND status with unclear counts, retiree distribution given by age and by pension amount but **not jointly** (the reason `Retirement` is EMPTY). AV + CAFR in folder, rich log.

## 4. What else to include in the package

| Item | Path | Why |
|---|---|---|
| Extraction catalogue | `Documentation/city_extraction_catalogue.md` | THE map: per-plan status, sources, verbatim logs — tells him exactly what is done and what the gaps are |
| Collection guide | `Documentation/guidebook_city_collection.md` | already sent — the original collectors' instructions incl. per-sheet keyword catalog (what each table is titled in an AV) |
| Target schema semantics | `Documentation/model_input_dictionary.md` | what each sheet feeds in the model, which sheets matter (6), which are ghost/defaulted |
| A blank/reference workbook | `phx_data19_gen.xlsx` doubles as the schema; templates in `Data/Sources/collection_templates/` (`default_assumptions.xlsx`, `_tiervars.xlsx`, `tiersasy_template.csv`) | target format |
| Fill-status data | `Documentation/provenance/city_sheet_fill_audit.csv` | machine-readable per-plan × sheet status for scoping |

## 5. Heterogeneity he must design for (from `data_sources_map.md`)

Heterogeneity is at the **actuarial-firm/document level**, not the city level: bucket granularities differ and must be combined/split; DROP plans (Houston, Dallas) contaminate active counts; mortality may be sex-split, status-split, pre-retirement-only, or given as life expectancy instead of rates (chi); retiree distributions may be by age OR by benefit amount but not joint (hou); one fund reported retiree counts as a **bar chart** (chi_edu); tier definitions are prose. The judgment calls are exactly what the logs record — any automated pipeline needs a human-review layer on those calls, which is also the project's reproducibility stance (the wiring is reproducible; hand extraction is not).

## 6. Suggested evaluation design

1. **Train/calibrate** on phx (§1) + chi_pol (§2): input PDF → target workbook, with the logs as the "reasoning trace".
2. **Hold out** a done plan he never sees the workbook for — good candidates: `sd_data19_gen` (SDCERS, PDFs + rich log) or `phi_data19_gen` (PMRS) — and score his pipeline's output against the human extraction.
3. **Production targets** (the actual gaps, per the catalogue): the `Retirement`/retdist column (EMPTY for bos, dal_ffpol, dc, all hou, all lax); the stub plans bos/dc; the empty cities aus/clt/ind; and the `copy?` mortality sheets.

## 7. Known blockers to flag to him

- **Missing source PDFs:** hou_ff (HFRRF, ppd_id 30) and all primary-layout cities (dc, den, fw, nsh, nyc, sea) have no in-folder PDFs — fetch from publicplansdata.org before those plans can be attempted.
- **Airtable docs:** only Boston's table documentation is exported locally; the full "All"-views re-export is still pending.
- **hou/chi/phx overstate their gaps** in the collection workbooks: the 2023 migration workbooks (`Data/Plans/Cities/_migration/`) already contain gap-fills (e.g. Houston retdist sourced by AG) — check `_migration/` before re-extracting those three.
