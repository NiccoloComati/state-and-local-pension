
library(ggplot2)
library(readxl)





DSdir <- "/data/smithafe/Pension_CF_Model/"
#DSdir <- "/data/smithafe/Pension_CF_Model/"
#DSdir <- "/Users/tanyaratra/Desktop/Tanya_Ratra/Fall2023/RA/State Pension Model"

# set the proper working directory
setwd(DSdir)


graph_years <- 15


plans <- c("CA10","AZ127","DC20","IL33","MA50","NY78","AZ06","CA111",
           "IL32","LA130","CA43","CA97","CA98","FL26","GA27","GA28",
           "IL34","IN37","LA44","LA163","ME47","MI53","CA144","MO175","ND82",
           "NJ71","NJ73","NM74","NY83","OK134","OR91","PA92",
           "PA93","RI96","SC100","SC99","TX108")


actual_data_all <- data.frame(fy =c(2001:2021), fr=0 ) 

forecast_data_all <- data.frame(fy  = seq(2017, by=1 , length.out=graph_years), Forecast=0,
                                Lo80=0, Hi80=0,Lo95=0,Hi95=0) 

for (i_loop in c(1:length(plans))){
  
  plan <- plans[[i_loop]]
  
  load(paste0(plan,"/",plan,"_AssetSim",".RData"))
  
  



#Get plan info
planinfo <- read_excel("Common_Data/ppd-data-latest.xlsx", sheet = "ppd-data-latest", col_names=TRUE)

planinfo <- planinfo[planinfo$ppd_id==ppid ,]



actual_data <- planinfo[planinfo$fy>2000,c("fy","ActAssets_GASB","ActLiabilities_GASB")]


actual_data$fr <- actual_data$ActAssets_GASB/actual_data$ActLiabilities_GASB




# Your actual time series data
#actual_data <- data.frame(Date = as.Date('2000-01-01') + seq(0, by = 3, length.out = 100),
#                          Value = rnorm(100, mean = 100, sd = 5))




all_forecast <-  Assets[1:graph_years,] / AAL[1:graph_years,] 

forcast_mean <- apply(all_forecast, 1, mean)

#all_forecast[all_forecast > 1.2] <- 1.2 



forecast_data <- data.frame(fy = seq(2017, by=1 , length.out=graph_years),
                            Forecast=forcast_mean,
                            Lo80 = apply(all_forecast, 1,  quantile, probs = .2),
                            Hi80= apply(all_forecast, 1,  quantile, probs = 0.8),
                            Lo95 = apply(all_forecast, 1,  quantile, probs = 0.05),
                            Hi95= apply(all_forecast, 1,  quantile, probs = .95))



# Your forecasted data, which includes the forecast and its lower and upper confidence intervals
#forecast_data <- data.frame(Date = as.Date('2000-01-01') + seq(300, by = 3, length.out = 20),
#                            Forecast = rnorm(20, mean = 100, sd = 5),
#                            Lo80 = rnorm(20, mean = 95, sd = 5),
#                            Hi80 = rnorm(20, mean = 105, sd = 5),
#                            Lo95 = rnorm(20, mean = 90, sd = 5),
#                            Hi95 = rnorm(20, mean = 110, sd = 5))


actual_data_all$fr <- actual_data_all$fr + (1/length(plans))*actual_data$fr

forecast_data_all$Forecast <- forecast_data_all$Forecast + (1/length(plans))*forecast_data$Forecast

forecast_data_all$Lo80 <- forecast_data_all$Lo80 + (1/length(plans))*forecast_data$Lo80

forecast_data_all$Lo95 <- forecast_data_all$Lo95 + (1/length(plans))*forecast_data$Lo95

forecast_data_all$Hi80 <- forecast_data_all$Hi80 + (1/length(plans))*forecast_data$Hi80

forecast_data_all$Hi95 <- forecast_data_all$Hi95 + (1/length(plans))*forecast_data$Hi95

}


# Base plot with actual data
p <- ggplot() + 
  geom_line(data = actual_data_all, aes(x = fy, y = fr), colour = "black")

# Add the forecast line
p <- p + geom_line(data = forecast_data_all, aes(x = fy, y = Forecast), colour = "blue")

# Add the confidence intervals with `geom_ribbon`
p <- p + geom_ribbon(data = forecast_data_all, aes(x = fy, ymin = Lo95, ymax = Hi95), alpha = 0.1) # 95% CI
p <- p + geom_ribbon(data = forecast_data_all, aes(x = fy, ymin = Lo80, ymax = Hi80), alpha = 0.2) # 80% CI

# Labels and theme
p <- p + labs(title = "Forecasted Funding Ratio",
              x = "Fiscal Year",
              y = "Funding Ratio") +
  theme_minimal()

# Print the plot
ggsave("Results/Output/Forecast_Plots/forecast_plot_avg.pdf", plot = p, width = 10, height = 6, dpi = 300)


