"""
Per-plan settings — every decision that applies to one plan rather than all of them.

**This is the only place such decisions belong.** They used to be scattered through
the 658-line engine file, two of them buried in the middle of executable code where
nobody would find them. If you are adding a plan-specific rule, add it here.

Each non-default entry carries its reason inline. The evidence behind them is in
`Documentation/states_track_context.md`.
"""

# ---------------------------------------------------------------------------
# 1. WHICH DATA SHEETS EACH PLAN USES         (inherited from the R implementation)
# ---------------------------------------------------------------------------
# Nine booleans per plan, in the fixed order the R scripts used. `True` means read
# the plan's own sheet from its workbook; `False` means fall back to the shared
# tables in `Data/Common/states/default_assumptions.xlsx`.
#
#   position:  1          2        3        4          5           6           7           8       9
#   sheet:     ageservice retdist  wagerel  mortality  wagegrowth  withdrawal  retirement  refund  disability
#
# Two of these are never read for ANY plan, whatever the flag says:
#   - `wagegrowth` (5): wage growth comes from the PPD scalar chain instead.
#   - `disability` (9): the flat term in section 4 is used instead. Note this means
#     position 9 is inert — the disability SWITCH is section 4, not this flag.
#
# 33 plan-sheets hold the plan's own data but are set False, so the shared table is
# used anyway. That is deliberate and predates this project; see the register.
AVAILABLE_DATA = {
    "AZ06":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "AZ127": [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "CA10":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "CA111": [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "CA144": [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "CA43":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "CA97":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "CA98":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "DC20":  [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "FL26":  [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "GA27":  [True , True , True , False, True , False, False, False, False],   # TTTFTFFFF
    "GA28":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "IL32":  [True , True , True , True , True , False, True , False, False],   # TTTTTFTFF
    "IL33":  [True , True , True , False, True , True , True , False, False],   # TTTFTTTFF
    "IL34":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "IN37":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "LA44":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "LA130": [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "LA163": [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "ME47":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "MI53":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "MO175": [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "ND82":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "NJ71":  [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "NJ73":  [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "NM74":  [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "NY78":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "NY83":  [True , True , True , False, True , True , False, False, False],   # TTTFTTFFF
    "OH88":  [True , True , True , True , True , False, False, False, False],   # TTTTTFFFF
    "OK134": [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "OR91":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "PA92":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "PA93":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "RI96":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "SC99":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "SC100": [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "TX108": [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
    "MA50":  [True , True , True , True , True , False, False, False, False],   # TTTTTFFFF
    "MA51":  [True , True , True , True , True , True , False, False, False],   # TTTTTTFFF
    "MO64":  [True , True , True , True , True , True , True , False, False],   # TTTTTTTFF
}


# ---------------------------------------------------------------------------
# 2. CONTRIBUTION RATES: plans whose PPD rate comes out missing
# ---------------------------------------------------------------------------
# For these, if the rate computed from the PPD is NaN, it is recomputed from the
# contribution dollars over the model's own payroll instead.
CONTRIB_RATE_NA_CHECK = {"AZ127", "CA144", "CA98", "IL32", "IN37", "LA130", "LA44"}


# ---------------------------------------------------------------------------
# 3. CONTRIBUTION RATES: plans measured against the model's own payroll
# ---------------------------------------------------------------------------
# Normally the rate is contributions / PPD `payroll` ("covered payroll"). For the
# plans below it is contributions / the payroll the engine builds for itself.
#
# FL26 only, on documentary evidence from its own FY2017 valuation report:
#   p.6  the report values the defined benefit Pension Plan, and its rates "are then
#        combined with contribution rates from the defined contribution FRS
#        Investment Plan to create blended proposed statutory employer contribution
#        rates."
#   p.9  "the payroll on which UAL Cost rates are determined is higher, and includes
#        the payroll of DROP"  [against a payroll figure for non-DROP actives]
#
# So FRS sets rates on a base spanning DROP participants and a DC plan this model
# does not represent. Applying that rate to our narrower workforce collected 63% of
# actual. Measured against the model's own payroll its implied total rate reads
# 20.8% against its own stated actuarial rate of 19.3%, versus 13.0% before.
#
# DELIBERATELY PER-PLAN. The same change across all 40 was tested over two full runs
# and rejected - no net gain on the independent metric. See
# `_ARCHIVE/superseded_2026-07-30/contribution_rate_denominator_test/OUTCOME.md`.
CONTRIB_RATE_MODEL_PAYROLL = {"FL26"}


# ---------------------------------------------------------------------------
# 4. THE DISABILITY TERM
# ---------------------------------------------------------------------------
# The engine adds `DisabilityPayoutRate` x active payroll to outflows every year.
# `True` applies it; `False` drops it for that plan.
#
# Evidence (2026-07-30) that this is additive on top of people already being paid:
# `beneficiaries_tot` scales the retiree population and `BeneficiaryBenefit_avg`
# prices it, and across 34 of the 35 plans publishing a membership breakdown,
# service + disability + survivor retirees sum to exactly 1.000 of
# `beneficiaries_tot`. So disability retirees are already inside the retiree stream.
# Removing the term moves first-year outflows from 6.5% above what plans actually
# paid to 0.6% above.
#
# LEFT ON EVERYWHERE, deliberately. Turning it off entirely would mean NO member
# ever becomes disabled across the 35-year projection, because the engine moves
# actives only into retirement and has no disability stock. So the term is
# duplication in year one and possibly the only representation of disability by year
# thirty. Neither setting is right; the proper fix is to model disability as a real
# decrement, which is engine work.
#
# To test the sensitivity, prefer `--disability-rate 0` on the command line, which
# switches it off for every plan at once without editing this file.
APPLY_DISABILITY_TERM = {
    "AZ06":  True,
    "AZ127": True,
    "CA10":  True,
    "CA111": True,
    "CA144": True,
    "CA43":  True,
    "CA97":  True,
    "CA98":  True,
    "DC20":  True,
    "FL26":  True,   # no PPD membership breakdown; behaves like the confirmed group on the outflow test
    "GA27":  True,
    "GA28":  True,
    "IL32":  True,   # no PPD membership breakdown; behaves like the confirmed group
    "IL33":  True,
    "IL34":  True,
    "IN37":  True,
    "LA44":  True,
    "LA130": True,   # removing the term moves it AWAY from actual, unlike the confirmed group
    "LA163": True,
    "ME47":  True,
    "MI53":  True,
    "MO175": True,
    "ND82":  True,
    "NJ71":  True,
    "NJ73":  True,
    "NM74":  True,
    "NY78":  True,   # no PPD membership breakdown; behaves like the confirmed group
    "NY83":  True,
    "OH88":  True,
    "OK134": True,
    "OR91":  True,   # no PPD membership breakdown; behaves like the confirmed group
    "PA92":  True,
    "PA93":  True,   # membership components do NOT sum to 1, unlike the other 34 - see the register
    "RI96":  True,
    "SC99":  True,
    "SC100": True,
    "TX108": True,
    "MA50":  True,
    "MA51":  True,
    "MO64":  True,
}


# ---------------------------------------------------------------------------
# 5. SOURCE-DATA OVERRIDES
# ---------------------------------------------------------------------------
# Where a published PPD value is wrong and we substitute a corrected one. Keyed by
# (plan, fiscal year) so an override never silently applies to another year.
#
# MI53 fy2022: `ActiveSalary_avg` is published as 5.32 ($000s). The same plan's
# `ActiveSalaries / actives_tot` gives 54.32, and those two agree to two decimals in
# every other year (2021: 51.16/51.15, 2023: 56.23/56.24). 2022 is the only year out
# of line, and it is the year this model runs. Correcting it moved MI53's liability
# gap from -30.5% to -11.9%.
SALARY_OVERRIDE = {("MI53", 2022): "ActiveSalaries/actives_tot"}


# ---------------------------------------------------------------------------
# 6. WORKBOOK READ QUIRKS
# ---------------------------------------------------------------------------
# Plans whose `retdist` sheet has an extra header row before the data.
RETDIST_SKIPROWS = {'MI53': 1}
