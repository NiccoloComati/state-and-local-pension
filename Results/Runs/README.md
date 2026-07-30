# Results/Runs — what each run is

**Naming: `YYYYMMDD_N`.** The date the run was produced, plus a sequence number
for that day. Folder names *identify* a run; they deliberately do not *describe*
it, because a descriptive label ("linearfill", "newppd") stops meaning anything a
few weeks later. What a run is belongs in this table.

Scenario runs are named the same way — they are runs, produced on a date. Which
baseline they reuse and which lever they move is metadata, and metadata goes in the
table, not the folder name.

| Run | Date | Plans | PPD file | Engine notes |
|---|---|---|---|---|
| `20260610_1` | 2026-06-10 | 37 | fy2023 copy (then named `ppd-data-latest.xlsx`) | Long-standing canonical run. MA50/MA51/MO64 absent. Inherited `LinearFill` — see below. |
| `20260610_2` | 2026-06-10 | 2 (AZ06, NJ73) | as above | **Scenario run.** Demo for the launcher notebook: employer contribution +2pp of payroll, applied even when overfunded, from year 0. Reuses `20260610_1`'s liabilities, so it is asset-stage only and has no detAL files. |
| `20260730_2` | 2026-07-30 | 40 | `ppd-data-latest_072026.xlsx` | **First run with the corrected `LinearFill`.** Otherwise identical to `20260730_1` — same plans, same PPD, same seed — so the difference between the two isolates that correction exactly. |
| `20260730_1` | 2026-07-30 | 40 | `ppd-data-latest_072026.xlsx` | First run with all 40 plans. Adds MA50/MA51/MO64, the three input guards, and the July PPD (24 restated fiscal-2022 values). Still the inherited `LinearFill`. |

## Two things to know before comparing runs

**Every run above EXCEPT `20260730_2` uses the defective `LinearFill`.** The within-band weight
inherited from the R implementation produced negative retiree headcounts for 3 of
40 plans, catastrophically for OK134. Corrected 2026-07-30 — see
`Documentation/states_track_context.md`. **OK134's numbers are unusable in every run except `20260730_2`**, and LA163 and
SC99 are mildly affected in those runs.

Measured effect of the correction, `20260730_1` -> `20260730_2` (identical apart
from it): one plan moved more than 1% (OK134, +5.9%), 33 moved more than 0.1%,
median move 0.22%. Exhaustion probabilities moved by at most 0.015. Surgical, as
the pre-implementation testing predicted.

OK134 across the three runs, which shows why this mattered:

| Run | Liability | vs reported | P(exhaust by 2056) |
|---|---|---|---|
| `20260610_1` | $6.87bn | **+134.5%** | **0.858** |
| `20260730_1` | $3.04bn | +3.7% | 0.382 |
| `20260730_2` | $3.22bn | **+9.8%** | **0.397** |

Most of that shift came from the July PPD, and the rest from the correction. Its
+3.7% in `20260730_1` was the broken formula landing at a flattering point, not a
fix. Note that in the long-standing canonical run it was the fourth-riskiest plan
of 37; it is not.

**The `run_tag` stored inside each pickle still shows the original tag** (`062026`,
`072026`, `scn_demo_c2s0`). The folders and filenames were renamed to this
convention on 2026-07-30; the in-payload field was left alone because nothing reads
it and rewriting ~2 GB of pickles to change a metadata string was not worth the
risk. If you ever need it to agree, it is a scripted pass, not a manual one.

## Conventions the runs rely on

- **Market seed 123** for every plan in a run, so simulation column *n* is the same
  market history across plans. This is what makes cross-plan aggregate
  distributions meaningful. Never give plans different seeds.
- `num_sim = 10000`, `plan_year = 2022`, 35-year horizon.
- The runner refuses to write into an existing non-empty run folder unless
  `--overwrite` or a `--skip-existing-*` flag is passed, and mints the next free
  `YYYYMMDD_N` if `--run-tag` is omitted.
