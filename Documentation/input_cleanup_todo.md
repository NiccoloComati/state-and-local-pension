# Input Cleanup To-Do — state track

**Created:** 2026-07-29. **Scope:** making the model's *inputs* clean, complete and
defensible across all 40 state plans. Not paper or analysis work.

**Status of every item here is OPEN.** Nothing below has been executed.

---

## How "missing data" is already handled (the design, so nothing here reads as alarm)

The engine never lacks an input. Three fallback layers exist by design:

1. **Distribution sheets.** Each plan carries a 9-boolean `availableData` vector
   (the `AVAILABLE_DATA` dict in `Code/python/fast/Main_PensionModel.py`). Where a
   flag is `False`, the same-named sheet of `Data/Common/states/default_assumptions.xlsx`
   is read instead — the shared actuarial tables.
2. **PPD scalars.** Chains in `functions_cf_model.py`: wage growth tries
   `PayrollGrowthAssumption` → `WageInflation` → legacy 2017 `wage_inf` →
   `InflationAssumption_GASB` → legacy `inflation`; inflation tries
   `InflationAssumption_GASB` → legacy `inflation`; the inactive count tries
   `InactiveVestedMembers` → legacy `inactive`.
3. **Constants.** Disability payout 2.5% of payroll, population growth 1%,
   `rf = 0.01 + Inflation`.

So the questions below are never "is there a number?" — there always is. They are
**is the fallback the right choice here, and does the flag match what is actually
in the workbook?** Several times below the answer is that plan-specific data
exists and is being passed over, or that a flag claims plan-specific data that
isn't there.

---

## Group A — Blockers with a concrete fix now in hand (gets coverage to 40/40)

### A1. MA51's employer contribution rate — solvable, source identified
`contrib_ER_regular` is empty for MA51 in **every year since 1999**, which makes
`EmployerContributionRate` NaN and is the plan's only real blocker. But the new
PPD file carries the same quantity under other names at fy2022:
`contrib_ER_tot = contrib_ER_state = 2,104,604` (with `contrib_ER_other = 179,369`).
**Do:** extend the employer-rate fallback to `contrib_ER_regular → contrib_ER_tot`,
check the same for `contrib_EE_regular`, and verify the resulting rate against
MA51's AV before adopting. Decide whether the fallback is MA51-only or general.
*(MA51's other suspected gap is a non-issue: `inactive_adj = 0.0` zeroes the
inactive population before `InactiveVestedMembers` is ever consulted.)*

### A2. Admit MO64 — one line
Verified workbook-equivalent to OK134 on every engine-read range, own declared
vector identical, PPD complete at fy2017/2022/2023/2024.
**Do:** add `'MO64': [T,T,T,T,T,T,T,F,F]` to `AVAILABLE_DATA`. No other change.

### A3. Admit MA50 — pick its availability vector
Its two R scripts disagree: 2017 says `TTTTTTTFF`, 2022 says `TTTTTFFFF`
(withdrawal and retirement → defaults). The 2022 reading matches the workbook,
whose withdrawal block uses non-standard age bins (20, 30, 40, 45, 50, …) and is
one row short.
**Do:** adopt the 2022 vector unless inspection of the AV says otherwise. Depends
on A4. The old indictment of MA50 was mostly wrong — see `project_context.md` §6.2.

### A4. The `wagerel` short block (MA50, MA51) — needs an explicit rule
Both have 10 age rows (25–70) where the generic `B2:L12` read expects 11 (25–75).
**R pads the missing row with `NA`; pandas returns a (10, 11) array and
`ConstantFill` silently leaves the top age bin at zero.** That silent divergence
is the real defect — not the missing row.
**Do:** choose and implement one rule (carry the age-70 row forward, take the
`default_assumptions` wagerel row, or explicit zeros), make the reader assert the
expected shape instead of truncating, and record the choice as a named assumption.
Also note MA50's `wagerel` is degenerate in a second way — identical value across
every service column, i.e. age-only relativities with no service dimension (the
same shape of problem as the `aus` wage broadcast on the city track).

---

## Group B — Flags that disagree with the workbooks (largest quality item)

Source: `Documentation/provenance/state_sheet_fill_audit.csv`, 40 plans × 9 sheets.
Of 360 sheet-instances: 282 hold plan-specific content, 74 hold the shared
default, 4 are absent. Flags exist for 37 plans (MA50/MA51/MO64 have none yet).

### B1. 36 sheet-instances hold plan-specific data that the engine ignores
Flag is `False`, so `default_assumptions.xlsx` is used even though the plan's own
numbers are sitting in the workbook:

| Sheet | Plans | Count |
|---|---|---|
| `retirement` | AZ06, AZ127, CA111, CA43, CA97, CA98, DC20, FL26, GA27, GA28, LA44, ME47, NJ71, NJ73, NM74, NY83, OH88, SC100, SC99 | **19** |
| `mortality` | AZ127, DC20, FL26, GA27, IL33, NJ71, NJ73, NM74, NY83 | **9** |
| `withdrawal` | GA27, IL32, OH88 | 3 |
| `refund` | FL26, IL34 | 2 |
| `disability` | CA10, FL26, IL34 | 3 (ghost sheet — see B3) |

**Do not bulk-flip these.** A `False` flag is often correct precisely because the
layout is non-standard and the generic reader would mis-map it — MA50's withdrawal
is the proven example. **Do:** per sheet-instance, check the block against the
engine's read range and against the plan's AV, then either flip the flag, fix the
read, or record why the default is the right call. Retirement (19 plans) is the
biggest single block and the most consequential — retirement rates drive both
benefit timing and the active-population run-off.

### B2. Three plans claim plan-specific mortality but hold the shared default
IN37, ME47, OR91: flag `True`, sheet content identical to the default table
(601 numeric cells, the shared signature). Numerically harmless — the same numbers
are used either way — but the flag misrepresents provenance, and **ME47 and IN37
are both in the >10% AAL-gap set** (Group E).
**Do:** set the flag to `False` or supply real plan mortality from the AV.

### B3. Two sheets are never read at all, regardless of flag
- `wagegrowth`: **37 plans hold plan-specific data that is never consumed.** Wage
  growth comes from the PPD scalar chain instead.
- `disability`: 3 plans hold real data; the engine uses the flat 2.5%-of-payroll
  constant for everyone.
**Do:** either wire these sheets in, or record explicitly — in the assumption
register and in run output — that we prefer the PPD chain and the 2.5% constant by
choice. Right now the workbook data is silently orphaned.

---

## Group C — The PPD refresh (new file landed 2026-07-28)

`Data/Common/states/ppd-data-latest.csv` (9.4 MB, 253 plans/year, **fy through
2024**) supersedes the May `.xlsx` (228 plans/year, fy through 2023).

### C1. FY2023 and FY2024 are now viable target years — this reverses the earlier read
The earlier "FY2023 is not a drop-in replacement" finding was a property of the
**old** file. In the new file all 40 plans have rows at fy2022, 2023 and 2024, and
the engine-read fields are complete except:
`contrib_ER_regular` (MA51, all years — see A1), `InactiveVestedMembers`
(MA51, NY78 — falls back to legacy 2017 by design), `InflationAssumption_GASB`
(NJ71, fy2022 only), `EQTotal_Actl` (MO175 fy2023–24; NM74 fy2024).
`PayrollGrowthAssumption` is absent for 13–15 plans in every year — expected, the
chain covers it. **fy2025 does not exist yet.**

### C2. Swapping the file is not free even at the same year — decide this first
24 fy2022 cells that the canonical run consumes are **restated** between the old
and new files, concentrated in the retiree block: `beneficiaries_tot` (12 plans),
`BeneficiaryBenefit_avg` (8), plus one each of `ActLiabilities_GASB` and
`actives_tot` and two `payroll`. Largest: ME47 retiree count −16.4% with average
benefit +19.6%; MO175 −14.5% / +17.0%; CA144 −8.0%; FL26 −6.8%.
**Do:** rebase the canonical run on the new file **at fy2022 first**, so the
restatement effect is isolated and measurable, before changing the year. Otherwise
a year change and a data revision are confounded.

### C3. Mechanics of any year change
Add `[PLAN]_<year>`-keyed rows to `PPD_planlevel_main_updated.csv` and to the tier
workbook — both are looked up by `[PLAN]_<plan_year>` and currently only have
`_2022` keys. Then `--plan-year <year>`; the runner is already parameterized.

### C4. The engine reads `.xlsx`; the new file is `.csv`
`pd.read_excel(..., sheet_name='ppd-data-latest')` is hard-coded. Either convert
the CSV to the expected workbook or teach the loader both. The CSV also needs
`encoding='latin-1'` — it is not UTF-8.

---

## Group D — Clarifications (no obvious defect, but the record is unclear)

- **D1.** `PPD_planlevel_main_updated.csv` supplies `pctmale`, `pctmrg`, `reduct`,
  `inactive_adj` on a `_2022` key, but its values are identical to the FY2017 file
  for all 37 plans — a re-key, not a re-collection. Decide whether to re-derive
  these (PPD carries member counts by sex) or to state plainly that they are 2017.
- **D2.** The tier workbook's latest `startdate` is **2018-07-01**, so benefit
  rules miss anything enacted since. CA97 also has `er4`/`er5`/`er6` empty (early
  retirement age). The PPD API now exposes tier-structured benefit parameters
  (`pensiontierbasics`, `pensionnormalretirementbenefit`, `pensioncolabenefit`, …),
  a candidate to audit or replace the hand curation. See `Data Extraction/ppd_source_survey.md` §4b.
- **D3.** `inactive_adj` semantics: `1.0` means "scale by the inactive count";
  anything else multiplies the active count. MA51's value is `0.0`, which zeroes
  the inactive population entirely. Confirm that is a deliberate statement about
  MA51 and not a missing value encoded as zero.
- **D4.** NY78 has no `InactiveVestedMembers` in any recent year, so its inactive
  count comes from the legacy 2017 `inactive`. Working as designed; should be a
  recorded assumption rather than an invisible fallback.
- **D5.** NJ71 lacks `InflationAssumption_GASB` at fy2022 and falls back to the
  2017 legacy inflation of 0.035, well above the 0.02–0.03 typical of the others.
  It is present at fy2023–24, so a year change resolves this one.
- **D6.** MO175 (fy2023–24) and NM74 (fy2024) lack `EQTotal_Actl`, so the 2-asset
  risky share would be incomplete if the year moves. Needs a rule before C3.

---

## Group E — The model-vs-reported AAL gaps (sequence last, and here is why)

13 of 37 plans differ from the PPD-reported AAL by more than 10%: OK134 +134.5%,
MI53 −30.7%, ME47 +30.1%, IN37 +28.3%, ND82 +19.6%, DC20 +19.3%, GA28 +17.6%,
NY78 +13.9%, and five more between 10% and 14%.

This is an input question as much as a modeling one, but it must come **after**
Groups A–C, because every one of those changes moves these numbers: flipping a
retirement or mortality flag (B1/B2) changes the liability directly; rebasing on
the new PPD (C2) changes both the modeled AAL and the reported target. Diagnosing
the gaps on inputs we are about to change would be wasted work.

Note the overlap already visible: ME47 and IN37 appear in B2 (mortality flagged
plan-specific but holding the default), and ME47 has the largest C2 restatement.

---

## Suggested order

**A → B → C → E**, with **D** running alongside.

A is small, self-contained and takes plan coverage from 37 to 40, which every
later step benefits from. B is the largest input-quality item and is independent
of the vintage question. C changes the numbers globally, so it should land after
the inputs are settled but before the gaps are diagnosed. E is the payoff and
needs stable inputs underneath it.

The one exception worth considering: **C2 (rebase at fy2022 on the new file)**
could be pulled forward, because it is a pure file swap at a fixed year and it
tells us how sensitive the results are to a PPD revision — useful context for
judging everything else.
