library(xtable)


#Load data used to create tables

load(file = "PA93/Data/PA93_09252023.RData")

#Create table comparing


planinfo <- read_excel("../../Data/Common/states/ppd-data-latest.xlsx", sheet = "ppd-data-latest", col_names=TRUE)


planinfo <- planinfo[planinfo$ppd_id==ppid,]


realized_fr <- data.frame(year=numeric(),realized_fr=numeric(),model_fr=numeric(),stringsAsFactors = F)

count <- 1
for (i in c(plan_year:max(planinfo$fy,na.rm=T))){
  
  realized_fr[count,"year"] <- i 
  
  realized_fr[count,"realized_fr"] <- planinfo[planinfo$fy==i,"ActAssets_GASB"] /
    planinfo[planinfo$fy==i,"ActLiabilities_GASB"] 
  
  
  realized_fr[count,"model_fr"] <- rowMeans(Assets)[count]/ AAL[count,1] 
  
  
  count <- count + 1 
  
}



print(xtable(realized_fr, type = "latex",digits=c(0,0,3,3)),include.rownames=FALSE)



