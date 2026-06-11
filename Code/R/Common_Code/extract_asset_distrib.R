ROOT <- normalizePath("c:/Users/nicco/Massachusetts Institute of Technology/MIT Golub Center for Finance and Policy - Documents (1)/Research and Education/Projects/State and Local Pension/State Pension Model")

run_tag    <- "062026"
run_dir    <- file.path(ROOT, "Results", "Runs", run_tag)
plans <- sort(c('AZ06','AZ127','CA10','CA111','CA144','CA43','CA97','CA98','DC20','FL26',
                'GA27','GA28','IL32','IL33','IL34','IN37','LA130','LA163','LA44',
                'ME47','MI53','MO175','ND82','NJ71','NJ73','NM74','NY78','NY83',
                'OH88','OK134','OR91','PA92','PA93','RI96','SC100','SC99','TX108'))

rows <- list()
for (plan in plans) {
  asset_file <- file.path(run_dir, plan,
                          paste0(plan, "_AssetSim_2022_2asset_", run_tag, ".RData"))
  if (!file.exists(asset_file)) {
    cat(sprintf("%-8s: missing\n", plan))
    rows[[length(rows)+1]] <- data.frame(
      plan       = plan, n_sims = NA_integer_,
      FR10_mean  = NA_real_,  FR10_p25 = NA_real_,
      FR10_p50   = NA_real_,  FR10_p75 = NA_real_,
      exhaust_pct = NA_real_,
      stringsAsFactors = FALSE
    )
    next
  }
  e <- new.env(parent = emptyenv())
  load(asset_file, envir = e)
  Assets <- e$Assets
  AAL    <- e$AAL
  Nyear  <- if (exists("Nyear", envir = e)) e$Nyear else nrow(Assets)

  # Use AAL row 10 (year 10) from the deterministic (col 1 or mean)
  aal10 <- if (ncol(AAL) > 1) mean(AAL[10,]) else AAL[10,1]
  fr10  <- if (aal10 > 1e6) Assets[10,] / aal10 else rep(NA_real_, ncol(Assets))

  exhaust_pct <- mean(apply(Assets, 2, function(a) any(a <= 0))) * 100

  n <- ncol(Assets)
  rows[[length(rows)+1]] <- data.frame(
    plan        = plan,
    n_sims      = n,
    FR10_mean   = mean(fr10, na.rm = TRUE),
    FR10_p25    = quantile(fr10, 0.25, na.rm = TRUE),
    FR10_p50    = quantile(fr10, 0.50, na.rm = TRUE),
    FR10_p75    = quantile(fr10, 0.75, na.rm = TRUE),
    exhaust_pct = exhaust_pct,
    stringsAsFactors = FALSE
  )
  cat(sprintf("%-8s: n=%d  FR10_mean=%.3f  exhaust=%.1f%%\n",
              plan, n, rows[[length(rows)]]$FR10_mean, exhaust_pct))
}

out <- do.call(rbind, rows)
out_file <- file.path(ROOT, "Results", "Runs", run_tag,
                      paste0("_asset_distrib_", run_tag, ".csv"))
write.csv(out, out_file, row.names = FALSE)
cat(sprintf("\nWrote %d rows to %s\n", nrow(out), out_file))
