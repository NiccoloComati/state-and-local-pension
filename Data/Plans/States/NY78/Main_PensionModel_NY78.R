# For each person, this is location of the BucketFill.R, PensionModel_Functions.R, and PensionModel_Liability_Tiers.R... as well as the .xlsx data
#DSdir <- "/home/dan/PhD/Pension_CF_Model/"
DSdir <- "/Users/tanyaratra/Desktop/Tanya_Ratra/Fall2023/RA/State Pension Model"
planFolder <- "NY78/"

fileName <- "NY78_2017.xlsx"

# set the proper working directory
setwd(DSdir)

# Check that the location is set.
#getwd()

# import library to read excel sheets 
library("readxl")
#get other code 

# import scripts with necessary functions 
# BucketFill fills out a bucket matrix using a linear function
source('Common_Code/bucketfill_cf_model.R')
source('Common_Code/functions_cf_model.R')
source('Common_Code/liability_cf_model.R')

# location and name of datasets
#DataLocation_Const <- "MortTable.xlsx"

# For replicability
set.seed(54848631)



## Plan Number
ppid <- 78



## Plan start
plan_start <- as.Date("2017-01-01")

## Plan ID
plan_id <- "NY78_2017"


## Plan Year
plan_year <- 2017


#Get plan info
planinfo <- read_excel("Common_Data/ppd-data-latest.xlsx", sheet = "ppd-data-latest", col_names=TRUE)

planinfo <- planinfo[planinfo$ppd_id==ppid & planinfo$fy == plan_year,]


#Additional info
PPD <- read.csv("Common_Data/PPD_planlevel_main.csv", stringsAsFactors = F)


PPD <- PPD[which(PPD$planid==plan_id),]



tierinfo <- read_excel("Common_Data/planchanges_main.xlsx", sheet = "in", col_names=TRUE)



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
NMonte <- 10

## Choose the proportion of assets you want to be stocks
AssetShareStocks <- (planinfo$COMDTotal_Actl+planinfo$OtherTotal_Actl+planinfo$PETotal_Actl+
                       planinfo$EQTotal_Actl+planinfo$AltMiscTotal_Actl+ planinfo$HFTotal_Actl+planinfo$RETotal_Actl)

## Choose the proportion of assets you want to be bonds
AssetShareBonds <- 1-AssetShareStocks

#How vector of asset allocation
AssetShare <- c(AssetShareStocks, AssetShareBonds)

######################################
## UNIVERSAL VARIABLES ACROSS TIERS ##
######################################

# DYNAMIC=change for each city/dataset; STATIC=fixed parameter; COMBO=static unless data indicates otherwise#

## (DYNAMIC) The year inactive members must begin taking benefits.
InactiveRetirement <- 65

## (DYNAMIC) AMOUNT OF ASSETS in the fund
Assets <- matrix(0,nrow = Nyear,ncol= NMonte)
Assets[1,] <- planinfo$ActAssets_GASB

## (DYNAMIC) yearly disability payout as a percent of payroll
DisabilityPayoutRate <-.025

## (DYNAMIC) At the inflation rate for now, need to find actual amount
refundReturn <-  planinfo$InflationAssumption_GASB

## (DYNAMIC) Inflation Rate
Inflation <-  planinfo$InflationAssumption_GASB


WageGrowth <-  planinfo$InflationAssumption_GASB

## (COMBO) Nominal risk-free rate
rf <- .01



## (DYNAMIC) discount factor for annuity
annuity_df <- rf

## (DYNAMIC) how much to discount liabilities
discountrate <- PPD$discount

## (DYNAMIC) These were backed out from looking at contributions from the AR report 
EmployeeContributionRate <- .1
EmployerContributionRate <- .25

## (DYNAMIC) COLA
COLA_c <- PPD$cola


## (COMBO) Growth rate of the population to determine hiring increases. Is a constant now but could become a Vector
PopulationGrowth <- 0.01




##

#The max age of a retired employee
RetirementMax <- 104


#Start age and oldest employee age
EmployeeStart <- 20
EmployeeEnd <- 74

ServiceStart <- 1
ServiceEnd <- 55

#Percent of Population that is male
pctmale <- PPD$pctmale
## (STATIC) Nominal expected returns for stocks, bonds
ExpRet <- c(0.075, rf)

## (STATIC)Standard deviations (volatility) for stocks, bonds
# SD <- c(0.20)
SD <- c(0)

## (STATIC) How much to scale cash-flows by to match CAFR
scaling <- 1

## (STATIC): Mortality Adjustment
# If the simulated number of deaths  differs from whats observed in the plan history
# Active employees die less mortality rate predicts. This might be because upon sickness they choose
# to leave and get refund or retire early?
MortAdujst <- 1

## (STATIC) Number of asset classes (stocks,bonds)
Nasset <- 2

###########################################
######### TIER SPECIFIC VARIABLES #########
###########################################

## THESE ARE DIFFERENT FOR EACH TIER AND WILL EITHER BE DYNAMIC OR COMBO VARIABLES
## WILL NEED TO INCORPORATE MORE TIERS AS NEEDED

## Tier 1 ##

## The factor used to calculate benefits
BenefitFactor_t1 <- tier_info2$benefitfactor[[1]]

## How many years of past are put into average for benefit calculation
WageYears_t1 <- tier_info2$yrsal[[1]]

## (DYNAMIC) COLA
COLA_t1 <- tier_info2$cola[[1]]

## (DYNAMIC) A cap on the replacement rate achievable by an employee
BenefitCap_t1 <- ifelse(tier_info2$maxsal[[1]]==-100,100,tier_info2$maxsal[[1]])

## (DYNAMIC) Number of years of service to get full benefit treatment
NyearFullBenefit_t1 <- tier_info2$vesting[[1]]

RetirementStart_t1 <- tier_info2$nr[[1]]


## Tier 2 ##

## The factor used to calculate benefits
BenefitFactor_t2 <- tier_info2$benefitfactor[[2]]

## How many years of past are put into average for benefit calculation
WageYears_t2 <- tier_info2$yrsal[[2]]

## (DYNAMIC) COLA
COLA_t2 <- tier_info2$cola[[2]]

## (DYNAMIC) A cap on the replacement rate achievable by an employee
BenefitCap_t2 <- ifelse(tier_info2$maxsal[[2]]==-100,100,tier_info2$maxsal[[2]])

## (DYNAMIC) Number of years of service to get full benefit treatment
NyearFullBenefit_t2 <- tier_info2$vesting[[2]]

RetirementStart_t2 <- tier_info2$nr[[2]]

## Tier 3 ##

## The factor used to calculate benefits
BenefitFactor_t3 <- tier_info2$benefitfactor[[3]]

## How many years of past are put into average for benefit calculation
WageYears_t3 <- tier_info2$yrsal[[3]]

## (DYNAMIC) COLA
COLA_t3 <- tier_info2$cola[[3]]

## (DYNAMIC) A cap on the replacement rate achievable by an employee
BenefitCap_t3 <- ifelse(tier_info2$maxsal[[3]]==-100,100,tier_info2$maxsal[[3]])

## (DYNAMIC) Number of years of service to get full benefit treatment
NyearFullBenefit_t3 <- tier_info2$vesting[[3]]

RetirementStart_t3 <- tier_info2$nr[[3]]




## Tier 4 ##

## The factor used to calculate benefits
BenefitFactor_t4 <- tier_info2$benefitfactor[[4]]

## How many years of past are put into average for benefit calculation
WageYears_t4 <- tier_info2$yrsal[[4]]

## (DYNAMIC) COLA
COLA_t4 <- tier_info2$cola[[4]]

## (DYNAMIC) A cap on the replacement rate achievable by an employee
BenefitCap_t4 <- ifelse(tier_info2$maxsal[[4]]==-100,100,tier_info2$maxsal[[4]])

## (DYNAMIC) Number of years of service to get full benefit treatment
NyearFullBenefit_t4 <- tier_info2$vesting[[4]]

RetirementStart_t4 <- tier_info2$nr[[4]]


## Tier 5 ##

## The factor used to calculate benefits
BenefitFactor_t5 <- tier_info2$benefitfactor[[5]]

## How many years of past are put into average for benefit calculation
WageYears_t5 <- tier_info2$yrsal[[5]]

## (DYNAMIC) COLA
COLA_t5 <- tier_info2$cola[[5]]

## (DYNAMIC) A cap on the replacement rate achievable by an employee
BenefitCap_t5 <- ifelse(tier_info2$maxsal[[5]]==-100,100,tier_info2$maxsal[[5]])

## (DYNAMIC) Number of years of service to get full benefit treatment
NyearFullBenefit_t5 <- tier_info2$vesting[[5]]

RetirementStart_t5 <- tier_info2$nr[[5]]


## Tier 6 ##

## The factor used to calculate benefits
BenefitFactor_t6 <- tier_info2$benefitfactor[[6]]

## How many years of past are put into average for benefit calculation
WageYears_t6 <- tier_info2$yrsal[[6]]

## (DYNAMIC) COLA
COLA_t6 <- tier_info2$cola[[6]]

## (DYNAMIC) A cap on the replacement rate achievable by an employee
BenefitCap_t6 <- ifelse(tier_info2$maxsal[[6]]==-100,100,tier_info2$maxsal[[6]])

## (DYNAMIC) Number of years of service to get full benefit treatment
NyearFullBenefit_t6 <- tier_info2$vesting[[6]]

RetirementStart_t6 <- tier_info2$nr[[6]]



#list tables in database

#Sheets are 
#1 ageservice
#2 retdist
#3 wagerel
#4 mortality
#5 wagegrowth
#6 withdrawal
#7 retirement
#8 refund
#9 disability (Code doesn't currently use fund reported disability)



#Which sheets are available in the dataset and which ones need a default value
availableData <- c(T,T,T,T,T,T,T,F,F)



####################Get ASY active employee data####################

if(availableData[[1]]){
asy_employee <- as.matrix(read_excel(paste0(planFolder,fileName),
                                sheet = "ageservice", range = "B2:L12",col_names = F))*planinfo$actives_tot

}else{
  asy_employee <- as.matrix(read_excel("Common_Data/default_assumptions.xlsx",
                                            sheet = "ageservice", range = "B2:L12",col_names = F))*
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
                                       sheet = "wagerel", range = "B2:L12",col_names = F))*
    planinfo$ActiveSalary_avg*1000
  
}else{
  asy_wage <- as.matrix(read_excel("Common_Data/default_assumptions.xlsx",
                                       sheet = "wagerel", range = "B2:L12",col_names = F))*
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
                                   sheet = "retirement", range = "Q2:AA12",col_names = F))/100
  
}else{
  
  #TO DO: There is no default retirement matrix yet because Brookings assumes constant rates
  asy_retrate <- as.matrix(read_excel("Common_Data/default_assumptions.xlsx",
                                 sheet = "retirement", range = "B2:L12",col_names = F))/100
}


RetirementRate <- ConstantFill(asy_retrate,enforce_service_limit=F)



#################### Get Refund Rate Data ####################

if(availableData[[8]]){
  asy_refundrate <- as.matrix(read_excel(paste0(planFolder,fileName),
                                      sheet = "refund", range = "B2:L12",col_names = F))*pctmale+
    as.matrix(read_excel(paste0(planFolder,fileName),
                         sheet = "refund", range = "O2:Y12",col_names = F))*(1-pctmale)
  
}else{
  
  
  asy_refundrate <- as.matrix(read_excel("Common_Data/default_assumptions.xlsx",
                                      sheet = "refund", range = "B2:L12",col_names = F))
}





RefundRate <- ConstantFill(asy_refundrate)



#################### Get Seperation Rate Data ####################
if(availableData[[6]]){
  asy_seprate <- as.matrix(read_excel(paste0(planFolder,fileName),
                                         sheet = "withdrawal", range = "A1:L12",col_names = F))*pctmale/100+
    as.matrix(read_excel(paste0(planFolder,fileName),
                         sheet = "withdrawal", range = "N1:Y12",col_names = F))*(1-pctmale)/100
  
  asy_seprate[1:12,1] <-  asy_seprate[1:12,1] *100
  
  asy_seprate[1,2:12] <-  asy_seprate[1,2:12] * 100
  
}else{
  
  
  asy_seprate <- as.matrix(read_excel("Common_Data/default_assumptions.xlsx",
                                         sheet = "withdrawal", range = "A1:L12",col_names = F))

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

  mort_table <- rbind(read_excel("Common_Data/default_assumptions.xlsx",
                                 sheet = "mortality", range = "B2:D6",col_names = T),
                      read_excel("Common_Data/default_assumptions.xlsx",
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
  
  
  ret_num <- read_excel("Common_Data/default_assumptions.xlsx",
                        sheet = "retdist", range = "B1:B17",col_names = T)*planinfo$beneficiaries_tot
  
  ret_ben <- read_excel("Common_Data/default_assumptions.xlsx",
                        sheet = "retdist", range = "F1:F17",col_names = T)*planinfo$BeneficiaryBenefit_avg*1000
  
}




#Slope is negative because there should be less people as age increases
RetirementNumber <- LinearFill(ret_num,Slope=-1,retirement=T)

RetirementBenefit <- ConstantFill(ret_ben,retirement=T)


#break down active into their own tiers 

active_t1<- active

active_t1[,-c((tier_serivce[2]+1):55)] <- 0


active_t2<- active

active_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <- 0


active_t3<- active

active_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <- 0




active_t4<- active

active_t4[,-c((tier_serivce[5]+1):tier_serivce[4])] <- 0


active_t5<- active

active_t5[,-c((tier_serivce[6]+1):tier_serivce[5])] <- 0


active_t6<- active

active_t6[,-c(1:tier_serivce[6])] <- 0


#Calculate the inactive matrix number assuming a given tier retirement start and vesting period
inactive <-Calc_Inactive(active, SeparationRate, RefundRate,
                         MortalityTable,RetirementStart_t1,NyearFullBenefit_t1)


inactive <- inactive * PPD$inactive



#break down inactive into their own tiers 

inactive_t1<- inactive

inactive_t1[,-c((tier_serivce[2]+1):55)] <- 0


inactive_t2<- inactive

inactive_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <- 0


inactive_t3<- inactive

inactive_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <- 0




inactive_t4<- inactive

inactive_t4[,-c((tier_serivce[5]+1):tier_serivce[4])] <- 0


inactive_t5<- inactive

inactive_t5[,-c((tier_serivce[6]+1):tier_serivce[5])] <- 0


inactive_t6<- inactive

inactive_t6[,-c(1:tier_serivce[6])] <- 0


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

MainRes_Tier1 <- Main_Current(active_t1,inactive_t1,COLA_t1,WageYears_t1,BenefitCap_t1,
                              BenefitFactor_t1,RetirementStart_t1,NyearFullBenefit_t1,CurrentTier=F)

MainRes_Tier2 <- Main_Current(active_t2,inactive_t2,COLA_t2,WageYears_t2,BenefitCap_t2,
                              BenefitFactor_t2,RetirementStart_t2,NyearFullBenefit_t2,CurrentTier=F)

MainRes_Tier3 <- Main_Current(active_t3,inactive_t3,COLA_t3,WageYears_t3,BenefitCap_t3,
                              BenefitFactor_t3,RetirementStart_t3,NyearFullBenefit_t3,CurrentTier=F)


MainRes_Tier4 <- Main_Current(active_t4,inactive_t4,COLA_t4,WageYears_t4,BenefitCap_t4,
                              BenefitFactor_t4,RetirementStart_t4,NyearFullBenefit_t4,CurrentTier=F)

MainRes_Tier5 <- Main_Current(active_t5,inactive_t5,COLA_t5,WageYears_t5,BenefitCap_t5,
                              BenefitFactor_t5,RetirementStart_t5,NyearFullBenefit_t5,CurrentTier=F)


MainRes_Tier6 <- Main_Current(active_t6,inactive_t6,COLA_t6,WageYears_t6,BenefitCap_t6,
                              BenefitFactor_t6,RetirementStart_t6,NyearFullBenefit_t6,CurrentTier=T)


proc.time() - ptm

RetRes <- Main_Ret(RetirementNumber,RetirementBenefit)


#Sum Cash Flows
main_cf <- MainRes_Tier1[[2]]  + MainRes_Tier2[[2]] + MainRes_Tier3[[2]] + MainRes_Tier4[[2]] +
  MainRes_Tier5[[2]]++ MainRes_Tier6[[2]]  

ret_cf <- RetRes[[2]]

cash_outflows <- main_cf+ret_cf

cash_inflows <- MainRes_Tier1[[3]]  + MainRes_Tier2[[3]]+ MainRes_Tier3[[3]]+ MainRes_Tier4[[3]]+
  MainRes_Tier5[[3]]++ MainRes_Tier6[[3]]


#
#COMPARE OUTPUT
#

#Liabilities
# This is the acturial accrued liabilities
# The first row in this data frame should match what is reported in the CAFR
AAL <- MainRes_Tier1[[1]]+MainRes_Tier2[[1]]+RetRes[[1]]+MainRes_Tier3[[1]]+MainRes_Tier4[[1]]
+MainRes_Tier5[[1]]+MainRes_Tier6[[1]]


Model_AAL <- AAL[1,1]

CAFR_AAL <- planinfo$ActLiabilities_GASB*1000 # get actual value from CAFR

#compute difference
Percent_difference <- (Model_AAL-CAFR_AAL)/CAFR_AAL


#Sum the 6 tiers of PVFB and then the retirement PVFB
model_PVFB <- sum(MainRes_Tier1[[4]][1,])+sum(MainRes_Tier2[[4]][1,])+sum(MainRes_Tier3[[4]][1,])+
  sum(MainRes_Tier4[[4]][1,])+sum(MainRes_Tier5[[4]][1,])+sum(MainRes_Tier6[[4]][1,])++RetRes[[1]][1,1]


#get PVFB from cafr
cafr_PVFB <- PPD$PVFB*1000

#compute difference
dif_PVFB <- (model_PVFB-cafr_PVFB)/cafr_PVFB


#Sum the 6 tiers of inactive employees
inactive_model <- sum(MainRes_Tier1[[4]][1,2])+ sum(MainRes_Tier2[[4]][1,2])+ sum(MainRes_Tier3[[4]][1,2])+
  sum(MainRes_Tier4[[4]][1,2])+ sum(MainRes_Tier5[[4]][1,2])+ sum(MainRes_Tier6[[4]][1,2])


#get inactive from cafr
inactive_cafr <- PPD$inact_liability*1000

#compute difference
dif_inactive <- (inactive_model-inactive_cafr)/inactive_cafr



#get retirement from model
ret_model <- RetRes[[1]][1,1]

#get retirement from cafr
ret_cafr <- PPD$ret_liability*1000

#compute difference
dif_ret <- (ret_model-ret_cafr)/ret_cafr

Compare_Result <- data.frame(type=character(),model=numeric(),cafr=numeric(),dif=numeric(),stringsAsFactors = F)


Compare_Result[1,1] <- "EAN"
Compare_Result[1,2] <- Model_AAL
Compare_Result[1,3] <- CAFR_AAL
Compare_Result[1,4] <- Percent_difference


Compare_Result[2,1] <- "PVFB"
Compare_Result[2,2] <- model_PVFB
Compare_Result[2,3] <- cafr_PVFB
Compare_Result[2,4] <- dif_PVFB


Compare_Result[3,1] <- "Retirement"
Compare_Result[3,2] <- ret_model
Compare_Result[3,3] <- ret_cafr
Compare_Result[3,4] <- dif_ret


Compare_Result[4,1] <- "Inactive"
Compare_Result[4,2] <- inactive_model
Compare_Result[4,3] <- inactive_cafr
Compare_Result[4,4] <- dif_inactive

save.image(file = "NY78/NY78_Compare_latest.RData")



#############################################################################
#############################################################################
# Loop Through Asset Pool With simulated Cashflows
#############################################################################
#############################################################################


# Start of Monte Carlo Loop
for (n in 1:NMonte) {
  for (t in 1:(Nyear-1)) {
    
    
    # Generate current year's returns ------------------------------
    normal_shock <- rnorm(1,mean=ExpRet[[1]],sd=SD[[1]])
    
    returns <- c(normal_shock,ExpRet[2])
    
    
    
    
    AnnualRet <- 0
    ret <- c(Nasset)
    for (i in 1:Nasset) {
      ret[i] <- returns[i]
      AnnualRet <- AnnualRet + AssetShare[i] * ret[i]
    }
    
    
    Assets[t+1,n] <- Assets[t,n]*(1+AnnualRet)-cash_outflows[t,n]+cash_inflows[t,n]
    
    
    
  }
  
  
}








