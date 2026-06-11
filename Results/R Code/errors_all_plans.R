

plans <- c("CA10","AZ127","DC20","IL33","MA50","NY78","AZ06","CA111",
"IL32","LA130","CA43","CA97","CA98","FL26","GA27","GA28",
"IL34","IN37","LA44","LA163","ME47","MI53","CA144","MO175","ND82",
"NJ71","NJ73","NM74","NY83","OH88","OK134","OR91","PA92",
"PA93","RI96","SC100","SC99","TX108")

result <- data.frame(plan=character(), EAN=double(),PVFB=double(),
                     Retirement=double(),Inactive=double())




for (i_loop in c(1:length(plans))){
  
plan <- plans[[i_loop]]

load(paste0("/mmfs1/data/smithafe/Pension_CF_Model/",plan,"/",plan,"_Compare_02152024_best.RData"))




result[i_loop,1] <- plan
result[i_loop,2] <- (CAFR_AAL-Model_AAL)/Model_AAL*100
result[i_loop,3] <-  Compare_Result[2,4]*100
result[i_loop,4] <-  Compare_Result[3,4]*100
result[i_loop,5] <-  Compare_Result[4,4]*100


}

mean(result$EAN)


write.csv(result,"Results/Output/plan_errors.csv",row.names = F,na = "")