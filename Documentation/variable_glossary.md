# Variable & Parameter Glossary — State Pension Model

**Last Updated:** 2026-05-27  
**Scope:** `State Pension Model/` (Common_Code + 40 plan folders)

---

## A. Plan Identification

| R Variable | What it is |
|---|---|
| `ppid` | Integer ID for this plan in the Public Plans Database (PPD) |
| `plan_id` | String label used throughout the model, format `"[PLAN]_[YEAR]"` e.g. `"MA50_2017"` |
| `plan_year` | Base year of the valuation data (typically 2017) |
| `plan_start` | Date object for the first day of the base year |
| `fileName` | Filename of the plan-specific Excel data file |

---

## B. Simulation Configuration

| R Variable | What it is | Value |
|---|---|---|
| `Nyear` | Number of years simulated forward from the base year | 35 |
| `NMonte` | Monte Carlo runs in individual plan scripts (quick testing) | 10 |
| `num_sim` | Monte Carlo runs in the full asset simulation | 10,000 |
| `NAsset` / `Nasset` | Number of asset classes in the portfolio model | 2 (stocks + bonds) or 5 |
| `set.seed(54848631)` | Fixed random seed ensuring reproducible simulation draws | Fixed |

---

## C. Economic & Return Assumptions

| R Variable | What it is | Typical Value |
|---|---|---|
| `Inflation` | Assumed annual rate of general price-level growth; drives real-vs-nominal distinctions throughout the model | ~0.025 (from plan's GASB filing) |
| `WageGrowth` | Annual rate at which all salaries grow; effectively the nominal wage inflation assumption | Set equal to `Inflation` in most plans |
| `rf` | Risk-free nominal interest rate; used as the return on bonds and as the annuity discount rate | 0.01 |
| `annuity_df` / `annuity_dr` | Discount rate used to price annuities — determines what $1/year of future pension payments is worth in today's dollars | Set equal to `rf` |
| `refundReturn` | Interest rate credited on employee contributions during their working years; determines the size of the lump-sum cash-out a departing worker receives | ~inflation rate |
| `discountrate` | Rate used to discount all future benefit obligations back to a present value. Plans use their assumed investment return for this (typically 7–8%), which is controversial — it makes liabilities appear smaller than they would under risk-free discounting | `PPD$discount` (most plans); `planinfo$InvestmentReturnAssumption_GASB` (MA50, others) |
| `ExpRet` | Expected annual return for each asset class used in Monte Carlo draws | `c(0.075 + Inflation, rf)` — stocks, bonds |
| `SD` | Annual return volatility (standard deviation) for each asset class | `c(0.20, 0)` — 20% for stocks, 0% for bonds |

---

## D. Asset Allocation

Portfolio weights drawn from PPD. In 2-asset scripts, all risky assets collapse into `AssetShareStocks`.

| R Variable | What it is |
|---|---|
| `AssetShareEquities` | Fraction of portfolio in publicly traded equities |
| `AssetShareFI` | Fraction in fixed income (bonds) |
| `AssetShareAlternatives` | Fraction in alternative assets and private equity |
| `AssetShareRE` | Fraction in real estate |
| `AssetShareCash` | Residual fraction in cash and short-term instruments |
| `AssetShare` | Full allocation vector; length = `Nasset` |
| `AssetShareStocks` | In the 2-asset model: all risky asset classes combined (equities + PE + RE + alts + hedge funds + commodities + other) |
| `AssetShareBonds` | In the 2-asset model: risk-free / bond portion = `1 − AssetShareStocks` |

---

## E. Workforce Demographics

| R Variable | What it is | Value |
|---|---|---|
| `EmployeeStart` | Minimum age at which new hires can enter the plan | 20 |
| `EmployeeEnd` | Maximum age for active employment tracked in the model | 74 |
| `RetirementMax` | Oldest age tracked in the retiree population | 104 |
| `ServiceStart` | Minimum years of service tracked in the age-service matrix | 1 |
| `ServiceEnd` | Maximum years of service tracked | 55 (template); 40 (MA50) |
| `InactiveRetirement` | Age at which a vested inactive member (deferred pensioner) must begin drawing their benefit | 65 |
| `PopulationGrowth` | Annual growth rate of the plan's total active workforce; affects long-run contribution base and liability growth | 0.01–0.03 (plan-specific) |
| `pctmale` | Share of the workforce that is male; used to weight male vs. female mortality tables | From PPD |
| `MortAdujst` | Scalar multiplier on all mortality rates; set to 1.0 at baseline, varied in longevity sensitivity analyses | 1.0 |

---

## F. Contribution & Benefit Structure

| R Variable | What it is | Typical Value |
|---|---|---|
| `EmployeeContributionRate` | Fraction of salary contributed annually by the employee to fund their pension | 0.10 (10%) |
| `EmployerContributionRate` | Fraction of payroll contributed annually by the employer (government) | 0.25 (25%) |
| `COLA_c` | Cost-of-living adjustment: the annual percentage increase applied to pension benefits after retirement to protect retirees from inflation. Applied plan-wide to all already-retired members regardless of tier | From PPD; MA50 = 0 (no COLA) |
| `BenefitCap_c` | The maximum allowed replacement rate — i.e., the pension cannot exceed this fraction of the member's pre-retirement salary, regardless of years of service | 1.0 = 100% of salary |
| `DisabilityPayoutRate` | Annual disability benefit outflow as a fraction of total payroll; approximates the cost of benefits paid to members who leave due to disability | 0.025 (2.5%); some plans use actual ratio |

---

## G. Tier-Specific Parameters

Public pension plans typically have multiple tiers reflecting changes in benefit generosity for workers hired after certain dates (later tiers are usually less generous). The model supports up to 6 tiers; parameters carry a `_t1` through `_t6` suffix. Inside `Main_Current()`, the relevant tier's values are promoted to plain global names (e.g., `BenefitFactor <<- BenefitFactor_t2`).

| R Variable Pattern | What it is |
|---|---|
| `BenefitFactor_t[n]` | The per-year accrual rate in the pension benefit formula: annual pension = BenefitFactor × years of service × average salary. E.g., 0.025 means a 30-year worker receives 75% of their average salary per year in retirement |
| `WageYears_t[n]` | Number of salary years averaged to compute the "final average salary" in the benefit formula. E.g., 3 = final 3-year average; 5 = highest 5-year average. Higher values reduce the benefit for workers with fast late-career wage growth |
| `COLA_t[n]` | Cost-of-living adjustment for this tier's retirees (see `COLA_c` above); allows different tiers to have different post-retirement indexation rules |
| `BenefitCap_t[n]` | Maximum replacement rate for this tier (see `BenefitCap_c`). PPD encodes "no cap" as −100; code converts to 100 |
| `NyearFullBenefit_t[n]` | Vesting period: minimum years of service before a worker earns any pension right. Workers who leave before this threshold receive only a refund of their own contributions, with no employer-funded pension |
| `RetirementStart_t[n]` | Normal retirement age for this tier — the age at which a member can retire and receive their full unreduced benefit |
| `tier_service` | Service years that tier members have already accrued as of the model start date. Computed from the tier's inception date, so workers in older tiers enter the model with more pre-existing service credit |

**Globals set inside `Main_Current()` (one set per tier run):**

| Global | Tier-specific source |
|---|---|
| `BenefitFactor` | `BenefitFactor_t[n]` |
| `WageYears` | `WageYears_t[n]` |
| `COLA` | `COLA_t[n]` |
| `BenefitCap` | `BenefitCap_t[n]` |
| `NyearFullBenefit` | `NyearFullBenefit_t[n]` |
| `RetirementStart` | `RetirementStart_t[n]` |

---

## H. PPD Database Fields

Loaded from `ppd-data-latest.xlsx` or `PPD_planlevel_main.csv`, filtered to the plan's `ppid` and `plan_year`. Two R objects are used: `planinfo` (full PPD row) and `PPD` (summary version).

| PPD Field | R Access | What it is |
|---|---|---|
| `ActAssets_GASB` | `planinfo$ActAssets_GASB` | Total plan assets as reported in the CAFR under GASB accounting standards (thousands $) |
| `ActLiabilities_GASB` | `planinfo$ActLiabilities_GASB` | Accrued Actuarial Liability (AAL) as reported — the present value of all pension benefits already earned by current and former members based on service to date, per the plan's own actuarial method (thousands $) |
| `InvestmentReturnAssumption_GASB` | `planinfo$InvestmentReturnAssumption_GASB` | The plan's assumed long-run investment return, as filed under GASB. This single number drives both the expected return on assets and the discounting of liabilities, so it heavily determines how large reported liabilities appear |
| `InflationAssumption_GASB` | `planinfo$InflationAssumption_GASB` | Inflation rate assumed by the plan's actuary |
| `InactiveVestedMembers` | `planinfo$InactiveVestedMembers` | Headcount of inactive vested members — workers who left employment after meeting the vesting threshold and are waiting to collect a deferred pension |
| `discount` | `PPD$discount` | Liability discount rate as recorded in PPD (used in most plan scripts in place of the planinfo field above) |
| `cola` | `PPD$cola` | The COLA rate reported for this plan: the annual percentage by which retiree benefits are increased after retirement (see `COLA_c`) |
| `pctmale` | `PPD$pctmale` | Share of active workforce that is male; used to blend male and female mortality tables |
| `pctmrg` | `PPD$pctmrg` | Share of retirees who are married; relevant because most plans pay a reduced survivor annuity to a spouse after the retiree's death |
| `reduct` | `PPD$reduct` | The actuarial reduction applied to a retiree's own benefit when they elect joint-and-survivor coverage (i.e., they take a lower payment in exchange for a spouse benefit continuing after their death) |
| `actives` | `PPD$actives` / `planinfo$actives_tot` | Total count of active contributing members |
| `inactive` | `PPD$inactive` | Total count of inactive vested members (deferred pensioners) |
| `retired` | `PPD$retired` | Total count of members currently receiving benefits |
| `avgsalary` | `PPD$avgsalary` | Mean salary among active members |
| `avgbenefit` | `PPD$avgbenefit` | Mean annual benefit payment among retirees |
| `avgageret` | `PPD$avgageret` | Average age at which members retire |
| `payroll` | `PPD$payroll` | Total salary payroll of active members; the base against which contribution rates are applied |
| `benefitfactor` | `PPD$benefitfactor` | The plan's benefit accrual multiplier: the fraction of final average salary earned per year of service (see `BenefitFactor_t[n]` above) |
| `benefitfactor_new` | `PPD$benefitfactor_new` | Benefit factor for the most recent (usually less generous) tier |
| `new_cola` | `PPD$new_cola` | COLA rate for the most recent tier |
| `nr` | `PPD$nr` | Normal retirement age plan-wide: age at which a member qualifies for a full unreduced benefit |
| `nr_new` | `PPD$nr_new` | Normal retirement age for the most recent tier (often higher than `nr`) |
| `er` | `PPD$er` | Early retirement age: the earliest age at which a member can retire with a reduced benefit |
| `new_er` | `PPD$new_er` | Early retirement age for the most recent tier |
| `vesting` | `PPD$vesting` | Vesting period in years: minimum service required before a member has any earned pension right |
| `new_vesting` | `PPD$new_vesting` | Vesting period for the most recent tier |
| `yrsal` | `PPD$yrsal` | Number of salary years averaged in the benefit formula — final N years or highest N years (plan-specific) |
| `new_yrsal` | `PPD$new_yrsal` | Salary averaging window for the most recent tier |
| `reqcont` | `PPD$reqcont` | Actuarially required contribution rate (% of payroll): what the actuary says the employer should contribute to keep the plan on track |
| `employeecont` | `PPD$employeecont` | Employee contribution rate (% of salary) |
| `employercont` | `PPD$employercont` | Employer contribution rate (% of payroll) |
| `totalcontr` | `PPD$totalcontr` | Total dollar contributions in the reporting year |
| `ncrate_tot` | `PPD$ncrate_tot` | Normal cost rate: the cost of one additional year of benefit accruals for all current active members, expressed as a % of payroll |
| `ret_liability` | `PPD$ret_liability` | Portion of AAL attributable to already-retired members |
| `inact_liability` | `PPD$inact_liability` | Portion of AAL attributable to inactive (deferred) members |
| `PVFB` | `PPD$PVFB` | Present Value of Future Benefits: the present value of all projected future payments to all current members — broader than AAL because it includes benefits not yet accrued |
| `inflation` | `PPD$inflation` | Inflation assumption in PPD (may differ slightly from `planinfo$InflationAssumption_GASB`) |
| `wage_inf` | `PPD$wage_inf` | Wage inflation: assumed rate of nominal wage growth used in the plan's actuarial valuation |
| `actgrowth20` / `actgrowthnat` / `actgrowthst` | `PPD$actgrowth...` | Historical active membership growth rates over 20 years, at national level, and at state level; used to calibrate `PopulationGrowth` |
| `EQTotal_Actl` | `planinfo$EQTotal_Actl` | Actual portfolio weight in public equities |
| `FITotal_Actl` | `planinfo$FITotal_Actl` | Actual portfolio weight in fixed income |
| `PETotal_Actl` | `planinfo$PETotal_Actl` | Actual portfolio weight in private equity |
| `AltMiscTotal_Actl` | `planinfo$AltMiscTotal_Actl` | Actual portfolio weight in miscellaneous alternatives |
| `HFTotal_Actl` | `planinfo$HFTotal_Actl` | Actual portfolio weight in hedge funds |
| `RETotal_Actl` | `planinfo$RETotal_Actl` | Actual portfolio weight in real estate |
| `COMDTotal_Actl` | `planinfo$COMDTotal_Actl` | Actual portfolio weight in commodities |
| `OtherTotal_Actl` | `planinfo$OtherTotal_Actl` | Actual portfolio weight in all other assets |

---

## I. Plan-Specific Excel Sheets → R Matrix Variables

Each plan's Excel file has up to 9 sheets. Raw data is loaded, then expanded to full age × service grids by `LinearFill()` / `ConstantFill()`.

| R Variable | Excel Sheet | Dimensions | What it is |
|---|---|---|---|
| `asy_employee` → `active` | Sheet 1: ageservice | age × service | Headcount of active employees cross-tabulated by current age and years of service; initializes the workforce simulation |
| `ret_num` → `RetirementNumber` | Sheet 2: retdist | age × 1 | Number of current retirees at each age; initializes the retired population |
| `ret_ben` → `RetirementBenefit` | Sheet 2: retdist | age × 1 | Average annual benefit received by retirees at each age |
| `asy_wage` → `BaseWage` | Sheet 3: wagerel | age × service × year | Salary relativities: how much more (or less) a worker at a given age and tenure earns relative to a reference worker. Separate from the overall wage growth rate — captures the shape of the wage-age-service profile |
| `mort_table` → `MortalityTable` | Sheet 4: mortality | age × 2 | Annual probability of dying at each age, by gender (column 1 = male, column 2 = female) |
| `asy_wagegrowth` | Sheet 5: wagegrowth | age | Age-specific component of wage growth (e.g., younger workers may see faster raises) |
| `asy_seprate` → `SeparationRate` | Sheet 6: withdrawal | age × service | Annual probability of voluntarily leaving employment at each age-service combination, before retirement |
| `asy_retrate` → `RetirementRate` | Sheet 7: retirement | age × service | Annual probability of retiring (transitioning to retired status) at each age-service combination |
| `asy_refundrate` → `RefundRate` | Sheet 8: refund | age × service | Among members who separate before retirement, the fraction who take a cash refund of their contributions rather than preserving a deferred pension |
| `dis_table` | Sheet 9: disability | age | Annual probability of leaving due to disability at each age (rarely populated; model uses `DisabilityPayoutRate` instead) |
| `AnnuityVector` | Computed | age | The price of a $1/year lifetime annuity at each age — converts a projected annual pension benefit into a present-value lump sum for liability calculation purposes |

---

## J. Employee State Matrices

Three-dimensional arrays tracking the workforce population through simulation time. Dimensions: age × service × year (or age × year for retirees).

| R Variable | Dimensions | What it is |
|---|---|---|
| `Employees` | age × service × year | Count of active contributing members by age and service in each simulated year |
| `Employees_t[n]` | same | Active members belonging to tier n only |
| `Inactive` | age × service × year | Vested deferred members: workers who left employment after meeting the vesting threshold, holding a frozen pension right that will pay out starting at retirement age. They make no contributions and accrue no new service |
| `InactiveBen` | age × service × year | The frozen annual benefit amount each inactive member has already earned, based on salary and service at the time they separated |
| `RetNum` | age × year | Number of members currently receiving retirement benefits at each age |
| `RetBen` | age × year | Average annual benefit paid to retirees at each age |
| `BaseWage` | age × service × year | Absolute salary level for a worker at a given age and service, growing by `WageGrowth` each year. Distinct from the salary relativities in `asy_wage` |

---

## K. Cash Flow & Liability Output Variables

| R Variable | What it is |
|---|---|
| `cash_outflows` | Total benefit payments made by the plan each year: retirement benefits + refunds to separators + death benefits + disability payments |
| `cash_inflows` | Total annual contributions flowing into the plan: employee + employer contributions |
| `main_cf` | Outflows from active and inactive members (all tiers combined) |
| `ret_cf` | Outflows from already-retired members |
| `AAL` | Accrued Actuarial Liability: the present value of all pension benefits already earned by current and former members, based on service to date. This is the plan's core liability measure. Vector of length `Nyear` |
| `NormalCost` | The cost of one additional year of pension accruals across all active members — i.e., how much benefit is earned in the current year by the entire workforce. The annual "flow" addition to AAL under the entry-age normal method |
| `PVFB` | Present Value of Future Benefits: present value of all projected lifetime payments to current members, including benefits not yet accrued. Larger than AAL; includes future service still to be earned |
| `Assets` | Total plan assets in each year and simulation; matrix of shape year × simulation |
| `UAAL` | Unfunded AAL: `AAL − Assets` — the funding gap, i.e. the amount by which the pension obligation exceeds current assets |
| `funding_ratio` | `Assets / AAL` — the primary sustainability metric. Above 1.0 = fully funded; below signals a shortfall; the paper uses thresholds of 0.10, 0.20, and 0.30 as distress triggers |
| `Model_AAL` | Model's computed AAL for the base year (scalar); compared to the plan's own reported figure |
| `CAFR_AAL` | Plan's officially reported AAL from its CAFR/actuarial valuation (scalar) |
| `Percent_difference` | `(Model_AAL − CAFR_AAL) / CAFR_AAL` — primary model validation check; captures how closely the model's liability matches what the plan itself reports |

**`Main_Current()` return list structure:**
- `[[1]]` = AAL (by year)
- `[[2]]` = CashOutflow
- `[[3]]` = CashInflow
- `[[4]]` = PresentValueFutureBenefits
- `[[5]]` = NormalCost

---

## L. Asset Simulation Parameters (asset_simulation.R)

| R Variable | What it is | Default |
|---|---|---|
| `Amortize` | Whether to spread the UAAL cost over multiple years rather than targeting it in the current period. When TRUE, the employer contribution includes a level payment to pay off the funding gap over `Amtorize_Period` years, similar to how a mortgage amortizes a debt | `FALSE` |
| `Amtorize_Period` | Years over which the UAAL is amortized when `Amortize = TRUE` | 30 |
| `AnnualRet` | Realized portfolio return in a given Monte Carlo year; computed as the weighted average of stock and bond returns | Drawn each iteration |
| `stock_normal_shock` | Standard-normal random draw used to generate the year's stock return | `rnorm(1)` |
| `bond_normal_shock` | Standard-normal random draw for bond return (currently SD=0, so effectively unused) | `rnorm(1)` |

---

## M. `availableData` Flag Vector

Every plan script sets `availableData <- c(T/F, ...)` with 9 entries. `FALSE` means the plan did not provide this data — the model falls back to `default_assumptions.xlsx`.

| Index | Sheet | What it covers |
|---|---|---|
| `[1]` | ageservice | Age × service distribution of active employees |
| `[2]` | retdist | Age distribution of current retirees |
| `[3]` | wagerel | Salary relativities by age and service |
| `[4]` | mortality | Mortality rates by age |
| `[5]` | wagegrowth | Age-specific wage growth |
| `[6]` | withdrawal | Voluntary separation / turnover rates |
| `[7]` | retirement | Retirement propensity rates |
| `[8]` | refund | Rate at which separating members cash out vs. take a deferred pension |
| `[9]` | disability | Disability rates (almost always FALSE; model uses the `DisabilityPayoutRate` scalar instead) |

Common patterns:
- Most plans: `c(T,T,T,T,T,T,F,F,F)` — have everything through withdrawal; missing retirement rates, refund rates, and disability
- MA50: `c(T,T,T,T,T,T,T,F,F)` — also has plan-specific retirement rates
- IL32: `c(T,T,T,T,T,F,T,F,F)` — missing withdrawal rates

---

## N. Naming Conventions

| Convention | Rule | Example |
|---|---|---|
| Tier suffix | `_t1` … `_t6` | `BenefitFactor_t1`, `active_t3` |
| Liability-only versions | `L_` prefix | `L_UpdateEmployeeCount()` — runs without adding new hires, for PV calculation |
| Rate matrices | `…Rate` suffix | `SeparationRate`, `RetirementRate`, `RefundRate` |
| Raw loaded data | `asy_` prefix | `asy_employee`, `asy_seprate` |
| Expanded simulation matrices | Plain name | `Employees`, `BaseWage`, `MortalityTable` |
| Cash flows | `cash_` prefix | `cash_inflows`, `cash_outflows` |
| Per-tier results list | `MainRes_Tier[n]` | `MainRes_Tier1[[1]]` = tier 1 AAL |
| Retirement results | `RetRes` | `RetRes[[1]]` = retired AAL, `RetRes[[2]]` = retired outflow |

---

## O. Plan-Specific Quirks

| Plan | Variable | Note |
|---|---|---|
| MA50 | `COLA_c` | 0 — Massachusetts general plan provides no post-retirement COLA |
| MA50 | `PopulationGrowth` | 0.03 — higher workforce growth assumed than the 0.01 default |
| MA50 | `ServiceEnd` | 40 (vs. 55 in the template) |
| MA50 | `discountrate` | Taken from `planinfo$InvestmentReturnAssumption_GASB`, not `PPD$discount` |
| MA50 | `inactive` | Scaled by `planinfo$InactiveVestedMembers` rather than `PPD$inactive` |
| MA50 | `DisabilityPayoutRate` | Computed from actual disability payroll data (~0.027) rather than the 0.025 default |
| MA50 | `availableData[7]` | `TRUE` — plan provides its own retirement propensity rates |
| CA10 | `AssetShareStocks` | Aggregated from 7 separate PPD allocation fields |
| CA10 | Tiers | 2-tier plan; `active_t3` through `active_t6` not created |
| IL32 | `availableData[6]` | `FALSE` — no plan-specific withdrawal/separation rates |
| IL32 | Tiers | 2-tier plan |
| NY78 | Tiers | 6-tier plan; used as the template (`Main_PensionModel_XX.R`) |
| NY78 | `Nasset` | 5 — template uses the full 5-asset model |
| PA93 | Script | `PA93_OneTier_PensionModel.R` variant exists for single-tier analysis |
| TX108, SC100, RI96 | Scripts | `_2` variant scripts exist |
