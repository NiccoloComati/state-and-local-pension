import numpy as np
from engine import state as g

# ---------------------------------------------------------------------------
# Within-band tilt, taken from the data (2026-07-30).
#
# LinearFill splits a 5-year band into single years. How the count should slope
# inside a band is not a free choice - the neighbouring bands already say it. If
# the 75-79 band holds 385 people and 80-84 holds 223, the population is falling
# by a factor 0.58 per band, and the slope inside the band should be consistent
# with that. Where the population is still RISING (the young retiree bands, as
# people retire into them) the slope inside the band rises too.
#
# This replaces a hand-set constant. Checked against two independent readings and
# both agree there is no single right constant:
#   - the ORIGINAL formula was, population-weighted, effectively assuming a tilt
#     of +0.0009 (an even split) while individual bands ranged -0.95 to +1.38;
#   - the DATA implies a population-weighted tilt of -0.010 (also ~even), with a
#     genuine spread across bands (unweighted median +0.098, IQR -0.25 to +0.18).
# A fixed constant would impose one slope everywhere and get the young bands
# backwards. Deriving it per band costs nothing and needs no parameter.
# ---------------------------------------------------------------------------
TILT_CAP = 0.9          # keeps every weight strictly positive


def _band_tilt(Collapsed, i, j, cap=TILT_CAP):
    """Tilt for band (i, j), from how fast the count changes to its neighbours.

    r = geometric mean of the available neighbour ratios along the age axis
    q = r ** ((N-1)/N)    the first-to-last ratio that implies INSIDE the band
    s = (1-q)/(1+q)       the tilt reproducing it; s>0 declines, s<0 rises
    Edge bands use their one neighbour; an isolated or empty band gets s = 0,
    i.e. an even split.
    """
    c = Collapsed[:, j]
    if not np.isfinite(c[i]) or c[i] <= 0:
        return 0.0
    ratios = []
    if i + 1 < len(c) and np.isfinite(c[i+1]) and c[i+1] > 0:
        ratios.append(c[i+1] / c[i])
    if i - 1 >= 0 and np.isfinite(c[i-1]) and c[i-1] > 0:
        ratios.append(c[i] / c[i-1])
    if not ratios:
        return 0.0
    r = float(np.exp(np.mean(np.log(ratios))))
    q = r ** 0.8                      # (N-1)/N with N = 5
    s = (1.0 - q) / (1.0 + q)
    return float(np.clip(s, -cap, cap))


def LinearFill_incorrect(Collapsed, Slope=1, retirement=False):
    """SUPERSEDED 2026-07-30. Kept, unchanged, so earlier results stay reproducible.

    This is the weight inherited from the original R implementation. It is wrong,
    and `Code/R/cluster_code_2022/*.R` still calls the R twin of this function on
    purpose so that lineage keeps producing exactly what it always produced.

    The weight was  Share = GroupCount/(N*M) + Slope*age , which
      1. subtracts an AGE IN YEARS from a HEADCOUNT PER CELL - different
         quantities, so the difference means nothing;
      2. puts GroupCount inside the weight, so the size of the tilt depends on how
         big the plan is (a band of 20,000 came out 0.1% tilted, a band of 500 at
         17%);
      3. centres the weights on (GroupCount/N - mean age) rather than on 1, so
         they straddle zero. Their sum - the normaliser - is
         GroupCount - (sum of the ages in the band), which VANISHES when a band
         holds about that many people, and changes sign either side of it.

    Measured over the 40 state plans: 3 produced NEGATIVE retiree headcounts.
    OK134's 75-79 band held 385.004 people against an age-sum of 385, giving a
    normaliser of 0.004 and cells of about +/-200,000 in a plan with 4,242
    retirees. Band totals still reconciled because the signs cancel, which is why
    it went unseen for years; a one-person PPD revision moved that plan's
    liability by 56%.

    Use `LinearFill` instead.
    """
    return _linear_fill_core(Collapsed, Slope, retirement, legacy=True)


def _linear_fill_core(Collapsed, Slope=1, retirement=False, legacy=False):
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
            s_band = 0.0 if legacy else _band_tilt(Collapsed, i - 1, j - 1)
            Share = np.zeros((N, M))
            sharesum = 0.0
            for k in range(1, N + 1):                   # R: for k in 1:N
                svcmax = rowmin + k - all_age_min

                if legacy:
                    # the superseded weight - see LinearFill_incorrect for why
                    w_age = GroupCount / (N * M) + Slope * (rowmin + k - 1)
                else:
                    # a perturbation around 1, driven only by POSITION in the band.
                    # Every weight is strictly positive, so no cell can go negative,
                    # and the weights sum to exactly N, so the normaliser is a
                    # constant and can never approach zero. The tilt comes from the
                    # neighbouring bands (see _band_tilt), not from a hand-set value.
                    u = 0.0 if N == 1 else (k - 1) / (N - 1)
                    w_age = 1.0 + s_band * (1.0 - 2.0 * u)

                for L in range(1, M + 1):               # R: for L in 1:M
                    if (columnmin + L - 1) > svcmax:
                        Share[k - 1, L - 1] = 0.0
                    else:
                        Share[k - 1, L - 1] = w_age
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
    from engine.functions import UpdateEmployeeCount, UpdateInactiveCount
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


def LinearFill(Collapsed, Slope=1, retirement=False):
    """Spread bucketed counts over single ages, with the slope taken from the data.

    Replaces the inherited weight (kept as `LinearFill_incorrect`) 2026-07-30.
    `Slope` is retained for call-signature compatibility but no longer sets the
    direction of the tilt - the neighbouring bands do, so a band whose population
    is still rising now tilts upward instead of being forced to decline.
    """
    return _linear_fill_core(Collapsed, Slope, retirement, legacy=False)
