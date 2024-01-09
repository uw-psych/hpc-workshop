#!/usr/bin/env python3
import polars
import sapa_bootstats
import os

# Get input path from BOOT_INPUT_PATH environment variable:
input_path = os.getenv("BOOT_INPUT_PATH")

# If no valid input path is provided, raise an error:
if input_path in (None, "") or not os.path.exists(input_path):
    raise ValueError(
        "Please provide a valid input path as first command line argument "
        "or set the BOOT_INPUT_PATH environment variable."
    )

# Set the categories we want to process:
categories = (
    "collected",
    "gender",
    "relstatus",
    "marstatus",
    "exer",
    "smoke",
    "country",
    "education",
    "jobstatus",
    ("gender", "smoke"),
    ("education", "smoke"),
    ("gender", "relstatus"),
)

# Get bootstrap iterations from BOOT_N_ITER environment var. or default 1000:
n_iter = int(os.getenv("BOOT_N_ITER", 1000))

# Get output directory from BOOT_OUTPUT_DIR environment var.
#   or default to the current directory:
output_dir = os.getenv("BOOT_OUTPUT_DIR", ".")

# Run sapa_bootstats:
sapa_bootstats.run(
    input_path, categories=categories, n_iter=n_iter, output_dir=output_dir
)
