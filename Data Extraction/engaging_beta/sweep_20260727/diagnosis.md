# Full corpus sweep 2026-07-27 — grid + adjudication (READ THIS to reproduce the diagnosis)

Batch `_batch_resumable`, 96 cells (16 plans x 6 sheets), run post all this-week's
fixes. Artifacts here: `summary.json`, `summary.csv`, `ra_worklist.csv`
(per-cell owner routing). Full per-run artifacts are committed locally under
`runs/sweep_20260727/<plan>_<target>_<ts>/` — the exact path is the `run_dir`
column in `ra_worklist.csv` (extraction.json = raw tables + declared ops +
notes; derived.json = output grid; report.json = per-cell mismatches).

**IMPORTANT framing (Niccolo's corrections, do not regress):** the workbook is
NOT the reference and mostly does not exist per plan/sheet — the reference is
the **source PDF (AV/CAFR)**. A score only exists where a 2022 workbook exists;
"verified" means a human compared the extracted value to the PDF. Scores are
triage hints, not truth.

## The grid
```
plan       Age_Serv_Num  Age_Serv_Wage   Ret_Rate   Sep_Rate   Avg_Mort   Retirement
aus          prod         prod           prod        prod        UNAV        UNAV
bos          CRASH        CRASH          prod        prod        prod        UNAV
chi_edu      1.00         0.00(ratio)    0.00        0.00        prod        UNAV
chi_ff       0.98!        0.00(ratio)    UNAV        0.09        UNAV        0.50
chi_gen      0.98         0.00(ratio)    0.00        0.00        CRASH       0.50
chi_pol      0.87(shift)  0.00(ratio)    0.00        0.00        prod        1.00
dal          0.98         0.02           0.00        0.00        0.00        1.00
hou_pol      1.00!        0.98           1.00        0.00        0.00        UNAV
lax_ffpol    1.00         0.92           prod        0.39        prod        UNAV
lax_gen      0.97         CRASH          UNAV        0.00        prod        UNAV
lax_uty      1.00         1.00           0.66        0.17        prod        UNAV
mil          1.00         prod           UNAV        0.00        UNAV        0.00(map)
phi          1.00         1.00           UNAV        0.17        0.00        CRASH
phx          1.00         0.97           0.86        0.79        0.55        1.00
sd           0.92         0.91           CRASH       0.18        CRASH       0.00(asmpt)
sf           0.99         0.93           prod        0.32        0.00        0.50
```
Tally: **13 OK · 47 CHECK · 15 PROD(no workbook) · 14 UNAV(model says absent) · 7 CRASH.**
Owner split (ra_worklist.csv): **58 RA · 26 assumption · 12 me.**

## Adjudication — the same-looking 0.00s have DIFFERENT causes (read the artifacts, not the score)
- **`0.00(ratio)` chi_edu/chi_ff/chi_gen/chi_pol Age_Serv_Wage — MINE (highest-leverage fix).** Each transcribed the salary-TOTALS table + the counts table correctly and its notes say "average = totals/lives", but declared **`derive: None`** — so the output is the raw million-dollar totals, not averages (e.g. chi_edu <25/svc4 cand=2,272,208 vs truth 43,955). NOT an interleaved-layout transcription failure (my earlier guess was wrong). One instruction/validator fix (force derive=ratio when a wage source is totals+counts; or reject an Age_Serv_Wage grid whose values are implausibly large) likely flips all four to ~1.0.
- **`0.00(map)` mil Retirement — MINE.** Right approach (derive=sum of 3 group tables, annualize_monthly) but MIS-MAPPED columns: Number got the monthly-benefit total (cand 4,912,470 vs truth 1,762), AverageBenefit got ~12. The executor test passes on a hand-correct declaration; the live model mis-declared the column sources.
- **`0.00(asmpt)` sd Retirement — ASSUMPTION.** Model correctly notes the source combines Retirees+Disabled+Beneficiaries and cannot isolate Service Retirees; left empty. Register 6c (which payee population). Not an error.
- **`0.87(shift)` chi_pol Age_Serv_Num — RA (real transcription error).** One-row column shift on the age-64 (60-64) row; source stops at age 63 so target 70 is empty. Localized, ~4 cells.
- **Ret_Rate / Sep_Rate / Avg_Mort 0.00s — mostly ASSUMPTION (register-gated):** tier folding (reg 1), ages-beyond-table (reg 2), impossibility zeroing + group-blend weights (reg 4), beneficiaries (reg 6b), sd aggregation (reg 5). Some are also hard cross-table blends.

## The 4-way triage (what to work on, in order)
**A. SOLVE NOW (mine, high leverage, mostly code/instruction):**
1. **Wage `derive=ratio` miss** — 4 chi plans (chi_edu/ff/gen/pol Age_Serv_Wage) from 0.00 -> ~1.0. Biggest single win. Fix: instruction + a validator/plausibility guard (Age_Serv_Wage output can't be a million-dollar "average").
2. **mil Retirement column mapping** — instruction/guard so Number<-count col, AverageBenefit<-ratio(monthly-total,count) x12.

**B. DIG DEEPER (mine, diagnose from artifacts/dumps):**
3. **7 crashes** — bos ASN/ASW, chi_gen Avg_Mort, lax_gen ASW, phi Retirement, sd Ret_Rate/Avg_Mort. Use the truncation classifier (loop vs large) + read contract errors. Some are loops (fixed to skip), some may be genuinely large or contract-arity.
4. **dal Age_Serv_Wage 0.02** — adjudicate; likely another totals/ratio or structure issue.
5. **chi_pol/lax_uty count '!' + chi_pol 0.87 shift** — localized transcription; check if best-of-N can select a clean sample or if the source text is the problem.

**C. ASSUMPTION-DEPENDENT (RA adjudicates -> flag -> Niccolo+coauthor):**
6. All Ret_Rate/Sep_Rate/Avg_Mort low/zero cells + sd Retirement. These are register items 1-6 (tier handling, carry-forward, impossibility conventions, beneficiaries, blend weights, aggregation). Blocked on decisions, NOT code. ~26 cells.

**D. HARDEST / open unknowns:**
7. **Rate/blend targets that need BOTH a convention decision AND a hard cross-table blend** (sd Sep_Rate group blend; Avg_Mort population blends) — even after the decision, the mapping is the rung-3 machinery's edge.
8. **Image-only tables** — UNKNOWN VOLUME. Any UNAV cell that is actually a picture (no text layer) needs a DIFFERENT extraction model (vision). The RA's Stream-B diagnosis quantifies this; currently unmeasured.

## This-week's fixes already banked (don't redo)
#2 wage table-order (phx 0.966), #4 averages false-suspect, #5 plan-total
reconciliation (mil 1.0 - the big one), C per_1000 + ratio-detection, D
derive=sum by position, currency `$91,130` parse, `--` multi-dash empty, best-of-N
skips a truncated/looping sample (not a run abort), append-lever DISPROVEN
(keep off), resumable sweep + sbatch --requeue (preemption-proof). Suite 13/13.

## Verify re-run of the 2026-07-27 solve-now fixes (evening, batch `_verify_fixes`)
Re-ran the 5 affected cells after the wage-ratio (88a12da) and duplicate-label
(0a3e963) guards. Adjudicated from the run artifacts, not the summary.
- **mil Retirement -> 1.0 clean.** Duplicate-label guard VALIDATED (was the x12 garbage).
- **chi_gen Age_Serv_Wage 0.00 -> 0.9831.** Wage-ratio guard VALIDATED.
- The other 3 chi wage cells now all declare the CORRECT `derive=ratio(salary_totals,
  counts)` (guard worked) but still score 0.0, for THREE distinct downstream reasons:
  - **chi_pol** — the salary (numerator) table was transcribed margins-only: ONLY the
    'Total' column filled, all 90 interior age x service cells null -> every average
    = total/None -> empty grid. FIXED offline: ratio-completeness guard (41f34e0),
    fires on all-null mapped cells; verified fires on chi_pol, silent on the others.
  - **chi_ff** — every numeric average is EXACTLY x12 too small. Confirmed against the
    PDF: Exhibit B.1 prints MONTHLY salary (age 20-24/1-4 yrs: 20 members, $119,627
    total = $5,981/member/mo; doc's own aggregate avg is $98,722 ANNUAL). Model
    transcribed monthly correctly but never annualized. NOT yet fixed: `annualize_monthly`
    currently CANCELS inside a ratio (ops.py 334-336 runs _grid on num and den with the
    same col_map; the x12 at ops.py:606 hits both and washes out on divide). Fix needs
    (a) ops.py+schema: annualize applied to the ratio RESULT (derive-level flag), (b) a
    wage FLOOR guard in validate() on implied avg = sum(num)/sum(den) < ~15k to trigger
    it (floor is false-positive-safe: a real annual avg is never < 15k), (c) prompt
    guidance. Also 18 zero-count (0/0) cells emit None vs truth 0.0 - a convention gap.
  - **chi_edu** — values present but misaligned; error ratio is NON-constant (3.5x, 4x)
    so NOT a scale bug -> age/service BAND-convention mismatch (col '4' blends
    'Under 1'+'1-4', fills 11 cells truth leaves empty). Needs source-PDF adjudication
    (RA), not a mechanical guard.
