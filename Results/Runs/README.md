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
| `20260730_1` | 2026-07-30 | 40 | `ppd-data-latest_072026.xlsx` | First run with all 40 plans. Adds MA50/MA51/MO64, the three input guards, and the July PPD (24 restated fiscal-2022 values). Still the inherited `LinearFill`. |

## Two things to know before comparing runs

**Every run above uses the defective `LinearFill`.** The within-band weight
inherited from the R implementation produced negative retiree headcounts for 3 of
40 plans, catastrophically for OK134. Corrected 2026-07-30 — see
`Documentation/states_track_context.md`. **OK134's numbers in every run above are
unusable**, and LA163 and SC99 are mildly affected. The first run carrying the fix
will be the next one produced.

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
