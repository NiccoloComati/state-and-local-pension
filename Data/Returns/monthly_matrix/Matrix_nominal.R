dir <- "/Users/luohouzhu/Library/CloudStorage/OneDrive-SharedLibraries-MassachusettsInstituteofTechnology/MIT Golub Center for Finance and Policy - Documents/Research and Education/Projects/State and Local Pension/MonthlyData/"
setwd(dir)

# import library to read excel sheets
library("readxl")

#Retrieve selected index data from Bloomberg
#Equities: SPX Index (S&P500 Index) - 02/27/1970
#Fixed Income: LBUSTRUU Index (Bloomberg US Agg Total Return Value Unhedged USD Index) - 01/30/1976
#Alternatives: SPLPEQTY Index (S&P Listed Private Equity Index) - 11/28/2003
#Cash: SPUSBUS Index (S&P U.S. Ultra Short Treasury Bill & Bond Index) - 10/31/2011
#Real Estate: (1) Debt - FNMR Index (FTSE NAREIT Mortgage REITS); (2) Equity - FNRE Index (FTSE NAREIT Equity REITS) - 02/29/1972

Equities <- read_excel(paste0(dir,"Equities.xlsx"),sheet = "Equities", col_names=TRUE)
Fixed_Income <- read_excel(paste0(dir,"Fixed Income.xlsx"),sheet = "Fixed_Income", col_names=TRUE)
Alternatives_PE <- read_excel(paste0(dir,"Alternatives.xlsx"),sheet = "Alternatives", col_names=TRUE)
Cash <- read_excel(paste0(dir,"Cash.xlsx"),sheet = "Cash", col_names=TRUE)
RE_Debt <- read_excel(paste0(dir,"RE Debt.xlsx"),sheet = "Real_Estate_D", col_names=TRUE)
RE_Equity <- read_excel(paste0(dir,"RE Equity.xlsx"),sheet = "Real_Estate_E", col_names=TRUE)

#################################################### Data Processing ##############################################################

#Renaming monthly return columns for clarity
names(Equities)[names(Equities) == "Return"] <- "Equities_MonthlyRtrn"
names(Fixed_Income)[names(Fixed_Income) == "Return"] <- "FI_MonthlyRtrn"
names(Alternatives_PE)[names(Alternatives_PE) == "Return"] <- "Alternatives_PE_MonthlyRtrn"
names(Cash)[names(Cash) == "Return"] <- "Cash_MonthlyRtrn"
names(RE_Debt)[names(RE_Debt) == "Return"] <- "RE_MonthlyRtrn_Debt"
names(RE_Equity)[names(RE_Equity) == "Return"] <- "RE_MonthlyRtrn_Equity"

#Calculate monthly return for real estate by putting in equal weight on debt & equity
RE_data <- merge(RE_Debt, RE_Equity, by = "Date", all = TRUE)
RE_data <- RE_data[order(RE_data$Date, decreasing = TRUE), ]
RE_data$RE_MonthlyRtrn <- 0.5 * RE_data$RE_MonthlyRtrn_Debt + 0.5 * RE_data$RE_MonthlyRtrn_Equity

#Extract the Date and Monthly Return columns from each Dataframe
Equities_data <- Equities[, c("Date", "Equities_MonthlyRtrn")]
FI_data <- Fixed_Income[, c("Date", "FI_MonthlyRtrn")]
Alternatives_PE_data <- Alternatives_PE[, c("Date", "Alternatives_PE_MonthlyRtrn")]
Cash_data <- Cash[, c("Date", "Cash_MonthlyRtrn")]
RE_data <- RE_data[, c("Date", "RE_MonthlyRtrn")]

#Convert Date format
Equities_data$Date <- as.Date(Equities_data$Date)
FI_data$Date <- as.Date(FI_data$Date)
Alternatives_PE_data$Date <- as.Date(Alternatives_PE_data$Date)
Cash_data$Date <- as.Date(Cash_data$Date)
RE_data$Date <- as.Date(RE_data$Date)

####################################################### Computation ##################################################################

#Start date using the earliest date that the Equities data can be traced 
start_date <- as.Date("1970-02-27")
end_date <- as.Date("2017-12-31")

#Filtering date for each asset category
Equities_data <- Equities_data[Equities_data$Date >= start_date & Equities_data$Date <= end_date, ]
FI_data <- FI_data[FI_data$Date >= start_date & FI_data$Date <= end_date, ]
Alternatives_PE_data <- Alternatives_PE_data[Alternatives_PE_data$Date >= start_date & Alternatives_PE_data$Date <= end_date, ]
Cash_data <- Cash_data[Cash_data$Date >= start_date & Cash_data$Date <= end_date, ]
RE_data <- RE_data[RE_data$Date >= start_date & RE_data$Date <= end_date, ]

#Merge the data sets into one
returns <- Reduce(function(x, y) merge(x, y, by = "Date", all = TRUE), 
                      list(Equities_data, FI_data, Alternatives_PE_data, Cash_data, RE_data))

#Remove the 'Date' column as it's not needed for the variance-covariance matrix
returns <- returns[, -1]

#Calculate variance-covariance matrix using all complete pairs of observations (ignoring NA values due to missing data on some days)
matrix_nominal <- cov(returns, use = "pairwise.complete.obs")

print(matrix_nominal)

################################################# Matrix Analysis #####################################################################
#assuming 12 months
Nmonth <- 12

#Scale the variance-covariance matrix to basis points (10^4)
scaled_matrix <- round(matrix_nominal * 10^4, digits = 2)
print(scaled_matrix)

#Make the matrix yearly
yearly_matrix <- Nmonth * matrix_nominal
print(yearly_matrix)

#Yearly matrix in basis points
scaled_yearly_matrix <- round(yearly_matrix * 10^4, digits = 2)
print(scaled_yearly_matrix)

#Calculate mean return for each asset category
Equities_mean <- mean(returns$Equities_MonthlyRtrn, na.rm = TRUE)
FI_mean <- mean(returns$FI_MonthlyRtrn, na.rm = TRUE)
Alternatives_PE_mean <- mean(returns$Alternatives_PE_MonthlyRtrn, na.rm = TRUE)
Cash_mean <- mean(returns$Cash_MonthlyRtrn, na.rm = TRUE)
RE_mean <- mean(returns$RE_MonthlyRtrn, na.rm = TRUE)

monthly_mean_returns <- c(Equities_monthly_mean = Equities_mean, 
                         FI_monthly_mean = FI_mean, 
                         Alternatives_PE_monthly_mean = Alternatives_PE_mean, 
                         Cash_monthly_mean = Cash_mean, 
                         RE_monthly_mean = RE_mean)
monthly_mean_returns <- round(monthly_mean_returns, 5)
print(monthly_mean_returns)

annual_mean_returns <- Nmonth * monthly_mean_returns
col_names <- c("Equities_annual_mean", "FI_annual_mean", "Alternatives_PE_annual_mean", "Cash_annual_mean", "RE_annual_mean")
names(annual_mean_returns) <- col_names
print(annual_mean_returns)

#Extract the diagonal elements (variances)
variances <- diag(matrix_nominal)

#Calculate monthly standard deviation in percentages for each asset category
monthly_stdev <- sqrt(variances)
monthly_stdev_percentage <- paste0(round(monthly_stdev * 100, 2), "%")
col_names_1 <- c("Equities_monthly_stdev", "FI_monthly_stdev", "Alternatives_PE_monthly_stdev", "Cash_monthly_stdev", "RE_monthly_stdev")
names(monthly_stdev_percentage) <- col_names_1

#Calculate the annual standard deviation in percentages assuming 12 months
annual_stdev <- sqrt(Nmonth) * monthly_stdev
annual_stdev_percentage <- paste0(round(annual_stdev * 100, 2), "%")
col_names_2 <- c("Equities_annual_stdev", "FI_annual_stdev", "Alternatives_PE_annual_stdev", "Cash_annual_stdev", "RE_annual_stdev")
names(annual_stdev_percentage) <- col_names_2
print(annual_stdev_percentage)

#Calculate the correlation matrix for the returns
correlation_nominal <- cor(returns[,c("Equities_MonthlyRtrn", "FI_MonthlyRtrn", "Alternatives_PE_MonthlyRtrn", "Cash_MonthlyRtrn", "RE_MonthlyRtrn")], use = "pairwise.complete.obs")
print(correlation_nominal)

################################################### Data Output #######################################################################
library(openxlsx)

#Create a new workbook
wb <- createWorkbook()

#Add sheets and write data to each sheet
addWorksheet(wb, "Nominal Matrix")
writeData(wb, "Nominal Matrix", matrix_nominal)
addWorksheet(wb, "Scaled Matrix")
writeData(wb, "Scaled Matrix", scaled_matrix)
addWorksheet(wb, "Yearly Matrix")
writeData(wb, "Yearly Matrix", yearly_matrix)
addWorksheet(wb, "Scaled Yearly Matrix")
writeData(wb, "Scaled Yearly Matrix", scaled_yearly_matrix)
addWorksheet(wb, "Annual Mean Returns")
writeData(wb, "Annual Mean Returns", as.data.frame(annual_mean_returns))
addWorksheet(wb, "Annual Stdev Percentage")
writeData(wb, "Annual Stdev Percentage", as.data.frame(annual_stdev_percentage))
addWorksheet(wb, "Correlation Coefficient")
writeData(wb, "Correlation Coefficient", as.data.frame(correlation_nominal))

#Save the workbook
saveWorkbook(wb, "/Users/luohouzhu/Desktop/NominalResults.xlsx", overwrite = TRUE)

############################################ Time Period Analysis #####################################################################
if (FALSE){
start_date <- as.Date("2017-12-31")
end_date <- as.Date("2024-03-14")

#Filtering date for each asset category
Equities_data <- Equities_data[Equities_data$Date >= start_date & Equities_data$Date <= end_date, ]
FI_data <- FI_data[FI_data$Date >= start_date & FI_data$Date <= end_date, ]
Alternatives_PE_data <- Alternatives_PE_data[Alternatives_PE_data$Date >= start_date & Alternatives_PE_data$Date <= end_date, ]
Cash_data <- Cash_data[Cash_data$Date >= start_date & Cash_data$Date <= end_date, ]
RE_data <- RE_data[RE_data$Date >= start_date & RE_data$Date <= end_date, ]

#Merge the datasets into one
returns <- Reduce(function(x, y) merge(x, y, by = "Date", all = TRUE), 
                  list(Equities_data, FI_data, Alternatives_PE_data, Cash_data, RE_data))

#Remove the 'Date' column as it's not needed for the variance-covariance matrix
returns <- returns[, -1]

#Calculate variance-covariance matrix using all complete pairs of observations (ignoring NA values due to missing data on some days)
matrix1 <- cov(returns, use = "pairwise.complete.obs")

# View the variance-covariance matrix
print(matrix1)

}