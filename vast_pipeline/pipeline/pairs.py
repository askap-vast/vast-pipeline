from itertools import combinations
import logging

import dask.dataframe as dd
import numpy as np
import pandas as pd
from psutil import cpu_count

from vast_pipeline.pipeline.utils import calculate_n_partitions


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
    measurement_combinations = (
        dd.from_pandas(df, npartitions=n_partitions)
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

    # Dask has a tendency to swap which order the measurement pairs are
    # defined in, even if the dataframe is pre-sorted. We want the pairs to be
    # in date order (a < b) so the code below corrects any that are not.
    measurement_combinations = measurement_combinations.join(
        df[['source', 'id', 'datetime']].set_index(['source', 'id']),
        on=['source', 'id_a'],
    )

    measurement_combinations = measurement_combinations.join(
        df[['source', 'id', 'datetime']].set_index(['source', 'id']),
        on=['source', 'id_b'], lsuffix='_a', rsuffix='_b'
    )

    to_correct_mask = (
        measurement_combinations['datetime_a']
        > measurement_combinations['datetime_b']
    )

    if np.any(to_correct_mask):
        logger.debug('Correcting measurement pairs order')
        (
            measurement_combinations.loc[to_correct_mask, 'id_a'],
            measurement_combinations.loc[to_correct_mask, 'id_b']
        ) = np.array([
            measurement_combinations.loc[to_correct_mask, 'id_b'].values,
            measurement_combinations.loc[to_correct_mask, 'id_a'].values
        ])

    measurement_combinations = measurement_combinations.drop(
        ['datetime_a', 'datetime_b'], axis=1
    )

    # add the measurement fluxes and errors
    association_fluxes = df.set_index(["source", "id"])[
        ["flux_int", "flux_int_err", "flux_peak", "flux_peak_err", "image"]
    ].rename(columns={"image": "image_name"})
    measurement_combinations = measurement_combinations.join(
        association_fluxes,
        on=["source", "id_a"],
    ).join(
        association_fluxes,
        on=["source", "id_b"],
        lsuffix="_a",
        rsuffix="_b",
    )

    # calculate 2-epoch metrics
    measurement_combinations["vs_peak"] = calculate_vs_metric(
        measurement_combinations.flux_peak_a,
        measurement_combinations.flux_peak_b,
        measurement_combinations.flux_peak_err_a,
        measurement_combinations.flux_peak_err_b,
    )
    measurement_combinations["vs_int"] = calculate_vs_metric(
        measurement_combinations.flux_int_a,
        measurement_combinations.flux_int_b,
        measurement_combinations.flux_int_err_a,
        measurement_combinations.flux_int_err_b,
    )
    measurement_combinations["m_peak"] = calculate_m_metric(
        measurement_combinations.flux_peak_a,
        measurement_combinations.flux_peak_b,
    )
    measurement_combinations["m_int"] = calculate_m_metric(
        measurement_combinations.flux_int_a,
        measurement_combinations.flux_int_b,
    )

    return measurement_combinations
