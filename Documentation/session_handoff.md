# Session Handoff Notes

Written 2026-06-11, updated 2026-07-10. This is the tacit-knowledge layer the
technical docs don't carry. Read it after `project_context.md` and the recent
`working_context.md` sections.

## ACTIVE WORKSTREAM (2026-07): the extraction pipeline

The current focus is the AV-PDF -> workbook extraction pipeline in
`Data Extraction/pipeline/`. **Read `Data Extraction/data_extraction_context.md`
FIRST for this workstream** - it is the living methodology + dated dev log with
every attempt, failure, diagnosis, and fix (v0 keyword-locator mistake; v0.1
two-stage transcribe+declare/execute contract; Parley output_config drop +
format guard; the ground-truth errors found; the chi_pol column-shift failure
and the layout-preserved-text fix that solved it). Run evidence with full API
records is in `Data Extraction/runs/` (committed - small JSONs).

State as of 2026-07-10: rung-1 scoreboard 4/4 effectively perfect across three
actuarial firms (phx GRS, sd Cheiron, chi_pol Segal); 2 human ground-truth
errors found (phx wage typo; sd dropped '70 and up' row); 0 unresolved model
errors. Next: complete the rung-1 matrix (Age_Serv_Wage on chi_pol/sd), then
Ret_Rate (rung 2: needs transpose + proportional re-grid ops added to
ops.py's vocabulary).

Environment specifics for this workstream:
- API goes through MIT Parley: `$env:ANTHROPIC_BASE_URL =
  "https://parley.api.mit.edu"` + `$env:ANTHROPIC_API_KEY = "sk-parley-v1-..."`
  (PowerShell `$env:`, NOT bash `export`). Parley SILENTLY drops newer API
  params (verified: output_config) - the pipeline validates client-side and
  self-corrects; assume any new param may be dropped and verify.
- Key rules learned: adjudicate every workbook mismatch against the PDF before
  calling it a model error (label noise is real); the model does ZERO
  arithmetic (ops.py executes declared maps); document text must be
  layout-preserved (pdfplumber layout=True; pypdf plain as per-page fallback).
- Deps beyond the June list: anthropic, pdfplumber (pypdf already there).
- External thread: Pietro Ramella (U. Miami) advises on the ML approach;
  materials sent = the pin-annotated phx AV + marked workbook + the
  3-rung difficulty ladder (`Documentation/ml_extraction_handoff.md`).

## The thesis (never lose this)

Lenney–Lutz–Sheiner (Brookings) is **the foil, not the companion**: their
mean/deterministic framing of pension sustainability is what this project
argues is wrong. Everything must be framed in stochastic outcome distributions
(exhaustion probabilities, tails, fans). When reproducing their figures, the
point is redoing them "the correct way." Never let new analysis collapse to a
mean or median without the distribution alongside. **Re-save this as a memory
in your new memory directory** (the old one was keyed to the dissolved
`State Pension Model/` path): type `project`, slug `lenney-paper-is-the-foil`.

## How Niccolo works (calibrate to this)

- Wants a plan/manifest to approve before big changes, then full autonomous
  execution — don't ask permission mid-stream.
- Pushes back when you overclaim. Two corrections worth remembering: "extraction
  is done for ~16 cities" (it was 70–90% with real gaps — verify fill, not file
  existence) and over-running simulations to re-validate path changes ("you are
  overfixating"). Validate proportionally: one decisive check (bit-identity)
  beats five redundant ones. But when *he* asks for re-checks, do them all.
- Hates: stale/duplicated clutter, 37-row table dumps in notebooks (use
  figures; keep frames as variables), speculative language in
  `project_context.md` (observed facts only there).
- Sacred: plan data folders move/copy **fully intact**; never dismantle data;
  never delete during reorganizations — move to `_ARCHIVE/`.
- Documentation discipline is a hard habit of this project: update
  `working_context.md` (chronological handoff log) as you work, durable facts
  to `project_context.md`, and keep them non-overlapping.

## Validation norms (established and expected)

- **Bit-identity is the gold standard** for refactors/relocations of the
  engine: rerun fast detal OK134 (~27s) with a scratch run tag and compare all
  37 arrays to `Results/Runs/062026/OK134/OK134_detAL_062026.pkl`; max diff
  must be 0.0. Scratch tags go to `_ARCHIVE/snapshots/` afterward (Remove-Item
  is sandbox-blocked; always Move instead of delete).
- Market seed **123** = the canonical common-shock seed; all scenarios reuse it
  so runs are path-by-path comparable. Never give plans different seeds (that
  was deliberately removed).
- `062026` = the canonical run (Python fast outputs only, 37 plans, MA50
  excluded, num_sim=10000).

## Performance expectations (so you don't misdiagnose)

- Fast detal: OK134 ~27s, AZ06 (3 tiers) ~1m15s isolated; full 37-plan batch
  ~8 min at `--parallel 19 --workers 1` (PVNC threads are GIL-bound — never
  raise workers).
- Asset stage: ~2–4s/plan at 10,000 sims (vectorized); full sweep ~2.5 min.
- Notebook full execution (nbconvert): ~2–3 min, zero errors expected.

## Environment quirks

- **OneDrive**: locks folders mid-operation (the empty `Github/` husk at root
  is a leftover of this — delete when unlocked); moving is cheap, copying GBs
  is not.
- **Sandbox**: `Remove-Item` on project paths gets blocked — use moves.
- **PowerShell**: cp1252 console chokes on Unicode (→) in python prints; write
  scripts to `$env:TEMP` with `Set-Content -Encoding utf8` and avoid fancy
  chars.
- **Installed/available**: py-spy, nbconvert+ipykernel, pyreadr, pypdf,
  openpyxl, pyarrow; R 4.4.1 at `C:\Program Files\R\R-4.4.1\bin\Rscript.exe`
  (not on PATH); `FRED_API_KEY` is set in the environment (FRED sections run
  for real).
- **Airtable**: CSV export captures only the CURRENT VIEW — "Default" views
  are filtered; export from "All" views. A partial export sits in
  `Data/Sources/airtable_export/` (only Boston's table docs); a full re-export
  is still pending.
- `Code/python/analysis/results.ipynb.bak` is the pre-rebuild notebook copy;
  `results_executed_smoke.ipynb` is a rendered preview — both deletable when
  Niccolo says so.

## State of the two open work streams (details in working_context)

1. **Scenario plan (parked, fully specified, levers built and validated):**
   step 0 = add `--compact` output mode to `asset_simulation.py` (full scenario
   payloads are ~0.5–1 GB each; the 24-run grid needs it), then contribution
   grid → generic inversion framework ("reform of X → risk level Y") in a new
   `analysis/scenario_analysis.ipynb` → equity grid (same framework,
   sub-analysis, NOT a copied section) → AAA revaluation (stage="both") →
   no-reform counterfactual (needs plan-by-plan reform curation first, not the
   "post-2007" cutoff). Open user decisions: risk targets, grid spec, compact
   confirmation. Tier handling of contribution add-ons is already resolved —
   see "Scenario design decisions" in working_context.
2. **City track:** next concrete step is the Houston bridge validation — wire
   `Data/Plans/Cities/_migration/hou19_migration.xlsx` +
   `planchanges_hougen-ag.xlsx` + Houston's PPD row through the Python
   pipeline and compare Model AAL vs reported AAL. Remember the fill-status
   caveats (bos/dc are placeholders; retiree distributions missing for
   hou/lax/dal/dc/bos → default-assumptions fallback).

## Known stale (don't trip on these)

- `Code/python/engaging/` Slurm scripts assume the pre-reorg tree — rework
  before any Engaging run (local is so fast it hasn't mattered).
- The original `Main_PensionModel.py` (non-fast) and `g.py` are kept as the
  verified reference lineage; production is `fast/`.
- R track has no current outputs (user deleted R RData results after Python
  was verified equivalent); rerunning R requires nothing special — paths were
  updated and resolution-checked, but no full R run has been executed
  post-reorg.
