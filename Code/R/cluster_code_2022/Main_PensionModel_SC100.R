# For each person, this is location of the BucketFill.R, PensionModel_Functions.R, and PensionModel_Liability_Tiers.R... as well as the .xlsx data
#DSdir <- "/home/dan/PhD/Pension_CF_Model/"
#DSdir <- "/data/smithafe/Pension_CF_Model/"
#DSdir <- "/Users/tanyaratra/Desktop/Tanya_Ratra/Fall2023/RA/State Pension Model"
script_path <- NA_character_
script_path <- tryCatch({
  ofile <- sys.frame(1)$ofile
  if (!is.null(ofile)) normalizePath(ofile) else NA_character_
}, error = function(e) NA_character_)
if (!file.exists(script_path)) {
  script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  script_path <- if (length(script_arg)) normalizePath(sub("^--file=", "", script_arg[1])) else file.path(normalizePath("cluster_062026"), "cluster_code_2022")
}
script_dir <- dirname(script_path)
current_dir <- normalizePath(file.path(script_dir, ".."))
run_tag <- "062026"

plan <- "SC100"
date_run <- "2022_July2024"
#Sheets are 
#1 ageservice (the number of workers in age service matrix)
#2 retdist (the distribution of retirees and benefits by age)
#3 wagerel (the wage relative to the average wage in age service matrix)
#4 mortality (mortality table by a)
#5 wagegrowth (current constant in our model)
#6 withdrawal (the rate which people withdraw from the workforce in age service matrix) [Also called Separation]
#7 retirement (the rate which people retire from the workforce in age service matrix)
#8 refund (the rate which people choose to receive a refund when they withdraw in age service matrix)
#9 disability (Code doesn't currently use fund reported disability)
#availableData <- c(1,2,3,4,5,6,7,8,9)
availableData <- c(T,T,T,T,T,T,F,F,F)


planFolder <- paste0("../../Data/Plans/States/", plan, "/")
runFolder <- file.path(dirname(dirname(current_dir)), "Results", "Runs", run_tag, plan)

fileName <- paste0(plan,"_2017.xlsx")

# set the proper working directory
setwd(current_dir)



# import library to read excel sheets 
#library("readxl")
library("readxl")
#get other code 

# import scripts with necessary functions 
# BucketFill fills out a bucket matrix using a linear function
source('Common_Code/bucketfill_cf_model.R')
source('Common_Code/functions_cf_model.R')
source('Common_Code/liability_cf_model.R')

# For replicability
set.seed(54848631)

## Plan Number
ppid <- as.numeric(gsub("[^0-9]", "", plan))

## Plan start
plan_start <- as.Date("2022-01-01")

## Plan ID
plan_id <- paste0(plan,"_2022") 


## Plan Year
plan_year <- 2022


#Get plan info
planinfo <- read_excel("../../Data/Common/states/ppd-data-latest.xlsx", sheet = "ppd-data-latest", col_names=TRUE)

planinfo <- planinfo[planinfo$ppd_id==ppid & planinfo$fy == plan_year,]


#Additional info
PPD <- read.csv("../../Data/Common/states/PPD_planlevel_main_updated.csv", stringsAsFactors = F)


PPD <- PPD[which(PPD$planid==plan_id),]

#####################################################################################
#################################Variables to Change#################################
#####################################################################################
###
#Variables can be changed throughout the code but these are some of the most commonly changed variables
###

#How much wages grow every year
WageGrowth <- get_wage_growth_assumption(plan, planinfo)


##  how much to discount liabilities
discountrate <- planinfo$InvestmentReturnAssumption_GASB

##  These were backed out from looking at contributions from the AR report 
EmployeeContributionRate <- planinfo$contrib_EE_regular/planinfo$payroll
EmployerContributionRate <- planinfo$contrib_ER_regular/planinfo$payroll




##  Inflation Rate
Inflation <- get_inflation_assumption(plan, planinfo)

## (COMBO) Nominal risk-free rate
rf <- .01+Inflation

## (COMBO) Growth rate of the population to determine hiring increases. Is a constant now but could become a Vector
PopulationGrowth <- 0.01



##  How much to scale cash-flows by to match CAFR
scaling <- 1



#####################################################################################
#####################################################################################
#####################################################################################



tierinfo <- read_excel("../../Data/Common/states/planchanges_main_2022_clean.xlsx", sheet = "in", col_names=TRUE)



tierinfo <- tierinfo[which(tierinfo$planid==plan_id),]

tier_info2 <- data.frame(startdate = as.Date(character()),
                         benefitfactor=double(),
                         vesting=double(),
                         maxsal=double(),
                         yrsal=double(),
                         nr =double(),
                         er=double(),
                         cola=double())



#put tier info into an easier to use format
for (i in c(1:6)) {
  
  
  tier_info2[i,1] <-  tierinfo[,c(paste0("startdate",i))]
  
  tier_info2[i,2] <-  tierinfo[,c(paste0("benefitfactor",i))]
  
  tier_info2[i,3] <-  tierinfo[,c(paste0("vesting",i))]
  
  tier_info2[i,4] <-  tierinfo[,c(paste0("maxsal",i))]
  
  tier_info2[i,5] <-  tierinfo[,c(paste0("yrsal",i))]
  
  tier_info2[i,6] <-  tierinfo[,c(paste0("nr",i))]
  
  tier_info2[i,7] <-  tierinfo[,c(paste0("er",i))]
  
  
  tier_info2[i,8] <-  tierinfo[,c(paste0("cola",i))]
  
  
}



tier_info2 <- unique(tier_info2)

#Number of tiers 
num_tiers <- dim(tier_info2)[1]

#services years for different tiers


tier_serivce <- round(as.numeric(difftime(plan_start,tier_info2$startdate,unit="weeks")) /52.25
                      ,digits=0)







######################################
## MODEL WIDE SIMULATION PARAMETERS ##
######################################

## Choose the number of years to simulate
Nyear <- 35

## Choose the number of simulations to run for simulation
NMonte <- 1


######################################
## UNIVERSAL VARIABLES ACROSS TIERS ##
######################################

##  The year inactive members must begin taking benefits.
InactiveRetirement <- 65

##  AMOUNT OF ASSETS in the fund
Assets <- matrix(0,nrow = Nyear,ncol= NMonte)
Assets[1,] <- planinfo$ActAssets_GASB*1000

##  yearly disability payout as a percent of payroll
DisabilityPayoutRate <-.025

##  At the inflation rate for now, need to find actual amount
refundReturn <-  rf

##  discount rate for annuity
annuity_dr <- rf

##  COLA
COLA_c <- mean(tier_info2$cola)

#percent marrired
pct_mrg <- PPD$pctmrg


#reduction in benefits for survivors
widow_reduct <- PPD$reduct


#The max age of a retired employee
RetirementMax <- 104

#Start age and oldest employee age
EmployeeStart <- 20
EmployeeEnd <- 74

ServiceStart <- 1
ServiceEnd <- 55

#Percent of Population that is male
pctmale <- PPD$pctmale

# If the simulated number of deaths  differs from whats observed in the plan history
# Active employees die less mortality rate predicts. This might be because upon sickness they choose
# to leave and get refund or retire early?
MortAdujst <- 1

###########################################
######### TIER SPECIFIC VARIABLES #########
###########################################

## THESE ARE DIFFERENT FOR EACH TIER 

for (i in c(1:6)){
  
  
  if(i <= num_tiers){
    
    # The factor used to calculate benefits
    varName <- paste0("BenefitFactor_t", i)
    assign(varName, tier_info2$benefitfactor[[i]]) 
    
    ## How many years of past are put into average for benefit calculation
    varName <- paste0("WageYears_t", i)
    assign(varName, tier_info2$yrsal[[i]]) 
    
    
    ##  COLA
    varName <- paste0("COLA_t", i)
    assign(varName, tier_info2$cola[[i]]) 
    
    
    ##  A cap on the replacement rate achievable by an employee
    varName <- paste0("BenefitCap_t", i)
    assign(varName,  ifelse(tier_info2$maxsal[[i]]==-100,100,tier_info2$maxsal[[i]])) #
    
    ##  Number of years of service to get full benefit treatment
    varName <- paste0("NyearFullBenefit_t", i)
    assign(varName,  tier_info2$vesting[[i]]) 
    
    # The age retirement starts
    varName <- paste0("RetirementStart_t", i)
    assign(varName, tier_info2$nr[[i]]) 
    
    
  }
  
  
}




####################Get ASY active employee data####################

if(availableData[[1]]){
asy_employee <- as.matrix(read_excel(paste0(planFolder,fileName),
                                sheet = "ageservice", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))*planinfo$actives_tot

}else{
  asy_employee <- as.matrix(read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                            sheet = "ageservice", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))*
    planinfo$actives_tot
  
  
}

#Linear Fill
#Takes ASY data
#The slope for how to linearly fill the buckets
# The column to use to fill the matrix

active <- LinearFill(asy_employee,Slope=1)



####################Get ASY wage employee data####################

if(availableData[[3]]){
  asy_wage <- as.matrix(read_excel(paste0(planFolder,fileName),
                                       sheet = "wagerel", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))*
    planinfo$ActiveSalary_avg*1000
  
}else{
  asy_wage <- as.matrix(read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                       sheet = "wagerel", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))*
    planinfo$ActiveSalary_avg*1000
  
  
}


#Constant Fill
#Takes ASY data
# The column to use to fill the matrix
BaseWage <- ConstantFill(asy_wage)

##Create a 3d matrix
BaseWage <- array(BaseWage, c(dim(BaseWage), Nyear));

BaseWage[,,2:Nyear] <- 0


####################Get Retirement Rate data####################
if(availableData[[7]]){
  asy_retrate <- as.matrix(read_excel(paste0(planFolder,fileName),
                                   sheet = "retirement", range = "Q2:AA12",col_names = F,.name_repair = "unique_quiet"))/100
  
}else{
  
  #TO DO: There is no default retirement matrix yet because Brookings assumes constant rates
  asy_retrate <- as.matrix(read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                 sheet = "retirement", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))/100
}


# -100 in source data signals ineligibility, not a rate; ConstantFill does not clip negatives
asy_retrate[asy_retrate < 0] <- 0
RetirementRate <- ConstantFill(asy_retrate,enforce_service_limit=F)



#################### Get Refund Rate Data ####################

if(availableData[[8]]){
  asy_refundrate <- as.matrix(read_excel(paste0(planFolder,fileName),
                                      sheet = "refund", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))*pctmale+
    as.matrix(read_excel(paste0(planFolder,fileName),
                         sheet = "refund", range = "O2:Y12",col_names = F,.name_repair = "unique_quiet"))*(1-pctmale)
  
}else{
  
  
  asy_refundrate <- as.matrix(read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                      sheet = "refund", range = "B2:L12",col_names = F,.name_repair = "unique_quiet"))
}



RefundRate <- ConstantFill(asy_refundrate)


#################### Get Seperation Rate Data ####################
if(availableData[[6]]){
  asy_seprate <- as.matrix(read_excel(paste0(planFolder,fileName),
                                         sheet = "withdrawal", range = "A1:L12",col_names = F,.name_repair = "unique_quiet"))*pctmale/100+
    as.matrix(read_excel(paste0(planFolder,fileName),
                         sheet = "withdrawal", range = "N1:Y12",col_names = F,.name_repair = "unique_quiet"))*(1-pctmale)/100
  
  asy_seprate[1:12,1] <-  asy_seprate[1:12,1] *100
  
  asy_seprate[1,2:12] <-  asy_seprate[1,2:12] * 100
  
}else{
  
  
  asy_seprate <- as.matrix(read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                         sheet = "withdrawal", range = "A1:L12",col_names = F,.name_repair = "unique_quiet"))

}



SeparationRate <- ConstantFill_SepRate(asy_seprate)

#asy_seprate <- asy_seprate[2:12,2:12]
#SeparationRate <- ConstantFill_brook(asy_seprate)

#################### Get Mortality Rate Data ####################


if(availableData[[4]]){
  mort_table <- rbind(read_excel(paste0(planFolder,fileName),
                                      sheet = "mortality", range = "B2:D6",col_names = T),
 read_excel(paste0(planFolder,fileName),
                         sheet = "mortality", range = "F2:H6",col_names = T))
  
}else{

  mort_table <- rbind(read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                 sheet = "mortality", range = "B2:D6",col_names = T),
                      read_excel("../../Data/Common/states/default_assumptions.xlsx",
                                 sheet = "mortality", range = "F2:H6",col_names = T))
  
}



MortalityTable <- MortTable(mort_table,pctmale)




#Calculate Annuity prices
# An annuity is paid out to the spouse of an employee that dies while active
AnnuityVector <- ComputeAnnuity(COLA_c)


#################### Get Retirement Number and Benefit Data ####################

if(availableData[[2]]){
  ret_num <- read_excel(paste0(planFolder,fileName),
                                 sheet = "retdist", range = "B1:B17",col_names = T)*planinfo$beneficiaries_tot
  
  ret_ben <- read_excel(paste0(planFolder,fileName),
                               sheet = "retdist", range = "F1:F17",col_names = T)*planinfo$BeneficiaryBenefit_avg*1000
  
}else{
  
  
  ret_num <- read_excel("../../Data/Common/states/default_assumptions.xlsx",
                        sheet = "retdist", range = "B1:B17",col_names = T)*planinfo$beneficiaries_tot
  
  ret_ben <- read_excel("../../Data/Common/states/default_assumptions.xlsx",
                        sheet = "retdist", range = "F1:F17",col_names = T)*planinfo$BeneficiaryBenefit_avg*1000
  
}




#Slope is negative because there should be less people as age increases
RetirementNumber <- LinearFill(ret_num,Slope=-1,retirement=T)

RetirementBenefit <- ConstantFill(ret_ben,retirement=T)


#Calculate the inactive matrix number assuming a given tier retirement start and vesting period
inactive <-Calc_Inactive(active, SeparationRate, RefundRate,
                         MortalityTable,RetirementStart_t1,NyearFullBenefit_t1)


#If the BC vested inactive members data is accurate based on what Brookings reported
# in 2017, then take the data from them. If it is inacurate then the number of inactives
# is a fraction of the total of actives based on Brookings reporting
inactive <- scale_inactive_members(inactive, plan, planinfo, PPD)

#create the different matrices for all the tiers
CreateTiers(active,inactive,num_tiers)


# Start the clock
ptm <- proc.time()

#Main_Current takes:
# 1. collapsed active  age/serv matrix
# 2. collapsed inactive age/serv matrix
# 3. COLA: Cost of Living adjust ment
# 4. WageYears: The number of years to calculate average wage for benefit calculation
# 5. BenefitCap : The maxiumum replacement rate
# 6. BenefitFactor : The factor times years of service to get replacement rate
# 7. RetirementStart : How old they can start retiring
# 8. NyearFullBenefit : The number of years to be fully vested
# 9. A flag for if it is the current tier


#Main_Current outputs a list of 3 matricies which are T x N
#Where T is the year and N is the simulation number:
# 1. The actuarial accrued liability
# 2. the cash out flow
# 3. the cash inflow

setCurrentTier <- F
for (i in c(1:6)){
  
  varName <- paste0("MainRes_Tier", i)
  
  
  if(num_tiers >= i){
    if(num_tiers==i){setCurrentTier <- T}
    # Create variable name dynamically
    assign(varName,  Main_Current(get(paste0("active_t", i)),get(paste0("inactive_t", i)),
                                  get(paste0("COLA_t", i)), get(paste0("WageYears_t", i)),get(paste0("BenefitCap_t", i)),
                                  get(paste0("BenefitFactor_t", i)),get(paste0("RetirementStart_t", i)),
                                  get(paste0("NyearFullBenefit_t", i)),CurrentTier=setCurrentTier))
  }else{
    
    assign(varName,list(array(0,dim(MainRes_Tier1[[1]])),array(0,dim(MainRes_Tier1[[2]])),
                        array(0,dim(MainRes_Tier1[[3]])),array(0,dim(MainRes_Tier1[[4]])),
                        array(0,dim(MainRes_Tier1[[5]]))))
    
  }
  
  
  
  
}




proc.time() - ptm

RetRes <- Main_Ret(RetirementNumber,RetirementBenefit)


#Sum Cash Flows
main_cf <- MainRes_Tier1[[2]]  + MainRes_Tier2[[2]] + MainRes_Tier3[[2]] + MainRes_Tier4[[2]] +
  MainRes_Tier5[[2]]+ MainRes_Tier6[[2]]  

ret_cf <- RetRes[[2]]

cash_outflows <- main_cf+ret_cf

cash_inflows <- MainRes_Tier1[[3]]  + MainRes_Tier2[[3]]+ MainRes_Tier3[[3]]+ MainRes_Tier4[[3]]+
  MainRes_Tier5[[3]]+ MainRes_Tier6[[3]]


NormalCost <- MainRes_Tier1[[5]]+MainRes_Tier2[[5]]+MainRes_Tier3[[5]]+MainRes_Tier4[[5]]+
  MainRes_Tier5[[5]]+MainRes_Tier6[[5]]


#
#COMPARE OUTPUT
#

#Liabilities
# This is the acturial accrued liabilities
# The first row in this data frame should match what is reported in the CAFR
AAL <- MainRes_Tier1[[1]]+MainRes_Tier2[[1]]+RetRes[[1]]+MainRes_Tier3[[1]]+MainRes_Tier4[[1]]+
  MainRes_Tier5[[1]]+MainRes_Tier6[[1]]


Model_AAL <- AAL[1,1]

CAFR_AAL <- planinfo$ActLiabilities_GASB*1000 # get actual value from CAFR

#compute difference
Percent_difference <- (Model_AAL-CAFR_AAL)/CAFR_AAL



Compare_Result <- data.frame(type=character(),model=numeric(),cafr=numeric(),dif=numeric(),stringsAsFactors = F)


Compare_Result[1,1] <- "EAN"
Compare_Result[1,2] <- Model_AAL
Compare_Result[1,3] <- CAFR_AAL
Compare_Result[1,4] <- Percent_difference




if (!dir.exists(runFolder)) {
  dir.create(runFolder, recursive = TRUE)
}
save.image(file = file.path(runFolder, paste0(plan, "_detAL_2022_", run_tag, ".RData")))




