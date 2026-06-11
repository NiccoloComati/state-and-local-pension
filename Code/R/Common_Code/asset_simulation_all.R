current_dir <- "/nfs/sloanlab007/projects/pension_cf_model_proj/Pension_CF_Model/"

# set the proper working directory
setwd(current_dir)

plans <- c("CA10","AZ127","DC20","IL33","MA50","NY78","AZ06","CA111",
           "IL32","LA130","CA43","CA97","CA98","FL26","GA27","GA28",
           "IL34","IN37","LA44","LA163","ME47","MI53","CA144","MO175","ND82",
           "NJ71","NJ73","NM74","NY83","OK134","OR91","PA92",
           "PA93","RI96","SC100","SC99","TX108")

for (i_loop in c(1:length(plans))){
  
plan <- plans[[i_loop]]
  
  
#load cash flow data
load(paste0(plan,"/",plan,"_Compare_02152024_best.RData"))
  

date_run <- "05312024_best"



#Amortize payments or constant percent of wages
Amortize <- F
#period over which to amortize
Amotorize_Period <- 30

Nasset <-2

#number of simulations to do
num_sim <- 10000

#Right now the Cash-flows can be duplicated between columns because
#there is no stochastic elements on the liability side
Assets <- matrix(Assets,nrow = nrow(Assets),ncol = num_sim)
AAL <- matrix(AAL,nrow = nrow(AAL),ncol = num_sim)
cash_inflows <- matrix(cash_inflows,nrow = nrow(cash_inflows),ncol = num_sim)
cash_outflows <- matrix(cash_outflows,nrow = nrow(cash_outflows),ncol = num_sim)


## (STATIC) Nominal expected returns for stocks, bonds
ExpRet <- c(0.075+Inflation, rf)

## (STATIC)Standard deviations (volatility) for stocks, bonds
SD <- c(0.20,0)

# Start of Monte Carlo Loop
for (n in 1:num_sim) {
  
  for (t in 1:(Nyear-1)) {
    
    # Generate current year's returns ------------------------------
    stock_normal_shock <- rnorm(1,mean=ExpRet[[1]],sd=SD[[1]])
    
    bond_normal_shock <- rnorm(1,mean=ExpRet[[2]],sd=SD[[2]])
    
    returns <- c(stock_normal_shock,bond_normal_shock)
    
    AnnualRet <- 0
    ret <- c(Nasset)
    for (i in 1:Nasset) {
      ret[i] <- returns[i]
      AnnualRet <- AnnualRet + AssetShare[i] * ret[i]
    }
    
    funding_ratio <- (Assets[t,n])/AAL[t,n]
    
    if(funding_ratio>1){
      
      contribution <-0  
      
    }else{
      
      if(Amortize){
        
        UAAL <-  AAL[t,n]-Assets[t,n]
        
        contribution <- NormalCost[t,1]+max(0,UAAL*(discountrate*
                                              (1+discountrate)^Amotorize_Period)/
                                      (((1+discountrate)^Amotorize_Period)-1))
        
        
      }else{
        
        contribution <- cash_inflows[t,n]
        
      }
      
    }
    
    Assets[t+1,n] <- Assets[t,n]*(1+AnnualRet)-cash_outflows[t,n]+contribution
    
    if(Assets[t+1,n] <0 ){
      
      Assets[t+1,n] <- 0
      next
      
    }
    
    
  }
  
}


save.image(file = paste0(plan,"/",plan,"_AssetSim",date_run,".RData"))



}
