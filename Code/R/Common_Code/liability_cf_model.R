
#Calculates the Present Value Normal Cost
PVNC_Calc <- function(Employees,Inactive,InactiveBen,RetNum,RetBen,
                      Wage,L_Nyear,Year,DiscountRate){
  
  #Create a 3d matrix 
  L_BaseWage <- array(Wage[,,Year], c(dim(Wage[,,Year]), L_Nyear));
  
  L_BaseWage[,,2:L_Nyear] <- 0
  
  
  ### Number of Active members ### 
  
  L_ActiveNumber <- array(0, c(dim(Employees[,,Year]), L_Nyear));  
  
  
  ### Number of Inactive Members ### 
  
  L_InactiveNumber <- array(0, c(dim(Inactive[,,Year]), L_Nyear))
  
  ### Inactive Benfits ### 
  
  L_InactiveBenefits <- array(0, c(dim(InactiveBen[,,Year]), L_Nyear))
  
  
  ### Retirement Data ###
  
  #Create 3d matix
  L_RetirementNumber <- array(0, c(length(RetNum[,,Year]),1, L_Nyear))
  
  L_RetirementBenefit <- array(0, c(length(RetNum[,,Year]),1, L_Nyear))
  
  ########  SET-UP AND SIMULATIONS  (no user input required) ########  
  
  PVNC_CashOutflow <- matrix(0,nrow = L_Nyear,ncol= 1)
  
  PVFB <- vector(length = dim(Employees)[1])
  
  # Start of Monte Carlo Loop 
  for (a in 1:dim(Employees)[1]) {
    
    L_BaseWage[,,2:L_Nyear] <- 0
    
    #TEMP
    L_ActiveNumber[,,1:L_Nyear] <- 0
    L_InactiveNumber[,,1:L_Nyear] <- 0
    L_InactiveBenefits[,,1:L_Nyear] <- 0
    L_RetirementNumber[,,1:L_Nyear] <- 0
    L_RetirementBenefit[,,1:L_Nyear] <- 0
    L_ActiveNumber[a,1,1] <- 1
    
    
    CashOutflow <- matrix(0,nrow = L_Nyear,ncol= 1)
    
    
    # Start of Time Loop ------------------------------
    for (t in 1:(L_Nyear-1)) {
      
      
      #Calculate the amount refunded to separators.
      #Refund is a function which takes number of employees, the separation rate, 
      #refund rate and the average of the last few years salary to 
      #calculate the total sum give 
      #out to refunds this year 
      RefundAmount = Refund(L_ActiveNumber[,,t], SeparationRate, RefundRate,
                            L_BaseWage,t)
      
      
      #Calculate the amount paid out due to death during employment or inactive and not receiving benefits
      #DeathPay is a function which takes number of employees, mortality table, 
      #number of inactive workers,  the average benefits for inactive works 
      #and the average of the last few years salary to calculate the total sum paid out due to death
      #in the event of death their spouse/heir is assumed to recieve an annuity based on
      #current salary and years of service
      DeathAmount = DeathPay( L_ActiveNumber[,,t], L_InactiveNumber[,,t] ,
                              L_InactiveBenefits[,,t], L_BaseWage[,,t],MortalityTable)
      
      

      
      #Disability Payout
      #Calculated as a percent of total payroll
      DisabilityAmount <- sum(L_BaseWage[,,t]*L_ActiveNumber[,,t])*DisabilityPayoutRate
      
      
      # NOTE: The EmployeeContributionRate may be different based on plan tier. Based on the current year and 
      # serivce years you may need to add if statements to break them out into different tiers
      
      #Keep track of the cash flow
      CashOutflow[t,1] <- sum(L_RetirementNumber[,,t]*L_RetirementBenefit[,,t])+
        RefundAmount+DeathAmount
      
      
      #Now Call the update employee function to compute the new distribution of employees
      L_ActiveNumber[,,t+1] <-  L_UpdateEmployeeCount(L_ActiveNumber,SeparationRate,
                                                      RetirementRate,MortalityTable,t)
      
      
      #Update Base Wage amount
      #Wages are increased by inflation
      L_BaseWage[,,t+1] <- L_BaseWage[,,t]*(1+WageGrowth)
      
      
      #Update the number of inactive vested employees
      L_InactiveNumber[,,t+1] <- UpdateInactiveCount(L_ActiveNumber,L_InactiveNumber,
                                                     SeparationRate,RefundRate, MortalityTable,t )
      
      
      #UPDATE INACTIVE BENEFITS
      
      L_InactiveBenefits[,,t+1] <- UpdateInactiveBenefits(L_InactiveNumber ,L_ActiveNumber,
                                                          L_BaseWage , L_InactiveBenefits,SeparationRate,t  )
      
      
      #UPDATE RETIREMENT NUMBERS 
      L_RetirementNumber[,,t+1] <-  UpdateRetirementNumber(L_RetirementNumber,
                                                           L_ActiveNumber,L_InactiveNumber, 
                                                           RetirementRate,MortalityTable,t)
      
      
      #UPDATE RETIREMENT BENEFITS
      L_RetirementBenefit[,,t+1] <-  UpdateRetirementBenefit(L_RetirementBenefit,L_RetirementNumber, L_BaseWage,
                                                             COLA,MortalityTable,L_InactiveNumber,L_InactiveBenefits,
                                                             L_ActiveNumber,RetirementRate,BenefitFactor,t)
      
    }
    
    libability <- 0
    
    for (i in c(1:dim(CashOutflow)[1])) {
      
      libability <-  libability + CashOutflow[i,1]/(1 + DiscountRate)^i
      
    }
    
    
    PVFB[a] <- libability
    
  }
  
  #Present Value Future Salaries
  PVFS <- array(0,c(dim(L_BaseWage[,,1])))
  
  for (i in (1:(dim(L_ActiveNumber)[1]))){
    
    #This min prevents unnecessary looping
    #Can't have more service than age allows
    for (j in  1:min(c(i,dim(L_ActiveNumber)[2]))) {
      
      YearsLeftToWork <- min(dim(L_ActiveNumber)[1]-i,dim(L_ActiveNumber)[2]-j)
      
      tempsum <- 0
      
      ListWage <- PastWages(L_BaseWage,i+YearsLeftToWork,j+YearsLeftToWork,j+YearsLeftToWork,j+YearsLeftToWork)
      
      #probability of staying employed until a certain date
      ProbTracker <- 1
      
      for(m in 0:(YearsLeftToWork)){
        
        jm <- j+m
        
        
        ProbSeparate <- SeparationRate[i+m,j+m] +  MortalityTable[i+m,2]+ RetirementRate[(i+m),jm]
        
      
        #Probability of seperating can't be hire then 1.
        ProbSeparate <- min(ProbSeparate,1)
        
        ProbTracker <- (1-ProbSeparate)*ProbTracker
        
        
        tempsum <- tempsum +  ListWage[[m+1]]*ProbTracker/(1 + DiscountRate)^m
        
        
      }
      
      
      PVFS[i,j] <- tempsum
      
      
    }
    
  }
  
  
  NCxs <- PVFB/PVFS[,1]
  
  NCxs[is.nan(NCxs)] <- 0
  NCxs[is.infinite(NCxs)] <- 0
  
  if (is.nan(sum(NCxs))) {
    stop("PVFS must be numeric", call. = FALSE)
  }
  
  
  
  
  return(list(NCxs,PVFS))
  
  
}



#Calculates the Total Liabilities

TotalLiabilities_Current <- function(Employees,Inactive,InactiveBen,
                                    Wage,L_Nyear,Year,DiscountRate,Scaling){
#Create a 3d matrix 
L_BaseWage <- array(Wage[,,Year], c(dim(Wage[,,Year]), L_Nyear));  

L_BaseWage[,,2:L_Nyear] <- 0


### Number of Active members ### 

L_ActiveNumber <- array(Employees[,,Year], c(dim(Employees[,,Year]), L_Nyear));  

L_ActiveNumber[,,2:L_Nyear] <- 0


### Number of Inactive Members ### 

L_InactiveNumber <- array(Inactive[,,Year], c(dim(Inactive[,,Year]), L_Nyear))


L_InactiveNumber[,,2:L_Nyear] <- 0


### Inactive Benfits ### 

L_InactiveBenefits <- array(InactiveBen[,,Year], c(dim(InactiveBen[,,Year]), L_Nyear))


L_InactiveBenefits[,,2:L_Nyear] <- 0



#Create 3d matix
L_RetirementNumber <- array(0, c(120-40+1,1, L_Nyear))
#L_RetirementNumber[,,2:L_Nyear] <- 0


L_RetirementBenefit <- array(0, c(120-40+1,1, L_Nyear))
#L_RetirementBenefit[,,2:L_Nyear] <- 0


########  SET-UP AND SIMULATIONS  (no user input required) ########  


L_CashOutflow <- matrix(0,nrow = L_Nyear,ncol= 2)

L_InactiveNumberTemp <- L_InactiveNumber
L_InactiveBenefitsTemp <- L_InactiveBenefits
L_RetirementNumberTemp <- L_RetirementNumber
L_RetirementBenefitTemp <- L_RetirementBenefit
L_ActiveNumberTemp <- L_ActiveNumber

for(i in c(1:2)){
  
 
if(i == 1){  
#Get the cash flows for current active employees only
  L_ActiveNumber <- L_ActiveNumberTemp
  L_InactiveNumber[,,1:L_Nyear] <- 0
  L_InactiveBenefits[,,1:L_Nyear] <- 0
  L_RetirementNumber[,,1:L_Nyear] <- 0
  L_RetirementBenefit[,,1:L_Nyear] <- 0
}else{
  #Get the cash flows for current inactive employees and retirees only
  L_ActiveNumber[,,1:L_Nyear] <- 0
  L_InactiveNumber <- L_InactiveNumberTemp
  L_InactiveBenefits<- L_InactiveBenefitsTemp
  L_RetirementNumber[,,1:L_Nyear] <- 0
  L_RetirementBenefit[,,1:L_Nyear] <- 0
  
  
}


# Start of Time Loop ------------------------------
for (t in 1:(L_Nyear-1)) {
  
  
  #Calculate the amount refunded to separators.
  #Refund is a function which takes number of employees, the separation rate, 
  #refund rate and the average of the last few years salary to 
  #calculate the total sum give 
  #out to refunds this year 
  RefundAmount = Refund(L_ActiveNumber[,,t], SeparationRate, RefundRate,
                        L_BaseWage,t)
  
  
  
  #Calculate the amount paid out due to death during employment or inactive and not receiving benefits
  #DeathPay is a function which takes number of employees, mortality table, 
  #number of inactive workers,  the average benefits for inactive works 
  #and the average of the last few years salary to calculate the total sum paid out due to death
  #in the event of death their spouse/heir is assumed to recieve an annuity based on
  #current salary and years of service
  DeathAmount = DeathPay( L_ActiveNumber [,,t], L_InactiveNumber[,,t] ,
                          L_InactiveBenefits[,,t], L_BaseWage[,,t],MortalityTable)
  
  
  
  #Disability Payout
  #Calculated as a percent of total payroll
  DisabilityAmount <- sum(L_BaseWage[,,t]*L_ActiveNumber[,,t])*DisabilityPayoutRate
  
  
  #Keep track of the cash flow
  L_CashOutflow[t,i] <- (sum(L_RetirementNumber[,,t]*L_RetirementBenefit[,,t])+
    RefundAmount+DeathAmount + DisabilityAmount)*Scaling
  


  #Update the employee number matrix. New Hires are done the same way as Sheiner et al
  #First get the total number of employees in year t+1
  
  #TotalEmployees <- sum(ActiveNumber[,,t])*(1+PopulationGrowth) 
  
  #Now Call the update employee function to compute the new distribution of employees
  L_ActiveNumber[,,t+1] <-  L_UpdateEmployeeCount(L_ActiveNumber,SeparationRate,
                                              RetirementRate,MortalityTable,t)
  
  
  #Update Base Wage amount
  #Wages are increased by inflation
  L_BaseWage[,,t+1] <- L_BaseWage[,,t]*(1+WageGrowth)
  
  
  #Update the number of inactive vested employees
  L_InactiveNumber[,,t+1] <- UpdateInactiveCount(L_ActiveNumber,L_InactiveNumber,
                                               SeparationRate,RefundRate, MortalityTable,t )
  
  #UPDATE INACTIVE BENEFITS
  
  L_InactiveBenefits[,,t+1] <- UpdateInactiveBenefits(L_InactiveNumber ,L_ActiveNumber,
                                                    L_BaseWage , L_InactiveBenefits,SeparationRate,t  )
  
  
  #UPDATE RETIREMENT NUMBERS 
  L_RetirementNumber[,,t+1] <-  UpdateRetirementNumber(L_RetirementNumber,
                                                     L_ActiveNumber,L_InactiveNumber, RetirementRate,MortalityTable,t)
  
  
  #UPDATE RETIREMENT BENEFITS
  L_RetirementBenefit[,,t+1] <-  UpdateRetirementBenefit(L_RetirementBenefit,L_RetirementNumber, L_BaseWage,COLA,
                                                       MortalityTable,L_InactiveNumber,L_InactiveBenefits,
                                                       L_ActiveNumber,RetirementRate,BenefitFactor,t)
  
  
}


}

Active_libability <- 0


for (i in c(1:dim(L_CashOutflow)[1])) {
  
  Active_libability <-  Active_libability + (L_CashOutflow[i,1])/(1 + DiscountRate)^i
  
}


#Retire Liability


Nonactive_libability <- 0


for (i in c(1:dim(L_CashOutflow)[1])) {
  
  Nonactive_libability <-  Nonactive_libability + (L_CashOutflow[i,2])/(1 + DiscountRate)^i
  
}





return(c(Active_libability,Nonactive_libability))




}






TotalLiabilities_Ret <- function(RetNum,RetBen,L_Nyear,Year,DiscountRate,Scaling){
  
  
  
  AgeSerMatrixDim <- c(EmployeeEnd-EmployeeStart+1,ServiceEnd-ServiceStart+1)
  

  #Create a 3d matrix 
  L_BaseWage <-array(0,c(AgeSerMatrixDim,L_Nyear))
  

  ### Number of Active members ### 
  
  L_ActiveNumber <-array(0,c(AgeSerMatrixDim,L_Nyear))
  
  
  ### Number of Inactive Members ### 
  
  L_InactiveNumber <- array(0,c(AgeSerMatrixDim,L_Nyear))
  

  
  
  ### Inactive Benfits ### 
  
  L_InactiveBenefits <- array(0,c(AgeSerMatrixDim,L_Nyear))
  
  

  
  
  ### Retirement Data ###
  
  #Create 3d matix
  L_RetirementNumber <- array(RetNum[,,Year], c(length(RetNum[,,Year]),1, L_Nyear))
  L_RetirementNumber[,,2:L_Nyear] <- 0
  
  
  L_RetirementBenefit <- array(RetBen[,,Year],c(length(RetNum[,,Year]),1, L_Nyear))
  L_RetirementBenefit[,,2:L_Nyear] <- 0
  
  
  
  ########  SET-UP AND SIMULATIONS  (no user input required) ########  
  
  
  L_CashOutflow <- matrix(0,nrow = L_Nyear,ncol= 1)

    
    
    # Start of Time Loop ------------------------------
    for (t in 1:(L_Nyear-1)) {
      
      
      #Keep track of the cash flow
      L_CashOutflow[t,1] <- (sum(L_RetirementNumber[,,t]*L_RetirementBenefit[,,t]))*Scaling
      
      #UPDATE RETIREMENT NUMBERS 
      L_RetirementNumber[,,t+1] <-  UpdateRetirementNumber(L_RetirementNumber,
                                                           L_ActiveNumber,L_InactiveNumber, RetirementRate,MortalityTable,t)
      
      
      #UPDATE RETIREMENT BENEFITS
      L_RetirementBenefit[,,t+1] <-  UpdateRetirementBenefit(L_RetirementBenefit,L_RetirementNumber, L_BaseWage,COLA,
                                                             MortalityTable,L_InactiveNumber,L_InactiveBenefits,
                                                             L_ActiveNumber,RetirementRate,BenefitFactor,t)
      
      
    }
    
    
  
  #Retire Liability
  
  
  Retire_libability <- 0
  
  
  for (i in c(1:dim(L_CashOutflow)[1])) {
    
    Retire_libability <-  Retire_libability + (L_CashOutflow[i,1])/(1 + DiscountRate)^i
    
  }
  
  
  
  
  
  return(Retire_libability)
  
  
  
  
}




