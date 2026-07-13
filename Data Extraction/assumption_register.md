# Assumption Register — Extraction & Modeling Decisions

**Purpose:** the single record of every modeling decision/assumption embedded in extracted data (by the 2022 human collectors or by our pipeline), its implications, and the options for resolving it. One entry per issue, kept short. Add entries as found; move to DECIDED with the decision and date when Niccolo rules. Companion to `data_extraction_context.md` (the how); this file is the *what-needs-deciding*.

**Status legend:** OPEN = needs a decision · NOTED = known data defect awaiting correction decision · DECIDED = resolved (decision recorded inline).

---

## OPEN — decisions needed

### 1. Tier-specific retirement rates cannot be represented in the engine (chi_pol, likely others)
- **The document:** chi_pol AV p.72 publishes retirement rates by age × TIER (Tier 1 / Tier 2, different rates at ages 50-59). Other plans may do the same for retirement/withdrawal/mortality.
- **The engine:** one `RetirementRate` matrix per plan; the tier loop swaps benefit parameters and per-tier retirement AGE (`RetirementStart_t`), but there is no input slot for per-tier rate tables (`Code/python/fast/Main_PensionModel.py` ~l.361, `sim_params.py`).
- **What the existing workbook embeds:** the 2022 collector folded tiers into the service dimension — service 5-11 → Tier 2 rates, 12+ → Tier 1 (her log documents it; rationale: Tier 2 = hired ≥2011 → ≤~9 yrs service at valuation). Only exact near the valuation date: simulated Tier-2 members accumulate service and drift into buckets carrying Tier-1 rates.
- **What our live extraction embeds:** run 20260713_120202 mapped ALL service rows to Tier 1 (model's stated fallback) — a different, coarser assumption.
- **Options:** (A) keep engine, choose a folding convention (the collector's service-bucket mapping is one candidate); (B) extend the engine — swap `RetirementRate` per tier like `COLA`, extraction becomes per-tier grids (same question then applies to withdrawal/mortality); (C) defer — BOTH tier columns are archived source-native in the run artifacts, so any convention can be re-derived later at zero API cost.
- **Nothing blocks deferral.** The derived grid is the only thing that depends on the choice.

### 2. Rate-table ages beyond the printed range (chi_pol Ret_Rate; template asks 50-70)
- **The document:** chi_pol prints ages 50-65 only, ending at 1.00 (mandatory retirement).
- **Workbook embeds:** the collector carried 1.00 forward to ages 66-70.
- **Our extraction embeds:** left 66-70 empty (nothing printed).
- **Options:** carry the terminal 1.00 forward (collector's move) / leave empty (then define what the engine does with empty rate cells) / shrink the template's age range.

### 3. phx Ret_Rate template semantics — two workbook-vs-PDF deviations
- **(a) age-70 column:** the AV prints an age-70 row of 100% everywhere; the workbook ignores it and carries the 66-69 rates. **(b) '>31' service column:** labels are unambiguous (25-31 includes 31; >31 = 32+, per Niccolo 2026-07-13), yet the workbook copies '>31' into all bins 31+ (the literal reading would blend row 31-32 from two columns).
- **Implication:** the current phx workbook Ret_Rate embeds both deviations; the model's literal extraction scores 0.8624 against it with ALL residuals being exactly these cells.
- **Decision needed:** which readings are canon for the template (affects scoring, and whether the phx workbook sheet should be regenerated from the pipeline output).

### 4. Sep_Rate template semantics — conventions adopted from the collectors (pending confirmation)
- **Service year 0 is excluded from the template.** Both phx and chi_pol collectors mapped template col '1' to source service-year-1 rates, dropping the printed year-0 rates (phx 17%, chi 3.0%). Adopted in our col spans ([1,1],[2,2],[3,3],[4,4],[5,6],[7,8],[9,10],[11,11],[12,12],[13,30],[31,40]).
  **Check before finalizing:** whether the engine ever reads a year-0 separation rate; if it does, the template's exclusion silently loses the printed year-0 rates.
- **Impossible-cell zeroing:** cells with service unattainable at that age (entry-age floor 20, documented by the collectors) are zeroed by code. Adopted the phx collector's stricter reading — zero unless the WHOLE service bucket is attainable (`mode: upper`); the alternative (zero only if NO part is attainable) is one config switch. One phx cell (age 25 x col '6' = 0.055) contradicts her own convention — likely her slip; it scores as the single 'wrong' cell in the executor test.
- **Rows beyond the printed table:** phx's source ages end at 60; her workbook rows 65/70 carry the age-60 rates forward — same question as entry "ages beyond the printed range" above; our extraction leaves them empty (22-cell known residual).
- **Impossibility conventions are inconsistent ACROSS collectors (live runs 2026-07-13):** phx zeroed per the strict rule (minus one cell); chi left attainable cells empty at ages 30-40 yet FILLED an unattainable one (age 50, svc 31-40; max service at 50 is 30 under any entry floor); sd applied no visible rule. The "ground truth" disagrees with itself — the convention needs an explicit ruling; until then, scoring differences in these cells are convention noise.
- **phx live Sep_Rate run embeds the carry-forward:** the model declared rows 65/70 <- copy(age-60 rates) DESPITE the spec's no-extrapolation rule (visible in the ops audit; matches the collector's move). The derived grid therefore embeds the still-open "ages beyond the printed table" assumption (entry 2). Re-derivable either way from the archived transcription once ruled.
- **sd (run 2026-07-13, raw 0.25 as expected):** publishes separation per GROUP (General/Safety); the workbook blends them with AGE-VARYING headcount weights (blend differs per age row). Blending needs the cross-table weighted op (rung 3, not built) with an age x group headcount weights table — the same op shape Avg_Mort needs.

### 5. sd Ret_Rate was never extracted (blank sheet) — and the source needs an aggregation assumption
- The sd workbook Ret_Rate has 0 filled cells; the collector's log: rates are "reported by service years and by age separately, unclear best way to aggregate."
- When extracted (a production-style run — no answer key), an aggregation assumption must be chosen and recorded here.

### 6. Age_Serv_Wage with only age-level salary evidence is NOT accepted as a final grid
- **Ruling for now (Niccolo 2026-07-13):** do not accept copied age-only average salaries as an `Age_Serv_Wage` grid. Flag these outputs as unresolved assumptions / cases needing a contract fix before use.
- **aus run 20260713_164833:** Table 13A prints service-count columns plus one `Average Annual Salary` per age band. The model transcribed those 10 salary values correctly, and they count-weight back to the printed all-ages average ($69,715), but then copied each age average across all service buckets. That is an assumption that salary varies by age only, not an extraction of age x service wages.
- **mil run 20260713_164600:** the report prints age-only earnings/salary summaries and separate age x service count tables, but no joint salary-by-age-and-service table. The model first tried to return no source table; validation forced a placeholder count table. The derived grid is all nulls, which is the honest state until an assumption is chosen.
- **Pipeline gap:** the schema has no clean `unavailable` / `underdetermined` status, and the Age_Serv_Wage rule "copy coarser average bins" is too permissive when an entire dimension is missing.
- **Options:** (A) add an unavailable status and leave these grids empty; (B) explicitly adopt age-only-within-age copying as a modeling assumption; (C) add another data source or model to estimate service variation; (D) add a separate age-only wage target/input so the evidence is preserved without pretending it is joint.

---

## NOTED — known defects in the existing workbooks (correction decision pending)

### 7. phx Age_Serv_Wage typo: 86,306 vs PDF's 86,309
- Age-65+/Over-30 cell (propagated into both split target columns). Found by the pipeline 2026-07-09, verified against the PDF. Decision: correct the workbook (and regenerate anything downstream that consumed it) or leave.

### 8. sd Age_Serv_Num AND Age_Serv_Wage: '70 and up' row dropped
- The collector's row 70 equals the source's '65 to 69' row verbatim on both sheets; the '70 and up' members (17 actives) are absent. Our extraction sums both per template semantics ('70' = 65-and-over, as phx did). Decision: adopt the corrected grids or keep the workbook as-is.

---

## Template conventions already in force (recorded, not open)
- Grid open ends: row/col label '70' = "65/70 and over"; '<25' = under 25; counts: 0 ≡ empty cell (`zero_equals_empty` in scoring); printed dashes = empty.
- Averages never summed/split; merged-bin averages are count-weighted; average = total$/count when only totals are published.
