DSdir <- "/home/dan/PhD/Pension_CF_Model/"
#DSdir <- "/data/smithafe/Pension_CF_Model/"
#DSdir <- "/Users/tanyaratra/Desktop/Tanya_Ratra/Fall2023/RA/State Pension Model"
plan <- "CA10"

fileName <- "CA10_Compare_01102024.RData"

# set the proper working directory
setwd(DSdir)


planFolder <- paste0(plan,"/")

#load cash-flow data
load(file = paste0(planFolder,fileName))


#Amortize payments or constant percent of wages
Amortize <- F
#period over which to amortize
Amtorize_Period <- 30

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

graph_years <-34

#remove last observation
funding_ratio <-   Assets[1:graph_years,] / AAL[1:graph_years,] 


funding_ratio_mean <- apply(funding_ratio, 1, mean)

#all_forecast[all_forecast > 1.2] <- 1.2 


funding_ratio <- data.frame(fy = seq(2017, by=1 , length.out=graph_years),
                            Forecast=funding_ratio_mean,
                            Sd = apply(funding_ratio, 1,  sd),
                            Median = apply(funding_ratio, 1,  quantile, probs = .5),
                            Lo80 = apply(funding_ratio, 1,  quantile, probs = .2),
                            Hi80= apply(funding_ratio, 1,  quantile, probs = 0.8),
                            Lo95 = apply(funding_ratio, 1,  quantile, probs = 0.05),
                            Hi95= apply(funding_ratio, 1,  quantile, probs = .95))





