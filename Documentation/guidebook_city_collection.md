AF - Last updated: 7-2022

# **Pensions Data Collection: A Guide**

# Table of Contents 

* Guide to this handbook
* To get started
* Data sources
* Things to collect 
* Things to document
* Definitions 

# Guide to this handbook: 

This is designed for people who will be collecting (and documenting) this data. The data is messy! It's not standardized! There are a lot of assumptions that need to be made. 

This data is being collected to model pension funds. The priority is to have data to feed into the model and produce calculations that are similar to what's in the actuarial reports. 

# To get started 

1. Get added to the Sharepoint folder and look through the folders
2. [Join the Airtable]( /invite/l?inviteId=invZYiF1HnffPHGFg&inviteToken=d97ded910a621d381b47fdf5d39ece03a11ab762ae80e1f686aa16c08158ffa2&utm_source=email) (and become familiar with Airtable if necessary)
    * Airtable is a database/spreadsheet software. [Here's](https://www.youtube.com/watch?v=pRUB4nnUp9o) a quick video to get started.
    * There are automations in place on this spreadsheet so that the appropriate documentation records are added whenever a plan is added. See "Workflow to collect and document the data" below. 
3. Read through this guide in full.
4. Start data collection

# Data sources

The data will mainly come from three sources: 
1. AVs and CAFRs taken from the [Public Plans Data](https://publicplansdata.org/resources/download-avs-cafrs/) website.
2. The Public Plans website also has a [database](https://publicplansdata.org/public-plans-database/) with specific variables about each plan. 
3. Directly searching for information on specific plans (usually on the city website) is often also fruitful when it's not available on the AV or CAFR.

To identify each plan-year combination, the database and the documentation will use an ID in the format: {city}\_data{year}\_{plan_type} where: 
* {city} is a 2-3 letter abbreviation of the city 
* {year} is the last two digits of the year
* {plan_type} is one or a combination of 
    * gen: general/municipal 
    * ff: firefighter
    * pol: police
    * edu: teachers/education
    * uty: utilities
    * Abbreviations can be combined. For example, a joint police and firefighter fund would be called ffpol. 

For example, the general pension plan for Boston in 2019 is abbreviated as bos_data19_gen.

# Workflow to collect and document the data

The below may be done by multiple people. Make sure to coordinate with the other people on the team!

0. Pick a plan and find the AV/CAFR from the [Public Plans Data](https://publicplansdata.org/resources/download-avs-cafrs/) website.
1. Fill out [this form](https://airtable.com/shrNjRlVr9OmRPcHu) to add the plan to the Airtable. Afterwards, the following things will happen on each sheet: 
    * **1. plans** will have a new record for this plan-year
    * **1a. checklist** will have a checklist with the remaining steps.
    * **2. tables** will create one record for each of the 9 tables.  
    * **3. tiers** will create a single record for one tier. New tiers should be added manually.
    * **4. plan details** will have one record for that plan
2. Collect data for the plan and tiers on the Excel sheet for the plan (see below)
3. Document the plan and tiers on sheets on **2. tables** and **3. tiers** respectively
4. Document the plan variables on **4. plan details**
5. Review missing pieces, fill in with assumptions, revise documentation
6. Transform the plan sheets and tier sheets into the right shape
7. Import into database 

# Things to collect: 

There are three types of data to collect. For each kind of data, the data needs to collected and documented. 

Type of variable | Where to collect | Where to document 
--- | --- | ---
A. Plan variables | ??? | Airtable: **4. plan details**
B. Plan sheets | Excel sheet in Sharepoint with name: {city}\_data{year}\_{plan_type}| Airtable: **2. tables**
C. Tier sheets | Excel sheet in Sharepoint with name: {city}\_data{year}\_{plan_type}| Airtable:  **3. tiers**
D. Tier variables | Excel sheet in Sharepoint with name: {city}\_data{year}\_{plan_type}_tiervars| Airtable: **4. plan details** 

The excel sheets can be found in the Sharepoint, which for me (for example) can be found at: 

    C:\Users\SLOANUSER\Massachusetts Institute of Technology\MIT Golub Center for Finance and Policy - State and Local Pension\1. Pension Data

Each city will have its own folder, and all the plan-year excel sheets for that year will be in that folder. 

## A. Plan variables

AG please document this

These will initially be taken from the public plans database, but they may change afterwards. 

## B. Plan sheets

For each plan-year, the following tables will need to be filled in: 

Sheet | Description | Unit
--- | --- | ---
Wage_Growth | Salary increase, including inflation/merit and promotion increases/COLA (if given) | Percentage out of 1
Refund_Rate | The number of people each year who are refunded their pension contributions when they leave public service, broken out by age and service year | Count
Avg_Mort | probability that an employee (active or retired) will pass away in a given year | Probability out of 1
Sep_Rate | Termination rate, broken out by age and service year | Percentage out of 1
Ret_Rate | Retirement rate, broken out by age and service year | Percentage out of 1
Retirement | Number of employees in retirement and  benefit amount, broken out by age | For number of employees: count, for benefit: average annual benefit in $
Age_Serv_Num | The number of active employees, broken out by age and service years | Count
Age_Serv_Wage | The average annual wages of active members, broken out by age and service years | Average annual wage
Inactv_Serv_Num | The number of inactive employees, broken out by age and service years | Count

Broadly, a lot of these things will be under "actuarial assumptions" 

### **Notes per sheet:**

Things to look for, assumptions that will often have to be made, thins that oftentimes won't be present

### Wage_Growth 

Keywords to look for: 
* Salary increase rate
* Annual Compensation Increases
* Future Salary Increases
* Salary increases

Other notes: 
* This is annual wage growth.
* This is nominal wage growth, so it should include all the inflation/COLA increases alongside the merit/promotion increases

### Refund_Rate  

Keywords: 

* Refunds
* Number of refunds 

Notes: 

* This is not the percentage that is refunded to people. Rather, it is the _number_ of people who have a refund
* Usually, you will be able to find the dollar amount of people who have refunds, or maybe the total number of people who have refunds.

### Avg_Mort 

Keywords: 
* Mortality Rates
* Rates of Pre-Retirement [or Post-Retirement] Mortality
* Rates of Mortality

Notes: 

* This is almost always broken out by male and female. When necessary, I made the following assumptions
    * [4% of career firefighters are women](https://www.nfpa.org/News-and-Research/Publications-and-media/Press-Room/News-releases/2020/Females-still-make-up-less-than-10-percent-of-the-US-fire-service)
    * [About half (48%) of government affairs employees are women](https://www.zippia.com/government-affairs-careers-738330/demographics/)
        * I would assume that utilities fall under the same category
    * [16.8% of police officers are women](https://www.zippia.com/police-officer-jobs/demographics/)
* Rates are also often reported separately for pre and post retirement. If this is the case, I generally use pre-retirement rates for under 65, and post-retirement rates for 65 and over.
* Sometimes you'll just see how the rates are calculated based on actuarial tables, and sometimes you'll see life expectancy instead.

### Sep_Rate 

Keywords: 
* Rates of Termination
* General Turnover
* Termination Rates 

Notes: 

* Oftentimes, this will only be reported by service years, not by service year and age. (or just by age) In those cases, just 

### Ret_Rate

Keywords: 
* Retirement
* Rates of Retirement
* Retirement Rates 

Notes: 
* This often isn't reported by both age and service years, so will have to assume constant across age/service year
* Sometimes reported across tiers--use age/service year information to combine

### Retirement

Keywords: 
* Distribution of Benefit Recipients
* Age Distribution of Retired Members 
* Service Retirement Annuitants
* Pensions Awarded in Current Year by Type and by Age
* Summary of Members in Pay Status -- Service Retirees
* Employee Annuitants as of [DATE] By Age and Annual Benefit
* Statistics on Service Retirement Annuities Classified by Age
* Schedule of Retired Members by Attained Age and Type of Pension Benefit
* Retirees Classified by Benefit Amount and Age
* Retired Members and Beneficiaries
* Retired Membership by Age
* Distribution of Retired Members and Beneficiaries
* Distribution of Retirees (Includes DROP Participants), Disabled, and Beneficiaries

Notes: 
* Oftentimes, this is reported by age distribution and by benefit amount, but not mutually both.

### Age_Serv_Num

Keywords: 
* Distribution of Active Members and Payroll by Age and Years of Service
* Distribution of Active Participants 
* All Members in Active Service
* DISTRIBUTION OF ACTIVE MEMBERS BY AGE AND BY YEARS OF SERVICE
* Active Member Counts by Age and Service
* Total Lives and Annual Salaries of All Active Participants Classified by Age and Years of Service
* Age and Service Distribution for Active Members
* Total Lives and Annual Salaries of Active Members Classified by Age and Years of Service
* MEMBERS IN ACTIVE SERVICE AS OF \[DATE\] BY AGE, YEARS OF SERVICE, AND AVERAGE PROJECTED COMPENSATION 

Notes:
* Will sometimes have different age buckets, need to combine and divide as needed 
* Will sometimes include DROP and sometimes exclude DROP 

### Age_Serv_Wage

Keywords (similar to Age_Serv_Num): 
* Distribution of Active Members and Payroll by Age and Years of Service
* Distribution of Active Participants (Excludes DROP Participants)
* All Members in Active Service
* DISTRIBUTION OF ACTIVE MEMBERS BY AGE AND BY YEARS OF SERVICE 
* Active Member Average Salary by Age and Service
* All Members in Active Service as of \[DATE\] By Age, Years of Service, and Total Salary
* Total Lives and Annual Salaries of All Active Participants Classified by Age and Years of Service
* Default Assumptions
* Total Lives and Annual Salaries of Active Members Classified by Age and Years of Service
* MEMBERS IN ACTIVE SERVICE AS OF \[DATE\] BY AGE, YEARS OF SERVICE, AND AVERAGE PROJECTED COMPENSATION TOTAL PLAN
* Distribution of Active Members

Notes:
* Will sometimes have different age buckets, need to combine and divide as needed 
* Will sometimes include DROP and sometimes exclude DROP 

### Inactv_Serv_Num

Keywords: 
* Summary of Inactive Vested Members
* Inactive Members as of \[DATE\] By Age and Years of Service

Notes:
* This isn't often present that often. 

## C. Tier sheets 

These sheets should be added to the end of the plan sheets in the Excel spreadsheet

Sheet Name | Description 
--- | ---
T{TIER #}_Age_Serv_Num | The number of active employees, broken out by age and service years
T{TIER #}_Inactv_Serv_Num | The number of inactive employees, broken out by age and service years 

If this information isn't available, sometimes you can also use the distributions from the default assumptions. 

## D. Tier variables 

This will be documented in a separate excel sheet called 

Each line on the spreadsheet should represent a different class. 

template was taken from Brookings--they used a similar method to collect their data. 

In general, take screenshots of everything and keep it in the Excel sheet--everything will have to be manually reviewed again anyway. 

Variable | Name | Notes
--- | --- | ---
planid | Name of the plan | e.g. bos_data19_gen
startdate1 | Start date for that tier | Assume the earliest start date is 1/1/1960
benefitfactor1 | Benefit factor | Percentage of pay to which you are entitled for each year of service in your pension). Oftentimes, this number changes based on the number of years of service. For instance, the benefit factor may be 2.0% for each of the first 20 years of service and 1.5% for each year afterwards. In those cases, feel free to use 2%, 1.5%, or something in between (I would do 2%) and put screenshot of the specific policy into the spreadsheet. 
cola1 | COLA adjustment | Usually, this is for the most recent year, can be a percentage or a calculation method (aka "min(.03, CPI)")
our_cola1 | Brookings COLA | ignore this variable for now
type1 | COLA Type | 1 = fixed, 2 = function of inflation, 3 = function of asset returns or funding level, 4 = ad hoc (typically 0)
compounded1 | Does the COLA compound? | 1 = yes, 2 = no
nr1 | Normal retirement age | If there are multiple ages at which you can retire (usually as a function of the number of service years), I usually assume that this is the oldest one. 
er1 | Early retirement age | If there are multiple ages at which you can retire (usually as a function of the number of service years), this can be the youngest one. BUT sometimes there is also a separate category on the AV/CAFR for early retirement. If so, use that.  
vesting1 | Years required for vesting | The number of years that someone has to work in order to have full access to the amount of their pension. Sometimes this is directly stated, but otherwise I just put the minimum service requirement to retire (usually something like 5)
maxsal1 | Maximum percentage of salary in pension | Percentage out of 1
yrsal1 | Number of years averaged for final salary calculation used for benefits | If there is no limit, feel free to put -100 (or just leave empty)
ercont1 | Employer contribution | Percentage of total payroll (alternatively, percentage of an employee's salary), percentage out of 1
eecont1 | Employee contribution | Percentage of employee salary that goes towards the pension fund, percentage out of 1 
Type | Name/Type of tier | Not always necessary (the start date should identify the tier), but sometimes there may be tiers with the same start date but with different provisions. Most commonly, this will for different kinds of employees, like police versus municipal employees. Use this variable to distinguish between those plans. 

# How to document the data

In general, if there are specific nuances for specific plans, feel free to leave the documentation/screenshots/explanation in the spreadsheets

For instance, many of the Excel workbooks will have a sheet called "AF_Scratch_Work" where I kept the intermediate calculations. 

## A. Plan variables 

This should be documented in **4. plan details**

AG please document this 

## B. Plan sheets

This will be documented in **2. tables**. For each table, the following should be recorded: 

* to what degree the information was available
* the document in which the information was found (AV/CAFR)
* the page number in the document where it was found
* the keywords that were associated with the table (title, headers, section, etc) 
* a description of what data was available 
* a description of the assumptions that were necessary to fill in the table (or a description of why the data wasn't able to be filled in)

## C. Tier sheets

This should be documented in **3. tiers**. For each tier, the following should be documented: 

* the number of the tier 
* a description of what the tier is 

## D. Tier variables 

This could be documented in **4. plan details** in the future, but currently, most of the documentation is left in the individual spreadsheets. 

# Conclusion

Ask questions, make assumptions, learn about pensions. '