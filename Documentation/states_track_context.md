# States Track — working context

**Created:** 2026-07-29. **Scope:** the 40 state plans and the working paper built
on them. Companion to `working_context.md` (the chronological log across all
tracks) and `project_context.md` (durable observed facts). Analysis and paper
framing are decided with Niccolo and are not recorded here in advance.

Written to be read without the code open: each item says what the input is and
what it drives before saying what is wrong with it.

## Decisions taken

- **2026-07-29 — Base year stays 2022.** Adopt the corrected 2022 figures from the
  newer PPD file (they are CRR revisions, so treated as improvements); comparing
  against the older file stays available later as a check, not a sensitivity.
- **2026-07-29 — Wage growth and disability sheets stay unused.** We keep taking
  wage growth from the PPD and disability at the flat 2.5% of payroll. The plan
  data stays in the workbooks and the switches can be turned on later; recorded
  here so the choice is explicit rather than accidental.
- **2026-07-29 — Admit MO64, MA51 and MA50** (37 plans -> 40). MO64 needs only a
  list entry; MA51 needs the employer-contribution fallback; MA50 takes its 2022
  switch settings. Every change is to be recorded so it can be reversed.
- **2026-07-29 — Match the original R behaviour** on the short salary sheet, unless
  R's behaviour is itself unusable. See §1d for how that resolved.

### DONE 2026-07-29 — the three plans are admitted; the switches are NOT being flipped

**Code changed** (`Code/python/fast/Main_PensionModel.py`), all three reversible:
1. `AVAILABLE_DATA` gained `MA50 [T,T,T,T,T,F,F,F,F]`, `MA51 [T,T,T,T,T,T,F,F,F]`,
   `MO64 [T,T,T,T,T,T,T,F,F]`, taken from each plan's own R script. Revert by
   deleting the three rows.
2. `_employer_contrib()` falls back to `contrib_ER_tot` / `contrib_ER_state` when
   `contrib_ER_regular` is empty, and prints a note when it fires. Revert by
   reading `contrib_ER_regular` alone.
3. `_pad_rows()` pads a short `wagerel` grid to 11 rows with zeros and prints a
   note. Same values pandas produced by silent truncation before, now explicit
   and loud, and it raises if a grid is ever too long.

**Verified:** OK134 rerun compared against the canonical pickle across 45
arrays and scalars — **max absolute difference 0.0, bit-identical**. Nothing moved
for existing plans.

**MA51's employer contribution is confirmed.** Massachusetts Teachers is funded by
a Commonwealth appropriation rather than a payroll-rate employer contribution,
which is exactly why `contrib_ER_regular` has been blank since 1999. The PPD's
FY2018 `contrib_ER_state` of $1.315bn matches the valuation report's stated FY18
appropriation of $1.303bn to 0.9%. Implied FY2022 rates (11.6% employee, 27.3%
employer) sit inside the range of the 37 modelled plans.

**First results for the three, against each plan's reported liability:**

| Plan | Model | Reported | Difference |
|---|---|---|---|
| MA50 | $49.3bn | $47.3bn | **+4.3%** — better than most of the existing 37 |
| MO64 | $68.7bn | $55.4bn | +24.0% — joins the group in §5 |
| MA51 | $12.2bn | $60.3bn | **-79.8% — not trustworthy, see below** |

MA50's good result is worth noting given its reputation: configured with its 2022
switch settings it behaves normally, which suggests the "suspicious results" that
got it dropped came from the older configuration rather than from the plan.

**MA51 is admitted but NOT closed.** A liability one fifth of the reported figure
is a structural failure, not a tolerance. The first thing to check is that its
inactive-member population is zeroed by construction (`inactive_adj = 0.0`, §4) in
a plan whose liability is dominated by long-service teachers. Do not use MA51 in
any results until this is understood.

Scratch outputs kept at `_ARCHIVE/snapshots/scratch_0729_three_plan_admission/`.

### LA44's `-100` values — resolved (2026-07-29)

They are "not eligible to retire" markers, and the engine already converts negatives
to zero before use. Not a defect.

### FLAG (2026-07-30) — the retirement-rate sheets have THREE separate problems

**STATUS: PARKED WITH REASON. No action pending.** The switches stay off, which is
the right call — those sheets were redirected to the shared default tables for a
reason, and 8 of 14 plans checked confirm it. Nothing here is a to-do. All three
problems below are recorded so they can be picked up deliberately later, and so
they appear in any writeup describing how retirement is modelled. The natural
moment to revisit is if the engine ever gains per-tier decrements — see
`Data Extraction/assumption_register.md` entry 1, which is the same issue on the
city track. The three problems are different in kind; none substitutes for another.

**Problem 1 — a model limitation. The engine holds one retirement grid per plan,
and the source documents do not publish one.** Checked 8 of the 14 plans against
their own 2017 valuation reports; all 8 show it:

| Plan | How its own valuation report splits retirement rates |
|---|---|
| ME47 (Maine) | 3 tiers. At age 60: Tier 1 25%, Tier 2 7.5%, Tier 3 4% |
| SC99 (SC Police) | an age-based and a service-based table, each x Class Two/Three x sex |
| CA43 (LA County) | 8 tables (A-6 to A-13), one per benefit plan (General A-E, Safety A-C) |
| SC100 (SC RS) | 3 tables x General/Teachers x Reduced/Normal x sex, plus a Rule-of-90 column — at least 24 series |
| FL26 (Florida RS) | 5 member classes (Regular, Special Risk, Special Risk Admin, Elected Officers, Senior Management) x sex, per tier |
| OH88 (Ohio Teachers) | grandfathered / non-grandfathered x sex x service band |
| LA44 (Louisiana SERS) | separate assumption sets for Regular Members and for Judges, by service band |
| AZ127 (AZ Corrections) | separate rate sets by hire date (pre / post 1 Jan 2012) |

Not one of the eight publishes a single age x service grid. SC100's withdrawal
rates are split the same way, so this is not confined to retirement.
**Still unchecked: 6 of the 14** — CA111, DC20, GA28, IL33, NM74, NY83.

Anything put in a single age x service grid is therefore a lossy collapse of a
richer structure — unavoidable given the current engine. This is the same issue as
entry 1 in `Data Extraction/assumption_register.md` (tier-specific retirement rates
cannot be represented). Carrying per-tier decrements would be a genuine model
extension, and it is worth considering later.

**Problem 2 — separately, the collapse that was chosen looks wrong in ways the
limitation does not force.** Taking ME47, where the published rates are per 1,000:

- The report gives **13 per 1,000 at age 45** and **29 at age 50**. The workbook
  puts **zero** in both. That is not a collapsing decision — those are published
  values that were dropped.
- The report's age 55-64 rates run from 40 to 250 per 1,000 depending on tier and
  age. The workbook puts a **flat 4%** across the whole band, i.e. the single
  lowest number in the range, applied everywhere. A headcount-weighted blend of
  the three tiers would have been available and would sit far higher.

So the collapse is not merely lossy, it is **systematically low**, and it discards
published data at the young ages. Whether that was a deliberate conservative choice
or an extraction error is not recorded anywhere. Either way the resulting sheet
understates retirement in the band where most retirement happens, which is why
using the shared default table instead is defensible.

**Problem 3 — for two plans the source document does not contain the rates at all.**
*Corrected 2026-07-30: an earlier version of this note named four plans. A
systematic page scan shows only two.* `DC20` (61 pages) and `GA28` (43 pages)
contain no locatable retirement-rate table, although both carry other assumption
tables. `CA111` and `IL33` **do** have retirement-rate pages — the first keyword
search simply missed them; they are unchecked, not missing.

Where the document in the plan folder holds no rate table, that workbook's
retirement sheet must have been built from a document we do not hold and which is
recorded nowhere. Those two cannot be checked against our own files at all. This is
a provenance gap, separate in kind from Problems 1 and 2. Nothing to do now —
obtaining the two full reports is only worth it if we decide to verify those sheets.

Only ME47 has been examined closely enough to demonstrate Problem 2; whether the
other collapses are also systematically low is unknown.

### CORRECTION (2026-07-30) — MA51's bad liability is NOT the inactive factor

Earlier suspicion was wrong. The cause is a units error in MA51's `retdist` sheet.

Column F of that sheet is supposed to hold a **benefit relativity**: each retiree
age band's average benefit divided by the plan's overall average benefit. The model
multiplies it by the reported average benefit, so a correct column must average
1.0 when weighted by headcount.

Checked across all 40 plans, and MA51 is the **only** one out of range:

| | headcount-weighted mean of column F |
|---|---|
| 38 plans | between 0.78 and 1.04, nearly all exactly 1.000 |
| **MA51** | **0.1188** |
| MI53 | not readable at the default offset (it uses `RETDIST_SKIPROWS = 1`; not a defect) |

MA51's column holds each band's **share of total benefit dollars**, not a ratio to
the average benefit — a different quantity entirely. Dividing column F by column B
(the share of retirees) recovers a proper relativity whose headcount-weighted mean
is **0.9696**, i.e. the correct column is derivable from the sheet itself without
opening the PDF.

That scales MA51's retiree benefits to roughly an eighth of their true size, which
accounts for the -79.8% liability gap. The inactive-scaling factor of 0.0 is a
separate open question (§4) and is not the cause here.

**FIXED 2026-07-30 — engine guard, approved route.** `_check_benefit_relativity()`
in `Code/python/fast/Main_PensionModel.py` now runs for **every** plan: it computes
the headcount-weighted mean of the relativity column, warns loudly whenever that
mean falls outside 0.75-1.35, and rebuilds the column as (column F / column B) only
when doing so demonstrably lands back near 1.0 — otherwise it warns and leaves the
published column alone. Empty tail bands carry the last populated value forward.
Workbooks are untouched. To disable, return `rel` unchanged at the top of the
function.

Verified on the data for all 40 plans without running any simulation: **39 plans
pass silently with their column bit-for-bit unchanged, and MA51 alone is rebuilt**
(0.1188 -> 0.9696, with the printed warning explaining what was wrong). Because the
other 39 arrays are untouched, no existing plan's inputs move.

MA51 has not been re-simulated — that is not a step to take here. Its inactive
scaling factor of 0.0 (§4) remains a separate open question, and should be judged
only after this fix is reflected in a run.

### ACCEPTED (2026-07-30) — MA50 and MO64 are in

Their gaps against reported liability (+4.3% and +24.0%) are not treated as
problems. The model uses its own consistent method and assumptions across all
plans; reported actuarial figures embed each plan's own choices. A difference is
expected and is not evidence that our inputs are wrong.

### Key finding on the skipped sheets (2026-07-29)

The switches were **deliberately changed between script generations**, not left
unexamined. Comparing each plan's 2017 script against its 2022 one: plan-specific
retirement rates were switched OFF for 14 plans in the 2022 update (AZ127, CA111,
CA43, DC20, FL26, GA28, IL33, LA44, ME47, NM74, NY83, OH88, SC100, SC99), along
with mortality for 5 of those and withdrawal for GA27 and OH88. The Python engine
inherited the 2022 settings. Six plans (AZ06, CA98, IL32, IL34, NJ71, NJ73) had
those sheets off in both generations.

**No reason is recorded anywhere** — not in script comments, not in the workbook
notes, not in any documentation. So we know the change was intentional and roughly
when it happened, but not why. That argues for checking against the valuation
reports rather than assuming the switches were simply neglected.

- **2026-07-29 — Base year stays 2022 (detail).** We are not moving to fiscal 2023 or 2024
  for now, to avoid changing several things at once. §3 below stays as a recorded
  option rather than a plan. The one part of §3 still live is whether to adopt the
  corrected 2022 figures from the newer PPD file.

## Open work on the inputs

**Everything in §1–§5 is OPEN. Nothing has been executed.**

---

## First: how the model handles missing data today

This matters because otherwise the list below reads like a pile of holes. It isn't.
The model can never be short of a number — there are three layers of backup:

**Each plan has a checklist of nine yes/no switches**, one for each data sheet in
its workbook (active members by age and service, the retiree age distribution,
salaries by age and service, mortality, wage growth, turnover, retirement rates,
refunds, disability). A "yes" means use this plan's own numbers. A "no" means use
the shared table in `default_assumptions.xlsx` instead — the generic actuarial
tables that stand in for any plan without its own.

**The plan-level figures from the PPD have ordered backups.** Wage growth, for
example, tries the PPD's payroll-growth assumption first, then its wage-inflation
figure, then the 2017 value, then the inflation assumption, then 2017 inflation.
Inflation and the inactive-member count work the same way.

**A handful of things are simply fixed by us**, the same for every plan, with no
data source at all: disability payments at 2.5% of payroll, workforce growth at
1% a year, the risk-free rate at 1% above inflation, the stock premium at 7.5%
with 20% volatility, and a 35-year horizon.

So no item below is "there's no number." Each one is either *the switch says one
thing and the workbook contains another*, or *we should decide whether the backup
is the right choice here*.

### On the sheets we don't use — already known, and this confirms it

The record already says not all nine sheets are read. `model_input_dictionary.md`
marks **wage growth** and **disability** as sheets the model never opens, and
`project_context.md` notes that 33 plan-sheets hold the plan's own data that the
switches tell the model to skip. `data_sources_map.md` goes further and says the
audit found mortality and retirement rates to be "half-real, half-default-copied."

The scan done for this document reproduces those numbers independently: 36 cases
where the plan's own data is skipped, of which 3 are the disability sheet the model
never reads anyway — **exactly the documented 33**. That agreement is a good sign
the existing record is accurate. What is new here is only the per-plan breakdown
(§2 below) and the three plans whose switch claims plan-specific mortality when the
sheet actually holds the shared default.

The fixed values (1% workforce growth, 2.5% disability, and the rest) are all listed
in `model_input_dictionary.md` §6. They are deliberate, not gaps. Whether 1% growth
for every plan in every state is a good assumption is a separate question, and a
fair one — it just isn't a data-cleanliness question.

---

## 1. Three plans we currently don't model at all

We run 37 of the 40. These three are the missing ones, and none of them is a lost
cause.

### 1a. MO64 (Missouri) — nothing wrong with it
Its workbook matches a known-good plan (OK134) in every respect the model cares
about: same sheets, same shapes, same layout, and the shares add to exactly 1.0 as
they should. The PPD has complete figures for it in 2017, 2022, 2023 and 2024.

It is missing for a purely clerical reason. The model's list of plans was copied
across from an older set of 38 R scripts, and MO64 wasn't in that set, so it never
got a row in the list. Adding one line admits it.

### 1b. MA51 (Massachusetts) — one gap, and we've found the fix
The one thing genuinely missing is the **employer contribution**. The field the
model reads has been empty for MA51 in every year since 1999.

The new PPD file has the number under different field names: employer contributions
of $2,104,604 for 2022 recorded as "total" and "state" rather than "regular."
So the fix is to let the model fall back to the total when the regular field is
empty. Worth checking the resulting rate against MA51's own valuation report before
adopting it, and worth deciding whether that fallback applies only to MA51 or to
any plan.

A second suspected gap turned out not to be one. MA51 is set up so its
inactive-member population is zero by construction, which means the missing
inactive-member count is never consulted.

### 1c. MA50 (Massachusetts PERC) — the old case against it was mostly wrong
MA50 has been carrying a reputation for being broken. Checking each claim:

- The "syntax error" is not one. `++` in R means plus-followed-by-a-plus-sign and
  gives the same answer as `+`. Verified.
- "Backward tier logic" and "produces no normal cost" describe an old 2017 version
  of its script. The 2022 version does neither — it uses the same shared function
  as every other plan.
- "Missing an asset multiplier" and "different risk-free rate" aren't MA50-specific
  at all; those lines are identical across plans.

What *is* real: MA50's two script versions disagree about which of its sheets to
trust. The older one says use the plan's own turnover and retirement rates; the
newer one says fall back to the shared defaults for both. The newer one looks
right, because MA50's turnover sheet is built on unusual age brackets (20, 30, 40,
45, 50…) instead of the regular five-year steps, so the model would read it against
the wrong ages.

### 1d. A genuine bug that affects MA50 and MA51 both
Their salary-by-age-and-service sheets stop at age 70; every other plan's runs to
age 75. The model reads a fixed block that assumes the longer version.

**R fills the missing row with "not available." Python quietly fills it with zeros.**
That means the two implementations disagree on real data, and the Python side does
it silently — no warning, no error. That silent disagreement is the actual defect;
the short sheet is just a layout quirk.

We need to pick one rule — repeat the age-70 row, use the shared default row, or
leave it at zero — write it down as a stated assumption, and make the reader check
the shape rather than quietly truncating.

One more thing about MA50's salary sheet: every service column holds the same
number, so its salaries vary by age only, with no seniority effect at all. Worth
a look at the source document. (This is the same problem as the Austin wage grid on
the city side.)

---

## 2. Sheets where the switch and the workbook disagree

### 2a. 36 cases where we have the plan's own data and skip it

The switch says "no," so the model uses the shared default table even though the
plan's own numbers are sitting right there in the workbook:

| Sheet | What it drives | Plans affected | Count |
|---|---|---|---|
| Retirement rates | how likely someone is to retire at each age and service level | AZ06, AZ127, CA111, CA43, CA97, CA98, DC20, FL26, GA27, GA28, LA44, ME47, NJ71, NJ73, NM74, NY83, OH88, SC100, SC99 | **19** |
| Mortality | how long members live, and so how long benefits are paid | AZ127, DC20, FL26, GA27, IL33, NJ71, NJ73, NM74, NY83 | **9** |
| Turnover | how many members leave before retiring | GA27, IL32, OH88 | 3 |
| Refunds | payouts to people who leave and take their money | FL26, IL34 | 2 |
| Disability | (never read regardless — see 2c) | CA10, FL26, IL34 | 3 |

**Checked 2026-07-29: the layout worry mostly does not apply here.** For each of
the 33 cases the block was read exactly as the model would read it, and the sheet's
own age and service labels were compared against a plan that is switched on:

- **Retirement, 17 of the 19** hold a full grid of plausible rates in exactly the
  right place, with age and service labels **identical** to the switched-on plans.
  Two exceptions: **FL26**'s sheet will not parse at that range, and **LA44**'s
  block is completely filled and contains −1 values, suggesting a different
  convention (possibly −1 meaning "not applicable").
- **Mortality, all 9** hold a complete block matching the reference in shape and
  magnitude.
- **Turnover, all 3** and **refunds, both** look in range.

So 31 of 33 could be switched on mechanically. **What is still unknown is why they
were switched off.** It is not a layout problem. It could be that someone compared
them against the valuation report and rejected them, or that they were switched off
early and never revisited. `Documentation/provenance/state_notes_harvest.md` does
not explain it. Before flipping any switch, check a sample against the plan's own
valuation report — the layout being right does not make the numbers right.

Retirement rates are the big one, at 19 plans. They matter twice over — they set
when benefits start being paid, and they drain the active workforce.

### 2b. Three plans claim their own mortality but hold the shared table
IN37, ME47 and OR91 are switched to "yes" for mortality, but their sheets contain
the generic default table, cell for cell. The numbers used are the same either way,
so nothing is computed wrongly — but the record says "plan-specific" when it isn't.

Worth noting that ME47 and IN37 both turn up again in §5 among the plans whose
modeled liability is furthest from the reported figure.

### 2c. Two sheets are never opened at all
**Wage growth**: 37 plans have their own wage-growth data in the workbook and the
model has never read any of it — it uses the PPD figures instead. **Disability**:
3 plans have real data; everyone gets the flat 2.5% of payroll.

Neither is necessarily wrong. But right now that data is orphaned without an
explicit decision. Either wire the sheets in, or record plainly — in the assumption
register and in what a run prints — that we prefer the PPD figures and the flat
rate by choice.

---

## 3. The PPD file, and which year to run

### 3a. DECIDED: we stay on 2022
Recorded 2026-07-29. The rest of this section is kept as background for when the
year question comes back, not as pending work. The one live piece is 3b's second
half — whether to take the corrected 2022 figures.

This section is a *choice*, not a problem. The model currently runs on the 2022
figures from the May version of the PPD, and it will keep doing that indefinitely
if we leave it alone. Staying on 2022 is entirely reasonable — it is the year the
work has been built around.

A newer PPD file arrived on 28 July (`ppd-data-latest.csv`, covering 253 plans and
running through fiscal 2024, against the old file's 228 plans through 2023).

### 3b. What the new file would buy us
Two separate things, and they're worth keeping apart:

**Newer years.** Fiscal 2023 and 2024 are both usable now for all 40 plans. My
earlier claim that 2023 was too patchy was based on the *old* file and no longer
holds. There's no 2025 yet. What's still missing anywhere is small and named:
MA51's employer contribution (§1b), the inactive-member count for MA51 and NY78
(both fall back to 2017 automatically), NJ71's inflation assumption in 2022 only,
and the equity share for MO175 in 2023–24 and NM74 in 2024.

**Corrected 2022 figures.** The new file reports *different numbers for 2022* than
the old one — 24 of the values we actually use have changed, nearly all in the
retiree block. CRR revised retiree counts and average benefits. The biggest:

| Plan | Retiree count | Average benefit |
|---|---|---|
| ME47 (Maine) | −16.4% | +19.6% |
| MO175 (Kansas City) | −14.5% | +17.0% |
| CA144 (San Diego City) | −8.0% | — |
| FL26 (Florida RS) | −6.8% | +7.2% |
| LA163 (Baton Rouge) | −7.5% | +8.1% |

These are corrections, so taking them is probably an improvement — but they will
move results, and ME47 is already one of the plans whose liability is furthest off
(§5), so this could be part of that story.

### 3c. What I meant by "confounded" — put plainly
If we decide to take the new file, the file and the year are two separate changes.
Change both at once and results will shift, but we won't know how much came from
the corrected 2022 figures and how much from moving to a newer year.

So if we go: run 2022 on the new file first, compare against what we have now, and
we'll have measured exactly what the data revision did. Then move the year as a
second step. That's the whole point — it isn't a problem with the data, just an
argument for two steps instead of one.

### 3d. Practical bits if we do move
The model reads an Excel file by a hard-coded name; the new one is a CSV (and needs
a non-standard text encoding to open). Either convert it or teach the loader both.
And two small lookup files — the one holding percent-male and related figures, and
the tier-rules workbook — are keyed by year and currently only have 2022 rows, so
they'd each need rows for whatever year we pick.

---

## 4. Things to clarify (no obvious defect, but the record is thin)

- **The four demographic figures** — percent male, percent married, the survivor
  benefit reduction, and the inactive-scaling factor — sit in a file labelled 2022
  but the values are identical to the 2017 file for all 37 plans. It was relabelled,
  not recollected. Decide whether to re-derive them or just state that they're 2017.
- **Tier rules stop at July 2018.** Anything a legislature changed since then isn't
  in the model. Also, CA97 is missing its early-retirement ages entirely. The PPD's
  online interface now publishes tier-by-tier benefit rules, which could either
  check or replace our hand-built file.
- **MA51's inactive-member setting is zero**, which wipes out that population
  entirely. Confirm that's a deliberate statement about MA51 and not a missing value
  that got written as a zero.
- **NY78 has no inactive-member count in any recent year**, so it silently uses the
  2017 figure. That works, but it should be a recorded assumption rather than an
  invisible fallback. Same for **NJ71's inflation**, which falls back to the 2017
  value of 3.5% — noticeably higher than the 2–3% the other plans use. NJ71 does
  have the figure in 2023 and 2024, so moving the year fixes that one.
- **MO175 and NM74 are missing their equity share** in the newer years, which the
  model needs to split assets between stocks and bonds. Needs a rule before any
  year change.

---

## 5. Plans whose modeled liability is far from the reported one

13 of the 37 plans differ from the PPD's reported liability by more than 10%:

| Plan | Difference |
|---|---|
| OK134 (Oklahoma Police) | +134.5% |
| MI53 (Michigan Public Schools) | −30.7% |
| ME47 (Maine) | +30.1% |
| IN37 (Indiana Teachers) | +28.3% |
| ND82 (North Dakota Teachers) | +19.6% |
| DC20 (Washington DC) | +19.3% |
| GA28 (Georgia Teachers) | +17.6% |
| NY78 (New York) | +13.9% |

Plus five more between 10% and 14%.

Some difference is expected — the model values liabilities its own consistent way
while each plan uses its own actuarial method, so they were never going to match
exactly. But 134% is not a method difference, and this is worth understanding.

**This should come last**, because everything above moves these numbers. Switching
on a plan's real retirement or mortality rates (§2) changes its liability directly.
Taking the new PPD (§3) changes both the modeled figure and the reported one we
compare against. Diagnosing the gaps on inputs we're about to change would be
wasted effort.

The overlaps are already visible: ME47 and IN37 both appear in §2b (claiming their
own mortality but holding the default), and ME47 has the largest correction in §3b.

---

## Suggested order

**§1 → §2 → §3 → §5**, with §4 alongside.

§1 is small, self-contained, and takes us from 37 plans to 40 — everything after
benefits from that. §2 is the biggest quality item and doesn't depend on the year
question at all. §3 moves every number, so it should land after the inputs are
settled but before we start diagnosing anything. §5 is the payoff and needs stable
inputs underneath it.

The one thing worth pulling forward is running 2022 on the new PPD file (§3c),
because it's a single clean swap and tells us how much a data revision moves the
results — useful context for judging everything else.
