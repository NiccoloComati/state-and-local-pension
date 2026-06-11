#!/usr/bin/env Rscript
# Patches Percent_difference in existing detAL RData files to use
# the canonical formula: (Model_AAL - CAFR_AAL) / CAFR_AAL
# Run from project root: Rscript "Cluster Code/cluster_062026/Common_Code/patch_percent_difference.R"

plans <- c("AZ06","AZ127","CA10","CA111","CA144","CA43","CA97","CA98",
           "DC20","FL26","GA27","GA28","IL32","IL33","IL34","IN37",
           "LA130","LA163","LA44","ME47")

run_tag  <- "062026"
run_dir  <- file.path("Results", "Runs", run_tag)

for (plan in plans) {
  rdata <- file.path(run_dir, plan, paste0(plan, "_detAL_2022_", run_tag, ".RData"))
  if (!file.exists(rdata)) {
    cat("SKIP (not found):", plan, "\n"); next
  }
  e <- new.env()
  load(rdata, envir = e)
  if (!exists("Model_AAL", envir = e) || !exists("CAFR_AAL", envir = e)) {
    cat("SKIP (missing scalars):", plan, "\n"); next
  }
  old_val <- e$Percent_difference
  e$Percent_difference <- (e$Model_AAL - e$CAFR_AAL) / e$CAFR_AAL
  save(list = ls(envir = e), file = rdata, envir = e)
  cat(sprintf("Patched %-6s  old=%.4f  new=%.4f\n", plan, old_val, e$Percent_difference))
}
cat("Done.\n")
