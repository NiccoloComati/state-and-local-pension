# How the model works, end to end

**Written 2026-08-03. Every claim here was checked against the code, not recalled.**
Line references are to `Code/python/`. Real numbers throughout come from **CA10
(California Teachers)** in run `20260731_1`, chosen because it is the largest plan
and has a simple two-tier structure.

This is the narrative companion to two existing reference documents. Use
`model_input_dictionary.md` to look up where a particular input comes from, and
`variable_glossary.md` to look up what a particular variable means. Use this one to
understand what actually *happens*: how a workforce is built, what changes between
one year and the next, how a liability is formed out of that, and how the
stochastic stage turns it into ten thousand futures.

---

## 0. The shape of the whole thing

The model runs in **two separate stages**, and almost every confusion about it
comes from not keeping them apart.

**Stage one — the deterministic projection** (`engine/run_plan.py`). One plan at a
time. It builds a starting population of employees and retirees, then rolls it
forward 34 years applying the same demographic rules every year. There is no
randomness anywhere in this stage. It produces four things per year: the accrued
liability, the money coming in, the money going out, and the normal cost. Run it
twice and you get identical numbers.

**Stage two — the stochastic asset simulation** (`asset_simulation.py`). It takes
stage one's cash flows as given and asks: if investment returns are uncertain, what
happens to the fund? It draws 10,000 market histories and rolls the assets forward
along each. Only the *asset* side is random. The liabilities and the cash flows are
the same in all 10,000 paths.

That asymmetry is the single most important thing to hold on to. **When a fan chart
in the analysis widens, that width is investment-return uncertainty and nothing
else.** The model contains no uncertainty about mortality, retirement behaviour,
workforce size, wage growth, or benefit policy.

---

## 1. What a plan is made of

Four sources feed one plan. None of them is a single tidy database row.

**The plan's own workbook**, `Data/Plans/States/CA10/CA10_2017.xlsx`. Nine sheets
describing the *shape* of the plan: how employees are spread across ages and years
of service, how their salaries vary, how retirees are spread across ages, and the
rates at which people quit, retire, die, and take refunds. The filename is
hard-coded as `{plan}_2017.xlsx` (`run_plan.py:93`) — these are FY2017 documents
regardless of what year you run.

**A nine-element switch list**, `AVAILABLE_DATA` in `settings/plan_settings.py`,
decides sheet by sheet whether to use the plan's own numbers or a shared fallback
in `default_assumptions.xlsx`. CA10 uses its own for the first six and the shared
default for retirement, refund and disability rates.

**The PPD row** for the plan and fiscal year, giving the *scale*: how many people
there are and how much money is involved. For CA10 at fiscal 2022:

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

**The tier workbook**, `planchanges_main_2022_clean.xlsx`, giving the benefit rules
and when they changed.

So: **shapes from 2017, scales from 2022.** There is no single base year, and the
combination is deliberate. The 2017 workbooks are the last full extraction of plan
demographics; the PPD supplies current totals.

---

## 2. Building the starting population

### The active employees

The `ageservice` sheet is an 11 × 11 grid of **shares** — the fraction of the
workforce in each five-year age band by each five-year service band. Multiply by
449,418 and you have headcounts per band (`run_plan.py:305`).

The model does not work in bands, though. It works in **single years of age and
single years of service**, on a 55 × 55 grid covering ages 20–74 and service 1–55
(`params.py:16-19`). So each band has to be split into its five constituent years.

That splitting is `LinearFill` (`engine/bucketfill.py`), and it is worth
understanding because it was wrong until July 2026. Splitting a band evenly would
put the same number of people at age 40 as at age 44, which is not right if the
workforce is growing or shrinking across that range. So the split is tilted, and
**the tilt is taken from the neighbouring bands**: if the next band up holds fewer
people, the count should already be falling inside this one. The tilt is a
multiplier centred on 1, so every cell stays positive and the five weights always
sum to five.

The inherited version instead *added* an age in years to a headcount, which made
the tilt depend on plan size and, for certain band sizes, made the normaliser
approach zero — producing cells of ±200,000 people in a plan with 4,242 retirees.
It is kept as `LinearFill_incorrect` so the older R lineage still reproduces its
original output.

### Their salaries

The `wagerel` sheet gives each cell's salary **relative to the plan average**.
Multiply by $80,143 and you have a dollar salary for every age-and-service cell
(`run_plan.py:329`). This one is expanded with `ConstantFill` — every year inside a
band gets the same value, no tilt — because a relativity is a smooth quantity, not
a headcount.

### The retirees

The `retdist` sheet gives the share of beneficiaries in each of 16 age bands
(column B) and each band's benefit relative to the average (column F). Multiplied
by 325,468 and $52,763 respectively (`run_plan.py:429-430`). Retirees live on their
own 81-row grid, ages 40 to 120.

Column F is the input that a guard now checks on every plan: it must average 1.0
when weighted by headcount, because it is a ratio to the average. MA51's column held
shares of total benefit dollars instead, which scaled its retiree benefits to about
an eighth of their true size.

### The inactive members — not read from anywhere

This one surprises people. **There is no inactive-members sheet.** Inactive members
are people who left before retiring but kept a vested benefit, and the model
*computes* them: `calc_inactive_fast` takes the active population and runs it
forward under the separation, refund and mortality rates until the stock of
inactive members stops changing, then normalises the resulting shape and scales it
to the PPD's inactive count (`run_plan.py:486-487`).

So the inactive population's *shape* is a converged steady state implied by the
plan's own decrements, not an observation. Its *size* is observed.

---

## 3. Tiers — the same plan under different promises

Public plans change what they promise new hires without changing what they promise
existing ones. Everyone hired before the change keeps the old deal. The model
represents that by splitting the workforce into **tiers**.

CA10 has two:

| Tier | Rules start | Benefit factor | Vesting | Salary averaging | Normal retirement age | COLA |
|---|---|---|---|---|---|---|
| 1 | 1963-01-01 | 2.4% per year of service | 5 years | 3 years | **63** | 2% |
| 2 | 2013-01-01 | 2.4% per year of service | 5 years | 3 years | **65** | 2% |

The split is by **length of service**, computed from each tier's start date back
from the valuation date (`run_plan.py:262-266`). Tier 2 began in 2013, which is
nine years before the 2022 valuation, so anyone with under nine years of service is
in tier 2 and everyone else is in tier 1. California Teachers' 2013 reform kept the
benefit formula but pushed normal retirement from 63 to 65.

Each tier is then projected **completely separately** and the results added
together. Its liability, its cash flows and its normal cost are all computed on its
own population with its own rules. This is why per-tier results exist in the saved
output at all.

**One asymmetry matters a great deal.** Only the newest tier receives new hires;
every older tier is a closed group that can only shrink (`core.py:618-623`, the
`CurrentTier` flag). That is realistic — nobody gets hired into the pre-2013 deal
any more — and it means the older tiers wind down over the projection while the
newest one carries the entire future workforce.

---

## 4. One year of the projection

This is the engine of the whole thing. Everything else is setup or accounting.

At each step the model holds six things: the active population by age and service,
their wages, the inactive population, the benefits those inactive members have
earned, the retiree population, and retiree benefits. Moving from one year to the
next (`core.py:588-632`):

**First, record this year's money.** Benefits paid to retirees, refunds to people
who quit and cashed out, death benefits, and the disability term. Contributions in.
These are computed from the state at the *start* of the year, before anyone moves.

**Then age everybody.** Each active employee cell moves diagonally — one year older,
one year more service — and is multiplied by the probability of *not* leaving
(`update_employees`, `core.py:93-108`):

```
survivors = population × (1 − mortality − separation − retirement)
```

The three decrements are subtracted, not compounded, which is a simplification but
a standard one at these rates.

**Refill the workforce, but only in the newest tier.** The target headcount is last
year's total times 1.01 — a **flat 1% workforce growth for every plan, with no data
source behind it**. New hires are added to the lowest service columns in proportion
to the existing intake pattern (`core.py:104-107`). Older tiers skip this entirely.

**Grow wages.** Every cell's salary rises by the plan's wage growth assumption —
3.5% for CA10, taken from the PPD's payroll growth assumption. One rate for
everybody; no promotional or seniority scale beyond what the starting `wagerel`
grid already encodes.

**Move the leavers into the inactive stock.** Those who separated and did *not* take
a refund become inactive vested members carrying a benefit calculated from their
service and final average salary (`core.py:124-171`). Inactive members then age,
and are removed by death or by reaching retirement.

**Retire people.** New retirees flow in from both the active and the inactive
populations at the retirement rate for their age and service (`core.py:174-197`).
Existing retirees die at their mortality rate — but not entirely: a married
retiree's benefit continues to a survivor at a reduced rate, which is why the
survival step carries `pct_mrg` and `widow_reduct`.

**Escalate retiree benefits** by the tier's COLA, 2% for both CA10 tiers
(`core.py:219`).

That is one year. Repeat 34 times.

### What the model cannot represent, structurally

- **Nobody retires early.** The tier workbook carries early-retirement ages
  (`er1`–`er6`) and the engine reads them into a frame and then never uses them.
  Only the *normal* retirement age drives anything.
- **Nobody becomes disabled.** There is no disability state. Members leave the
  active population by quitting, retiring or dying, and that is all.
- **One retirement-rate grid per plan**, though the source valuation reports
  publish rates split by tier, member class, sex and hire date. Any single grid is
  a lossy collapse of that.
- **Contribution rates are plan-level**, though the tier workbook carries
  tier-specific ones that are never read.

---

## 5. How the liability is computed, and why "entry-age normal"

The accrued liability is not accumulated during the year loop. It is computed
**from scratch at each year** by running a second, nested projection.

### The identity

```
AAL  =  (PV of future benefits for actives  −  PV of future normal costs)
        +  PV of future benefits for inactives and retirees
```

which is `core.py:602-603`. In words: of everything the plan will eventually pay
its current employees, some has been earned already and some will be earned by
future work. The part attributable to future work is the future normal cost.
Subtract it, and what remains is what has been *accrued*. Benefits for people who
have already stopped working are accrued in full, so they are added without
subtraction.

### The two projections that produce it

**The present value of future benefits** comes from `_liab_path`
(`core.py:459-494`), which runs a **closed-group** projection: it takes today's
population, rolls it forward under exactly the same yearly rules as section 4, but
**with no new hires** (`l_update_employees` rather than `update_employees`). It
collects every benefit dollar paid along the way and discounts it at the plan's
assumed return — 7% for CA10. Two of these run in parallel, one starting from the
actives and one from the inactives and retirees, which is where the two components
of the identity come from.

This is the reason the closed-group distinction matters: **the liability counts
only people who are already here.** The cash-flow projection in section 4, by
contrast, keeps hiring. They are answering different questions on purpose.

**The normal cost** is where "entry age" enters, in `pvnc_calc_fast`
(`core.py:404-452`). The model runs **55 separate one-person simulations**, one for
each possible entry age from 20 to 74. In each, a single employee starts with zero
service and is followed to death, and the present value of every benefit they
generate is recorded. Alongside it, the present value of that person's future
salary is computed. Divide one by the other:

```
normal cost rate at entry age x  =  PV(all benefits) / PV(all salary)
```

That is the **level percentage of salary** which, paid every year from entry, would
exactly fund the benefits — the definition of entry-age normal. A member's normal
cost in any year is then that rate times their current salary, and the *present
value of future* normal costs is that rate times the present value of their
remaining salary. Both appear in `core.py:595-599`.

The rates are computed once per tier and escalated with inflation thereafter, which
is a shortcut — recomputing them each year would be exact and expensive.

### For CA10 in the base year

| Component | Amount |
|---|---|
| Tier 1 accrued liability | $152.8bn |
| Tier 2 accrued liability | $18.1bn |
| Already-retired accrued liability | $184.3bn |
| **Model total** | **$355.2bn** |
| Reported (GASB) liability | $346.1bn |
| Difference | **+2.6%** |

That the model's own method lands within 3% of the plan's actuaries using their own
methods is reassuring, but closeness is not the objective — the model applies one
consistent method to all 40 plans, whereas each reported figure embeds that plan's
own actuarial choices.

---

## 6. The money in and out

**Inflows** are simple to the point of bluntness (`core.py:612-613`):

```
contributions = total active payroll × (employee rate + employer rate)
```

For CA10 the rates are 10.14% and 16.26%, from the PPD's contribution dollars
divided by covered payroll. Year-one contributions come to **$9.51bn**.

Two consequences worth knowing. Contributions scale automatically with the
projected workforce and wages, so they grow at roughly 1% plus wage growth
regardless of the plan's funded position — **there is no funding policy in stage
one**, no amortisation schedule, no actuarially determined contribution. And money
recorded in the PPD as a *state* contribution is excluded entirely, which is a
deliberate decision affecting ten plans and radically affecting three.

**Outflows** are four separate terms (`core.py:610-611`):

```
outflow = retiree benefits + refunds + death benefits + disability
```

For CA10 in year one that totals **$14.97bn**, of which $13.45bn is payments to
people already retired.

The **disability term** is a flat 2.5% of active payroll added every year. It is not
connected to any disability population — there isn't one in the model. The evidence
recorded in July 2026 is that it double-counts, because the retiree stream already
pays disability retirees; removing it moves the median first-year outflow across
plans from about 6% above what plans actually paid to a fraction of a percent above.
That median masks real variation between plans, and the term is left switched on
pending a decision.

---

## 7. The asset stage

Now the randomness (`asset_simulation.py:392-430`).

**Assets are split into two buckets.** Everything risky — public equity, private
equity, real estate, hedge funds, commodities, alternatives, "other" — is one
bucket, and the rest is the other. CA10's reported allocation makes that **87.4%
risky, 12.6% safe**.

**Returns.** The risky bucket earns inflation plus a 7.5% premium with 20% standard
deviation. The safe bucket earns the risk-free rate — inflation plus 1%, so 3.75%
for CA10 — with **zero** volatility. Bonds cannot lose money in this model.

**One shared market history.** A single 34 × 10,000 matrix of standard normal draws
is generated from seed 123 and **every plan in a run uses the same one**. Simulation
column 4,712 is the same sequence of good and bad years for all 40 plans. This is
what makes cross-plan aggregates meaningful: a bad path is bad for everyone at once,
exactly as a real market downturn would be. It is also what makes the joint-failure
analysis possible at all.

**The roll-forward**, one year at a time:

```
assets[t+1] = max( assets[t] × (1 + return[t]) − outflow[t] + contribution[t] , 0 )
```

**The contribution rule is a single line and deserves attention**
(`asset_simulation.py:418`):

```
contribution = 0 if funded ratio > 1 else cash_inflows[t]
```

If the plan is underfunded it contributes what stage one said it would. If it is
overfunded it contributes **nothing**. There is no other behaviour: no catch-up when
funding falls, no gradual return, no amortisation. (An amortisation branch exists in
the code but is switched off in every run to date.)

**The floor at zero is what "exhaustion" means.** Once assets hit zero they are
clamped there. The plan is not modelled as borrowing or defaulting; the fund simply
holds nothing, and benefits above contributions are implicitly being paid from
somewhere outside the model. Checked across all 40 plans in `20260731_1`, **no path
ever recovers** once it hits zero: 0 recoveries out of 132,127 exhausting paths.

### For CA10

Starting from $257.5bn, identical in all 10,000 paths, and running to 2056:

| | |
|---|---|
| 5th percentile of final assets | **$0** (exhausted) |
| Median | $349.6bn |
| 95th percentile | $7,819bn |
| Probability of exhausting by 2056 | **0.337** |

That spread — zero to nearly eight trillion — is the compounding of a 20% annual
standard deviation over 34 years on an 87% equity allocation. The upper tail should
be treated with care: contributions stop above full funding but nothing else ever
happens, so a fortunate plan accumulates without limit, with no sponsor ever
spending, refunding or improving benefits out of a surplus.

---

## 8. What comes out, and its shape

Per plan, per run:

| Output | Shape | Random? |
|---|---|---|
| `AAL` | 35 × 10,000 | **No** — one column repeated |
| `cash_inflows`, `cash_outflows`, `NormalCost` | 35 × 10,000 | **No** — one column repeated |
| `Assets` | 35 × 10,000 | **Yes** |
| `MainRes` / `RetRes` (per tier) | 35 × 1 each | No |

The liability matrices are stored 10,000 columns wide purely so the arithmetic
lines up with assets; they carry one distinct column of information.

**The two sides do not have the same length**, which trips people up. The liability
loop fills 34 rows (2022–2055) and never writes the 35th, which is exactly zero for
all 40 plans. The asset loop fills all 35 (2022–2056). So asset exhaustion can be
measured one year further out than anything requiring a funded ratio.

---

## 9. Nine things that surprise people

1. **Only investment returns are random.** Everything demographic is a single
   deterministic path.
2. **Wages, benefits and cash flows are identical in all 10,000 simulations.**
3. **The liability is a closed group; the cash-flow projection is not.** Different
   questions, deliberately.
4. **Only the newest tier hires.** Older tiers wind down.
5. **The workforce grows at exactly 1% a year in every plan**, with no data source.
6. **Nobody retires early and nobody becomes disabled**, structurally.
7. **Overfunded plans stop contributing entirely** and there is no rule that ever
   restarts them.
8. **Exhausted plans never recover** — verified, not assumed.
9. **There is no funding policy.** Contributions are a fixed share of payroll. Every
   contribution-policy question therefore requires a new run, not a re-analysis.

---

## 10. Where each piece lives

| What | Where |
|---|---|
| Loading inputs, building the population, tiers | `engine/run_plan.py` |
| Band-to-single-year expansion | `engine/bucketfill.py` |
| The yearly update rules, liability, normal cost | `engine/core.py` |
| PPD fallback chains, inactive scaling | `engine/functions.py` |
| Every per-plan exception, with its reason | `settings/plan_settings.py` |
| The stochastic asset stage | `asset_simulation.py` |
| Scenario variants | `scenarios.py` |

Nothing in `Analysis/` shares code with any of it — the analysis layer only ever
reads saved outputs.
