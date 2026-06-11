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

################################################### Data Processing ##############################################################

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
Equities_M <- Equities[, c("Date", "Equities_MonthlyRtrn")]
FI_M <- Fixed_Income[, c("Date", "FI_MonthlyRtrn")]
Alternatives_PE_M <- Alternatives_PE[, c("Date", "Alternatives_PE_MonthlyRtrn")]
Cash_M <- Cash[, c("Date", "Cash_MonthlyRtrn")]
RE_M <- RE_data[, c("Date", "RE_MonthlyRtrn")]

#Import monthly CPI data
CPI <- read_excel(paste0(dir,"CPI.xlsx"),sheet = "CPI", col_names=TRUE)

#Create a mapping of month names to month numbers
months_map <- setNames(as.character(1:12), tolower(month.name))

#Convert month names in 'Period' to month numbers, using the mapping
CPI$Month <- as.numeric(months_map[tolower(CPI$Period)])

#Create a unified Date column by pasting Year, Month, and setting Day to "01"
CPI$Date <- as.Date(paste(CPI$Year, CPI$Month, "01", sep = "-"))
names(CPI)[names(CPI) == "Over-the-Month Percent Change"] <- "CPI_Rate"
CPI_data <- CPI[, c("Date", "CPI_Rate")]

#Convert Date format for each asset category & Normalize Date to the first of the month
Equities_M$Date <- as.Date(format(Equities_M$Date, "%Y-%m-01"))
FI_M$Date <- as.Date(format(FI_M$Date, "%Y-%m-01"))
Alternatives_PE_M$Date <- as.Date(format(Alternatives_PE_M$Date, "%Y-%m-01"))
Cash_M$Date <- as.Date(format(Cash_M$Date, "%Y-%m-01"))
RE_M$Date <- as.Date(format(RE_M$Date, "%Y-%m-01"))

####################################################### Computation ##################################################################

#start date using the earliest date that the Alternatives data can be traced
start_date <- as.Date("1970-02-01")
end_date <- as.Date("2017-12-01")

#Filtering date for each asset category
Equities_M <- Equities_M[Equities_M$Date >= start_date & Equities_M$Date <= end_date, ]
FI_M <- FI_M[FI_M$Date >= start_date & FI_M$Date <= end_date, ]
Alternatives_PE_M <- Alternatives_PE_M[Alternatives_PE_M$Date >= start_date & Alternatives_PE_M$Date <= end_date, ]
Cash_M <- Cash_M[Cash_M$Date >= start_date & Cash_M$Date <= end_date, ]
RE_M <- RE_M[RE_M$Date >= start_date & RE_M$Date <= end_date, ]
CPI_M <- CPI_data[CPI_data$Date >= start_date & CPI_data$Date <= end_date, ]

#Merge the datasets into one
nominal_returns <- Reduce(function(x, y) merge(x, y, by = "Date", all = TRUE), 
                  list(Equities_M, FI_M, Alternatives_PE_M, Cash_M, RE_M, CPI_M))

#Create a new dataframe for real returns
Real_return <- data.frame(
  Real_Equities_Rtrn = nominal_returns$Equities_MonthlyRtrn - nominal_returns$CPI_Rate,
  Real_FI_Rtrn = nominal_returns$FI_MonthlyRtrn - nominal_returns$CPI_Rate,
  Real_Alternatives_PE_Rtrn = nominal_returns$Alternatives_PE_MonthlyRtrn - nominal_returns$CPI_Rate,
  Real_Cash_Rtrn = nominal_returns$Cash_MonthlyRtrn - nominal_returns$CPI_Rate,
  Real_RE_Rtrn = nominal_returns$RE_MonthlyRtrn - nominal_returns$CPI_Rate
)

#Calculate variance-covariance matrix using all complete pairs of observations (ignoring NA values due to missing data on some days)
matrix_real <- cov(Real_return, use = "pairwise.complete.obs")

print(matrix_real)

################################################# Matrix Analysis #####################################################################
#assuming 12 months
Nmonth <- 12

#Scale the variance-covariance matrix to basis points (10^4)
scaled_matrix_real <- round(matrix_real * 10^4, digits = 2)
print(scaled_matrix_real)

#Make the matrix yearly
yearly_matrix_real <- Nmonth * matrix_real
print(yearly_matrix_real)

#Yearly matrix in basis points
scaled_yearly_matrix_real <- round(yearly_matrix_real * 10^4, digits = 2)
print(scaled_yearly_matrix_real)

#Calculate real mean return for each asset category
Equities_mean_real <- mean(Real_return$Real_Equities_Rtrn, na.rm = TRUE)
FI_mean_real <- mean(Real_return$Real_FI_Rtrn, na.rm = TRUE)
Alternatives_PE_mean_real <- mean(Real_return$Real_Alternatives_PE_Rtrn, na.rm = TRUE)
Cash_mean_real <- mean(Real_return$Real_Cash_Rtrn, na.rm = TRUE)
RE_mean_real <- mean(Real_return$Real_RE_Rtrn, na.rm = TRUE)

real_monthly_mean_returns <- c(Equities_monthly_mean_real = Equities_mean_real, 
                        FI_monthly_mean_real = FI_mean_real, 
                        Alternatives_PE_monthly_mean_real = Alternatives_PE_mean_real, 
                        Cash_monthly_mean_real = Cash_mean_real, 
                        RE_monthly_mean_real = RE_mean_real)
real_monthly_mean_returns <- round(real_monthly_mean_returns, 5)
print(real_monthly_mean_returns)

annual_mean_returns_real <- Nmonth * real_monthly_mean_returns
col_names_3 <- c("Equities_annual_mean", "FI_annual_mean", "Alternatives_PE_annual_mean", "Cash_annual_mean", "RE_annual_mean")
names(annual_mean_returns_real) <- col_names_3
print(annual_mean_returns_real)

#Extract the diagonal elements (variances)
variances_real <- diag(matrix_real)

#Calculate monthly standard deviation in percentages for each asset category
monthly_stdev_real<- sqrt(variances_real)
monthly_stdev_percentage_real <- paste0(round(monthly_stdev_real * 100, 2), "%")
col_names_4 <- c("Equities_monthly_stdev", "FI_monthly_stdev", "Alternatives_PE_monthly_stdev", "Cash_monthly_stdev", "RE_monthly_stdev")
names(monthly_stdev_percentage_real) <- col_names_4

#Calculate the annual standard deviation in percentages assuming 12 months
annual_stdev_real <- sqrt(Nmonth) * monthly_stdev_real
annual_stdev_percentage_real <- paste0(round(annual_stdev_real * 100, 2), "%")
col_names_5 <- c("Equities_annual_stdev", "FI_annual_stdev", "Alternatives_PE_annual_stdev", "Cash_annual_stdev", "RE_annual_stdev")
names(annual_stdev_percentage_real) <- col_names_5
print(annual_stdev_percentage_real)

#Calculate the correlation matrix for the returns
correlation_real <- cor(Real_return, use = "pairwise.complete.obs")
print(correlation_real)

save(correlation_real, file = paste0(dir,"correlation_matrix.RData"))

################################################### Data Output #######################################################################
library(openxlsx)

output_file <- "/Users/luohouzhu/Desktop/NominalResults.xlsx"
wb <- loadWorkbook(output_file)

addWorksheet(wb, "Real Matrix")
writeData(wb, "Real Matrix", matrix_real)
addWorksheet(wb, "Scaled Matrix Real")
writeData(wb, "Scaled Matrix Real", scaled_matrix_real)
addWorksheet(wb, "Yearly Matrix Real")
writeData(wb, "Yearly Matrix Real", yearly_matrix_real)
addWorksheet(wb, "Scaled Yearly Matrix Real")
writeData(wb, "Scaled Yearly Matrix Real", scaled_yearly_matrix_real)
addWorksheet(wb, "Annual Mean Returns Real")
writeData(wb, "Annual Mean Returns Real", as.data.frame(annual_mean_returns_real))
addWorksheet(wb, "Annual Stdev Percentage Real")
writeData(wb, "Annual Stdev Percentage Real", as.data.frame(annual_stdev_percentage_real))
addWorksheet(wb, "Correlation Coefficient Real")
writeData(wb, "Correlation Coefficient Real", as.data.frame(correlation_real))

# Save the workbook
saveWorkbook(wb, output_file, overwrite = TRUE)
