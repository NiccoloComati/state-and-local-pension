# Input Cleanup To-Do — state track

**Created:** 2026-07-29. **Scope:** getting the model's *inputs* clean and complete
across all 40 state plans. This is not paper or analysis work.

**Everything below is OPEN. Nothing has been executed.**

Written to be read without the code open. Each item says what the input is, what
is actually wrong (if anything), and what the choices are.

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

**These should not be switched on in bulk.** A "no" is often correct precisely
because the plan's sheet is laid out unusually and the model would misread it —
MA50's turnover sheet above is the proven example of exactly that. Each one needs
its block compared against the model's expected layout and against the plan's
valuation report, then either switched on, or the reader fixed, or a note recorded
saying the default is the better choice here.

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

### 3a. Nothing is broken and doing nothing is a valid option
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
