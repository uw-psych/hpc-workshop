#!/usr/bin/env Rscript
if (!requireNamespace("boot", quietly = TRUE)) install.packages("boot"); requireNamespace("boot", quietly = TRUE)

#
# Calculate Cohen's D
#'
#' @param d numeric vector of values
#' @param f vector of factor
#'
#' @return list with Cohen's D and df
cohen_d <- function(d, f) {
  d <- d[order(f)]
  f <- f[order(f)]
  ns <- as.numeric(table(f))
  m <- c()
  s <- c()
  for (l in levels(f)) {
    m = c(m, mean(d[f == l]))
    s = c(s, sd(d[f == l]))
  }
  delta.m <- as.numeric(m[1] - m[2])
  stdev <-
    sqrt(((ns[1] - 1) * s[1] ^ 2 + (ns[2] - 1) * s[2] ^ 2) / (ns[1] +
        ns[2] - 2))
  return(list(d = delta.m / stdev, df = ns[1] + ns[2] - 2))
}


#' Get Cohen's D estimate for a set of indices in a data frame
#'
#' @param data a data frame
#' @param response name of the response variable
#' @param group name of the grouping variable
#' @param indices indices to select
#'
#' @return numeric value with Cohen's D
bs_cohen_d <-  function(data, response, group, indices) {
  d <- data[indices,] # allows boot to select sample
  fit <- cohen_d(d[[response]], d[[group]])
  return(fit$d)
}

#' Get Cohen's D for a scale in the data frame by a dichotomous grouping variable
#'
#' @param data the data frame
#' @param scale column name for the scale
#' @param group a dichotomous grouping variable (default: "gender")
#' @param n.iter number of iterations (default: 100)
#'
#' @return a data frame with columns "scale", "d" (the estimate), "ci.level" (the confidence level), "ci.ll" (the lower bound), and "ci.ul" (the upper bound)
get_cohens_d_for_scale <- function(data,
  scale,
  group = "gender",
  n.iter = 1000) {
  message(
    "Computing Cohen's D for scale ",
    scale,
    " on group ",
    group,
    " with ",
    n.iter,
    " bootstrapped iterations"
  )
  # Get initial estimate:
  estimate <- cohen_d(data[[scale]], data[["gender"]])

  # Calculate bootstrapped statistic:
  results <-
    boot::boot(
      data = data,
      statistic = bs_cohen_d,
      R = n.iter,
      response = scale,
      group = group
    )

  # Obtain confidence intervals for estimate:
  cis <- boot::boot.ci(results, type = "basic")

  # Return data frame with scale, the estimate, the confidence level, the lower bound, and the upper bound:
  message(
    "Done computing Cohen's D for scale ",
    scale,
    " on group ",
    group,
    " with ",
    n.iter,
    " bootstrapped iterations"
  )
  data.frame(
    scale = scale,
    d = estimate$d,
    ci.level = cis$basic[[1]],
    ci.ll = cis$basic[[4]],
    ci.ul = cis$basic[[5]]
  )
}

# Set the random seed for reproducibility:
set.seed(42)

# Set the number of iterations reproducibility from the BOOT_ITER environment variable, or use 10000:
BOOT_ITER <- as.integer(Sys.getenv("BOOT_ITER", unset = "10000"))

# Get command-line arguments:
cmd_args <- commandArgs(trailingOnly = TRUE)

# Read in the data, getting the input filename from the first command-line argument:
scores <- read.csv(cmd_args[1], stringsAsFactors = TRUE)

# Get the scales to compute from the command-line arguments:
scales <- cmd_args[-1]

# Calculate result:
for (scale in scales) {
  result <- get_cohens_d_for_scale(scores, scale, n.iter = BOOT_ITER)
  output_filename <- paste0("output/", scale, "_by_gender.csv")
  dir.create(dirname(output_filename),
    recursive = TRUE,
    showWarnings = FALSE)
  write.csv(result, output_filename, row.names = FALSE)
  message("Wrote result to ", output_filename)
}
