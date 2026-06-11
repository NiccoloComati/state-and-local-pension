
#Maydir <- "/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/"

# import library to read excel sheets
library("readxl")

#Get 10 selected indices info from Bloomberg
#BCOMTR:Bloomberg Commodities total returns
#CRY: Thomson Reuters/CoreCommodity Index
#CRYTR: Thomson Reuters/CoreCommodity Index total returns
#FTAW02: FTSE All World Excluding US
#FTSE: FTSE 100 Index*
#ICELIBOR3Mon: ICE USD LIBOR 3 Mon
#RUSSEL3000: Russel 3000
#SBWGU: Citi World Government Bond Ind
#US00: ICE BoAML US Broad Market Ind
#W1DOW: Dow Jones Global Index

BCOMTR <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/BCOMTR.xlsx", sheet = "BCOMTR", col_names=TRUE)
CRY <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/CRY.xlsx", sheet = "CRY", col_names=TRUE)
CRYTR <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/CRYTR.xlsx", sheet = "CRYTR", col_names=TRUE)
FTAW02 <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/FTAW02.xlsx", sheet = "FTAW02", col_names=TRUE)
FTSE <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/FTSE100.xlsx", sheet = "FTSE", col_names=TRUE)
ICELIBOR3Mon <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/ICELIBOR3Mon.xlsx", sheet = "ICELIBOR3Mon", col_names=TRUE)
Russel3000 <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/RUSSEL3000.xlsx", sheet = "RUSSEL3000", col_names=TRUE)
SBWGU <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/SBWGU.xlsx", sheet = "SBWGU", col_names=TRUE)
US00 <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/US00.xlsx", sheet = "US00", col_names=TRUE)
W1DOW <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/W1DOW.xlsx", sheet = "W1DOW", col_names=TRUE)


#Import OLS estimator for each index
#Theta <- read_excel("/Users/luohouzhu/Library/CloudStorage/OneDrive-MassachusettsInstituteofTechnology/Attachments/Coefficient_Estimates.xlsx", sheet = "Theta", col_names=TRUE)

#Initialize an empty list to store the dictionary structure
asset_dictionary <- list()

#Manually input the OLS estimator data for each index
#Each asset category becomes a list with index names as names for OLS_Coefficient values
asset_dictionary$Equities <- c(Russel3000 = 1.02, ICELIBOR3Mon = -0.042, W1DOW = -1.11, 
                               FTAW02 = 0.86, SBWGU = 0.019, US00 = -0.47)

asset_dictionary$`Fixed Income` <- c(Russel3000 = 0.3, FTSE = 0.12, SBWGU = -0.27, 
                                     BCOMTR = 0.27, CRYTR = -0.11)

asset_dictionary$`Real Estate` <- c(Russel3000 = -3.29, FTSE = 0.45, W1DOW = 7.13, 
                                    SBWGU = -3.3, US00 = -0.7, BCOMTR = 0.19)

asset_dictionary$Cash <- c(Russel3000 = 0.23, FTSE = 0.063)

asset_dictionary$Alternatives <- c(Russel3000 = 0.11, FTSE = 0.25, W1DOW = -0.32, 
                                   SBWGU = 0.6, US00 = -0.38)

asset_dictionary$Other <- c(FTSE = 0.33, BCOMTR = -1.62, CRY = -2.7, CRYTR = 4.14)



#################################################################################################################################
##################################################Computation####################################################################
#################################################################################################################################

#Extract the Date and DailyRtrn columns from each Dataframe
BCOMTR_data <- BCOMTR[, c("Date", "DailyRtrn")]
CRY_data <- CRY[, c("Date", "DailyRtrn")]
CRYTR_data <- CRYTR[, c("Date", "DailyRtrn")]
FTAW02_data <- FTAW02[, c("Date", "DailyRtrn")]
FTSE_data <- FTSE[, c("Date", "DailyRtrn")]
ICELIBOR3Mon_data <- ICELIBOR3Mon[, c("Date", "DailyRtrn")]
Russel3000_data <- Russel3000[, c("Date", "DailyRtrn")]
SBWGU_data <- SBWGU[, c("Date", "DailyRtrn")]
US00_data <- US00[, c("Date", "DailyRtrn")]
W1DOW_data <- W1DOW[, c("Date", "DailyRtrn")]

#Define the start and end dates
start_date <- as.Date("2003-11-24")
end_date <- as.Date("2017-12-31")

#Create a master date frame that spans the specified date range
master_dates <- data.frame(Date = seq(from = start_date, to = end_date, by = "day"))

#Create an empty list to store the aggregated daily returns for each asset category
category_daily_returns <- list()

#Loop over each asset category in the dictionary
for (category in names(asset_dictionary)) {
  #Create an empty data frame to store the weighted daily returns for the current category
  category_data <- merge(master_dates, data.frame(Date = master_dates$Date, DailyReturn = rep(0, nrow(master_dates))), by = "Date")
  
  #Loop over each index within the current asset category
  for (index in names(asset_dictionary[[category]])) {
    #Get the OLS coefficient for the current index
    ols_coefficient <- asset_dictionary[[category]][index]
    
    #Construct the name of the data frame that contains the daily return for the current index
    index_data_name <- paste0(index, "_data")
    
    #Dynamically retrieve the daily returns for the current index
    index_data <- get(index_data_name)
    
    #Ensure 'Date' is in Date format (if not already)
    index_data$Date <- as.Date(index_data$Date)
    
    #Merge the index data with master_dates to align and filter by the specified date range
    aligned_index_data <- merge(master_dates, index_data, by = "Date", all.x = TRUE)
    
    #Replace NA in 'DailyRtrn' with 0 to avoid NA in sum
    aligned_index_data$DailyRtrn[is.na(aligned_index_data$DailyRtrn)] <- 0
    
    #Calculate the weighted daily return for the current index
    weighted_returns <- aligned_index_data$DailyRtrn * ols_coefficient
    
    #Add the weighted daily returns to the category's daily returns
    category_data$DailyReturn <- category_data$DailyReturn + weighted_returns
  }
  
  #Store the aggregated daily returns for the current category in the list
  category_daily_returns[[category]] <- category_data
}

#Print the aggregated daily returns for each asset category
print(category_daily_returns)

#Print the last 10 rows of aggregated daily returns
print(tail(category_daily_returns$Equities,10))

#################################################################################################################################
###########################################Outputting the variance-covariance matrix#############################################
#################################################################################################################################

#Combine the daily returns into a single data frame & Crate a dataframe for combined returns
combined_returns <- data.frame(Date = category_daily_returns[[1]]$Date)

#Add each category's daily returns as a new column
for(category in names(category_daily_returns)) {
  combined_returns[[category]] <- category_daily_returns[[category]]$DailyReturn
}

#Drop the 'Date' column for variance-covariance calculation
combined_returns <- combined_returns[,-1]

#Calculate the variance-covariance matrix
matrix_fed <- cov(combined_returns, use = "pairwise.complete.obs")

#Print the variance-covariance matrix
print(matrix_fed)

scaled_matrix_fed <- round(matrix_fed * 10^4, digits = 2)
print(scaled_matrix_fed)
