# Variable & Parameter Glossary — State & Local Pension Model

**Created:** 2026-05-27 (R-era) · **Refreshed:** 2026-07-07
**Scope:** the production Python engine (`Code/python/fast/`) and the verified R reference (`Code/R/`). Variable names carry over from R to Python **verbatim** (the `PlanParams` dataclass in `fast/sim_params.py` keeps the R names, including the `MortAdujst` typo); only the mechanism differs — R mutates globals with `<<-`, Python threads a `PlanParams` object through function arguments and swaps tier values via `dataclasses.replace()`.

**Division of labor with the other docs:** this glossary says what each variable *means*. Where a piece of input data *comes from* (source channel, fallback chain, read ranges) is `model_input_dictionary.md`; per-plan instance provenance is `provenance/provenance_register.csv`.

---

# Part I — Model Inputs (source data)

## I.A PPD Database Fields

Loaded from `Data/Common/states/ppd-data-latest.xlsx` (row `ppd_id` × `fy = plan_year`), with legacy fallbacks in `PPD_planlevel_main.csv` / `PPD_planlevel_main_updated.csv`. The R code exposes two objects, `planinfo` (full PPD row) and `PPD` (legacy summary csv row); Python reads the same fields into `PlanParams` and scalars.

| PPD Field | What it is |
|---|---|
| `ActAssets_GASB` | Total plan assets as reported under GASB (thousands $) — initializes `Assets[0]` (×1000) |
| `ActLiabilities_GASB` | Reported Accrued Actuarial Liability (thousands $) — becomes `CAFR_AAL` for validation |
| `InvestmentReturnAssumption_GASB` | The plan's assumed long-run investment return; the model's `discountrate` for liabilities. Controversial: it drives both asset expectations and liability discounting |
| `InflationAssumption_GASB` | The actuary's inflation assumption — the model's `Inflation` (legacy `inflation` as fallback) |
| `PayrollGrowthAssumption` / `WageInflation` | First two links of the `WageGrowth` fallback chain (see Part II.C) |
| `InactiveVestedMembers` | Headcount of inactive vested members (deferred pensioners) — inactive-scaling input |
| `actives_tot` | Active member count — scales the `ageservice` shares to headcounts |
| `beneficiaries_tot`, `BeneficiaryBenefit_avg` | Retiree count and average benefit — scale the `retdist` distribution |
| `ActiveSalary_avg` | Mean active salary — scales the `wagerel` relativities into dollars |
| `contrib_EE_regular`, `contrib_ER_regular`, `payroll` | Dollar contributions and payroll — become the employee/employer contribution *rates* |
| `EQTotal_Actl`, `FITotal_Actl`, `PETotal_Actl`, `AltMiscTotal_Actl`, `HFTotal_Actl`, `RETotal_Actl`, `COMDTotal_Actl`, `OtherTotal_Actl` | Actual portfolio weights by asset class — collapsed into the 2-asset `AssetShare` (risky = everything but FI) |

**Demographic scalars found ONLY in the legacy csv** (`PPD_planlevel_main_updated.csv`, keyed `[PLAN]_2022`; no city rows yet):

| Field | What it is |
|---|---|
| `pctmale` | Share of members male — blends the male/female mortality, withdrawal, and refund tables |
| `pctmrg` (`pct_mrg`) | Share of retirees married — drives the widow/survivor death-benefit calculation |
| `reduct` (`widow_reduct`) | Survivor-benefit reduction factor for joint-and-survivor coverage |
| `inactive_adj` | Flag/multiplier selecting the inactive-scaling rule (1 → use `InactiveVestedMembers`; else `actives_tot × inactive_adj`) |

Legacy tier-rule summary fields in PPD (`benefitfactor`, `nr`, `er`, `vesting`, `yrsal`, `cola` and their `_new`/`new_` variants) informed the hand-curated `planchanges` workbook but the engine reads tier rules from `planchanges_main_2022_clean.xlsx`, not from these.

## I.B Plan Workbook Sheets → Model Matrices

Each `Data/Plans/States/[PLAN]/[PLAN]_2017.xlsx` has up to 9 sheets. Raw bucketed data is expanded to full age × service grids by `LinearFill()` / `ConstantFill()` (`bucketfill_cf_model`).

| Raw (R name) | Model object | Sheet | What it is |
|---|---|---|---|
| `asy_employee` | `active` → `Employees` | 1 ageservice | Active headcount by age × service bucket (shares, scaled by `actives_tot`) |
| `ret_num`, `ret_ben` | `RetirementNumber`, `RetirementBenefit` | 2 retdist | Current-retiree age distribution and benefit relativities |
| `asy_wage` | `BaseWage` (via `ConstantFill`) | 3 wagerel | Salary relativities by age × service — the *shape* of the wage profile, distinct from the growth rate |
| `mort_table` | `MortalityTable` | 4 mortality | Death probabilities by age, male + female blocks, blended by `pctmale` |
| — | — | 5 wagegrowth | **GHOST SHEET — never read.** Wage growth comes from the PPD scalar chain (Part II.C) |
| `asy_seprate` | `SeparationRate` | 6 withdrawal | Annual probability of leaving employment pre-retirement, by age × service |
| `asy_retrate` | `RetirementRate` | 7 retirement | Annual probability of retiring, by age × service |
| `asy_refundrate` | `RefundRate` | 8 refund | Among separators, the fraction cashing out contributions vs. deferring |
| — | — | 9 disability | **GHOST SHEET — never read.** Replaced by the `DisabilityPayoutRate = 0.025` constant |
| `AnnuityVector` | computed | — | Price of a $1/year lifetime annuity at each age (discounted survival-weighted sum) — converts annual benefits to present-value lump sums |

## I.C `availableData` Flag Vector

Per-plan 9-boolean vector — in R set per script, in Python hard-coded in the `AVAILABLE_DATA` dict of `fast/Main_PensionModel.py`. `False` → the same-named sheet of `default_assumptions.xlsx` is used instead. Order: `[ageservice, retdist, wagerel, mortality, wagegrowth, withdrawal, retirement, refund, disability]`.

Common patterns: most plans `T,T,T,T,T,T,F,F,F`; IL32 lacks withdrawal (`[6]=F`). Caveat from the provenance scan: 33 plan-sheets contain plan-specific data despite `False` flags — verify sheet layout before ever flipping a flag.

---

# Part II — Simulation Variables (code)

## II.A Plan Identification

| Variable | What it is |
|---|---|
| `ppid` / `ppd_id` | Integer plan ID in the Public Plans Database |
| `plan_id` | String label, `"[PLAN]_[YEAR]"` e.g. `"AZ06_2022"` |
| `plan_year` | Base year of the valuation data used for model inputs (canonical run: 2022 scalars layered on FY2017 distributions — the documented "hybrid") |
| `plan_start` | Date of the first day of the base year (anchors tier-service arithmetic) |
| `run_tag` | Output label selecting the folder under `Results/Runs/` (canonical: `062026`). Output naming, not model content |

## II.B Simulation Configuration

| Variable | What it is | Canonical value |
|---|---|---|
| `Nyear` | Projection horizon in years | 35 |
| `num_sim` | Monte Carlo paths in the asset simulation | 10,000 |
| `NMonte` | **Legacy (R-era):** Monte Carlo runs in the embedded quick asset loops of individual R plan scripts (1 or 10). The Python detAL stage is deterministic; `PlanParams.NMonte = 1` | 1 |
| detal seed | `np.random.seed(54848631)` (R parity: `set.seed(54848631)`) | 54848631 |
| market seed | Seed of the ONE standardized shock matrix `Z` shared by all plans (common market shocks) | 123 |
| asset classes | Production model is 2-asset (stocks + bonds). The 5-asset correlated-real-return model was an R-track variant, now archived | 2 |

## II.C Economic & Return Assumptions

| Variable | What it is | Value / source |
|---|---|---|
| `Inflation` | Assumed annual price-level growth | `InflationAssumption_GASB` → legacy `inflation` |
| `WageGrowth` | Annual nominal salary growth applied to `BaseWage` | Fallback chain: `PayrollGrowthAssumption` → `WageInflation` → legacy `wage_inf` → `InflationAssumption_GASB` → legacy `inflation` |
| `rf` | Risk-free nominal rate; the bond return | `0.01 + Inflation` (set by the runner) |
| `annuity_dr` | Discount rate for annuity pricing | = `rf` |
| `refundReturn` | Interest credited on employee contributions, sets the separator's lump-sum cash-out | = `rf` |
| `discountrate` | Rate discounting future benefit obligations to present value. Plans use their assumed investment return (~7%), which makes liabilities look smaller than under risk-free discounting — a core critique theme | `InvestmentReturnAssumption_GASB`; replaceable per run via `--discount-override` (scenario lever, e.g. AAA revaluation) |
| `stock_premium` | Expected real stock premium; stock expected return = `stock_premium + Inflation` | 0.075 (CLI-overridable) |
| `stock_vol` | Annual stock return volatility | 0.20 (CLI-overridable); bond vol = 0 |

## II.D Asset Allocation (2-asset)

| Variable | What it is |
|---|---|
| `AssetShare` | `[stocks, bonds]` weights. Risky share = Σ of the 7 non-FI PPD `*Total_Actl` weights; bonds = 1 − risky |
| `--equity-share`, `--derisk-to`/`--derisk-years` | Scenario levers: flat risky-share override, or a linear de-risking glidepath (weights become time-varying) |

## II.E Workforce Demographics

| Variable | What it is | Value |
|---|---|---|
| `EmployeeStart` / `EmployeeEnd` | Youngest / oldest active age tracked | 20 / 74 |
| `ServiceStart` / `ServiceEnd` | Service-year range of the age-service grid | 1 / 55 |
| `RetirementMax` | Oldest retiree age tracked | 104 |
| `InactiveRetirement` | Age at which a vested inactive member must begin drawing | 65 (constant in `core.py`) |
| `PopulationGrowth` | Annual active-workforce growth (new-hire refill) | 0.01 constant (MA50's script used 0.03, but MA50 is excluded from production) |
| `pctmale` | Male share, weights male vs. female tables | legacy csv |
| `MortAdujst` | Scalar multiplier on all mortality rates (typo preserved from R) | 1.0 |

## II.F Contribution & Benefit Structure

| Variable | What it is |
|---|---|
| `EmployeeContributionRate` | Employee contribution as a fraction of salary — `contrib_EE_regular / payroll`; recomputed from the workforce matrix when the PPD ratio is NaN (`CONTRIB_RATE_NA_CHECK` plans) |
| `EmployerContributionRate` | Employer contribution as a fraction of payroll — same construction |
| `DisabilityPayoutRate` | Disability outflow as a fraction of payroll (replaces ghost sheet 9) — 0.025 |
| `--contrib-add`, `--policy-start`, `--contrib-always` | Scenario levers: add-on contribution in pp of payroll, its start year, and whether it is paid even when funded (base rule contributes 0 when FR > 1) |

## II.G Tier-Specific Parameters

Plans have up to 6 tiers (later hires, usually less generous). Parameters carry `_t1`…`_t6` suffixes; per-tier values are promoted for each tier run — in R via globals (`BenefitFactor <<- BenefitFactor_t2`), in Python via `dataclasses.replace(params, ...)`.

| Pattern | What it is |
|---|---|
| `BenefitFactor_t[n]` | Per-service-year accrual rate: annual pension = factor × service × average salary (0.025 × 30 yrs = 75% replacement) |
| `WageYears_t[n]` | Salary-averaging window in the benefit formula (final/highest N years) |
| `COLA_t[n]` | Post-retirement cost-of-living adjustment for the tier's retirees |
| `BenefitCap_t[n]` | Maximum replacement rate; PPD encodes "no cap" as −100 → converted to 100 |
| `NyearFullBenefit_t[n]` | Vesting period: minimum service before any employer-funded pension right |
| `RetirementStart_t[n]` | Normal retirement age (full unreduced benefit) |
| `tier_service` | Service years the tier had accrued at `plan_start`: `round((plan_start − startdate)/52.25 weeks)`. Adjacent tiers can round to the SAME year (the OH88 case) |

**Behavioral quirk carried over from R:** after the tier loop, the retired-population projection (`Main_Ret` / `main_ret_fast`) uses the **last tier's** `COLA` / `BenefitFactor` / `NyearFullBenefit` — R's global-mutation side effect, deliberately replicated in Python (`_t[num_tiers]`).

## II.H Employee State Matrices

Three-dimensional arrays tracking the population through time: age × service × year (retirees: age × year).

| Variable | Dimensions | What it is |
|---|---|---|
| `Employees` (`active`) | age × service × year | Active contributing members |
| `Employees_t[n]` (`active_t[n]`) | same | Tier-n actives (partition of `active` by `tier_service` boundaries) |
| `Inactive` | age × service × year | Vested deferred members: no contributions, no new accrual, frozen right pays from `InactiveRetirement` |
| `InactiveBen` | age × service × year | The frozen annual benefit each inactive member earned at separation |
| `RetNum` / `RetBen` | age × year | Retiree counts / average annual benefits by age |
| `BaseWage` | age × service × year | Absolute salary level, growing by `WageGrowth`; the relativities give its cross-sectional shape |

## II.I Cash Flow & Liability Outputs

| Variable | What it is |
|---|---|
| `cash_outflows` | Annual benefit payments: retirement benefits + refunds + death benefits + disability |
| `cash_inflows` | Annual contributions: employee + employer |
| `AAL` | Accrued Actuarial Liability — PV of benefits already earned by service to date (entry-age normal). The core liability measure, length `Nyear` |
| `NormalCost` | Cost of one additional year of accruals across all actives — the annual flow addition to AAL |
| `PVFB` | PV of ALL projected lifetime payments to current members, including future accruals — larger than AAL |
| `Assets` | Plan assets, year × simulation matrix (year × `num_sim` after the asset stage) |
| `UAAL` | `AAL − Assets`, the funding gap |
| `funding_ratio` | `Assets / AAL` — the primary sustainability metric, analyzed as a distribution (fans, exhaustion probabilities, threshold risks), never just its mean |
| `Model_AAL` / `CAFR_AAL` | Model-computed vs. plan-reported base-year AAL |
| `Percent_difference` | `(Model_AAL − CAFR_AAL) / CAFR_AAL` — the validation check, standardized to this formula everywhere 2026-06-09 |
| `MainRes_Tier[n]` | Per-tier result list: `[AAL, CashOutflow, CashInflow, PVFB, NormalCost]` — kept in the detAL pkl, enables tier-level liability attribution without new runs |
| `RetRes` | Already-retired members' results: `[AAL, CashOutflow]` |

## II.J Asset-Stage Variables (`asset_simulation.py`)

| Variable | What it is |
|---|---|
| `Z` | THE standardized shock matrix, `(Nyear−1) × num_sim`, drawn once from the market seed and **shared by every plan** — column n is the same market history for all plans, so cross-plan aggregate distributions are meaningful (deliberate departure from R's independent per-plan draws) |
| stock return | `(stock_premium + Inflation_p) + stock_vol × Z[t,n]` — per-plan expected level, common shocks |
| contribution rule | If funded (FR > 1): base contribution 0; if underfunded: scheduled inflows. Scenario add-ons per II.F |
| `Amortize` / `Amtorize_Period` | **R asset-script flags** (spread UAAL payoff over 30 years, mortgage-style); the R scripts set `Amortize = FALSE`. Note the `Amotorize_Period` typo bug in the R 5-asset script (harmless while FALSE) |
| `market_seed`, `common_market_shocks`, `scenario` | Provenance stored in every asset pkl payload |

## II.K Naming Conventions

| Convention | Rule | Example |
|---|---|---|
| Tier suffix | `_t1` … `_t6` | `BenefitFactor_t1`, `active_t3` |
| Liability-only versions | `L_` / `l_` prefix — no new hires, for PV calculations | R `L_UpdateEmployeeCount()`, Python `l_update_employees()` |
| Rate matrices | `…Rate` suffix | `SeparationRate`, `RetirementRate`, `RefundRate` |
| Raw loaded data | `asy_` prefix | `asy_employee`, `asy_seprate` |
| Cash flows | `cash_` prefix | `cash_inflows`, `cash_outflows` |
| R → Python functions | PascalCase → snake_case, same semantics | `UpdateEmployeeCount` → `update_employees`, `ComputeAnnuity` → `compute_annuity`, `PVNC_Calc` → `pvnc_calc_fast` |

## II.L Plan-Specific Quirks

| Plan | Note |
|---|---|
| **MA50** | **Excluded from the production Python runner** (structural outlier: different risk-free formula, missing ×1000 asset multiplier, backward tier logic, no NormalCost). Its R-era quirks — COLA 0, PopulationGrowth 0.03, ServiceEnd 40, discountrate from `InvestmentReturnAssumption_GASB`, disability rate from actual payroll data — live only in the R reference |
| IL32 | `availableData[6] = F` — no plan-specific withdrawal rates; 2-tier plan |
| OH88 | 6 tiers; Tiers 2–3 start 6 months apart and round to the SAME `tier_service` (41) — the case behind the `_zero_outside` descending-sequence fix |
| NY78 | 6-tier plan; was the R template (`Main_PensionModel_XX.R`) |
| CA10 | 2-tier plan |
| PA93 / TX108 / SC100 / RI96 | R-era `_OneTier` / `_2` variant scripts exist in the reference tree |
| AZ127, CA144, CA98, IL32, IN37, LA130, LA44 | `CONTRIB_RATE_NA_CHECK` set — contribution rates recomputed from the workforce matrix when the PPD ratio is NaN |
