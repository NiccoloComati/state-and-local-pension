# How the model works, end to end

**Written 2026-08-03, corrected the same day.** Every claim was checked against the
code. Line references are to `Code/python/`. Real numbers come from **CA10
(California Teachers)** in run `20260731_1`.

This is the narrative companion to two reference documents. `model_input_dictionary.md`
says where an input comes from; `variable_glossary.md` says what a variable means.
This one says what *happens*.

---

## What changed in the 2026-08-03 correction

Niccolo's review caught three factual errors and one piece of sloppy framing. All
are fixed below; they are listed here so the document does not have to be reread to
find them.

**1. The sheet-switch list was described wrongly (§1).** I wrote that CA10 "uses its
own for the first six and the shared default for retirement, refund and disability".
That is wrong. CA10's entry is `[T,T,T,T,T,T,T,F,F]` — it uses **its own retirement
rates**, and only the refund sheet falls back to the shared default. The cause of
the error is worth recording: **the order of the nine switches is not the order of
the tabs in the workbook.** The switch order is a fixed convention inherited from the
R scripts (ageservice, retdist, wagerel, mortality, wagegrowth, withdrawal,
retirement, refund, disability) and is documented at the top of
`settings/plan_settings.py`. Reading position 7 off the tab order gives the wrong
sheet.

**2. "Only the normal retirement age drives the projection" was wrong (§4).**
Verified across every Python file: `RetirementStart` — the normal retirement age
`nr` — is **only ever assigned, never read**. So is the early retirement age `er`.
**Neither affects anything.** Retirement is driven entirely by the retirement-rate
grid. The assumption register entry E6 in `states_track_context.md` carries the same
wrong statement and needs the same correction.

**3. The claim about valuation reports was overstated (§4).** I wrote that "the
source valuation reports publish rates split by tier, member class, sex and hire
date" as though it were general. The evidence is **eight plans examined**, each
splitting its rates in some such way. It is not a claim about all forty, and the
reports are not uniform.

**4. The disability figure was quoted the way you have already corrected me on
(§6).** The "6% above actual to 0.06% above" numbers are *medians across plans*, and
per plan the picture is materially different — among the 34 plans where the
double-count is confirmed, removing the term only improves the individual match for
22. Rewritten.

Three things the review surfaced that were not in the original at all, now included:

**5. The normal cost rate is indexed by current age, not entry age (§5).**
**6. There is no `InactiveRetirement = 65` anywhere in the Python engine (§4).**
**7. CA10's two tiers apply identical benefit rules (§3).**

Sections 2, 4, 5, 6, 7 and 9 were also expanded where the original was too compressed
to be checkable.

---

## 0. The shape of the whole thing

Two separate stages, and most confusion comes from not keeping them apart.

**Stage one — the deterministic projection** (`engine/run_plan.py`). Builds a
starting population and rolls it forward 34 years under fixed rules. No randomness
anywhere. Produces the accrued liability, money in, money out, and normal cost, per
year. Run it twice, get identical numbers.

**Stage two — the stochastic asset simulation** (`asset_simulation.py`). Takes stage
one's cash flows as given and asks what happens to the fund if investment returns
are uncertain. Draws 10,000 market histories.

**Only the asset side is random.** Liabilities and cash flows are identical in all
10,000 paths. Every fan width you see in the analysis is investment-return
uncertainty and nothing else — there is no uncertainty about mortality, retirement
behaviour, workforce size, wage growth, or policy.

---

## 1. What a plan is made of

### The plan's own workbook — nine sheets

`Data/Plans/States/CA10/CA10_2017.xlsx`. The filename is hard-coded as
`{plan}_2017.xlsx` (`run_plan.py:93`), so these are FY2017 documents whatever year
you run.

A nine-element switch list in `settings/plan_settings.py` decides, sheet by sheet,
whether to read the plan's own numbers or a shared fallback in
`default_assumptions.xlsx`. **The switch order is a fixed R-era convention and is
not the workbook's tab order:**

| # | Sheet | What it holds | CA10 |
|---|---|---|---|
| 1 | `ageservice` | Share of the workforce in each age × service band | own |
| 2 | `retdist` | Share of retirees by age band, and their relative benefit | own |
| 3 | `wagerel` | Salary in each age × service band, relative to the plan average | own |
| 4 | `mortality` | Death rates by age, male and female | own |
| 5 | `wagegrowth` | Wage growth by age and service | **never read, any plan** |
| 6 | `withdrawal` | Probability of quitting, by age and service | own |
| 7 | `retirement` | Probability of retiring, by age and service | **own** |
| 8 | `refund` | Probability a leaver cashes out instead of keeping a benefit | shared default |
| 9 | `disability` | — | **never read; the switch is inert** |

**Two sheets are never read for any plan, whatever the flag says.** `wagegrowth` is
superseded by the PPD scalar chain — wage growth is a single rate per plan, so the
age-and-service detail in the sheet is discarded. `disability` is superseded by the
flat payroll term in §6; position 9 does nothing, and the real disability switch is
`APPLY_DISABILITY_TERM` in the same settings file.

Across the 40 plans, 33 sheet-instances hold the plan's own data but are switched to
the shared default anyway. That predates this project and no reason for it is
recorded anywhere.

### The PPD row — the scale

Everything above is *shape*. The PPD row for the plan and fiscal year supplies
*size*. For CA10 at fiscal 2022:

| | |
|---|---|
| Active employees | 449,418 |
| Average active salary | $80,143 |
| Retirees and other beneficiaries | 325,468 |
| Average benefit | $52,763 |
| Inactive vested members | 47,044 |
| Assets | $257.5bn |
| Reported liability | $346.1bn |
| Assumed investment return | 7.00% |
| Assumed inflation | 2.75% |
| Assumed payroll growth | 3.50% |

**Yes — that is exactly the division you described.** The workbook sheets are all
*relative* quantities: shares of a population, salaries relative to an average,
benefits relative to an average, and probabilities. None of them carries a headcount
or a dollar. The PPD supplies every absolute number: how many people, how much
salary, how much benefit, how many assets. Multiply one by the other and you have a
starting position.

### The tier workbook — the benefit rules

`planchanges_main_2022_clean.xlsx`, one row per plan, thirteen fields per tier and
up to six tiers. What each field is, and whether the engine uses it:

| Field | What it is | Used? |
|---|---|---|
| `startdate` | When this set of rules began applying to new hires | **Yes** — it defines the tier boundary |
| `benefitfactor` | Percentage of final average salary earned per year of service. CA10: 2.4% | **Yes** |
| `vesting` | Years of service before any benefit is owed. CA10: 5 | **Yes** |
| `yrsal` | How many final years are averaged for "final average salary". CA10: 3 | **Yes** |
| `maxsal` | Cap on the benefit as a share of salary. `-100` means no cap | **Yes** |
| `cola` | Annual increase applied to benefits in payment. CA10: 2% | **Yes** |
| `nr` | Normal retirement age. CA10: 63 (tier 1), 65 (tier 2) | **NO — read and never used** |
| `er` | Early retirement age. CA10: 50 | **NO — read and never used** |
| `eecont`, `ercont` | Employee and employer contribution rates for this tier | **NO — never read** |
| `our_cola`, `type`, `compounded` | Alternative COLA encodings | **NO — never read** |

So the rules that actually bite are: **how much you earn per year of service, how
long until you are vested, how many years are averaged, whether there is a cap, and
how fast the benefit grows once in payment.** Everything about *when* you may retire
comes from the retirement-rate grid instead.

On your question about where tier-specific contribution rates would come from:
`eecont`/`ercont` are already in this workbook, populated (CA10: 10.25% employee,
22.16% employer for both tiers). They came with the inherited Brookings collection,
so implementing tier-specific contributions would not need new data collection — but
it would need a check that they are populated and consistent across all 40 plans,
which has not been done.

### The demographic scalars

`PPD_planlevel_main_updated.csv` supplies four values per plan: the share of members
who are male, the share married, the survivor benefit reduction, and an inactive
scaling factor.

---

## 2. Building the starting population

### The active employees

`ageservice` is an 11 × 11 grid of shares by five-year age band and five-year service
band. Multiplied by 449,418 it becomes headcounts (`run_plan.py:305`).

The model works in **single years**, on a 55 × 55 grid covering ages 20–74 and
service 1–55 (`params.py:16-19`), so each band is split into its five years by
`LinearFill`. The split is tilted rather than even, and the tilt comes from the
neighbouring bands: if the next band up holds fewer people, the count should already
be falling inside this one. The tilt multiplies a base of 1, so cells stay positive
and weights always sum to five.

The inherited version instead *added* an age in years to a headcount, which made the
tilt depend on plan size and, at certain band sizes, drove the normaliser to zero —
producing cells of ±200,000 people in a plan with 4,242 retirees. Kept as
`LinearFill_incorrect` so the R lineage still reproduces its original output.

### Their salaries — `wagerel`

Each cell's salary **relative to the plan average**, multiplied by $80,143
(`run_plan.py:329`). Expanded with `ConstantFill` — every year inside a band takes
the same value, no tilt — because a relativity is smooth, not a headcount.

### Wage growth — and why `wagegrowth` is unused

Wages grow at **one rate for the whole plan, every year**. For CA10 that is 3.50%,
the PPD's payroll growth assumption. If that field is missing the model falls back
through wage inflation, then a 2017 legacy file, then general inflation.

The `wagegrowth` sheet holds growth varying by age and service — the promotional and
seniority pattern — for 37 of the 40 plans. **It is read by nothing.** The
consequence: the *shape* of the salary surface across ages and service is frozen at
its 2017 pattern and every cell inflates at the same rate forever. Nobody's salary
grows faster because they are early in a career.

### Mortality

The `mortality` sheet holds death rates at a handful of ages for men and women
separately. `mort_table_fast` (`core.py:263`) expands these to every age from 20 to
119 and blends male and female into one rate using the plan's share of male members.
Below age 30 the age-30 rate is used. There is one mortality table per plan applied
to actives, inactives and retirees alike — no separate healthy/disabled/annuitant
tables, and no mortality improvement over time.

### The retirees — `retdist`

Column B gives the share of beneficiaries in each of 16 age bands; column F gives
each band's benefit relative to the average. Multiplied by 325,468 and $52,763
(`run_plan.py:429-430`). Retirees live on their own 81-row grid, ages 40 to 120.

**To your question: yes, this is only people already receiving a benefit at the
valuation date.** It is a snapshot of the current retiree population and nothing
else. Everyone who retires during the projection is created by the year loop, out of
the active and inactive populations, and added to this same grid as they arrive.

Column F is checked on every plan by a guard: it must average 1.0 when weighted by
headcount, because it is a ratio to the average. MA51's column held shares of total
benefit dollars instead, scaling its retiree benefits to an eighth of true size.

### The inactive members — computed, not read

**There is no inactive-members sheet**, and the definition matters, so precisely:

> An **inactive member** is someone who **stopped working for the employer, did not
> take a cash refund of their contributions, and has not started drawing a pension
> yet.** They are owed a benefit, based on the service and salary they had when they
> left, which they will collect later.

Three clarifications on your reading:

- **Refunds are the opposite of becoming inactive.** A leaver either takes the cash
  and is gone from the plan entirely, or keeps the claim and becomes inactive. The
  `refund` sheet gives the probability of the first. So inactive members are the
  ones who did *not* take a refund.
- **Dead people are not inactive.** Death removes people from every population.
  Where a member was married, part of the benefit continues to a survivor at a
  reduced rate — that continues inside the *retiree* population, not the inactive
  one.
- **Vesting**: a leaver with less service than the vesting requirement is owed
  nothing. CA10 vests at 5 years.

The population is computed, not observed: `calc_inactive_fast` (`core.py:282`) runs
the active population forward under the separation, refund and mortality rates until
the stock of inactive members stops changing — a converged steady state — then
normalises that shape and scales it to the PPD's inactive count of 47,044
(`run_plan.py:486-487`). So the *shape* is implied by the plan's own decrements and
the *size* is observed.

---

## 3. Tiers — the same plan under different promises

Plans change what they promise new hires without changing what they promise existing
ones. The model splits the workforce into **tiers** by length of service, computed
from each tier's start date back from the valuation date (`run_plan.py:262-266`).

CA10 has two: tier 2 began in 2013, nine years before the 2022 valuation, so anyone
with under nine years of service is in tier 2 and everyone else in tier 1.

**A finding worth knowing, which the review prompted.** Comparing every tier field
the engine reads, CA10's two tiers differ in only three: `startdate`, `nr` (63 vs
65) and `er` (both 50, one stored as text). **`nr` and `er` are never read.** So
CA10's two tiers apply **identical benefit rules** — same 2.4% factor, same 5-year
vesting, same 3-year averaging, same 2% COLA, no cap. The 2013 reform that raised
normal retirement from 63 to 65 is, in this model, invisible.

The tier split still does two real things: it partitions the population, and it
determines who hires.

### What is and is not tier-specific

This answers your question about whether tiers already being separate contradicts
needing code changes for tier handling. They are separate at one level and not at
another:

| | |
|---|---|
| **Per tier** | Benefit factor, vesting, salary-averaging years, benefit cap, COLA — and its own population, liability, cash flows and normal cost, computed independently and added up |
| **Plan-wide, shared by every tier** | Retirement rates, withdrawal rates, mortality, refund rates, contribution rates, wage growth |

So the *benefit formula* is tier-aware; the *behaviour* is not. Everyone retires,
quits and dies on the same schedule regardless of tier, and pays the same
contribution rate. That is where the outstanding code work sits — it is a
liability-side gap, not an asset-side one.

**One asymmetry matters a great deal.** Only the newest tier receives new hires;
older tiers are closed groups that can only shrink (`core.py:618-623`, the
`CurrentTier` flag). Realistic — nobody is hired into the pre-2013 deal any more —
and it means older tiers wind down while the newest carries the whole future
workforce.

---

## 4. One year of the projection

At each step the model holds six things: the active population by age and service,
their wages, the inactive population, the benefits those inactives have earned, the
retiree population, and retiree benefits. Moving one year (`core.py:588-632`):

### Step 1 — record this year's money

Computed from the state at the *start* of the year, before anyone moves. Your point
that the original lumped these together was fair; here they are separately.

**Money in — two components** (`core.py:612-613`):

| Component | Formula |
|---|---|
| Employee contributions | active payroll × employee rate (CA10: 10.14%) |
| Employer contributions | active payroll × employer rate (CA10: 16.26%) |

where active payroll is the sum over every cell of headcount × salary. CA10 year
one: **$9.51bn** total. That is all. There is no other inflow — investment income
belongs to stage two, and state appropriations are excluded by decision.

**Money out — four components** (`core.py:605-611`):

| Component | What it is | CA10 year one |
|---|---|---|
| Retiree benefits | retiree headcount × their benefit, summed over ages | $13.45bn |
| Refunds | leavers who cash out, receiving their own past contributions accumulated at the risk-free rate | included in the $1.52bn below |
| Death benefits | for members who die in service or while inactive, the value of the benefit paid to survivors | included below |
| Disability | a flat 2.5% of active payroll (§6) | included below |
| **Total** | | **$14.97bn** |

(The three non-retiree terms are not stored separately in the saved output, only in
aggregate; the $1.52bn is their sum.)

**Normal cost** is recorded alongside but is *not* a cash flow — it is an accounting
quantity, defined in §5.

### Step 2 — age everyone

Each active cell moves diagonally, one year older and one year more service, and is
multiplied by the probability of not leaving (`core.py:93-108`):

```
survivors = population × (1 − mortality − separation − retirement)
```

**On your pushback about subtraction: you are right and my original wording was
wrong.** The three events are mutually exclusive within a year in this model's
construction — someone who dies does not also separate — so adding the rates and
subtracting once is the *correct* treatment, not an approximation. I have removed the
word "simplification".

What is worth flagging instead is that **there is no clamp**. If the three rates ever
summed above 1 for some cell, the multiplier would go negative and the cell would go
negative with it. A clamp to 1.0 exists in the present-value-of-salary calculation
(`core.py:442`) but not in the population update (`core.py:97-98, 115-116`). Whether
any plan's grids actually reach that point is **not verified** — the saved outputs
do not contain the active matrix, so checking it needs a run that saves it.

### Step 3 — refill the workforce, newest tier only

The target headcount is last year's total × 1.01 — a **flat 1% growth for every
plan, with no data source behind it**. The shortfall is distributed across the
**first three service columns** in proportion to how many people were in those
columns last year (`core.py:104-107`):

```
cm = Employees[:, :3, year-1]                       # everyone with 1-3 years service
Employees[:, :3, year] += (cm / cm.sum()) × shortfall
```

**That is what "intake pattern" meant, and it was too vague.** Concretely: the model
looks at the *age profile* of everyone currently in their first three years of
service — the plan's recent hiring pattern, however many 22-year-olds versus
35-year-olds it takes on — and hires the new cohort in exactly those proportions.
That profile is frozen: whatever the mix was in 2017, it is the mix in 2056.

Older tiers skip this entirely.

### Step 4 — grow wages

Every cell rises by the plan's single wage growth rate, 3.50% for CA10.

### Step 5 — move leavers into the inactive stock

Those who separated and did **not** take a refund become inactive vested members
carrying a benefit computed from their service and final average salary
(`core.py:124-171`). Inactive members then age, and are removed by two things: death,
and retirement.

**How inactive members retire, since you asked:** through exactly the same
retirement-rate grid as actives. `update_retirement_number` (`core.py:185-193`) draws
new retirees from the active *and* inactive populations using the same
`RetirementRate[age, service]`, with service frozen at whatever they had when they
left.

**And a correction to a claim in `project_context.md`:** §4.2 there says inactive
members "eventually draw benefits at `InactiveRetirement = 65`". **No such constant
exists anywhere in `Code/python`** — I searched every file. Inactive members retire
through the rate grid, not at a fixed age. That statement should be checked against
the R lineage and corrected.

### Step 6 — retire people, and pay survivors

New retirees arrive from both actives and inactives. Existing retirees die at their
mortality rate — but not entirely: a married retiree's benefit continues to a
survivor at a reduced rate, which is why the survival step carries the married share
and the survivor reduction (`core.py:217-218`).

### Step 7 — escalate benefits in payment

By the tier's COLA, 2% for CA10.

That is one year. **The loop runs 34 times**, and the reason is mechanical rather
than conceptual — see §8, where the 34-versus-35 question is answered properly.

### What the model cannot represent, structurally

- **No retirement age is used at all.** Both `nr` and `er` are loaded and never read.
  Retirement happens purely through the rate grid, which does spread retirement
  across ages exactly as you supposed. **What is missing is not the timing but the
  benefit distinction**: real plans pay a *reduced* benefit to someone retiring
  early, and this model has one benefit formula per tier applied at whatever age the
  grid retires you. So a plan cannot represent "you may go at 50, but at a penalty".
  My original phrasing, "nobody retires early", was wrong and misleading.
- **No disability state.** Members leave active service by quitting, retiring or
  dying, and that is all. The 2.5% payroll term is attached to no population.
- **One retirement-rate grid per plan.** Of the plans examined against their own
  valuation reports — **eight, not all forty** — every one published rates split some
  further way: by tier, member class, sex, or hire date. A single grid collapses
  that. The reports are not uniform and this is not a claim about all 40.
- **Contribution rates are plan-level**, though `eecont`/`ercont` sit unread in the
  tier workbook.
- **No mortality improvement.** One table, unchanged over 34 years.

---

## 5. The liability, and what "entry-age normal" actually means

This section was the least clear in the original and is rewritten.

### First, the question the liability answers

Not "what will this plan pay out?" but: **"of everything this plan will eventually
pay to the people who are already its members, how much has been earned by work
already done?"**

That is why it is a **closed group** — the term you flagged as unexplained. A closed
group means: take today's members, let nobody new join, and follow them to the end.
New hires are excluded not by oversight but because they have not earned anything
yet. Their future benefits are a future obligation, not a present one.

This is exactly why it differs from the cash-flow projection in §4, which *does* keep
hiring. The cash-flow projection asks "what will this fund pay and receive?" — a
question about the ongoing institution. The liability asks "what does it owe right
now?" — a question about accrued obligations. Two questions, deliberately different
populations.

### The identity

```
AAL  =  (PV of future benefits for current actives  −  PV of their future normal costs)
        +  PV of future benefits for current inactives and retirees
```

(`core.py:602-603`)

For the actives, everything they will ever be paid splits into a part earned already
and a part they will earn by working more. Subtract the second and what remains is
accrued. **Inactives and retirees are added without any subtraction, and your
reasoning for why is exactly right**: they will never work another day for this
employer, so no part of their benefit is attributable to future service. Their
benefit is already fixed by past service and salary. That they have not started
*collecting* yet is irrelevant — it is earned.

### The first piece: present value of future benefits

`_liab_path` (`core.py:459-494`) runs a closed-group projection: today's population,
rolled forward under exactly the same yearly rules as §4 but with **no new hires**
(`l_update_employees` rather than `update_employees`). Every benefit dollar paid
along the way is collected and discounted at the plan's assumed return, 7% for CA10.
Two of these run in parallel — one starting from the actives, one from the inactives
and retirees — giving the two terms of the identity.

**To your question: no, neither term includes future employees.** Nothing about
anyone not yet hired appears in the AAL.

### The second piece: normal cost, built from the ground up

Start from the problem it solves. A member works for 30 years and then collects a
pension for 25. The pension is *earned* across those 30 working years — but how much
in each one? There is no natural answer; it is an allocation choice, and different
choices are different actuarial methods.

**Entry-age normal makes this choice: allocate the cost as a constant percentage of
the member's salary, every year from hire to exit.** So if the answer is "8.7% of
pay", then 8.7% of pay is the cost attributed to each working year, and the accrued
liability at any moment is what has built up under that schedule.

**The percentage is found by setting up an equality at the moment of hire.** For a
brand-new employee, nothing is accrued yet, so the entire benefit must be funded by
future contributions:

```
(that percentage) × (present value of all the salary they will ever earn)
      =  present value of all the benefits they will ever receive
```

Rearranged:

```
percentage  =  PV(all their benefits)  /  PV(all their salary)
```

**And now the 55 one-person simulations make sense.** To evaluate that ratio you need
a hypothetical new hire — but the answer depends on how old they are when hired,
because someone hired at 25 has forty years of salary ahead and someone hired at 55
has ten. So the model runs **one simulation per possible hiring age, 20 through 74 —
55 of them** (`core.py:404-452`). Each places a single employee, one person, at that
age with zero service, and follows them under the plan's own quit, retire, die and
refund rates until they are gone, accumulating the present value of every benefit
they generate. Alongside, the present value of that same person's future salary. The
ratio is the percentage for that hiring age.

These are not projections of anything real. They are a **pricing exercise** run once
per tier to establish a schedule of rates: "an employee hired at age *x* costs *y*
percent of pay per year". That schedule is then applied to the actual workforce:

| Quantity | How it is built |
|---|---|
| **Normal cost** this year | rate × the member's current salary, summed over everyone (`core.py:597-599`) |
| **PV of future normal costs** | rate × PV of the member's *remaining* salary, summed over everyone (`core.py:595-596`) |

The second is what gets subtracted in the identity above. That is the whole
mechanism, and it is why normal cost appears in the outputs as a separate series: it
is the annual cost of ongoing accrual, an accounting quantity rather than a cash
flow.

### An observation about the implementation, offered as a question

The rate schedule is indexed by **entry age**, correctly. But when it is applied to
the workforce, the contraction at `core.py:595-599` pairs it with the employee's
**current age** — so someone aged 50 with 20 years of service is charged the rate
for *entering* at 50, not the rate for entering at 30.

Standard entry-age normal uses the actual entry age, which here would be current age
minus service. I am flagging this as an observation, not a verdict: it is inherited
from the R implementation, and the fast engine was verified bit-identical to the
original which was verified against R, so it is not a translation error. Whether it
is the intended treatment is a question worth putting to someone who knows the
actuarial convention.

### For CA10 in the base year

| Component | Amount |
|---|---|
| Accrued liability, tier 1 actives *and their inactives* | $152.8bn |
| Accrued liability, tier 2 actives *and their inactives* | $18.1bn |
| Accrued liability, members already retired at 2022 | $184.3bn |
| **Model total** | **$355.2bn** |
| Reported (GASB) liability | $346.1bn |
| Difference | **+2.6%** |

**On your question about the labels: the label was too generic and you were right to
query it.** The already-retired figure is a *separate population*, not a tier.
Retirees are the 325,468 people already collecting at the valuation date; they are
projected by their own routine (`main_ret_fast`) rather than by the tier machinery,
because they have no service, no salary and no normal cost. They are not "outside the
tiers" for any conceptual reason — the tier split is a partition of *workers*, and
they are not workers.

**And on your second question: no, these do not sit on both sides.** The liability is
$355.2bn; the assets are $257.5bn; they are different quantities and the plan is
underfunded by the difference. Nothing is double-counted.

---

## 6. The disability term, and what "the retiree stream" means

`outflow = retiree benefits + refunds + death benefits + disability`

The disability term is a flat **2.5% of active payroll**, added every year, attached
to no population — there is no disability state in the model.

**"The retiree stream" means the first term**, retiree headcount × retiree benefit,
and the argument that it already covers disability retirees runs like this. The
retiree population is scaled by the PPD's `beneficiaries_tot`, which is **every**
beneficiary the plan pays, and priced at `BeneficiaryBenefit_avg`, the average across
that same whole group. Checked across the 35 plans that publish a breakdown, service
+ disability + survivor retirees sum to exactly 1.0000 of `beneficiaries_tot`, with
disability retirees a median 3.3%. So disability retirees are inside that first term
already, being paid — and then 2.5% of payroll is added on top.

(Nothing to do with contribution rates; those are the *inflow* side.)

**On how strong the evidence is — and you have corrected me on this before, so
stating it properly:** in aggregate, removing the term moves the median first-year
outflow across plans from about 6% above what plans actually paid to close to 1:1.
**Per plan it does not hold.** Among the 34 plans where the double-count is confirmed
from the PPD breakdown, removing the term only improves the individual match for 22 —
12 get worse. LA130 and PA93 move away decisively. So the test has real power in
aggregate and weak power on any single plan, and the term is left switched on
pending a decision.

A nuance that survives: the term may have been intended for members who become
disabled *in future*, who never enter the retiree stream because the engine has no
disability transition. On that reading it is a crude stand-in rather than pure
duplication — but at 2.5% of payroll it is several times the size of the gap it
could legitimately fill.

---

## 7. The asset stage

**Two buckets.** Everything risky — public equity, private equity, real estate, hedge
funds, commodities, alternatives, "other" — is one; the rest is the other. CA10:
**87.4% risky, 12.6% safe**.

**Returns.** Risky earns inflation plus a 7.5% premium with 20% standard deviation.
Safe earns the risk-free rate, inflation plus 1% (3.75% for CA10), with **zero
volatility** — bonds cannot lose money here.

**One shared market history.** A single 34 × 10,000 matrix of standard normal draws
from seed 123, and **every plan in a run uses the same one**. Simulation column 4,712
is the same sequence of good and bad years for all 40 plans.

**This is a change from the inherited implementation, and it is what makes the
cross-plan work possible.** The R lineage drew each plan's returns independently. Under
independent draws, one plan's bad decade coincides with another's good one, the
aggregate fluctuations cancel, and any aggregate fan understates risk badly — it
implicitly assumes the states are exposed to unrelated economies. Sharing one shock
matrix makes a bad path bad for everyone at once, which is what a real downturn does,
and is the reason the joint-failure analysis is possible at all.

**The roll-forward:**

```
assets[t+1] = max( assets[t] × (1 + return[t]) − outflow[t] + contribution[t] , 0 )
```

**The contribution rule** (`asset_simulation.py:418`):

```
contribution = 0 if funded ratio > 1 else cash_inflows[t]
```

Underfunded, the plan contributes what stage one said. Overfunded, it contributes
**nothing** — and never restarts, since there is no rule that resumes contributions
if funding falls back. There is no catch-up, no gradual return, no amortisation. (An
amortisation branch exists but is switched off in every run to date.)

### Your three questions about this, which are all really one question

**"If overfunded plans stop contributing, is the money gone?"** No. The contribution
is simply never made — the employer keeps it. Nothing leaves the fund. Stage one's
`cash_inflows` still records what *would* have been contributed; the asset stage
declines to add it.

**"Then why do funding ratios reach 5?"** Because contributions are not what makes a
well-funded plan grow — **returns are**. An 87%-equity portfolio compounds at roughly
7–9% expected while the liability grows much more slowly, so a plan that gets ahead
keeps getting further ahead, with contributions switched off the whole time. There is
no contradiction: contributions stop, compounding does not, and nothing in the model
ever spends a surplus. Hence the medians above 3.0 at 2055 for several plans.

**"When a plan is exhausted, is money being created from nowhere?"** No, and my
original phrasing was loose. The recursion clamps at zero: with assets at zero,
`max(0 × (1+r) − outflow + contribution, 0)` is zero whenever outflow exceeds
contribution. **The model does not pay the shortfall — it simply stops tracking it.**
No money is created. The benefits that would have to be paid are outside the model's
accounting entirely, which is exactly the quantity the conditional-severity section
of the analysis notebook now computes as the pay-as-you-go shortfall.

**"Could a plan ever recover?"** Yes, mechanically — nothing prevents it. If in some
year contributions exceeded outflows, assets would rise above zero and the plan would
be funded again. It simply never happens: checked across all 40 plans, **0 recoveries
out of 132,127 exhausting paths**. The reason is structural rather than enforced — a
plan exhausts because its benefit payments have outgrown its contributions, and that
gap widens as the retiree population matures.

### For CA10

| | |
|---|---|
| Starting assets, identical in all 10,000 paths | $257.5bn |
| 5th percentile of 2056 assets | **$0** (exhausted) |
| Median | $349.6bn |
| 95th percentile | $7,819bn |
| Probability of exhausting by 2056 | **0.337** |

---

## 8. What comes out

`MainRes` and `RetRes` are the raw per-population results, and I used them in the
original without introducing them. **`MainRes`** is a dictionary keyed 1–6 by tier,
each entry holding that tier's accrued liability, outflows, inflows, present value of
future benefits and normal cost. **`RetRes`** is the same for the already-retired
population, with liability and outflows only. Adding them up is exactly how the
plan-level totals are formed (`run_plan.py:527-530`).

| Output | Shape | Random? |
|---|---|---|
| `AAL` | 35 × 10,000 | **No** |
| `cash_inflows`, `cash_outflows`, `NormalCost` | 35 × 10,000 | **No** |
| `Assets` | 35 × 10,000 | **Yes** |
| `MainRes` / `RetRes` (per tier) | 35 × 1 each | No |

**On the 10,000 columns of deterministic output: nothing is computed 10,000 times.**
The deterministic stage runs with `NMonte = 1` (`run_plan.py:287`) and produces a
single column. The asset stage widens it to 10,000 by *recycling* that one column
(`asset_simulation.py:323-333`) purely so the arithmetic lines up with the assets
matrix. The cost is disk space, not compute.

### Why the two sides have different lengths

The liability loop is `for t in range(1, Nyear)` writing to index `t-1`, so it fills
rows 0–33 and **never touches row 34**, which is exactly zero for all 40 plans. The
asset loop is `for t in range(nyear-1)` writing `assets[t+1]`, filling rows 1–34. So
liabilities cover 2022–2055 and assets cover 2022–2056.

**Is that wrong?** It is at least an inconsistency nobody chose deliberately: the
liability loop's `t-1` indexing means the last array slot is simply never computed,
which reads as an off-by-one rather than a decision. Two consequences: exhaustion can
be measured a year further out than any funded-ratio measure, and 4.4% of exhausting
paths first exhaust in that extra year. It has been documented rather than changed,
because changing it moves published numbers and needs a deliberate decision. Also
worth noting `Nyear = 35` is the array height, not the count of projected liability
years, which is 34.

**And this answers "why 34 and not 35"** — nothing conceptual, just where the loop
stops.

---

## 9. Things that surprise people

1. **Only investment returns are random.** Everything else — wages, benefits, cash
   flows, headcounts — is a single deterministic path repeated in all 10,000
   simulations. (The original listed this as two separate points; it is one.)
2. **The liability is a closed group; the cash-flow projection is not.** The
   liability follows today's members with no new hires, because it measures what is
   owed now. The cash-flow projection keeps hiring, because it measures what the fund
   will pay and receive. Different questions on purpose.
3. **Only the newest tier hires.** Older tiers wind down.
4. **The workforce grows at exactly 1% a year in every plan**, with no data source.
5. **No retirement age is used.** `nr` and `er` are both read and never applied;
   retirement comes entirely from the rate grid. What is missing is the *reduced
   benefit* for early retirement, not the timing.
6. **There is no disability state**, and the 2.5% payroll term is attached to no
   population.
7. **Overfunded plans stop contributing entirely** and no rule ever restarts them,
   while returns keep compounding — which is what produces funding ratios above 3.
8. **Exhausted plans never recover** in practice, though nothing prevents it.
9. **There is no funding policy.** Contributions are a fixed percentage of payroll,
   forever. In particular:
   - **No amortisation schedule** — a real plan that is underfunded calculates
     an extra payment designed to close the gap over a set number of years, typically
     20–30. This model makes no such payment; the deficit is never targeted.
   - **No actuarially determined contribution** — the annual figure a plan's
     actuaries calculate as what *should* be paid, normally normal cost plus that
     amortisation payment. The model neither computes nor uses it.
   - Consequently, **every contribution-policy question requires a new run**, not a
     re-analysis. That is what the contribution grid in `scenarios.py` exists for.

---

## 10. Where each piece lives

| What | Where |
|---|---|
| Loading inputs, building the population, tiers | `engine/run_plan.py` |
| Band-to-single-year expansion | `engine/bucketfill.py` |
| Yearly update rules, liability, normal cost | `engine/core.py` |
| PPD fallback chains, inactive scaling | `engine/functions.py` |
| Every per-plan exception, with its reason | `settings/plan_settings.py` |
| The stochastic asset stage | `asset_simulation.py` |
| Scenario variants | `scenarios.py` |

Nothing in `Analysis/` shares code with any of it; the analysis layer only reads
saved outputs.

---

## Open items this document raised

Recorded here so they are not lost. None has been acted on.

1. **`nr` and `er` are never used.** Register entry E6 in `states_track_context.md`
   says only `er` is unused and that `nr` "drives the projection". It does not.
2. **`project_context.md` §4.2 refers to `InactiveRetirement = 65`.** No such
   constant exists in `Code/python`.
3. **The normal cost rate is applied by current age rather than entry age** (§5).
4. **No clamp on summed decrements** in the population update, unverified whether it
   ever binds.
5. **CA10's two tiers are behaviourally identical**, since their only rule difference
   is `nr`. How many other plans have tiers that differ only in unused fields has not
   been checked.
