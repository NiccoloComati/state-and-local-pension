import numpy as np
import pandas as pd
import g


# ---------------------------------------------------------------------------
# Data-loading helpers
# ---------------------------------------------------------------------------

def first_nonmissing_numeric(*values):
    for value in values:
        if value is None:
            continue
        try:
            arr = np.atleast_1d(np.array(value, dtype=float).ravel())
        except (TypeError, ValueError):
            continue
        if len(arr) == 0:
            continue
        v = float(arr[0])
        if not np.isnan(v):
            return v
    return float('nan')


def get_legacy_ppd_value(plan, column, fiscal_year=2017):
    import os
    legacy_file = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..',
        'Data', 'Common', 'states', 'PPD_planlevel_main.csv'))
    if not os.path.exists(legacy_file):
        return float('nan')
    legacy_ppd = pd.read_csv(legacy_file)
    if column not in legacy_ppd.columns:
        return float('nan')
    legacy_plan_id = f"{plan}_{fiscal_year}"
    row = legacy_ppd[legacy_ppd['planid'] == legacy_plan_id]
    if len(row) == 0:
        return float('nan')
    return first_nonmissing_numeric(row[column].iloc[0])


def get_inactive_member_count(plan, planinfo):
    return first_nonmissing_numeric(
        planinfo['InactiveVestedMembers'].iloc[0],
        get_legacy_ppd_value(plan, "inactive")
    )


def get_wage_growth_assumption(plan, planinfo):
    wage_growth = first_nonmissing_numeric(
        planinfo['PayrollGrowthAssumption'].iloc[0],
        planinfo['WageInflation'].iloc[0],
        get_legacy_ppd_value(plan, "wage_inf"),
        planinfo['InflationAssumption_GASB'].iloc[0],
        get_legacy_ppd_value(plan, "inflation")
    )
    if np.isnan(wage_growth):
        raise ValueError(f"Missing wage growth assumption for {plan}")
    return wage_growth


def get_inflation_assumption(plan, planinfo):
    inflation = first_nonmissing_numeric(
        planinfo['InflationAssumption_GASB'].iloc[0],
        get_legacy_ppd_value(plan, "inflation")
    )
    if np.isnan(inflation):
        raise ValueError(f"Missing inflation assumption for {plan}")
    return inflation


def scale_inactive_members(inactive, plan, planinfo, PPD):
    inactive_adj = first_nonmissing_numeric(PPD['inactive_adj'].iloc[0])
    if np.isnan(inactive_adj):
        raise ValueError(f"Missing inactive_adj for {plan}")
    if inactive_adj == 1.0:
        inactive_count = get_inactive_member_count(plan, planinfo)
        if np.isnan(inactive_count):
            raise ValueError(f"Missing inactive member count for {plan}")
        return inactive * inactive_count
    active_count = first_nonmissing_numeric(planinfo['actives_tot'].iloc[0])
    if np.isnan(active_count):
        raise ValueError(f"Missing active member count for {plan}")
    return inactive * active_count * inactive_adj


# ---------------------------------------------------------------------------
# Simulation functions
# ---------------------------------------------------------------------------

def PastWages(Wage, age, service, years, period):
    # R: wageVec[indexer] <- Wage[i, (service-period+indexer), (years-period+indexer)]
    # All indices 1-based in R; translate to 0-based here
    wageVec = np.zeros(period)
    indexer = 1
    for i in range(age - period + 1, age + 1):   # R: (age-period+1):age
        wageVec[indexer - 1] = Wage[i - 1,
                                    service - period + indexer - 1,
                                    years  - period + indexer - 1]
        indexer += 1
    return wageVec


def Refund(Employees, SepRate, RefRate, Wage, year):
    # year: 1-based
    NumRefund    = Employees * SepRate * RefRate
    AmountRefund = 0.0
    for i in range(1, Employees.shape[0] + 1):          # R: 1:dim(Employees)[1]
        for j in range(1, min(i, Employees.shape[1] - 1) + 1):  # R: 1:min(c(i,dim-1))
            if NumRefund[i - 1, j - 1] > 0:
                if year < j:
                    TempRefund = (Wage[i - 1, j - 1, year - 1] * g.EmployeeContributionRate
                                  * float(np.sum((1 + g.refundReturn) ** np.arange(1, j + 1))))
                else:
                    pw = PastWages(Wage, age=i, service=j, years=year, period=j)
                    TempRefund = float(np.sum(pw * g.EmployeeContributionRate
                                              * (1 + g.refundReturn) ** np.arange(1, j + 1)))
                AmountRefund += TempRefund * NumRefund[i - 1, j - 1]
    return AmountRefund


def DeathPay(Employees, Inactive, InactiveBen, Wage, MortTable):
    DeathTotal = 0.0
    for i in range(1, Employees.shape[0] + 1):          # R: 1:dim(Employees)[1]
        Mort    = MortTable[i - 1, 1]                   # R: MortTable[i,2]
        Annuity = g.AnnuityVector[i - 1]                # R: AnnuityVector[i]
        for j in range(1, min(i, Employees.shape[1] - 1) + 1):
            DeathTotal += (Employees[i - 1, j - 1] * Mort * Annuity
                           * min(g.BenefitFactor * j, g.BenefitCap)
                           * Wage[i - 1, j - 1] * g.MortAdujst
                           + Inactive[i - 1, j - 1] * Mort * Annuity * InactiveBen[i - 1, j - 1])
    return DeathTotal


def UpdateEmployeeCount(Employees, SepRate, RetRate, MortTable, TotalEmployees, year):
    # year: 1-based; reads slice year-1, writes slice year
    for i in range(1, Employees.shape[0]):               # R: 1:(dim-1)
        Mort = MortTable[i - 1, 1]                       # R: MortTable[i,2]
        for j in range(1, min(i, Employees.shape[1] - 1) + 1):
            ProbSeparate = Mort + SepRate[i - 1, j - 1] + RetRate[i - 1, j - 1]
            # R: Employees[i+1,j+1,year+1] <- Employees[i,j,year]*(1-ProbSeparate)
            Employees[i, j, year] = Employees[i - 1, j - 1, year - 1] * (1.0 - ProbSeparate)

    # R: CalibrateMatrix <- Employees[,1:3,year] / sum(Employees[,1:3,year])
    cm_denom = float(Employees[:, 0:3, year - 1].sum())
    CalibrateMatrix = Employees[:, 0:3, year - 1] / cm_denom
    # R: Employees[,1:3,year+1] <- Employees[,1:3,year+1] + CalibrateMatrix*(TotalEmployees-sum(Employees[,,year+1]))
    Employees[:, 0:3, year] += CalibrateMatrix * (TotalEmployees - float(Employees[:, :, year].sum()))
    return Employees[:, :, year].copy()                  # R: return(Employees[,,year+1])


def UpdateInactiveCount(Employees, Inactive, SepRate, RefRate, MortTable, year):
    # year: 1-based; reads slice year-1, writes slice year
    # R: Inactive[2:dim1,, year+1] <- Inactive[1:(dim1-1),,year]
    Inactive[1:, :, year] = Inactive[:-1, :, year - 1]

    ProbSepNoRef = SepRate * (1.0 - RefRate)

    for i in range(g.NyearFullBenefit + 1, Employees.shape[0] + 1):    # R: (NyearFullBenefit+1):dim[1]
        DeathRate = MortTable[i - 1, 1]
        for j in range(g.NyearFullBenefit,
                       min(i, Employees.shape[1] - 1) + 1):            # R: NyearFullBenefit:min(i,dim-1)
            ProbRemove = DeathRate + g.RetirementRate[i - 1, j - 1]
            # R: Inactive[i,j,year+1] <- Inactive[i,j,year+1] - Inactive[i-1,j,year]*ProbRemove
            Inactive[i - 1, j - 1, year] -= Inactive[i - 2, j - 1, year - 1] * ProbRemove
            ProbSeparate = ProbSepNoRef[i - 1, j - 1]
            # R: Inactive[i,j,year+1] <- Inactive[i,j,year+1] + Employees[i,j,year]*ProbSeparate
            Inactive[i - 1, j - 1, year] += Employees[i - 1, j - 1, year - 1] * ProbSeparate

    return Inactive[:, :, year].copy()


def UpdateInactiveBenefits(Inactive, Employees, Wage, InactiveBen, SepRate, year):
    # year: 1-based
    # R: TotalBenefits <- Inactive[,,(year:(year+1))] * InactiveBen[,,(year:(year+1))]  → shape (55,55,2)
    TotalBenefits = np.zeros((Inactive.shape[0], Inactive.shape[1], 2))
    TotalBenefits[:, :, 0] = Inactive[:, :, year - 1] * InactiveBen[:, :, year - 1]
    TotalBenefits[:, :, 1] = Inactive[:, :, year]     * InactiveBen[:, :, year]

    DeathRate  = g.MortalityTable[:Inactive.shape[0], 1]           # R: MortalityTable[(1:nrow),2]
    remove_rate = DeathRate[:, np.newaxis] + g.RetirementRate      # R recycling: DeathRate+RetirementRate

    # R: TotalBenefits[2:dim1,,2] <- TotalBenefits[1:(dim1-1),,1] - TotalBenefits[1:(dim1-1),,1]*remove_rate[1:(dim1-1),]
    TotalBenefits[1:, :, 1] = (TotalBenefits[:-1, :, 0]
                                - TotalBenefits[:-1, :, 0] * remove_rate[:-1, :])

    ProbSepNoRef = SepRate * (1.0 - g.RefundRate)

    for i in range(g.NyearFullBenefit + 1, Employees.shape[0] + 1):
        for j in range(g.NyearFullBenefit,
                       min(i, Employees.shape[1] - 1) + 1):
            ProbSeparate = ProbSepNoRef[i - 1, j - 1]
            NewSep = Employees[i - 1, j - 1, year - 1] * ProbSeparate
            if year < g.WageYears:
                NewBenefit = min(g.BenefitFactor * j, g.BenefitCap) * Wage[i - 1, j - 1, year - 1] * NewSep
            else:
                pw = PastWages(Wage, i, j, year, g.WageYears)
                NewBenefit = min(g.BenefitFactor * j, g.BenefitCap) * float(np.mean(pw)) * NewSep
            TotalBenefits[i - 1, j - 1, 1] += NewBenefit

    # R: result <- TotalBenefits[,,2] / Inactive[,,year+1]; NaN/Inf -> 0
    with np.errstate(invalid='ignore', divide='ignore'):
        result = TotalBenefits[:, :, 1] / Inactive[:, :, year]
    result[np.isnan(result) | np.isinf(result)] = 0.0
    return result


def UpdateRetirementNumber(Retirement, Employees, Inactive, RetRate, MortTable, year):
    # year: 1-based; reads slice year-1, writes slice year
    MortIndex = 20  # R: MortIndex <- 20
    n = Retirement.shape[0]
    DeathRate = MortTable[(MortIndex - 1):(MortIndex - 1 + n), 1]  # R: MortTable[MortIndex:(dim+MortIndex-1),2]

    # R mutates the function-local argument copy here.  Keep the caller's
    # year slice unchanged, because UpdateRetirementBenefit reads it next.
    Retirement_current = Retirement[:, :, year - 1].copy()
    Retirement_current -= Retirement_current * DeathRate[:, np.newaxis] * (1.0 - g.pct_mrg)

    # R: Retirement[2:dim1,1,year+1] <- Retirement[1:(dim1-1),1,year]
    Retirement[1:, 0, year] = Retirement_current[:-1, 0]

    for i in range(20, Employees.shape[0] + 1):        # R: for i in 20:dim(Employees)[1]
        NewRetire  = 0.0
        rowIndex2  = i - 20                            # R: rowIndex2 <- (i-20+1) → 0-based: i-20
        for j in range(g.NyearFullBenefit,
                       min(i, Employees.shape[1]) + 1):  # R: NyearFullBenefit:min(i,dim[2])
            ProbRetirement = RetRate[i - 1, j - 1]
            NewRetire += ((Employees[i - 1, j - 1, year - 1] * ProbRetirement)
                          + (Inactive[i - 1, j - 1, year - 1] * ProbRetirement))
        Retirement[rowIndex2, 0, year] += NewRetire    # R: Retirement[rowIndex2,1,year+1] <- ... + NewRetire

    result = Retirement[:, :, year].copy()
    result[np.isnan(result) | np.isinf(result) | np.isnan(result)] = 0.0
    return result


def UpdateRetirementBenefit(RetBen, RetNum, Wage, cola, MortTable, Inactive, InactiveBen,
                             Employees, RetRate, BenFactor, year):
    # year: 1-based
    # R: TotalRetirmentBenefits <- array(RetBen[,1,(year:(year+1))],c(n,1,2)) * array(RetNum[,1,(year:(year+1))],c(n,1,2))
    n = RetBen.shape[0]
    TotalRetirmentBenefits = np.zeros((n, 1, 2))
    TotalRetirmentBenefits[:, 0, 0] = RetBen[:, 0, year - 1] * RetNum[:, 0, year - 1]
    TotalRetirmentBenefits[:, 0, 1] = RetBen[:, 0, year]     * RetNum[:, 0, year]

    MortIndex = 20
    DeathRate = MortTable[(MortIndex - 1):(MortIndex - 1 + n), 1]  # R: MortTable[MortIndex:(dim+MortIndex-1),2]

    # R: TotalRetirmentBenefits[,,1] <- TotalRetirmentBenefits[,,1] - TotalRetirmentBenefits[,,1]*DeathRate +
    #                                    TotalRetirmentBenefits[,,1]*DeathRate*pct_mrg*widow_reduct
    # Single-expression RHS: all references to TotalRetirmentBenefits[,,1] on the RHS use the original value
    _orig0 = TotalRetirmentBenefits[:, :, 0].copy()
    TotalRetirmentBenefits[:, :, 0] = (_orig0
                                        - _orig0 * DeathRate[:, np.newaxis]
                                        + _orig0 * DeathRate[:, np.newaxis] * g.pct_mrg * g.widow_reduct)

    rowDim = n
    # R: TotalRetirmentBenefits[2:rowDim,1,2] <- TotalRetirmentBenefits[1:(rowDim-1),1,1]*(1+cola)
    TotalRetirmentBenefits[1:, 0, 1] = TotalRetirmentBenefits[:-1, 0, 0] * (1.0 + cola)

    for i in range(20, Employees.shape[0] + 1):        # R: for i in 20:dim(Employees)[1]
        NewBenefit = 0.0
        rowIndex2  = i - 20                            # R: rowIndex2 <- (i-20+1)
        for j in range(g.NyearFullBenefit,
                       min(i, Employees.shape[1]) + 1):
            ProbRetirement  = RetRate[i - 1, j - 1]
            NewRetireActive   = Employees[i - 1, j - 1, year - 1] * ProbRetirement
            NewRetireInactive = Inactive[i - 1, j - 1, year - 1]  * ProbRetirement
            NewBenefit += NewRetireInactive * InactiveBen[i - 1, j - 1, year - 1]
            if year < g.WageYears:
                NewBenefit += min(BenFactor * j, g.BenefitCap) * Wage[i - 1, j - 1, year - 1] * NewRetireActive
            else:
                pw = PastWages(Wage, i, j, year, g.WageYears)
                NewBenefit += min(BenFactor * j, g.BenefitCap) * float(np.mean(pw)) * NewRetireActive
        TotalRetirmentBenefits[rowIndex2, 0, 1] += NewBenefit

    with np.errstate(invalid='ignore', divide='ignore'):
        result = TotalRetirmentBenefits[:, :, 1] / RetNum[:, :, year]
    result[np.isnan(result) | np.isinf(result)] = 0.0
    return result


def L_UpdateEmployeeCount(Employees, SepRate, RetRate, MortTable, year):
    # Like UpdateEmployeeCount but without new-hire calibration (liability path)
    for i in range(1, Employees.shape[0]):
        Mort = MortTable[i - 1, 1]
        for j in range(1, min(i, Employees.shape[1] - 1) + 1):
            ProbSeparate = Mort + SepRate[i - 1, j - 1] + RetRate[i - 1, j - 1]
            Employees[i, j, year] = Employees[i - 1, j - 1, year - 1] * (1.0 - ProbSeparate)
    return Employees[:, :, year].copy()


def ComputeAnnuity(COLA):
    AnnuityVector = np.zeros(g.EmployeeEnd - g.EmployeeStart + 1)
    for i in range(1, g.EmployeeEnd - g.EmployeeStart + 2):   # R: 1:(EmployeeEnd-EmployeeStart+1)
        liveProb    = 1.0
        curage      = i
        annuityFactor = 0.0
        for m in range(curage, g.MortalityTable.shape[0] + 1):  # R: curage:dim(MortalityTable)[1]
            liveProb       = (1.0 - g.MortalityTable[m - 1, 1]) * liveProb
            annuityFactor += (liveProb
                              * (1.0 / (1.0 + g.annuity_dr)) ** (m - curage)
                              * (1.0 + COLA) ** (m - curage))
        AnnuityVector[i - 1] = annuityFactor
    return AnnuityVector


# ---------------------------------------------------------------------------
# Main simulation loops
# ---------------------------------------------------------------------------

def Main_Current(ActiveNumber, InactiveNumber, COLA_f, WageYears_f, BenefitCap_f,
                 BenefitFactor_f, RetirementStart_f, NyearFullBenefit_f, CurrentTier=True):
    from liability_cf_model import PVNC_Calc, TotalLiabilities_Current

    # R: <<- assignments
    g.COLA             = COLA_f
    g.WageYears        = int(WageYears_f)
    g.BenefitCap       = BenefitCap_f
    g.BenefitFactor    = BenefitFactor_f
    g.RetirementStart  = int(RetirementStart_f)
    g.NyearFullBenefit = int(NyearFullBenefit_f)

    Nyear  = g.Nyear
    NMonte = g.NMonte

    # R: array(ActiveNumber, c(dim(ActiveNumber), Nyear)); [,,2:Nyear]<-0
    AN = np.zeros((ActiveNumber.shape[0], ActiveNumber.shape[1], Nyear))
    AN[:, :, 0] = ActiveNumber

    IN = np.zeros((InactiveNumber.shape[0], InactiveNumber.shape[1], Nyear))
    IN[:, :, 0] = InactiveNumber

    InactiveBenefits = np.zeros_like(IN)
    for i in range(1, IN.shape[0] + 1):
        for j in range(1, IN.shape[1] + 1):
            if IN[i - 1, j - 1, 0] != 0.0:
                InactiveBenefits[i - 1, j - 1, 0] = (g.BaseWage[i - 1, j - 1, 0]
                                                       * min(BenefitFactor_f * j, BenefitCap_f))

    RetirementNumber  = np.zeros((120 - 40 + 1, 1, Nyear))
    RetirementBenefit = np.zeros((120 - 40 + 1, 1, Nyear))

    AAL                        = np.zeros((Nyear, NMonte))
    CashOutflow                = np.zeros((Nyear, NMonte))
    CashInflow                 = np.zeros((Nyear, NMonte))
    PresentValueFutureBenefits = np.zeros((Nyear, 2))
    PresentValueNormalCost     = np.zeros((Nyear, 1))
    NormalCost                 = np.zeros((Nyear, 1))
    PVFS_vec                   = np.zeros((Nyear, 1))

    PVNC_Values = PVNC_Calc(AN, IN, InactiveBenefits, RetirementNumber,
                             RetirementBenefit, g.BaseWage, 80, 1, g.discountrate)

    for n in range(1, NMonte + 1):                              # R: for n in 1:NMonte
        AN[:, :, 1:] = 0.0
        IN[:, :, 1:] = 0.0
        g.BaseWage[:, :, 1:] = 0.0
        InactiveBenefits[:, :, 1:] = 0.0
        RetirementNumber[:, :, 1:]  = 0.0
        RetirementBenefit[:, :, 1:] = 0.0

        for t in range(1, Nyear):                               # R: for t in 1:(Nyear-1)
            if PresentValueFutureBenefits[t - 1, :].sum() == 0.0:
                PresentValueFutureBenefits[t - 1, :] = TotalLiabilities_Current(
                    AN, IN, InactiveBenefits, g.BaseWage, 80, t, g.discountrate, g.scaling)

                PVFS  = PVNC_Values[1] * (1.0 + g.Inflation) ** (t - 1)
                NCxs  = PVNC_Values[0] * (1.0 + g.Inflation) ** (t - 1)
                PVNC_val = 0.0
                NC_val   = 0.0
                for i in range(1, AN.shape[0] + 1):
                    for j in range(1, min(i, AN.shape[1]) + 1):
                        PVNC_val += AN[i - 1, j - 1, t - 1] * NCxs[i - 1] * PVFS[i - 1, j - 1]
                        NC_val   += AN[i - 1, j - 1, t - 1] * NCxs[i - 1] * g.BaseWage[i - 1, j - 1, t - 1]
                PresentValueNormalCost[t - 1, 0] = PVNC_val
                NormalCost[t - 1, 0]             = NC_val
                PVFS_vec[t - 1, 0]               = float(PVFS.sum())

            AAL[t - 1, n - 1] = ((PresentValueFutureBenefits[t - 1, 0]
                                   - PresentValueNormalCost[t - 1, 0])
                                  + PresentValueFutureBenefits[t - 1, 1])

            RefundAmount    = Refund(AN[:, :, t - 1], g.SeparationRate, g.RefundRate, g.BaseWage, t)
            DeathAmount     = DeathPay(AN[:, :, t - 1], IN[:, :, t - 1],
                                       InactiveBenefits[:, :, t - 1], g.BaseWage[:, :, t - 1],
                                       g.MortalityTable)
            DisabilityAmount = float((g.BaseWage[:, :, t - 1] * AN[:, :, t - 1]).sum()) * g.DisabilityPayoutRate

            CashOutflow[t - 1, n - 1] = (float((RetirementNumber[:, :, t - 1]
                                                 * RetirementBenefit[:, :, t - 1]).sum())
                                          + RefundAmount + DeathAmount + DisabilityAmount)
            CashInflow[t - 1, n - 1]  = (float((g.BaseWage[:, :, t - 1] * AN[:, :, t - 1]).sum())
                                          * (g.EmployeeContributionRate + g.EmployerContributionRate))

            TotalEmployees = float(AN[:, :, t - 1].sum()) * (1.0 + g.PopulationGrowth)
            g.BaseWage[:, :, t] = g.BaseWage[:, :, t - 1] * (1.0 + g.WageGrowth)

            if CurrentTier:
                AN[:, :, t] = UpdateEmployeeCount(AN, g.SeparationRate, g.RetirementRate,
                                                  g.MortalityTable, TotalEmployees, t)
            else:
                AN[:, :, t] = L_UpdateEmployeeCount(AN, g.SeparationRate, g.RetirementRate,
                                                    g.MortalityTable, t)

            IN[:, :, t]                = UpdateInactiveCount(AN, IN, g.SeparationRate,
                                                              g.RefundRate, g.MortalityTable, t)
            InactiveBenefits[:, :, t]  = UpdateInactiveBenefits(IN, AN, g.BaseWage,
                                                                  InactiveBenefits, g.SeparationRate, t)
            RetirementNumber[:, :, t]  = UpdateRetirementNumber(RetirementNumber, AN, IN,
                                                                  g.RetirementRate, g.MortalityTable, t)
            RetirementBenefit[:, :, t] = UpdateRetirementBenefit(RetirementBenefit, RetirementNumber,
                                                                   g.BaseWage, g.COLA, g.MortalityTable,
                                                                   IN, InactiveBenefits, AN,
                                                                   g.RetirementRate, BenefitFactor_f, t)

    return [AAL, CashOutflow, CashInflow, PresentValueFutureBenefits, NormalCost]


def Main_Ret(RetirementNumber, RetirementBenefit):
    from liability_cf_model import TotalLiabilities_Ret

    Nyear  = g.Nyear
    NMonte = g.NMonte

    # R: array(RetirementNumber, c(dim, Nyear)); [,,2:Nyear]<-0
    RN = np.zeros((RetirementNumber.shape[0], RetirementNumber.shape[1], Nyear))
    RN[:, :, 0] = RetirementNumber

    RB = np.zeros((RetirementBenefit.shape[0], RetirementBenefit.shape[1], Nyear))
    RB[:, :, 0] = RetirementBenefit

    AgeSerDim    = (g.EmployeeEnd - g.EmployeeStart + 1, g.ServiceEnd - g.ServiceStart + 1)
    AN_zero      = np.zeros((*AgeSerDim, Nyear))
    IN_zero      = np.zeros((*AgeSerDim, Nyear))
    BW_zero      = np.zeros((*AgeSerDim, Nyear))
    IB_zero      = np.zeros((*AgeSerDim, Nyear))

    AAL                        = np.zeros((Nyear, NMonte))
    CashOutflow                = np.zeros((Nyear, NMonte))
    PresentValueFutureBenefits = np.zeros((Nyear, 1))

    for n in range(1, NMonte + 1):
        RN[:, :, 1:] = 0.0
        RB[:, :, 1:] = 0.0

        for t in range(1, Nyear):
            if PresentValueFutureBenefits[t - 1, :].sum() == 0.0:
                PresentValueFutureBenefits[t - 1, :] = TotalLiabilities_Ret(
                    RN, RB, 80, t, g.discountrate, g.scaling)

            AAL[t - 1, n - 1]         = PresentValueFutureBenefits[t - 1, 0]
            CashOutflow[t - 1, n - 1] = float((RN[:, :, t - 1] * RB[:, :, t - 1]).sum())

            RN[:, :, t] = UpdateRetirementNumber(RN, AN_zero, IN_zero,
                                                  g.RetirementRate, g.MortalityTable, t)
            RB[:, :, t] = UpdateRetirementBenefit(RB, RN, BW_zero, g.COLA, g.MortalityTable,
                                                   IN_zero, IB_zero, AN_zero,
                                                   g.RetirementRate, g.BenefitFactor, t)

    return [AAL, CashOutflow]
