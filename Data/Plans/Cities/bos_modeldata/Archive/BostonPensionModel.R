#location of the LinearFilll.R, ConstantFil.R and Chicago_Pseudo.xlsx 
setwd("/home/dan/golub/NCF/")


#read excel spreadsheets
library("readxl")

ptm <- proc.time()

#LinearFill fills out a bucket matrix using a linear function 
source('ModelCode/LinearFill.R')
#LinearFill fills out a bucket matrix using the constant amount in each bucket
source('ModelCode/ConstantFill.R')
source('ModelCode/PensionModel_Liability.R')
source('ModelCode/PensionModel_PVNC.R')

DataLocation <- "BostonModelCode/BostonData2.xlsx"


## Input simulation parameters 
Nyear <- 10  ## Choose the number of years to simulate

NMonte <- 10  ## Choose the number of simulations to run for simulation

## Input plan return and reserve fund parameters 

AssetShareStocks <- .6 ## Choose a multiple for capping reserve (e.g. 1 means capping reserve at 1 year's floor payment)
AssetShareBonds <- 1-AssetShareStocks  ## Choose the proportion of assets you want to be bonds



########  OTHER PARAMETERS  ########


Tiers <- 2 #number of plan tiers 

TierYears <- c(2011) #years of tier splits

TierVest <- c(10,10) #Vesting Years by tier

CurrentYear <- 2020 #Starting Year

BenefitFactor <- .025 #The factor used to calculate benefits

AgeMinStartWork <- 20  # Youngest age of new workers at beginning of first work year

RetirementStart <- 50  #The earliest age people can retire

NyearFullBenefit <- 10  # Number of years of service to get full benefit treatment



#Mortality Adjustment
#If the simulated number of deaths  differs from whats observed in the plan history
#Active employees die less mortality rate predicts. This might be because upon sickness they choose
#to leave and get refund or retire early?
MortAdujst <- 1

#COLA
COLA <- .03

#Chicago calculates their yearly disability payout as a percent of payroll
DisabilityPayoutRate <- .075


#These were backed out from looking at contributions from the AR report
EmployeeContributionRate <- .1

EmployerContributionRate <- .25

Nasset <- 2  # Number of asset classes (stocks, bonds)
rf <- 0.025  # Nominal risk-free rate
refundRate <- .025 #the amount of interest that gets accumulated for refunds.
Inflation <- 0.02 # Inflation rate
annuity_df <- 0.04 # discount factor for annuity
discountrate <- .0715 #how much to discount liabilities

# Fixed plan parameters

WageYears <- 5 #how many years of past are put into average for benefit calculation

BenefitCap <- .8 # A cap on the replacement rate achievable by an employee 

PopulationGrowth <- 0.03  #Growth rate of the population to determine hiring increases.
#Is a constant now but could become a Vector


# Fixed investment parameters
ExpRet <- c(0.075, rf)  # Nominal expected returns for stocks, bonds
SD <- c(0.20)  # Standard deviations (volatility) for stocks, bonds

AssetShare <- c(AssetShareStocks, AssetShareBonds)


#### Wage Growth ### 
WageGrth <- as.data.frame(read_excel(DataLocation, sheet = "Wage_Growth"))

#What are the start and end of each bucket?
WageGrthServiceMinMax <- data.frame(AgeMin=c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21),
                                    AgeMax=c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,40))

#Fill out the matrix
WageGrth <- ConstantFill(WageGrth,RowBoundaries = WageGrthServiceMinMax )



#Create a matrix with the age/ service  min / max.
#These matrices are used as input into fucntions to expand bucketed matrices
MemberAgeMinMax <- data.frame(AgeMin=c(20,25,30,35,40,45,50,55,60,65,70),
                              AgeMax=c(24,29,34,39,44,49,54,59,64,69,74)
)


MemberServiceMinMax <- data.frame(ServiceMin=c(1,5,10,15,20,25,30,35,40),
                                  ServiceMax= c(4,9,14,19,24,29,34,39,45)
)



#### Wages ### 

#Import Collapsed Wages
CollapasedWage <-as.data.frame(read_excel(DataLocation, sheet = "Age_Serv_Wage", col_names=TRUE))

#Uncollapse Wages
BaseWage <- ConstantFill(CollapasedWage , RowBoundaries=MemberAgeMinMax, ColumnBoundaries=MemberServiceMinMax)

#Create a 3d matrix 
BaseWage <- array(BaseWage, c(dim(BaseWage), Nyear));  

BaseWage[,,2:Nyear] <- 0


#No Longer need the orginal Collapsed Wages
rm(CollapasedWage)


### Number of Active members ### 

#Import Collapsed Active age service matrix
CollapasedAct <-as.data.frame(read_excel(DataLocation, sheet = "Age_Serv_Num", col_names=TRUE))

#Expand Collapsed Active Age Service Matrix
ActiveNumber <- LinearFill(CollapasedAct , RowBoundaries=MemberAgeMinMax,
                           ColumnBoundaries=MemberServiceMinMax,Slope=2)

ActiveNumber <- array(ActiveNumber, c(dim(ActiveNumber), Nyear));  

ActiveNumber[,,2:Nyear] <- 0


#No Longer need the orginal collapsed matrix
rm(CollapasedAct)


### Number of Inactive Members ### 

#Import collapsed inactive age service matrix
CollapasedInact <-as.data.frame(read_excel(DataLocation, sheet = "Inactv_Serv_Num", col_names=TRUE))


#Expand Collapsed Active Age Service Matrix
InactiveNumber <- LinearFill(CollapasedInact , RowBoundaries=MemberAgeMinMax, 
                             ColumnBoundaries=MemberServiceMinMax,Slope=2)

InactiveNumber <- array(InactiveNumber, c(dim(InactiveNumber), Nyear))


InactiveNumber[,,2:Nyear] <- 0

#Inactive matrix keeps track of vested members
#remove unvested members
InactiveNumber[,1:(NyearFullBenefit-1),1] <- 0




#No Longer need the orginal collapsed matrix
rm(CollapasedInact)


### Inactive Benfits ### 

# Initalize the inactive benefits matrix 
# Assume that the inactive benefits matrix is based off of 
# current year salaires

InactiveBenefits <- array(0, dim(InactiveNumber))

for (i in (1:dim(InactiveNumber)[1])){
  
  for (j in (1:dim(InactiveNumber)[2])){
    
    if(InactiveNumber[i,j,1] == 0){
      
      InactiveBenefits[i,j,1] <- 0 
      
    }else{
      
      InactiveBenefits[i,j,1] <- BaseWage[i,j,1] * min(BenefitFactor*j,BenefitCap)
      
    }
    
  }
  
} 



### Retirement Data ###

#Create a matrix with the age min / max.
#These matrices are used as input into fucntions to expand bucketed matrices
RetirementAgeMinMax <- data.frame(AgeMin=c(50,55,60,65,70,75,80,85,90,95,100),
                                  AgeMax=c(54,59,64,69,74,79,84,89,94,99,104)
)


RetirementData <-as.data.frame(read_excel(DataLocation, sheet = "Retirement", col_names=TRUE))

#Slope is negative because there should be less people as age increases
RetirementNumber <- LinearFill(RetirementData[,c(1:2)]  , RowBoundaries=RetirementAgeMinMax,Slope=-2)

RetirementBenefit <- ConstantFill(RetirementData[,c(1,3)], RowBoundaries=RetirementAgeMinMax)


#Adjust for Tiers
#all retired chicago members are in the same tier 

RetirementNumber <- cbind(RetirementNumber,0)
RetirementBenefit <- cbind(RetirementBenefit,0)

#Create 3d matix
RetirementNumber <- array(RetirementNumber, c(dim(RetirementNumber), Nyear))
RetirementNumber[,,2:Nyear] <- 0


RetirementBenefit <- array(RetirementBenefit, c(dim(RetirementBenefit), Nyear))
RetirementBenefit[,,2:Nyear] <- 0


#Retirement Rate 

#Create a matrix with the age min / max.
#These matrices are used as input into fucntions to expand bucketed matrices
RetirementRateAgeMinMax <- data.frame(AgeMin=c(50:69,70),
                                      AgeMax=c(50:69,75))

RetirementRateServiceMinMax <- data.frame(ServiceMin=c(10,21),
                                          ServiceMax= c(20,45)
)


RetirementRate <-as.data.frame(read_excel(DataLocation, sheet = "Ret_Rate", col_names=TRUE))

#Because Chicago has their retirement rate in service/age matrix, the data needs to be 
#transposed to make it a age/service matrix to keep it consistant with other matrix
RetirementRate <- matrix(as.numeric(t(RetirementRate)[2:dim(t(RetirementRate))[1],]),ncol = dim(t(RetirementRate))[2],
                         nrow=dim(t(RetirementRate))[1]-1)

RetirementRate <- cbind(0,RetirementRate)


RetirementRate <- ConstantFill(RetirementRate,RowBoundaries = RetirementRateAgeMinMax,
                               ColumnBoundaries = RetirementRateServiceMinMax,AgeService=FALSE)




## Seperation Rate ##

SeperationServiceMinMax <- data.frame(ServiceMin=c(1:9,10),
                                      ServiceMax= c(1:9,45)
)

SeperationAgeMinMax <- data.frame(AgeMin=c(20,30,40,50),
                                  AgeMax= c(29,39,49,74)
)


SeparationRate <-as.data.frame(read_excel(DataLocation, sheet = "Sep_Rate", col_names=TRUE))

SeparationRate<- ConstantFill(SeparationRate , RowBoundaries = SeperationAgeMinMax,
                              ColumnBoundaries =  SeperationServiceMinMax)


#################


## Refund Rate ##

#Create a matrix with the age min / max.
#These matrices are used as input into fucntions to expand bucketed matrices
RefundRateAgeMinMax <- data.frame(AgeMin=c(20,25,30,35,40,45,50,55,60,65,70),
                                  AgeMax=c(24,29,34,39,44,49,54,59,64,69,74))

RefundRateServiceMinMax <- data.frame(ServiceMin=c(1,5,10,15,20,25,30,35),
                                      ServiceMax=c(4,9,14,19,24,29,34,45))


RefundRate <-as.data.frame(read_excel(DataLocation, sheet = "Refund_Rate", col_names=TRUE))

#Remove last few columns that are all zero
RefundRate <- RefundRate[,-c(10:12)]



RefundRate <- ConstantFill(RefundRate , RowBoundaries = RefundRateAgeMinMax,
                           ColumnBoundaries =  RefundRateServiceMinMax)



## Mortality Table 

MortalityTable <-as.data.frame(read_excel(DataLocation, sheet = "Avg_Mort", col_names=TRUE))


MortalityTable[,2] <- MortalityTable[,2]* MortAdujst


#Annuity Amounts. Used in Death Pay

AnnuityVector <- vector(length= dim(ActiveNumber)[1])

for (i in c(1:ActiveNumber[1])){
  
  liveProb <- 1
  
  curage <- i
  
  #Get Annuity Factor for given Age
  annuityFactor<- 0
  
  for(m in curage:dim(MortalityTable)[1]){
    
    #probability of living from year current age to age m
    liveProb <- (1-MortalityTable[m,2])*liveProb
    
    #From Sheiner et al. 
    annuityFactor <- annuityFactor + liveProb*
      (1/(1+annuity_df))^(m-curage)*(1+COLA)^(m-curage)
    
    
  }
  
  AnnuityVector[i] <- annuityFactor
  
  
  
}


############# Simulation Functions #####################

# PastWages function
#This function will return a vector of past wages of length period
#This will be used in benefit calculations 
PastWages <- function(Wage,age,service,years,period){
  
  wageVec<-vector(length = period)
  
  indexer<- 1
  
  for(i in ((age-period+1):age)){
    
    
    
    wageVec[indexer] <- Wage[i,(service-period+indexer),(years-period+indexer)]
    
    
    indexer <- indexer+1
    
    
    
  }
  
  
  return(wageVec) 
  
  
}






#calculate the amount refunded each year
Refund <-function( Employees, SepRate, RefRate, Wage,year){
  
  NumRefund <- Employees*SepRate*RefRate
  
  AmountRefund <- 0
  
  for (i in (1:dim(Employees)[1])){
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    
    for (j in 1:min(c(i,dim(Employees)[2]-1))){
      
      if(NumRefund[i,j]>0){
        
        if(year<j){
          
          #If we don't know their previous years salary assume its constant
          #Return the Risk free rate of all their contributions 
          
          
          TempRefund <- Wage[i,j,year]*EmployeeContributionRate* sum((1+refundRate)^seq(j))
          
          
          AmountRefund <- AmountRefund + TempRefund* NumRefund[i,j]
          
        }else{
          
          #Have to loop through each year because wages are different
          #Return the Risk free rate of all their contributions 
          
          
          TempRefund <- sum(PastWages(Wage,age=i,service = j,year,j) *EmployeeContributionRate*(1+refundRate)^seq(j))
          
          
          AmountRefund <- AmountRefund+ TempRefund* NumRefund[i,j]
          
        }
        
      }
    }
    
  } 
  
  AmountRefund  
  
  
}

#If an employee dies, pay out an annuity based off their years of service and current
#salary. If an inactive memeber dies, pay out an annuity based on their accured benefits
DeathPay <- function(Employees,Inactive,InactiveBen,Wage,MortTable){
  
  DeathTotal <- 0
  
  
  for (i in c(1:dim(Employees)[1])) {
    
    Mort <- MortTable[i,2]
    
    Annuity <- AnnuityVector[i]
    
    for (j in c(1:dim(Employees)[2])){
      
      DeathTotal <- DeathTotal + Employees[i,j]*Mort*Annuity*min(BenefitFactor*j,BenefitCap)*Wage[i,j]+
        Inactive[i,j]*Mort*Annuity*InactiveBen[i,j]
      
      
    }
    
  }
  DeathTotal
  
}


# UpdateEmployeeCount is a function.
#What this function does is age the current workforce by 1 year.
#Removing the retirees, separators and people who have died.
#Then it adds employees to the workforce to make the number of employees equal
#TotalEmployees from above. The new employees are added assuming that the age 
#distribution and relative salaries of new hires match the distribution of current 
#employees with fewer than 3 years of service.
# As inputs the function takes the current number of employees,
#separation rates, retirement rates, a mortality table and the new number of total #employees.


UpdateEmployeeCount <- function(Employees,SepRate,RetRate,MortTable,TotalEmployees,year){
  
  
  retirementAgeIndex <- RetirementStart-AgeMinStartWork
  
  retirementServiceIndex <- min(RetirementRateServiceMinMax)
  
  for (i in 1:(dim(Employees)[1]-1)){
    
    
    Mort <-  MortTable[i,2] 
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in 1:min(c(i,dim(Employees)[2]-1))) {
      
      
      ProbSeparate <-  Mort + SepRate[i,j] 
      
      #Add retirement seperation probability if they are the right age
      if(i>=retirementAgeIndex& j >= retirementServiceIndex) {
        
        ProbSeparate <- ProbSeparate + RetirementRate[(i-retirementAgeIndex+1),
                                                      (j- retirementServiceIndex+1)]
        
      }
      
      Employees[i + 1, j+1, year + 1] <- Employees[i, j, year] * (1 - ProbSeparate) 
      
    }
    
    
  }
  
  #create a distribution based on how many employees each group lost
  CalibrateMatrix <- (Employees[,1:3,year]-Employees[,1:3 , year + 1])
  
  #remove values less than 0
  CalibrateMatrix[CalibrateMatrix<0] <- 0
  
  
  #Fewer than 3 years distibution 
  Employees[,1:3 , year + 1] <- Employees[,1:3 , year + 1]+ 
    (CalibrateMatrix)/sum(CalibrateMatrix)*(TotalEmployees-sum(Employees[, , year + 1]))    
  
  
  return(Employees[,,year+1])
  
  
  
}

# Update the number of Inactive employees and the benefits they are owed.
# The function UpdateInactiveCount ages the current inactive works by 1 year.  
# Like Sheiner, function assume that inactive workers take benefits as soon as they are 
#eligible. Add the new separators and subtract the inactive participants that have died.
# This function takes as input the current number of employees, separation rates, and the mortality table 
UpdateInactiveCount <- function(Employees, Inactive,SepRate,RefRate,MortTable,year){
  
  
  
  #Age everyone in the inactive matrix
  Inactive[2:(dim(Inactive)[1]),, year + 1] <- Inactive[1:(dim(Inactive)[1]-1), , year ]
  
  #Probability of seperating and not taking refund 
  ProbSepNoRef <- SepRate*(1-RefRate)
  
  
  for (i in (NyearFullBenefit+1):(dim(Employees)[1])){
    
    #get mortality rate
    DeathRate <-  MortTable[i,2] 
    
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]-1))) {
      
      #Remove people that die from the number count 
      
      Inactive[i, j, year + 1] <- Inactive[i, j, year + 1] - (Inactive[i-1, j, year ] * (DeathRate))
      
      
      #Add employees that seperate  
      ProbSeparate <- ProbSepNoRef[i,j]
      Inactive[i, j, year + 1] <- Inactive[i, j, year + 1] +  (Employees[i, j, year] * (ProbSeparate))
      
    }
  }
  
  
  
  
  return(Inactive[,, year + 1])
  
  
  
  
}


# The function UpdateInactiveBenefits updates the average benefits to be received by 
# the inactive workers. To update the average the function will 
# need the total benefits currently expected to be received plus the new additions to benefits.

# NOTE: The benefit factor may be different based on plan tier. Based on the current year and 
# serivce years you may need to add if statements to break them out into different tiers

UpdateInactiveBenefits <- function(Inactive,Employees,Wage,InactiveBen,SepRate,year){
  
  # To adjust the average benefits, we need to know what the total benefits were. 
  # Get the total benefits, TotalRetirmentBenefits is a temporary matrix to store total benefits
  TotalBenefits <- Inactive[,,(year:(year+1))]  * InactiveBen[,,(year:(year+1))]
  
  # Move the total Benfits forward a year
  # Now assumes that no growth is added to accrued benefits
  # Could add the risk-free interest rate growth to benefits?
  TotalBenefits[2:(dim(TotalBenefits)[1]),, 2] <- TotalBenefits[1:(dim(TotalBenefits)[1]-1), , 1 ]
  
  
  for (i in (NyearFullBenefit+1):(dim(Employees)[1])){
    
    
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]-1))) {
      
      
      #Add employees that seperate  
      ProbSeparate <- SepRate[i,j]
      
      NewSep <-  (Employees[i, j, year] * (ProbSeparate) )
      
      
      if(year<WageYears){
        
        #If we don't know their previous years salary assume its constant
        NewBenefit <- min(BenefitFactor*j,BenefitCap)*Wage[i,j,year]*NewSep
        
      }else{
        
        #If we know the past years ages we can calculate the average
        NewBenefit <- min(BenefitFactor*j,BenefitCap)*mean(PastWages(Wage,i,j,year,WageYears))*NewSep
        
      }
      
      TotalBenefits[i,j, 2] <-  TotalBenefits[i,j, 2]+NewBenefit
      
      
    }
  }
  
  
  
  #End up dividing by 0 so remove NaN
  result <- TotalBenefits[,, 2] /Inactive [,,year+1]
  result[is.nan(result)] <- 0
  
  return(result) 
  
  
}

# the function UpdateRetirementNumber ages the retirement group by 1 year. 
# It subtracts those that die and adds those who enter retirement.

# NOTE: The retirement matrix is sperated by tiers. Based on the current year and 
# serivce years you may need to add if statements to break them out into different tiers
UpdateRetirementNumber <- function(Retirement,Employees, Inactive,RetRate,MortTable,year){
  
  #Tier
  #For this draft 1 tier is used
  Tier <- 1
  
  #Index number for mortality table
  MortIndex <- RetirementStart-AgeMinStartWork+1
  
  #Get the mortality rates 
  DeathRate <-  MortTable[(MortIndex:(dim(Retirement)[1]+MortIndex-1)),2] 
  
  #Age everyone in the retirement matrix. Keep only those that survive
  #Subtract out the benefits from the people that were lost. 
  #Use Rauh’s assumption that 60% of the population is married and to a spouse of the same age
  
  Retirement[,,year] <- Retirement[,,year] - (Retirement[,,year]*DeathRate*.4) 
  
  #Age everyone in the retirement matrix. Keep only those that survive
  Retirement[2:(dim(Retirement)[1]),Tier, year + 1] <- Retirement[1:(dim(Retirement)[1]-1), Tier, year ]
  
  for (i in (RetirementStart-AgeMinStartWork):(dim(Employees)[1])){
    
    #Count new retirees
    NewRetire <- 0
    
    #Sets the row index for certain matrices
    rowIndex <- (i-(RetirementStart-AgeMinStartWork)+1)
    
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]-1))) {
      
      
      #Sets the column index for certain matrices
      colIndex <- (j-NyearFullBenefit+1) 
      
      #Add employees that retire  
      ProbRetirement<- RetRate[rowIndex,colIndex]
      
      
      NewRetire <- NewRetire+  (Employees[i, j, year] * (ProbRetirement)) + (Inactive[i,j,year]*ProbRetirement)
      
    }
    
    Retirement[rowIndex,Tier, year + 1] <- Retirement[rowIndex,Tier, year + 1] + NewRetire
    
  }
  
  return(Retirement[,, year + 1])
  
}

# the function UpdateRetirementBenefit updates the average benefits received by those in retirement.

UpdateRetirementBenefit <- function( RetBen , RetNum, Wage ,cola,
                                     MortTable, Inactive, InactiveBen , Employees,
                                     RetRate, BenFactor,year){
  
  #Tier
  #For this draft 1 tier is used
  Tier <- 1
  
  #To adjust the average benefits, we need to know what the total benefits were. 
  #Get the total benefits, TotalRetirmentBenefits is a temporary matrix to store total benefits
  TotalRetirmentBenefits <- RetBen[,,(year:(year+1))] * RetNum[,,(year:(year+1))]
  
  #Index number for mortality table
  MortIndex <- RetirementStart-AgeMinStartWork+1
  
  #Get the mortality rates 
  DeathRate <-  MortTable[(MortIndex:(dim(TotalRetirmentBenefits)[1]+MortIndex-1)),2] 
  
  #Age everyone in the retirement matrix. Keep only those that survive
  #Subtract out the benefits from the people that were lost. 
  #Use Rauh’s assumption that 60% of the population is married and to a spouse of the same age
  #and that the plan allows for 50% survivorship benefit
  
  TotalRetirmentBenefits[,,1] <- TotalRetirmentBenefits[,,1] - (TotalRetirmentBenefits[,,1]*DeathRate*.4)  -
    (TotalRetirmentBenefits[,,1]*DeathRate*.6*.5)
  
  
  #Define a variable for number of rows
  rowDim <- dim(TotalRetirmentBenefits)[1]
  
  #Move the Benefits forward a year
  #Adjust for cola
  TotalRetirmentBenefits[2:(rowDim),Tier, 2] <- TotalRetirmentBenefits[1:(rowDim-1), Tier, 1 ]*(1+cola)
  
  #Add the inactive employees that are now receiving benefits. 
  
  
  
  # Add the active employees that enter retirement
  
  #NOTE: The tier is not stored in the active employees’ matrices so if there’s more than 1 tier there needs to be
  # a series of if statements to check the tier
  for (i in (RetirementStart-AgeMinStartWork):(dim(Employees)[1])){
    
    #sum the new benefits
    NewBenefit <- 0
    
    #Sets the row index for certain matrices
    rowIndex <- (i-(RetirementStart-AgeMinStartWork)+1)
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]-1))) {
      
      #Sets the column index for certain matrices
      colIndex <- (j-NyearFullBenefit+1) 
      
      #Add employees that retire  
      ProbRetirement<- RetRate[rowIndex,colIndex]
      
      
      NewRetireActive <- (Employees[i, j, year] * (ProbRetirement))
      
      NewRetireInactive <- (Inactive[i,j,year] * (ProbRetirement))
      
      NewBenefit <-  NewBenefit+ NewRetireInactive*InactiveBen[i,j,year]
      
      if(year<WageYears){
        
        #If we don't know their previous years salary assume its constant
        NewBenefit <- NewBenefit + min(BenefitFactor*j,BenefitCap)*Wage[i,j,year]*NewRetireActive
        
      }else{
        
        #If we know the past years ages we can calculate the average
        NewBenefit <- NewBenefit + min(BenefitFactor*j,BenefitCap)*mean(PastWages(Wage,i,j,year,WageYears))*NewRetireActive
        
      }
      
      
      
      
    }
    
    
    TotalRetirmentBenefits[rowIndex,Tier,2]<-  TotalRetirmentBenefits[rowIndex,Tier, 2]+NewBenefit
    
    
  }
  
  
  # The new average benefit for each age-tier of retirement
  #End up dividing by 0 so remove NaN
  result <- TotalRetirmentBenefits[,,2]/RetNum[,,year+1]
  result[is.nan(result)] <- 0
  return(result)
}


# L_UpdateEmployeeCount is a function which updates employees lost but does not add new employees.
#L is for liability. This function is used in functions that calculate liabilities
#What this function does is age the current workforce by 1 year.
#Removing the retirees, separators and people who have died.
# As inputs the function takes the current number of employees,
#separation rates, retirement rates, a mortality table

L_UpdateEmployeeCount <- function(Employees,SepRate,RetRate,MortTable,year){
  
  
  retirementAgeIndex <- RetirementStart-AgeMinStartWork
  
  retirementServiceIndex <- min(RetirementRateServiceMinMax)
  
  for (i in 1:(dim(Employees)[1]-1)){
    
    
    Mort <-  MortTable[i,2] 
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in 1:min(c(i,dim(Employees)[2]-1))) {
      
      
      ProbSeparate <-  Mort + SepRate[i,j] 
      
      #Add retirement seperation probability if they are the right age
      if(i>=retirementAgeIndex& j >= retirementServiceIndex) {
        
        ProbSeparate <- ProbSeparate + RetirementRate[(i-retirementAgeIndex+1),
                                                      (j- retirementServiceIndex+1)]
        
      }
      
      Employees[i + 1, j+1, year + 1] <- Employees[i, j, year] * (1 - ProbSeparate) 
      
    }
    
    
  }
  
  return(Employees[,,year+1])
  
  
}










########  SET-UP AND SIMULATIONS  (no user input required) ########  

count1 <- 0 # Count the number of times the fund goes bankrupt

prob1 <- 0  # Setting up proportion of instances in which fund goes bankrupt

set.seed(54848631) # For replicability

Assets <- matrix(0,nrow = Nyear,ncol= NMonte)

Assets[1,] <- 1823646734

AAL <- matrix(0,nrow = Nyear,ncol= NMonte)

CashOutflow <- matrix(0,nrow = Nyear,ncol= NMonte)

PresentValueFutureBenefits <- matrix(0,nrow=Nyear,ncol=2)

PresentValueNormalCost <- matrix(0,nrow=Nyear,ncol=1)


###FOR TESTING
Tracker <- matrix(0,nrow = Nyear,ncol= NMonte)
TrackList <- list()
####

#Count the number of defaults
CountDefault <- 0 

# Only need to calculate the values used to calculate  present value of normal costs once
# This is a costly function to run and every year it is only increased by the inflation rate
# This function returns the two values needed to calculate present value of future normal cost
# The first value is present value of costs and the second is present value of future wages

PVNC_Values <- PVNC_Calc(ActiveNumber,InactiveNumber,
                         InactiveBenefits,RetirementNumber,
                         RetirementBenefit,BaseWage,80,1,discountrate)

# Start of Monte Carlo Loop 
for (n in 1:NMonte) {
  
  #wipe clean the matricies, except for the 1st year
  ActiveNumber[,,2:Nyear] <- 0
  InactiveNumber[,,2:Nyear] <- 0
  BaseWage[,,2:Nyear] <- 0
  InactiveBenefits[,,2:Nyear] <- 0
  RetirementNumber[,,2:Nyear] <- 0
  RetirementBenefit[,,2:Nyear] <- 0
  
  
  # Start of Time Loop ------------------------------
  for (t in 1:(Nyear-1)) {
    
    #Present Value of Future Benefits
    #This function doesnt change between simulations
    #If there is already a value in the matrix it doesn't need to be run again for that year
    #This first checks to see if the function needs to be run or if it has already been run in
    #another simulation
    if(sum(PresentValueFutureBenefits[t,]) == 0){
      
      PresentValueFutureBenefits[t,] <- TotalLiabilities(ActiveNumber,
                                                         InactiveNumber,InactiveBenefits,
                                                         RetirementNumber,RetirementBenefit,BaseWage,80,t,discountrate)
      
      
      
      
      
      PVFS <- PVNC_Values[[2]]*(1+Inflation)^(t-1)
      
      NCxs <- PVNC_Values[[1]]*(1+Inflation)^(t-1)
      
      PVNC <- 0
      
      
      for (i in (1:(dim(ActiveNumber)[1]))){
        
        
        #This min prevents unnecessary looping
        #Can't have more service than age allows
        for (j in  1:min(c(i,dim(ActiveNumber)[2]))) {
          
          
          PVNC <- PVNC + ActiveNumber[i,j,t]*NCxs[i]*PVFS[i,j]
          
          
        }
        
      }
      
      
      
      
      PresentValueNormalCost[t,1] <- PVNC
      
      
    }
    
    
    
    
    
    #Acturial Accrued Liability
    #Present Value Normal Cost is subtracted from Active Members PVFB then added with nonactive PVFB
    
    AAL[t,n] <-(PresentValueFutureBenefits[t,1]-PresentValueNormalCost[t,1])+ PresentValueFutureBenefits[t,2]
    
    
    #Calculate the amount refunded to separators.
    #Refund is a function which takes number of employees, the separation rate, 
    #refund rate and the average of the last few years salary to 
    #calculate the total sum give 
    #out to refunds this year 
    RefundAmount = Refund(ActiveNumber[,,t], SeparationRate, RefundRate,
                          BaseWage,t)
    
    
    
    #Calculate the amount paid out due to death during employment or inactive and not receiving benefits
    #DeathPay is a function which takes number of employees, mortality table, 
    #number of inactive workers,  the average benefits for inactive works 
    #and the average of the last few years salary to calculate the total sum paid out due to death
    #in the event of death their spouse/heir is assumed to recieve an annuity based on
    #current salary and years of service
    DeathAmount = DeathPay( ActiveNumber [,,t], InactiveNumber[,,t] ,
                            InactiveBenefits[,,t], BaseWage[,,t],MortalityTable)
    
    
    #Disability Payout
    #Calculated as a percent of total payroll
    DisabilityAmount <- sum(BaseWage[,,t]*ActiveNumber[,,t])*DisabilityPayoutRate
    
    # Generate current year's returns ------------------------------
    normal_shock <- rnorm(1,mean=ExpRet[[1]],sd=SD[[1]])
    
    returns<- c(normal_shock,ExpRet[2])
    
    AnnualRet <- 0
    ret <- c(Nasset)
    for (i in 1:Nasset) {
      ret[i] <- returns[i]
      AnnualRet <- AnnualRet + AssetShare[i] * ret[i]
    }
    
    
    #Update the asset value:  
    #adding the capital gain and contributions.
    #Subtracting due to death, refunds and retirement benefits paid out.
    
    # NOTE: The EmployeeContributionRate may be different based on plan tier. Based on the current year and 
    # serivce years you may need to add if statements to break them out into different tiers
    Assets[t+1,n] <- Assets[t,n]*(1+AnnualRet)+sum(BaseWage[,,t]*ActiveNumber[,,t])*
      (EmployeeContributionRate+EmployerContributionRate)-sum(RetirementNumber[,,t]*RetirementBenefit[,,t])-
      RefundAmount-DeathAmount-DisabilityAmount
    
    #Keep track of the cash flow
    CashOutflow[t,n] <- sum(RetirementNumber[,,t]*RetirementBenefit[,,t])+
      RefundAmount+DeathAmount+DisabilityAmount
    
    if(Assets[t+1,n] < 0){
      
      #Add default to default counter
      CountDefault <- CountDefault+1
      
      #Set asset amount to 0
      Assets[t+1,n] <- 0
      #break for loop go to next
      #break
      
    }
    
    #Update the employee number matrix. New Hires are done the same way as Sheiner et al
    #First get the total number of employees in year t+1
    
    TotalEmployees <- sum(ActiveNumber[,,t])*(1+PopulationGrowth) 
    
    #Now Call the update employee function to compute the new distribution of employees
    ActiveNumber[,,t+1] <-  UpdateEmployeeCount(ActiveNumber,SeparationRate,
                                                RetirementRate,MortalityTable,TotalEmployees,t)
    
    
    #Update Base Wage amount
    #Wages are increased by inflation
    BaseWage[,,t+1] <- BaseWage[,,t]*(1+Inflation)
    
    
    #Update the number of inactive vested employees
    InactiveNumber[,,t+1] <- UpdateInactiveCount(ActiveNumber,InactiveNumber,
                                                 SeparationRate,RefundRate, MortalityTable,t )
    
    
    #UPDATE INACTIVE BENEFITS
    
    InactiveBenefits[,,t+1] <- UpdateInactiveBenefits(InactiveNumber ,ActiveNumber,
                                                      BaseWage , InactiveBenefits,SeparationRate,t  )
    
    
    #UPDATE RETIREMENT NUMBERS 
    RetirementNumber[,,t+1] <-  UpdateRetirementNumber(RetirementNumber,
                                                       ActiveNumber,InactiveNumber, RetirementRate,MortalityTable,t)
    
    
    #UPDATE RETIREMENT BENEFITS
    RetirementBenefit[,,t+1] <-  UpdateRetirementBenefit(RetirementBenefit,RetirementNumber, BaseWage,COLA,
                                                         MortalityTable,InactiveNumber,InactiveBenefits,
                                                         ActiveNumber,RetirementRate,BenefitFactor,t)
    
    
  }
  
  
}
proc.time() -ptm


