# States Track — working context

**Created:** 2026-07-29. **Scope:** the 40 state plans and the working paper built
on them. Companion to `working_context.md` (the chronological log across all
tracks) and `project_context.md` (durable observed facts). Analysis and paper
framing are decided with Niccolo and are not recorded here in advance.

Written to be read without the code open: each item says what the input is and
what it drives before saying what is wrong with it.

## WHERE THIS STANDS — read this first (2026-07-31)

**The inputs are settled.** Everything below in this file is the evidence trail. If
you are picking this up cold, read this section, then `## Decisions taken`, then the
`## Assumption and limitation register`. The dated sections are the working record
and can be read on demand.

### The state in one paragraph

The model runs all **40** state plans (was 37). The engine has been corrected in
several places, the per-plan decisions are consolidated in
`Code/python/settings/plan_settings.py`, and `Code/python/` was restructured so
`engine/` is the model and `reference/` is the older verified lineage. The current
results run is **`20260731_1`**, produced 2026-07-31 and the first run to reflect
the current code. Analysis is the live work.

### What changed this session, in order

1. **Three plans admitted** — MA50, MA51, MO64 — taking coverage from 37 to 40.
2. **PPD refreshed** to the July 2026 download, files renamed `ppd-data-latest_2023.xlsx` (older) and `ppd-data-latest_072026.xlsx` (current). Base year stays **2022**.
3. **`LinearFill` corrected.** The inherited within-band weight mixed units, made the tilt depend on plan size, and could divide by ~zero — it produced negative retiree headcounts for 3 plans and cells of ±200,000 people for OK134. Replaced with a weight normalised around 1 whose tilt is derived per band from the neighbouring bands. The old version is kept as `LinearFill_incorrect`, which `Code/R/cluster_code_2022/` still calls so that lineage reproduces its original results.
4. **MI53's 2022 average salary** corrected (published 5.32, should be 54.32) — its liability gap moved from -30.5% to -11.9%.
5. **MA51's employer rate set to zero**, consistently with excluding state appropriations everywhere.
6. **FL26 contribution-rate exception** applied, on documentary evidence from its own valuation report.
7. **Disability double-count established** and made switchable, but **left ON**.
8. **Code restructured**, which exposed a silent path bug that had changed MA51's liability by 0.7% with no error.

### Runs on disk

`20260610_1` (37 plans, old engine) · `20260610_2` (scenario demo) ·
`20260730_1` (40 plans, pre-correction) · `20260730_2` (LinearFill corrected) ·
`20260730_3` (superseded) · `20260730_4` (rejected experiment) ·
**`20260731_1` — current**.
What each contains: `Results/Runs/README.md`.

### The run that made `20260731_1` current (2026-07-31)

Produced with the standard command, at `--parallel 6` rather than 20 — the machine
used was a 12-logical-core laptop with about 2.7 GB of memory free, not the desktop
the 20-process figure was set for. Parallelism does not affect results; the seed and
simulation count are what matter, and both were unchanged.

**Verified against `20260730_3` across every parquet array of all 40 plans: 39 plans
bit-identical at maximum absolute difference exactly 0.0, FL26 alone changed** — so
the pair isolates FL26's contribution-rate exception exactly, as predicted. FL26's
exhaustion probability moves **0.3801 -> 0.2399**, matching the figure measured in
the archived denominator experiment, and its year-0 liability moves **-0.057%**,
which is the refund channel and inside its documented range. Run is structurally
complete: 40/40 plan folders, 80 pickles, 320 parquet files, 80 logs.

### THE IMMEDIATE NEXT STEP

**The analysis**, which lives in **`Analysis/results.ipynb`** and opens on the newest
run automatically.

```powershell
cd "...\Code\python"
python run_simulation.py --plans all --stage both --fast --num-sim 10000 --run-tag YYYYMMDD_N --parallel <cores> --workers 1 --seed 123
```

### What is open, in rough priority order

| # | Item | State |
|---|---|---|
| 1 | **The analysis.** The paper's exhibits, what it argues, which figures carry the thesis | Live work from 2026-07-31, on `20260731_1`. Decided with Niccolo, not by proposal. |
| 2 | **The 13 plans whose modelled liability is >10% from reported** | MI53 and OK134 largely explained. The rest unexamined. Note Niccolo does not treat closeness to actuarial figures as a goodness measure. |
| 3 | **Disability term** — currently ON, evidence says it double-counts for 34 of 40 | One flag flips it: `--disability-rate 0`. Worth running both as a stated sensitivity. |
| 4 | **11 of the 14 switched-off retirement sheets** unchecked against their valuation reports | Switches stay off; 3 checked, all confirm the structural reason. |
| 5 | **PA93 and LA130** — the disability evidence does not hold for them | Unexplained. |
| 6 | **NY78 and ND82** wage relativities average 0.906 and 0.974 rather than 1 | Property of the source workbooks, not our code. Unresolved. |
| 7 | **Scenario layer** — built, parked, never run at scale | `scenarios.py` + `scenario_launcher.ipynb`. Step 0 is a `--compact` output mode; payloads are 0.5-1 GB each. |

---

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

## DONE 2026-07-30 — the PPD file is now dated, and the July download is live

The engine had been reading a file called `ppd-data-latest.xlsx`, a name that says
nothing about which download it is. Both vintages now carry their date, and every
reference points at one of them explicitly.

| File | Coverage | Who reads it |
|---|---|---|
| `ppd-data-latest_2023.xlsx` | fiscal years to **2023**, 228 plans/year | `Code/R/cluster_code_2022/` (38 scripts) — the frozen path that reproduces the validated run |
| `ppd-data-latest_072026.xlsx` | fiscal years to **2024**, 253 plans/year | the Python engine, the analysis module, `Code/R/cluster_code_2022_072026/` (38 scripts), and the four PPD-reading helpers in `Code/R/Common_Code/` |

The July download arrived as a CSV in a non-standard text encoding. It was converted
once to the workbook form the engine expects, keeping the sheet name
`ppd-data-latest` so no sheet references had to change. **Conversion verified:** all
26 fields the engine reads are identical after the round trip, 7,325 rows x 272
columns preserved, and all 40 modelled plans present at fiscal 2022. The CSV is kept
alongside and is gitignored.

The R side was handled by copying the cluster folder rather than editing it in
place, so `cluster_code_2022/` still points at the May file and still reproduces
what was validated, while `cluster_code_2022_072026/` is the current-data twin.

**Note on the two naming conventions.** They are deliberately different, because we
know different things about the two files. `20260730_1` on the newer one is its actual
download date. **The older file's download date is not known** — Niccolo recalls it
being around 2023, and the local file timestamp is a OneDrive sync artefact (several
unrelated files carry the identical timestamp), so it is not evidence of anything.
It is therefore named `2023`, after the last fiscal year it covers — the one
property verifiable from the file itself. Read that as coverage, not as a download
date.

**This changes results.** The July file restates 24 of the fiscal-2022 values the
model consumes, almost all retiree counts and average benefits — ME47 -16.4% on
retiree count with +19.6% on average benefit, MO175 -14.5%/+17.0%, and smaller
moves for CA144, FL26, LA163, MO64, LA130. These are CRR revisions and were adopted
deliberately (see Decisions taken). Nothing has been re-run.

---

## CORRECTION APPLIED 2026-07-30 — LinearFill's within-band weight

**This is a correction to inherited code, not a modelling assumption.** The
formula came with the original R implementation and was taken to be right. It is
not. Every result the project has produced to date, including `20260610_1` and
`20260730_1`, was computed with the defective version.

### What was wrong

`LinearFill` splits a five-year age band into single years. Its weight was

```
Share = GroupCount/(N*M) + Slope * age
```

which subtracts an age in years from a headcount per cell. Three consequences:

1. **Mixed units** — the difference of a count and an age has no meaning.
2. **Size-dependent tilt** — because the headcount sits inside the weight, a band
   holding 20,000 people came out almost flat (0.1% tilt) while a band holding 500
   came out at 17%. A plan's age profile must not depend on how large the plan is.
3. **Centred on zero instead of on 1** — the weights average
   `GroupCount/N - mean age`, so they straddle zero. Their sum, used as the
   normaliser, is `GroupCount - (sum of the ages in the band)`. When a band holds
   about that many people the normaliser approaches zero, the division explodes,
   and either side of that point the tilt silently reverses direction.

Each band has its own danger point — the sum of the five ages it covers, so 210 for
40-44 up to 485 for 95-99. A band holding roughly 200-600 people is at risk. Both
extremes are safe, which is why this survived: very large bands give near-uniform
positive weights, very small bands give near-uniform negative weights that cancel
in the normalisation. Only the middle breaks.

**Measured on the 40 plans:** three produced negative retiree headcounts — OK134
(worst cell -8,778), LA163 (-30), SC99 (-30). OK134's 75-79 band held 385.004
people against an age-sum of 385, so the normaliser was 0.004 and the band was
filled with about +/-200,000 people in a plan with 4,242 retirees. Band totals
still reconciled because the positives and negatives cancel, so no aggregate check
ever flagged it. A one-person PPD revision moved that plan's liability by 56%.

The active side (`Slope = +1`) **cannot** hit the singularity — it adds an age
instead of subtracting one, so all weights stay positive. Confirmed: zero negative
cells on the active side under either version. The size-dependent tilt still
applied there.

### What it is now

A perturbation around 1, driven only by position in the band:

```
u = (k-1)/(N-1)                position, 0 -> 1 across the band
w = 1 + s * (1 - 2u)           s > 0 declines with age, s < 0 rises
```

All weights strictly positive, so no cell can go negative, and they sum to
exactly `N`, so the normaliser is a constant that can never approach zero.

**`s` is taken from the data, not set by hand.** The neighbouring bands already
say how fast the population is changing: if the 75-79 band holds 385 people and
80-84 holds 223, the population is falling by a factor 0.58 per band, and the
slope inside the band should be consistent with that. Where the population is
still *rising* — the young retiree bands, as people retire into them — the slope
inside the band rises too.

```
r = geometric mean of the available neighbour ratios
q = r ** ((N-1)/N)             the first-to-last ratio implied inside the band
s = (1-q)/(1+q)                clipped to +/-0.9 so weights stay positive
```

Edge bands use their single neighbour; isolated or empty bands get `s = 0`, an
even split. `Slope` stays in the signature for compatibility but no longer sets
the direction — the data does.

### Why not a fixed constant

Three readings were compared before choosing, and all three say no single
constant is right:

| Reading | Population-weighted tilt |
|---|---|
| What the ORIGINAL formula was effectively assuming | **+0.0009** (i.e. an even split), while individual bands ranged **-0.95 to +1.38** |
| What the DATA implies | **-0.010** (also ~even), unweighted median +0.098, IQR -0.25 to +0.18 |
| A hand-set constant (the first attempt used 0.10) | arbitrary — nothing supports it |

So the old formula was, in aggregate, doing an even split — but erratically, with
sign flips and blow-ups band to band. And the data has real structure that a
single constant cannot represent: bands below the population peak should rise,
bands above it should fall. A fixed positive tilt gets the young bands backwards.

Deriving it per band costs nothing, needs no parameter, and is the honest version
of what "linear fill" was always trying to do.

### Verification, all 40 plans, both call sites

| | Inherited | Corrected |
|---|---|---|
| Plans with negative retiree headcounts | **3** | **0** |
| Plans with negative active headcounts | 0 | 0 |
| Totals preserved vs the inherited version | — | **40/40** |

Mean retiree age change: **median 0.011 years**, 90th percentile 0.031, and
**10.4 years for OK134** — the broken one. Mean active age change: median 0.029
years, max 0.082.

Note how small that is. Because the derived tilt reproduces what the old formula
was *effectively* doing for healthy plans, the 39 sound plans move about a
hundredth of a year — roughly ten times less than the hand-set 0.10 would have
moved them. The correction is almost entirely confined to the plan that was
broken.

R and Python produce identical output (declining bands 234.1255, 217.0628,
200.0000, 182.9372, 165.8745 in both; rising bands 64.6562 ... 95.3438).

### DECISION 2026-07-30 — direction of the within-band slope comes from the data

**Flagged for the coauthor discussion. This is the one point where the correction
deliberately departs from what the inherited code intended, so it should be raised
explicitly rather than presented as a bug fix.**

**What the original intended.** Decoded from the code: the base term
`GroupCount/(N*M)` is exactly an even split, and the function is named `LinearFill`
against a sibling `ConstantFill`. So the intent was *an even split plus a linear
adjustment in age*, with the direction fixed by the caller — `Slope = +1` for
actives (rising with age), `Slope = -1` for retirees (declining). That intent is
sound and the correction keeps it. The only structural change is that the
adjustment now **multiplies** the even share instead of being **added** to it as an
absolute number of years, which is what removes the unit mismatch, the dependence
on plan size, and the vanishing normaliser.

**Where we depart.** The original hardcoded the direction: every retiree band
declines with age, in every plan, always. We take the direction from the
neighbouring bands instead. Measured across all 40 plans:

| | |
|---|---|
| Populated retiree bands | 438 |
| Bands where the data agrees they decline | 242 |
| **Bands that actually rise** | **196 — 44.7%** |
| Plans with at least one rising band | **40 of 40** |
| Median share of a plan's retirees in a rising band | **47.7%** |

This is structural, not noise. A retiree population climbs from about age 50 to a
peak near 65-70 as members retire into it, then falls as they die. Forcing a
decline everywhere gets the whole pre-peak half backwards — for OK134 the tilt is
negative for every band below 65-69 and positive above it, and 65-69 is exactly
where its population peaks.

**The consequence Niccolo identified, confirmed empirically.** Forcing a decline
inside every band while the band *totals* are rising produces a sawtooth: the
profile falls across a band, then jumps up at the boundary into the larger next
band, then falls again. Measuring the age-to-age step, within bands versus across
band boundaries:

| Plan | Version | Within-band step | Step at a boundary | Ratio |
|---|---|---|---|---|
| CA10 | inherited | 0.02% | 66.6% | **4,200x** |
| CA10 | corrected | 13.1% | 24.6% | 1.9x |
| TX108 | inherited | 0.02% | 59.4% | **2,940x** |
| TX108 | corrected | 14.9% | 22.2% | 1.5x |
| FL26 | inherited | 0.01% | 49.2% | **6,240x** |
| FL26 | corrected | 8.8% | 19.1% | 2.2x |
| OK134 | inherited | 1.5% | 64.0% | 42x |
| OK134 | corrected | 11.1% | 11.1% | **1.0x** |

The inherited version was effectively a **staircase** — almost perfectly flat
inside each band (0.01-0.02% steps) with cliffs of 50-67% between them. The
corrected version spreads that change across the band, so the boundary step becomes
comparable to an ordinary within-band step. For OK134 it is indistinguishable.

**What to raise with the coauthor.** That we now let the data set the direction of
the within-band slope rather than asserting a universal decline; that this is the
only intentional departure from the inherited method; and that the alternative —
keeping the fixed direction and taking only the magnitude from the data — was
considered and rejected because it reintroduces the sawtooth for roughly half the
retiree population. It is a one-line change if the decision goes the other way.

### Where it is applied

Both languages keep the inherited version under the name `LinearFill_incorrect`,
unchanged, with the explanation attached — nothing deleted.

| File | What happened |
|---|---|
| `Code/python/bucketfill_cf_model.py` | `LinearFill_incorrect` added (inherited weight), `LinearFill` corrected |
| `Code/R/Common_Code/bucketfill_cf_model.R` | same, in the one shared file |
| `Code/R/cluster_code_2022/*.R` (38) | call sites changed to `LinearFill_incorrect` — **behaviour unchanged**, this lineage still reproduces exactly what it always produced |
| `Code/R/cluster_code_2022_072026/*.R` (38) | unchanged; they call `LinearFill`, which is now the corrected one |

Both lineages source the same shared file, so isolating the two versions means
two functions in one file rather than two files. An earlier attempt used a second
file plus 38 repointed `source()` lines; that was replaced with this, which is
cleaner and leaves the reproduction path explicit in the code rather than in a
folder name.

### Consequence for existing results

`20260610_1` and `20260730_1` both carry the defective version. OK134's numbers in both are
unusable. LA163 and SC99 are mildly affected. The other 37 plans are affected only
to the extent of the size-dependent tilt, which is worth about a tenth of a year of
mean age.

---

## Minor, checked 2026-07-30: do the workbook share sheets sum to 1?

Raised because the fill totals did not always match the PPD headcount. It is
rounding, not a defect.

Retiree shares sum to exactly 1 for **36 of 40** plans; the four that miss are IL33
(0.9969), MA50 (0.9978), RI96 (0.9995) and MA51 (0.9996). Active shares are exact
for **37 of 40**, worst miss 0.0003 (MI53).

The largest consequence is IL33's modelled retiree headcount sitting 0.31% below
its PPD count. That is published percentages not quite totalling 100, well inside
any tolerance that matters, and it behaves identically under both versions of
`LinearFill`. Recorded, no action.

---

## 2026-07-30 — the 072026 run completed, and it exposed a real bug in LinearFill

**Run status: complete and clean.** 40/40 liability outputs, 40/40 asset outputs,
40/40 parquet bundles, `plan_year=2022`, `num_sim=10000`, market seed 123, common
shocks on for every plan, zero NaNs in any Assets matrix, and no errors in any of
the 80 logs. All three input guards fired on exactly the plans they were meant to
and on no others.

This session's fixes did what they were meant to. MA51 moved from -79.8% to -21.9%
against its reported liability once the benefit-relativity column was rebuilt; MA50
sits at +4.3% and MO64 at +24.0%. 21 of the 37 plans common to both runs are
bit-identical to `20260610_1`; the 16 that moved did so because of the July PPD's
restated values.

### The bug: `LinearFill` can produce negative retiree headcounts

**What raised it.** OK134's modelled liability fell from $6.87bn to $3.04bn between
the two runs — from +134.5% against reported to +3.7%. Chasing that down: the two
runs are exactly reproducible, running current code against the old PPD reproduces
$6.87bn exactly, and **every derived scalar is identical between the two files
except `beneficiaries_tot`, which changed from 4,242 to 4,241.** One retiree.

A one-person change cannot move a liability by 56%, so this is not data.

**The mechanism.** `LinearFill` (`Code/python/bucketfill_cf_model.py`) distributes a
bucketed count across single ages using

```
Share  = GroupCount / (N*M) + Slope * age
sharesum = sum(Share)                       # = GroupCount - sum(ages in the band)
Expanded = Share * GroupCount / sharesum
```

On the retirement path `Slope = -1`, so the formula **subtracts an age from a
headcount** — two different units — and `sharesum` is `GroupCount` minus the sum of
the five ages in the band. When a band's headcount happens to land near that sum,
`sharesum` approaches zero and the division explodes.

OK134's 75-79 band is almost exactly on it. Sum of ages 75..79 = 385:

| `beneficiaries_tot` | band headcount | sharesum | resulting age cells |
|---|---|---|---|
| 4,242 | 385.004 | **+0.004** | -201,115 to +201,269 |
| 4,241 | 384.913 | **-0.087** | -8,778 to +8,932 |

In a plan with about 4,200 retirees, the model was placing ±200,000 people in
individual age cells, with large positives and negatives that nearly cancel. The
band totals still come out right because of the renormalisation, so nothing looks
wrong at the aggregate level — but the age *distribution* inside the band is
meaningless, and the liability is computed off that distribution.

**Blast radius, measured across all 40 plans at fiscal 2022:** three produce
negative retiree headcounts — **OK134** (most negative cell -8,778, severe),
**LA163** (-30) and **SC99** (-30, both mild). The other 37 are clean, though
several sit close enough to the boundary to be one data revision away from it
(ND82, NJ71, CA98, AZ127, MA50 all have a band within about 35 of zero).

**Consequences to be clear about.** OK134's long-standing +134.5% gap was this bug,
not its data. Its new +3.7% is **not** a fix — it is the same bug landing at a less
extreme point on the same discontinuity, and its number is still built on a broken
age distribution. Any result for OK134 should be treated as unusable until this is
resolved. LA163 and SC99 are mildly affected.

**Not fixed, deliberately.** `LinearFill` is shared by every plan and is a faithful
translation of the R reference implementation, so the same behaviour exists in R.
Changing it alters retiree distributions for all 40 plans, which is a model-equation
change and needs an explicit decision rather than a quiet patch.

---

## 2026-07-30 — input-sanity sweep on 20260730_2: two real problems found

Asked whether anything in the results makes us suspicious of the inputs. Method:
compare the model's FIRST projected year against what the PPD says each plan
actually paid and received in 2022. Those actuals are independent of the model's
machinery, so a large gap points at an input rather than at the projection.

### Finding 1 — the model misses state contributions, and it hits the three riskiest plans

The engine builds contributions from `contrib_EE_regular + contrib_ER_regular`.
Plans funded by a state appropriation record that money in `contrib_ER_state`
instead, and the engine never sees it. Share of each plan's ACTUAL total
contributions currently captured:

| | |
|---|---|
| Captures more than 95% | 28 of 40 |
| Captures less than 95% | **12 of 40** |
| Captures less than 50% | **5 of 40** |

**The overlap with the risk ranking is the problem.** The three riskiest plans in
the run are exactly three of the worst-captured:

| Plan | P(exhaust by 2056) | Contributions captured | Missing per year |
|---|---|---|---|
| **NJ73** New Jersey Teachers | **0.978** (riskiest) | 17.9% | $4.19bn |
| **IN37** Indiana Teachers | **0.961** | 12.1% | $1.55bn |
| **IL34** Illinois Teachers | **0.941** | 16.9% | $5.87bn |

Between them **$11.6bn a year of state contributions is invisible to the model.**
Their position at the top of the risk ranking is very likely an artifact of that,
not a finding about those plans.

Also affected: MA51 27%, AZ127 30%, RI96 59%, OK134 65%, TX108 68%, CA10 71%,
ME47 73%, LA130 85%, MA50 90%.

**Proposed fix, tested:** read `contrib_ER_tot` instead of `contrib_ER_regular`.
It is the sum of regular, state and other, and never exceeds `contrib_tot`, so
there is no double-counting risk.

| | Median capture | Below 95% | Below 50% |
|---|---|---|---|
| Now (`ER_regular`) | 0.983 | 12 | 5 |
| With `ER_tot` | **0.999** | **5** | **0** |

Residual after the change: RI96 at 0.59 and LA130 at 0.85, whose shortfall is on
the employee or "other" side and needs a separate look. **Not implemented — this
materially lowers risk for the three headline plans and is a decision to take
deliberately.** Note the existing MA51 fallback does not catch these, because it
only fires when `contrib_ER_regular` is *empty*; NJ73, IN37 and IL34 have small
but non-zero values there.

### Finding 2 — MI53's average salary is wrong in the PPD by a factor of about twelve

`ActiveSalary_avg` for Michigan Public Schools is **$5,318**. Its own `payroll`
divided by its own `actives_tot` gives **$64,181**. Every other plan sits between
$52,000 and $90,000, and for most of them the stated and implied figures agree to
within a few percent.

It cannot be the headcount instead: at $5,318 average salary, MI53's $9.96bn
payroll would need 1.87 million active members against the 155,229 reported.

This explains MI53's standing as the **worst negative liability gap in the study**
(-30.5% against reported): the model scales every active member's wage off that
figure, so its whole active liability is built on salaries a twelfth of their true
size. It also explains its funded-ratio gap of +28pp.

**Not fixed** — needs a decision on whether to override the PPD value with
`payroll / actives_tot`, and whether to apply that rule generally.

### Finding 3 — FL26's payroll and average salary disagree with each other

Stated `ActiveSalary_avg` $54,709; `payroll / actives_tot` implies $87,360. An
internal inconsistency in the PPD row rather than an error we introduced, but the
model uses the stated figure, so FL26's payroll comes out at 63% of its reported
payroll. Worth a look, lower priority than the two above.

### What came back clean

The model's first-year benefit outflow runs a median 9% above what plans actually
paid in 2022, range 0.82x to 1.49x. That is the expected direction, since the
model's outflow includes refunds and death benefits alongside retiree payments.
No plan looks wrong on this measure. Discount rates, inflation, exhaustion
probabilities and asset shapes all sit in plausible ranges with nothing pinned at
an extreme.

---

## 2026-07-30 — follow-up on the three input findings

### Finding 1 (REFRAMED): state contributions are not the same as employer contributions

An earlier version of this note treated the two as interchangeable and concluded
from TX108 that the exclusion was an artifact. **That conclusion was wrong**, and it
was wrong because of the conflation. Correct distinction:

- **Employer contribution** — the entity that employs the members paying for their
  pensions. A labour cost, not a subsidy, even when that employer is a government.
- **State contribution** (`contrib_ER_state`) — a state paying into a plan whose
  employers are *other* entities, typically school districts. That is an external
  transfer, and excluding it is exactly what a study of unsubsidised fund dynamics
  would want.

**10 of 40 plans receive a state contribution**, and the composition matters:

| Plan | State share of all contributions | Who employs the members |
|---|---|---|
| IN37 Indiana Teachers | 87.9% | school districts — **external subsidy** |
| IL34 Illinois Teachers | 83.1% | school districts — **external subsidy** |
| NJ73 New Jersey Teachers | 82.1% | school districts — **external subsidy** |
| AZ127 AZ State Corrections Officers | 69.7% | **the state itself — employer money** |
| MA51 Massachusetts Teachers | 64.3% | school districts — **external subsidy** |
| OK134 Oklahoma Police | 34.6% | municipalities — **external subsidy** |
| CA10 California Teachers | 28.8% | school districts — **external subsidy** |
| ME47 Maine State and Teacher | 27.5% | mixed |
| TX108 Texas Teachers | 24.1% | school districts — **external subsidy** |
| MA50 Massachusetts SRS | 3.1% | **the state itself — employer money** |

So the current exclusion is **defensible for 7 or 8 of the 10** and questionable for
**AZ127** and **MA50**, where the state is the employer and the money is a labour
cost rather than a transfer. TX108 does not settle anything against the principle —
Texas Teachers are employed by districts, so excluding the state share there is
consistent with it.

Whether it was *intended* is still unrecorded: the original R reads the two fields
with no comment, and no document states a rationale. But the effect lines up with
the principle for most affected plans.

**The consequence for the risk ranking flips.** If excluding state money is
deliberate, then NJ73, IN37 and IL34 topping the ranking is not an artifact — it is
the finding that those three plans cannot survive on employer and employee
contributions alone and depend on continuing state subsidy. That is a substantive
result, not a bug.

### Finding 2 (CORRECTED TWICE): MI53's 2022 average salary has a dropped digit

Two earlier readings of this were wrong and are recorded so the reasoning is
traceable: first "wrong by a factor of twelve", then "the value is monthly". The
time series settles it.

`ActiveSalary_avg` normally equals `ActiveSalaries / actives_tot` exactly. For MI53:

| Year | stated `ActiveSalary_avg` | `ActiveSalaries / actives_tot` |
|---|---|---|
| 2019 | 46.15 | 46.15 |
| 2020 | 48.35 | 48.35 |
| 2021 | 51.16 | 51.15 |
| **2022** | **5.32** | **54.32** |
| 2023 | 56.23 | 56.24 |
| 2024 | 59.02 | 59.02 |

Every year agrees to the second decimal except 2022, where **54.32 is recorded as
5.32** — a dropped leading digit, in the one year we run. It is not a monthly
figure: monthly would be 63.82, and the surrounding years progress smoothly through
54.32. The earlier "monthly" reading only looked plausible because 5.318 x 12 lands
near `payroll / actives_tot`, which is the wrong comparison — `payroll` is a
different field (see Finding 3).

**Correct value: 54.32**, from `ActiveSalaries / actives_tot`, consistent with every
neighbouring year. Not yet applied.

### Finding 3: FL26 is a denominator mismatch, and it affects six plans

The engine computes contribution rates as `contributions / payroll`, then applies
those rates to a payroll it constructs itself as `actives_tot x ActiveSalary_avg`.
That constructed figure equals the PPD's **`ActiveSalaries`** field — which is a
different, narrower quantity than **`payroll`** for some plans.

For FL26: `payroll` $38.68bn, `ActiveSalaries` $24.22bn. The rate is calculated on
the larger base and applied to the smaller one, so the plan collects **63%** of the
contributions intended. The gap is definitional and persistent, widening from 1.45x
in 2018 to 1.68x in 2024 — FRS's covered payroll spans a broader population than
its valuation actives (it separately reports 32,150 DROP members).

Six plans disagree by more than 10%: MI53 12.07x (the monthly issue above),
FL26 1.60x, CA10 1.11x, IN37 1.10x, NJ73 0.88x, NY78 0.84x.

**Fix available:** use `ActiveSalaries` as the rate denominator so numerator and
denominator describe the same population. It is populated for all 40 plans and its
ratio to the engine's constructed payroll has a median of 1.000.

**None of the three is implemented.** All change results, and two of them change
the risk ranking.

---

## DECISIONS 2026-07-30 (evening): state money, MI53 salary, and the payroll question

### DECIDED — state contributions stay excluded, and MA51's employer rate is zero

10 of 40 plans receive money recorded in `contrib_ER_state`. The engine has always
dropped it and **that behaviour is kept deliberately.** The distinction being drawn
is between a contribution owed under the employment contract and an appropriation a
legislature makes to keep a fund solvent; the second is not part of the fund's own
dynamics, which is what this study is about.

Recorded honestly as an **assumption, not a discovery**: nothing in the PPD or in
any project document states the original intent, the original R simply reads the
two fields, and the PPD codebook labels these variables by *who paid*
(`contrib_ER_state` = "State Employer Contributions", a sub-item of employer
contributions) rather than by *why*. Establishing the economic character of each
plan's state money would mean reading its funding statute, which has not been done.

**The fallback added earlier today is removed.** It fired for MA51 alone and handed
it $2.1bn of Commonwealth appropriation — exactly the money every other plan has
excluded. MA51's `contrib_ER_regular` is empty because its *entire* employer
contribution is a state appropriation, so under this rule **its employer
contribution rate is zero.** It still runs. MA51 keeps its **employee** contributions, which are 27.3% of its total
contributions and 11.6% of payroll; it loses only the employer side. So it is not
left with nothing — it becomes a plan whose entire *employer* contribution is a
state appropriation. Its risk should rise from the 0.005 it showed while receiving
that money, but by how much is a matter for the run, not for assertion here.

### DECIDED — MI53's 2022 average salary is overridden

Published as 5.32 (thousands). Its own `ActiveSalaries / actives_tot` gives 54.32,
and those two agree to two decimals in every other year (2021: 51.16 / 51.15;
2023: 56.23 / 56.24). Replaced with 54.32, printed at run time, revertible by
deleting one block.

**Effect, measured:** MI53's liability moves from $68.16bn to **$86.51bn**, and its
gap against the reported figure from **-30.5% to -11.9%** — no longer the worst
negative outlier in the study.

### The payroll-denominator question, decomposed

The engine measures the contribution rate against the PPD's **covered payroll** and
then charges it against **its own projected payroll**. Splitting that gap into its
two possible sources settles what is actually fixable:

| Comparison | What it tests | Result |
|---|---|---|
| model payroll / (actives x avg salary) | does the engine's own wage machinery preserve total payroll? | **median 1.0000; only 5 of 40 outside 1%** |
| covered payroll / (actives x avg salary) | do the two PPD fields describe the same population? | median 1.0008 but **12 of 40 outside 5%**, range 0.84 to 1.60 |

**So the gap is overwhelmingly a PPD definitional matter, not a model artifact.**
For 35 of 40 plans the engine builds exactly the payroll implied by headcount and
average salary.

**SUPERSEDED 2026-08-04 — see the entry "The wage-relativity grids that do not
average to 1" below.** The count of two was wrong (there are seven), the direction
was wrong (four plans GAIN payroll, they do not all lose it), and "unambiguously
fixable" was wrong (for NY78 the workbook is right and the mismatch is a real
property of the source data). The original text follows for the record.

**What is unambiguously fixable (model side):** two plans lose payroll in the
engine's own construction — **NY78 at -9.4%** and **ND82 at -2.6%** — because their
wage-relativity matrix does not average to 1 across the active distribution.
Normalising that matrix is a small, self-contained correction with no data-source
question attached.

**What is a choice, not a bug (PPD side):** for the other 12 plans covered payroll
genuinely spans a different population from the valuation actives — FL26 at 1.60x
is the clearest, with 32,150 DROP members reported separately. Two defensible
positions: leave the rate measured on covered payroll (today's behaviour, so
first-year contributions are wrong by that ratio), or measure it against the
engine's own payroll (first-year contributions then equal what the plan actually
received, and scale with the projected workforce thereafter). The second is
self-consistent and gives a testable anchor; the first stays closer to the plan's
published contribution basis. **Neither is implemented.**

---

## 2026-07-30 — the payroll-denominator beta was TESTED. Recommendation: do not adopt.

Two full 40-plan runs, identical except for the denominator:
`20260730_3` production, `20260730_4` beta (`Code/python/beta/`, drift-checked).
Both clean: 40/40 outputs, no errors, all 40 confirmed running the intended engine.

Judged on metrics that do **not** rely on closeness to reported actuarial liability.

| Metric | Production | Beta |
|---|---|---|
| **1.** First-year contributions vs what the plan actually received | median 0.9997, within 5% for 27/40 | 1.0000, 38/40 |
| **2.** Implied contribution rate vs the plan's **own stated actuarial rate** | median gap **3.88pp**, mean 7.64pp, within 3pp for **17/38** | median gap **3.80pp**, mean **7.75pp**, within 3pp for **16/38** |
| **3.** First-year net cash flow (contributions − benefits) vs actual | median gap **25.8%**, within 10% for 8/40 | median gap **28.4%**, within 10% for 8/40 |
| **4.** Exhaustion probability | — | median change **−0.0001**; only **1 of 40** moves more than 0.05 |

**Metric 1 proves nothing** — beta is 1.000 by construction. It confirms the wiring.

**Metric 2 is the discriminating one and it does not discriminate.** Beta is
marginally better on the median, marginally *worse* on the mean, and worse on the
count within 3pp. Plan by plan it helps some and hurts others: FL26 improves from
6.3pp off to 1.5pp, CA10 from 7.4 to 4.4 — but MI53 worsens from 7.2 to 15.0,
CA111, OR91 and NY78 all worsen. No net gain.

**Metric 3 is slightly worse under beta.** Making contributions match actual does
not improve net cash flow, because the benefit side carries its own gap.

**So: do not adopt as a blanket change.** The evidence does not show the beta
denominator is more correct; it shows it is a different arbitrary choice that
happens to anchor one quantity.

### Two things the test did settle

**The refund channel is real but negligible.** The employee contribution rate does
feed `refund()` and therefore liabilities, as flagged — but measured, the AAL moves
by a median of 0.004% and at most 0.09%. Not a reason to avoid the change, and my
earlier concern about it was overstated.

**FL26 is a genuine single-plan case.** It is the only plan whose outcome moves
materially (exhaustion 0.380 -> 0.240) and the only one where beta is clearly
better on the independent metric (1.5pp off its stated rate versus 6.3pp). Its
covered payroll is 1.60x its active salaries and its production contribution rate
of 13.0% sits well below its own stated actuarial rate of 19.3%. Worth handling as
a plan-specific question rather than a global rule.

### A separate open question this surfaced

**Net cash flow is off by a median 25% in BOTH runs**, with only 8 of 40 within
10%. That is not about the denominator — it is present either way. The benefit side
runs about 9% above what plans actually paid and the contribution side has its own
definitional gaps. Worth a look on its own terms.

The beta is left in place, drift-checked, so this can be re-tested if the inputs
change. Nothing in production was altered.

---

## 2026-07-30 — the net-cash-flow gap traced: disability is being counted twice

The 25% net-cash-flow gap was **not** a second problem, and digging took about
twenty minutes rather than a session.

**Step 1 — the net gap is the outflow gap, magnified.** Contributions already match
what plans received (median ratio 0.9997). So the net gap in *dollars* is just the
outflow gap in dollars; expressing it over the much smaller net inflates the
percentage. Median outflow gap $210m, median net gap $162m, correlated 0.70. One
question, not two.

**Step 2 — the outflow gap is almost entirely the flat disability assumption.**
The engine adds `DisabilityPayoutRate = 0.025` of payroll to outflows every year.

| Model year-1 outflow vs what plans actually paid out | Median ratio |
|---|---|
| as the engine runs today | **1.0619** |
| with the disability term removed | **1.0006** |

Removing it takes the outflow from 6% high to **six hundredths of one percent** off.
The disability term accounts for a median 65% of the excess.

**Step 3 — why that is double counting.** The retiree population is scaled by
`beneficiaries_tot` and priced at `BeneficiaryBenefit_avg`. Checked across the 35
plans that publish the breakdown: **service + disability + survivor retirees sum to
exactly 1.0000 of `beneficiaries_tot`** (median), with disability retirees a median
3.3% of the total. So disability retirees are *already inside* the retiree stream
and are already being paid through it — and the engine then adds a further 2.5% of
payroll on top.

That the outflow lands within 0.06% of actual once the term is removed is
independent confirmation.

**Status: not changed.** Removing the term is a model-equation change affecting all
40 plans and needs an explicit decision. Worth noting it would *lower* outflows by
about 6% across the board, which lowers exhaustion risk everywhere — a level shift,
not a re-ranking.

Recorded as limitation **E4** territory: the 2.5% constant was always documented as
an assumption; what is new is the evidence that it is additive on top of an outflow
that is already correct.

### The denominator test is archived

`Code/python/beta/` is gone. It now lives at
`_ARCHIVE/superseded_2026-07-30/contribution_rate_denominator_test/` with an
`OUTCOME.md` recording that it was rejected and why, so the question is not
reopened from scratch. `run_simulation.py` is back to two engines, production and
the original reference. Verified: `--fast` selects production, no `beta` references
remain.

---

## 2026-07-30 — FL26: cause established from the plan's own valuation report

FL26's covered payroll is 1.60x its active salaries, and its modelled contribution
rate (13.0%) sits far below its own stated actuarial rate (19.3%). The FY2017 FRS
valuation report explains why, in its own words.

**Page 6:** the report values *"the defined benefit Florida Retirement System (FRS)
Pension Plan"*, and its rates *"are then combined with contribution rates from the
defined contribution FRS Investment Plan to create blended proposed statutory
employer contribution rates."* So FRS is two plans, and the statutory contribution
rates are blended across both.

**Page 9, decisive:** *"the payroll on which UAL Cost rates are determined is
higher, and includes the payroll of D[ROP]"* — and the payroll figure it quotes is
for *"non-DROP active Pension Plan members"*.

So FRS deliberately sets contribution rates on a **broader payroll base** than the
Pension Plan's active members: it adds DROP participants (32,150 reported
separately) and blends with the Investment Plan. Our model represents only the
Pension Plan's active members, so applying a rate calculated on the wider base to
the narrower population under-collects — which is exactly the 63% we measured.

**This is documented plan structure, not a data error**, and it is specific to
FL26 among the 40. It is the one plan where the archived denominator experiment was
clearly better on the independent metric: its implied rate lands at 20.8% against a
stated 19.3% (1.5pp off), versus 13.0% under production (6.3pp off), and its
exhaustion probability moves 0.380 -> 0.240.

**Proposed handling, not yet applied:** measure FL26's contribution rate against the
model's own payroll, as a documented per-plan exception with this evidence
attached — the same mechanism the archived experiment applied globally and which
the evidence rejected globally.

## 2026-07-30 — where the disability double count actually happens, line by line

`core.py` builds each year's outflow as **four** separate terms (lines 605-611):

```
COutflow = (RN x RB)  +  ref  +  dth  +  dis
            retirees     refunds  death   disability
```

**The first counting is inside `RN x RB`.** Those two come from
`Main_PensionModel.py` lines 455-456:

```
ret_num = retdist_col_B x beneficiaries_tot          -> RetirementNumber (RN)
ret_ben = retdist_col_F x BeneficiaryBenefit_avg     -> RetirementBenefit (RB)
```

`beneficiaries_tot` is **every** beneficiary the plan pays. Verified across the 35
plans publishing a breakdown: service + disability + survivor retirees sum to
exactly 1.0000 of it, disability retirees being a median 3.3%. And
`BeneficiaryBenefit_avg` is the average benefit across that same whole group. So
`RN x RB` already pays every disability retiree on the books.

**The second counting is the `dis` term**, line 608:

```
dis = (active payroll) x DisabilityPayoutRate      # 0.025
```

2.5% of the active payroll, added on top, every year.

**A nuance worth keeping.** The `dis` term may have been intended for a different
population — members who become disabled *in future*, who never enter `RN` because
the engine only moves actives into retirement via `RetirementRate`, never into a
disability stock. On that reading it is a crude stand-in for future disabilitants
rather than pure duplication.

But in the first projected year it is unambiguously additive on top of an outflow
that is already right: removing it moves the model from 6.2% above actual to 0.06%
above. Whatever it was meant to represent, at 2.5% of payroll it is roughly six
times the size of the gap it could legitimately fill.

**Not changed.** Any fix affects all 40 plans and would lower outflows about 6%
across the board.

---

## APPLIED 2026-07-30 — FL26 exception, and disability made a switchable lever

### FL26 contribution rates now measured against the model's own payroll

Applied as a **per-plan exception**, with FRS's own words quoted in the code beside
it. The same change applied to all 40 was tested and rejected; this one rests on
documentary evidence specific to FL26.

Effect: EE rate 0.0197 -> 0.0315, ER 0.1103 -> 0.1760. Implied total rate moves from
13.0% to 20.8% against FL26's own stated actuarial rate of 19.3%. Exhaustion
probability moves 0.380 -> 0.240 (measured in the archived experiment).

**Verified no spillover:** OK134 rerun is bit-identical to `20260730_3`, max
absolute difference 0.0 across AAL, cash flows and normal cost.

### Disability: answers to the two open questions

**Does it affect all plans the same way? No — and not in the way you would expect.**

*Is disability inside `beneficiaries_tot` everywhere?* 35 of 40 plans publish the
breakdown. **34 of those 35 have service + disability + survivors summing to 1.000**
of `beneficiaries_tot`, so the retiree stream is paying disability retirees.
**PA93 is the one exception** — its components do not sum to 1, so the argument is
not established for it. Five plans publish no breakdown at all and cannot be checked
directly: **FL26, IL32, LA130, NY78, OR91**.

*How big is the term, plan by plan?* It varies by nearly five-fold:

| | Share of first-year outflow |
|---|---|
| median | **5.1%** |
| range | **2.3% (CA144) to 11.1% (DC20)** |

Most affected: DC20 11.1%, TX108 9.0%, RI96 7.9%, CA111 7.9%, IN37 7.1%.
Least: CA144 2.3%, LA163 3.0%, LA44 3.3%, IL34 3.6%, CA97 3.6%.

**And it bears no relation to a plan's actual disability population.** Disability
retirees range from 0.4% to 10.4% of beneficiaries, and that is uncorrelated with
how hard the 2.5% term hits: IN37 has 0.4% disability retirees and a 7.1% outflow
impact, while CA144 has 10.4% and a 2.3% impact. The term scales with *payroll*, so
it lands hardest on plans with many actives relative to retirees — an artefact of
plan maturity, not of disability incidence.

### It is now a lever, not a hardcoded constant

`--disability-rate` on both the engine and `run_simulation.py`, default **0.025** so
behaviour is unchanged. `--disability-rate 0` switches the term off for a
sensitivity. No need to edit anything per plan.

Verified on OK134: year-one outflow falls 5.32% with the term off (159.5m -> 151.0m),
and its liability moves too, since outflows feed the liability calculation.

**Nothing is changed by default.** The double-count evidence is strong but removing
the term shifts every plan's outflows by 2-11%, so it stays a deliberate choice.

---

## 2026-07-30 — disability: per-plan switch built, and can the 6 unknowns be settled?

### The switch

`APPLY_DISABILITY_TERM` in `fast/Main_PensionModel.py`, sitting alongside
`CONTRIB_RATE_NA_CHECK` and `RETDIST_SKIPROWS` — the same per-plan-override pattern
already used elsewhere, so it lives where someone would look for it rather than
only on the command line.

**All entries are `True`, so behaviour is unchanged** (verified: OK134 bit-identical
to `20260730_3`, max difference 0.0). Setting a plan `False` drops its disability
term; verified this works (OK134 outflow -5.32%).

Two levers now, deliberately different in kind:
- `APPLY_DISABILITY_TERM[plan] = False` — a **statement about that plan**.
- `--disability-rate 0` — a **global sensitivity**, everything off at once.

Worth recording: `availableData` position 9 is nominally the disability slot, but it
has never been wired to anything — the disability *sheet* is read for no plan. This
switch governs the flat term, which is what actually runs.

### Can the six unverified plans be settled? Partly, and no runs are needed

The test: compare first-year outflow against what the plan actually paid, with and
without the term. If removing it moves a plan toward 1.00, the retiree stream was
already covering disability. This is computable from the existing run — the term is
just 0.025 x model payroll — so it needs no simulation.

| Group | Median with term | Median without | Closer without |
|---|---|---|---|
| 34 confirmed from the PPD breakdown | 1.0647 | **1.0062** | 22/34 |
| 6 unverified | 1.0540 | **0.9971** | 4/6 |

Per plan among the six:

| Plan | With | Without | Behaves like the confirmed group? |
|---|---|---|---|
| FL26 | 1.0804 | 1.0299 | yes |
| IL32 | 1.0896 | 1.0193 | yes |
| NY78 | 1.0574 | 0.9982 | yes |
| OR91 | 1.0506 | 0.9960 | yes |
| **LA130** | 1.0095 | 0.9705 | **no** — already near 1 with the term |
| **PA93** | 0.9237 | 0.8824 | **no** — already below 1, removing makes it worse |

**PA93 fails both tests independently** — it is also the one plan whose PPD
membership components do not sum to 1. Two unrelated signals agreeing is worth
noting.

**But the honest limit:** even among the 34 plans where we *know* disability sits
inside `beneficiaries_tot`, removing the term only improves the individual match for
22. The median moves decisively; individual plans are noisy, because benefit levels
and timing differ from actual for other reasons. **So this test has real power in
aggregate and weak power per plan.** It supports treating FL26, IL32, NY78 and OR91
like the rest, and flags LA130 and PA93 as different — but it cannot settle any
single plan on its own.

### The pending decision

Flipping the 34 confirmed plans to `False` is a real change: it lowers their
first-year outflows by 2-11% and therefore lowers exhaustion risk across the board.
The mechanism is built and the evidence is recorded; the flip itself is not made.

---

## 2026-07-30 — Python folder restructured, and a silent path bug it exposed

### The restructure

| Was | Now |
|---|---|
| `fast/Main_PensionModel.py` | `engine/run_plan.py` |
| `fast/core.py`, `fast/sim_params.py` | `engine/core.py`, `engine/params.py` |
| `bucketfill_cf_model.py`, `functions_cf_model.py`, `liability_cf_model.py`, `g.py` | `engine/bucketfill.py`, `engine/functions.py`, `engine/liability.py`, `engine/state.py` |
| `Main_PensionModel_original.py` | `reference/run_plan_original.py` |
| `config/plans_*.txt` | `settings/plans_*.txt` |
| six per-plan dicts scattered through a 658-line file | **`settings/plan_settings.py`** |

`fast/` was a misleading name — it stopped being "the fast option" when it became the
engine, while the loose modules beside it were equally part of the model.
`Main_PensionModel.py` suggested a main program, which it is not; `run_simulation.py`
is. `run_plan.py` says what it does.

`settings/plan_settings.py` now holds every per-plan decision in six commented
sections, each non-default entry carrying its reason. The nine-sheet availability
matrix inherited from R is written out with the sheet names above the columns and a
TTTF summary per row. Values were extracted programmatically from the engine and
asserted equal, not retyped.

### The bug this exposed — and how nearly it was missed

MA51's liability moved 0.7% after the restructure. Everything checked identical:
statement-level diffs of every moved file showed only import lines, `PlanParams`
fields and defaults matched, all core function sources matched, and hashing every
array entering the simulation — active matrix, wages, inactive, tier partitions, all
four decrement tables, annuity vector — showed **no difference at all**.

The cause was one line in what is now `engine/functions.py`:

```python
legacy_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', '..', 'Data', 'Common', 'states',
                           'PPD_planlevel_main.csv')
if not os.path.exists(legacy_file):
    return float('nan')          # <- silent
```

Correct at `Code/python/`, wrong one level deeper at `Code/python/engine/`, where it
resolved to `Code/Data/...`. The file was not there, so **the function returned NaN
and every fallback chain that reaches the legacy PPD failed quietly.** MA51's wage
growth fell through from the legacy 0.040 to `InflationAssumption_GASB` 0.025.

No error, no warning, a 0.7% liability change, and it would have been invisible
without a bit-identity check against a previous run.

**Fixed two ways:** the path now walks up until it finds a folder containing
`Data/Common/states`, so it no longer depends on how deep the file sits; and a
missing file now **raises** instead of returning NaN, because a broken path and a
plan legitimately absent from the legacy file should never look the same.

**Verified bit-identical to `20260730_3`** for MA51 and for every other plan whose
fallbacks reach that file — NJ71, NY78, PA92, LA130 — max absolute difference 0.0
across AAL, cash flows and normal cost.

**The lesson worth keeping:** moving a file can change results without changing a
line of logic, and a fallback that returns a quiet default will hide it. Any future
move of engine code should be followed by a bit-identity check, not a code review.

---

## The wage-relativity grids that do not average to 1 (established 2026-08-04)

**Recorded, deliberately not fixed.** The evidence says the collectors did their job
and that at least two different things are going on, so a blanket correction would
paper over both. Nothing here is a to-do; it is written down so it is not
rediscovered as a surprise and so it appears in any writeup describing how payroll
is built.

### What the input is, and what "averaging to 1" means

The `wagerel` sheet gives each age × service cell's salary **as a ratio to the
plan's average salary**. The engine multiplies that ratio by the PPD's
`ActiveSalary_avg` to get a dollar salary per cell, then builds payroll as the sum
over cells of headcount × cell salary.

Because it is a ratio to the plan's own average, the **headcount-weighted mean of
the grid should come out at exactly 1** — otherwise the payroll the engine builds
does not equal `actives_tot × ActiveSalary_avg`, which is what the PPD says the
payroll is. This matters because the whole model is built on shapes from the
workbooks scaled by totals from the PPD; a grid that does not average to 1 lets the
workbook set part of the *level*, which is supposed to come from the PPD alone.

### Measured across all 40 plans

29 of 40 are within 0.1% of 1. Seven are off by more than 1%, in both directions:

| Plan | Weighted mean | Payroll effect | Direction |
|---|---|---|---|
| **NY78** | 0.906 | **−$1.97bn a year** | builds 9.4% too little |
| ND82 | 0.974 | −$0.02bn | 2.6% too little |
| OK134 | 0.988 | −$0.004bn | 1.2% too little |
| GA27 | 1.012 | +$0.03bn | 1.2% too much |
| ME47 | 1.013 | +$0.03bn | 1.3% too much |
| **NJ71** | 1.082 | **+$1.00bn a year** | 8.2% too much |
| **NJ73** | 1.086 | **+$1.13bn a year** | 8.6% too much |

Net across all 40 it is $0.20bn on a $384bn base, so in aggregate it is nothing;
the two large cases sit in opposite directions and nearly cancel.

**Why it does not wash out within a plan.** Contributions are payroll × rate, so
they carry the error directly. Retiree benefits — the dominant outflow for a mature
plan — come from `BeneficiaryBenefit_avg`, not the wage grid, and are unaffected.
So the error passes almost undiluted into net cash flow. **NJ73 is the riskiest
plan in the study and is currently credited with 8.6% more contribution income than
its own headcount and average salary imply.**

*(MI53 appears to be off by 921% on this test. It is not: the engine uses its
corrected salary of 54.32 while `planinfo` still carries the published 5.32, and
54.32 / 5.32 = 10.21. A measurement artefact, not a data problem.)*

### Two distinct causes, established from the workbooks themselves

**NY78 — the workbook is right, and the mismatch is real.** Its `wagerel` sheet
carries the collector's own working block and, at cell M15, the note **"note
average salaries are only for full time/full-year"**. The relativity is built as
cell salary ÷ M28, where M28 = 80,951 is the plan's reported overall average. The
collector also computed, at B29, the headcount-weighted average implied by the
salary cells: `=SUMPRODUCT(B17:L27, ageservice!B2:L12)` = 73,374.88. And
**73,374.88 / 80,951 = 0.9064**, exactly the discrepancy measured from the run
outputs. A whole column of per-age-band differences sits beside it, from +16 at
ages 20–24 to −19,606 at age 70+, largest where part-time and short-service members
concentrate. So the salary table covers full-time, full-year employees while the
headcount table covers every active member. Two source tables, two populations,
measured and left visible at collection time.

**NJ71 and NJ73 — the workbook is internally consistent, so the gap arises
downstream.** Their relativity denominators *are* the weighted average:
`=B32/$B$43` for NJ73 where B43 is itself the SUMPRODUCT, and `=E44/$L$55` for
NJ71. By construction those grids average to exactly 1.0000 against their own
headcount weights. CA10, which passes cleanly, is built the same way. So their +8%
appears **after** the workbook, in the engine's own expansion of the 11 × 11 band
grids to 55 × 55 — most plausibly because `LinearFill` (headcounts) and
`ConstantFill` (wages) apply service-limit masking differently, so cells carrying
headcount in one grid are zeroed in the other and the effective weights shift.
**That mechanism is a hypothesis, not established.**

**The remaining four are unexplained.** ME47 has 94 SUMPRODUCT cells in a different
and messier arrangement; ND82's relativity points straight at the `ageservice`
sheet; OK134 and GA27 carry no self-check at all, GA27's values being hardcoded
with no formulas.

### Why nothing was changed

Normalising every grid to average 1 would make the engine internally consistent in
one line. It was rejected because it would treat opposite situations identically:
for NY78 it would overwrite a documented property of the source data, and for
NJ71/NJ73 it would hide what may be a defect in our own expansion code. The honest
position is that the collectors recorded what their sources said, and that at least
one of the seven cases points at us rather than at them.

**If this is ever picked up**, the order is: establish the `LinearFill` /
`ConstantFill` masking question first, because it is the one that could be ours and
could affect more than payroll; only then decide what to do about the rest.

---

## Assumption and limitation register — state track

**One place for everything embedded in the state model that is a choice, a
substitution, a known gap, or a structural limit.** Anything here can be revisited;
each row says how. Started 2026-07-30, consolidating findings previously scattered
across this file, `model_input_dictionary.md` and `project_context.md`. The city
track's equivalent is `Data Extraction/assumption_register.md`.

### A. Places the engine alters or substitutes an input at load time

| # | What happens | Which plans | Why | How to undo |
|---|---|---|---|---|
| A1 | The retiree benefit-relativity column is checked, and rebuilt as `col F / col B` when its headcount-weighted mean falls outside 0.75–1.35 | MA51 only (39 of 40 untouched) | MA51's column holds shares of total benefit dollars, not ratios to the average benefit, scaling its retiree benefits to about an eighth of true size | Return `rel` unchanged in `_check_benefit_relativity()`. Full description: `model_input_dictionary.md` §1.1 |
| A2 | A salary-by-age-and-service grid shorter than 11 age rows is padded with zero rows | MA50, MA51 | Their sheets stop at age 70; every full-length plan carries zeros in that row. R padded with "not available", which would spread through the wage matrix | Remove the `_pad_rows()` call |
| A3 | Employer contribution falls back to `contrib_ER_tot` / `contrib_ER_state` when `contrib_ER_regular` is empty | MA51 | Massachusetts Teachers is funded by a Commonwealth appropriation, not a payroll rate. Verified: PPD FY2018 $1.315bn against the report's stated FY18 appropriation of $1.303bn | Read `contrib_ER_regular` alone in `_employer_contrib()` |

All three print to run output when they fire, so a run log shows which plans were touched.

### B. Inputs we hold but deliberately do not use

| # | Input | Scale | What we use instead | Decided |
|---|---|---|---|---|
| B1 | The `wagegrowth` sheet | 37 plans hold plan-specific data | The PPD scalar chain (payroll growth, then wage inflation, then 2017, then inflation) | 2026-07-29, keep as is |
| B2 | The `disability` sheet | 3 plans hold real data | A flat 2.5% of payroll for every plan | 2026-07-29, keep as is |
| B3 | Plan-specific retirement rates | 19 plans | The shared default table | Switches stay off — see E1/E2 |
| B4 | Plan-specific mortality | 9 plans | The shared default table | As above |
| B5 | Plan-specific turnover | 3 plans (GA27, IL32, OH88) | The shared default table | As above |
| B6 | Plan-specific refund rates | 2 plans (FL26, IL34) | The shared default table | As above |

B3 to B6 total 33 sheet-instances, matching the count already in `project_context.md`.
Nothing here blocks a run; every one has a working fallback.

Also: IN37, ME47 and OR91 are switched to use their own mortality, but their sheets
contain the shared default table cell for cell. Same numbers either way, but the
record misstates provenance.

### C. Data older than the label it carries

| # | What | Label | Actual vintage |
|---|---|---|---|
| C1 | All nine distribution sheets | used in a 2022 run | FY2017 — the workbook filename is hard-coded `[PLAN]_2017.xlsx` |
| C2 | Percent male, percent married, survivor reduction, inactive scaling | `[PLAN]_2022` | FY2017 values, identical to the 2017 file for all 37 plans; relabelled, not recollected |
| C3 | Tier and benefit rules | `[PLAN]_2022` | Latest tier start date anywhere in the file is **2018-07-01**; nothing enacted since is represented |

Full per-input decomposition: `project_context.md` §3.1.

### D. Per-plan open items

| # | Plan | Item | Status |
|---|---|---|---|
| D1 | MA51 | Inactive scaling set to **0.0**, so the plan has no inactive members at all. Recorded identically in both `PPD_planlevel_main_updated.csv` and `inactive_supplement_2022.csv`, so it is a deliberate entry rather than a typo in one place — but no reason is recorded. A common-assumption substitute exists: the all-plan median inactive-to-active ratio is **0.116**, giving MA51 about 11,455 inactive members. This was **not** the cause of its bad liability — that was A1 | **DECIDED 2026-07-30: leave at 0.0.** It was entered deliberately in two places, the reason simply was not written down, and the impact is small. Recorded here as an assumption to revisit rather than a defect to fix |
| D2 | CA97 | Early-retirement ages `er4`, `er5`, `er6` are empty in the tier file | **RESOLVED 2026-07-30: not a problem.** The engine never consumes the early-retirement age at all. CA97's blanks are also in tiers 4-6, which are identical rows that collapse to one tier. *Wording corrected 2026-08-04:* an earlier version listed the per-tier loop as setting the *normal* retirement age alongside benefit factor, salary-averaging years, COLA, benefit cap and vesting, which implied `nr` is consumed while only `er` is dead. **Both are equally unused** — the loop assigns a value to a field nothing reads. The parameters the loop sets that actually drive the projection are benefit factor, vesting, salary-averaging years, benefit cap and COLA. See E6 |
| D3 | NY78 | No reported inactive-member count in any recent PPD year, so it silently uses the 2017 figure | Works as designed; recorded so it is visible |
| D4 | NJ71 | No inflation assumption at FY2022, so it falls back to the 2017 value of **3.5%**, noticeably above the 2–3% other plans use. Present at FY2023–24, so a year change would resolve it | Recorded; no action while we stay on 2022 |
| D5 | MO175, NM74 | No equity share at FY2023–24, needed to split assets between stocks and bonds | Only matters if the year changes |
| D6 | MA51 | The A1 repair has been checked for internal consistency only, **not** against MA51's valuation report | OPEN |

### E. Structural model limitations

| # | Limitation | Where the evidence is |
|---|---|---|
| E1 | **The engine holds one retirement grid per plan, and the source documents do not publish one.** 8 of the 14 affected plans checked; all 8 split their rates by tier, member class, sex, hire date, or across up to eight separate tables. Any single grid is a lossy collapse | The FLAG section below. Same issue as entry 1 of the city register |
| E2 | **Separately, ME47's collapse is systematically low** — it drops published age-45 and age-50 rates to zero and applies the lowest published rate flat across ages 55–64. Only ME47 has been examined this closely | As above |
| E3 | Workforce growth fixed at **1% a year for every plan**, no data source | `model_input_dictionary.md` §6 |
| E4 | Disability payout fixed at 2.5% of payroll; risk-free rate at inflation plus 1%; stock premium 7.5% with 20% volatility; horizon 35 years | As above |
| E5 | Tier-specific contribution rates exist in the tier workbook (`eecont` / `ercont`) but are **not consumed** — one plan-level rate is used | As above §4 |
| E6 | **CORRECTED 2026-08-04. No retirement age is used at all.** Both `er1`..`er6` (early) and `nr1`..`nr6` (normal) are read from the tier workbook into the parameter object and **never read back** — verified across every Python file, and in R the one line that would have used `RetirementStart` is commented out (`functions_cf_model.R:857`), so this was never a translation loss. Retirement is driven entirely by the age × service retirement-rate grid, which spreads retirement across ages, so the earlier claim that "no plan can retire early" was wrong. **What is actually missing is the benefit reduction**: the formula is `min(BenefitFactor × service, BenefitCap) × final average salary` at all five places it appears, with no age term, so a member the grid retires at 52 receives the same unreduced benefit as one retiring at 67. The *timing* of early retirement is representable through the grid; the reduction that should accompany it is not. Overstates liabilities by an unmeasured amount | `engine/core.py:80, 162, 234, 236, 565`; `engine/run_plan.py:255, 283` |

### F. Provenance gaps

| # | Gap |
|---|---|
| F1 | **DC20 and GA28**: the valuation report in the plan folder contains no retirement-rate table, so those workbooks' retirement sheets came from a document we do not hold and which is recorded nowhere. Established by a full page scan, not a keyword search |
| F2 | Six of the 14 switched-off retirement sheets remain unchecked: CA111, DC20, GA28, IL33, NM74, NY83 |
| F3 | No reason is recorded anywhere for the 2022 decision to switch off 14 plans' retirement sheets. E1 is an inference from the source documents, not a recovered rationale |
| F4 | **CONFIRMED DEAD 2026-07-30.** `inactive_supplement_2022.csv` is an *exact* duplicate of the `inactive_adj` column of `PPD_planlevel_main_updated.csv` — all 40 rows agree, zero disagreements — and it is referenced by **no code anywhere** in `Code/`. Nothing to fix numerically. It can be moved to `_ARCHIVE/` whenever convenient; left in place for now since it is harmless and tracked in git |

---

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
