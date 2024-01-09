#!/usr/bin/env python3
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
        df.sample(fraction=1.0, with_replacement=True, shuffle=True)
        .lazy()
        .select(pl.col(by), pl.col("^IPIP.*$"))
        .melt(id_vars=by, variable_name="scale")
        .group_by(by + ("scale",))
        .agg(
            pl.col("value").mean().alias("mean"),
            pl.col("value").median().alias("median"),
        )
        .melt(id_vars=by + ("scale",), variable_name="stat")
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
        pl.concat((get_stats(df, by) for i in tqdm.tqdm(range(n_iter))))
        .group_by(by + ("scale", "stat"))
        .agg(
            pl.median("value").alias("median"),
            pl.quantile("value", 0.025).alias("ci95.ll"),
            pl.quantile("value", 0.975).alias("ci95.ul"),
        )
        .collect()
    )
    return result


def run(
    path: str,
    categories: (tuple | None) = None,
    n_iter: int = 1000,
    output_dir: (str | None) = None,
    output_dict: (dict | None) = None,
):
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
    output_dir : str, optional
        The directory in which to write the output CSV files. If None, no files are written.
    output_dict : dict, optional
        A dictionary to store the output data. If None, no data is stored.

    Returns
    -------
    None
    """

    # Read the CSV file into a DataFrame:
    if path.endswith("csv.gz"):  # If the file is compressed with gzip:
        with gzip.open(path, "rb") as f:
            df = pl.read_csv(f.read(), null_values=["NA", ""])
    else:  # If the file is not compressed:
        df = pl.read_csv(path, null_values=["NA", ""])

    # Drop subject ID column (RID) and convert all string columns to factors:
    df = df.drop("RID").with_columns(pl.selectors.string().cast(pl.Categorical))

    # If categories is None, use all the categorical columns:
    categories = categories or tuple(df.lazy().select(pl.col(pl.Categorical)).columns)

    # Print the number of cores we are using:
    #  (only works on Linux)
    if hasattr(os, "sched_getaffinity"):
        print(
            f"Using {len(os.sched_getaffinity(0))} cores on node {os.uname().nodename}"
        )

    # Print the categories we are operating on:
    print(f'Operating on categories "{categories}"')

    start = time.time()  # Start the clock
    # Loop through the categories and calculate the statistics:
    for category in categories:
        # Make sure category is a tuple
        category = (category,) if isinstance(category, str) else category
        print(f'Processing category "{category}"')
        result = boot_stats(df, by=category, n_iter=n_iter)

        # Write the results to a CSV file if output_dir is not None:
        if output_dir is not None:
            # Make output directory if it doesn't exist:
            os.makedirs(output_dir, exist_ok=True)

            # Make the filename from the category:
            filename = "boot" + "_" * (len(category) > 0) + ",".join(category) + ".csv"

            # Write the results to a CSV file:
            result.write_csv(os.path.join(output_dir, filename))

            print(f'Wrote "{os.path.join(output_dir, filename)}"')

        # Add the results to the output dictionary if output_dict is not None:
        if output_dict is not None:
            key = ",".join(category)
            output_dict[key] = result

    elapsed = datetime.timedelta(seconds=time.time() - start)  # End the clock
    print(f"Done processing {n_iter} iterations in {elapsed}")
