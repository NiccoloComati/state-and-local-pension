"""
Generic pension model runner.
Usage:  python "Python Code/Main_PensionModel.py" <PLAN_ID>
Example: python "Python Code/Main_PensionModel.py" AZ06

Covers all 37 standard plans.  MA50 is a structural outlier and excluded.
"""
import argparse
import os
import sys
import pickle
import time
import numpy as np
import pandas as pd
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import g
from bucketfill_cf_model import (LinearFill, ConstantFill, ConstantFill_SepRate,
                                   MortTable, Calc_Inactive, CreateTiers)
from functions_cf_model import (get_wage_growth_assumption, get_inflation_assumption,
                                  scale_inactive_members, ComputeAnnuity,
                                  Main_Current, Main_Ret)

# ---------------------------------------------------------------------------
# Per-plan lookup tables  (sourced line-by-line from each R script)
# ---------------------------------------------------------------------------
# Sheets: 1=ageservice 2=retdist 3=wagerel 4=mortality 5=wagegrowth
#         6=withdrawal 7=retirement 8=refund 9=disability
AVAILABLE_DATA = {
    'AZ06':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'AZ127': [True,  True,  True,  False, True,  True,  False, False, False],
    'CA10':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'CA111': [True,  True,  True,  True,  True,  True,  False, False, False],
    'CA144': [True,  True,  True,  True,  True,  True,  True,  False, False],
    'CA43':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'CA97':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'CA98':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'DC20':  [True,  True,  True,  False, True,  True,  False, False, False],
    'FL26':  [True,  True,  True,  False, True,  True,  False, False, False],
    'GA27':  [True,  True,  True,  False, True,  False, False, False, False],
    'GA28':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'IL32':  [True,  True,  True,  True,  True,  False, True,  False, False],
    'IL33':  [True,  True,  True,  False, True,  True,  True,  False, False],
    'IL34':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'IN37':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'LA44':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'LA130': [True,  True,  True,  True,  True,  True,  True,  False, False],
    'LA163': [True,  True,  True,  True,  True,  True,  True,  False, False],
    'ME47':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'MI53':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'MO175': [True,  True,  True,  True,  True,  True,  True,  False, False],
    'ND82':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'NJ71':  [True,  True,  True,  False, True,  True,  False, False, False],
    'NJ73':  [True,  True,  True,  False, True,  True,  False, False, False],
    'NM74':  [True,  True,  True,  False, True,  True,  False, False, False],
    'NY78':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'NY83':  [True,  True,  True,  False, True,  True,  False, False, False],
    'OH88':  [True,  True,  True,  True,  True,  False, False, False, False],
    'OK134': [True,  True,  True,  True,  True,  True,  True,  False, False],
    'OR91':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'PA92':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'PA93':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'RI96':  [True,  True,  True,  True,  True,  True,  True,  False, False],
    'SC99':  [True,  True,  True,  True,  True,  True,  False, False, False],
    'SC100': [True,  True,  True,  True,  True,  True,  False, False, False],
    'TX108': [True,  True,  True,  True,  True,  True,  True,  False, False],
}

# 7 plans where R applies a payroll-based fallback when contribution rates are NA
# (R: if(is.na(EmployeeContributionRate)){ ... *1000 / sum(active*BaseWage[,,1]) })
CONTRIB_RATE_NA_CHECK = {'AZ127', 'CA144', 'CA98', 'IL32', 'IN37', 'LA130', 'LA44'}

# Plan-specific retiree-distribution reads from the R scripts.
# R MI53 uses range B2:B18 / F2:F18 with col_names=TRUE; the rest use B1:B17 / F1:F17.
RETDIST_SKIPROWS = {'MI53': 1}

DEFAULT_RUN_TAG = "062026"
DEFAULT_PLAN_YEAR = 2022
DEFAULT_TIER_FILE = "planchanges_main_2022_clean.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", help="Plan id, such as AZ06")
    parser.add_argument("--run-tag", default=DEFAULT_RUN_TAG)
    parser.add_argument("--plan-year", type=int, default=DEFAULT_PLAN_YEAR)
    parser.add_argument("--tier-file", default=DEFAULT_TIER_FILE)
    parser.add_argument("--date-run", default=None)
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
args = parse_args()
plan = args.plan
plan_year = args.plan_year

if plan not in AVAILABLE_DATA:
    raise ValueError(f"Plan '{plan}' not in AVAILABLE_DATA. "
                     f"Valid plans: {sorted(AVAILABLE_DATA)}")

availableData = AVAILABLE_DATA[plan]

# ---- Paths ----
script_dir  = os.path.dirname(os.path.abspath(__file__))
current_dir = os.path.normpath(os.path.join(script_dir, '..'))   # Code/
root_dir    = os.path.dirname(current_dir)                        # project root
common_dir  = os.path.join(root_dir, 'Data', 'Common', 'states')
run_tag     = args.run_tag

date_run  = args.date_run or f"{plan_year}"
plan_folder = os.path.normpath(os.path.join(root_dir, 'Data', 'Plans', 'States', plan))
run_folder  = os.path.normpath(os.path.join(root_dir, 'Results', 'Runs', run_tag, plan))

file_name = f"{plan}_2017.xlsx"

np.random.seed(54848631)

# ---- Scalar helper ----
def _s(df, col):
    return float(df[col].values[0])

# ---- PPD and planinfo ----
ppid      = int(''.join(filter(str.isdigit, plan)))
plan_start = date(plan_year, 1, 1)
plan_id   = f"{plan}_{plan_year}"

planinfo_all = pd.read_excel(
    os.path.join(common_dir, 'ppd-data-latest.xlsx'),
    sheet_name='ppd-data-latest', header=0)
planinfo = planinfo_all[
    (planinfo_all['ppd_id'] == ppid) & (planinfo_all['fy'] == plan_year)
].reset_index(drop=True)

PPD_all = pd.read_csv(os.path.join(common_dir, 'PPD_planlevel_main_updated.csv'))
PPD = PPD_all[PPD_all['planid'] == plan_id].reset_index(drop=True)

# ---- Global economic parameters ----
WageGrowth               = get_wage_growth_assumption(plan, planinfo)
discountrate             = _s(planinfo, 'InvestmentReturnAssumption_GASB')
EmployeeContributionRate = _s(planinfo, 'contrib_EE_regular') / _s(planinfo, 'payroll')
EmployerContributionRate = _s(planinfo, 'contrib_ER_regular') / _s(planinfo, 'payroll')
Inflation                = get_inflation_assumption(plan, planinfo)
rf                       = 0.01 + Inflation
PopulationGrowth         = 0.01
scaling                  = 1.0

# ---- Tier info ----
tier_file = (
    args.tier_file
    if os.path.isabs(args.tier_file)
    else os.path.join(common_dir, args.tier_file)
)
tierinfo_all = pd.read_excel(
    tier_file,
    sheet_name='in', header=0)
tierinfo = tierinfo_all[tierinfo_all['planid'] == plan_id].reset_index(drop=True)

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
tier_info2 = pd.DataFrame(tier_rows).drop_duplicates().reset_index(drop=True)
num_tiers  = len(tier_info2)

# R: round(as.numeric(difftime(plan_start, startdate, unit="weeks")) / 52.25, digits=0)
tier_serivce = []
for i in range(num_tiers):
    sd    = pd.to_datetime(tier_info2['startdate'].iloc[i]).date()
    weeks = (plan_start - sd).days / 7.0
    tier_serivce.append(int(round(weeks / 52.25)))
g.tier_serivce = tier_serivce

# ---- Simulation parameters ----
Nyear  = 35
NMonte = 1
g.Nyear  = Nyear
g.NMonte = NMonte

Assets    = np.zeros((Nyear, NMonte))
Assets[0, :] = _s(planinfo, 'ActAssets_GASB') * 1000

DisabilityPayoutRate = 0.025
refundReturn         = rf
annuity_dr           = rf
COLA_c               = float(tier_info2['cola'].mean())
pct_mrg              = _s(PPD, 'pctmrg')
widow_reduct         = _s(PPD, 'reduct')
RetirementMax        = 104
EmployeeStart        = 20;  EmployeeEnd  = 74
ServiceStart         = 1;   ServiceEnd   = 55
pctmale              = _s(PPD, 'pctmale')
MortAdujst           = 1.0

# Push non-contribution-rate globals to g
g.EmployeeStart          = EmployeeStart;  g.EmployeeEnd  = EmployeeEnd
g.ServiceStart           = ServiceStart;   g.ServiceEnd   = ServiceEnd
g.WageGrowth             = WageGrowth
g.discountrate           = discountrate
g.Inflation              = Inflation
g.rf                     = rf
g.PopulationGrowth       = PopulationGrowth
g.scaling                = scaling
g.pct_mrg                = pct_mrg
g.widow_reduct           = widow_reduct
g.pctmale                = pctmale
g.MortAdujst             = MortAdujst
g.DisabilityPayoutRate   = DisabilityPayoutRate
g.refundReturn           = refundReturn
g.annuity_dr             = annuity_dr

# ---- Tier-specific variables ----
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

# ---- Active employee data (B2:L12, col_names=F) ----
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

# ---- Wage data (B2:L12, col_names=F) ----
if availableData[2]:
    asy_wage = pd.read_excel(
        os.path.join(plan_folder, file_name), sheet_name='wagerel',
        usecols='B:L', skiprows=1, nrows=11, header=None).to_numpy(dtype=float)
else:
    asy_wage = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='wagerel', usecols='B:L', skiprows=1, nrows=11,
        header=None).to_numpy(dtype=float)
asy_wage = asy_wage * _s(planinfo, 'ActiveSalary_avg') * 1000
BaseWage_2d = ConstantFill(asy_wage)
BaseWage    = np.zeros((BaseWage_2d.shape[0], BaseWage_2d.shape[1], Nyear))
BaseWage[:, :, 0] = BaseWage_2d
g.BaseWage = BaseWage

# ---- Contribution rate NA fallback (R: if(is.na(...)){...*1000/sum(active*BaseWage[,,1])}) ----
# Applied only to the 7 plans whose R script contains this check.
if plan in CONTRIB_RATE_NA_CHECK:
    if np.isnan(EmployeeContributionRate):
        EmployeeContributionRate = (_s(planinfo, 'contrib_EE_regular') * 1000.0
                                    / float((active * BaseWage_2d).sum()))
    if np.isnan(EmployerContributionRate):
        EmployerContributionRate = (_s(planinfo, 'contrib_ER_regular') * 1000.0
                                    / float((active * BaseWage_2d).sum()))

# Push contribution rates to g (after NA-check so fallback values propagate)
g.EmployeeContributionRate = EmployeeContributionRate
g.EmployerContributionRate = EmployerContributionRate

# ---- Retirement rate (Q2:AA12 from plan; B2:L12 from default; col_names=F) ----
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
g.RetirementRate = RetirementRate

# ---- Refund rate (B2:L12 plan; B2:L12+O2:Y12 blended; col_names=F) ----
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
g.RefundRate = RefundRate

# ---- Separation rate (A1:L12 + N1:Y12 blended; col_names=F) ----
if availableData[5]:
    asy_seprate = (
        pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='withdrawal',
                      usecols='A:L', skiprows=0, nrows=12, header=None).to_numpy(dtype=float) * pctmale / 100.0
        + pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='withdrawal',
                        usecols='N:Y', skiprows=0, nrows=12, header=None).to_numpy(dtype=float) * (1.0 - pctmale) / 100.0)
    asy_seprate[0:12, 0] *= 100   # R: asy_seprate[1:12, 1] *= 100
    asy_seprate[0, 1:12] *= 100   # R: asy_seprate[1, 2:12] *= 100
else:
    asy_seprate = pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='withdrawal', usecols='A:L', skiprows=0, nrows=12,
        header=None).to_numpy(dtype=float)
SeparationRate = ConstantFill_SepRate(asy_seprate)
g.SeparationRate = SeparationRate

# ---- Mortality (B2:D6 + F2:H6, col_names=T → 4 data rows each) ----
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
mort_m.columns = ['Age', 'M', 'F']
mort_f.columns = ['Age', 'M', 'F']
mort_table    = pd.concat([mort_m, mort_f], ignore_index=True)
MortalityTable = MortTable(mort_table, pctmale)
g.MortalityTable = MortalityTable

# ---- Annuity vector ----
AnnuityVector = ComputeAnnuity(COLA_c)
g.AnnuityVector = AnnuityVector

# ---- Retirement number and benefit (B1:B17, F1:F17, col_names=T → 16 data rows) ----
if availableData[1]:
    retdist_skiprows = RETDIST_SKIPROWS.get(plan, 0)
    ret_num = (pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='retdist',
                              usecols='B:B', skiprows=retdist_skiprows, nrows=16, header=0)
               .to_numpy(dtype=float) * _s(planinfo, 'beneficiaries_tot'))
    ret_ben = (pd.read_excel(os.path.join(plan_folder, file_name), sheet_name='retdist',
                              usecols='F:F', skiprows=retdist_skiprows, nrows=16, header=0)
               .to_numpy(dtype=float) * _s(planinfo, 'BeneficiaryBenefit_avg') * 1000)
else:
    ret_num = (pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='retdist', usecols='B:B', skiprows=0, nrows=16, header=0)
               .to_numpy(dtype=float) * _s(planinfo, 'beneficiaries_tot'))
    ret_ben = (pd.read_excel(
        os.path.join(common_dir, 'default_assumptions.xlsx'),
        sheet_name='retdist', usecols='F:F', skiprows=0, nrows=16, header=0)
               .to_numpy(dtype=float) * _s(planinfo, 'BeneficiaryBenefit_avg') * 1000)

RetirementNumber  = LinearFill(ret_num, Slope=-1, retirement=True)
RetirementBenefit = ConstantFill(ret_ben, retirement=True)

# ---- Inactive members ----
inactive = Calc_Inactive(active, SeparationRate, RefundRate, MortalityTable,
                          RetirementStart_t[1], NyearFullBenefit_t[1])
inactive = scale_inactive_members(inactive, plan, planinfo, PPD)
CreateTiers(active, inactive, num_tiers)

# ---- Tier active/inactive arrays (set by CreateTiers via g) ----
tier_actives   = [g.active_t1,   g.active_t2,   g.active_t3,
                  g.active_t4,   g.active_t5,   g.active_t6]
tier_inactives = [g.inactive_t1, g.inactive_t2, g.inactive_t3,
                  g.inactive_t4, g.inactive_t5, g.inactive_t6]

def _fmt(s: float) -> str:
    return f"{int(s // 60)}m {s % 60:.1f}s" if s >= 60 else f"{s:.1f}s"

# ---- Main simulation ----
_t0 = time.perf_counter()
MainRes = {}
setCurrentTier = False
for i in range(1, 7):
    if num_tiers >= i:
        if num_tiers == i:
            setCurrentTier = True
        _ti = time.perf_counter()
        MainRes[i] = Main_Current(
            tier_actives[i - 1], tier_inactives[i - 1],
            COLA_t[i], WageYears_t[i], BenefitCap_t[i],
            BenefitFactor_t[i], RetirementStart_t[i], NyearFullBenefit_t[i],
            CurrentTier=setCurrentTier)
        print(f"  tier {i}/{num_tiers} done  ({_fmt(time.perf_counter() - _ti)})")
    else:
        MainRes[i] = [np.zeros(MainRes[1][k].shape) for k in range(5)]

_ti = time.perf_counter()
RetRes = Main_Ret(RetirementNumber, RetirementBenefit)
print(f"  Main_Ret done  ({_fmt(time.perf_counter() - _ti)})")

# ---- Aggregate results ----
main_cf       = sum(MainRes[i][1] for i in range(1, 7))
ret_cf        = RetRes[1]
cash_outflows = main_cf + ret_cf
cash_inflows  = sum(MainRes[i][2] for i in range(1, 7))
NormalCost    = sum(MainRes[i][4] for i in range(1, 7))

AAL = (MainRes[1][0] + MainRes[2][0] + RetRes[0]
       + MainRes[3][0] + MainRes[4][0] + MainRes[5][0] + MainRes[6][0])

Model_AAL          = float(AAL[0, 0])
CAFR_AAL           = _s(planinfo, 'ActLiabilities_GASB') * 1000
Percent_difference = (Model_AAL - CAFR_AAL) / CAFR_AAL

Compare_Result = pd.DataFrame({
    'type':  ['EAN'],
    'model': [Model_AAL],
    'cafr':  [CAFR_AAL],
    'dif':   [Percent_difference],
})

print(f"Model AAL : {Model_AAL:,.0f}")
print(f"CAFR  AAL : {CAFR_AAL:,.0f}")
print(f"Pct diff  : {Percent_difference:.4%}")

# ---- Save ----
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
        'planinfo': planinfo,
        'Compare_Result': Compare_Result,
        'Model_AAL': Model_AAL, 'CAFR_AAL': CAFR_AAL,
        'Percent_difference': Percent_difference,
    }, fh)
print(f"Saved: {save_path}")
print(f"Total time: {_fmt(time.perf_counter() - _t0)}")
