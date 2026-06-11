"""
Fast simulation core — replaces functions_cf_model.py and liability_cf_model.py.

Changes vs original:
  - No g module: all parameters passed via PlanParams.
  - UpdateEmployeeCount / L_UpdateEmployeeCount: vectorized diagonal shift.
  - DeathPay: vectorized triangle-masked elementwise sum.
  - ComputeAnnuity: vectorized inner loop via np.cumprod.
  - PVNC_Calc: parallel across 55 starting ages (ThreadPoolExecutor).
  - TotalLiabilities_Current: parallel 2 paths (ThreadPoolExecutor).
  - MortTable / Calc_Inactive / CreateTiers: no g, return values instead of mutating globals.
"""
from __future__ import annotations

import os
import warnings
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from .sim_params import PlanParams


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def past_wages(Wage, age, service, years, period):
    wageVec = np.zeros(period)
    for k in range(period):
        i = age - period + 1 + k
        wageVec[k] = Wage[i - 1, service - period + k, years - period + k]
    return wageVec


def past_wages_mean(Wage, age, service, years, period):
    """float(np.mean(past_wages(...))) without numpy dispatch/allocation.

    Bit-identical for period <= 8: numpy's pairwise summation is sequential
    below its unroll block size, so a left-to-right Python sum followed by a
    single divide performs the same IEEE operations in the same order.
    """
    s = 0.0
    for k in range(period):
        i = age - period + 1 + k
        s += Wage[i - 1, service - period + k, years - period + k]
    return s / period


# ---------------------------------------------------------------------------
# Simulation functions
# ---------------------------------------------------------------------------

def refund(Employees, SepRate, RefRate, Wage, year, p: PlanParams):
    NumRefund    = Employees * SepRate * RefRate
    AmountRefund = 0.0
    ecr = p.EmployeeContributionRate
    rr  = p.refundReturn
    # (1+rr)**k is elementwise, so slicing a precomputed vector yields the
    # exact same values as rebuilding (1+rr)**arange(1, j+1) per cell.
    all_powers = (1 + rr) ** np.arange(1, Employees.shape[1])
    for i in range(1, Employees.shape[0] + 1):
        for j in range(1, min(i, Employees.shape[1] - 1) + 1):
            if NumRefund[i - 1, j - 1] > 0:
                powers = all_powers[:j]
                if year < j:
                    TempRefund = Wage[i-1, j-1, year-1] * ecr * float(powers.sum())
                else:
                    pw = past_wages(Wage, i, j, year, j)
                    TempRefund = float(np.sum(pw * ecr * powers))
                AmountRefund += TempRefund * NumRefund[i - 1, j - 1]
    return AmountRefund


def death_pay(Employees, Inactive, InactiveBen, Wage, MortTable, p: PlanParams):
    """Vectorized: replaces DeathPay double loop with triangle-masked numpy ops."""
    n_age, n_svc = Employees.shape
    mort    = MortTable[:n_age, 1][:, np.newaxis]           # (n_age, 1)
    annuity = p.AnnuityVector[:n_age][:, np.newaxis]        # (n_age, 1)
    j_1b    = np.arange(1, n_svc + 1)[np.newaxis, :]        # 1-based j: (1, n_svc)
    ben     = np.minimum(p.BenefitFactor * j_1b, p.BenefitCap)

    # mask: j_0 <= min(i_0, n_svc-2)
    i_idx = np.arange(n_age)[:, np.newaxis]
    j_idx = np.arange(n_svc)[np.newaxis, :]
    mask  = j_idx <= np.minimum(i_idx, n_svc - 2)

    active_part   = Employees * mort * annuity * ben * Wage * p.MortAdujst
    inactive_part = Inactive  * mort * annuity * InactiveBen

    return float(np.where(mask, active_part + inactive_part, 0.0).sum())


def update_employees(Employees, SepRate, RetRate, MortTable, TotalEmployees, year):
    """Vectorized: replaces UpdateEmployeeCount double loop with diagonal numpy shift."""
    n_age, n_svc = Employees.shape[0], Employees.shape[1]
    mort = MortTable[:n_age - 1, 1]
    P    = mort[:, np.newaxis] + SepRate[:n_age-1, :n_svc-1] + RetRate[:n_age-1, :n_svc-1]
    upd  = Employees[:n_age-1, :n_svc-1, year-1] * (1.0 - P)

    i_idx = np.arange(n_age - 1)[:, np.newaxis]
    j_idx = np.arange(n_svc - 1)[np.newaxis, :]
    Employees[1:, 1:, year] = np.where(j_idx <= np.minimum(i_idx, n_svc - 2), upd, 0.0)

    cm   = Employees[:, :3, year-1]
    cm_s = float(cm.sum())
    if cm_s:
        Employees[:, :3, year] += (cm / cm_s) * (TotalEmployees - float(Employees[:, :, year].sum()))
    return Employees[:, :, year].copy()


def l_update_employees(Employees, SepRate, RetRate, MortTable, year):
    """Vectorized: replaces L_UpdateEmployeeCount (no calibration)."""
    n_age, n_svc = Employees.shape[0], Employees.shape[1]
    mort = MortTable[:n_age - 1, 1]
    P    = mort[:, np.newaxis] + SepRate[:n_age-1, :n_svc-1] + RetRate[:n_age-1, :n_svc-1]
    upd  = Employees[:n_age-1, :n_svc-1, year-1] * (1.0 - P)

    i_idx = np.arange(n_age - 1)[:, np.newaxis]
    j_idx = np.arange(n_svc - 1)[np.newaxis, :]
    Employees[1:, 1:, year] = np.where(j_idx <= np.minimum(i_idx, n_svc - 2), upd, 0.0)
    return Employees[:, :, year].copy()


def update_inactive_count(Employees, Inactive, SepRate, RefRate, MortTable, year, p: PlanParams):
    nfb     = p.NyearFullBenefit
    RetRate = p.RetirementRate
    Inactive[1:, :, year] = Inactive[:-1, :, year - 1]
    ProbSepNoRef = SepRate * (1.0 - RefRate)
    for i in range(nfb + 1, Employees.shape[0] + 1):
        DeathRate = MortTable[i - 1, 1]
        for j in range(nfb, min(i, Employees.shape[1] - 1) + 1):
            ProbRemove = DeathRate + RetRate[i-1, j-1]
            Inactive[i-1, j-1, year] -= Inactive[i-2, j-1, year-1] * ProbRemove
            Inactive[i-1, j-1, year] += Employees[i-1, j-1, year-1] * ProbSepNoRef[i-1, j-1]
    return Inactive[:, :, year].copy()


def update_inactive_benefits(Inactive, Employees, Wage, InactiveBen, SepRate, year, p: PlanParams):
    nfb     = p.NyearFullBenefit
    RetRate = p.RetirementRate
    WageYrs = p.WageYears
    BenFact = p.BenefitFactor
    BenCap  = p.BenefitCap
    RefRate = p.RefundRate
    DR      = p.MortalityTable[:Inactive.shape[0], 1]

    TotalBenefits = np.zeros((Inactive.shape[0], Inactive.shape[1], 2))
    TotalBenefits[:, :, 0] = Inactive[:, :, year-1] * InactiveBen[:, :, year-1]
    TotalBenefits[:, :, 1] = Inactive[:, :, year]   * InactiveBen[:, :, year]

    remove_rate = DR[:, np.newaxis] + RetRate
    TotalBenefits[1:, :, 1] = (TotalBenefits[:-1, :, 0]
                                - TotalBenefits[:-1, :, 0] * remove_rate[:-1, :])

    ProbSepNoRef = SepRate * (1.0 - RefRate)
    for i in range(nfb + 1, Employees.shape[0] + 1):
        for j in range(nfb, min(i, Employees.shape[1] - 1) + 1):
            NewSep = Employees[i-1, j-1, year-1] * ProbSepNoRef[i-1, j-1]
            if NewSep == 0.0:
                continue  # NewBen would be exactly 0.0; x += 0.0 is a no-op
            if year < WageYrs:
                NewBen = min(BenFact * j, BenCap) * Wage[i-1, j-1, year-1] * NewSep
            else:
                NewBen = (min(BenFact * j, BenCap)
                          * past_wages_mean(Wage, i, j, year, WageYrs) * NewSep)
            TotalBenefits[i-1, j-1, 1] += NewBen

    with np.errstate(invalid='ignore', divide='ignore'):
        result = TotalBenefits[:, :, 1] / Inactive[:, :, year]
    result[np.isnan(result) | np.isinf(result)] = 0.0
    return result


def update_retirement_number(Retirement, Employees, Inactive, RetRate, MortTable, year, p: PlanParams):
    nfb       = p.NyearFullBenefit
    pct_mrg   = p.pct_mrg
    MortIndex = 20
    n         = Retirement.shape[0]
    DeathRate = MortTable[(MortIndex-1):(MortIndex-1+n), 1]

    Retirement_current  = Retirement[:, :, year-1].copy()
    Retirement_current -= Retirement_current * DeathRate[:, np.newaxis] * (1.0 - pct_mrg)
    Retirement[1:, 0, year] = Retirement_current[:-1, 0]

    for i in range(20, Employees.shape[0] + 1):
        NewRetire = 0.0
        rowIndex2 = i - 20
        for j in range(nfb, min(i, Employees.shape[1]) + 1):
            prob = RetRate[i-1, j-1]
            if prob == 0.0:
                continue  # term would be exactly 0.0
            NewRetire += (Employees[i-1, j-1, year-1] + Inactive[i-1, j-1, year-1]) * prob
        Retirement[rowIndex2, 0, year] += NewRetire

    result = Retirement[:, :, year].copy()
    result[np.isnan(result) | np.isinf(result)] = 0.0
    return result


def update_retirement_benefit(RetBen, RetNum, Wage, cola, MortTable,
                               Inactive, InactiveBen, Employees, RetRate,
                               BenFactor, year, p: PlanParams):
    nfb       = p.NyearFullBenefit
    pct_mrg   = p.pct_mrg
    wid_red   = p.widow_reduct
    WageYrs   = p.WageYears
    BenCap    = p.BenefitCap
    MortIndex = 20
    n         = RetBen.shape[0]
    DeathRate = MortTable[(MortIndex-1):(MortIndex-1+n), 1]

    TRB = np.zeros((n, 1, 2))
    TRB[:, 0, 0] = RetBen[:, 0, year-1] * RetNum[:, 0, year-1]
    TRB[:, 0, 1] = RetBen[:, 0, year]   * RetNum[:, 0, year]

    _orig0 = TRB[:, :, 0].copy()
    TRB[:, :, 0] = (_orig0 - _orig0 * DeathRate[:, np.newaxis]
                    + _orig0 * DeathRate[:, np.newaxis] * pct_mrg * wid_red)
    TRB[1:, 0, 1] = TRB[:-1, 0, 0] * (1.0 + cola)

    for i in range(20, Employees.shape[0] + 1):
        NewBenefit = 0.0
        rowIndex2  = i - 20
        for j in range(nfb, min(i, Employees.shape[1]) + 1):
            prob = RetRate[i-1, j-1]
            if prob == 0.0:
                continue  # both retire terms would be exactly 0.0
            NewRetireActive   = Employees[i-1, j-1, year-1] * prob
            NewRetireInactive = Inactive[i-1, j-1, year-1]  * prob
            if NewRetireInactive != 0.0:
                NewBenefit += NewRetireInactive * InactiveBen[i-1, j-1, year-1]
            if NewRetireActive != 0.0:
                if year < WageYrs:
                    NewBenefit += min(BenFactor * j, BenCap) * Wage[i-1, j-1, year-1] * NewRetireActive
                else:
                    NewBenefit += (min(BenFactor * j, BenCap)
                                   * past_wages_mean(Wage, i, j, year, WageYrs) * NewRetireActive)
        TRB[rowIndex2, 0, 1] += NewBenefit

    with np.errstate(invalid='ignore', divide='ignore'):
        result = TRB[:, :, 1] / RetNum[:, :, year]
    result[np.isnan(result) | np.isinf(result)] = 0.0
    return result


def compute_annuity(COLA, p: PlanParams) -> np.ndarray:
    """Vectorized inner loop via cumprod: replaces ComputeAnnuity."""
    n         = p.EmployeeEnd - p.EmployeeStart + 1
    mort      = p.MortalityTable[:, 1]
    dr_factor = (1.0 + COLA) / (1.0 + p.annuity_dr)
    AV        = np.zeros(n)
    for i in range(n):
        surv    = np.cumprod(1.0 - mort[i:])
        k       = np.arange(len(surv))
        AV[i]   = float(np.dot(surv, dr_factor ** k))
    return AV


# ---------------------------------------------------------------------------
# Data-expansion helpers (no g)
# ---------------------------------------------------------------------------

def mort_table_fast(collapsed_mort, pct_male, employee_start: int = 20) -> np.ndarray:
    """Replaces MortTable from bucketfill_cf_model.py — takes employee_start explicitly."""
    ages_range = range(employee_start, 120)
    result = np.zeros((len(ages_range), 2))
    for count, i in enumerate(ages_range):
        result[count, 0] = i
        if i < 30:
            row = collapsed_mort[collapsed_mort['Age'] == 30]
            result[count, 1] = float(row['M'].iloc[0]) * pct_male + float(row['F'].iloc[0]) * (1 - pct_male)
        elif i < 100:
            decade = (i // 10) * 10
            rows = collapsed_mort[collapsed_mort['Age'] == decade]
            result[count, 1] = float(rows['M'].mean()) * pct_male + float(rows['F'].mean()) * (1 - pct_male)
        else:
            row = collapsed_mort[collapsed_mort['Age'] == 90]
            result[count, 1] = float(row['M'].iloc[0]) * pct_male + float(row['F'].iloc[0]) * (1 - pct_male)
    return result


def calc_inactive_fast(active, withdrawal, refund_rate, MortalityTable_f, p: PlanParams) -> np.ndarray:
    """Replaces Calc_Inactive — no g, uses fast update functions."""
    nfb = p.NyearFullBenefit
    ws  = 5000

    ActiveNumber                = np.zeros((active.shape[0], active.shape[1], ws))
    ActiveNumber[:, :, 0]       = active
    InactiveNumber              = np.zeros_like(ActiveNumber)
    TotalEmployees              = float(ActiveNumber[:, :, 0].sum())

    ActiveNumber[:, :, 1]   = update_employees(ActiveNumber, withdrawal, p.RetirementRate,
                                                MortalityTable_f, TotalEmployees, 1)
    InactiveNumber[:, :, 1] = update_inactive_count(ActiveNumber, InactiveNumber,
                                                     withdrawal, refund_rate, MortalityTable_f, 1, p)
    t = 2
    while (abs(float(np.mean(InactiveNumber[:, :, t-1] - InactiveNumber[:, :, t-2]))) > 0.00005
           and t < ws):
        ActiveNumber[:, :, t]   = update_employees(ActiveNumber, withdrawal, p.RetirementRate,
                                                    MortalityTable_f, TotalEmployees, t)
        InactiveNumber[:, :, t] = update_inactive_count(ActiveNumber, InactiveNumber,
                                                         withdrawal, refund_rate, MortalityTable_f, t, p)
        t += 1

    if t >= ws:
        warnings.warn(f"calc_inactive_fast: {ws} iterations without convergence.")

    final = InactiveNumber[:, :, t-1]
    total = float(final.sum())
    if total == 0.0:
        result = np.zeros(active.shape)
        sub    = ActiveNumber[:, nfb-1:55, 0]
        denom2 = float(sub.sum())
        result[:, nfb-1:55] = sub / denom2 if denom2 != 0.0 else 0.0
        return result
    return final / total


def create_tiers_fast(active, inactive, num_tiers, tier_service) -> list:
    """
    Replaces CreateTiers — returns list of (active_t, inactive_t) tuples (length 6,
    zero-filled for unused tiers) instead of mutating g globals.
    """
    def _zero_outside(mat, keep_from, keep_to):
        if keep_from >= keep_to:
            keep_from, keep_to = keep_to - 1, keep_from + 1
        out = mat.copy()
        if keep_from > 0:
            out[:, :keep_from] = 0
        if keep_to < out.shape[1]:
            out[:, keep_to:] = 0
        return out

    ts = tier_service
    zero = np.zeros_like(active)

    if num_tiers == 1:
        pairs = [(active.copy(), inactive.copy())]
    elif num_tiers == 2:
        pairs = [(_zero_outside(active, ts[1], 55), _zero_outside(inactive, ts[1], 55)),
                 (_zero_outside(active, 0, ts[1]),  _zero_outside(inactive, 0, ts[1]))]
    elif num_tiers == 3:
        pairs = [(_zero_outside(active, ts[1], 55),    _zero_outside(inactive, ts[1], 55)),
                 (_zero_outside(active, ts[2], ts[1]), _zero_outside(inactive, ts[2], ts[1])),
                 (_zero_outside(active, 0, ts[2]),     _zero_outside(inactive, 0, ts[2]))]
    elif num_tiers == 4:
        pairs = [(_zero_outside(active, ts[1], 55),    _zero_outside(inactive, ts[1], 55)),
                 (_zero_outside(active, ts[2], ts[1]), _zero_outside(inactive, ts[2], ts[1])),
                 (_zero_outside(active, ts[3], ts[2]), _zero_outside(inactive, ts[3], ts[2])),
                 (_zero_outside(active, 0, ts[3]),     _zero_outside(inactive, 0, ts[3]))]
    elif num_tiers == 5:
        pairs = [(_zero_outside(active, ts[1], 55),    _zero_outside(inactive, ts[1], 55)),
                 (_zero_outside(active, ts[2], ts[1]), _zero_outside(inactive, ts[2], ts[1])),
                 (_zero_outside(active, ts[3], ts[2]), _zero_outside(inactive, ts[3], ts[2])),
                 (_zero_outside(active, ts[4], ts[3]), _zero_outside(inactive, ts[4], ts[3])),
                 (_zero_outside(active, 0, ts[4]),     _zero_outside(inactive, 0, ts[4]))]
    else:  # 6
        pairs = [(_zero_outside(active, ts[1], 55),    _zero_outside(inactive, ts[1], 55)),
                 (_zero_outside(active, ts[2], ts[1]), _zero_outside(inactive, ts[2], ts[1])),
                 (_zero_outside(active, ts[3], ts[2]), _zero_outside(inactive, ts[3], ts[2])),
                 (_zero_outside(active, ts[4], ts[3]), _zero_outside(inactive, ts[4], ts[3])),
                 (_zero_outside(active, ts[5], ts[4]), _zero_outside(inactive, ts[5], ts[4])),
                 (_zero_outside(active, 0, ts[5]),     _zero_outside(inactive, 0, ts[5]))]

    while len(pairs) < 6:
        pairs.append((zero.copy(), zero.copy()))
    return pairs


# ---------------------------------------------------------------------------
# PVNC — parallel across starting ages
# ---------------------------------------------------------------------------

def _pvnc_single_age(a_0, n_age, n_svc, L_Nyear, DiscountRate, Wage_year, p: PlanParams):
    """One independent PVNC simulation starting with a single employee at age a_0 (0-based)."""
    L_BW = np.zeros((n_age, n_svc, L_Nyear));  L_BW[:, :, 0] = Wage_year
    L_AN = np.zeros((n_age, n_svc, L_Nyear));  L_AN[a_0, 0, 0] = 1.0
    L_IN = np.zeros((n_age, n_svc, L_Nyear))
    L_IB = np.zeros((n_age, n_svc, L_Nyear))
    n_ret = 120 - 40 + 1
    L_RN  = np.zeros((n_ret, 1, L_Nyear))
    L_RB  = np.zeros((n_ret, 1, L_Nyear))
    CashOutflow = np.zeros(L_Nyear)

    for t in range(1, L_Nyear):
        ref = refund(L_AN[:, :, t-1], p.SeparationRate, p.RefundRate, L_BW, t, p)
        dth = death_pay(L_AN[:, :, t-1], L_IN[:, :, t-1], L_IB[:, :, t-1],
                        L_BW[:, :, t-1], p.MortalityTable, p)
        CashOutflow[t-1] = float((L_RN[:, :, t-1] * L_RB[:, :, t-1]).sum()) + ref + dth

        L_AN[:, :, t] = l_update_employees(L_AN, p.SeparationRate, p.RetirementRate, p.MortalityTable, t)
        L_BW[:, :, t] = L_BW[:, :, t-1] * (1.0 + p.WageGrowth)
        L_IN[:, :, t] = update_inactive_count(L_AN, L_IN, p.SeparationRate, p.RefundRate, p.MortalityTable, t, p)
        L_IB[:, :, t] = update_inactive_benefits(L_IN, L_AN, L_BW, L_IB, p.SeparationRate, t, p)
        L_RN[:, :, t] = update_retirement_number(L_RN, L_AN, L_IN, p.RetirementRate, p.MortalityTable, t, p)
        L_RB[:, :, t] = update_retirement_benefit(L_RB, L_RN, L_BW, p.COLA, p.MortalityTable,
                                                   L_IN, L_IB, L_AN, p.RetirementRate, p.BenefitFactor, t, p)

    dr   = DiscountRate
    pvfb = sum(CashOutflow[i] / (1.0 + dr)**(i + 1) for i in range(L_Nyear))
    return a_0, pvfb


def pvnc_calc_fast(Employees, Inactive, InactiveBen, RetNum, RetBen,
                   Wage, L_Nyear, Year, DiscountRate, p: PlanParams,
                   n_workers: int | None = None):
    """Parallel PVNC: 55 independent age-simulations run via ThreadPoolExecutor."""
    n_age     = Employees.shape[0]
    n_svc     = Employees.shape[1]
    Wage_year = Wage[:, :, Year - 1]

    if n_workers is None:
        n_workers = min(n_age, os.cpu_count() or 4)

    PVFB = np.zeros(n_age)
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futs = [pool.submit(_pvnc_single_age, a_0, n_age, n_svc, L_Nyear,
                            DiscountRate, Wage_year, p)
                for a_0 in range(n_age)]
        for fut in futs:
            a_0, pvfb_a = fut.result()
            PVFB[a_0] = pvfb_a

    # PVFS: build wage path from Wage_year then compute present-value future salaries
    L_BW_pvfs = np.zeros((n_age, n_svc, L_Nyear))
    L_BW_pvfs[:, :, 0] = Wage_year
    for t in range(1, L_Nyear):
        L_BW_pvfs[:, :, t] = L_BW_pvfs[:, :, t-1] * (1.0 + p.WageGrowth)

    SR  = p.SeparationRate
    MT  = p.MortalityTable
    RR  = p.RetirementRate
    PVFS = np.zeros((n_age, n_svc))
    for i in range(1, n_age + 1):
        for j in range(1, min(i, n_svc) + 1):
            YLW      = min(n_age - i, n_svc - j)
            ListWage = past_wages(L_BW_pvfs, i + YLW, j + YLW, j + YLW, j + YLW)
            ProbTracker = 1.0
            tempsum     = 0.0
            for m in range(YLW + 1):
                jm          = j + m
                ProbSep     = min(SR[i+m-1, j+m-1] + MT[i+m-1, 1] + RR[i+m-1, jm-1], 1.0)
                ProbTracker = (1.0 - ProbSep) * ProbTracker
                tempsum    += ListWage[m] * ProbTracker / (1.0 + DiscountRate)**m
            PVFS[i-1, j-1] = tempsum

    NCxs = PVFB / PVFS[:, 0]
    NCxs[np.isnan(NCxs) | np.isinf(NCxs)] = 0.0
    if np.isnan(NCxs.sum()):
        raise ValueError("PVFS must be numeric")

    return [NCxs, PVFS]


# ---------------------------------------------------------------------------
# Liability calculations
# ---------------------------------------------------------------------------

def _liab_path(path_idx, E0, IN0, IB0, W0, L_Nyear, DiscountRate, p: PlanParams):
    """Single-path forward projection for TotalLiabilities_Current."""
    n_age = E0.shape[0];  n_svc = E0.shape[1]
    n_ret = 120 - 40 + 1
    L_AN  = np.zeros((n_age, n_svc, L_Nyear))
    L_IN  = np.zeros((n_age, n_svc, L_Nyear))
    L_IB  = np.zeros((n_age, n_svc, L_Nyear))
    L_RN  = np.zeros((n_ret, 1, L_Nyear))
    L_RB  = np.zeros((n_ret, 1, L_Nyear))
    L_BW  = np.zeros((n_age, n_svc, L_Nyear));  L_BW[:, :, 0] = W0

    if path_idx == 0:   # active-only path
        L_AN[:, :, 0] = E0
    else:               # inactive+retiree path
        L_IN[:, :, 0] = IN0
        L_IB[:, :, 0] = IB0

    cashout = np.zeros(L_Nyear)
    for t in range(1, L_Nyear):
        ret_cf = float((L_RN[:, :, t-1] * L_RB[:, :, t-1]).sum())
        ref    = refund(L_AN[:, :, t-1], p.SeparationRate, p.RefundRate, L_BW, t, p)
        dth    = death_pay(L_AN[:, :, t-1], L_IN[:, :, t-1], L_IB[:, :, t-1],
                           L_BW[:, :, t-1], p.MortalityTable, p)
        dis    = float((L_BW[:, :, t-1] * L_AN[:, :, t-1]).sum()) * p.DisabilityPayoutRate
        cashout[t-1] = (ret_cf + ref + dth + dis) * p.scaling

        L_AN[:, :, t] = l_update_employees(L_AN, p.SeparationRate, p.RetirementRate, p.MortalityTable, t)
        L_BW[:, :, t] = L_BW[:, :, t-1] * (1.0 + p.WageGrowth)
        L_IN[:, :, t] = update_inactive_count(L_AN, L_IN, p.SeparationRate, p.RefundRate, p.MortalityTable, t, p)
        L_IB[:, :, t] = update_inactive_benefits(L_IN, L_AN, L_BW, L_IB, p.SeparationRate, t, p)
        L_RN[:, :, t] = update_retirement_number(L_RN, L_AN, L_IN, p.RetirementRate, p.MortalityTable, t, p)
        L_RB[:, :, t] = update_retirement_benefit(L_RB, L_RN, L_BW, p.COLA, p.MortalityTable,
                                                   L_IN, L_IB, L_AN, p.RetirementRate, p.BenefitFactor, t, p)

    dr = DiscountRate
    return sum(cashout[i] / (1.0 + dr)**(i + 1) for i in range(L_Nyear))


def total_liabilities_current_fast(Employees, Inactive, InactiveBen, Wage,
                                    L_Nyear, Year, DiscountRate, p: PlanParams):
    """Parallel 2-path TotalLiabilities_Current."""
    E0  = Employees[:, :, Year-1]
    IN0 = Inactive[:, :, Year-1]
    IB0 = InactiveBen[:, :, Year-1]
    W0  = Wage[:, :, Year-1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        f0 = pool.submit(_liab_path, 0, E0, IN0, IB0, W0, L_Nyear, DiscountRate, p)
        f1 = pool.submit(_liab_path, 1, E0, IN0, IB0, W0, L_Nyear, DiscountRate, p)
        active_liab   = f0.result()
        inactive_liab = f1.result()
    return np.array([active_liab, inactive_liab])


def total_liabilities_ret_fast(RetNum, RetBen, L_Nyear, Year, DiscountRate, p: PlanParams):
    n_age_ser = (p.EmployeeEnd - p.EmployeeStart + 1,
                 p.ServiceEnd  - p.ServiceStart  + 1)
    L_AN = np.zeros((*n_age_ser, L_Nyear))
    L_IN = np.zeros_like(L_AN)
    L_BW = np.zeros_like(L_AN)
    L_IB = np.zeros_like(L_AN)

    n_ret = len(RetNum[:, :, Year-1].ravel())
    L_RN  = np.zeros((n_ret, 1, L_Nyear));  L_RN[:, :, 0] = RetNum[:, :, Year-1]
    L_RB  = np.zeros((n_ret, 1, L_Nyear));  L_RB[:, :, 0] = RetBen[:, :, Year-1]

    cashout = np.zeros(L_Nyear)
    for t in range(1, L_Nyear):
        cashout[t-1] = float((L_RN[:, :, t-1] * L_RB[:, :, t-1]).sum()) * p.scaling
        L_RN[:, :, t] = update_retirement_number(L_RN, L_AN, L_IN, p.RetirementRate, p.MortalityTable, t, p)
        L_RB[:, :, t] = update_retirement_benefit(L_RB, L_RN, L_BW, p.COLA, p.MortalityTable,
                                                   L_IN, L_IB, L_AN, p.RetirementRate, p.BenefitFactor, t, p)

    dr = DiscountRate
    return sum(cashout[i] / (1.0 + dr)**(i + 1) for i in range(L_Nyear))


# ---------------------------------------------------------------------------
# Main simulation loops
# ---------------------------------------------------------------------------

def main_current_fast(ActiveNumber, InactiveNumber, BaseWage_0, p: PlanParams,
                       CurrentTier: bool = True, n_workers: int | None = None):
    """
    Fast Main_Current.
    BaseWage_0: (n_age, n_svc) initial wage array (= BaseWage_2d from data loading).
    p: PlanParams with tier-specific fields already set via dataclasses.replace.
    """
    Nyear  = p.Nyear
    NMonte = p.NMonte
    n_age  = ActiveNumber.shape[0]
    n_svc  = ActiveNumber.shape[1]
    n_ret  = 120 - 40 + 1

    AN = np.zeros((n_age, n_svc, Nyear));  AN[:, :, 0] = ActiveNumber
    IN = np.zeros_like(AN);               IN[:, :, 0] = InactiveNumber
    BW = np.zeros_like(AN);               BW[:, :, 0] = BaseWage_0

    # Mask matching the original loop constraint: j_exp <= i_exp (0-based).
    # ConstantFill can populate cells where j_exp == i_exp + 1 (service = age - 19),
    # but the original NC loop limits j to min(i, n_svc) in 1-indexed form,
    # which corresponds to j_exp <= i_exp in 0-indexed form. Without this mask,
    # the NC einsum over-counts the superdiagonal cells where BW != 0 but PVFS == 0.
    _nc_mask = np.tril(np.ones((n_age, n_svc), dtype=bool))

    # Initial inactive benefits
    j_1b = np.arange(1, n_svc + 1)[np.newaxis, :]
    ben  = np.minimum(p.BenefitFactor * j_1b, p.BenefitCap)
    IB   = np.zeros_like(AN)
    IB[:, :, 0] = np.where(IN[:, :, 0] != 0.0, BW[:, :, 0] * ben, 0.0)

    RN = np.zeros((n_ret, 1, Nyear))
    RB = np.zeros((n_ret, 1, Nyear))

    AAL      = np.zeros((Nyear, NMonte))
    COutflow = np.zeros((Nyear, NMonte))
    CInflow  = np.zeros((Nyear, NMonte))
    PVFB     = np.zeros((Nyear, 2))
    PVNC_arr = np.zeros((Nyear, 1))
    NC       = np.zeros((Nyear, 1))
    PVFS_vec = np.zeros((Nyear, 1))

    PVNC_Values = pvnc_calc_fast(AN, IN, IB, RN, RB, BW, 80, 1,
                                  p.discountrate, p, n_workers=n_workers)

    for n in range(1, NMonte + 1):
        AN[:, :, 1:] = 0.0;  IN[:, :, 1:] = 0.0
        BW[:, :, 1:] = 0.0;  IB[:, :, 1:] = 0.0
        RN[:, :, 1:] = 0.0;  RB[:, :, 1:] = 0.0

        for t in range(1, Nyear):
            if PVFB[t-1, :].sum() == 0.0:
                PVFB[t-1, :] = total_liabilities_current_fast(
                    AN, IN, IB, BW, 80, t, p.discountrate, p)

                PVFS     = PVNC_Values[1] * (1.0 + p.Inflation)**(t - 1)
                NCxs     = PVNC_Values[0] * (1.0 + p.Inflation)**(t - 1)
                PVNC_arr[t-1, 0] = float(np.einsum('ij,i,ij->',
                                                     AN[:, :, t-1], NCxs, PVFS))
                NC[t-1, 0]       = float(np.einsum('ij,i,ij->',
                                                     AN[:, :, t-1], NCxs,
                                                     np.where(_nc_mask, BW[:, :, t-1], 0.0)))
                PVFS_vec[t-1, 0] = float(PVFS.sum())

            AAL[t-1, n-1] = ((PVFB[t-1, 0] - PVNC_arr[t-1, 0])
                              + PVFB[t-1, 1])

            ref = refund(AN[:, :, t-1], p.SeparationRate, p.RefundRate, BW, t, p)
            dth = death_pay(AN[:, :, t-1], IN[:, :, t-1], IB[:, :, t-1],
                            BW[:, :, t-1], p.MortalityTable, p)
            dis = float((BW[:, :, t-1] * AN[:, :, t-1]).sum()) * p.DisabilityPayoutRate

            COutflow[t-1, n-1] = (float((RN[:, :, t-1] * RB[:, :, t-1]).sum())
                                   + ref + dth + dis)
            CInflow[t-1, n-1]  = (float((BW[:, :, t-1] * AN[:, :, t-1]).sum())
                                   * (p.EmployeeContributionRate + p.EmployerContributionRate))

            TotalEmp    = float(AN[:, :, t-1].sum()) * (1.0 + p.PopulationGrowth)
            BW[:, :, t] = BW[:, :, t-1] * (1.0 + p.WageGrowth)

            if CurrentTier:
                AN[:, :, t] = update_employees(AN, p.SeparationRate, p.RetirementRate,
                                                p.MortalityTable, TotalEmp, t)
            else:
                AN[:, :, t] = l_update_employees(AN, p.SeparationRate, p.RetirementRate,
                                                  p.MortalityTable, t)

            IN[:, :, t] = update_inactive_count(AN, IN, p.SeparationRate, p.RefundRate,
                                                 p.MortalityTable, t, p)
            IB[:, :, t] = update_inactive_benefits(IN, AN, BW, IB, p.SeparationRate, t, p)
            RN[:, :, t] = update_retirement_number(RN, AN, IN, p.RetirementRate,
                                                    p.MortalityTable, t, p)
            RB[:, :, t] = update_retirement_benefit(RB, RN, BW, p.COLA, p.MortalityTable,
                                                     IN, IB, AN, p.RetirementRate,
                                                     p.BenefitFactor, t, p)

    return [AAL, COutflow, CInflow, PVFB, NC]


def main_ret_fast(RetirementNumber, RetirementBenefit, p: PlanParams):
    """Fast Main_Ret."""
    Nyear  = p.Nyear
    NMonte = p.NMonte
    n_as   = (p.EmployeeEnd - p.EmployeeStart + 1,
              p.ServiceEnd  - p.ServiceStart  + 1)

    RN = np.zeros((RetirementNumber.shape[0], RetirementNumber.shape[1], Nyear))
    RN[:, :, 0] = RetirementNumber
    RB = np.zeros_like(RN);  RB[:, :, 0] = RetirementBenefit

    AN_z = np.zeros((*n_as, Nyear));  IN_z = np.zeros_like(AN_z)
    BW_z = np.zeros_like(AN_z);      IB_z = np.zeros_like(AN_z)

    AAL      = np.zeros((Nyear, NMonte))
    COutflow = np.zeros((Nyear, NMonte))
    PVFB     = np.zeros((Nyear, 1))

    for n in range(1, NMonte + 1):
        RN[:, :, 1:] = 0.0;  RB[:, :, 1:] = 0.0

        for t in range(1, Nyear):
            if PVFB[t-1, :].sum() == 0.0:
                PVFB[t-1, 0] = total_liabilities_ret_fast(RN, RB, 80, t, p.discountrate, p)

            AAL[t-1, n-1]      = PVFB[t-1, 0]
            COutflow[t-1, n-1] = float((RN[:, :, t-1] * RB[:, :, t-1]).sum())

            RN[:, :, t] = update_retirement_number(RN, AN_z, IN_z, p.RetirementRate,
                                                    p.MortalityTable, t, p)
            RB[:, :, t] = update_retirement_benefit(RB, RN, BW_z, p.COLA, p.MortalityTable,
                                                     IN_z, IB_z, AN_z, p.RetirementRate,
                                                     p.BenefitFactor, t, p)

    return [AAL, COutflow]
