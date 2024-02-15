#!/usr/bin/env python3
# Calculate bootstrapped statistics for a subset of categories (array job version)

import itertools  # For chunking the categories
import polars as pl  # Polars dataframes for parsing and processing the data
import gzip  # For reading the compressed CSV file
import tqdm  # Progress bar
import time, datetime, os, sys  # Misc. utilities


def get_stats(df: pl.DataFrame, by: tuple) -> pl.DataFrame:
    """
    Calculate mean and median for a given DataFrame grouped by specified columns.

    Parameters
    ----------
    df : pl.DataFrame
        The DataFrame for which to calculate statistics.
    by : tuple
        The columns by which to group the DataFrame.

    Returns
    -------
    pl.DataFrame
        A DataFrame containing the calculated statistics, grouped by the specified columns.
    """
    result = (
        df.sample(
            fraction=1.0, with_replacement=True, shuffle=True
        )  # Sample with replacement
        .lazy()  # Lazy evaluation to optimize performance by waiting to execute the operations until the end
        .select(
            pl.col(by), pl.col("^IPIP.*$")
        )  # Select the columns for the categories and each IPIP scale
        .melt(id_vars=by, variable_name="scale")  # Melt the DataFrame to long format
        .group_by(by + ("scale",))  # Group by the specified columns and the scale
        .agg(
            pl.col("value").mean().alias("mean"),  # Calculate the mean
            pl.col("value").median().alias("median"),  # Calculate the median
        )
        .melt(
            id_vars=by + ("scale",), variable_name="stat"
        )  # Melt the DataFrame to long format
    )
    return result


def boot_stats(df: pl.DataFrame, by: tuple, n_iter: int) -> pl.DataFrame:
    """
    Perform bootstrap sampling on a DataFrame and calculate statistics for each category.

    This function takes a DataFrame and a tuple of categories, performs bootstrap sampling
    with replacement from the original DataFrame, and returns a DataFrame with the calculated
    statistics for each category.

    Parameters
    ----------
    df : pl.DataFrame
        The DataFrame from which to sample.
    by : tuple
        The columns by which to group the DataFrame.
    n_iter : int
        The number of bootstrap iterations to perform.

    Returns
    -------
    pl.DataFrame
        A DataFrame containing the calculated statistics for each category, grouped by the
        specified columns.
    """
    result = (
        # Concatenate the results of n_iter bootstrap iterations:
        # Each iteration is a DataFrame with the calculated statistics.
        # tqdm.tqdm() is used to display a progress bar over the iterations.
        pl.concat((get_stats(df, by) for i in tqdm.tqdm(range(n_iter))))
        .group_by(by + ("scale", "stat"))
        .agg(
            pl.median("value").alias("median"),  # Median of the values
            pl.quantile("value", 0.025).alias("ci95.ll"),  # Lower limit of 95% CI
            pl.quantile("value", 0.975).alias("ci95.ul"),  # Upper limit of 95% CI
        )
        .collect()  # Collect the results into a DataFrame
    )
    return result


def run(
    path: str,
    categories: tuple | None = None,
    n_iter: int = 1000,
    output_dir: str = os.getcwd(),
) -> None:
    """
    Open the file to process for bootstrapping, run the bootstrap process, and write the output.

    This function takes a path to a CSV file, a tuple of categories, the number of bootstrap
    iterations to perform, and an optional output directory. It reads the CSV file into a
    DataFrame, performs bootstrap sampling with replacement from the DataFrame, and writes
    the resulting statistics to a CSV file in the output directory.

    Parameters
    ----------
    path : str
        The path to the CSV file to process. The CSV file may be compressed with gzip
        if the extension is ".csv.gz".
    categories : tuple, optional
        The columns by which to group the DataFrame. If None, all categorical columns are used.
    n_iter : int, default 1000
        The number of bootstrap iterations to perform.
    output_dir : str, default current working directory
        The directory in which to write the output CSV files.

    Returns
    -------
    None
    """

    # -- Read the CSV file into a DataFrame --
    # Set the reader to gzip.open if the file is compressed with gzip:
    reader = open if not path.endswith("csv.gz") else gzip.open
    with reader(path, "rb") as f:
        df = pl.read_csv(f.read(), null_values=["NA", ""])

    # Drop subject ID column (RID) and convert all string columns to factors:
    df = df.drop("RID").with_columns(pl.selectors.string().cast(pl.Categorical))

    # If categories is None, use all the categorical columns:
    categories = categories or tuple(df.lazy().select(pl.col(pl.Categorical)).columns)

    # -- Print details about this run --
    # Get the number of cores we are using (only works on Linux):
    ncores = (
        "?" if not hasattr(os, "sched_getaffinity") else len(os.sched_getaffinity(0))
    )

    # Print the number of cores we are using and the name of the cluster node:
    print(f"Using {ncores} cores on node {os.uname().nodename}")

    # Print the categories we are operating on:
    print(f'Operating on categories "{categories}"')

    # -- Loop through the categories and calculate the statistics --
    start = time.time()  # Start the clock
    for category in categories:
        print(f'Processing categories "{category}"')

        # Make sure category is a tuple so we can pass it to boot_stats:
        category = (category,) if isinstance(category, str) else category

        # Calculate the statistics for the category:
        result = boot_stats(df, by=category, n_iter=n_iter)

        # Make the filename from the categories, omitting the category name if it's empty:
        filename = "boot" + ("_" * (len(category) > 0)) + ",".join(category) + ".csv"
        path = os.path.join(output_dir, filename)

        # Write the results to a CSV file:
        result.write_csv(path)
        print(f'Wrote "{path}"')

    # -- Report the time taken to process the data --
    elapsed = datetime.timedelta(seconds=time.time() - start)
    print(f"Done processing {n_iter} iterations in {elapsed}")


# -- When the script is run, get inputs and run the process --
if __name__ == "__main__":
    # Get input path from BOOT_INPUT_PATH environment variable:
    input_path = os.getenv("BOOT_INPUT_PATH")

    # If no valid input path is provided, raise an error:
    if input_path in (None, "") or not os.path.exists(input_path):
        raise ValueError(
            "BOOT_INPUT_PATH environment variable must be set to a valid path to a CSV file."
        )

    ### Get bootstrap iterations from BOOT_N_ITER environment var. or default 1000:
    n_iter = int(os.getenv("BOOT_N_ITER", 1000))

    # Get output directory from BOOT_OUTPUT_DIR environment var.
    #   or default to the current directory:
    output_dir = os.getenv("BOOT_OUTPUT_DIR", os.getcwd())
    # Make output directory if it doesn't exist:
    os.makedirs(output_dir, exist_ok=True)

    # Set the categories we want to calculate grouped statistics for:
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
    # -- Additional code for array jobs --
    # Get task count and task id from environment variables:
    task_count = int(os.getenv("SLURM_ARRAY_TASK_COUNT", 1))
    task_id = int(os.getenv("SLURM_ARRAY_TASK_ID", 1))
    min_task_id = int(os.getenv("SLURM_ARRAY_TASK_MIN", 1))  # Get the minimum task ID
    task_index = (task_id - min_task_id) + 1  # Convert task_id to 1-based index

    # Split categories into chunks:
    chunks = list(
        itertools.batched(
            categories, (len(categories) // task_count) + (len(categories) % task_count)
        )
    )

    # Get categories for this task:
    task_categories = chunks[task_index - 1]

    # Calculate the statistics for the specified categories and write the output to the output directory:
    run(input_path, task_categories, n_iter, output_dir)
