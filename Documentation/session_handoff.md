# Session Handoff Notes (from the 2026-06 sessions)

Written 2026-06-11 by the outgoing assistant session for the incoming one.
This is the tacit-knowledge layer that the technical docs don't carry. Read it
after `project_context.md` and the recent `working_context.md` sections.

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
