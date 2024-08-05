from itertools import combinations
import logging

import dask.dataframe as dd
import numpy as np
import pandas as pd
from psutil import cpu_count


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


def calculate_measurement_pair_metrics(df: pd.DataFrame) -> pd.DataFrame:
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
    n_cpu = 10 #cpu_count() - 1 # temporarily hardcode n_cpu
    
    partition_size_mb=100
    mem_usage_mb = df.memory_usage(deep=True).sum() / 1e6
    npartitions = int(np.ceil(mem_usage_mb/partition_size_mb))
    
    if npartitions < n_cpu:
        npartitions=n_cpu
    logger.debug(f"Running calculate_measurement_pair_metrics with {n_cpu} CPUs....")
    logger.debug(f"and using {npartitions} partions of {partition_size_mb}MB...")
    
    out = dd.from_pandas(df.set_index('source'), npartitions=npartitions)

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
    # sel_cols = ["source", "id", "datetime", ]
    ddf = dd.from_pandas(df, npartitions=40)
    ddf = ddf[["source", "id", "datetime", "flux_int", "flux_int_err",
               "flux_peak", "flux_peak_err", "image"]].rename(columns={"image": "image_name"})
    ddf = ddf.persist()
    # ddf_base = ddf[sel_cols]

    # for source, group in df.set_index("source").groupby("source"):
    #     group = group.sort_values(by="datetime")
    #     tt = pd.DataFrame(list(combinations(group["id"], 2)), columns=["id_a", "id_b"])
        
    #     tt = tt.merge(group, left_on="id_a", right_on="id").drop("id", axis=1)
        
    #     tt = tt.merge(group, left_on="id_b", right_on="id", suffixes=("_a", "_b")).drop("id", axis=1)
    #     breakpoint()
    #     print(source, group)
    
    def combine_df(group):
        group = group.sort_values(by="datetime")
        tt = pd.DataFrame(list(combinations(group["id"], 2)), columns=["id_a", "id_b"])
        
        tt = tt.merge(group, left_on="id_a", right_on="id").drop("id", axis=1)
        
        tt = tt.merge(group, left_on="id_b", right_on="id", suffixes=("_a", "_b")).drop("id", axis=1)
        return tt
        
    check = ddf.groupby("source").apply(combine_df)

    # calculate 2-epoch metrics
    check["vs_peak"] = calculate_vs_metric(
        check.flux_peak_a,
        check.flux_peak_b,
        check.flux_peak_err_a,
        check.flux_peak_err_b,
    )
    check["vs_int"] = calculate_vs_metric(
        check.flux_int_a,
        check.flux_int_b,
        check.flux_int_err_a,
        check.flux_int_err_b,
    )
    check["m_peak"] = calculate_m_metric(
        check.flux_peak_a,
        check.flux_peak_b,
    )
    check["m_int"] = calculate_m_metric(
        check.flux_int_a,
        check.flux_int_b,
    )
    
    res = check.compute(num_workers=n_cpu, scheduler="processes")
    breakpoint()
    measurement_combinations = (
        ddf.set_index("source")
        .groupby("source")["id"]
        .apply(
            lambda x: pd.DataFrame(list(combinations(x, 2))), meta={0: "i", 1: "i"},)
        .compute(num_workers=n_cpu, scheduler="processes")
    )
    
    """Drop the RangeIndex from the MultiIndex as it isn't required and rename the columns.
    Example resultant DataFrame:
               source   id_a   id_b
        0           1      1   9284
        1           1      1  17597
        2           1      1  26984
        3           1   9284  17597
        4           1   9284  26984
        ...       ...    ...    ...
        33640   11105  11845  19961
        33641   11124   3573  12929
        33642   11124   3573  21994
        33643   11124  12929  21994
        33644   11128   6216  23534
    Where source is the source ID, id_a and id_b are measurement IDs.
    """

    measurement_combinations = measurement_combinations.reset_index(
        level=1, drop=True
    ).rename(columns={0: "id_a", 1: "id_b"}).astype(int).reset_index()
    dmc = dd.from_pandas(measurement_combinations, npartitions=npartitions)
    # breakpoint()
    # Dask has a tendency to swap which order the measurement pairs are
    # defined in, even if the dataframe is pre-sorted. We want the pairs to be
    # in date order (a < b) so the code below corrects any that are not.
    dmc = dmc.merge(
        df[['source', 'id', 'datetime', 'flux_int', 'flux_int_err', 'flux_peak', 'flux_peak_err', 'image']],
        left_on=['source', 'id_a'], right_on=["source", "id"]
    ).drop("id", axis=1)
    dmc.compute(num_workers=n_cpu, scheduler="processes")
    breakpoint()
    dmc = dmc.merge(
        ddf[['source', 'id', 'datetime', 'flux_int', 'flux_int_err', 'flux_peak', 'flux_peak_err', 'image']],
        left_on=['source', 'id_b'], right_on=["source", "id"], suffixes=("_a", "_b")).drop("id", axis=1)
    # breakpoint()
    to_correct_mask = (
        dmc['datetime_a']
        > dmc['datetime_b']
    )
    # breakpoint()
    # if np.any(to_correct_mask):
    #     logger.debug('Correcting measurement pairs order')
    #     (
    #         dmc.loc[to_correct_mask, 'id_a'],
    #         dmc.loc[to_correct_mask, 'id_b']
    #     ) = np.array([
    #         dmc.loc[to_correct_mask, 'id_b'].values,
    #         dmc.loc[to_correct_mask, 'id_a'].values
    #     ])

    # dmc = dmc.drop(
    #     ['datetime_a', 'datetime_b'], axis=1
    # )
    
    # add the measurement fluxes and errors
    # association_fluxes = df.set_index(["source", "id"])[
    #     ["flux_int", "flux_int_err", "flux_peak", "flux_peak_err", "image"]
    # ].rename(columns={"image": "image_name"})
    # breakpoint()
    # measurement_combinations = measurement_combinations.join(
    #     association_fluxes,
    #     on=["source", "id_a"],
    # ).join(
    #     association_fluxes,
    #     on=["source", "id_b"],
    #     lsuffix="_a",
    #     rsuffix="_b",
    # )
    
    # calculate 2-epoch metrics
    dmc["vs_peak"] = calculate_vs_metric(
        dmc.flux_peak_a,
        dmc.flux_peak_b,
        dmc.flux_peak_err_a,
        dmc.flux_peak_err_b,
    )
    # breakpoint()
    dmc["vs_int"] = calculate_vs_metric(
        dmc.flux_int_a,
        dmc.flux_int_b,
        dmc.flux_int_err_a,
        dmc.flux_int_err_b,
    )
    
    dmc["m_peak"] = calculate_m_metric(
        dmc.flux_peak_a,
        dmc.flux_peak_b,
    )
    dmc["m_int"] = calculate_m_metric(
        dmc.flux_int_a,
        dmc.flux_int_b,
    )
    # breakpoint()
    # dmc.set_index("source")
    # breakpoint()
    dmc.compute(num_workers=n_cpu, scheduler="processes")
    return dmc
