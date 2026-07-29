# PPD as a source: report library + API survey (2026-07-29)

What publicplansdata.org (CRR) can give this project, established by direct
probing rather than reading the site's descriptions. Companion data:
`ppd_report_availability.csv` (per plan x document x year).

---

## 1. The report library — where the AVs and CAFRs actually live

Each plan's **Quick Facts** page has a "Financial Reports" block linking the
Comprehensive Annual Financial Report, the **Actuarial Valuation**, sometimes a
GASB67-68 valuation, and an Investment Policy Statement:

```
https://publicplansdata.org/quick-facts/by-pension-plan/plan/?ppd_id=<ID>
```

The files sit at a path that is NOT linked from the site navigation:

```
https://publicplansdata.org/wp-content/uploads/reports/<FILE>.pdf
```

`<FILE>` = `<STATE>_<CITY>-<FUND>_<DOCTYPE>_<YEAR>_<ppd_id>.pdf` — the same
convention this project already uses. **The year is swappable in the URL**: the
page shows only the newest report, but replacing the year fetches earlier
vintages (verified: Seattle AV 2022 -> 2019 both return real PDFs). So the
recipe is: read one link off the Quick Facts page to learn the plan's filename
token, then construct any year.

Caveats found: a plan page occasionally links the WRONG fund (sd's page links a
Sacramento AV) while the correctly-constructed sd URL works; some pages omit the
AV link although the file exists (nyc_ers); doc-type token is sometimes
`FinancialStatements` or `ACFR` instead of `CAFR`.

## 2. Availability and frequency (probed 2008-2024, 33 city funds)

- **32 of 33 city funds have at least one AV; the median plan has 15 years of
  AV history**, most of them an unbroken annual run 2008-2022.
- **The library ends at 2022, with some 2023. No 2024 yet** (the database's
  numeric tables run to 2024, but the posted documents lag).
- **A uniform vintage is achievable**: AV covers **2019 for 27 funds** and
  **2022 for 28**. FY2019 is the project's current corpus year; FY2022 would be
  the newest uniform refresh.
- Thin spots (few AV years, so a time series is not possible there): clt_ff
  (2022-23 only), nyc_fire (2021-23), nyc_ers (2018-21), nyc_pol (2017-21),
  nyc_edu (sparse), hou_gen (2017-23), aus_ff (7 yrs), bos (8 yrs), hou_ff (10).
- **clt_le (Charlotte Law Enforcement, 229) has no hosted reports at all.**

Implication beyond filling gaps: because most funds have ~15 consecutive AVs,
the corpus is not restricted to one snapshot — the same extraction could build a
**time series** of demographic structure per plan, which the model currently
freezes at its original extraction year.

## 3. What is NOT in the PPD, and never will be

The PPD is **plan-level summary data**. It does not contain — and cannot
replace — the six granular tables the extraction pipeline exists to recover:
active counts and wages by age x service, separation/retirement/mortality rates
by age and service, and the retiree age distribution. Those live only inside the
AV PDFs. Downloading more PPD numeric data does not reduce the extraction work.

## 4. What the API IS good for (three concrete roles)

`https://publicplansdata.org/api/` — 34 datasets, 1,106 variables, CSV/JSON,
filterable by `filterppdid`, `filterfystart`/`filterfyend`, tier and employee
group. No key needed.

**(a) An independent verifier for extracted grids — the highest-value use.**
`pensionmembership` carries scalars that are implied by our extracted grids, so
they check the extraction WITHOUT a human workbook (most cells have no
workbook). Proven on phx, computing the implied values from our own extracted
Age_Serv_Num x Age_Serv_Wage grids:

| quantity | from our extraction | PPD API | agreement |
|---|---|---|---|
| total actives | 7,941 | 7,941 | exact |
| total payroll | $562.3M | $563.0M | 0.1% |
| average salary | $70,811 | $70,896 | 0.1% |
| average age | 46.8 | 46.6 | 0.2 yrs |
| average tenure | 11.6 | 12.2 | 0.6 yrs |

(The age/tenure gaps are bucket-midpoint approximations on our side, not
extraction error.) This extends the existing `actives_tot` check — which only
covers Age_Serv_Num — to **Age_Serv_Wage** (`ActiveSalary_avg`, `ActiveSalaries`)
and **Retirement/retdist** (`beneficiaries_ServiceRetirees`,
`ServiceRetireeAge_avg`, `ServiceRetireeBenefit_avg`, `benefits_ServiceRetirees`).

**(b) A source for the TIER PARAMETER file.** `planchanges_main.xlsx` is
hand-curated (benefit factors, COLA, vesting, retirement ages, salary averaging,
caps). The API publishes exactly these, tier-structured (`TierID`, `EEGroupID`,
`fy_start`/`fy_end`): `pensiontierbasics` (incl. `TierHireDate` /
`TierClosedDate` — the model's `tier_startdate` arithmetic),
`pensionnormalretirementbenefit` (`normal_BenefitFactor`),
`pensionnormalretirementeligibility`, `pensionfinalaveragesalary`,
`pensioncolabenefit` (30 vars), `pensionbenefitcap`,
`pensionemployeecontributionrate`, `pensionearlyretirement*`, `pensionbenefitmin`.
Verified live for phx: Tier 1 (pre-2013, closed 2013-06-30) / Tier 2 (2013+).
This is a candidate to REPLACE or audit hand curation — a separate piece of work
from PDF extraction.

**(c) Plan-level model inputs and assumptions**, refreshed programmatically:
`pensiongasbassumptions` (discount rate, inflation, cost/asset-valuation method,
amortization period), `pensionfundingandmethods`, plus asset allocation and
returns.

## 5. Corpus scope — what the data says (vs the old plan)

Checked against the PPD itself rather than the earlier folder list:

- **Fort Worth: NOT in the PPD** (no plan, no reports). Its AV must come from
  the retirement system directly (fwretirement.org).
- **Indianapolis: NOT in the PPD** as a city fund — Indianapolis employees sit
  in state plans (Indiana PERF 36, Teachers 37, Police & Fire '77 fund 242).
  The empty `ind_modeldata` folder does not correspond to a city plan.
- **Charlotte: IS in the PPD** — Firefighters' RS (182, AV 2022-23 only) and Law
  Enforcement (229, no reports).
- **City funds present in the PPD that the pipeline never registered** (all with
  long AV histories unless noted): `dc_teach` 20, `den_schools` 23,
  `hou_gen` 204 (its 2019 AV is ALREADY in the hou folder), `hou_ff` 30,
  `dal_pf` 153, `aus_ff` 216, `aus_pol` 217, `nyc_fire` 149, `nyc_pol` 150,
  `nyc_edu` 211, `clt_ff` 182. Adding them is a scope decision, not a data gap.

## 6. Downloaded this session (FY2019, verified)

Into `Data/Plans/Cities/<city>_modeldata/`, verified for plan identity, year,
text layer, and presence of the target exhibits:

| file | pages | text | target tables present |
|---|---|---|---|
| `DC_DCRB-PFRS-TRS_AV_2019_19_20.pdf` (+CAFR) | 78 | 123K | age/service, termination, mortality |
| `CO_DENVERCITYCOUNTY-DERP_AV_2019_22.pdf` (+CAFR) | 75 | 118K | all five |
| `TN_NASHVILLECITY-MPP_AV_2019_158.pdf` | 131 | 168K | age/service, termination, retirement, mortality |
| `NY_NYC-ERS_AV_2019_76.pdf` (+CAFR) | 124 | 218K | termination, retirement, mortality |
| `WA_SEATTLECITY-ERS_AV_2019_156.pdf` (+CAFR) | 66 | 128K | age/service, retirement, mortality |

Two things to carry forward:
- **DC's report is a COMBINED document** covering Teachers (20) AND Police &
  Firefighters (19) — one PDF, two funds (filename `..._19_20.pdf`).
- **NYC's FY2019 valuation uses June 30, 2017 census data** (the plan's stated
  "LAG" methodology). Its demographic tables are therefore two years older than
  the label — a base-year alignment issue for the model, not an extraction bug.
