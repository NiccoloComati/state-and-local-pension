############# Simulation Functions #####################
#These functions are used in the Monte Carlo Simulation

first_nonmissing_numeric <- function(...){
  
  values <- list(...)
  for(value in values){
    
    if(length(value) == 0){
      next
    }
    
    numeric_value <- suppressWarnings(as.numeric(unlist(value)[1]))
    if(!is.na(numeric_value)){
      return(numeric_value)
    }
    
  }
  
  return(NA_real_)
  
}


get_legacy_ppd_value <- function(plan, column, fiscal_year = 2017){
  
  legacy_file <- file.path("Common_Data", "PPD_planlevel_main.csv")
  if(!file.exists(legacy_file)){
    return(NA_real_)
  }
  
  legacy_ppd <- read.csv(legacy_file, stringsAsFactors = FALSE)
  if(!(column %in% names(legacy_ppd))){
    return(NA_real_)
  }
  
  legacy_plan_id <- paste0(plan, "_", fiscal_year)
  legacy_row <- legacy_ppd[legacy_ppd$planid == legacy_plan_id,]
  if(nrow(legacy_row) == 0){
    return(NA_real_)
  }
  
  return(first_nonmissing_numeric(legacy_row[[column]]))
  
}


get_inactive_member_count <- function(plan, planinfo){
  
  first_nonmissing_numeric(
    planinfo$InactiveVestedMembers,
    get_legacy_ppd_value(plan, "inactive")
  )
  
}


get_wage_growth_assumption <- function(plan, planinfo){
  
  wage_growth <- first_nonmissing_numeric(
    planinfo$PayrollGrowthAssumption,
    planinfo$WageInflation,
    get_legacy_ppd_value(plan, "wage_inf"),
    planinfo$InflationAssumption_GASB,
    get_legacy_ppd_value(plan, "inflation")
  )
  
  if(is.na(wage_growth)){
    stop("Missing wage growth assumption for ", plan)
  }
  
  return(wage_growth)
  
}


get_inflation_assumption <- function(plan, planinfo){
  
  inflation <- first_nonmissing_numeric(
    planinfo$InflationAssumption_GASB,
    get_legacy_ppd_value(plan, "inflation")
  )
  
  if(is.na(inflation)){
    stop("Missing inflation assumption for ", plan)
  }
  
  return(inflation)
  
}


scale_inactive_members <- function(inactive, plan, planinfo, PPD){
  
  inactive_adj <- first_nonmissing_numeric(PPD$inactive_adj)
  if(is.na(inactive_adj)){
    stop("Missing inactive_adj for ", plan)
  }
  
  if(inactive_adj == 1){
    inactive_count <- get_inactive_member_count(plan, planinfo)
    if(is.na(inactive_count)){
      stop("Missing inactive member count for ", plan)
    }
    return(inactive * inactive_count)
  }
  
  active_count <- first_nonmissing_numeric(planinfo$actives_tot)
  if(is.na(active_count)){
    stop("Missing active member count for ", plan)
  }
  
  return(inactive * active_count * inactive_adj)
  
}


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
          
          
          TempRefund <- Wage[i,j,year]*EmployeeContributionRate* sum((1+refundReturn)^seq(j))
          
          
          AmountRefund <- AmountRefund + TempRefund* NumRefund[i,j]
          
        }else{
          
          #Have to loop through each year because wages are different
          #Return the Risk free rate of all their contributions 
          
          
          TempRefund <- sum(PastWages(Wage,age=i,service = j,year,j) *EmployeeContributionRate*(1+refundReturn)^seq(j))
          
          
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
    
    for (j in 1:min(c(i,dim(Employees)[2]-1))){
      
      DeathTotal <- DeathTotal + Employees[i,j]*Mort*Annuity*min(BenefitFactor*j,BenefitCap)*Wage[i,j]*MortAdujst+
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
  

  for (i in 1:(dim(Employees)[1]-1)){
    
    
    Mort <-  MortTable[i,2] 
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in 1:min(c(i,dim(Employees)[2]-1))) {
      
      
      ProbSeparate <-  Mort + SepRate[i,j] + RetRate[i,j]
      
     
      
      Employees[i + 1, j+1, year + 1] <- Employees[i, j, year] * (1 - ProbSeparate) 
      
    }
    
    
  }
  
  #create a distribution based on how many employees each group lost
  CalibrateMatrix <-  (Employees[,1:3,year])/sum(Employees[,1:3,year])


  
  

  Employees[,1:3 , year + 1] <- Employees[,1:3 , year + 1]+ 
    (CalibrateMatrix*(TotalEmployees-sum(Employees[, , year + 1])))    

  
  return(Employees[,,year+1])
  
  
  
}

# Update the number of Inactive employees and the benefits they are owed.
# The function UpdateInactiveCount ages the current inactive works by 1 year.  
#Add the new separators and subtract the inactive participants that have died.
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
      
      #Remove those that retire or die
      ProbRemove <- DeathRate +  RetirementRate[i,j]
      Inactive[i, j, year + 1] <- Inactive[i, j, year + 1] - (Inactive[i-1, j, year ] * (ProbRemove))
      
      
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
  
  #Get the mortality rates 
  DeathRate <-  MortalityTable[(1:nrow(TotalBenefits)),2] 
  #Rate to remove benefits of people that have left due to retirement or death
  remove_rate <- DeathRate+RetirementRate
  
  
  # Move the total Benfits forward a year and remove benefits of those that are no longer in the system
  # Now assumes that no growth is added to accrued benefits
  # Could add the risk-free interest rate growth to benefits?
  TotalBenefits[2:(dim(TotalBenefits)[1]),, 2] <- TotalBenefits[1:(dim(TotalBenefits)[1]-1), , 1 ]-
    TotalBenefits[1:(dim(TotalBenefits)[1]-1), , 1 ]*remove_rate[1:(dim(TotalBenefits)[1]-1),]
  
  #Probability of seperating and not taking refund 
  ProbSepNoRef <- SepRate*(1-RefundRate)
  
  for (i in (NyearFullBenefit+1):(dim(Employees)[1])){
    
    
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]-1))) {
      
      
      #Add employees that seperate  
      ProbSeparate <- ProbSepNoRef[i,j]
      
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
  result[is.nan(result) |is.infinite(result)  ] <- 0
  
  return(result) 
  
  
}

# the function UpdateRetirementNumber ages the retirement group by 1 year. 
# It subtracts those that die and adds those who enter retirement.

# NOTE: The retirement matrix is sperated by tiers. Based on the current year and 
# serivce years you may need to add if statements to break them out into different tiers
UpdateRetirementNumber <- function(Retirement,Employees, Inactive,RetRate,MortTable,year){

  #Index number for mortality table
  MortIndex <- 20
  
  #Get the mortality rates 
  DeathRate <-  MortTable[(MortIndex:(dim(Retirement)[1]+MortIndex-1)),2] 
  
  #Age everyone in the retirement matrix. Keep only those that survive
  #Subtract out the benefits from the people that were lost. 
  # Use Rauh’s assumption that 60% of the population is married and to a spouse of the same age
  
  Retirement[,,year] <- Retirement[,,year] - (Retirement[,,year]*DeathRate*(1-pct_mrg)) 
  
  #Age everyone in the retirement matrix. Keep only those that survive
  Retirement[2:(dim(Retirement)[1]),1, year + 1] <- Retirement[1:(dim(Retirement)[1]-1), 1, year ]
  
  for (i in (20):(dim(Employees)[1])){
    
    #Count new retirees
    NewRetire <- 0

    rowIndex2 <- (i-(20)+1)
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]))) {
    

      #Add employees that retire  
      ProbRetirement<- RetRate[i,j]
      
      
      NewRetire <- NewRetire +  (Employees[i, j, year] * (ProbRetirement)) + (Inactive[i,j,year]*ProbRetirement)
      
    }
    
    Retirement[rowIndex2,1, year + 1] <- Retirement[rowIndex2,1, year + 1] + NewRetire
    
  }
  
  result <- Retirement[,, year + 1]
  result[is.nan(result) | is.infinite(result)| is.na(result)] <- 0
  
  return(result)
  
}

# the function UpdateRetirementBenefit updates the average benefits received by those in retirement.

UpdateRetirementBenefit <- function( RetBen , RetNum, Wage ,cola,
                                     MortTable, Inactive, InactiveBen , Employees,
                                     RetRate, BenFactor,year){
 
  #To adjust the average benefits, we need to know what the total benefits were. 
  #Get the dim(total benefits, TotalRetirmentBenefits is a temporary matrix to store total benefits
  TotalRetirmentBenefits <- array(RetBen[,1,(year:(year+1))],c(dim(RetNum)[1],1,2)) *
    array(RetNum[,1,(year:(year+1))],c(dim(RetNum)[1],1,2))
  
  #Index number for mortality table
  MortIndex <- 20
  
  #Get the mortality rates 
  DeathRate <-  MortTable[(MortIndex:(dim(TotalRetirmentBenefits)[1]+MortIndex-1)),2] 
  
  #Age everyone in the retirement matrix. Keep only those that survive
  #Subtract out the benefits from the people that were lost. 
  #Use Rauh’s assumption that 60% of the population is married and to a spouse of the same age
  #and that the plan allows for 50% survivorship benefit
  
  TotalRetirmentBenefits[,,1] <- TotalRetirmentBenefits[,,1] - (TotalRetirmentBenefits[,,1]*DeathRate)  +
    (TotalRetirmentBenefits[,,1]*DeathRate*pct_mrg* widow_reduct)
  
  #Define a variable for number of rows
  rowDim <- dim(TotalRetirmentBenefits)[1]
  
  #Move the Benefits forward a year
  #Adjust for cola
  TotalRetirmentBenefits[2:(rowDim),1, 2] <- TotalRetirmentBenefits[1:(rowDim-1), 1, 1 ]*(1+cola)

    # Add the active and inactive employees that enter retirement
  
  #NOTE: The tier is not stored in the active employees’ matrices so if there’s more than 1 tier there needs to be
  # a series of if statements to check the tier
  for (i in (20):(dim(Employees)[1])){
    
    #sum the new benefits
    NewBenefit <- 0
    
    rowIndex2 <- (i-(20)+1)
    
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in NyearFullBenefit:min(c(i,dim(Employees)[2]))) {
      
      
      #Add employees that retire  
      ProbRetirement<- RetRate[i,j]
      
      
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
    
    
    TotalRetirmentBenefits[rowIndex2,1,2]<-  TotalRetirmentBenefits[rowIndex2,1, 2]+NewBenefit
    
    
  }
  
  
  # The new average benefit for each age-tier of retirement
  #End up dividing by 0 so remove NaN
  result <- TotalRetirmentBenefits[,,2]/RetNum[,,year+1]
  result[is.nan(result) | is.infinite(result)| is.na(result)] <- 0
  return(result)
}


# L_UpdateEmployeeCount is a function which updates employees lost but does not add new employees.
#L is for liability. This function is used in functions that calculate liabilities
#What this function does is age the current workforce by 1 year.
#Removing the retirees, separators and people who have died.
# As inputs the function takes the current number of employees,
#separation rates, retirement rates, a mortality table

L_UpdateEmployeeCount <- function(Employees,SepRate,RetRate,MortTable,year){
  
  
  
  for (i in 1:(dim(Employees)[1]-1)){
    
    
    Mort <-  MortTable[i,2] 
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in 1:min(c(i,dim(Employees)[2]-1))) {
      
      
      ProbSeparate <-  Mort + SepRate[i,j] + RetRate[i,j]
      
      Employees[i + 1, j+1, year + 1] <- Employees[i, j, year] * (1 - ProbSeparate) 
      
    }
    
    
  }
  
  return(Employees[,,year+1])
  
  
}



#Annuity Amounts. Used in Death Pay

ComputeAnnuity <- function(COLA){
  
  AnnuityVector <- vector(length= EmployeeEnd-EmployeeStart+1)
  
  for (i in c(1:(EmployeeEnd-EmployeeStart+1))){
    
    liveProb <- 1
    
    curage <- i
    
    #Get Annuity Factor for given Age
    annuityFactor<- 0
    
    for(m in curage:dim(MortalityTable)[1]){
      
      #probability of living from year current age to age m
      liveProb <- (1-MortalityTable[m,2])*liveProb
      
      #From Sheiner et al. 
      annuityFactor <- annuityFactor + liveProb*
        (1/(1+annuity_dr))^(m-curage)*(1+COLA)^(m-curage)
      
      
    }
    
    AnnuityVector[i] <- annuityFactor
    
    
    
  }
  
  return(AnnuityVector)
  
}





# This the is the monte carlo simulation for the employees that aren't retired
# in the starting year of the simulations
Main_Current <- function(ActiveNumber,InactiveNumber,COLA_f,WageYears_f,BenefitCap_f,
                        BenefitFactor_f,RetirementStart_f,NyearFullBenefit_f,CurrentTier=T){

COLA <<-COLA_f  
WageYears <<- WageYears_f
BenefitCap <<-  BenefitCap_f 
BenefitFactor <<- BenefitFactor_f
RetirementStart <<- RetirementStart_f
NyearFullBenefit <<- NyearFullBenefit_f
  



### Number of Active members ### 

#Expand Collapsed Active Age Service Matrix

ActiveNumber <- array(ActiveNumber, c(dim(ActiveNumber), Nyear));  

ActiveNumber[,,2:Nyear] <- 0





### Number of Inactive Members ### 



#Expand Collapsed Active Age Service Matrix

InactiveNumber <- array(InactiveNumber, c(dim(InactiveNumber), Nyear))


InactiveNumber[,,2:Nyear] <- 0




#Inactive matrix keeps track of vested members
#remove unvested members
#InactiveNumber[,1:(NyearFullBenefit-1),1] <- 0




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



#Create 3d matix
RetirementNumber <- array(0, c(120-40+1,1, Nyear))



RetirementBenefit <- array(0, c(120-40+1,1, Nyear))



########  SET-UP AND SIMULATIONS  (no user input required) ########  

count1 <- 0 # Count the number of times the fund goes bankrupt

prob1 <- 0  # Setting up proportion of instances in which fund goes bankrupt

AAL <- matrix(0,nrow = Nyear,ncol= NMonte)

CashOutflow <- matrix(0,nrow = Nyear,ncol= NMonte)

CashInflow <- matrix(0,nrow = Nyear,ncol= NMonte)

PresentValueFutureBenefits <- matrix(0,nrow=Nyear,ncol=2)

PresentValueNormalCost <- matrix(0,nrow=Nyear,ncol=1)

NormalCost <- matrix(0,nrow=Nyear,ncol=1)

PVFS_vec <- matrix(0,nrow=Nyear,ncol=1)

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
      
      PresentValueFutureBenefits[t,] <- TotalLiabilities_Current(ActiveNumber,
                                                         InactiveNumber,InactiveBenefits,
                                                         BaseWage,80,t,discountrate,scaling)
      
      
      
      
      
      PVFS <- PVNC_Values[[2]]*(1+Inflation)^(t-1)
      
      NCxs <- PVNC_Values[[1]]*(1+Inflation)^(t-1)
      
      PVNC <- 0
      
      NC <- 0
      
      
      
      for (i in (1:(dim(ActiveNumber)[1]))){
        
        
        #This min prevents unnecessary looping
        #Can't have more service than age allows
        for (j in  1:min(c(i,dim(ActiveNumber)[2]))) {
          
          
          PVNC <- PVNC + ActiveNumber[i,j,t]*NCxs[i]*PVFS[i,j]
          
          NC <- NC + ActiveNumber[i,j,t]*NCxs[i]*BaseWage[i,j,t]
          
          
        }
        
      }
      
      
      
      
      PresentValueNormalCost[t,1] <- PVNC
      
      NormalCost[t,1] <- NC
      
      PVFS_vec[t,1] <- sum(PVFS)
      
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
    
    
    #*Changed* In TX 10,000 is paid to surving spouse in death amount
    #Assume 60% are married with spouses that get paid
    #MortIndex <- RetirementStart-EmployeeStart+1
    #DeathAmount <- DeathAmount + sum((RetirementNumber[,,t]*
    #                                    MortalityTable[(MortIndex:(dim(RetirementNumber)[1]+MortIndex-1)),2] *.4)*10000)
    
    
    #Disability Payout
    #Calculated as a percent of total payroll
    DisabilityAmount <- sum(BaseWage[,,t]*ActiveNumber[,,t])*DisabilityPayoutRate
  
    #Keep track of the cash flow
    CashOutflow[t,n] <- (sum(RetirementNumber[,,t]*RetirementBenefit[,,t])+
      RefundAmount+DeathAmount+DisabilityAmount)
   
    
    CashInflow[t,n] <- (sum(BaseWage[,,t]*ActiveNumber[,,t])*
                          (EmployeeContributionRate+EmployerContributionRate))
    
    #Update the employee number matrix. New Hires are done the same way as Sheiner et al
    #First get the total number of employees in year t+1
    
    TotalEmployees <- sum(ActiveNumber[,,t])*(1+PopulationGrowth) 
    
  
    #Update Base Wage amount
    #Wages are increased by inflation
    BaseWage[,,t+1] <- BaseWage[,,t]*(1+WageGrowth)
    
    if(CurrentTier){
      #Now Call the update employee function to compute the new distribution of employees
      ActiveNumber[,,t+1] <-  UpdateEmployeeCount(ActiveNumber,SeparationRate,
                                                  RetirementRate,MortalityTable,TotalEmployees,t)
      
        }else{
      
      #Now Call the update employee function to compute the new distribution of employees
      ActiveNumber[,,t+1] <-  L_UpdateEmployeeCount(ActiveNumber,SeparationRate,
                                                  RetirementRate,MortalityTable,t)
    }
    
    
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



return(list(AAL,CashOutflow,CashInflow,PresentValueFutureBenefits,NormalCost))


}




# This the is the monte carlo simulation for the employees that are retired
# in the starting year of the simulations


Main_Ret <-function(RetirementNumber,RetirementBenefit){
  
  ### Retirement Data ###
  
  

  #Create 3d matix
  RetirementNumber <- array(RetirementNumber, c(dim(RetirementNumber), Nyear))
  RetirementNumber[,,2:Nyear] <- 0
  
  
  RetirementBenefit <- array(RetirementBenefit, c(dim(RetirementBenefit), Nyear))
  RetirementBenefit[,,2:Nyear] <- 0
  
  ########  SET-UP AND SIMULATIONS  (no user input required) ########  
  
  count1 <- 0 # Count the number of times the fund goes bankrupt
  
  prob1 <- 0  # Setting up proportion of instances in which fund goes bankrupt
  
  AAL <- matrix(0,nrow = Nyear,ncol= NMonte)
  
  CashOutflow <- matrix(0,nrow = Nyear,ncol= NMonte)
  
  PresentValueFutureBenefits <- matrix(0,nrow=Nyear,ncol=1)
  
  
  ###FOR TESTING
  Tracker <- matrix(0,nrow = Nyear,ncol= NMonte)
  TrackList <- list()
  ####
  
  AgeSerMatrixDim <- c(EmployeeEnd-EmployeeStart+1,ServiceEnd-ServiceStart+1)
  
  #wipe clean the matricies
  ActiveNumber <- array(0,c(AgeSerMatrixDim,Nyear))
  InactiveNumber <-  array(0,c(AgeSerMatrixDim,Nyear))
  BaseWage<-  array(0,c(AgeSerMatrixDim,Nyear))
  InactiveBenefits <-  array(0,c(AgeSerMatrixDim,Nyear))
  
  
  # Start of Monte Carlo Loop 
  for (n in 1:NMonte) {
    
    
    #wipe clean the matricies, except for the 1st year
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
        
        PresentValueFutureBenefits[t,] <- TotalLiabilities_Ret( RetirementNumber,RetirementBenefit,
                                                                80,t,discountrate,scaling)
      }
        #Acturial Accrued Liability
        #Present Value Normal Cost is subtracted from Active Members PVFB then added with nonactive PVFB
        
        AAL[t,n] <- PresentValueFutureBenefits[t,1]
        
        #Keep track of the cash flow
        CashOutflow[t,n] <- (sum(RetirementNumber[,,t]*RetirementBenefit[,,t]))
        
        #UPDATE RETIREMENT NUMBERS 
        RetirementNumber[,,t+1] <-  UpdateRetirementNumber(RetirementNumber,
                                                           ActiveNumber,InactiveNumber, RetirementRate,MortalityTable,t)
        
        
        #UPDATE RETIREMENT BENEFITS
        RetirementBenefit[,,t+1] <-  UpdateRetirementBenefit(RetirementBenefit,RetirementNumber, BaseWage,COLA,
                                                             MortalityTable,InactiveNumber,InactiveBenefits,
                                                             ActiveNumber,RetirementRate,BenefitFactor,t)
        
        
      
      
      
    }


  }
  
  
  return(list(AAL,CashOutflow))
  
  
}





