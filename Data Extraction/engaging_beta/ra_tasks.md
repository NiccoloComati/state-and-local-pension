# RA task spec — verifying the extraction against the PDFs

**Scope:** every plan, all 6 sheets, every cell. No plan or sheet has priority.
The reference is the **source PDF (AV / CAFR)** — NOT the 2022 workbook (which
mostly doesn't exist per plan/sheet and is error-prone; use it only for specific
methodology points, and only as one more thing to reconcile against the PDF).

Start from `engaging_beta/sweep_20260727/ra_worklist.csv` — one row per cell with
its owner (RA / assumption / me) and a note. Each cell points to a run dir whose
artifacts are the two things to read:
- `extraction.json` — the RAW tables as read off the PDF + the DECLARED
  transformation (sum/average/blend/split/ratio...) + the model's plain-English
  `notes` (read the notes FIRST — they state the model's intention).
- `derived.json` — the final grid that transformation produces.

## Stream A — extracted / attempted cells: compare to the PDF at two layers
1. **Transcription:** does the raw table in extraction.json match the PDF, digit
   for digit?
2. **Transformation:** is the declared operation the RIGHT one? (A cell can be
   wrong because a digit was mis-read OR because the op was mis-declared - e.g.
   summed when it should have averaged, mapped a bin to the wrong column - even
   if every raw number is perfect.)
Annotate correct/not at EACH layer.

**Effort triage (no workbook = no score for most cells, so don't key off score):**
check hard where the automated PDF-INDEPENDENT verifiers fire - the within-table
printed-totals reconciliation (a '!' flag) and the PPD/CAFR headcount cross-check
('~' or ppd=off) - and on the inherently harder sheets (rates/blends). Cells that
already reconcile get a light spot-check.

## Stream B — missing / wrong / empty cells: record WHY
- **assumption needed** -> identify which; decide it if EASY, FLAG it if not
  (routes to Niccolo + coauthor). The open ones are in `assumption_register.md`.
- **image-only table** -> our text-based model can't read it -> **needs a
  different (vision) extraction model**. Record explicitly (this is NOT the same
  as "not in the document").
- **data genuinely not in the document** -> record as such, no action.
- **real extraction/transformation error** -> a Stream-A finding; routes to the
  code owner.

## Output — structured, one row per cell (extend ra_worklist.csv)
`plan, sheet, cell, extracted_value, PDF_value, PDF_page, verdict, layer
(transcription/transformation/assumption/image), reason`.
This routes cleanly to: workbook-fix / register-decision / code-owner / vision /
recorded-as-absent.

## Easy assumption items the RA can settle (from the register)
- verify 2 known workbook defects vs the PDF: phx Age_Serv_Wage 86,306 -> 86,309;
  sd dropped '70 & up' row.
- engine check: does the simulation ever read a year-0 separation rate?
- Milwaukee: is monthly-benefit x12 correct given escalators / 13th checks?
- survey which plans have tier-split rate tables / age-only salary / rates
  printed beyond the template's age range (feeds the hard decisions).

## Hard items to FLAG (Niccolo + coauthor)
tier handling (per-tier rate tables vs one engine matrix); ages/service beyond
the printed table (carry forward vs empty vs shrink template); impossibility-cell
zeroing convention; beneficiaries in/out of mortality & retiree weights; age-only
wage evidence (broadcast vs empty vs other source); rate-blend weight conventions.

## Working mode
RA works a chunk independently -> joint review with Niccolo -> continue. It is a
LOOP: annotations -> fixes/decisions/re-runs -> re-verify (cells re-open after a
fix, not closed on first pass).
