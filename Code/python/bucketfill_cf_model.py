import numpy as np
import g


def LinearFill(Collapsed, Slope=1, retirement=False):
    if retirement:
        all_age_max, all_age_min = 120, 40
        all_serv_max, all_serv_min = 1, 1
        Expanded = np.zeros((all_age_max - all_age_min + 1, all_serv_max - all_serv_min + 1))
        rowmins = np.array([40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115])
        rowmaxs = rowmins + 4
        colmins = np.array([1])
        colmaxs = np.array([1])
    else:
        all_age_max, all_age_min = 74, 20
        all_serv_max, all_serv_min = 54, 0
        Expanded = np.zeros((all_age_max - all_age_min + 1, all_serv_max - all_serv_min + 1))
        rowmins = np.array([20,25,30,35,40,45,50,55,60,65,70])
        rowmaxs = rowmins + 4
        colmins = np.array([0,5,10,15,20,25,30,35,40,45,50])
        colmaxs = colmins + 4

    for i in range(1, Collapsed.shape[0] + 1):          # R: for i in 1:nrow(Collapsed)
        rowmin = int(rowmins[i - 1])
        rowmax = int(rowmaxs[i - 1])
        for j in range(1, Collapsed.shape[1] + 1):      # R: for j in 1:ncol(Collapsed)
            columnmin = int(colmins[j - 1])
            columnmax = int(colmaxs[j - 1])
            N = rowmax - rowmin + 1
            M = columnmax - columnmin + 1
            GroupCount = Collapsed[i - 1, j - 1]
            Share = np.zeros((N, M))
            sharesum = 0.0
            for k in range(1, N + 1):                   # R: for k in 1:N
                svcmax = rowmin + k - all_age_min
                for L in range(1, M + 1):               # R: for L in 1:M
                    if (columnmin + L - 1) > svcmax:
                        Share[k - 1, L - 1] = 0.0
                    else:
                        Share[k - 1, L - 1] = GroupCount / (N * M) + Slope * (rowmin + k - 1)
                    sharesum += Share[k - 1, L - 1]
            # R: Expanded[(rowmin+1-all_age_min):(rowmax+1-all_age_min), (columnmin+1-all_serv_min):(columnmax+1-all_serv_min)]
            row_s = rowmin - all_age_min
            row_e = rowmax - all_age_min + 1
            col_s = columnmin - all_serv_min
            col_e = columnmax - all_serv_min + 1
            if sharesum != 0.0:
                Expanded[row_s:row_e, col_s:col_e] = Share * GroupCount / sharesum

    Expanded[np.isnan(Expanded)] = 0.0
    return Expanded


def ConstantFill(Collapsed, enforce_service_limit=True, retirement=False):
    if retirement:
        all_age_max, all_age_min = 120, 40
        all_serv_max, all_serv_min = 1, 1
        Expanded = np.zeros((all_age_max - all_age_min + 1, all_serv_max - all_serv_min + 1))
        rowmins = np.array([40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115])
        rowmaxs = rowmins + 4
        colmins = np.array([1])
        colmaxs = np.array([1])
    else:
        all_age_max, all_age_min = 74, 20
        all_serv_max, all_serv_min = 54, 0
        Expanded = np.zeros((all_age_max - all_age_min + 1, all_serv_max - all_serv_min + 1))
        rowmins = np.array([20,25,30,35,40,45,50,55,60,65,70])
        rowmaxs = rowmins + 4
        colmins = np.array([0,5,10,15,20,25,30,35,40,45,50])
        colmaxs = colmins + 4

    for i in range(1, Collapsed.shape[0] + 1):
        rowmin = int(rowmins[i - 1])
        rowmax = int(rowmaxs[i - 1])
        for j in range(1, Collapsed.shape[1] + 1):
            columnmin = int(colmins[j - 1])
            columnmax = int(colmaxs[j - 1])
            N = rowmax - rowmin + 1
            M = columnmax - columnmin + 1
            GroupValue = Collapsed[i - 1, j - 1]
            if enforce_service_limit:
                Share = np.zeros((N, M))
                for k in range(1, N + 1):
                    svcmax = rowmin + k - all_age_min
                    for L in range(1, M + 1):
                        if (columnmin + L - 1) > svcmax:
                            Share[k - 1, L - 1] = 0.0
                        else:
                            Share[k - 1, L - 1] = GroupValue
            else:
                Share = np.full((N, M), float(GroupValue))
            row_s = rowmin - all_age_min
            row_e = rowmax - all_age_min + 1
            col_s = columnmin - all_serv_min
            col_e = columnmax - all_serv_min + 1
            Expanded[row_s:row_e, col_s:col_e] = Share

    Expanded[np.isnan(Expanded)] = 0.0
    return Expanded


def ConstantFill_SepRate(Collapsed):
    all_age_max, all_age_min = 74, 20
    all_serv_max, all_serv_min = 54, 0
    Expanded = np.zeros((all_age_max - all_age_min + 1, all_serv_max - all_serv_min + 1))

    rows = range(20, 75)   # R: c(20:74)
    cols = range(1, 56)    # R: c(1:55)

    ages  = Collapsed[1:12, 0].astype(float).copy()   # R: Collapsed[2:12, 1]
    servs = Collapsed[0, 1:12].astype(float).copy()   # R: Collapsed[1, 2:12]

    if servs[0] == 0:
        servs = servs + 1

    for i in rows:
        for j in cols:
            list1 = ages - i
            list1 = np.where(list1 < 0, 100.0, list1)
            if int(np.sum(list1 == 100)) == 11:
                list1[10] = 0.0                        # R: list1[11] <- 0
            age_row = int(np.where(list1 == np.min(np.abs(list1)))[0][0]) + 1  # R: which(...)+1

            list2 = servs - j
            list2 = np.where(list2 < 0, 100.0, list2)
            if int(np.sum(list2 == 100)) == 11:
                list2[10] = 0.0
            serv_col = int(np.where(list2 == np.min(np.abs(list2)))[0][0]) + 1

            if i - j + 1 < all_age_min:
                GroupValue = 0.0
            else:
                GroupValue = float(Collapsed[age_row, serv_col])  # R: Collapsed[age_index, serv_index]

            Expanded[i - all_age_min, j - 1] = GroupValue  # R: Expanded[i-all_age_min+1, j]

    Expanded[np.isnan(Expanded)] = 0.0
    return Expanded


def MortTable(collapsed_mort, pct_male):
    # Returns numpy array (n_ages, 2): col 0 = Age, col 1 = Death_Prob
    # Mirrors R data.frame with columns Age, Death_Prob; accessed as MortTable[i,2] -> [i-1,1]
    ages_range = range(g.EmployeeStart, 120)
    result = np.zeros((len(ages_range), 2))
    for count, i in enumerate(ages_range):
        result[count, 0] = i
        if i < 30:
            row = collapsed_mort[collapsed_mort['Age'] == 30]
            result[count, 1] = float(row['M'].iloc[0]) * pct_male + float(row['F'].iloc[0]) * (1 - pct_male)
        elif 30 <= i < 100:
            decade = (i // 10) * 10
            rows = collapsed_mort[collapsed_mort['Age'] == decade]
            result[count, 1] = float(rows['M'].mean()) * pct_male + float(rows['F'].mean()) * (1 - pct_male)
        else:
            row = collapsed_mort[collapsed_mort['Age'] == 90]
            result[count, 1] = float(row['M'].iloc[0]) * pct_male + float(row['F'].iloc[0]) * (1 - pct_male)
    return result


def Calc_Inactive(active, withdrawal, refund, MortalityTable_f, RetirementStart_f, NyearFullBenefit_f):
    from functions_cf_model import UpdateEmployeeCount, UpdateInactiveCount
    g.RetirementStart  = int(RetirementStart_f)   # R: RetirementStart <<- RetirementStart_f
    g.NyearFullBenefit = int(NyearFullBenefit_f)  # R: NyearFullBenefit <<- NyearFullBenefit_f

    ws = 5000  # workspace — not projection horizon (R: Nyear <- 5000 local)

    ActiveNumber   = np.zeros((active.shape[0], active.shape[1], ws))
    ActiveNumber[:, :, 0] = active                         # R: array(active, c(dim(active),Nyear)); [,,2:Nyear]<-0
    InactiveNumber = np.zeros((active.shape[0], active.shape[1], ws))  # R: [,,1:Nyear]<-0

    TotalEmployees = float(ActiveNumber[:, :, 0].sum())    # R: sum(ActiveNumber[,,1])

    # R: ActiveNumber[,,2] <- UpdateEmployeeCount(ActiveNumber,...,1)
    ActiveNumber[:, :, 1] = UpdateEmployeeCount(ActiveNumber, withdrawal, g.RetirementRate,
                                                 MortalityTable_f, TotalEmployees, 1)
    # R: InactiveNumber[,,2] <- UpdateInactiveCount(ActiveNumber,InactiveNumber,...,1)
    InactiveNumber[:, :, 1] = UpdateInactiveCount(ActiveNumber, InactiveNumber,
                                                   withdrawal, refund, MortalityTable_f, 1)
    t = 2  # R: t <- 2
    while (abs(float(np.mean(InactiveNumber[:, :, t - 1] - InactiveNumber[:, :, t - 2]))) > 0.00005
           and t < ws):
        ActiveNumber[:, :, t] = UpdateEmployeeCount(ActiveNumber, withdrawal, g.RetirementRate,
                                                     MortalityTable_f, TotalEmployees, t)
        InactiveNumber[:, :, t] = UpdateInactiveCount(ActiveNumber, InactiveNumber,
                                                       withdrawal, refund, MortalityTable_f, t)
        t += 1

    if t >= ws:
        import warnings
        warnings.warn(f"Calc_Inactive reached {ws} iterations before satisfying the convergence tolerance.")

    final = InactiveNumber[:, :, t - 1]
    total = float(final.sum())
    denom = total / total if total != 0.0 else float('nan')  # R: is.nan(sum(InactiveNumber[,,t]/sum(...)))
    if np.isnan(denom):
        result = np.zeros(active.shape)
        nfb = int(NyearFullBenefit_f)
        sub = ActiveNumber[:, nfb - 1:55, 0]              # R: ActiveNumber[,NyearFullBenefit_f:55,1]
        denom2 = float(sub.sum())
        result[:, nfb - 1:55] = sub / denom2 if denom2 != 0.0 else 0.0
        return result
    else:
        return final / total                               # R: InactiveNumber[,,t]/sum(InactiveNumber[,,t])


def CreateTiers(active, inactive, num_tiers):
    ts = g.tier_serivce  # 0-based Python list/array of tier service boundaries

    def _zero_outside(mat, keep_from, keep_to):
        # keep columns [keep_from:keep_to] (Python 0-based), zero rest
        # R's a:b for a>=b is a descending sequence spanning both endpoints;
        # expand the keep range to match (e.g. keep_from==keep_to=41 → [40:42])
        if keep_from >= keep_to:
            keep_from, keep_to = keep_to - 1, keep_from + 1
        out = mat.copy()
        if keep_from > 0:
            out[:, :keep_from] = 0
        if keep_to < out.shape[1]:
            out[:, keep_to:] = 0
        return out

    if num_tiers == 1:
        # R: active_t1 <<- active; inactive_t1 <<- inactive
        g.active_t1   = active.copy()
        g.inactive_t1 = inactive.copy()

    elif num_tiers == 2:
        # R: active_t1[,-c((tier_serivce[2]+1):55)] <<- 0  (keep cols tier_serivce[2]:55, 1-based → Python ts[1]:55)
        g.active_t1   = _zero_outside(active,   ts[1], 55)
        g.active_t2   = _zero_outside(active,   0, ts[1])
        g.inactive_t1 = _zero_outside(inactive, ts[1], 55)
        g.inactive_t2 = _zero_outside(inactive, 0, ts[1])

    elif num_tiers == 3:
        g.active_t1   = _zero_outside(active,   ts[1], 55)
        g.active_t2   = _zero_outside(active,   ts[2], ts[1])
        g.active_t3   = _zero_outside(active,   0, ts[2])
        g.inactive_t1 = _zero_outside(inactive, ts[1], 55)
        g.inactive_t2 = _zero_outside(inactive, ts[2], ts[1])
        g.inactive_t3 = _zero_outside(inactive, 0, ts[2])

    elif num_tiers == 4:
        g.active_t1   = _zero_outside(active,   ts[1], 55)
        g.active_t2   = _zero_outside(active,   ts[2], ts[1])
        g.active_t3   = _zero_outside(active,   ts[3], ts[2])
        g.active_t4   = _zero_outside(active,   0, ts[3])
        g.inactive_t1 = _zero_outside(inactive, ts[1], 55)
        g.inactive_t2 = _zero_outside(inactive, ts[2], ts[1])
        g.inactive_t3 = _zero_outside(inactive, ts[3], ts[2])
        g.inactive_t4 = _zero_outside(inactive, 0, ts[3])

    elif num_tiers == 5:
        g.active_t1   = _zero_outside(active,   ts[1], 55)
        g.active_t2   = _zero_outside(active,   ts[2], ts[1])
        g.active_t3   = _zero_outside(active,   ts[3], ts[2])
        g.active_t4   = _zero_outside(active,   ts[4], ts[3])
        g.active_t5   = _zero_outside(active,   0, ts[4])
        g.inactive_t1 = _zero_outside(inactive, ts[1], 55)
        g.inactive_t2 = _zero_outside(inactive, ts[2], ts[1])
        g.inactive_t3 = _zero_outside(inactive, ts[3], ts[2])
        g.inactive_t4 = _zero_outside(inactive, ts[4], ts[3])
        g.inactive_t5 = _zero_outside(inactive, 0, ts[4])

    else:  # 6
        g.active_t1   = _zero_outside(active,   ts[1], 55)
        g.active_t2   = _zero_outside(active,   ts[2], ts[1])
        g.active_t3   = _zero_outside(active,   ts[3], ts[2])
        g.active_t4   = _zero_outside(active,   ts[4], ts[3])
        g.active_t5   = _zero_outside(active,   ts[5], ts[4])
        g.active_t6   = _zero_outside(active,   0, ts[5])
        g.inactive_t1 = _zero_outside(inactive, ts[1], 55)
        g.inactive_t2 = _zero_outside(inactive, ts[2], ts[1])
        g.inactive_t3 = _zero_outside(inactive, ts[3], ts[2])
        g.inactive_t4 = _zero_outside(inactive, ts[4], ts[3])
        g.inactive_t5 = _zero_outside(inactive, ts[5], ts[4])
        g.inactive_t6 = _zero_outside(inactive, 0, ts[5])
