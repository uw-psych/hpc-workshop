#!/usr/bin/env Rscript

# Get the output filename and the input filenames from the command-line arguments:
filenames <- commandArgs(trailingOnly = TRUE)
output_filename <- filenames[1]
input_filenames <- filenames[-1]

# Read in the results and merge them into a data frame:
results <- do.call(rbind, lapply(input_filenames, read.csv))

# Write the output:
write.csv(results, output_filename, row.names = FALSE)

# Remove input files:
invisible(lapply(input_filenames, file.remove))

message("Wrote result to ", output_filename)
