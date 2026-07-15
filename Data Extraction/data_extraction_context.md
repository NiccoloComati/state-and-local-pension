# Data Extraction Context

**Created:** 2026-07-08
**Purpose:** The living document for the AV-PDF -> model-workbook extraction pipeline: the methodology we currently believe in (update it when we change our mind) and the chronological development log. Companion documents: `assumption_register.md` (THE record of embedded modeling assumptions/decisions awaiting Niccolo's ruling - add to it whenever an extraction embeds a choice), `Documentation/ml_extraction_handoff.md` (the worked examples / difficulty ladder shared with Pietro Ramella), `Documentation/city_extraction_catalogue.md` (per-plan extraction status + human collector logs), `Documentation/model_input_dictionary.md` (what each extracted sheet feeds in the model).

---

## 1. Methodology (current thinking, 2026-07-08)

### The problem
The model needs ~6 granular tables per pension plan (active age x service counts and wages, separation/retirement/mortality rates, retiree distribution). They exist only inside PDF actuarial valuations, one per plan-year, each actuarial firm in its own format. Manual extraction costs hours per plan, so the detailed distributions are frozen at their original extraction while only summary scalars get refreshed.

### Architecture: two stages + a router
- **Stage A - extract-to-schema:** the model receives the WHOLE document and both locates the relevant table(s) and produces a structured grid matching a fixed target schema, reporting the source pages/titles it used. Locating across heterogeneous documents is part of what the ML solves - no keyword heuristics, no human-specified pages in the normal flow. (Feasible because the full text layer of these AVs is only ~18-47K tokens against a 1M context window; the model reporting `source_pages` also recovers page-level provenance for free.)
- **Stage B - reason/compute:** transform the extracted grid(s) into the model format by EMITTING auditable operations (not computing in-weights), fill the schema, flag what is missing.
- **Router** (refined from the original four-way EXTRACT/COMPUTE/HUMAN/GRAPH design): "not all info" is three distinct situations with different handling - (a) *truly absent* (model-defaults exist -> don't chase), (b) *present but non-joint* (no extraction fixes it -> modeling decision), (c) *underdetermined weights* (sometimes solvable from other tables -> try, else human).

### Design principles (with the evidence behind them)
1. **Schema-guided, not open-ended.** The target schema already exists (the 9-sheet collection workbook format + `model_input_dictionary.md`); extraction is "fill this grid", not "find all tables". Pietro's zero-shot Qwen test ("extract all tables") is the counterexample.
2. **The transformation vocabulary is small.** Everything the human collectors did across 25 workbooks reduces to ~8 operations: merge bins (sum / weighted average), split open bins evenly, transpose + proportional re-grid, M/F average, population-weighted blend, average = total$/count, carry rate flat, zero impossible cells. Stage B should compose programs from this fixed vocabulary -> auditability + cheap human review. (Verified cell-by-cell on Phoenix, 2026-07-07.)
3. **Cross-table dependencies are real.** The hardest verified case (mortality blend) uses headcounts from two OTHER extracted tables as weights -> Stage B operates on document-level state, and intermediate primitives (counts by age) are first-class schema targets.
4. **Text-first, vision-fallback.** The 2019 AVs are mostly born-digital; the rung-1/rung-2 Phoenix tables came out of the raw text layer. Some AVs have image-only content (4 of 17 had firm names only in letterhead images) -> vision is the fallback slot, not the default.
5. **Eval-first.** Ground truth exists (the human-extracted workbooks); every extractor variant is scored the same deterministic way, cell by cell. Success is measured, not eyeballed.
6. **Reproducibility-of-record.** Every LLM call's full request + raw response is archived next to the output (the machine analog of the collectors' AF_Scratch_Work sheet). Re-runnability via pinned weights is the (possible) Phase-2 upgrade; at our volume (~hundreds of documents/year) API cost is not a binding constraint - reproducibility is.
7. **Calibrate on cities, scale to states.** City ground truth has verified page-level provenance (phx) and written collector logs; the 40 state workbooks are Brookings extractions with UNDOCUMENTED provenance, so a state mismatch cannot be attributed (extractor error vs unknown Brookings judgment). States are the scale-out corpus - and the pipeline may eventually RECOVER their lost provenance.
8. **Format heterogeneity clusters by actuarial firm** (GRS, Segal, Cheiron cover 13 of our 17 in-folder AVs) -> per-firm few-shot examples are a cheap upgrade path.

### Difficulty ladder (the verified test cases)
| Rung | Example (all Phoenix AV 2019) | What it tests |
|---|---|---|
| 1 - transcription + bin boundaries | p.38 F.3 -> Age_Serv_Num; p.39 F.4 -> Age_Serv_Wage | pure extraction + merge/split |
| 2 - re-gridding, mechanical rules | p.49 B.4 -> Sep_Rate; p.50 B.5 -> Ret_Rate | transpose, proportional re-bucket, fill implied cells |
| 3 - data not in the PDF as extracted | p.48 B.1 -> Avg_Mort (headcount-weighted blend); pp.41-43 -> Retirement | cross-table computation + judgment |

### Evaluation design
- **Calibrate:** phx (cell-level verified), chi_pol (different firm, logged).
- **Hold out:** sd or phi (done plans, score blind).
- **Production targets:** the retdist column (10/25 empty), bos/dc stubs, aus (AV in-folder, workbook never filled), `copy?` mortality sheets.

---

## 2. Pipeline v0 (built 2026-07-08)

Minimal end-to-end loop: **locate -> extract -> score**. Deliberately rudimentary; the goal today is that the loop exists and produces a number, not high accuracy.

```
Data Extraction/
  data_extraction_context.md   <- this file
  sample_code_pietro.ipynb     <- Pietro's TATR/Qwen sample (Colab)
  pipeline/
    targets.json     target schema: canonical grid + transformation rules per
                     sheet (Age_Serv_Num, Age_Serv_Wage live; Ret_Rate stub);
                     keywords retained for the diagnostic scan only
    harness.py       ground-truth loader (workbook sheet -> canonical grid,
                     OneDrive-lock-safe) + deterministic cell-by-cell scorer
    locate.py        full-document text access (pypdf); the old keyword page
                     ranking survives only as a diagnostic (--keyword-scan)
    extract.py       Anthropic API call (claude-opus-4-8, structured outputs
                     via output_config.format -> guaranteed-parse JSON grid);
                     the model locates the table in the FULL document and
                     reports source_pages + source_table_title; archives full
                     request+response per call. NEEDS ANTHROPIC_API_KEY.
    run_test.py      orchestrator CLI; plans registry (phx, chi_pol, sd)
  runs/              per-run artifacts: candidate.json, record.json, report.json
```

**Canonical grid:** `{"row_labels": [...], "col_labels": [...], "cells": [[number|"*"|null]], "notes": "..."}` - the shared contract between truth loader, extractor, and scorer. `notes` is where the model must record its judgment calls (mirrors the human logs).

**Scoring:** positional alignment, per-cell exact / close(<1%) / wrong / missing / extra, `*`-suppression respected; accuracy = (exact + star_ok) / filled truth cells; label mismatches reported separately.

**Verified without API key (2026-07-08):**
- harness: phx Age_Serv_Num and Age_Serv_Wage load as clean 10x8 grids matching the schema labels; truth-vs-truth self-score = 1.0 (59 filled cells each).
- locate: phx p.38 ranks #1 for Age_Serv_Num (the verified correct page).
- extract: dry-run prompt contains the actual Exhibit F.3 text; `anthropic` SDK installed.

### How to run
```powershell
# one-time: set the key (or add to your user env vars)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

cd "Data Extraction"

# inspect the prompt without spending anything (whole document goes in)
python pipeline/run_test.py --plan phx --target Age_Serv_Num --dry-run

# the real thing: whole document in, model locates + extracts, scored vs the
# human workbook (expect ~$0.10-0.30/call at 18-47K input tokens)
python pipeline/run_test.py --plan phx --target Age_Serv_Num
python pipeline/run_test.py --plan phx --target Age_Serv_Wage

# the cross-firm test (the real question): different actuary, zero changes
python pipeline/run_test.py --plan chi_pol --target Age_Serv_Num
python pipeline/run_test.py --plan sd --target Age_Serv_Num

# diagnostics only (not part of the flow):
python pipeline/run_test.py --plan phx --target Age_Serv_Num --keyword-scan
python pipeline/run_test.py --plan phx --target Age_Serv_Num --pages 38 --dry-run
```
Expected on phx: near-perfect (rung 1; the table transfers almost verbatim) AND `source_pages` = [38]. Any failure there is plumbing, not ML difficulty. The chi_pol/sd numbers with zero prompt changes are the finding to report.

### Known limitations (v0, deliberate)
- Text layer only; no vision fallback yet (a near-empty text layer aborts with a clear message).
- Ret_Rate (rung 2) schema is stubbed but not tested.
- No Stage-B code-emission yet - the rung-1 transformations are done by the model inline, per the rules in targets.json. The composable-operations design comes when rung 2/3 are tackled.
- Scoring is positional; if a plan's workbook grid deviates from the template, labels flag it but cells still compare by position.

---

## 3. Development log

### 2026-07-08 - v0 built (locate/extract/score loop)
- Decided test corpus: cities with ground truth (NOT states - Brookings provenance undocumented, mismatches undiagnosable). Calibrate phx, generalize chi_pol/sd.
- Built `pipeline/` (targets.json, harness.py, locate.py, extract.py, run_test.py) as above.
- Verified everything up to the API call (harness self-score 1.0; locator finds phx p.38; dry-run prompt correct). API key left for Niccolo to set; no live extraction run yet.
- Model choice: `claude-opus-4-8` with structured outputs (`output_config.format` + JSON schema -> guaranteed parse). NOTE: `temperature` is REMOVED on current Anthropic models (400 error) - determinism comes from schema+prompt, do not add sampling params.

### 2026-07-07 - groundwork (see ml_extraction_handoff.md and working_context.md)
- Verified the Phoenix difficulty ladder cell-by-cell (the 3-rung examples sent to Pietro).
- Established the ~8-operation transformation vocabulary, the cross-table dependency finding, the three-way "missing" taxonomy, the firm-clustering fact (GRS/Segal/Cheiron = 13/17 AVs).

### 2026-07-08 (later) - v0 corrected: whole-document extraction, no keyword locator
User pushback (correct): the keyword page-locator + human-specified pages put a
brittle heuristic in the slot the architecture assigns to the model. Locating
the table across heterogeneous documents IS part of what the ML solves.
Rewired: the model now receives the FULL document text (~18-47K tokens for the
three test AVs, trivially within context) and must locate + extract in one
schema-guided call, reporting source_pages + source_table_title (which also
recovers page-level provenance for free). Keyword ranking demoted to a
--keyword-scan diagnostic; --pages kept as a debug lever only. Also fixed
Windows cp1252 print crash on Unicode PDF text (stdout reconfigured to utf-8).

### 2026-07-08 (v0.1) - two stages properly separated: transcribe + declare, execute deterministically
User pushback #2 (correct, and decisive on the reproducibility argument): even
rung-1 bin changes are conceptually Stage B, and the SOURCE-NATIVE tables are
worth keeping - they are the page-level provenance the human collectors never
recorded, and the audit trail for every derived number.

New contract (one API call, two strictly separated parts):
- Stage A output = `source_tables` (tables transcribed EXACTLY as printed:
  original bins, '*' suppression, nulls; page + printed title) + `row_map` /
  `col_map` (DECLARED bin-mapping operations: rows copy/sum/weighted_avg with
  a weights_table reference, cols copy/sum/share_even) + `notes`.
- Stage B = `ops.py` executes the declared maps deterministically. The model
  does ZERO arithmetic; every derived number is computed by our code.

Consequences: extraction errors vs mapping errors are separately diagnosable
(source table wrong vs ops wrong); arithmetic is exact by construction (no
more "close" cells from in-weights math); the ops list is a machine-readable
collector log; the wage table's cross-table weights (counts) are explicit in
the contract (weighted_avg must reference the transcribed counts table).

Executor verified against reality (test_ops_phx.py): hand-built Stage-A result
with the ACTUAL phx pp.38-39 tables (source-native bins) -> ops.execute ->
100% vs the human workbook on BOTH targets (counts 59/59 exact incl. the
2.5/2.5 splits; wages 57 exact + 2 star_ok, weighted avg 44580.22077922078
bit-exact). Run artifacts are now extraction.json (source + maps) +
derived.json (scored grid) + record.json + report.json.

### 2026-07-09 - first live run (via MIT Parley proxy) + format-robustness fix
Environment: user routes API calls through MIT's Parley service
(ANTHROPIC_BASE_URL=https://parley.api.mit.edu, key sk-parley-v1-...; on
PowerShell set with $env:, not bash `export`).

Finding: Parley silently DROPS output_config (structured outputs) - the model
returned a reasonable but non-conforming JSON dialect (row objects instead of
cells lists, {table,labels} objects in sources, notes as list). The pipeline
crashed in ops.execute.

Fix in extract.py: (1) exact output template embedded in the prompt
(FORMAT_SPEC); (2) client-side validate() checking the full contract; (3) one
automatic retry feeding the specific violations back; (4) fence-tolerant JSON
parsing; output_config still sent for endpoints that honor it. record.json now
stores all attempts incl. format_problems.

RESULT (salvaged from the non-conforming live response, converted + executed):
phx Age_Serv_Num = 59/59 EXACT (accuracy 1.0) vs the human workbook. The
model located p.38 unaided, transcribed Exhibit F.3 perfectly source-native,
and declared the correct ops (sum merge for <25, share_even for Over 30).
First live datapoint: rung-1 extraction works end to end.

### 2026-07-09 - API backend decision: stay on MIT Parley for now
Decision (Niccolo): keep routing through Parley (ANTHROPIC_BASE_URL=
https://parley.api.mit.edu) - MIT-paid, institutionally sanctioned, and it
works (first live run 59/59 through it; client-side validation covers the
dropped-output_config defect). Direct Anthropic key is a drop-in switch later
(only the two env vars change; zero code changes).

Triggers to revisit and go direct:
1. VISION FALLBACK - when we need to send page images (image-only AVs,
   chart-only data like chi_edu's retiree bar chart), test whether Parley
   passes image content blocks; if it drops them like output_config, that
   forces the switch (or at least a direct key for that stage).
2. PAPER-GRADE PRODUCTION RUNS - when extractions become research artifacts,
   the no-middlebox reproducibility argument favors direct API.
Cheap meanwhile: ask the Parley team whether they support structured outputs
(output_config) and image inputs - may be a version lag they would fix.
Behind Parley, assume any newer API parameter can be SILENTLY dropped -
verify features rather than assume (no error is raised, they just don't
happen). Expect the format-retry to fire occasionally; that is the guard
working.

### 2026-07-09 - live results: phx both targets; GROUND TRUTH ERROR FOUND
Live runs through Parley (post format-guard):
- phx Age_Serv_Num: 59/59 EXACT (1.0), no format retry needed. Correct ops
  declared (sum merge <25, share_even Over 30).
- phx Age_Serv_Wage: 55 exact + 2 star_ok + 2 "close" = 0.9661. Model
  correctly transcribed BOTH tables (F.4 wages p.39 + F.3 counts p.38 as
  weights) and declared weighted_avg with weights_table=1; the <25 weighted
  merge came out EXACT (44,580.22, computed by ops.py).
- The 2 "close" cells are a HUMAN ERROR IN THE GROUND TRUTH: workbook has
  86,306 for age-70/Over-30; the PDF prints 86,309 (verified directly).
  Collector typo from 2022, propagated into both split target columns. The
  model+pipeline output is more accurate than the human workbook on this cell.
Consequences for evaluation: accuracy < 1.0 must be adjudicated against the
PDF before being read as model error - label noise exists in the human
workbooks, and mismatches are cheap to adjudicate precisely BECAUSE we keep
the source-native transcription. test_ops_phx.py fixture corrected to the PDF
value (86,309) with the known-typo assertion (close==2 expected vs workbook).

### 2026-07-09 - cross-firm results adjudicated; totals self-check added
Live cross-firm runs (zero prompt changes), then adjudicated vs the PDFs:

- **chi_pol Age_Serv_Num raw 0.55 -> REAL MODEL FAILURE.** The model shifted
  rows 50-54/55-59/60-63 one service column LEFT. Cause: Segal's layout
  interleaves count and salary lines and the text layer collapses column
  alignment into ambiguous whitespace. Adjudication: the table's printed
  column totals (Total Active row) prove the HUMAN was right (e.g. col
  '1 to 4' printed 3,261 = works only with 50-54's '2' at 5-9).
- **sd Age_Serv_Num raw 0.65 -> MODEL RIGHT, adjudicated ~1.0.** After fixing
  scoring conventions (printed '-' dashes normalized to null in the truth
  loader; zero_equals_empty for count targets) it re-scores 0.92, and ALL
  remaining mismatches are row 70: the human collector used only '65 to 69'
  and DROPPED the '70 and up' row (17 active members lost) - GROUND TRUTH
  ERROR #2. The model summed both per template semantics ('70' = 65 and over,
  as phx's collector did).

Pipeline upgrades from these lessons:
1. **Printed-totals self-check** (the chi_pol fix): the contract now asks for
   printed_row_totals/printed_col_totals; ops.totals_check() verifies the
   transcription sums against them (a one-column shift preserves row sums but
   breaks column sums). Wired into extract()'s retry loop: a totals failure
   triggers one self-correction attempt with the specific discrepancies; if
   still failing, proceeds with a loud TRANSCRIPTION SUSPECT warning.
   Retro-test: the check fires with 8 discrepancies on the saved bad chi_pol
   transcription.
2. harness: '-'/en-dash/em-dash normalized to null; score(zero_equals_empty=)
   for count targets (targets.json flag on Age_Serv_Num).

Scoreboard after adjudication: phx 2/2 perfect; sd correct (truth wrong);
chi_pol = the one real failure, now guarded by the totals tripwire - RERUN
chi_pol to test whether self-correction fixes it. If totals-guarded retry is
not enough for Segal-style layouts, next escalations: layout-aware text
(pdfplumber x-coordinates) or the vision fallback.

Evaluation lesson now twice-confirmed: disagreement with the workbook must be
adjudicated against the PDF before being read as model error - already 2
human errors found (phx typo 86306/86309; sd dropped 70+ row) vs 1 model
error (chi_pol shift).

### 2026-07-09 - chi_pol retry insufficient -> layout-preserved text (pdfplumber)
Rerun with the totals guard: tripwire fired and retried, but the model
reproduced the same shift - its notes show it KNOWS the printed totals yet
cannot fix the cells, because plain text extraction destroys the alignment
information (it cannot recover what is not there). Escalation per plan:
document text is now LAYOUT-PRESERVED via pdfplumber extract_text(layout=True)
(x-coordinate-proportional whitespace; pypdf plain text as per-page fallback
where layout mode drops content - pypdf's own layout mode loses this table
entirely). Verified: the chi p.46 rows now show their leading empty columns
visually. Cost: ~3x chars (phx 71K / chi 135K / sd 105K tokens) - fine.
System prompt now tells the model horizontal position indicates the column.
pdfplumber added to deps. chi_pol rerun pending.

### 2026-07-09 (evening) - LAYOUT FIX CONFIRMED: chi_pol 1.0
Rerun after the pdfplumber layout-preserved text (run
chi_pol_Age_Serv_Num_20260709_161002): **38/38 exact, accuracy 1.0, printed-
totals check OK, single attempt** (no retry needed). The Segal-layout column-
alignment failure is solved by giving the model geometry-preserving text.

FINAL v0.1 SCOREBOARD (rung-1 targets, whole-document, zero per-plan tuning):
| plan/target              | raw    | adjudicated | notes |
|--------------------------|--------|-------------|-------|
| phx Age_Serv_Num  (GRS)  | 1.0    | 1.0         | clean first try |
| phx Age_Serv_Wage (GRS)  | 0.966  | 1.0         | found workbook TYPO (86,306 vs PDF 86,309) |
| sd  Age_Serv_Num (Cheiron)| 0.65  | ~1.0        | conventions + human DROPPED '70 and up' row (17 members) |
| chi_pol Age_Serv_Num (Segal, hardest layout) | 0.55 -> 1.0 | 1.0 | fixed by layout-preserved text |

Three firms, four extractions, all effectively perfect after the two
pipeline lessons (totals self-check; layout-preserved text). Two ground-truth
errors found vs zero remaining model errors. This is the result package to
show Pietro.

Next candidates (in order): Age_Serv_Wage on chi_pol/sd (completes the rung-1
matrix); Ret_Rate (first rung-2 target - needs transpose + proportional
re-grid ops in the vocabulary + executor); then rung-3 (Avg_Mort blend).

### 2026-07-10 - chi_pol Age_Serv_Wage: vocabulary gap found and fixed (ratio op)
Live run (other machine synced; this machine needed pdfplumber + anthropic
installed) scored 0.0 - but adjudication shows a PIPELINE gap, not a model
failure, and the two-stage architecture is what made that diagnosable:

- Chicago Police's AV publishes NO average-salary exhibit. Exhibit C Part III
  (p.46) prints total LIVES and total annual SALARY DOLLARS by age x service.
  The model found both, transcribed both tables correctly (verified below),
  and its notes said exactly the right thing: "Average salary per cell =
  total salary / count, which deterministic code must compute". But ops.py
  v0.1 had no division operation (op #6 of the conceptual 8-op vocabulary,
  "average = total$/count", was never implemented), so the model declared the
  closest legal thing (weighted_avg) and the executor produced aggregated
  COUNTS -> wrong=38.
- The "totals check failed" warnings were a second, separate bug: the AV's own
  printed totals are rounded (sum of printed cells off by +-1 dollar on
  hundreds of millions). totals_check now uses max(0.5, 1e-5*|printed|)
  tolerance - still razor-sharp for real column shifts (which move an entire
  cell value) - and prints full-precision diffs instead of %g.

Fix (contract + executor, committed with this entry):
- ops.execute(..., derive=) - new optional declared op
  {"op":"ratio","numerator_table":i,"denominator_table":j}: both tables are
  aggregated with the SAME row/col maps (additive ops only; weighted_avg
  rejected in ratio mode), then divided cell-wise. Merged-bin averages are
  exact by construction (sum both, then divide).
- extract.py: derive added to RESULT_SCHEMA/FORMAT_SPEC/SYSTEM; validate()
  checks it (op, table indices, no weighted_avg rows) and tolerates its
  absence (old-shape responses stay valid).
- targets.json Age_Serv_Wage: new rule telling the model about the
  totals-instead-of-averages case.

Validation (ZERO new API cost - this is why we archive source-native
transcriptions): pipeline/test_ops_chipol_wage.py re-executes the ARCHIVED
run-121937 transcription under the corrected declaration -> **38/38 EXACT
(1.0)** vs the human workbook, bit-exact incl. non-round cells like
70959.51336898396 (proving the human collector also computed total$/count).
Totals check passes with the tolerance. phx regression (test_ops_phx.py)
unchanged: counts 59/59, wages 0.9661 with only the known workbook-typo
cells.

LIVE RERUN CONFIRMED (run chi_pol_Age_Serv_Wage_20260710_123312): the model
declared derive: ratio = t0/t1 UNPROMPTED, transcribed both Part III tables
(salary$ + counts, printed-totals OK), single attempt -> **38/38 EXACT
(1.0)**. Note for the writeup: Segal titles both panels near-identically; the
model assigned numerator/denominator by CONTENT, not title.

### 2026-07-10 - sd Age_Serv_Wage: second vocabulary gap (COLUMN weighted_avg); rung-1 matrix complete
Live run sd_Age_Serv_Wage_20260710_124156 crashed in ops.execute - again a
vocabulary gap the model itself flagged: Cheiron's Table A-8 publishes
averages directly (phx-style) but with FINER service columns than the target
('Under 1'+'1 to 4' -> '4'; '35 to 39'+'40 and up' -> '40'). Merging averages
across COLUMNS needs a count-weighted average, but col_map ops were only
copy/sum/share_even. The model's notes: "col ops are limited to
copy/sum/share_even, so share_even is used, though these are averages -
noted" - it declared the least-bad illegal thing; validate() missed the
share_even arity violation; the executor crashed (after archiving the
transcription, so diagnosis + fix validation cost zero API).

Fix: ops.py col op "weighted_avg" (weights = counts table, row-aggregated
first with weighted_avg degraded to sum - counts are additive; the two-stage
row-then-column weighting is exactly the full count-weighted mean of the
merged cells). Stage-1 refactored into _stage1() to reuse on the weights
table. validate() now enforces arity (copy/share_even take exactly one
source; weighted_avg requires integer weights_table; both maps additive in
ratio mode) so bad declarations are caught in the RETRY LOOP, not the
executor. Schema/FORMAT_SPEC/SYSTEM/targets.json updated symmetrically.

Zero-cost validation (pipeline/test_ops_sd_wage.py, archived transcription +
corrected col ops): 52 exact + 1 close of 57; ALL 5 mismatches are the age-70
row, adjudicated as GROUND-TRUTH ERROR #2 AGAIN (the workbook's row 70 equals
A-8's '65 to 69' row VERBATIM - the collector ignored '70 and up' on the wage
sheet too; our blend is correct per template semantics '70' = 65-and-over).
Regressions clean: chi_pol ratio test 38/38, phx counts 59/59 / wages 0.9661
(known typo cells only).

FINAL RUNG-1 SCOREBOARD (3 plans x 2 targets, three firms, adjudicated):
| plan/target | raw | adjudicated |
|---|---|---|
| phx Age_Serv_Num (GRS) | 1.0 | 1.0 |
| phx Age_Serv_Wage (GRS) | 0.966 | 1.0 (workbook typo) |
| chi_pol Age_Serv_Num (Segal) | 1.0 (after layout fix) | 1.0 |
| chi_pol Age_Serv_Wage (Segal) | 1.0 (after ratio op) | 1.0 |
| sd Age_Serv_Num (Cheiron) | 0.65 | ~1.0 (human dropped 70+) |
| sd Age_Serv_Wage (Cheiron) | 0.912 (local re-exec) | ~1.0 (same human error) |

LIVE RERUN CONFIRMED (run sd_Age_Serv_Wage_20260710_125005): the model
declared col weighted_avg (weights=t1) UNPROMPTED for both column merges and
row weighted_avg for '70'; score identical to the local re-execution
(52 exact + 1 close of 57, mismatches = the known age-70 human error only).
The format-retry fired once on attempt 1 (Parley drops output_config; the
guard corrected it) - expected behavior.
Running tally: 2 human ground-truth errors (in 3 sheets!) vs 1 model error
(chi_pol shift, fixed by layout text) vs 2 pipeline vocabulary gaps (ratio,
col weighted_avg - both flagged by the model itself in notes).

Next: Ret_Rate (rung 2 - transpose + proportional re-grid ops), then rung 3
(Avg_Mort blend).

### 2026-07-10 - rung-2 machinery built: transpose + overlap_weighted + percent conversion (Ret_Rate live-ready)
Contract/executor extensions (v0.3), all keeping the model at ZERO arithmetic:
- transpose (top-level bool): table transcribed AS PRINTED; code transposes
  before mapping; row_map then maps the printed COLUMNS onto target rows.
- op "overlap_weighted" (rows and cols): re-grids RATES across non-aligned
  bins. The model declares each source bin's numeric span ("source_spans",
  null = open end: '<15' -> [null,14]); the TARGET bins' spans are fixed
  template semantics in targets.json (target_row_spans/target_col_spans),
  passed to ops.execute by run_test - never model-declared. Code computes
  integer-year overlap weights: value = sum(w_s*v_s)/sum(w_s). Rates are
  intensive: inside-one-bin targets copy; spanning targets blend (the
  verified 12-19 = 3/8x0 + 5/8x0.225 = 0.140625 case).
- values_unit: "percent" per table -> code DIVIDES by 100 (division, not
  *0.01: 35.00/100 == the double a human typing 0.35 produces - bit-exact
  scoring; *0.01 gives 0.35000000000000003).
- validate() checks all of it (transpose bool, spans aligned/integer/null,
  spans only on overlap_weighted); old-shape responses stay valid.
- targets.json Ret_Rate spec completed (spans, convert_percent_to_decimal,
  rewritten rules); no run_test.py plan changes needed beyond passing the
  new fields through.

DISCOVERY - two UNDOCUMENTED discrepancies between the phx Ret_Rate workbook
and the PDF (phx_log.txt says only "broken out and averaged if needed"; we
cannot tell whether these are deliberate collector choices or errors):
- the age-70-row discrepancy: the AV's printed age-70 row (100% retirement
  everywhere) is IGNORED; the workbook's col 70 carries the 66-69 rates.
- the '>31'-boundary discrepancy: the workbook copies the '>31' column into
  all service bins 31+, i.e. treats '>31' as 31-and-over. But the printed
  labels are internally consistent and unambiguous: '25-31' includes 31, so
  '>31' can only mean 32+ (correct handling 50/50-blends row 31-32). The
  workbook CONTRADICTS the printed table here - deliberate unrecorded
  override or error, unknown.
The span-declaration design makes exactly this auditable: the ambiguity is
IN the declared spans, not hidden in arithmetic.

Zero-cost verification (pipeline/test_ops_phx_retrate.py, hand-transcribed
ACTUAL p.50 B.5 table): literal spans -> 163/189 with ALL 26 mismatches
confined to row 31-32 + col 70 (the two discrepancies above), every blend cell bit-exact
(0.140625, 0.178125, 0.204375, 0.25125, 0.22, 0.315625, 0.296875);
human-implied spans -> 180/189, ONLY the 9 col-70 cells differ (the age-70-row discrepancy).
Regressions: phx counts/wages, chi_pol ratio, sd col-weighted_avg all pass;
old-shape contract responses still validate.

Expected live phx Ret_Rate raw score: ~0.95 if the model reads the bins like
the human, ~0.86 literal - either way the col-70 mismatches are the age-70-row discrepancy, NOT
model error. Adjudicate against the PDF as always. Cross-firm chi_pol/sd
Ret_Rate after phx.

### 2026-07-13 - FIRST LIVE RUNG-2 RUN (phx Ret_Rate) + overlap-resolution fix (v0.4)
Live run phx_Ret_Rate_20260713_093322 (this machine; format guard corrected
19 contract problems on attempt 1 - Parley as usual). Raw 0.778, decomposed:

1. **Transcription: PERFECT.** The 14x4 p.50 B.5 table matches the PDF
   exactly; transpose, values_unit=percent, and all span declarations correct
   (notes state '>31' -> [32,null] explicitly - the correct reading: '25-31'
   includes 31, so '>31' is 32+).
2. **col 70 (9 cells): the age-70-row discrepancy, as pre-registered** - model faithfully uses the
   AV's printed 100%-at-70 row; the workbook ignores it.
3. **row 31-32 (17 cells): the '>31'-boundary discrepancy, as pre-registered** - correct '>31'=[32,null] span
   blends 25-31/>31 50-50; the workbook copies '>31'.
4. **row 12-19 (16 cells): NEW model error class** - the model declared all
   spans correctly but mapped 12-19 to '<15' ONLY, missing its 15-24 overlap
   (its own notes say "5-11 and 12-19 fall entirely within '<15'" - a
   reasoning slip the spans themselves contradict).

Fix (v0.4): **overlap_weighted source sets are now COMPUTED, not trusted.**
ops.resolve_overlap_sources() pools the declared (bin -> span) pairs per
axis and derives each target's source set from span arithmetic; the model's
own set is only an audited hint (run_test prints "[stage B] overlap audit"
lines when they differ). The model's genuine judgment stays exactly where it
belongs: what each printed bin MEANS (the span; any genuinely ambiguous label remains
visible and auditable). validate() now also rejects a bin declared with two
different spans (caught in the retry loop, not the executor).

Zero-cost validation: archived run re-executed -> **0.8624 (163/189), the
exact pre-registered "literal reading" scenario**; audit line fires:
"12-19: model declared ['<15'] but spans imply ['15-24','<15']". ALL 26
remaining mismatches = the age-70 row (9) + the '>31' boundary (17); zero unexplained. Full regression
suite green (phx counts/wages, chi_pol ratio, sd col-weighted_avg, retrate
executor test).

Rung-2 verdict: the machinery works end to end live; the one new error class
found is now structurally eliminated (same pattern as rung 1: model
transcribes + declares meaning; code does ALL derivation). Next: cross-firm
Ret_Rate (chi_pol, sd - zero prompt changes), then rung 3 (Avg_Mort
cross-table blend op).

### 2026-07-13 (later) - '>31' adjudicated by Niccolo; chi_pol Ret_Rate adjudicated; tier + carry-forward rules added
**'>31' boundary re-adjudicated (Niccolo):** the printed labels are NOT
ambiguous - mathematically '>31' excludes 31, and the adjacent '25-31' column
already contains it. So the model's literal spans are simply CORRECT, and the
phx workbook's treatment (copying '>31' into bins 31+) is a deviation from
the labels, not an alternative reading. Both residual classes of the phx
Ret_Rate run are therefore workbook deviations from the PDF.

**chi_pol Ret_Rate live run (raw 0.709) adjudicated:**
- Transcription PERFECT: the p.72 table is age(50-65) x Tier1/Tier2 - not
  service-structured at all; both tier columns transcribed exactly (verified
  against the PDF), values already decimals (correctly no percent flag).
- 10 wrong (row 5-11, ages 50-59): the human mapped service 5-11 -> Tier 2,
  rest -> Tier 1 (her log documents it; rationale: Tier 2 = hired >= 2011 ->
  at most ~9 years of service at end-2019, so low-service buckets ARE Tier 2
  members). The model mapped everything -> Tier 1 (stated in notes). REAL
  model-judgment gap - the human's tier->service translation is better.
- 45 missing (ages 66-70): the printed table ends at 65 with rates 1.00
  (mandatory retirement); the human carried 1.00 forward to the template's
  66-70 columns; the model faithfully left unprinted ages empty.

**Engine reality (answer to "extract per-tier?"):** the simulation engine
consumes ONE retirement-rate matrix per plan (tiers differ by benefit rules,
not rate tables). Tier-published rates are folded into the template's
SERVICE dimension via hire-date arithmetic - service at valuation date
determines tier membership. Both of the human's moves are already
expressible with the existing 'copy' op; what was missing was GUIDANCE.

**Fix (guidance-only, no code):** two rules added to targets.json Ret_Rate:
(1) tier-published tables -> transcribe all tier columns, map each target
service row to its tier via the hire-cutoff/valuation-date arithmetic, state
it in notes; (2) if the printed ages end below the target's last column AND
the final printed rates are 1.00, carry 1.00 forward by copying the last
printed age's column. chi_pol rerun pending to test both.

**sd Ret_Rate: NO GROUND TRUTH** - the workbook sheet exists but has 0 filled
cells (the collector's log said "unclear best way to aggregate" and she never
did it). sd cannot be scored on this target; rung-2 scoring corpus = phx +
chi_pol. (A future sd run would be a PRODUCTION-style extraction - output
with no answer key, reviewable via the audit artifacts.)

### 2026-07-13 (correction) - the two Ret_Rate rules RETRACTED; tier handling is an OPEN DECISION
I (the assistant) added the tier->service and carry-1.00-forward rules by
adopting the human collector's approach as template convention - while
Niccolo was explicitly questioning whether that approach is even right. Both
rules are removed from targets.json. Correction to the engine claim as well:
the engine's tier loop swaps COLA/WageYears/BenefitCap/BenefitFactor/
RetirementStart/NyearFullBenefit per tier, and RetirementRate is a single
plan-level matrix - so tiers DO get per-tier retirement AGES, but per-tier
retirement-rate MATRICES have no input slot today. The real world (chi_pol
p.72) does publish per-tier rate assumptions.

THE OPEN DECISION (Niccolo's):
A. Keep the engine as-is -> tier-published rates must be folded into ONE
   service x age matrix -> then choose the folding convention (the human's
   service-bucket mapping is one candidate; it is only exact near the
   valuation date - as simulated Tier-2 members accumulate service they
   would drift into buckets carrying Tier-1 rates).
B. Extend the engine: swap RetirementRate per tier in the tier loop (like
   COLA), extraction target becomes per-tier grids. More faithful; touches
   the verified engine and the template format.
C. Defer: the archive ALREADY stores both tier columns source-native (the
   chi_pol run transcribed both), so any folding convention can be
   re-executed later from the archived transcriptions at zero API cost. Only
   the derived grid depends on the decision.
Also open, same question smaller: ages beyond the printed table (chi prints
50-65 ending at 1.00; the template grid runs to 70) - carry 1.00 forward
(the human's move), leave empty, or shrink the template's age range.

### 2026-07-13 - Sep_Rate target built (offline-verified); assumption register created
`assumption_register.md` created (per Niccolo): the single record of embedded
modeling assumptions/decisions with options, seeded with the tier question
(deferred - both tier columns archived), ages-beyond-table, the phx Ret_Rate
deviations, sd's blank Ret_Rate, and the two known workbook defects. The two
prematurely-added Ret_Rate rules were retracted the same day.

Sep_Rate target (offline work, no live run yet):
- Template grid confirmed IDENTICAL across phx/chi_pol/sd: ages 25..70 x
  service cols 1,2,3,4,6,8,10,11,12,30,40. Reverse-engineered the col
  semantics from BOTH collectors' numbers: spans [1],[2],[3],[4],[5-6],
  [7-8],[9-10],[11],[12],[13-30],[31-40] - chi's age-70 row proves the
  averaging (col '6' = mean of source years 5,6) and both collectors dropped
  source year 0 (register entry 4).
- targets.json spec written: same declaration machinery as Ret_Rate (spans +
  overlap_weighted; percent flag; zero_equals_empty because collectors were
  inconsistent about 0-vs-empty in filler cells) + one new executor step:
  ops.zero_impossible() (entry-age-20 floor, mode=upper per the phx
  collector's convention; register entry 4). Rules cover the known source
  shapes: age x service (phx), service-only -> transpose + copy to all age
  rows (chi), per-group tables -> transcribe all, flag unblended (sd; the
  group blend is the rung-3 op).
- Offline proof (test_ops_phx_seprate.py, hand-transcribed actual p.49
  table): 87 exact, 1 wrong (the collector's own age-25/col-6 inconsistency),
  22 missing (her rows 65/70 carried beyond the printed table) - i.e. every
  cell inside the printed data reproduces exactly and every residual is a
  known register item. Full regression suite green.

Live runs pending (user): phx, chi_pol, sd Sep_Rate.

### 2026-07-13 - Sep_Rate live runs (all three plans) adjudicated
- **phx 0.9909:** 109/110 exact; single wrong = the known collector
  inconsistency (age-25/col-6). CAVEAT: the model declared rows 65/70 <-
  copy(60) - carrying rates beyond the printed table DESPITE the spec's
  no-extrapolation rule (instruction miss, but fully visible in the ops
  audit; matches the collector's move). The derived grid embeds the OPEN
  carry-forward assumption (register entry 2) - flagged in the register.
- **chi_pol 0.9767:** transpose + per-year spans + blends all correct; ALL 9
  residuals are impossibility-convention noise, and they prove the
  collectors had NO consistent rule (chi's collector emptied attainable
  cells at ages 30-40 but filled an unattainable one at age 50/svc 31-40).
  Register entry 4 updated: the convention needs a ruling.
- **sd 0.2545, as pre-registered:** the model transcribed BOTH group columns
  (General/Safety), mapped from General, flagged the unblended state. The
  truth's blend weights VARY BY AGE (age-specific group headcounts) - which
  pins the spec of the missing rung-3 op: cross-table blend with an
  age x group headcount weights table; same op shape Avg_Mort needs.
Sep_Rate verdict: pipeline machinery correct on all three shapes (age x
service grid / service-only / per-group); remaining gaps are the open
conventions (register) and the rung-3 blend op.

NEXT: the rung-3 op (cross-table population-weighted blend, weights from a
headcount table, age-aligned) -> unlocks sd Sep_Rate AND Avg_Mort (the last
sheet class). Then Retirement (retdist; ops already exist).

### 2026-07-13 - production-mode plans added (cold extraction test)
Niccolo's call: run the extractor on documents NOBODY pre-extracted, then
review. Added to the plans registry: aus (Austin COAERS - workbook empty,
fully cold, GRS), mil (Milwaukee ERS - NOVEL actuarial firm, only
Age_Serv_Num has truth), bos (Boston SBRS stub, Segal) - all with in-folder
AVs and healthy text layers (aus 89K / mil 161K / bos ~ tokens).
run_test.py now handles absent/blank truth: PRODUCTION MODE - artifacts
saved, no score, review = adjudicate extraction.json + derived.json against
the PDF; external sanity check available vs PPD actives_tot. Runs pending.

### 2026-07-13 - Milwaukee cold run: cross-table additive sum op built
First cold-corpus scored anchor: `mil_Age_Serv_Num_20260713_161425` (novel
AV format, only Age_Serv_Num has truth). Raw score 0.3625 looked bad, but
adjudication shows a PIPELINE vocabulary gap, not a model failure:

- Stage A found and transcribed the three group-level active-count tables
  that together cover the whole plan: General Employees (8,442), Policemen
  (1,827), Firemen (705). All three printed-totals checks passed; total =
  10,974, matching the workbook.
- The model's notes said the right deterministic operation: "Code should sum
  the three source tables cell-wise." But the contract had only
  `derive=ratio`; `ops.execute()` therefore mapped table 0 only (General),
  producing total 8,442 and the systematic undercount.

Fix: document-level `derive={"op":"sum","tables":[...]}` added. In sum mode,
same-shaped additive source tables are summed cell-wise first, then the
normal row/col maps run once; weighted_avg maps are rejected because this op
is for additive quantities. `targets.json` Age_Serv_Num now tells the model
to use derive=sum when a plan-wide count distribution is split across
same-shaped employee-group tables.

Zero-cost validation: `pipeline/test_ops_mil_counts.py` re-executes the
archived Milwaukee transcription with `derive=sum(t0,t1,t2)` -> **80/80
exact (1.0)** vs the human workbook. Printed totals OK on all three group
tables. This creates no new modeling assumption; it is pure addition of
published subgroup counts.

### 2026-07-13 - production review: Austin/Milwaukee wage grids flagged, not accepted
Reviewed the next three out-of-sample artifacts (no new edits during the
review):

- `mil_Age_Serv_Wage_20260713_164600`: the report does not publish average
  salary by age x service, nor total salary dollars by age x service. It has
  age-only earnings/salary summaries and separate age x service count tables.
  The model first returned the clean "no source table" answer, but the current
  validator requires a non-empty `source_tables` list, so the retry included a
  count table as a placeholder and left all mappings empty. `derived.json` is
  80 null cells. This is a flagged unavailable target, not an accepted wage
  extraction.
- `aus_Age_Serv_Num_20260713_164723`: strong production extraction. Table
  13A is already "All Active Participants" (Groups A/B are subsets), printed
  totals check out, source service years 0-4 are summed into target col `4`,
  and the derived active total is 10,149.
- `aus_Age_Serv_Wage_20260713_164833`: transcription is right but the output
  is not accepted as final. Table 13A prints one `Average Annual Salary` per
  age band only; the model copied each age average across every service
  bucket because the target rule permits copying coarser averages. The 10 age
  values are internally consistent (count-weighting by the Austin age totals
  reproduces the printed all-ages salary of $69,715), but the service
  dimension is not observed.

Niccolo ruling for now: age-only salary evidence must NOT be silently accepted
as an `Age_Serv_Wage` grid. It should be flagged as an unresolved
assumption/contract issue until a decision is made. The assumption register
now has an OPEN entry for this class. Likely future fix: add an explicit
`unavailable` / `underdetermined` representation, and/or tighten
Age_Serv_Wage guidance so copying an average across an entirely missing
dimension is not treated as a valid extraction by default.

### 2026-07-14 - second-reviewer adjudication of the 2026-07-13 production runs
Independent re-check of the review above (all claims verified against the
artifacts and the PDFs, no disagreement with the conclusions):
- aus Age_Serv_Num: transcription compared cell-for-cell against the printed
  Table 13A (p.36) - all 120 cells, row totals, and column totals match.
- External PPD cross-check (ppd-data-latest.xlsx, fy2019 `actives_tot`):
  Milwaukee 10,974 and Austin 10,149 - both equal the extracted totals
  exactly. Two fully independent confirmations of the cold count runs.
- mil Age_Serv_Wage record.json confirms the sequence as described: attempt 0
  answered honestly with `source_tables: []` ("no data exists to derive
  average salary by age and service"); the validator's non-empty rule forced
  the placeholder retry. The contract penalizes the honest answer - the
  `unavailable` fix in register entry 6 is the right target.
- One executor consistency note (no current data hits it): in
  `_sum_tables`, a "*" summed with numbers is silently dropped (5 + "*" = 5),
  while ratio mode propagates "*". Whether a masked group count should yield
  "*" or a partial sum is a small open convention; flagged, not changed.

### 2026-07-14 - v0.5: the 'unavailable' contract (the mil wage fix)
The mil Age_Serv_Wage run exposed a contract defect: the model's FIRST answer
was the honest one (`source_tables: []`, "no data exists to derive average
salary by age and service"), but the validator's non-empty rule rejected it
and the retry was forced to stuff in a placeholder counts table. The contract
penalized honesty.

Fix (mechanism only - no modeling decision taken):
- Stage A may now declare `"unavailable": true` when the target (or a whole
  dimension of its grid) is not published in any derivable form. Requirements
  enforced by validate(): row_map/col_map EMPTY, derive null, notes must state
  what the document publishes instead. source_tables MAY carry the closest
  related tables (transcribed as printed) as archived evidence - so whatever
  is later decided with the coauthor (broadcast age-only averages, leave
  blank, other source) can be applied from the archive at zero API cost.
- The prompt now explicitly forbids approximating a missing dimension (e.g.
  copying an age-only average across every service column, as the aus wage
  run did) - per the standing ruling in register entry 6 these outputs are
  flagged, not accepted.
- The old failure's validator message now routes the retry to the fix: an
  empty source_tables without the flag tells the model to declare
  unavailable properly.
- Stage B (`run_test.py`) skips execution and derives `ops.empty_grid()` -
  the all-null template grid - and says loudly that the missing data is an
  assumption-register item. Scoring still runs where truth exists, so a lazy
  unavailable is punished: vs the filled mil counts sheet an empty grid
  scores 0.275 (only the literal-zero cells match under the 0-equals-empty
  counts convention; all 58 data cells score missing).

Zero-cost validation: `pipeline/test_unavailable.py` - clean declarations
accepted (with and without evidence tables), half-states rejected (maps/
derive/blank notes), and the ARCHIVED mil attempt-0 response now receives the
unavailable guidance. Full regression suite still green (6/6 executor tests).

### 2026-07-14 - v0.6: the rung-3 op (group_weighted population blend), offline-verified
The cross-table population-weighted blend - the op sd Sep_Rate pinned and
Avg_Mort needs - is built and verified at zero API cost.

**First, the sd truth's recipe was reverse-engineered exactly** (solve
a = (truth - rS)/(rG - rS) per cell from the archived B-2 transcription):
the collector blended General/Safety rates with JOINT (age-bin x
service-bin) headcounts from Tables A-9/A-11 (p.45/46) - a(25, svc 1-4) =
27/(27+194) = 0.1222, a(30, 10-14) = 38/(38+85) = 0.3089, confirmed against
the printed tables - and mapped each template service col from a SINGLE
source year (col '6' <- year 6, more evidence on register entry 4's
col-semantics question).

**The op (v0.6), zero model arithmetic as always:**
- `group_weighted` (row_map AND col_map): sources = the group rows/columns;
  `weights_tables` = one source_tables index PER source, each a transcribed
  headcount table. The weight for output cell (r, c) is the group's
  population at that cell's coordinates: exact label match, or span
  containment via the weight table's declared `row_spans`/`col_spans` (NEW
  optional per-table fields - the model declares printed bin semantics, code
  does the matching) against the target spans; partial bins contribute
  |bin ∩ query|/|bin| of their count (common factors cancel in the blend).
  Single-row/column weight tables broadcast along the missing axis.
  value = sum(w_s*v_s)/sum(w_s).
- `transpose` semantics FIXED to main-table-only: aux tables (weights) keep
  their printed orientation (transposing them would flip the axes under the
  weight lookup). No archived case relied on aux transposition.
- Rejected in ratio/sum modes (additive-only, like weighted_avg); validate()
  enforces weights_tables alignment/indices and per-table span shape;
  old-shape responses stay valid.

**Zero-cost verification:**
- `test_ops_sd_seprate_blend.py` (hand-transcribed ACTUAL B-2 + A-9 + A-11):
  97 exact + 1 close of 110 vs the sd workbook, joint-count shares
  reproduced exactly; ALL 12 remaining mismatches are cols '30'/'40' - the
  collector weighted those by the single count bucket containing year 30/40
  while the op uses the value's source-bin span ('20+'); a weight-bucket
  convention within register entry 4, both variants re-derivable.
  (Baseline before the op: 0.2545 unblended.)
- `test_ops_phx_mort_blend.py`: the rung-3 LADDER case - one group_weighted
  entry with sources [Pre-M, Pre-F, Post-M, Post-F] and weights
  [actives, actives, retirees, retirees] reproduces the verified phx
  unisex mortality blend to the last digit (age 50:
  0.0014591621621621621; the M/F simple average is absorbed by weight
  scale invariance: [n,n,m,m] weights ≡ (M+F)/2 then n:m blend).
- Full suite green: 9/9 executor tests (incl. all pre-existing).

Register updated (entry 4): the sd recipe evidence + the cols-30/40
weight-bucket convention question. targets.json Sep_Rate per-group rule now
declares the blend instead of flagging unblended output.

NEXT: (a) live sd Sep_Rate rerun - tests whether the model declares
group_weighted + weight tables + spans unprompted (the derived grid embeds
whichever conventions - adjudicate per register); (b) the Avg_Mort target
spec (grid semantics from the template workbook + rules; the blend op and
the percent/spans machinery are ready); (c) the remaining cold runs (bos,
aus/mil rung-2 targets).

### 2026-07-14 - LIVE sd Sep_Rate: blend declared UNPROMPTED; two declaration
gaps moved into the retry loop (v0.6.1)
Live run sd_Sep_Rate_20260714_195442. The headline: the model transcribed
B-2 AND both A-9/A-11 headcount tables (printed-totals OK on both), declared
group_weighted with weights_tables=[1,2] on every age row, and used
TEMPLATE-faithful col maps (overlap_weighted 5+6 -> col '6', 13..20+ -> col
'30' - more faithful than the collector's single-year convention). It missed
two DECLARATIONS: no row_spans/col_spans on any table, and no
values_unit=percent on B-2 - the executor raised its clear errors (by
design), crashing after archiving.

Zero-cost salvage: patching the spans + unit mechanically and re-executing
the archived declaration scores 0.6455, and EVERY mismatch is pre-registered
convention noise: (i) impossibility-cell zeroing (our strict mode=upper vs
her fills - register 4), (ii) merged-col semantics (template [5,6] average
vs her single-year - register 4), (iii) her joint-bucket weights on cols
30/40. Cols 1-4 exact across all ages: the blend arithmetic is confirmed
live. Verdict: model right, contract under-enforced.

Fix (v0.6.1) - both gaps now caught in the RETRY loop, not the executor:
- validate() requires row_spans/col_spans on every multi-row/col weights
  table referenced by group_weighted, and spans on the main table's
  weight-lookup axis (row_spans when transpose=true).
- validate() gained a unit-plausibility check (needs the target spec, now
  passed in): a main table with values > 1.5 for a probability target and no
  percent flag is flagged with the exact correction.
- Retro-test: the archived live run yields exactly 6 problems (the 5 span
  gaps + the unit); the fully-declared version validates clean. Full suite
  9/9 unchanged.

The register-4 convention rulings (impossibility mode, merged-col semantics,
aggregate-col weight bucket) remain THE open item deciding what sd Sep_Rate's
final derived grid should be; all variants re-derivable from this run's
archived transcription. A live re-rerun would only confirm the retry loop
closes the declaration gaps end to end (~$2, optional).

### 2026-07-14 - Avg_Mort target spec built and executor-proven (offline)
The last sheet class. Template confirmed from the workbooks: 100 single-age
rows (20-119) x one 'Death_Prob' column; phx is the ONLY ground truth
(chi_pol and sd Avg_Mort sheets are EMPTY - both become production-mode
targets; chi publishes life expectancy, covered by the unavailable rule).

The verified phx recipe reduces to ONE group_weighted column entry:
Death_Prob <- group_weighted(Pre-M, Pre-W, Post-M, Post-W) with
weights_tables [actives, actives, retirees, retirees]:
- M/F simple average = sharing one weight table per population;
- the 20-49 pre-only / 50-69 blend / 70+ post-only segmentation EMERGES from
  the weight tables' coverage: retirees have no bins below 50, and the
  actives 'Over 65' bin is declared CLIPPED to [65,69] (the collector's
  implicit judgment, now a stated-in-notes rule + adopted convention in the
  register). No hard-coded segments anywhere.
- each 5-year sample age's declared span ([50,54]...) maps it onto its
  band's single-age rows; no extrapolation past age 94 (the workbook's
  95-119 carry-forward = register entry 2's question, 25 known residuals).
- retiree weights confirmed against the workbook: 55-59 = 594 matches the
  value back-solved from truth at age 55 exactly.

targets.json Avg_Mort spec written (rules incl. the unavailable path for
life-expectancy-only documents). Executor fix: overlap_weighted entries with
EMPTY sources now return None (the legitimate no-data declaration) instead
of raising. Offline proof (test_ops_phx_avgmort.py, hand-transcribed actual
p.48 panels + F.3 age totals + retiree counts): **75/75 printed-range cells
EXACT, zero wrong**, only residual = the 25 carry-forward cells. Suite 10/10.

NEXT: live phx Avg_Mort (~$1.5-2) - the full rung-3 ladder case end to end;
expect ~0.75 raw with all mismatches being the 95+ carry-forward. Then bos
counts/wage cold runs; then Retirement (retdist).

### 2026-07-14 - LIVE phx Avg_Mort: rung-3 ladder case ran end to end; two weight judgments adjudicated
Live run phx_Avg_Mort_20260714_202443, raw 0.25. Adjudication: ZERO
mechanical errors - the model transcribed all three tables perfectly (the
p.48 panels as one 15x6 table; F.3 age totals WITH the [65,69] clip declared
per the rule; F.6 pay-status counts), declared the single group_weighted
column with weights t1,t1,t2,t2, per-band row maps, values_unit=percent,
no extrapolation past 94, and excluded the disability rates - all
unprompted, single attempt. The whole score gap is two WEIGHT JUDGMENTS
plus the known 95+ carry-forward:
1. Weight population: the model summed F.6's Service Retirees + Disabled +
   Beneficiaries; the collector used Service Retirees only (her counts ARE
   F.6's service-retiree column: 168/594/1178/1499/... - source recovered).
   The model's choice is self-inconsistent (it excluded the post-disability
   RATES but included disabled members in the weights) - now a rule:
   weights must match the populations whose rates are blended. Beneficiaries
   in/out remains genuinely open -> register entry 6b.
2. '<55' bottom bin read literally as [null,54], smearing 280 payees across
   ages 0-54 (the small 20-49 contamination, 15 cells 'close'). Now ruled:
   clip retiree bottom bins to plausible retirement ages ([50,54]).
Zero-cost re-derivation of the ARCHIVED transcription with the collector's
two choices: **75/75 printed-range cells EXACT** - identical to the offline
proof; only the 25 register-2 carry-forward cells remain. targets.json
Avg_Mort rules 2-3 strengthened (weight-population consistency; clip BOTH
open ends incl. retiree bottom bins).

All three rungs of the difficulty ladder are now live-proven. Remaining
live items: bos counts/wage cold runs; aus/mil rung-2/3 targets; sd
Sep_Rate confirm rerun. Remaining build item: Retirement (retdist) target
spec - ops all exist.
