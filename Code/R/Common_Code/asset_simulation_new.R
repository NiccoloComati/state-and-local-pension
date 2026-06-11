library(readxl)

current_dir <- "/nfs/sloanlab007/projects/pension_cf_model_proj/Pension_CF_Model/"


#Set the proper working directory
setwd(current_dir)


plan <- "CA10"

fileName <- "CA10_Compare_03062024_Adj.RData"

planFolder <- paste0(plan,"/")

#Plan Number
ppdid <- 10

#Plan Year
plan_year <- 2017

#Get plan info
planinfo <- read_excel("../../Data/Common/states/ppd-data-latest.xlsx", sheet = "ppd-data-latest", col_names=TRUE)

planinfo <- planinfo[planinfo$ppd_id==ppdid & planinfo$fy == plan_year,]

#Find corresponding inflation ratess
Inflation_rate <- planinfo$InflationAssumption_GASB



#Load cash-flow data
load(file = paste0(planFolder,fileName))

#Import real returns
load(file = "Returns/correlation_matrix.RData")

#Amortize payments or constant percent of wages
Amortize <- F
#period over which to amortize
Amortize_Period <- 30

#number of simulations to do
num_sim <- 10000

#Right now the Cash-flows can be duplicated between columns because
#there is no stochastic elements on the liability side
Assets <- matrix(Assets,nrow = nrow(Assets),ncol = num_sim)
AAL <- matrix(AAL,nrow = nrow(AAL),ncol = num_sim)
cash_inflows <- matrix(cash_inflows,nrow = nrow(cash_inflows),ncol = num_sim)
cash_outflows <- matrix(cash_outflows,nrow = nrow(cash_outflows),ncol = num_sim)

#Calculate the variance-covariance matrix using the correlation matrix and suggested volatility for each asset category
suggested_expret <- c(Equities = 0.05, FI = 0.01, Alternatives_PE = 0.05, Cash = 0.0, RE = 0.03)
suggested_volatility <- c(Equities = 0.15, FI = 0.0559, Alternatives_PE = 0.15, Cash = 0.0, RE = 0.08)

#Names for correlation matrix
dimnames(correlation_real) <- list(c("Equities", "FI", "Alternatives_PE", "Cash", "RE"),
                                     c("Equities", "FI", "Alternatives_PE", "Cash", "RE"))

#Calculate the variance-covariance matrix
var_cov_matrix <- matrix(nrow = 5, ncol = 5)
for (i in 1:5) {
  for (j in 1:5) {
    var_cov_matrix[i, j] <- correlation_real[i, j] * suggested_volatility[i] * suggested_volatility[j]
  }
}

#Set row and column names
dimnames(var_cov_matrix) <- dimnames(correlation_real)

var_cov_matrix <- round(var_cov_matrix,5)

#Import MASS package to simulate multivariate normal distributions
library(MASS)

set.seed(514654)

r_shocks <- matrix(0,nrow=nrow(Assets),ncol = ncol(Assets))

n_shocks <- matrix(0,nrow=nrow(Assets),ncol = ncol(Assets))

all_shocks <- matrix(0,nrow=nrow(Assets)*ncol(Assets),ncol = 5)


#Sum asset classes
total_equity <- planinfo$EQTotal_Actl

total_fi <- planinfo$FITotal_Actl

total_cash <- planinfo$CashTotal_Actl

total_alt <- planinfo$HFTotal_Actl + planinfo$COMDTotal_Actl+ planinfo$PETotal_Actl+
  planinfo$AltMiscTotal_Actl+planinfo$OtherTotal_Actl

total_re <- planinfo$RETotal_Actl

AssetShare <- c(total_equity,total_fi,total_alt,total_cash,total_re)

count<-1

#Start of Monte Carlo Loop
for (n in 1:num_sim) {
  
  for (t in 1:(Nyear-1)) {
   
    #real return: Generate current year's real returns for all asset categories ------------------------------
    shocks <- mvrnorm(n=1, mu=suggested_expret, Sigma=var_cov_matrix)
    
    #Calculate the portfolio's annual return based on the simulated shocks and asset weights
    AnnualRealRet <- sum(AssetShare * shocks)
    AnnualNominalRet <- (1+AnnualRealRet)*(1+Inflation_rate) - 1
    
    
    r_shocks[t,n] <- AnnualRealRet
    
    n_shocks[t,n] <- AnnualNominalRet
    
    all_shocks[count,] <- shocks
    
    count <- count+1
    
    #AAL -  actuarial accrued liabilities
    #Funding ratio - compares the current assets to the actuarial accrued liabilities.
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
    
    Assets[t+1,n] <- Assets[t,n]*(1+AnnualNominalRet)-cash_outflows[t,n]+contribution
    
    if(Assets[t+1,n] <0 ){
      
      Assets[t+1,n] <- 0
      next
      
    }
    
    
  }
  
}


graph <-34

#remove last observation
funding_ratio <- Assets[1:graph,] / AAL[1:graph,]
funding_ratio_mean <- apply(funding_ratio, 1, mean)

#all_forecast[all_forecast > 1.2] <- 1.2 


funding_ratio_output <- data.frame(fy = seq(2017, by=1 , length.out=graph),
                            Forecast=funding_ratio_mean,
                            Sd = apply(funding_ratio, 1,  sd),
                            Median = apply(funding_ratio, 1,  quantile, probs = .5),
                            Lo80 = apply(funding_ratio, 1,  quantile, probs = .2),
                            Hi80= apply(funding_ratio, 1,  quantile, probs = 0.8),
                            Lo95 = apply(funding_ratio, 1,  quantile, probs = 0.05),
                            Hi95= apply(funding_ratio, 1,  quantile, probs = .95))


write.csv(funding_ratio_output,"CA10_Asset_Sim.csv",row.names = F)
