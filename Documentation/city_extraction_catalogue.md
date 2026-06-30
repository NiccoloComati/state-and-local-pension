# City Extraction Catalogue

**Generated** by `build_city_extraction_catalogue.py` (do not hand-edit; regenerate). Per city plan: what is extracted on each model-relevant sheet, the source documents it came from, and the verbatim collector provenance/assumptions. Use it to (a) review and check the already-extracted plans and learn the extraction method, and (b) work the remaining gaps yourself.

**Status legend:** DONE (plan-specific extracted data) | COPIED-DEFAULT (a generic table was pasted in — verify whether it's a legitimate published standard table or a placeholder) | EMPTY (sheet exists but blank) | ABSENT (no sheet).

**Which sheets matter:** the engine reads only `ageservice, retdist, wagerel, mortality, withdrawal, retirement, refund`. `Wage_Growth` and `disability` are GHOST sheets (never read — wage growth comes from PPD). `Refund_Rate` and `Inactv_Serv_Num` are model-DEFAULTED (don't block a run). So real extraction effort = the 6 columns below. See `model_input_dictionary.md`.

**How extraction was documented (the 'from where'):** (1) the source AV/CAFR PDFs listed per plan; (2) the collector logs reproduced verbatim below (Amy Fan / Alex Gant, 2022) — these state, per sheet, what was found, in which document, and what assumption was made; (3) the Airtable base 'Pensions documentation' (export in `Data/Sources/airtable_export/`, currently only Boston's table rows — needs an 'All'-views re-export); (4) the per-sheet keyword catalog in `guidebook_city_collection.md` (what each table is titled in an AV — your search guide when extracting new ones).


## Master matrix (6 model-relevant sheets)

| plan | fund(s) | Age\_Serv\_Num | Age\_Serv\_Wage | Sep\_Rate | Avg\_Mort | Ret\_Rate | Retirement |
|---|---|---|---|---|---|---|---|
| bos_data19_gen | 148 = Boston (State-Boston RS) | DONE | DONE | copy? | copy? | copy? | EMPTY |
| chi_data19_edu | 11 = Chicago Teachers (CTPF) | DONE | DONE | DONE | copy? | DONE | EMPTY |
| chi_data19_ff | 206 = Chicago Fire (FABF) | DONE | DONE | DONE | copy? | copy? | DONE |
| chi_data19_gen | 145 = Chicago Municipal (MEABF) | DONE | DONE | DONE | copy? | DONE | DONE |
| chi_data19_pol | 146 = Chicago Police (PABF) | DONE | DONE | DONE | copy? | DONE | DONE |
| dal_data19_ffpol | 201 = Dallas ERF | DONE | DONE | DONE | DONE | copy? | EMPTY |
| dal_data19_primary_AF | 201 = Dallas ERF | DONE | DONE | DONE | copy? | DONE | DONE |
| dc_data19_ffpol | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | DONE | copy? | copy? | copy? | copy? | EMPTY |
| den_data18_primary | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | ABSENT | DONE | copy? | DONE | copy? | copy? |
| den_data19_primary | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | ABSENT | DONE | copy? | DONE | copy? | copy? |
| fw_dataYY_primary | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | DONE | DONE | DONE | DONE | DONE | DONE |
| hou_data19_ff | 30 = Houston Firefighters (HFRRF) | DONE | DONE | DONE | DONE | DONE | EMPTY |
| hou_data19_gen | 204 = Houston Municipal (HMERF) | DONE | DONE | DONE | DONE | DONE | EMPTY |
| hou_data19_pol | 208 = Houston Police (HPOPS) | DONE | DONE | DONE | DONE | DONE | EMPTY |
| lax_data19_ffpol | 140 = LA Fire & Police (LAFPP) | DONE | DONE | DONE | copy? | copy? | EMPTY |
| lax_data19_gen | 139 = LA City Employees (LACERS) | DONE | DONE | DONE | copy? | copy? | EMPTY |
| lax_data19_uty | 141 = LA Water & Power (DWP) | DONE | DONE | DONE | copy? | DONE | EMPTY |
| mil_data19_gen | 151 = Milwaukee ERS | DONE | copy? | DONE | copy? | copy? | DONE |
| nsh_data20_primary | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | DONE | DONE | DONE | DONE | DONE | DONE |
| nyc_data20_primary | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | ABSENT | DONE | DONE | DONE | DONE | DONE |
| phi_data19_gen | 152 = Philadelphia Municipal (PMRS) | DONE | DONE | DONE | DONE | copy? | DONE |
| phx_data19_gen | 94 = Phoenix (COPERS) | DONE | DONE | DONE | DONE | DONE | DONE |
| sd_data19_gen | 144 = San Diego (SDCERS) | DONE | DONE | DONE | DONE | copy? | DONE |
| sea_data19_primary | — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx) | ABSENT | DONE | DONE | copy? | DONE | DONE |
| sf_data19_gen | 98 = San Francisco (SFERS) | DONE | DONE | DONE | DONE | copy? | DONE |

## Per-plan detail


### bos_data19_gen
- **Fund / ppd_id:** 148 = Boston (State-Boston RS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** MA_BOSTONCITY-SBRS_AV_2019_148.pdf
- **Source CAFR/ACFR PDF(s):** MA_BOSTONCITY-SBRS_CAFR_2019_148.pdf
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | COPIED-DEFAULT (verify) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | COPIED-DEFAULT (verify) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### chi_data19_edu
- **Fund / ppd_id:** 11 = Chicago Teachers (CTPF)
- **Folder layout:** per-fund
- **Source AV PDF(s):** IL_CHICAGOCITY-CTPF_AV_2019_11.pdf
- **Source CAFR/ACFR PDF(s):** IL_CHICAGOCITY-CTPF_CAFR_2019_11.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `chi_data19_edu_log.md`:**

```
Amy Fan 3-2022

Chicago Teachers log


# Primary 

## What wasn't there
* Refund rate 
* Average mortality (life expectancy was there instead) 
* Inactive service numbers
* Retirement numbers were given in a BAR CHART, and broken out by monthly benefit by gender

## Assumptions
* Wage growth: given by age, used age_serv_num table to calculate by years of service
* Retirement Rate: This was a pain, see the sheet for calculations. Gave reitrement rate for two tiers that differed depending on the number of years of service.
* Separation rate: only given by years of service, assume that people didn't start working earlier than 20
* Age_Serv_Num: scraped from sheet
* Age_Serv_Wage: scraped from sheet 

# Tiers 

# Overview
```

### chi_data19_ff
- **Fund / ppd_id:** 206 = Chicago Fire (FABF)
- **Folder layout:** per-fund
- **Source AV PDF(s):** IL_CHICAGOCITY-FABF_AV_2019_206.pdf
- **Source CAFR/ACFR PDF(s):** IL_CHICAGOCITY-FABF_FinancialStatements_2019_206.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | DONE (plan-specific) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `chi_data19_ff_log.md`:**

```
Amy Fan 3-2022

Chicago Firefighters log


# Primary 

## What wasn't there 
* Inactive Service Numbers 

## What was kind of there
* Average mortality: need to manually calculate from the tables, not officially given
* Retirement rates: given by tier, broken out by firefighters and paramedics (unclear how many of each there are)

## Assumptions
* Wage Growth: Minor assumptions, filled in buckets 
* Refund Rate: Combined male and female, assumed that anyone with 
* Separation Rate: No one started working before 20, constant rate of separation for each service bucket (regardless of age)
* Retirement: Combined male and female, computed average manually 
* Age Service Number: combine male and female
* Age Service Wage: Combined male and femaled, computed average manually 

# Tiers 

2 Tiers: 

Tier 1: First hired before January 1, 2011
Tier 2: First hired on or after January 1, 2011
```

### chi_data19_gen
- **Fund / ppd_id:** 145 = Chicago Municipal (MEABF)
- **Folder layout:** per-fund
- **Source AV PDF(s):** IL_CHICAGOCITY-MEABF_AV_2019_145.pdf
- **Source CAFR/ACFR PDF(s):** IL_CHICAGOCITY-MEABF_CAFR_2019_145.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | DONE (plan-specific) |

**Provenance log — `chi_data19_gen_log.md`:**

```
Amy Fan 3-2022

Chicago General log


# Primary 

## What wasn't there 
* Inactive Service Number 
* Retirement Numbers 

## What's kind of there
* Refund Rate: Total number of active, inactive, retirees, and beneficiaries 
* Avg_Mort: Gives estimatation method but not death probability 

## Assumptions
* Wage_Growth: Minor assumptions
* Sep_Rate: No information on age, assume constant, assume no one starts earlier than 20
* Retirement rate: Reported for 3 different tiers, combined based on Age_Serv_Num
* Age_Serv_Num: Combined age and service buckets
* Age_Serv_Wage: Manually computed, combined age and service buckets 

# Tiers 

**Tier 1:** First hired before January 1, 2011
**Tier 2:** First hired from non-reciprocal Fund on or after January 1, 2011 and before July 6, 2017
**Tier 3:** First hired on or after July 6, 2017 or former Tier 2 members that elected to make a one-time irrevocable election to switch to Tier 3 ("elective" Tier 3)
```

### chi_data19_pol
- **Fund / ppd_id:** 146 = Chicago Police (PABF)
- **Folder layout:** per-fund
- **Source AV PDF(s):** IL_CHICAGOCITY-PABF_AV_2019_146.pdf
- **Source CAFR/ACFR PDF(s):** — none in folder —
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | DONE (plan-specific) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `chi_data19_pol_log.md`:**

```
Amy Fan 3-2022

Chicago Police log


# Primary 

## What wasn't there 
* Average Mortality (or at least there was only life expectancy)
* Inactv_Serv_Num

## Assumptions
* Wage Growth: 25-40 took weighted average
* Refund Rate: combined male and female
* Separation rate: Assumed constant across years, didn't start working earlier than 20
* Retirement Rate: 5-11 years of experience all Tier 2, everyone else Tier 1
* Retirement: combined annuity information by age buckets
* Age_Serv_Num: combined <1 year and 1-4 years

# Tiers 

2 Tiers: 
* A member who started working for the CPD prior to January 1, 2011 is considered a "Tier 1" participant
* A member who started working for the CPD on or after January 1, 2011 is considered a "Tier 2" participant in the pension fund pursuant to Article 5 of the Illinois Pension Code.
```

### dal_data19_ffpol
- **Fund / ppd_id:** 201 = Dallas ERF
- **Folder layout:** per-fund
- **Source AV PDF(s):** Tx_Dallas_ERF_AV_2019_201.pdf
- **Source CAFR/ACFR PDF(s):** Tx_Dallas_ERF_CAFR_2019_201.pdf
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | COPIED-DEFAULT (verify) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log — `UpdateLog_Dallas.docx`:**

```
Update Log
2/10/2022-
Completed
Moved all readily available data from existing 2019 dataset into the correct format. 
Added comments to each area where there were band aids applied. 
Notes:
Ret_Rate
Data is not robhust. The data was only presented in age ranges.
Refund_Rate
No data
Avg_Mort
Data is not robhust. The data was only presented in age ranges.
Sep_Rate
Is not broken out by age in data set. 
Retirement
The final three age ranges are not broken out in data set. Evenly divided for simplicity. 
Age_Serv_Num
Data set ended their service year data at 30+. Final 2 service year ranges are split evenly. 
Age_Serv_Wage
See Above
Inact_Serv_Num
No data
 
SUMMARY FOR DALLAS 
What wasn't there: 
Refund Rate
Inactive_Service Number
What assumptions were made: 
Sheet
Assumptions 
Wage_Growth 
None
Ret_Rate
Tier A, Tier B? (I think I only see Tier B here) 
Alex Gant:
There are numerous assumptions happening here. 
1) Data starts at &lt;55. Copied results for each. 
2) Service years are broken out into a) &lt;40 years of service; and b) &gt;40 years of service. 
3. The data exists broken out by Male/Female. This data combines them, presumes equal population.
Avg_Mort
Given by every 10 years from 30-90, averaged by male and female 
Sep_Rate
Alex Gant:
Data included only Male/Female metrics-- not total. Used rudimentary calculation based with assumption that Male and Female Pop are equal: 
(MaleRate/1000 + FemaleRate/1000)/2000
Retirement 
90+ split across 90-94, 95-99, 100+ 
Avg_Serv_Num
Less than 1 and 1-4 combined, 30+ split 
Age_Serv_Wage
Same as Avg_Serv_Num
TIERS 
What was given: 
Eligibility for each Tier
Tier A 
A person who was employed by the City prior to January 1, 2017, or who was re-employed by the City on or after January 1, 2017 and whose pre January 1, 2017 credited service was not cancelled by withdrawal or forfeiture or was reinstated. 
Tier B 
A person who was employed by the City on or after January 1, 2017, or who was re-employed by the City on or after January 1, 2017 and whose pre January 1, 2017 credited service has been cancelled by withdrawal or forfeiture.
Assumptions:
Half of the people who had worked 0-4 years were in Tier A, half were in Tier B
Everyone else was in Tier A
```

### dal_data19_primary_AF
- **Fund / ppd_id:** 201 = Dallas ERF
- **Folder layout:** per-fund
- **Source AV PDF(s):** Tx_Dallas_ERF_AV_2019_201.pdf
- **Source CAFR/ACFR PDF(s):** Tx_Dallas_ERF_CAFR_2019_201.pdf
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | COPIED-DEFAULT (verify) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log — `UpdateLog_Dallas.docx`:**

```
Update Log
2/10/2022-
Completed
Moved all readily available data from existing 2019 dataset into the correct format. 
Added comments to each area where there were band aids applied. 
Notes:
Ret_Rate
Data is not robhust. The data was only presented in age ranges.
Refund_Rate
No data
Avg_Mort
Data is not robhust. The data was only presented in age ranges.
Sep_Rate
Is not broken out by age in data set. 
Retirement
The final three age ranges are not broken out in data set. Evenly divided for simplicity. 
Age_Serv_Num
Data set ended their service year data at 30+. Final 2 service year ranges are split evenly. 
Age_Serv_Wage
See Above
Inact_Serv_Num
No data
 
SUMMARY FOR DALLAS 
What wasn't there: 
Refund Rate
Inactive_Service Number
What assumptions were made: 
Sheet
Assumptions 
Wage_Growth 
None
Ret_Rate
Tier A, Tier B? (I think I only see Tier B here) 
Alex Gant:
There are numerous assumptions happening here. 
1) Data starts at &lt;55. Copied results for each. 
2) Service years are broken out into a) &lt;40 years of service; and b) &gt;40 years of service. 
3. The data exists broken out by Male/Female. This data combines them, presumes equal population.
Avg_Mort
Given by every 10 years from 30-90, averaged by male and female 
Sep_Rate
Alex Gant:
Data included only Male/Female metrics-- not total. Used rudimentary calculation based with assumption that Male and Female Pop are equal: 
(MaleRate/1000 + FemaleRate/1000)/2000
Retirement 
90+ split across 90-94, 95-99, 100+ 
Avg_Serv_Num
Less than 1 and 1-4 combined, 30+ split 
Age_Serv_Wage
Same as Avg_Serv_Num
TIERS 
What was given: 
Eligibility for each Tier
Tier A 
A person who was employed by the City prior to January 1, 2017, or who was re-employed by the City on or after January 1, 2017 and whose pre January 1, 2017 credited service was not cancelled by withdrawal or forfeiture or was reinstated. 
Tier B 
A person who was employed by the City on or after January 1, 2017, or who was re-employed by the City on or after January 1, 2017 and whose pre January 1, 2017 credited service has been cancelled by withdrawal or forfeiture.
Assumptions:
Half of the people who had worked 0-4 years were in Tier A, half were in Tier B
Everyone else was in Tier A
```

### dc_data19_ffpol
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** per-fund
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | COPIED-DEFAULT (verify) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | COPIED-DEFAULT (verify) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | COPIED-DEFAULT (verify) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### den_data18_primary
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** primary+tier
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes, AG Scratch Sheet

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | COPIED-DEFAULT (verify) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | COPIED-DEFAULT (verify) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | COPIED-DEFAULT (verify) |
| Age_Serv_Num | ageservice | CORE | ABSENT (no sheet) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### den_data19_primary
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** primary+tier
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes, AG Scratch Sheet

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | COPIED-DEFAULT (verify) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | COPIED-DEFAULT (verify) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | COPIED-DEFAULT (verify) |
| Age_Serv_Num | ageservice | CORE | ABSENT (no sheet) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### fw_dataYY_primary
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** primary+tier
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | COPIED-DEFAULT (verify) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | DONE (plan-specific) |

**Provenance log — `Log.docx`:**

```
(empty)
```

### hou_data19_ff
- **Fund / ppd_id:** 30 = Houston Firefighters (HFRRF)
- **Folder layout:** per-fund
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (30) — must be fetched. Other PDFs present: 2019_Houston_MERF_AV.pdf, TX_HOUSTONCITY-HPOPS_AV_2019_208.pdf, TX_HMERF_CAFR_2019_204.pdf, TX_HOUSTONCITY-HPOPS_CAFR_2019_208.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### hou_data19_gen
- **Fund / ppd_id:** 204 = Houston Municipal (HMERF)
- **Folder layout:** per-fund
- **Source AV PDF(s):** — none in folder —
- **Source CAFR/ACFR PDF(s):** TX_HMERF_CAFR_2019_204.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### hou_data19_pol
- **Fund / ppd_id:** 208 = Houston Police (HPOPS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** TX_HOUSTONCITY-HPOPS_AV_2019_208.pdf
- **Source CAFR/ACFR PDF(s):** TX_HOUSTONCITY-HPOPS_CAFR_2019_208.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `hou_data19_pol_log.md`:**

```
Amy Fan 4-2022

Houston Police 

# Primary 

## What wasn't there 
* Refund Rate (only had the amount of the refunds, not the number) 
* Inactv_Serv_Mem

## What was kind of there
* Avg_Mort: Broken out by male and female and by active/retired/disabled, unclear on the numbers for each. 
* Retirement: Has distribution by age and by pension amount, but not joint. 

## Assumptions
* Wage_Growth: Assumed constant after 18+ years 
* Separation_Rate: Assumed constant within service years buckets 
* Ret_Rate: 
* Age_Serv_Num: includes DROP participants 
* Age_Serv_Wage: includes DROP participants 

# Tiers 

* T1: ACTIVE MEMBERS SWORN PRIOR TO OCTOBER 9, 2004 
* T2: ACTIVE MEMBERS SWORN AFTER OCTOBER 9, 2004
* T3: CURRENT DROP MEMBERSHIP

Unclear if DROP membership is needed, but I included it in for now
```

### lax_data19_ffpol
- **Fund / ppd_id:** 140 = LA Fire & Police (LAFPP)
- **Folder layout:** per-fund
- **Source AV PDF(s):** CA_LACITY-LAFPP_AV_2019_140.pdf
- **Source CAFR/ACFR PDF(s):** CA_LACITY-LAFPP_CAFR_2019_140.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `lax_data19_ffpol_log.md`:**

```
Amy Fan 4-2022

Los Angeles Firefighter and Police fund 

# Primary 

## What wasn't there 
* Inactive Service Number 

## What was kind of there
* Refund Rate: Includes 484 and 458 inactive members due a refund of member contributions as of June 30, 2018 and June 30, 2019, respectively, no information on distribution 
* Average mortality: broken out by sex, only for pre-retirement mortality rates, broken out by fire and police 
* Retirement rate:Tier, but 
* Retirement: Reported by number and average benefit, but not broken out by age 

## Assumptions
* Wage Growth: Manually added in inflation and "across the board" salary increases (given) to merit and promotion increases 
* Separation Rate: Reported by age and service for police and firefighters separately, combined using data on the number of police and firefighters by age and service 
* Age_Serv_Num: Combined age and service buckets
* Age_Serv_Wage: Combied age and service buckets 

# Tiers 

6 Tiers in the plan, 8 tiers on the sheet 

* T1: Tier 2
* T2: Tier 3
* T3: Tier 4
* T4: Tier 5 (without harbor port police)
* T5: Tier 6 (without harbor port police)
* T6: harbor port police, Tier 5
* T7: harbor port police, Tier 6
* T8: airport police, Tier 6
```

### lax_data19_gen
- **Fund / ppd_id:** 139 = LA City Employees (LACERS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** CA_LACITY-LACERS_AV_2019_139.pdf
- **Source CAFR/ACFR PDF(s):** CA_LACITY-LACERS_CAFR_2019_139.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `lax_data19_gen_log.md`:**

```
Amy Fan 4-2022

Los Angeles ERS

# Primary 

## What wasn't there 
* Inactive Service Number 
* Refund Rate

## What was kind of there
* Average mortality: only given for pre-reitrement
* Retirement rate: Broken out by tier by type of plan, but no information on number of people in each tier 
* Retirement: Reported by number and average benefit, but not broken out by age 

## Assumptions
* Wage Growth: Manually added in inflation and "across the board" salary increases (given) to merit and promotion increases 
* Separation Rate: Assumed constant across age/service years (depending on what was reported), no one started working earlier than 20  
* Age_Serv_Num: Combined age and service buckets
* Age_Serv_Wage: Combied age and service buckets 

# Tiers 

6 Tiers in the plan, 8 tiers on the sheet 

* T1: Tier 1
* T2: Tier 3

Tier 1
(§ 4.1002(a))
All employees who became members of the System before July 1, 2013, and certain employees who became
members of the System on or after July 1, 2013. In addition, pursuant to Ordinance No. 184134, all Tier 2
employees who became members of the System between July 1, 2013 and February 21, 2016 were transferred
to Tier 1 effective February 21, 2016. Includes Airport Peace Officers who did not pay for enhanced benefits.
Tier 1 Enhanced
(§4.1002(e))
All Tier 1 Airport Peace Officers (including certain fire fighters) appointed to their positions before
January 7, 2018 who elected to remain at LACERS after January 6, 2018, and who paid their mandatory
additional contribution of $5,700 to LACERS before January 8, 2019, or prior to their retirement date, whichever
was earlier.
Tier 3
(§4.1080.2(a))
All employees who became members of the System on or after February 21, 2016, except as provided
otherwise in Section 4.1080.2(b) of the Los Angeles Administrative Code
```

### lax_data19_uty
- **Fund / ppd_id:** 141 = LA Water & Power (DWP)
- **Folder layout:** per-fund
- **Source AV PDF(s):** CA_LACITY-DWP_AV_2019_141.pdf
- **Source CAFR/ACFR PDF(s):** CA_LACITY-DWP_CAFR_2019_141.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | EMPTY (missing) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `lax_data19_uty_log.md`:**

```
Amy Fan 4-2022

Los Angeles Water and Power Plan 

# Primary 

## What wasn't there 
* Refund Rate
* Inactv_Serv_Num (both overall and for tiers) 

## What was kind of there
* Average Mortality: gave calculation method, but only reported rates for pre-retirement
* Retirement: includes a graph of the amounts and the number of people, but not the intersection (and also no #s) 

## Assumptions
* Wage Growth: manually added inflation and "across the board" salary increases (given) to the merit and promotion increases
* Separation Rate: Same separation rate by age for the same service year, no one started earlier than 20
* Retirement rate: reported separately for tiers and for <30 and 30+ years of experience 
* Age_Serv_Num: Combined age/service buckets 
* Age_Serv_Wage: Combined age/service buckets and took weighted average

# Tiers 

2 Tiers: 
* Tier 1: All members hired before January 1, 2014. Utility Pre-Craft Trainee, Construction Electrical Helper, or Construction Electrical Mechanic hired before January 1, 2014 and continuously employed until eligible for membership become Tier 1 members upon membership.
* Tier 2: All members hired on or after January 1, 2014
```

### mil_data19_gen
- **Fund / ppd_id:** 151 = Milwaukee ERS
- **Folder layout:** per-fund
- **Source AV PDF(s):** WI_MILWAUKEECITY-ERS_AV_2019_151.pdf
- **Source CAFR/ACFR PDF(s):** WI_MILWAUKEECITY-ERS_CAFR_2019_151.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | COPIED-DEFAULT (verify) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### nsh_data20_primary
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** primary+tier
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | DONE (plan-specific) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | DONE (plan-specific) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

### nyc_data20_primary
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** primary+tier
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | COPIED-DEFAULT (verify) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | ABSENT (no sheet) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log — `updatelog_nyc.docx`:**

```
Feb 14, 2022
Updates: Null
Notes: 
Data set not useful - need to extract directly from CAFR/Pension report.
```

### phi_data19_gen
- **Fund / ppd_id:** 152 = Philadelphia Municipal (PMRS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** PA_PHILADELPHIACITY-MPERS_AV_2019_152.pdf
- **Source CAFR/ACFR PDF(s):** — none in folder —
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `phi_log.docx`:**

```
Amy Fan 
3-2022
Philadelphia log 
SUMMARY FOR PHILADELPHIA 
What information was not there: 
refund rate
inactive service numbers
What was assumed:
Sheet
Assumptions
Wage Growth
This was reported by age, not by service years. However, combined with the information on age x service years, I was able to calculate the wage growth for each age range. Then, I assumed that wage growth was the same for each age within an age range.
Average Mortality
This was reported separately for pre-retirement and post-retirement by male and female. However, not each age was included for the pre-retirement and post-retirement tables: pre-retirement included ages 20-69, while post-retirement included ages 50-95. For ages 20-50 and 65+, I just took the average of the male and female mortality rates for pre-retirement and post-retirement respectively and spread them evenly across the age bin. For ages 50-69, I first took the average of the male/female mortality rates for both the pre and post retirement tables. Then, I took a weighted average of the rates based on the number of active employees (taken from age_serv_num) and retired employees (taken from the retired sheet) 
Separation
This wasn't reported by service year, only by age. Thus, I assumed the same separation rate across the number of service years for each age. However, I also assumed that no one started working before they were 20, so for any of those cases (i.e. 30 years old and 20 years of service), the separation rate is zero 
Retirement
Minimal edits, manually calculated average benefit from total benefit/number of people in age bucket. There was only one age bucket for 85+ that was reported though, so I spread the number of people evenly across the four corresponding age buckets.
Age_Serv_Num
Minimal edits, combined &lt;1 year and 1-4 years, also split 30+ years across 30-34 and 35-40
Age_Serv_Wage
Similar, took weighted average of &lt;1 year and 1-4 years (based off above), assumed same average wage for 30-34 and 35-40
Current questions: 
Retirement rate: Retirement rates are reported by specific plans x age buckets, and also by "first year eligible"/"subsequent years" in some cases. How should the retirement rates be calculated in this case? 
TIERS 
Tier #
Vintage
Type
1
1967
Municipal
2
1967
Police
3
1967
Fire
4
1987
Municipal
5
1987
Elected
6
1987
Police
7
1987
Fire
8
2010
Municipal
9
2016
Municipal
What was not there: 
Inactive members 
Documents used
AV: https://publicplansdata.org/reports/PA_PHILADELPHIACITY-MPERS_AV_2019_152.pdf
Municipal pension financials: https://www.phila.gov/media/20201021085008/muni-pension-financials-FY2019.pdf
Notes
3-1-2022: 
Wage_Growth
By age, not by service years
Refund_Rate
A: What is this? 
B: I don't think I can find it
Avg_Mort
Broken out by plan for male and female by pre-retirement and post-retirement mortality
Ret_Rate
By age and vintage but not by years of service
Sep_rate
Rate of termination by age, but not years of service
Retirement
Haven't found yet
Age_Serv_Num
Combine less than one year with 1-4 years
Split 30+ years between 30-34 and 34-40 years 
Age_Serv_Wage
Weighted average for 1 year + 1-4 year for "&lt;4 years"
Same average salary
3-2-2022: 
Decided to only keep municipal and elected plans 
Questions: 
Is percent married (pctmrg) out of 100 or out of 1? 
1
And is it for all members or active members? 
70% of active members and 50% of non-active members are assumed to be married forretirees with the 50% J&amp;S with return on contribution form of payment only. Male spousesare assumed to be four-years older than female spouses.
Reqcont (required contribution): for the employer?
Employer, but include both  (add column)  
There's wage_inf and inflation: what's the difference?
Wage infl: cola,   
How much do I aggregate the tiers (Each plan is then broken down into types of employees and plan)
Only municipal and elected
3-4-2022:
```

### phx_data19_gen
- **Fund / ppd_id:** 94 = Phoenix (COPERS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** AZ_PHOENIXCITY-COPERS_AV_2019_94.pdf
- **Source CAFR/ACFR PDF(s):** AZ_PHOENIXCITY-COPERS_CAFR_2019_94.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | DONE (plan-specific) |

**Provenance log — `phx_log.txt`:**

```
Amy Fan 3-2022

Log for Phoenix, Arizona


# PRIMARY

What wasn't there: 
* Refund rate 

What was assumed: 
* Wage Growth: just merit or longevity growth
* Average Mortality: Used both pre-retirement and post-retirement death rates. Calculated percentages
	* grouped in age buckets of 5
	* only pre-retirement used from ages 20-49
	* only post-retirement used from ages 70+
	* for ages 50-69, used weighted average 
* Sep_Rate: Only reported "termination rate" for ages 20-60, and for 0,1,2,3,4,5+ years of service
	* Assumed that no one started earlier than 20 years old, so termination rate is 0 for those cells
* Retirement_rate: reported in different age/service buckets, broken out and averaged if needed. 
* Retirement: Few assumptions, manually calculated annual benefit, split up 90+ across multiple age buckets 
* Age_Serv_Num: Combined and divided when needed
* Age_Serv_Wage: Combined and took weighted averages if needed 
* Inactive_Serv_Num: "Inactive Vested Members" 

# TIERS

What information was there: 
* total number of people per tier
* Eligibility per tier 
	* Members who were hired before July 1, 2013, as well as members who join the City after July 1, 2013 who were members of ASRS prior to July 1, 2011 and did not withdraw their contributions are Tier 1 members.
	* Members hired into employment with the City between July 1, 2013 and December 31, 2015 who are not 
Tier 1 members are Tier 2 members.
	* Members hired into employment with the City on or after January 1, 2016 who are not Tier 1 members or Tier 2 members are Tier 3 members.

Assumptions: 
* people had to be 20 or older when starting their job
* The distribution of people followed the default assumptions if the above was met, otherwise there were 0 people
```

### sd_data19_gen
- **Fund / ppd_id:** 144 = San Diego (SDCERS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** CA_SANDIEGOCITY-SDCERS_AV_2019_144.pdf
- **Source CAFR/ACFR PDF(s):** CA_SANDIEGOCITY-SDCERS_CAFR_2019_144.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log — `sd_data19_gen_log.md`:**

```
Amy Fan 4-2022

San Diego ERS

# Primary 

## What wasn't there 
* Refund Rate
* Inactv_Serv_Num

## What was kind of there
* Retirement rate: reported by service years and by age separately, unclear best way to aggregate 

## Assumptions
* Wage_Growth: computed wage growth for 1-4 years by taking weighted average of general and safety, manually added inflation in 
* Avg_Mort: assumed 50/50 male/female, took average and spread across age buckets
* Sep_Rate: weighted average for each age/service bucket between general and safety employees 
* Retirement: Everyone 90+ is distributed evenly between 90-94, 95-99, and 100+
* Age_Serv_Num: Combined buckets 
* Age_Serv_Wage: Combined buckets by taking weighted average 

# Tiers 

There is membership information for the "General" and "Safety" plans, but I don't think these are "tiers" as we define them. 

From the AV: 

    Throughout this report there will be references to "Old Plan," "2009 Plan," "2011 Plan," "2012 Plan," "2012 No COL Plan," and "Prop B Plan" which distinguishes each membership category's various benefit tiers according to their effective dates.

There is no information for these tiers on the AV/CAFR
```

### sea_data19_primary
- **Fund / ppd_id:** — (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)
- **Folder layout:** primary+tier
- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id (nan) — must be fetched. Other PDFs present: none
- **In-workbook scratch/notes sheets:** Notes

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | DONE (plan-specific) |
| Avg_Mort | mortality | matters | COPIED-DEFAULT (verify) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | DONE (plan-specific) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | ABSENT (no sheet) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | ABSENT (no sheet) |

**Provenance log — `log_sea.docx`:**

```
February 15, 2022
Updates:
Finished with all available data. 
Notes: 
Need to manually search for missing variables.
```

### sf_data19_gen
- **Fund / ppd_id:** 98 = San Francisco (SFERS)
- **Folder layout:** per-fund
- **Source AV PDF(s):** CA_SANFRANCITYCOUNTY-SFERS_AV_2019_98.pdf
- **Source CAFR/ACFR PDF(s):** CA_SANFRANCITYCOUNTY-SFERS_CAFR_2019_98.pdf
- **In-workbook scratch/notes sheets:** Notes, AF_Scratch_Work

| sheet | model input | role | status |
|---|---|---|---|
| Wage_Growth | wagegrowth (GHOST: engine ignores) | unused | DONE (plan-specific) |
| Refund_Rate | refund (model-defaults) | defaulted | EMPTY (missing) |
| Avg_Mort | mortality | matters | DONE (plan-specific) |
| Sep_Rate | withdrawal | CORE | DONE (plan-specific) |
| Ret_Rate | retirement | matters | COPIED-DEFAULT (verify) |
| Retirement | retdist | matters (retdist) | DONE (plan-specific) |
| Age_Serv_Num | ageservice | CORE | DONE (plan-specific) |
| Age_Serv_Wage | wagerel | CORE | DONE (plan-specific) |
| Inactv_Serv_Num | inactive scaling (model-defaults) | defaulted | COPIED-DEFAULT (verify) |

**Provenance log:** none in folder (provenance, if any, is in Airtable).

## Airtable table-level documentation (export)

`2. tables-Default.csv` — 18 rows, columns: Name, Complete Data? , Location, pg #, Keywords, What was given, Assumptions

(Per the data-sources map this 'Default' export captured only Boston's table rows; a re-export from the Airtable 'All' views is needed to get every plan's per-table source-doc + page + assumptions.)

```
                          Name  Complete Data?   Location  pg #  Keywords  What was given  Assumptions
                  _Wage_Growth              NaN       NaN   NaN       NaN             NaN          NaN
                  _Refund_Rate              NaN       NaN   NaN       NaN             NaN          NaN
                     _Avg_Mort              NaN       NaN   NaN       NaN             NaN          NaN
                     _Sep_Rate              NaN       NaN   NaN       NaN             NaN          NaN
                     _Ret_Rate              NaN       NaN   NaN       NaN             NaN          NaN
                   _Retirement              NaN       NaN   NaN       NaN             NaN          NaN
                 _Age_Serv_Num              NaN       NaN   NaN       NaN             NaN          NaN
                _Age_Serv_Wage              NaN       NaN   NaN       NaN             NaN          NaN
              _Inactv_Serv_Num              NaN       NaN   NaN       NaN             NaN          NaN
    bos_data19_gen_Wage_Growth              NaN       NaN   NaN       NaN             NaN          NaN
    bos_data19_gen_Refund_Rate              NaN       NaN   NaN       NaN             NaN          NaN
       bos_data19_gen_Avg_Mort              NaN       NaN   NaN       NaN             NaN          NaN
       bos_data19_gen_Sep_Rate              NaN       NaN   NaN       NaN             NaN          NaN
       bos_data19_gen_Ret_Rate              NaN       NaN   NaN       NaN             NaN          NaN
     bos_data19_gen_Retirement              NaN       NaN   NaN       NaN             NaN          NaN
   bos_data19_gen_Age_Serv_Num              NaN       NaN   NaN       NaN             NaN          NaN
  bos_data19_gen_Age_Serv_Wage              NaN       NaN   NaN       NaN             NaN          NaN
bos_data19_gen_Inactv_Serv_Num              NaN       NaN   NaN       NaN             NaN          NaN
```
