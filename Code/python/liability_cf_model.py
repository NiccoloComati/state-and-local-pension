import numpy as np
import g
from functions_cf_model import (Refund, DeathPay, UpdateInactiveCount, UpdateInactiveBenefits,
                                  UpdateRetirementNumber, UpdateRetirementBenefit,
                                  L_UpdateEmployeeCount, PastWages)


def PVNC_Calc(Employees, Inactive, InactiveBen, RetNum, RetBen, Wage, L_Nyear, Year, DiscountRate):
    # Year: 1-based
    n_age  = Employees.shape[0]
    n_svc  = Employees.shape[1]

    # R: L_BaseWage <- array(Wage[,,Year], c(dim, L_Nyear)); [,,2:L_Nyear]<-0
    L_BaseWage = np.zeros((n_age, n_svc, L_Nyear))
    L_BaseWage[:, :, 0] = Wage[:, :, Year - 1]

    L_ActiveNumber   = np.zeros((n_age, n_svc, L_Nyear))
    L_InactiveNumber = np.zeros((n_age, n_svc, L_Nyear))
    L_InactiveBenefits = np.zeros((n_age, n_svc, L_Nyear))

    n_ret = len(RetNum[:, :, Year - 1].ravel())
    L_RetirementNumber  = np.zeros((n_ret, 1, L_Nyear))
    L_RetirementBenefit = np.zeros((n_ret, 1, L_Nyear))

    CashOutflow = np.zeros((L_Nyear, 1))
    PVFB = np.zeros(n_age)

    for a in range(1, n_age + 1):                          # R: for a in 1:dim(Employees)[1]
        L_BaseWage[:, :, 1:]    = 0.0
        L_ActiveNumber[:, :, :] = 0.0
        L_InactiveNumber[:, :, :] = 0.0
        L_InactiveBenefits[:, :, :] = 0.0
        L_RetirementNumber[:, :, :] = 0.0
        L_RetirementBenefit[:, :, :] = 0.0
        L_ActiveNumber[a - 1, 0, 0] = 1.0                 # R: L_ActiveNumber[a,1,1] <- 1

        CashOutflow[:] = 0.0

        for t in range(1, L_Nyear):                        # R: for t in 1:(L_Nyear-1)
            RefundAmount  = Refund(L_ActiveNumber[:, :, t - 1], g.SeparationRate, g.RefundRate,
                                   L_BaseWage, t)
            DeathAmount   = DeathPay(L_ActiveNumber[:, :, t - 1], L_InactiveNumber[:, :, t - 1],
                                     L_InactiveBenefits[:, :, t - 1], L_BaseWage[:, :, t - 1],
                                     g.MortalityTable)
            DisabilityAmount = float((L_BaseWage[:, :, t - 1] * L_ActiveNumber[:, :, t - 1]).sum()) * g.DisabilityPayoutRate

            CashOutflow[t - 1, 0] = (float((L_RetirementNumber[:, :, t - 1]
                                             * L_RetirementBenefit[:, :, t - 1]).sum())
                                      + RefundAmount + DeathAmount)

            L_ActiveNumber[:, :, t]   = L_UpdateEmployeeCount(L_ActiveNumber, g.SeparationRate,
                                                                g.RetirementRate, g.MortalityTable, t)
            L_BaseWage[:, :, t]        = L_BaseWage[:, :, t - 1] * (1.0 + g.WageGrowth)
            L_InactiveNumber[:, :, t]  = UpdateInactiveCount(L_ActiveNumber, L_InactiveNumber,
                                                              g.SeparationRate, g.RefundRate,
                                                              g.MortalityTable, t)
            L_InactiveBenefits[:, :, t] = UpdateInactiveBenefits(L_InactiveNumber, L_ActiveNumber,
                                                                   L_BaseWage, L_InactiveBenefits,
                                                                   g.SeparationRate, t)
            L_RetirementNumber[:, :, t]  = UpdateRetirementNumber(L_RetirementNumber, L_ActiveNumber,
                                                                    L_InactiveNumber, g.RetirementRate,
                                                                    g.MortalityTable, t)
            L_RetirementBenefit[:, :, t] = UpdateRetirementBenefit(L_RetirementBenefit, L_RetirementNumber,
                                                                     L_BaseWage, g.COLA, g.MortalityTable,
                                                                     L_InactiveNumber, L_InactiveBenefits,
                                                                     L_ActiveNumber, g.RetirementRate,
                                                                     g.BenefitFactor, t)

        liability = 0.0
        for i in range(1, CashOutflow.shape[0] + 1):      # R: 1:dim(CashOutflow)[1]
            liability += CashOutflow[i - 1, 0] / (1.0 + DiscountRate) ** i
        PVFB[a - 1] = liability

    # Present Value Future Salaries
    PVFS = np.zeros((n_age, n_svc))
    for i in range(1, n_age + 1):
        for j in range(1, min(i, n_svc) + 1):
            YearsLeftToWork = min(n_age - i, n_svc - j)
            ListWage = PastWages(L_BaseWage,
                                 i + YearsLeftToWork, j + YearsLeftToWork,
                                 j + YearsLeftToWork, j + YearsLeftToWork)
            ProbTracker = 1.0
            tempsum     = 0.0
            for m in range(0, YearsLeftToWork + 1):       # R: 0:YearsLeftToWork
                jm = j + m
                ProbSeparate = (g.SeparationRate[i + m - 1, j + m - 1]
                                + g.MortalityTable[i + m - 1, 1]
                                + g.RetirementRate[i + m - 1, jm - 1])
                ProbSeparate = min(ProbSeparate, 1.0)
                ProbTracker  = (1.0 - ProbSeparate) * ProbTracker
                tempsum     += ListWage[m] * ProbTracker / (1.0 + DiscountRate) ** m
            PVFS[i - 1, j - 1] = tempsum

    NCxs = PVFB / PVFS[:, 0]
    NCxs[np.isnan(NCxs) | np.isinf(NCxs)] = 0.0
    if np.isnan(NCxs.sum()):
        raise ValueError("PVFS must be numeric")

    return [NCxs, PVFS]


def TotalLiabilities_Current(Employees, Inactive, InactiveBen, Wage, L_Nyear, Year, DiscountRate, Scaling):
    # Year: 1-based
    n_age = Employees.shape[0]
    n_svc = Employees.shape[1]

    L_BaseWage = np.zeros((n_age, n_svc, L_Nyear))
    L_BaseWage[:, :, 0] = Wage[:, :, Year - 1]

    L_ActiveNumber_base   = np.zeros((n_age, n_svc, L_Nyear))
    L_ActiveNumber_base[:, :, 0] = Employees[:, :, Year - 1]

    L_InactiveNumber_base = np.zeros((n_age, n_svc, L_Nyear))
    L_InactiveNumber_base[:, :, 0] = Inactive[:, :, Year - 1]

    L_InactiveBenefits_base = np.zeros((n_age, n_svc, L_Nyear))
    L_InactiveBenefits_base[:, :, 0] = InactiveBen[:, :, Year - 1]

    L_RetirementNumber_base  = np.zeros((120 - 40 + 1, 1, L_Nyear))
    L_RetirementBenefit_base = np.zeros((120 - 40 + 1, 1, L_Nyear))

    L_CashOutflow = np.zeros((L_Nyear, 2))

    for i_loop in range(1, 3):                             # R: for i in c(1:2)
        L_ActiveNumber    = L_ActiveNumber_base.copy()
        L_InactiveNumber  = L_InactiveNumber_base.copy()
        L_InactiveBenefits = L_InactiveBenefits_base.copy()
        L_RetirementNumber  = L_RetirementNumber_base.copy()
        L_RetirementBenefit = L_RetirementBenefit_base.copy()

        if i_loop == 1:                                    # R: active path only
            L_InactiveNumber[:, :, :] = 0.0
            L_InactiveBenefits[:, :, :] = 0.0
            L_RetirementNumber[:, :, :] = 0.0
            L_RetirementBenefit[:, :, :] = 0.0
        else:                                              # R: inactive+retiree path only
            L_ActiveNumber[:, :, :] = 0.0
            L_RetirementNumber[:, :, :] = 0.0
            L_RetirementBenefit[:, :, :] = 0.0

        for t in range(1, L_Nyear):
            RefundAmount  = Refund(L_ActiveNumber[:, :, t - 1], g.SeparationRate, g.RefundRate,
                                   L_BaseWage, t)
            DeathAmount   = DeathPay(L_ActiveNumber[:, :, t - 1], L_InactiveNumber[:, :, t - 1],
                                     L_InactiveBenefits[:, :, t - 1], L_BaseWage[:, :, t - 1],
                                     g.MortalityTable)
            DisabilityAmount = float((L_BaseWage[:, :, t - 1] * L_ActiveNumber[:, :, t - 1]).sum()) * g.DisabilityPayoutRate

            L_CashOutflow[t - 1, i_loop - 1] = (
                (float((L_RetirementNumber[:, :, t - 1] * L_RetirementBenefit[:, :, t - 1]).sum())
                 + RefundAmount + DeathAmount + DisabilityAmount) * Scaling)

            L_ActiveNumber[:, :, t]    = L_UpdateEmployeeCount(L_ActiveNumber, g.SeparationRate,
                                                                 g.RetirementRate, g.MortalityTable, t)
            L_BaseWage[:, :, t]         = L_BaseWage[:, :, t - 1] * (1.0 + g.WageGrowth)
            L_InactiveNumber[:, :, t]   = UpdateInactiveCount(L_ActiveNumber, L_InactiveNumber,
                                                               g.SeparationRate, g.RefundRate,
                                                               g.MortalityTable, t)
            L_InactiveBenefits[:, :, t] = UpdateInactiveBenefits(L_InactiveNumber, L_ActiveNumber,
                                                                   L_BaseWage, L_InactiveBenefits,
                                                                   g.SeparationRate, t)
            L_RetirementNumber[:, :, t]  = UpdateRetirementNumber(L_RetirementNumber, L_ActiveNumber,
                                                                    L_InactiveNumber, g.RetirementRate,
                                                                    g.MortalityTable, t)
            L_RetirementBenefit[:, :, t] = UpdateRetirementBenefit(L_RetirementBenefit, L_RetirementNumber,
                                                                     L_BaseWage, g.COLA, g.MortalityTable,
                                                                     L_InactiveNumber, L_InactiveBenefits,
                                                                     L_ActiveNumber, g.RetirementRate,
                                                                     g.BenefitFactor, t)

    Active_liability = sum(L_CashOutflow[i - 1, 0] / (1.0 + DiscountRate) ** i
                           for i in range(1, L_CashOutflow.shape[0] + 1))

    Nonactive_liability = sum(L_CashOutflow[i - 1, 1] / (1.0 + DiscountRate) ** i
                              for i in range(1, L_CashOutflow.shape[0] + 1))

    return np.array([Active_liability, Nonactive_liability])


def TotalLiabilities_Ret(RetNum, RetBen, L_Nyear, Year, DiscountRate, Scaling):
    # Year: 1-based
    AgeSerDim = (g.EmployeeEnd - g.EmployeeStart + 1, g.ServiceEnd - g.ServiceStart + 1)

    L_BaseWage         = np.zeros((*AgeSerDim, L_Nyear))
    L_ActiveNumber     = np.zeros((*AgeSerDim, L_Nyear))
    L_InactiveNumber   = np.zeros((*AgeSerDim, L_Nyear))
    L_InactiveBenefits = np.zeros((*AgeSerDim, L_Nyear))

    n_ret = len(RetNum[:, :, Year - 1].ravel())
    L_RetirementNumber  = np.zeros((n_ret, 1, L_Nyear))
    L_RetirementNumber[:, :, 0]  = RetNum[:, :, Year - 1]

    L_RetirementBenefit = np.zeros((n_ret, 1, L_Nyear))
    L_RetirementBenefit[:, :, 0] = RetBen[:, :, Year - 1]

    L_CashOutflow = np.zeros((L_Nyear, 1))

    for t in range(1, L_Nyear):
        L_CashOutflow[t - 1, 0] = (float((L_RetirementNumber[:, :, t - 1]
                                           * L_RetirementBenefit[:, :, t - 1]).sum()) * Scaling)
        L_RetirementNumber[:, :, t]  = UpdateRetirementNumber(L_RetirementNumber, L_ActiveNumber,
                                                               L_InactiveNumber, g.RetirementRate,
                                                               g.MortalityTable, t)
        L_RetirementBenefit[:, :, t] = UpdateRetirementBenefit(L_RetirementBenefit, L_RetirementNumber,
                                                                L_BaseWage, g.COLA, g.MortalityTable,
                                                                L_InactiveNumber, L_InactiveBenefits,
                                                                L_ActiveNumber, g.RetirementRate,
                                                                g.BenefitFactor, t)

    Retire_liability = sum(L_CashOutflow[i - 1, 0] / (1.0 + DiscountRate) ** i
                           for i in range(1, L_CashOutflow.shape[0] + 1))

    return Retire_liability
