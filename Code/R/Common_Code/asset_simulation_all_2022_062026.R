script_path <- NA_character_
script_path <- tryCatch({
  ofile <- sys.frame(1)$ofile
  if (!is.null(ofile)) normalizePath(ofile) else NA_character_
}, error = function(e) NA_character_)
if (!file.exists(script_path)) {
  script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  script_path <- if (length(script_arg)) {
    normalizePath(sub("^--file=", "", script_arg[1]))
  } else {
    file.path(normalizePath("Cluster Code/cluster_062026"), "Common_Code",
              "asset_simulation_all_2022_062026.R")
  }
}

script_dir <- dirname(script_path)
root_dir <- normalizePath(file.path(script_dir, "..", "..", ".."))
setwd(root_dir)

run_tag <- "062026"
run_dir <- file.path(root_dir, "Results", "Runs", run_tag)
log_dir <- file.path(run_dir, "_logs")
input_suffix <- paste0("_detAL_2022_", run_tag, ".RData")
output_suffix <- paste0("_AssetSim_2022_2asset_", run_tag, ".RData")

dir.create(run_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

plan_dirs <- list.dirs(run_dir, recursive = FALSE, full.names = TRUE)
plan_dirs <- plan_dirs[basename(plan_dirs) != "_logs"]
input_files <- Sys.glob(file.path(run_dir, "*", paste0("*", input_suffix)))
input_plans <- basename(dirname(input_files))
plans <- sort(unique(c(basename(plan_dirs), input_plans)))
if (!length(plans)) {
  stop("No run plan folders or deterministic A/L input files found under: ",
       run_dir)
}

# Amortize payments or constant percent of wages
Amortize <- FALSE

# Period over which to amortize
Amotorize_Period <- 30

Nasset <- 2

# Number of asset simulations to run
num_sim <- 10000

required_objects <- c(
  "Assets",
  "AAL",
  "cash_inflows",
  "cash_outflows",
  "Inflation",
  "rf",
  "planinfo",
  "Nyear"
)
if (Amortize) {
  required_objects <- c(required_objects, "NormalCost", "discountrate")
}

get_asset_share_2asset <- function(planinfo) {
  risky_asset_cols <- c(
    "COMDTotal_Actl",
    "OtherTotal_Actl",
    "PETotal_Actl",
    "EQTotal_Actl",
    "AltMiscTotal_Actl",
    "HFTotal_Actl",
    "RETotal_Actl"
  )

  missing_cols <- setdiff(risky_asset_cols, names(planinfo))
  if (length(missing_cols)) {
    stop("planinfo is missing asset allocation columns: ",
         paste(missing_cols, collapse = ", "))
  }

  asset_share_stocks <- sum(as.numeric(planinfo[1, risky_asset_cols]),
                            na.rm = TRUE)
  c(asset_share_stocks, 1 - asset_share_stocks)
}

output_matches_num_sim <- function(output_file, expected_num_sim) {
  if (!file.exists(output_file)) {
    return(FALSE)
  }

  output_env <- new.env(parent = emptyenv())
  load(output_file, envir = output_env)
  if (!exists("Assets", envir = output_env, inherits = FALSE)) {
    return(FALSE)
  }

  actual_num_sim <- if (exists("num_sim", envir = output_env, inherits = FALSE)) {
    output_env$num_sim
  } else {
    NA_integer_
  }

  identical(as.integer(actual_num_sim), as.integer(expected_num_sim)) &&
    ncol(output_env$Assets) == expected_num_sim
}

manifest_rows <- list()
add_manifest_row <- function(plan, detal_status, asset_status, skip_reason,
                             input_file, output_file) {
  manifest_rows[[length(manifest_rows) + 1L]] <<- data.frame(
    run_tag = run_tag,
    plan = plan,
    detal_status = detal_status,
    asset_status = asset_status,
    num_sim = num_sim,
    detAL_file = input_file,
    asset_file = output_file,
    skip_reason = skip_reason,
    timestamp = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
    stringsAsFactors = FALSE
  )
}

invalid_detal_reason <- function(run_env) {
  Nyear <- run_env$Nyear
  loop_rows <- seq_len(Nyear - 1)

  checks <- list(
    AAL = run_env$AAL[loop_rows, , drop = FALSE],
    Assets = run_env$Assets[loop_rows, , drop = FALSE],
    cash_inflows = run_env$cash_inflows[loop_rows, , drop = FALSE],
    cash_outflows = run_env$cash_outflows[loop_rows, , drop = FALSE]
  )

  problems <- character(0)
  if (any(is.na(checks$AAL) | checks$AAL <= 0)) {
    problems <- c(problems, "AAL has NA or non-positive values in asset-loop rows")
  }
  if (any(is.na(checks$Assets))) {
    problems <- c(problems, "Assets has NA values in asset-loop rows")
  }
  if (any(is.na(checks$cash_inflows))) {
    problems <- c(problems, "cash_inflows has NA values in asset-loop rows")
  }
  if (any(is.na(checks$cash_outflows))) {
    problems <- c(problems, "cash_outflows has NA values in asset-loop rows")
  }

  if (length(problems)) {
    paste(problems, collapse = "; ")
  } else {
    NA_character_
  }
}

for (i_loop in seq_along(plans)) {
  plan <- plans[[i_loop]]
  plan_run_dir <- file.path(run_dir, plan)
  dir.create(plan_run_dir, recursive = TRUE, showWarnings = FALSE)
  input_file <- file.path(plan_run_dir, paste0(plan, input_suffix))
  output_file <- file.path(plan_run_dir, paste0(plan, output_suffix))

  if (output_matches_num_sim(output_file, num_sim)) {
    cat(sprintf("[%d/%d] %s: skipping existing current output %s\n",
                i_loop, length(plans), plan, output_file))
    add_manifest_row(plan, "found", "existing", "", input_file, output_file)
    next
  }

  if (!file.exists(input_file)) {
    cat(sprintf("[%d/%d] %s: skipping missing deterministic input %s\n",
                i_loop, length(plans), plan, input_file))
    add_manifest_row(plan, "missing", "skipped",
                     "deterministic A/L input not found",
                     input_file, output_file)
    next
  }

  cat(sprintf("[%d/%d] %s: loading %s\n",
              i_loop, length(plans), plan, input_file))

  run_env <- new.env(parent = globalenv())
  load(input_file, envir = run_env)

  missing_objects <- required_objects[
    !vapply(required_objects, exists, logical(1),
            envir = run_env, inherits = FALSE)
  ]
  if (length(missing_objects)) {
    cat(sprintf("[%d/%d] %s: skipping invalid input; missing objects: %s\n",
                i_loop, length(plans), plan,
                paste(missing_objects, collapse = ", ")))
    add_manifest_row(plan, "invalid", "skipped",
                     paste("missing objects:",
                           paste(missing_objects, collapse = ", ")),
                     input_file, output_file)
    next
  }

  invalid_reason <- invalid_detal_reason(run_env)
  if (!is.na(invalid_reason)) {
    cat(sprintf("[%d/%d] %s: skipping invalid input; %s\n",
                i_loop, length(plans), plan, invalid_reason))
    add_manifest_row(plan, "invalid", "skipped", invalid_reason,
                     input_file, output_file)
    next
  }

  run_env$Amortize <- Amortize
  run_env$Amotorize_Period <- Amotorize_Period
  run_env$Nasset <- Nasset
  run_env$num_sim <- num_sim
  if (!exists("AssetShare", envir = run_env, inherits = FALSE)) {
    run_env$AssetShare <- get_asset_share_2asset(run_env$planinfo)
  }

  if (length(run_env$AssetShare) < Nasset) {
    stop(plan, " has fewer than ", Nasset, " AssetShare entries.")
  }

  evalq({
    Assets <- matrix(Assets, nrow = nrow(Assets), ncol = num_sim)
    AAL <- matrix(AAL, nrow = nrow(AAL), ncol = num_sim)
    cash_inflows <- matrix(cash_inflows, nrow = nrow(cash_inflows),
                           ncol = num_sim)
    cash_outflows <- matrix(cash_outflows, nrow = nrow(cash_outflows),
                            ncol = num_sim)

    ## (STATIC) Nominal expected returns for stocks, bonds
    ExpRet <- c(0.075 + Inflation, rf)

    ## (STATIC) Standard deviations (volatility) for stocks, bonds
    SD <- c(0.20, 0)

    # Start of Monte Carlo Loop
    for (n in seq_len(num_sim)) {
      for (t in seq_len(Nyear - 1)) {
        stock_normal_shock <- rnorm(1, mean = ExpRet[[1]], sd = SD[[1]])
        bond_normal_shock <- rnorm(1, mean = ExpRet[[2]], sd = SD[[2]])
        returns <- c(stock_normal_shock, bond_normal_shock)

        AnnualRet <- 0
        ret <- numeric(Nasset)
        for (i in seq_len(Nasset)) {
          ret[i] <- returns[i]
          AnnualRet <- AnnualRet + AssetShare[i] * ret[i]
        }

        funding_ratio <- (Assets[t, n]) / AAL[t, n]

        if (funding_ratio > 1) {
          contribution <- 0
        } else {
          if (Amortize) {
            UAAL <- AAL[t, n] - Assets[t, n]
            contribution <- NormalCost[t, 1] +
              max(0, UAAL * (discountrate *
                (1 + discountrate)^Amotorize_Period) /
                (((1 + discountrate)^Amotorize_Period) - 1))
          } else {
            contribution <- cash_inflows[t, n]
          }
        }

        Assets[t + 1, n] <- Assets[t, n] * (1 + AnnualRet) -
          cash_outflows[t, n] + contribution

        if (Assets[t + 1, n] < 0) {
          Assets[t + 1, n] <- 0
          next
        }
      }
    }
  }, envir = run_env)

  save(list = ls(envir = run_env, all.names = TRUE),
       file = output_file,
       envir = run_env)

  add_manifest_row(plan, "valid", "saved", "", input_file, output_file)

  cat(sprintf("[%d/%d] %s: saved %s\n",
              i_loop, length(plans), plan, output_file))
}

if (length(manifest_rows)) {
  write.csv(do.call(rbind, manifest_rows),
            file = file.path(run_dir, "_manifest.csv"),
            row.names = FALSE)
}
