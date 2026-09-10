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
| ~~`20260730_1`~~ | 2026-07-30 | 40 | `ppd-data-latest_072026.xlsx` | **DELETED 2026-08-04.** First run with all 40 plans. Added MA50/MA51/MO64, the three input guards, and the July PPD. Carried the inherited defective `LinearFill`. |
| ~~`20260730_2`~~ | 2026-07-30 | 40 | `_072026` | **DELETED 2026-08-04.** First run with the corrected `LinearFill`; the `_1`/`_2` pair isolated that correction. |
| ~~`20260730_3`~~ | 2026-07-30 | 40 | `_072026` | **DELETED 2026-08-04.** Added MI53's corrected 2022 salary and MA51's employer rate set to zero. |
| ~~`20260730_4`~~ | 2026-07-30 | 40 | `_072026` | **DELETED 2026-08-04.** The rejected denominator experiment. Its conclusion and evidence survive in `_ARCHIVE/superseded_2026-07-30/contribution_rate_denominator_test/OUTCOME.md`, which is what mattered. |
| `20260731_1` | 2026-07-31 | 40 | `_072026` | Adds FL26's contribution-rate exception. Superseded by `20260804_1`. Last run on the old 35-row horizon. |
| `20260804_1` | 2026-08-04 | 40 | `_072026` | First run covering **2022–2057** on both sides, and the first pricing normal cost by entry age. **Kept as the reference run**: it is the last run made before the early-retirement reduction, and `--no-early-retirement-reduction` reproduces it bit-identically, which is the regression check that the engine still behaves. |
| **`20260908_1`** | 2026-09-08 | 40 | `_072026` | **THE CURRENT BASELINE.** First run with the early-retirement reduction on, which is now the baseline specification. Also the first to save population counts and the outflow split (`active_members`, `inactive_members`, `beneficiaries`, `benefit_payments`, `refunds`, `death_benefits`, `disability_payments`). Analyse this one. |
| `20260910_1` | 2026-09-10 | 40 | `_072026` | **Counterfactual.** No post-2007 reforms: every tier starting after 2007-01-01 takes the benefit rules of the newest pre-2007 tier, via `--tier-file planchanges_noreform2007_2022_clean.xlsx`. Start dates untouched, so the same members sit in the same tiers. Feeds Lenney figures 11 and 12. |
| `20260910_2` | 2026-09-10 | 40 | `_072026` | **Counterfactual.** COLA set to zero for every tier (`planchanges_cola0_2022_clean.xlsx`). Feeds Lenney figure 4. |
| `20260910_3` | 2026-09-10 | 40 | `_072026` | **Counterfactual.** COLA set to each plan's own inflation assumption (`planchanges_colainflation_2022_clean.xlsx`). Feeds Lenney figure 4. |

## Scenario runs: the contribution grids

Scenario runs carry a prefix and reuse a baseline's liabilities through
`--detal-run-tag`, so they contain asset-stage output only. Two grids exist, identical
in shape, differing only in which baseline they sit on.

| Prefix | Baseline | Purpose |
|---|---|---|
| `scn_c<delta>s<start>` | `20260908_1` | The baseline grid. Lenney table 2, figures 9 and 10 |
| `scn_nr_c<delta>s<start>` | `20260910_1` | The same grid on no-reform liabilities, so the two can be differenced. Lenney figures 11 and 12 |

Each grid is **4 increases x 4 start years = 16 runs**: `+2.5, 5, 10, 17.5` percentage
points of payroll, beginning in year `0, 5, 10, 20`. All share market seed **123** and
pay the add-on even when a plan is overfunded.

**Why the grid stops at +20pp.** Extrapolating the curves, holding a plan's 20-year
exhaustion probability below 1% would need roughly +127pp of payroll for IL34 and +45pp
for LA163. Those are not policies. Plans that do not reach a target inside the grid are
reported as not reachable, which is the result rather than a gap. Five plans are in that
position at the 1% target: IL34, IN37, LA163, MA51, NJ73.

**An earlier, wider grid was discarded.** A 7 x 5 grid (deltas to 17.5, starts to 20) ran
on 2026-09-08 and filled the disk, because each scenario was then 2.2 GB. It was deleted
and replaced by the 4 x 4 grid above once compaction landed.

## Output size: compaction, 2026-09-08

`AAL`, `cash_inflows`, `cash_outflows` and `NormalCost` are deterministic: every one of
the 10,000 simulation columns holds the same value. Until 2026-09-08 they were stored at
full width anyway, in both the pickle and the parquet bundle, which made a scenario run
2.2 GB when about 350 MB was real content, and filled the disk mid-grid. They are now
collapsed to a single column before saving, checked rather than assumed, so anything that
does vary by simulation stays full width. `Assets` is never collapsed.

Effect: a scenario run went from 2.2 GB to about 435 MB and from 25 seconds to 8. Runs
made before that date keep the old shape and still load; `PlanResult.funding_ratio()`
divides through numpy so both widths work.

## Deleted 2026-08-04

Nine run folders totalling 19.4 GB were deleted: the five superseded scenario runs
above, and `20260730_1` through `20260730_4`. All were superseded, and in each case
what they established is recorded either in this file or in the archived write-up
named in the table. `20260731_1` was **kept** as the last run on the old 35-row
horizon, in case anything needs comparing across the break described below.

## A break in comparability: 2026-08-04

**Every run in the table above was produced with a 35-row projection whose
liability side filled only 34 of those rows.** Two engine changes on 2026-08-04
end that, so runs produced from then on are not directly comparable to these:

- **The horizon is now the base year plus 35 projected years, 2022-2057**, on both
  sides. `Nyear` went 35 -> 36 and the liability loop, which evaluated row `t-1`
  and then advanced, was restructured so it fills every row instead of leaving the
  last one at zero. Previously liabilities ran to 2055 and assets to 2056.
- **The normal-cost rate is applied by entry age**, current age minus service,
  rather than by current age.

**Measured across all 40 plans** (`20260731_1` -> `20260804_1`, rows 0-33 where the
horizon change cannot reach, so this isolates the normal-cost change):

| | |
|---|---|
| Year-0 accrued liability | median **+2.47%**; **36 plans rose, 4 fell**; range -1.9% (LA130) to +11.0% (MA51) |
| Year-0 normal cost | median **-14.4%**, range -35.5% to +96.4% |
| Cash inflows and outflows | **bit-identical for all 40 plans**, as they must be |

The single-plan test on OK134 was **not representative** — it showed liability
-1.7% and normal cost +51%, both against the majority direction. The sign of the
change depends on how a plan's age-and-service mix sits against the rate schedule,
so it varies plan by plan.

Years 2022-2055 remain comparable in kind across the break; the two appended years
are new. `Analysis/results.ipynb` detects which convention a run uses from its data
and handles both, so older runs still analyse correctly.

## Two things to know before comparing runs

**`20260610_1`, `20260610_2` and `20260730_1` use the defective `LinearFill`.** `20260730_2`, `_3` and `_4` carry the correction. The within-band weight
inherited from the R implementation produced negative retiree headcounts for 3 of
40 plans, catastrophically for OK134. Corrected 2026-07-30 — see
`Documentation/states_track_context.md`. **OK134's numbers are unusable in the three runs that predate the correction**, and
LA163 and SC99 are mildly affected there.

**`20260731_1` reflects the current code, and the `20260730_3` -> `20260731_1` pair
isolates FL26's contribution-rate exception exactly.** Verified across every parquet
array of all 40 plans: **39 plans bit-identical, maximum absolute difference exactly
0.0**, no shape, NaN-pattern or missing-file differences anywhere, and FL26 alone
changed. FL26's exhaustion probability moves **0.3801 -> 0.2399**, reproducing the
figure measured in the archived denominator experiment; its year-0 liability moves
**-0.057%** ($208.874bn -> $208.755bn), which is the employee contribution rate
feeding `refund()` and sits inside the documented range for that channel (median
0.004%, maximum 0.09%). The 13 `RuntimeWarning` lines in the logs are the same 13
plans at the same line as in `20260730_3` — pre-existing, not introduced.

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
