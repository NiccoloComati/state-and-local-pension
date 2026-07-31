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
| `20260610_1` | 2026-06-10 | 37 | fy2023 copy (then named `ppd-data-latest.xlsx`) | Long-standing canonical run. MA50/MA51/MO64 absent. Inherited `LinearFill`. |
| `20260610_2` | 2026-06-10 | 2 (AZ06, NJ73) | as above | **Scenario run.** Launcher demo: employer contribution +2pp of payroll, applied even when overfunded, from year 0. Reuses `20260610_1`'s liabilities, so asset-stage only, no detAL files. |
| `20260730_1` | 2026-07-30 | 40 | `ppd-data-latest_072026.xlsx` | First run with all 40 plans. Adds MA50/MA51/MO64, the three input guards, and the July PPD (24 restated fiscal-2022 values). Still the inherited `LinearFill`. |
| `20260730_2` | 2026-07-30 | 40 | `_072026` | **First run with the corrected `LinearFill`.** Otherwise identical to `20260730_1`, so the pair isolates that correction exactly. |
| **`20260730_3`** | 2026-07-30 | 40 | `_072026` | **THE CURRENT RUN.** Adds MI53's corrected 2022 salary and MA51's employer rate set to zero. This is the one to analyse. |
| `20260730_4` | 2026-07-30 | 40 | `_072026` | **Rejected experiment**, kept for the record. Identical to `20260730_3` except contribution rates measured against the model's own payroll. Tested and not adopted — see `_ARCHIVE/superseded_2026-07-30/contribution_rate_denominator_test/OUTCOME.md`. |

## Two things to know before comparing runs

**`20260610_1`, `20260610_2` and `20260730_1` use the defective `LinearFill`.** `20260730_2`, `_3` and `_4` carry the correction. The within-band weight
inherited from the R implementation produced negative retiree headcounts for 3 of
40 plans, catastrophically for OK134. Corrected 2026-07-30 — see
`Documentation/states_track_context.md`. **OK134's numbers are unusable in the three runs that predate the correction**, and
LA163 and SC99 are mildly affected there.

**No run yet reflects the current code.** Since `20260730_3` the only behavioural
change is FL26's contribution-rate exception; everything else has been verified
bit-identical. So a fresh run would differ from `20260730_3` **for FL26 only**.

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
