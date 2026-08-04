"""
THE PRODUCTION ENGINE. Projects one plan's liabilities and cash flows.

Called per plan by ../run_simulation.py; not usually run by hand. Every per-plan
decision lives in ../settings/plan_settings.py, not here.

Differences vs reference/run_plan_original.py, the verified lineage it replaced:
  - No g module: all state in PlanParams dataclass.
  - Vectorized inner loops (UpdateEmployeeCount, DeathPay, ComputeAnnuity).
  - Parallel PVNC_Calc (ThreadPoolExecutor across 55 starting ages).
  - Parallel TotalLiabilities_Current (2 paths in parallel).
  - Identical data loading, identical pkl output format.

Usage:  python engine/run_plan.py <PLAN_ID> --run-tag YYYYMMDD_N
"""
import argparse
import os
import sys
import pickle
import time
from dataclasses import replace as dc_replace

import numpy as np
import pandas as pd
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.bucketfill import LinearFill, ConstantFill, ConstantFill_SepRate
from engine.functions   import (get_wage_growth_assumption, get_inflation_assumption,
                                   scale_inactive_members)
from engine.params import PlanParams
from settings.plan_settings import (AVAILABLE_DATA, APPLY_DISABILITY_TERM,
                                    CONTRIB_RATE_NA_CHECK, RETDIST_SKIPROWS,
                                    SALARY_OVERRIDE, CONTRIB_RATE_MODEL_PAYROLL)
from engine.core       import (mort_table_fast, calc_inactive_fast, create_tiers_fast,
                              compute_annuity, main_current_fast, main_ret_fast)

# ---------------------------------------------------------------------------
# Per-plan settings come from settings/plan_settings.py - see that file
# ---------------------------------------------------------------------------






DEFAULT_RUN_TAG  = None   # must be passed explicitly; see run_simulation.py
DEFAULT_PLAN_YEAR = 2022
DEFAULT_TIER_FILE = "planchanges_main_2022_clean.xlsx"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("plan")
    p.add_argument("--run-tag",   default=DEFAULT_RUN_TAG)
    p.add_argument("--plan-year", type=int, default=DEFAULT_PLAN_YEAR)
    p.add_argument("--tier-file", default=DEFAULT_TIER_FILE)
    p.add_argument("--date-run",  default=None)
    p.add_argument("--workers",   type=int, default=None,
                   help="Thread-pool workers for PVNC parallel (default: cpu_count)")
    p.add_argument("--disability-rate", type=float, default=0.025,
                   help="Disability payout as a share of active payroll (default 0.025). "
                        "Set 0 to switch the term off. See the note at DisabilityPayoutRate "
                        "below: the retiree stream already pays disability retirees, so this "
                        "term is additive on top of them. Provided as a sensitivity lever.")
    p.add_argument("--discount-override", type=float, default=None,
                   help="Replace the plan's GASB discount rate in AAL/PVNC computations "
                        "(e.g. an AAA yield for market-value liability scenarios)")
    return p.parse_args()


args      = parse_args()
plan      = args.plan
plan_year = args.plan_year

if plan not in AVAILABLE_DATA:
    raise ValueError(f"Plan '{plan}' not in AVAILABLE_DATA.")

availableData = AVAILABLE_DATA[plan]

script_dir  = os.path.dirname(os.path.abspath(__file__))         # Code/python/engine/
code_dir    = os.path.normpath(os.path.join(script_dir, '..', '..'))  # Code/
root_dir    = os.path.dirname(code_dir)                               # project root
common_dir  = os.path.join(root_dir, 'Data', 'Common', 'states')
if args.run_tag is None:
    raise SystemExit("--run-tag is required (convention: YYYYMMDD_N). "
                     "Normally you would go through run_simulation.py.")
run_tag     = args.run_tag
plan_folder = os.path.normpath(os.path.join(root_dir, 'Data', 'Plans', 'States', plan))
run_folder  = os.path.normpath(os.path.join(root_dir, 'Results', 'Runs', run_tag, plan))

file_name = f"{plan}_2017.xlsx"
np.random.seed(54848631)


def _s(df, col):
    return float(df[col].values[0])


def _pad_rows(mat, n_rows, what):
    """Pad a short bucket grid up to n_rows with zero rows.

    Added 2026-07-29. MA50 and MA51 stop their `wagerel` grid at age 70; every
    other plan runs to age 75, and in those plans that final row is all zeros.
    R's read_excel pads the absent row with NA (which would spread through the
    wage matrix); pandas silently returns a short array, which ConstantFill then
    leaves as zeros in the top age bin. Same values as pandas produced before,
    but now explicit and loud instead of a silent truncation.
    """
    if mat.shape[0] == n_rows:
        return mat
    if mat.shape[0] > n_rows:
        raise ValueError(f"{what}: got {mat.shape[0]} rows, expected at most {n_rows}")
    pad = n_rows - mat.shape[0]
    print(f"  NOTE: {what} has {mat.shape[0]} rows, expected {n_rows}; "
          f"padding {pad} trailing row(s) with zeros "
          f"(matches the all-zero final row every full-length plan carries)")
    return np.vstack([mat, np.zeros((pad, mat.shape[1]))])


def _check_benefit_relativity(rel, share, plan):
    """Validate (and if needed rebuild) the retiree benefit-relativity column.

    Added 2026-07-30. `retdist` column F must hold each retiree age band's average
    benefit DIVIDED BY the plan's overall average benefit, because the engine
    multiplies it by `BeneficiaryBenefit_avg`. A correct column therefore averages
    1.0 when weighted by the headcount shares in column B.

    Checked across all 40 state plans: 38 fall between 0.78 and 1.04 (nearly all
    exactly 1.000). MA51 alone sits at 0.1188 because its column holds each band's
    SHARE OF TOTAL BENEFIT DOLLARS instead — a different quantity. Dividing by the
    headcount share recovers a proper relativity (MA51: 0.9696).

    Warns loudly whenever the mean is off, and rebuilds the column only when the
    dollar-share reading demonstrably fixes it. To disable, return `rel` unchanged.
    """
    LO, HI = 0.75, 1.35
    r = np.asarray(rel, dtype=float).ravel()
    w = np.asarray(share, dtype=float).ravel()
    ok = (w > 0) & np.isfinite(r)
    if not ok.any() or w[ok].sum() == 0:
        return rel
    mean = float((r[ok] * w[ok]).sum() / w[ok].sum())
    if LO <= mean <= HI:
        return rel

    print(f"  WARNING: {plan} retdist benefit-relativity column averages {mean:.4f} "
          f"(headcount-weighted); a correct column averages 1.0.")
    with np.errstate(divide='ignore', invalid='ignore'):
        cand = np.where(w > 0, r / np.where(w > 0, w, np.nan), np.nan)
    if not np.isfinite(cand[ok]).all():
        print(f"           Could not rebuild it; leaving the column as published.")
        return rel
    cand_mean = float((cand[ok] * w[ok]).sum() / w[ok].sum())
    if not (LO <= cand_mean <= HI):
        print(f"           Dividing by the headcount share gives {cand_mean:.4f}, "
              f"still wrong; leaving the column as published.")
        return rel
    # carry the last populated band forward into the empty tail bands
    out = cand.copy()
    last = np.nan
    for i in range(len(out)):
        if np.isfinite(out[i]):
            last = out[i]
        else:
            out[i] = last if np.isfinite(last) else 0.0
    print(f"           The column holds SHARES OF TOTAL BENEFIT DOLLARS, not ratios "
          f"to the average benefit.")
    print(f"           Rebuilt as (column F / column B); it now averages "
          f"{cand_mean:.4f}. Empty tail bands carry the last populated value.")
    return out.reshape(np.asarray(rel).shape)


def _employer_contrib(planinfo, plan):
    """Employer contribution in PPD thousands, EXCLUDING state contributions.

    The engine has always read `contrib_ER_regular` only, so money a state pays
    into a plan on behalf of other employers (`contrib_ER_state`) never enters the
    projection. 10 of the 40 plans have such money; it is dropped for all of them.
    Decision 2026-07-30: keep that behaviour. The distinction being drawn is between
    a contribution owed under the employment contract and an appropriation the
    legislature makes to keep a fund solvent, and the second is not part of the
    fund's own dynamics. Recorded as an assumption, not a discovery — nothing in the
    PPD or in any project document states the original intent, and the PPD's own
    taxonomy splits these fields by who paid rather than by why.

    A brief fallback to `contrib_ER_tot` was added earlier on 2026-07-30 and is
    REMOVED here: it fired for MA51 alone and handed it $2.1bn of Commonwealth
    appropriation, which is precisely the money every other plan has excluded.

    MA51 therefore has an employer contribution of zero, because its entire employer
    contribution is a state appropriation. It keeps its EMPLOYEE contributions
    (27.3% of its total contributions, 11.6% of payroll) — only the employer side
    goes. To revert, return `contrib_ER_regular` and let NaN propagate.
    """
    v = _s(planinfo, 'contrib_ER_regular')
    if np.isnan(v):
        print(f"  NOTE: {plan} has no contrib_ER_regular. Its employer contribution is "
              f"entirely a state appropriation, which this model excludes by design, "
              f"so the employer contribution rate is set to ZERO.")
        return 0.0
    return v
    for alt in ('contrib_ER_tot', 'contrib_ER_state'):
        if alt in planinfo.columns:
            a = _s(planinfo, alt)
            if not np.isnan(a):
                print(f"  NOTE: contrib_ER_regular is empty; using {alt} = {a:,.0f}")
                return a
    return v


# ---- PPD and planinfo ----
ppid       = int(''.join(filter(str.isdigit, plan)))
plan_start = date(plan_year, 1, 1)
plan_id    = f"{plan}_{plan_year}"

planinfo_all = pd.read_excel(
    os.path.join(common_dir, 'ppd-data-latest_072026.xlsx'),
    sheet_name='ppd-data-latest', header=0)
planinfo = planinfo_all[
    (planinfo_all['ppd_id'] == ppid) & (planinfo_all['fy'] == plan_year)
].reset_index(drop=True)

PPD_all = pd.read_csv(os.path.join(common_dir, 'PPD_planlevel_main_updated.csv'))
PPD     = PPD_all[PPD_all['planid'] == plan_id].reset_index(drop=True)

# ---- Economic parameters ----
WageGrowth               = get_wage_growth_assumption(plan, planinfo)
discountrate             = _s(planinfo, 'InvestmentReturnAssumption_GASB')
if args.discount_override is not None:
    print(f"discount override: {args.discount_override} (plan GASB rate was {discountrate})")
    discountrate = args.discount_override
EmployeeContributionRate = _s(planinfo, 'contrib_EE_regular') / _s(planinfo, 'payroll')
EmployerContributionRate = _employer_contrib(planinfo, plan) / _s(planinfo, 'payroll')
Inflation                = get_inflation_assumption(plan, planinfo)
rf                       = 0.01 + Inflation
PopulationGrowth         = 0.01

# ---- Tier info ----
tier_file = (args.tier_file if os.path.isabs(args.tier_file)
             else os.path.join(common_dir, args.tier_file))
tierinfo_all = pd.read_excel(tier_file, sheet_name='in', header=0)
tierinfo     = tierinfo_all[tierinfo_all['planid'] == plan_id].reset_index(drop=True)

tier_rows = []
for i in range(1, 7):
    tier_rows.append({
        'startdate':     tierinfo[f'startdate{i}'].values[0],
        'benefitfactor': float(tierinfo[f'benefitfactor{i}'].values[0]),
        'vesting':       float(tierinfo[f'vesting{i}'].values[0]),
        'maxsal':        float(tierinfo[f'maxsal{i}'].values[0]),
        'yrsal':         float(tierinfo[f'yrsal{i}'].values[0]),
        'nr':            float(tierinfo[f'nr{i}'].values[0]),
        'er':            float(tierinfo[f'er{i}'].values[0]),
        'cola':          float(tierinfo[f'cola{i}'].values[0]),
    })
tier_info2  = pd.DataFrame(tier_rows).drop_duplicates().reset_index(drop=True)
num_tiers   = len(tier_info2)
COLA_c      = float(tier_info2['cola'].mean())

tier_serivce = []
for i in range(num_tiers):
    sd    = pd.to_datetime(tier_info2['startdate'].iloc[i]).date()
    weeks = (plan_start - sd).days / 7.0
    tier_serivce.append(int(round(weeks / 52.25)))

# ---- Tier-specific parameters ----
BenefitFactor_t    = {}
WageYears_t        = {}
COLA_t             = {}
BenefitCap_t       = {}
NyearFullBenefit_t = {}
RetirementStart_t  = {}
for i in range(1, 7):
    if i <= num_tiers:
        BenefitFactor_t[i]    = float(tier_info2['benefitfactor'].iloc[i - 1])
        WageYears_t[i]        = float(tier_info2['yrsal'].iloc[i - 1])
        COLA_t[i]             = float(tier_info2['cola'].iloc[i - 1])
        maxsal_i              = float(tier_info2['maxsal'].iloc[i - 1])
        BenefitCap_t[i]       = 100.0 if maxsal_i == -100 else maxsal_i
        NyearFullBenefit_t[i] = float(tier_info2['vesting'].iloc[i - 1])
        RetirementStart_t[i]  = float(tier_info2['nr'].iloc[i - 1])

# ---- Demographic data ----
# Height of every projection array: the base year plus 35 projected years, so the
# projection covers plan_year .. plan_year + 35 (2022-2057 at the default).
#
# Raised from 35 on 2026-08-04 (item A1). At 35 the liability loop filled only 34
# rows and the asset loop 35, so the two sides ran to different years and the
# horizon was one year shorter than the "35 years" it was described as everywhere.
# Both were corrected together: the loop bound in engine/core.py now fills every
# row, and this value now means what it appears to mean. The R lineage still uses
# 35 with the old loop, so R and Python outputs are no longer directly comparable
# until the same change is made there.
Nyear  = 36
NMonte = 1

Assets       = np.zeros((Nyear, NMonte))
Assets[0, :] = _s(planinfo, 'ActAssets_GASB') * 1000

pctmale  = _s(PPD, 'pctmale')
pct_mrg  = _s(PPD, 'pctmrg')
wid_red  = _s(PPD, 'reduct')

if availableData[0]:
    asy_employee = pd.read_excel(
        os.path.join(plan_folder, file_name), sheet_name='ageservice',
        usecols='B:L', skiprows=1, nrows=11, header=None).to_numpy(dtype=float)
else:
    asy_employee = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='ageservice', usecols='B:L', skiprows=1, nrows=11,
        header=None).to_numpy(dtype=float)
asy_employee = asy_employee * _s(planinfo, 'actives_tot')
active = LinearFill(asy_employee, Slope=1)

if availableData[2]:
    asy_wage = pd.read_excel(
        os.path.join(plan_folder, file_name), sheet_name='wagerel',
        usecols='B:L', skiprows=1, nrows=11, header=None).to_numpy(dtype=float)
else:
    asy_wage = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='wagerel', usecols='B:L', skiprows=1, nrows=11,
        header=None).to_numpy(dtype=float)

if (plan, plan_year) in SALARY_OVERRIDE:
    _pub = _s(planinfo, 'ActiveSalary_avg')
    _fix = _s(planinfo, 'ActiveSalaries') / _s(planinfo, 'actives_tot')
    print(f"  NOTE: {plan} fy{plan_year} ActiveSalary_avg published as {_pub:,.2f} "
          f"(thousands); replaced with {_fix:,.2f} from ActiveSalaries/actives_tot, "
          f"consistent with every neighbouring year.")
    _salary_avg = _fix
else:
    _salary_avg = _s(planinfo, 'ActiveSalary_avg')
# --------------------------------------------------------------------------
asy_wage    = _pad_rows(asy_wage, 11, f"{plan} wagerel B2:L12")
asy_wage    = asy_wage * _salary_avg * 1000
BaseWage_2d = ConstantFill(asy_wage)


if plan in CONTRIB_RATE_MODEL_PAYROLL:
    _mp = float((active * BaseWage_2d).sum())
    _ee_new = _s(planinfo, 'contrib_EE_regular') * 1000.0 / _mp
    _er_new = _employer_contrib(planinfo, plan) * 1000.0 / _mp
    print(f"  NOTE: {plan} contribution rates measured against the model's own payroll "
          f"({_mp:,.0f}) rather than PPD covered payroll "
          f"({_s(planinfo, 'payroll') * 1000:,.0f}), because this plan sets its rates on a "
          f"wider base (DROP + the DC Investment Plan) that this model does not represent. "
          f"EE {EmployeeContributionRate:.4f}->{_ee_new:.4f}, "
          f"ER {EmployerContributionRate:.4f}->{_er_new:.4f}")
    EmployeeContributionRate, EmployerContributionRate = _ee_new, _er_new
# ---------------------------------------------------------------------------

if plan in CONTRIB_RATE_NA_CHECK:
    if np.isnan(EmployeeContributionRate):
        EmployeeContributionRate = (_s(planinfo, 'contrib_EE_regular') * 1000.0
                                    / float((active * BaseWage_2d).sum()))
    if np.isnan(EmployerContributionRate):
        EmployerContributionRate = (_s(planinfo, 'contrib_ER_regular') * 1000.0
                                    / float((active * BaseWage_2d).sum()))

if availableData[6]:
    asy_retrate = pd.read_excel(
        os.path.join(plan_folder, file_name), sheet_name='retirement',
        usecols='Q:AA', skiprows=1, nrows=11, header=None).to_numpy(dtype=float) / 100.0
else:
    asy_retrate = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='retirement', usecols='B:L', skiprows=1, nrows=11,
        header=None).to_numpy(dtype=float) / 100.0
asy_retrate[asy_retrate < 0] = 0
RetirementRate = ConstantFill(asy_retrate, enforce_service_limit=False)

if availableData[7]:
    asy_refundrate = (
        pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='refund',
                      usecols='B:L', skiprows=1, nrows=11, header=None).to_numpy(dtype=float) * pctmale
        + pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='refund',
                        usecols='O:Y', skiprows=1, nrows=11, header=None).to_numpy(dtype=float) * (1.0 - pctmale))
else:
    asy_refundrate = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='refund', usecols='B:L', skiprows=1, nrows=11,
        header=None).to_numpy(dtype=float)
RefundRate = ConstantFill(asy_refundrate)

if availableData[5]:
    asy_seprate = (
        pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='withdrawal',
                      usecols='A:L', skiprows=0, nrows=12, header=None).to_numpy(dtype=float) * pctmale / 100.0
        + pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='withdrawal',
                        usecols='N:Y', skiprows=0, nrows=12, header=None).to_numpy(dtype=float) * (1.0 - pctmale) / 100.0)
    asy_seprate[0:12, 0] *= 100
    asy_seprate[0, 1:12] *= 100
else:
    asy_seprate = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='withdrawal', usecols='A:L', skiprows=0, nrows=12,
        header=None).to_numpy(dtype=float)
SeparationRate = ConstantFill_SepRate(asy_seprate)

if availableData[3]:
    mort_m = pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='mortality',
                            usecols='B:D', skiprows=1, nrows=4, header=0)
    mort_f = pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='mortality',
                            usecols='F:H', skiprows=1, nrows=4, header=0)
else:
    mort_m = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='mortality', usecols='B:D', skiprows=1, nrows=4, header=0)
    mort_f = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='mortality', usecols='F:H', skiprows=1, nrows=4, header=0)
mort_m.columns = mort_f.columns = ['Age', 'M', 'F']
mort_table     = pd.concat([mort_m, mort_f], ignore_index=True)
MortalityTable = mort_table_fast(mort_table, pctmale, employee_start=20)

if availableData[1]:
    retdist_skip = RETDIST_SKIPROWS.get(plan, 0)
    _num_share = pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='retdist',
                                usecols='B:B', skiprows=retdist_skip, nrows=16,
                                header=0).to_numpy(dtype=float)
    _ben_rel   = pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='retdist',
                                usecols='F:F', skiprows=retdist_skip, nrows=16,
                                header=0).to_numpy(dtype=float)
else:
    _num_share = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='retdist', usecols='B:B', skiprows=0, nrows=16,
        header=0).to_numpy(dtype=float)
    _ben_rel   = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='retdist', usecols='F:F', skiprows=0, nrows=16,
        header=0).to_numpy(dtype=float)

_ben_rel = _check_benefit_relativity(_ben_rel, _num_share, plan)
ret_num  = _num_share * _s(planinfo, 'beneficiaries_tot')
ret_ben  = _ben_rel   * _s(planinfo, 'BeneficiaryBenefit_avg') * 1000

RetirementNumber  = LinearFill(ret_num, Slope=-1, retirement=True)
RetirementBenefit = ConstantFill(ret_ben, retirement=True)

# ---- Settings that are choices rather than plan data ----
# Hoisted out of the PlanParams call below so the values that actually ran can be
# saved with the results. Before 2026-07-31 the disability rate was computed
# inline and never recorded anywhere: not in the saved payload, not in the run
# log. Two runs differing only in `--disability-rate` were therefore
# indistinguishable from their outputs, which is exactly the comparison the
# sensitivity is meant to support.
apply_disability_term = APPLY_DISABILITY_TERM.get(plan, True)
DisabilityPayoutRate = args.disability_rate if apply_disability_term else 0.0

# ---- Build base PlanParams ----
base_params = PlanParams(
    Nyear=Nyear, NMonte=NMonte,
    WageGrowth=WageGrowth, Inflation=Inflation,
    discountrate=discountrate, rf=rf,
    PopulationGrowth=PopulationGrowth, scaling=1.0,
    annuity_dr=rf,
    EmployeeContributionRate=EmployeeContributionRate,
    EmployerContributionRate=EmployerContributionRate,
    # Disability payout, as a share of ACTIVE payroll, added to outflows every year
    # (core.py `dis` term). Evidence recorded 2026-07-30: the retiree stream already
    # pays disability retirees — `beneficiaries_tot` provably contains them (service +
    # disability + survivors sum to exactly 1.0000 of it across the 34 of 35 plans
    # publishing a breakdown) and `BeneficiaryBenefit_avg` averages over that whole
    # group. Removing this term moves first-year outflows from 6.2% above what plans
    # actually paid to 0.06% above.
    # Kept at 0.025 so behaviour is unchanged; `--disability-rate 0` runs the
    # sensitivity. Note the term bears no relation to a plan's actual disability
    # population: it ranges from 2.3% to 11.1% of outflow across the 40 plans while
    # actual disability retirees range from 0.4% to 10.4% of beneficiaries, uncorrelated.
    DisabilityPayoutRate=DisabilityPayoutRate,
    refundReturn=rf,
    pct_mrg=pct_mrg, widow_reduct=wid_red,
    MortAdujst=1.0, pctmale=pctmale,
    SeparationRate=SeparationRate,
    RefundRate=RefundRate,
    RetirementRate=RetirementRate,
    MortalityTable=MortalityTable,
    # Tier fields filled per-tier below
    NyearFullBenefit=int(NyearFullBenefit_t[1]),
    RetirementStart=int(RetirementStart_t[1]),
)

# AnnuityVector uses mean COLA across tiers (same as original)
AnnuityVector = compute_annuity(COLA_c, base_params)
base_params   = dc_replace(base_params, AnnuityVector=AnnuityVector)

# ---- Inactive members ----
params_tier1 = dc_replace(base_params,
                           NyearFullBenefit=int(NyearFullBenefit_t[1]),
                           RetirementStart=int(RetirementStart_t[1]))
inactive = calc_inactive_fast(active, SeparationRate, RefundRate, MortalityTable, params_tier1)
inactive = scale_inactive_members(inactive, plan, planinfo, PPD)

tier_pairs = create_tiers_fast(active, inactive, num_tiers, tier_serivce)

def _fmt(s: float) -> str:
    return f"{int(s // 60)}m {s % 60:.1f}s" if s >= 60 else f"{s:.1f}s"

# ---- Main simulation ----
_t0 = time.perf_counter()
MainRes        = {}
setCurrentTier = False
for i in range(1, 7):
    if num_tiers >= i:
        if num_tiers == i:
            setCurrentTier = True
        p_tier = dc_replace(base_params,
                             COLA=COLA_t[i],
                             WageYears=int(WageYears_t[i]),
                             BenefitCap=BenefitCap_t[i],
                             BenefitFactor=BenefitFactor_t[i],
                             RetirementStart=int(RetirementStart_t[i]),
                             NyearFullBenefit=int(NyearFullBenefit_t[i]))
        act_i, inact_i = tier_pairs[i - 1]
        _ti = time.perf_counter()
        MainRes[i] = main_current_fast(act_i, inact_i, BaseWage_2d, p_tier,
                                        CurrentTier=setCurrentTier,
                                        n_workers=args.workers)
        print(f"  tier {i}/{num_tiers} done  ({_fmt(time.perf_counter() - _ti)})")
    else:
        MainRes[i] = [np.zeros(MainRes[1][k].shape) for k in range(5)]

_ti = time.perf_counter()
RetRes = main_ret_fast(RetirementNumber, RetirementBenefit,
                        dc_replace(base_params,
                                   COLA=COLA_t[num_tiers],
                                   BenefitFactor=BenefitFactor_t[num_tiers],
                                   NyearFullBenefit=int(NyearFullBenefit_t[num_tiers])))
print(f"  Main_Ret done  ({_fmt(time.perf_counter() - _ti)})")

# ---- Aggregate ----
cash_outflows = sum(MainRes[i][1] for i in range(1, 7)) + RetRes[1]
cash_inflows  = sum(MainRes[i][2] for i in range(1, 7))
NormalCost    = sum(MainRes[i][4] for i in range(1, 7))
AAL           = sum(MainRes[i][0] for i in range(1, 7)) + RetRes[0]

Model_AAL          = float(AAL[0, 0])
CAFR_AAL           = _s(planinfo, 'ActLiabilities_GASB') * 1000
Percent_difference = (Model_AAL - CAFR_AAL) / CAFR_AAL

Compare_Result = pd.DataFrame({'type': ['EAN'], 'model': [Model_AAL],
                                'cafr': [CAFR_AAL], 'dif': [Percent_difference]})

print(f"Model AAL : {Model_AAL:,.0f}")
print(f"CAFR  AAL : {CAFR_AAL:,.0f}")
# Echo the settings that are choices rather than data, so the log says what ran.
print(f"Settings  : PopulationGrowth={PopulationGrowth}, "
      f"DisabilityPayoutRate={DisabilityPayoutRate}"
      + ("" if apply_disability_term
         else f" (per-plan switch OFF; --disability-rate was {args.disability_rate})"))
print(f"Pct diff  : {Percent_difference:.4%}")

# ---- Save (identical structure to the reference runner) ----
os.makedirs(run_folder, exist_ok=True)
save_path = os.path.join(run_folder, f"{plan}_detAL_{run_tag}.pkl")
with open(save_path, 'wb') as fh:
    pickle.dump({
        'plan': plan, 'ppid': ppid, 'plan_id': plan_id, 'plan_year': plan_year,
        'run_tag': run_tag, 'Nyear': Nyear, 'NMonte': NMonte,
        'Assets': Assets, 'AAL': AAL, 'NormalCost': NormalCost,
        'cash_outflows': cash_outflows, 'cash_inflows': cash_inflows,
        'MainRes': MainRes, 'RetRes': RetRes,
        'Inflation': Inflation, 'rf': rf, 'discountrate': discountrate,
        'discount_override': args.discount_override,
        # Settings that are model choices, saved so a run describes itself.
        # These flow onward automatically: the asset stage starts its payload
        # from this dict, and write_parquet_bundle promotes any scalar into
        # scalars.parquet, so they reach the analysis layer without further
        # plumbing. `stock_premium` and `stock_vol` are already recorded inside
        # `scenario_json` and are not duplicated here.
        'PopulationGrowth': PopulationGrowth,
        'DisabilityPayoutRate': DisabilityPayoutRate,
        'disability_rate_requested': args.disability_rate,
        'apply_disability_term': apply_disability_term,
        'EmployeeContributionRate': EmployeeContributionRate,
        'EmployerContributionRate': EmployerContributionRate,
        'planinfo': planinfo,
        'Compare_Result': Compare_Result,
        'Model_AAL': Model_AAL, 'CAFR_AAL': CAFR_AAL,
        'Percent_difference': Percent_difference,
    }, fh)
print(f"Saved: {save_path}")
print(f"Total time: {_fmt(time.perf_counter() - _t0)}")
