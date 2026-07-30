#This function takes a bucketed matrix and expands the buckets
#The matrix is filled in  with a linear function
# ============================================================================
# SUPERSEDED 2026-07-30 - renamed from LinearFill to LinearFill_incorrect.
#
# This is the weight the project inherited. It is wrong. It is kept here,
# unchanged, and `cluster_code_2022/*.R` still calls it ON PURPOSE so that
# lineage keeps reproducing exactly the results it always produced.
# `cluster_code_2022_072026/*.R` calls the corrected LinearFill below.
#
# The weight was   Share[k,L] <- GroupCount/(N*M) + Slope*(rowmin + k-1)
# Three defects:
#  1. It subtracts an AGE IN YEARS from a HEADCOUNT PER CELL. Different
#     quantities; the difference has no meaning.
#  2. GroupCount sits inside the weight, so the size of the tilt depends on how
#     big the plan is - a band of 20,000 came out 0.1% tilted, a band of 500 at
#     17%. A plan's age profile must not depend on its size.
#  3. The weights are centred on (GroupCount/N - mean age) instead of on 1, so
#     they straddle zero. Their sum - used as the normaliser - equals
#     GroupCount minus the sum of the ages in the band. It VANISHES when a band
#     holds about that many people, and flips sign either side of that point.
#
# Measured over the 40 state plans: three produced NEGATIVE retiree headcounts.
# OK134's 75-79 band held 385.004 people against an age-sum of 385, so the
# normaliser was 0.004 and the band filled with about +/-200,000 people in a
# plan with 4,242 retirees. Band totals still reconciled because the positives
# and negatives cancel, which is why it went unnoticed; a one-person PPD
# revision then moved that plan's liability by 56%.
# ============================================================================
LinearFill_incorrect <- function(Collapased,Slope = 1,retirement=F){
  
  
  if(retirement){
    
    #Get the overall min/max because these are used multiple times in the function
    all_age_max <- 120
    all_age_min <- 40
    
    all_serv_max <- 1
    all_serv_min <- 1
    
    Expanded <- matrix(0,
                       nrow =all_age_max-all_age_min+1,
                       ncol=all_serv_max-all_serv_min+1)
    
    rowmins <- c(40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115)
    rowmaxs <- rowmins+4
    colmins <- c(1)
    colmaxs <- c(1)
    
  }else{
  
  
  #Get the overall min/max because these are used multiple times in the function
  all_age_max <- 74
  all_age_min <- 20
  
  
  all_serv_max <-54
  all_serv_min <- 0
  
  #Create a new age/ service matrix to fill
  
  Expanded <- matrix(0,
                         nrow =all_age_max-all_age_min+1,
                         ncol=all_serv_max-all_serv_min+1)
  
  rowmins <- c(20,25,30,35,40,45,50,55,60,65,70)
  rowmaxs <- rowmins+4
  
  colmins <- c(0,5,10,15,20,25,30,35,40,45,50)
  colmaxs <- colmins+4
  }
  
  
  for (i in c(1:nrow(Collapased))){
      
      rowmin <- rowmins[i]
      
      rowmax <- rowmaxs[i]
      
      
      for (j in c(1:ncol(Collapased))){
      
    
        columnmin <- colmins[j]
        
        columnmax <- colmaxs[j]
        
      
      
      N <- rowmax- rowmin + 1
      
      M <- columnmax- columnmin + 1
    
      #Get the number of employees in cell i,j
      #j+1 because the first column of the collapsed matrix is a label
      GroupCount <- Collapased[i,j]
      
      
      #Create Empty matrix to store the shares
      
      Share <- matrix(0,nrow = N,ncol = M)
      
      sharesum <- 0
      
      for (k in c(1:N)){
        
        # Check if age service rule should be inforced
        # Can not have more service than age allows
        # if not make it so that that if statement is never triggered in the next loop
          svcmax <- rowmin + k - all_age_min
        
        
        for(L in c(1:M)){
          
          
          
          if((columnmin + L - 1) > svcmax){
            Share[k,L] <- 0
          }else{
            
            Share[k,L] <- GroupCount/(N*M) + Slope*(rowmin + k-1 )
            
          }
          
          sharesum <- sharesum + Share[k,L] 
          
          
        } 
        
        
      }
      
      Expanded[((rowmin+1-all_age_min):(rowmax+1-all_age_min)),
               ((columnmin+1-all_serv_min):(columnmax+1-all_serv_min))] <-  Share * GroupCount/sharesum
      
      
      }
    
    
  }
  
  
  
  
  Expanded[is.nan(Expanded)] <- 0
  
  Expanded[is.na(Expanded)] <- 0  
  
  return(Expanded)
  
}




#AgeService checks if the age service rule should be inforced
# meaning you cant have more service than age allows
# enforce_service_limit makes it so that if service is greater than age allows the value is 0
#most of the time you want this but not for retirement rate matricies
ConstantFill <- function(Collapased, enforce_service_limit = T,retirement=F){
  
  if(retirement){
    
    #Get the overall min/max because these are used multiple times in the function
    all_age_max <- 120
    all_age_min <- 40
    
    all_serv_max <- 1
    all_serv_min <- 1
    
    Expanded <- matrix(0,
                       nrow =all_age_max-all_age_min+1,
                       ncol=all_serv_max-all_serv_min+1)
    
    rowmins <- c(40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115)
    rowmaxs <- rowmins+4
    colmins <- c(1)
    colmaxs <- c(1)
    
    
  }else{
  #Get the overall min/max because these are used multiple times in the function
  all_age_max <- 74
  all_age_min <- 20
  
  
  all_serv_max <-54
  all_serv_min <- 0                                         
  
  #Create a new age/ service matrix to fill
  
  Expanded <- matrix(0,
                     nrow =all_age_max-all_age_min+1,
                     ncol=all_serv_max-all_serv_min+1)
  
  rowmins <- c(20,25,30,35,40,45,50,55,60,65,70)
  rowmaxs <- rowmins+4
  
  colmins <- c(0,5,10,15,20,25,30,35,40,45,50)
  colmaxs <- colmins+4
  }
  
  for (i in c(1:nrow(Collapased))){
    
   
    
    
    rowmin <- rowmins[i]
    
    rowmax <- rowmaxs[i]
    
    
    for (j in c(1:ncol(Collapased))){
      
      
      columnmin <- colmins[j]
      
      columnmax <- colmaxs[j]
      
    
      N <- rowmax- rowmin + 1
      
      M <- columnmax- columnmin + 1
      
      
      #Get the  value of the cell
      GroupValue <- Collapased[i,j]
      
      #Create Empty matrix to store the shares
      if(enforce_service_limit){
      Share <- matrix(0,nrow = N,ncol = M)
      
      for (k in c(1:N)){
        
        
          svcmax <- rowmin + k - all_age_min
        
        
        for(L in c(1:M)){
          
          
          
          if((columnmin + L - 1) > svcmax){
            Share[k,L] <- 0
          }else{
            
            Share[k,L] <- GroupValue
            
          }
          
          
          
          
          
          
          
        }
        
        
      }
      
      }else{Share <- matrix(GroupValue,nrow = N,ncol = M)}
      
      
      Expanded[((rowmin+1-all_age_min):(rowmax+1-all_age_min)),
               ((columnmin+1-all_serv_min):(columnmax+1-all_serv_min))]  <-  Share
      
    }
    
    
    
  
  }
  
  
  
  
  Expanded[is.nan(Expanded)] <- 0
  
  Expanded[is.na(Expanded)] <- 0
  
  
  return(Expanded)
  
}


#Constant Fill but only for separation because
# separation matrices can have different rows/columns
ConstantFill_SepRate <-  function(Collapased){
  
  #AgeService checks if the age service rule should be inforced
  # meaning you cant have more service than age allows
  # enforce_service_limit makes it so that if service is greater than age allows the value is 0
  #most of the time you want this but not for retirement rate matricies
  
  
  #Get the overall min/max because these are used multiple times in the function
  all_age_max <- 74
  all_age_min <- 20
  
  
  all_serv_max <-54
  all_serv_min <- 0                                         
  
  #Create a new age/ service matrix to fill
  
  Expanded <- matrix(0,
                     nrow =all_age_max-all_age_min+1,
                     ncol=all_serv_max-all_serv_min+1)
  
  rows <- c(20:74)
  
  
  
  cols <- c(1:55)
  
  
  
  ages <- Collapased[2:12,1]
  
  
  servs <- Collapased[1,2:12]
  
  if (servs[[1]]==0) {
    servs <- servs+1
  }
  
  
  for (i in rows){
    
    
    
    
    for (j in cols){
      
      
      
      
      
      list1 <- ages - i 
      
      list1<- ifelse(list1<0,100,list1)
      
      
      
      if(sum(list1==100)==11){list1[11] <- 0}
      
      age_index <-which(list1 == min(abs(list1)))+1
      
      
      
      list2 <- servs - j 
      
      list2<- ifelse(list2 < 0,100,list2)
      
      
      if(sum(list2==100)==11){list2[11] <- 0}
      
      
      serv_index <- which(list2 == min(abs(list2)))+1
      
      
      #Create Empty matrix to store the shares
      
      
      if(i - j+1 < all_age_min){
        
        GroupValue <- 0 
        
      }else{
        
        #Get the  value of the cell
        GroupValue <- Collapased[age_index,serv_index]
        
        
      }
      
      
      
      
      
      
      Expanded[i-all_age_min+1, j]  <-  GroupValue
      
    }
    
    
    
    
  }
  
  
  
  
  Expanded[is.nan(Expanded)] <- 0
  
  Expanded[is.na(Expanded)] <- 0
  
  
  return(Expanded)
  
}







#Mortality Table
#Constructs a mortality table given the format of the brookings data
MortTable <- function(collapsed_mort, pct_male){
  
  Expanded <- data.frame(Age=double(),Death_Prob=double())
  count<-1
  for(i in c(EmployeeStart:119)){
    
    if(i < 30){
      
      Expanded[count,"Age"] <- i
      Expanded[count,"Death_Prob"] <- collapsed_mort[collapsed_mort$Age==30,"M"]*pct_male+
        collapsed_mort[collapsed_mort$Age==30,"F"]*(1-pct_male)
      
    }else if(i >= 30 & i < 100 ){
      
   
      Expanded[count,"Age"] <- i
      #The mean is taken because there are more than 1 values for age 60
      Expanded[count,"Death_Prob"] <- mean(collapsed_mort[collapsed_mort$Age==floor(i/10)*10,"M"][[1]])*pct_male+
        mean(collapsed_mort[collapsed_mort$Age==floor(i/10)*10,"F"][[1]])*(1-pct_male)
      
    }else{
      
      Expanded[count,"Age"] <- i
      Expanded[count,"Death_Prob"] <- collapsed_mort[collapsed_mort$Age==90,"M"]*pct_male+
        collapsed_mort[collapsed_mort$Age==90,"F"]*(1-pct_male)

    }
    
    count <- count +1
 
  }
  
  return(Expanded)
  
  
  
  
  
}


Calc_Inactive <- function(active, withdrawal, refund,MortalityTable,RetirementStart_f,
                          NyearFullBenefit_f){
  
  
  RetirementStart <<- RetirementStart_f
  
  NyearFullBenefit <<- NyearFullBenefit_f
  
  
  # Workspace for fixed-point inactive distribution convergence, not projection horizon.
  Nyear <- 5000
  
  
  ActiveNumber <- array(active, c(dim(active), Nyear));  
  
  ActiveNumber[,,2:Nyear] <- 0

  
  InactiveNumber <- ActiveNumber

  InactiveNumber[,,1:Nyear] <- 0
  
  TotalEmployees <- sum(ActiveNumber[,,1])
  
  #Now Call the update employee function to compute the new distribution of employees
  ActiveNumber[,,2] <-  UpdateEmployeeCount(ActiveNumber,SeparationRate,
                                            RetirementRate,MortalityTable,TotalEmployees,1)
  
  
  #Update the number of inactive vested employees
  InactiveNumber[,,2] <- UpdateInactiveCount(ActiveNumber,InactiveNumber,
                                             SeparationRate,RefundRate, MortalityTable,1 )
  
  #Update the employee number matrix. New Hires are done the same way as Sheiner et al
  #First get the total number of employees in year t+1
  
  
  t<- 2
  while (abs(mean((InactiveNumber[,,t] - InactiveNumber[,,t-1] )))>.00005 &&
         t < Nyear) {
    
    
    #Now Call the update employee function to compute the new distribution of employees
    ActiveNumber[,,t+1] <-  UpdateEmployeeCount(ActiveNumber,SeparationRate,
                                                RetirementRate,MortalityTable,TotalEmployees,t)
    
    
    #Update the number of inactive vested employees
    InactiveNumber[,,t+1] <- UpdateInactiveCount(ActiveNumber,InactiveNumber,
                                                 SeparationRate,RefundRate, MortalityTable,t )
    t <- t+1
    
  }
  
  if(t >= Nyear){
    warning("Calc_Inactive reached ", Nyear,
            " iterations before satisfying the convergence tolerance.")
  }
  
  if(is.nan(sum(InactiveNumber[,,t]/sum(InactiveNumber[,,t])))){
    
    InactiveNumber <- array(0, c(dim(active)))
    
     InactiveNumber[,NyearFullBenefit_f:55] <-ActiveNumber[,NyearFullBenefit_f:55,1]/
       sum(ActiveNumber[,NyearFullBenefit_f:55,1]) 
    return(InactiveNumber)

  }else{
    
    return(InactiveNumber[,,t]/sum(InactiveNumber[,,t]))
    
    
  }
  
  
  
  
  
}
  
  
CreateTiers <- function(active, inactive, num_tiers){
  
  if (num_tiers==1) {
    
    
    active_t1 <<- active
    
    inactive_t1 <<- inactive
    
    
  }else if (num_tiers==2) {
    
    
    active_t1 <<- active
    
    active_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    active_t2 <<- active
    
    active_t2[,-c(1:tier_serivce[2])] <<- 0
    
    
    inactive_t1 <<- inactive
    
    inactive_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    inactive_t2<<- inactive
    
    inactive_t2[,-c(1:tier_serivce[2])] <<- 0
    
    
    
  }else if (num_tiers==3) {
    
    active_t1<<- active
    
    active_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    active_t2<<- active
    
    active_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    active_t3<<- active
    
    active_t3[,-c(1:tier_serivce[3])] <<- 0
    
    inactive_t1<<- inactive
    
    inactive_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    inactive_t2<<- inactive
    
    inactive_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    inactive_t3<<- inactive
    
    inactive_t3[,-c(1:tier_serivce[3])] <<- 0
    
    
  }else if (num_tiers==4) {
    
    active_t1<<- active
    
    active_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    active_t2<<- active
    
    active_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    active_t3<<- active
    
    active_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <<- 0
    
    
    active_t4<<- active
    
    active_t4[,-c(1:tier_serivce[4])] <<- 0
    
    
    inactive_t1<<- inactive
    
    inactive_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    inactive_t2<<- inactive
    
    inactive_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    inactive_t3<<- inactive
    
    inactive_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <<- 0
    
    
    inactive_t4<<- inactive
    
    inactive_t4[,-c(1:tier_serivce[4])] <<- 0
    
    
    
  }else if (num_tiers==5) {
    
    
    active_t1<<- active
    
    active_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    active_t2<<- active
    
    active_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    active_t3<<- active
    
    active_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <<- 0
    
    
    active_t4<<- active
    
    active_t4[,-c((tier_serivce[5]+1):tier_serivce[4])] <<- 0
    
    
    active_t5<<- active
    
    active_t5[,-c(1:tier_serivce[5])] <<- 0
    
    
    
    
    
    inactive_t1<<- inactive
    
    inactive_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    inactive_t2<<- inactive
    
    inactive_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    inactive_t3<<- inactive
    
    inactive_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <<- 0
    
    
    inactive_t4<<- inactive
    
    inactive_t4[,-c((tier_serivce[5]+1):tier_serivce[4])] <<- 0
    
    
    inactive_t5<<- inactive
    
    inactive_t5[,-c(1:tier_serivce[5])] <<- 0
    
    
    
    
  }else{
    
    
    active_t1<<- active
    
    active_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    active_t2<<- active
    
    active_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    active_t3<<- active
    
    active_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <<- 0
    
    
    active_t4<<- active
    
    active_t4[,-c((tier_serivce[5]+1):tier_serivce[4])] <<- 0
    
    
    active_t5<<- active
    
    active_t5[,-c((tier_serivce[6]+1):tier_serivce[5])] <<- 0
    
    
    active_t6<<- active
    
    active_t6[,-c(1:tier_serivce[6])] <<- 0
    
    #break down inactive into their own tiers 
    
    inactive_t1<<- inactive
    
    inactive_t1[,-c((tier_serivce[2]+1):55)] <<- 0
    
    
    inactive_t2<<- inactive
    
    inactive_t2[,-c((tier_serivce[3]+1):tier_serivce[2])] <<- 0
    
    
    inactive_t3<<- inactive
    
    inactive_t3[,-c((tier_serivce[4]+1):tier_serivce[3])] <<- 0
    
    
    inactive_t4<<- inactive
    
    inactive_t4[,-c((tier_serivce[5]+1):tier_serivce[4])] <<- 0
    
    
    inactive_t5<<- inactive
    
    inactive_t5[,-c((tier_serivce[6]+1):tier_serivce[5])] <<- 0
    
    
    inactive_t6<<- inactive
    
    inactive_t6[,-c(1:tier_serivce[6])] <<- 0
  }
  
  
}
  
  


# ============================================================================
# LinearFill - CORRECTED 2026-07-30. Mirrors Code/python/bucketfill_cf_model.py.
#
# The weight is now a perturbation around 1, driven only by POSITION in the
# band. Every weight is strictly positive, so no cell can go negative, and the
# weights sum to exactly N, so the normaliser is a constant and can never
# approach zero.
#
# The size of the tilt is taken from the DATA, not set by hand: the neighbouring
# bands already say how fast the population is changing. Where it falls the
# slope inside the band falls; where it still rises (the young retiree bands)
# the slope rises. Two independent readings agree no single constant is right -
# the original formula was effectively assuming +0.0009 population-weighted
# (an even split) while individual bands ranged -0.95 to +1.38, and the data
# implies -0.010 population-weighted with a real spread across bands.
#
# `Slope` is kept in the signature for compatibility but no longer sets the
# direction of the tilt; the data does.
# ============================================================================
TILT_CAP <- 0.9   # keeps every weight strictly positive

band_tilt <- function(Collapased, i, j, cap = TILT_CAP) {
  cc <- Collapased[, j]
  if (!is.finite(cc[i]) || cc[i] <= 0) return(0)
  ratios <- c()
  if (i + 1 <= length(cc) && is.finite(cc[i+1]) && cc[i+1] > 0) ratios <- c(ratios, cc[i+1]/cc[i])
  if (i - 1 >= 1        && is.finite(cc[i-1]) && cc[i-1] > 0) ratios <- c(ratios, cc[i]/cc[i-1])
  if (length(ratios) == 0) return(0)
  r <- exp(mean(log(ratios)))
  q <- r^0.8                       # (N-1)/N with N = 5
  s <- (1 - q)/(1 + q)
  max(-cap, min(cap, s))
}

LinearFill <- function(Collapased, Slope = 1, retirement = F) {

  if (retirement) {
    all_age_max <- 120; all_age_min <- 40
    all_serv_max <- 1;  all_serv_min <- 1
    rowmins <- c(40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115)
    colmins <- c(1); colmaxs <- c(1)
  } else {
    all_age_max <- 74; all_age_min <- 20
    all_serv_max <- 54; all_serv_min <- 0
    rowmins <- c(20,25,30,35,40,45,50,55,60,65,70)
    colmins <- c(0,5,10,15,20,25,30,35,40,45,50); colmaxs <- colmins + 4
  }
  rowmaxs <- rowmins + 4
  Expanded <- matrix(0, nrow = all_age_max-all_age_min+1, ncol = all_serv_max-all_serv_min+1)

  for (i in c(1:nrow(Collapased))) {
    rowmin <- rowmins[i]; rowmax <- rowmaxs[i]
    for (j in c(1:ncol(Collapased))) {
      columnmin <- colmins[j]; columnmax <- colmaxs[j]
      N <- rowmax - rowmin + 1
      M <- columnmax - columnmin + 1
      GroupCount <- Collapased[i,j]
      s_band <- band_tilt(Collapased, i, j)

      Share <- matrix(0, nrow = N, ncol = M)
      sharesum <- 0
      for (k in c(1:N)) {
        svcmax <- rowmin + k - all_age_min
        u <- if (N == 1) 0 else (k - 1)/(N - 1)
        w_age <- 1 + s_band * (1 - 2*u)
        for (L in c(1:M)) {
          if ((columnmin + L - 1) > svcmax) { Share[k,L] <- 0 } else { Share[k,L] <- w_age }
          sharesum <- sharesum + Share[k,L]
        }
      }
      if (sharesum != 0) {
        Expanded[((rowmin+1-all_age_min):(rowmax+1-all_age_min)),
                 ((columnmin+1-all_serv_min):(columnmax+1-all_serv_min))] <- Share * GroupCount/sharesum
      }
    }
  }
  Expanded[is.nan(Expanded)] <- 0
  Expanded[is.na(Expanded)]  <- 0
  Expanded
}
