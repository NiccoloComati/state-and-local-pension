# RA task spec — verifying extraction against the PDFs

**Scope: verification only.** Check cells the pipeline appears to have extracted
correctly, against the source document, and report what you find. Assumption and
convention questions are NOT in scope — they sit with Niccolo (and his coauthor).
If a cell turns out to need one, stop and record it; do not decide it.

Every plan, all 6 sheets. No plan or sheet has priority.

**The reference is the source PDF (AV / CAFR)** — NOT the 2022 workbook. The
workbook mostly doesn't exist per plan/sheet and is error-prone; use it only for
specific methodology points, and only as one more thing to reconcile against the
PDF. A cell with no workbook is still fully checkable: the PDF is the truth.

Start from `sweep_20260727/ra_worklist.csv`, rows with `owner = RA`. The other
owners are not yours: `Niccolo` = assumption/convention decisions, `code` =
pipeline bugs. Row assignments change as fixes land — work from the newest
worklist, and expect cells to re-open after a re-run rather than close on first
pass.

## What to read
Each row points at a run dir holding:
- `extraction.json` — the RAW tables as read off the PDF, the DECLARED
  transformation (sum / average / blend / ratio / split...), and the model's
  plain-English `notes`. **Read the notes first** — they state what the model
  thought it was doing.
- `derived.json` — the final grid that transformation produces.
- `report.json` — present only where a workbook exists.

## The check: two layers, annotate each separately
1. **Transcription** — does the raw table in `extraction.json` match the PDF,
   digit for digit? Record the page and exhibit you checked against.
2. **Transformation** — is the declared operation the RIGHT one for what the
   document prints? A cell can be wrong with perfect digits (summed where it
   should have averaged, a bin mapped to the wrong column, dollars divided by
   dollars instead of by a headcount), and it can look right while hiding a
   mis-read digit. The two fail independently, so record them independently.

Real failure modes seen so far, so you know what to look for: a whole table
transcribed one column late (every value correct, every one in the wrong
column); a printed `Total` line transcribed as if it were an age band; monthly
salary reported as annual; an exhibit printing a count line and a dollar line
per age band flattened into a single table; two exhibits printed side by side
on one page and read as one.

## Effort triage
Most cells have no workbook, so there is no score to key off. Check hardest
where the automated PDF-INDEPENDENT verifiers complain:
- `totals` = `suspect` (`!` in the batch view) — the table disagrees with the
  totals printed in the exhibit itself. Almost always a transcription slip.
- `ppd` = `off` (`~`) — headcount disagrees with the PPD/CAFR cross-check.

Cells where both reconcile get a light spot-check. Rate and blend sheets are
inherently harder and deserve more time even when quiet.

## When a cell is not simply right or wrong, record which of these it is
- **needs an assumption/convention** → record it and move on; it routes to
  Niccolo. Do not settle it.
- **image-only table** → our text-based model cannot read it at all, so it needs
  a different (vision) extraction model. Flag it explicitly — this is NOT the
  same as "not in the document", and we need the count of these.
- **genuinely not in the document** → record as such, no action.
- **extraction or transformation error** → routes to the code owner, with the
  PDF page and the correct value.

## Output — one row per cell, extending ra_worklist.csv
`plan, sheet, cell, extracted_value, PDF_value, PDF_page, verdict, layer
(transcription / transformation / assumption / image), reason`

Give the page and exhibit for every judgement, right or wrong — a "correct"
verdict with no page reference cannot be re-checked by anyone else.

## Working mode
Work a chunk independently → joint review with Niccolo → continue. It is a LOOP:
annotations → fixes / decisions / re-runs → re-verify.
