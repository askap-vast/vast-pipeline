from itertools import combinations
import logging

import dask.dataframe as dd
import numpy as np
import pandas as pd
import pyarrow as pa

from vast_pipeline.utils.utils import calculate_workers_and_partitions


logger = logging.getLogger(__name__)

PAIRS_SCHEMA = [
                ('id_a', pa.string()),
                ('id_b', pa.string()),
                ('source', pa.string()),
                ('flux_int_a', pa.float32()),
                ('flux_int_err_a', pa.float32()),
                ('flux_peak_a', pa.float32()),
                ('flux_peak_err_a', pa.float32()),
                ('image_name_a', pa.string()),
                ('flux_int_b', pa.float32()),
                ('flux_int_err_b', pa.float32()),
                ('flux_peak_b', pa.float32()),
                ('flux_peak_err_b', pa.float32()),
                ('image_name_b', pa.string()),
                ('vs_peak', pa.float32()),
                ('vs_int', pa.float32()),
                ('m_peak', pa.float32()),
                ('m_int', pa.float32()),
                ('vs_abs_significant_max_peak', pa.float32()),
                ('vs_abs_significant_max_int', pa.float32()),
                ('m_abs_significant_max_peak', pa.float32()),
                ('m_abs_significant_max_int', pa.float32()),]


def calculate_measurement_pair_aggregate_metrics(
    pairs_parquet_dir: str,
    min_vs: float,
    flux_type: str = "peak",
) -> pd.DataFrame:
    """
    Calculate the aggregate maximum measurement pair variability metrics
    to be stored in `Source` objects. Only measurement pairs with
    abs(Vs metric) >= `min_vs` are considered.
    The measurement pairs are filtered on abs(Vs metric) >= `min_vs`,
    grouped by the source ID column `source`, then the row index of the
    maximum abs(m) metric is found. The absolute Vs and m metric values from
    this row are returned for each source.

    Args:
        pairs_parquet_dir:
            The directory where parquets of measurement pairs are saved
        min_vs:
            The minimum value of the Vs metric (i.e. column `vs_{flux_type}`)
            the measurement pair must have to be included in the aggregate
            metric determination.
        flux_type:
            The flux type on which to perform the aggregation, either "peak"
            or "int". Default is "peak".

    Returns:
        Measurement pair aggregate metrics indexed by the source ID, `source`.
            The metric columns are named: `vs_abs_significant_max_{flux_type}`
            and `m_abs_significant_max_{flux_type}`.
    """

    # Ingest parquet files
    columns = ["source", f"vs_abs_significant_max_{flux_type}", f"m_abs_significant_max_{flux_type}"]
    filters = [(f"vs_abs_significant_max_{flux_type}", ">=", min_vs)]

    pair_filtered = dd.read_parquet(pairs_parquet_dir, columns=columns, filters=filters)

    def _get_max_flux(partition):
        partition=partition.reset_index(drop=True)
        inds = []
        for name, group in partition.groupby("source"):
            idx = group[f"m_abs_significant_max_{flux_type}"].idxmax()
            inds.append(int(idx))
        return partition.loc[inds]

    pair_agg_metrics = pair_filtered.map_partitions(_get_max_flux)

    return pair_agg_metrics


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


def calculate_measurement_pair_metrics(
        df: pd.DataFrame, pairs_dir="./measurement_pairs.parquet") -> dd.DataFrame:
    """Generate a DataFrame of measurement pairs and their 2-epoch variability metrics
    from a DataFrame of measurements. For more information on the variability metrics, see
    Section 5 of Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105.

    Args:
        df (pd.DataFrame): Input measurements. Must contain columns: id, source, flux_int,
            flux_int_err, flux_peak, flux_peak_err, has_siblings.
        n_cpu:
            The desired number of workers for Dask
        max_partition_mb:
            The desired maximum size (in MB) of the partitions for Dask.

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

    # select relevant columns
    df_pairs = df[["id", "flux_int", "flux_int_err",
               "flux_peak", "flux_peak_err", "image", "datetime"]].rename(columns={"image": "image_name"})

    # keep record of divisions
    source_divisions = df_pairs.divisions
    n_partitions = df_pairs.npartitions
    
    def _get_pair_partition(partition):
        partition = partition.sort_values(["source", "datetime"])
        # Extract combinations for each group within the partition
        result = []
        for name, group in partition.groupby("source"):
            combs = list(combinations(group['id'], 2))
            for comb in combs:
                result.append((comb[0], comb[1], name))

        res = pd.DataFrame(result, columns=["id_a", "id_b", "source"])
        res = res.sort_values(by=["source", "id_a", "id_b"])
        return res
    
    def _merge_pair_partitions(df1_partition, df2_partition, col1, col2, suffixes=("_x", "_y")):
        return df1_partition.merge(df2_partition, left_on=col1, right_on=col2, how="left", suffixes=suffixes).drop(col2, axis=1)
        
    # obtain pairs
    pairs = df_pairs.map_partitions(_get_pair_partition, meta={"id_a": "str", "id_b": "str", "source": "str"})

    result = dd.map_partitions(_merge_pair_partitions, pairs, df_pairs, "id_a", "id")
   
    result = dd.map_partitions(_merge_pair_partitions, result, df_pairs, "id_b", "id", suffixes=("_a", "_b"))

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
    result = result.drop(["datetime_a", "datetime_b"], axis=1)

    # get absolute value of metrics
    result['vs_abs_significant_max_peak'] = result['vs_peak'].abs()
    result['vs_abs_significant_max_int'] = result['vs_int'].abs()
    result['m_abs_significant_max_peak'] = result['m_peak'].abs()
    result['m_abs_significant_max_int'] = result['m_int'].abs()

    result.to_parquet(pairs_dir, write_index=False, overwrite=True,
                      compute=True, engine="pyarrow", schema=pa.schema(PAIRS_SCHEMA))
    
    return n_partitions, source_divisions

