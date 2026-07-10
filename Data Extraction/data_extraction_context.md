# Data Extraction Context

**Created:** 2026-07-08
**Purpose:** The living document for the AV-PDF -> model-workbook extraction pipeline: the methodology we currently believe in (update it when we change our mind) and the chronological development log. Companion documents: `Documentation/ml_extraction_handoff.md` (the worked examples / difficulty ladder shared with Pietro Ramella), `Documentation/city_extraction_catalogue.md` (per-plan extraction status + human collector logs), `Documentation/model_input_dictionary.md` (what each extracted sheet feeds in the model).

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
