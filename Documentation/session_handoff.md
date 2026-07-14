# Session Handoff Notes

Written 2026-06-11, updated 2026-07-13. This is the tacit-knowledge layer the
technical docs don't carry. Read it after `project_context.md` and the recent
`working_context.md` sections.

## ACTIVE WORKSTREAM (2026-07): the extraction pipeline

The current focus is the AV-PDF -> workbook extraction pipeline in
`Data Extraction/pipeline/`. **Read `Data Extraction/data_extraction_context.md`
FIRST for this workstream** (and `Data Extraction/assumption_register.md` - the
record of embedded modeling assumptions awaiting decisions) - it is the living methodology + dated dev log with
every attempt, failure, diagnosis, and fix (v0 keyword-locator mistake; v0.1
two-stage transcribe+declare/execute contract; Parley output_config drop +
format guard; the ground-truth errors found; the chi_pol column-shift failure
and the layout-preserved-text fix that solved it). Run evidence with full API
records is in `Data Extraction/runs/` (committed - small JSONs).

State as of 2026-07-10 (second session, commits 15cb813 + 0219dca, PUSHED):
- **Rung-1 matrix COMPLETE: 6/6** (phx/chi_pol/sd x Age_Serv_Num/Age_Serv_Wage,
  three firms), all effectively perfect after adjudication. The two wage runs
  exposed two PIPELINE VOCABULARY GAPS - both times the model transcribed
  correctly and flagged the gap itself in notes, and both were fixed +
  validated at zero API cost from the archived transcriptions:
  v0.2 = derive:ratio (chi publishes salary TOTALS+counts, no averages;
  avg = total$/count computed by ops.py) and column weighted_avg (sd merges
  average columns; count-weighted) + validate() arity enforcement.
- Ground-truth-error tally: sd's collector dropped '70 and up' on the WAGE
  sheet too (same error #2); running score 2 human errors vs 1 model error
  (fixed) vs 2 vocabulary gaps (fixed).
- **v0.3 = rung-2 machinery BUILT AND EXECUTOR-VERIFIED, live run pending**:
  transpose, overlap_weighted (model declares source bin SPANS, null=open
  end; target spans fixed in targets.json; code computes year-overlap
  weights - the verified 12-19 = 3/8x0+5/8x0.225 = 0.140625 bit-exact),
  values_unit=percent (code DIVIDES by 100). Ret_Rate target spec complete.
  test_ops_phx_retrate.py verifies on the hand-transcribed actual phx p.50
  B.5 table. DISCOVERY: two undocumented workbook-vs-PDF
  discrepancies in phx Ret_Rate truth (choice or error unknown) - the AV
  prints 100% retirement at age 70 but the workbook ignores it (carries
  66-69 rates); and the workbook treats '>31' as 31-and-over even though the printed
  bins are unambiguous ('25-31' includes 31, so '>31' = 32+) - the workbook
  contradicts the printed table. Full details in data_extraction_context.md dev log.
- GitHub housekeeping: repo renamed to lowercase
  `state-and-local-pension`; remote URL updated; README mojibake fixed.
  This machine (the second one) now has pdfplumber + anthropic installed.

Current 2026-07-13 delta (details in `data_extraction_context.md`):
- Ret_Rate phx/chi_pol adjudicated; tier-specific retirement-rate handling
  and ages-beyond-table are now OPEN decisions in `assumption_register.md`.
- Sep_Rate target built and live-run on phx/chi_pol/sd; machinery works, sd
  pins the missing rung-3 group-blend op.
- Production-mode cold plans added (`aus`, `mil`, `bos`). Milwaukee
  Age_Serv_Num exposed and fixed a pure executor vocabulary gap:
  `derive={"op":"sum","tables":[...]}` for same-shaped additive subgroup
  tables; archived run now re-executes 80/80 exact.
- Latest production review: `aus_Age_Serv_Num_20260713_164723` looks solid
  (Table 13A all-active total 10,149). `mil_Age_Serv_Wage_20260713_164600`
  and `aus_Age_Serv_Wage_20260713_164833` are NOT accepted as final wage
  grids: they only have age-level wage evidence, not age x service wages.
  The Austin wage grid copied each age average across service buckets; that
  is now an OPEN assumption/contract issue in `assumption_register.md`.

2026-07-14 delta: the `unavailable` contract landed (v0.5, offline, zero API
cost): Stage A can now declare a target not derivable (empty maps, all-null
grid, notes stating what the document publishes instead, evidence tables
archived), the prompt forbids approximating a missing dimension (the aus
wage broadcast can no longer happen), and the old mil-wage failure is a
regression test (`pipeline/test_unavailable.py`; suite 7/7). Assumption
decisions stay parked in `assumption_register.md` for the coauthor session -
the register is the agenda, nothing is blocked by deferral.

**NEXT ACTION (agreed order, one item at a time to spare the API budget):**
1. Build the rung-3 op: cross-table population-weighted blend (age-varying
   headcount weights). Spec pinned by sd Sep_Rate; same shape needed by
   Avg_Mort. Validate at zero API cost against the archived sd transcription.
2. Remaining cold runs when Niccolo runs them: bos counts/wage, then
   Ret_Rate/Sep_Rate on aus/mil (stresses rung-2 machinery out-of-sample).
3. New targets after the blend op: Avg_Mort, then Retirement (retdist).

```powershell
cd "Data Extraction"
python pipeline/run_test.py --plan bos --target Age_Serv_Num
python pipeline/run_test.py --plan bos --target Age_Serv_Wage
```

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
