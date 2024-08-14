from itertools import combinations
import logging

import dask.dataframe as dd
import numpy as np
import pandas as pd
from psutil import cpu_count
from vast_pipeline.utils.utils import calculate_n_partitions

logger = logging.getLogger(__name__)


def calculate_vs_metric(
    flux_a: float, flux_b: float, flux_err_a: float, flux_err_b: float
) -> float:
    """Calculate the Vs variability metric which is the t-statistic that the provided
    fluxes are variable. See Section 5 of Mooley et al. (2016) for details,
    DOI: 10.3847/0004-637X/818/2/105.

    Args:
        flux_a (float): flux value "A".
        flux_b (float): flux value "B".
        flux_err_a (float): error of `flux_a`.
        flux_err_b (float): error of `flux_b`.

    Returns:
        float: the Vs metric for flux values "A" and "B".
    """
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)


def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """Calculate the m variability metric which is the modulation index between two fluxes.
    This is proportional to the fractional variability.
    See Section 5 of Mooley et al. (2016) for details, DOI: 10.3847/0004-637X/818/2/105.

    Args:
        flux_a (float): flux value "A".
        flux_b (float): flux value "B".

    Returns:
        float: the m metric for flux values "A" and "B".
    """
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))


def calculate_measurement_pair_metrics(df: pd.DataFrame, path=".") -> dd.DataFrame:
    """Generate a DataFrame of measurement pairs and their 2-epoch variability metrics
    from a DataFrame of measurements. For more information on the variability metrics, see
    Section 5 of Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105.

    Args:
        df (pd.DataFrame): Input measurements. Must contain columns: id, source, flux_int,
            flux_int_err, flux_peak, flux_peak_err, has_siblings.

    Returns:
        Measurement pairs and 2-epoch metrics. Will contain columns:
            source - the source ID
            id_a, id_b - the measurement IDs
            flux_int_a, flux_int_b - measurement integrated fluxes in mJy
            flux_int_err_a, flux_int_err_b - measurement integrated flux errors in mJy
            flux_peak_a, flux_peak_b - measurement peak fluxes in mJy/beam
            flux_peak_err_a, flux_peak_err_b - measurement peak flux errors in mJy/beam
            vs_peak, vs_int - variability t-statistic
            m_peak, m_int - variability modulation index
    """
    # n_cpu = 10 #cpu_count() - 1 # temporarily hardcode n_cpu
    
    # partition_size_mb=100
    # mem_usage_mb = df.memory_usage(deep=True).sum() / 1e6
    # npartitions = int(np.ceil(mem_usage_mb/partition_size_mb))
    
    # if npartitions < n_cpu:
    #     npartitions=n_cpu
    # logger.debug(f"Running calculate_measurement_pair_metrics with {n_cpu} CPUs....")
    # logger.debug(f"and using {npartitions} partions of {partition_size_mb}MB...")
    
    n_cpu = cpu_count() - 1
    logger.debug(f"Running association with {n_cpu} CPUs")
    n_partitions = calculate_n_partitions(df.set_index('source'), n_cpu)

    """Create a DataFrame containing all measurement ID combinations per source.
    Resultant DataFrame will have a MultiIndex(["source", RangeIndex]) where "source" is
    the source ID and RangeIndex is an unnamed temporary ID for each measurement pair,
    unique only together with source.
    DataFrame will have columns [0, 1], each containing a measurement ID. e.g.
                       0      1
        source
        1       0      1   9284
                1      1  17597
                2      1  26984
                3   9284  17597
                4   9284  26984
        ...          ...    ...
        11105   2  11845  19961
        11124   0   3573  12929
                1   3573  21994
                2  12929  21994
        11128   0   6216  23534
    """
    df = df.sort_values(["source", "datetime"]).reset_index(drop=True)
    df = df.set_index("source")
    
    # select relevant columns
    df = df[["id", "datetime", "flux_int", "flux_int_err",
               "flux_peak", "flux_peak_err", "image"]].rename(columns={"image": "image_name"})
    
    # add a new column which gives a unique identification number for each row
    scale = 10**(len(str(df.index[-1])))
    df["uind"] = df["id"] + df.index/scale
    if df["uind"].duplicated().any():
        print("something wrong with the unique identifier")

    # ingest to dask
    ddf = dd.from_pandas(df, npartitions=24) # temp: hard coded for now
    
    def get_pair_partition(partition, scale):
        # Extract combinations for each group within the partition
        result = []
        for name, group in partition.groupby("source"):
            combs = list(combinations(group['id'], 2))
            dec = name/scale
            for comb in combs:
                result.append((comb[0]+dec, comb[1]+dec, name))  # Include source if needed
        res = pd.DataFrame(result, columns=["uind_a", "uind_b", "source"])
        
        return res
    
    def merge_pair_partitions(df1_partition, df2_partition, col1, col2, suffixes=("_x", "_y")):
        return df1_partition.merge(df2_partition, left_on=col1, right_on=col2, suffixes=suffixes).drop(col2, axis=1)
        
        
    pairs = ddf.map_partitions(get_pair_partition, scale, meta={"uind_a":"float64", "uind_b":"float64", "source":"int32"})
    
    result = dd.map_partitions(merge_pair_partitions, pairs, ddf, "uind_a", "uind")
    result = dd.map_partitions(merge_pair_partitions, result, ddf, "uind_b", "uind", suffixes=("_a", "_b"))

    # calculate 2-epoch metrics
    result["vs_peak"] = calculate_vs_metric(
        result["flux_peak_a"],
        result["flux_peak_b"],
        result["flux_peak_err_a"],
        result["flux_peak_err_b"],
    )
    
    result["vs_int"] = calculate_vs_metric(
        result.flux_int_a,
        result.flux_int_b,
        result.flux_int_err_a,
        result.flux_int_err_b,
    )

    result["m_peak"] = calculate_m_metric(
        result.flux_peak_a,
        result.flux_peak_b,
    )

    result["m_int"] = calculate_m_metric(
        result.flux_int_a,
        result.flux_int_b,
    )
    
    # remove datetime columns
    # todo: double check whether we need to ingest them to dask at the first place
    result = result.drop(["datetime_a", "datetime_b"], axis=1)

    # get absolute value of metrics
    result['vs_abs_significant_max_peak'] = result['vs_peak'].abs()
    result['vs_abs_significant_max_int'] = result['vs_int'].abs()
    result['m_abs_significant_max_peak'] = result['m_peak'].abs()
    result['m_abs_significant_max_int'] = result['m_int'].abs()
    
    result.to_parquet(path+"/pair_metric", write_index=False, overwrite=True, compute=True)
    
    return result
    