import os
import logging
import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord
from typing import List, Dict

from vast_pipeline.models import Run
from vast_pipeline.utils.utils import StopWatch, optimize_floats, optimize_ints
from vast_pipeline.pipeline.loading import (
    make_upload_associations, make_upload_sources, make_upload_related_sources,
    update_sources
)
from vast_pipeline.pipeline.pairs import calculate_measurement_pair_metrics
from vast_pipeline.pipeline.utils import parallel_groupby


logger = logging.getLogger(__name__)


def calculate_measurement_pair_aggregate_metrics(
    measurement_pairs_df: pd.DataFrame,
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
        measurement_pairs_df:
            The measurement pairs and their variability metrics. Must at least
            contain the columns: source, vs_{flux_type}, m_{flux_type}.
        min_vs:
            The minimum value of the Vs metric (i.e. column `vs_{flux_type}`)
            the measurement pair must have to be included in the aggregate
            metric determination.
        flux_type:
            The flux type on which to perform the aggregation, either "peak"
            or "int". Default is "peak".

    Returns:
        Measurement pair aggregate metrics indexed by the source ID, `source`.
        The metric columns are named: `vs_abs_significant_max_{flux_type}` and
        `m_abs_significant_max_{flux_type}`.
    """
    pair_agg_metrics = measurement_pairs_df.set_index("source").iloc[
        measurement_pairs_df.query(f"abs(vs_{flux_type}) >= @min_vs")
        .groupby("source")
        .agg(m_abs_max_idx=(f"m_{flux_type}", lambda x: x.abs().idxmax()),)
        .astype(np.int32)["m_abs_max_idx"]  # cast row indices to int and select them
        .reset_index(drop=True)  # keep only the row indices
    ][[f"vs_{flux_type}", f"m_{flux_type}"]]

    pair_agg_metrics = pair_agg_metrics.abs().rename(columns={
        f"vs_{flux_type}": f"vs_abs_significant_max_{flux_type}",
        f"m_{flux_type}": f"m_abs_significant_max_{flux_type}",
    })
    return pair_agg_metrics


def final_operations(
    sources_df: pd.DataFrame,
    p_run: Run,
    new_sources_df: pd.DataFrame,
    source_aggregate_pair_metrics_min_abs_vs: float,
    add_mode: bool,
    done_source_ids: List[int],
    previous_parquets: Dict[str, str]
) -> int:
    """
    Performs the final operations of the pipeline:
    - Calculates the statistics for the final sources.
    - Uploads sources and writes parquet.
    - Uploads related sources and writes parquet.
    - Uploads associations and writes parquet.

    Args:
        sources_df:
            The main sources_df dataframe produced from the pipeline.
            Contains all measurements and the association information.
            The `id` column is the Measurement object primary key that has
            already been saved to the database.
        p_run:
            The pipeline Run object of which the sources are associated with.
        new_sources_df:
            The new sources dataframe, only contains the
            'new_source_high_sigma' column (source_id is the index).
        source_aggregate_pair_metrics_min_abs_vs:
            Only measurement pairs where the Vs metric exceeds this value
            are selected for the aggregate pair metrics that are stored in
            `Source` objects.
        add_mode:
            Whether the pipeline is running in add mode.
        done_source_ids:
            A list containing the source ids that have already been uploaded
            in the previous run in add mode.

    Returns:
        The number of sources contained in the pipeline (used in the next steps
        of main.py).
    """
    timer = StopWatch()

    # calculate source fields
    logger.info(
        'Calculating statistics for %i sources...',
        sources_df.source.unique().shape[0]
    )
    srcs_df = parallel_groupby(sources_df)
    logger.info('Groupby-apply time: %.2f seconds', timer.reset())

    # add new sources
    srcs_df["new"] = srcs_df.index.isin(new_sources_df.index)
    srcs_df = pd.merge(
        srcs_df,
        new_sources_df["new_high_sigma"],
        left_on="source",
        right_index=True,
        how="left",
    )
    srcs_df["new_high_sigma"] = srcs_df["new_high_sigma"].fillna(0.0)

    # calculate nearest neighbour
    srcs_skycoord = SkyCoord(
        srcs_df['wavg_ra'].values,
        srcs_df['wavg_dec'].values,
        unit=(u.deg, u.deg)
    )
    idx, d2d, _ = srcs_skycoord.match_to_catalog_sky(
        srcs_skycoord,
        nthneighbor=2
    )

    # add the separation distance in degrees
    srcs_df['n_neighbour_dist'] = d2d.deg

    # create measurement pairs, aka 2-epoch metrics
    timer.reset()
    measurement_pairs_df = calculate_measurement_pair_metrics(sources_df)
    logger.info('Measurement pair metrics time: %.2f seconds', timer.reset())

    # calculate measurement pair metric aggregates for sources by finding the row indices
    # of the aggregate max of the abs(m) metric for each flux type.
    pair_agg_metrics = pd.merge(
        calculate_measurement_pair_aggregate_metrics(
            measurement_pairs_df, source_aggregate_pair_metrics_min_abs_vs, flux_type="peak",
        ),
        calculate_measurement_pair_aggregate_metrics(
            measurement_pairs_df, source_aggregate_pair_metrics_min_abs_vs, flux_type="int",
        ),
        how="outer",
        left_index=True,
        right_index=True,
    )

    # join with sources and replace agg metrics NaNs with 0 as the DataTables API JSON
    # serialization doesn't like them
    srcs_df = srcs_df.join(pair_agg_metrics).fillna(value={
        "vs_abs_significant_max_peak": 0.0,
        "m_abs_significant_max_peak": 0.0,
        "vs_abs_significant_max_int": 0.0,
        "m_abs_significant_max_int": 0.0,
    })
    logger.info("Measurement pair aggregate metrics time: %.2f seconds", timer.reset())

    # upload sources to DB, column 'id' with DB id is contained in return
    if add_mode:
        # if add mode is being used some sources need to updated where as some
        # need to be newly uploaded.
        # upload new ones first (new id's are fetched)
        src_done_mask = srcs_df.index.isin(done_source_ids)
        srcs_df_upload = srcs_df.loc[~src_done_mask].copy()
        srcs_df_upload = make_upload_sources(srcs_df_upload, p_run, add_mode)
        # And now update
        srcs_df_update = srcs_df.loc[src_done_mask].copy()
        logger.info(
            f"Updating {srcs_df_update.shape[0]} sources with new metrics.")
        srcs_df = update_sources(srcs_df_update, batch_size=1000)
        # Add back together
        if not srcs_df_upload.empty:
            srcs_df = srcs_df.append(srcs_df_upload)
    else:
        srcs_df = make_upload_sources(srcs_df, p_run, add_mode)

    # gather the related df, upload to db and save to parquet file
    # the df will look like
    #
    #         from_source_id  to_source_id
    # source
    # 714     60              14396
    # 1211    94              12961
    #
    # the index ('source') has the initial id generated by the pipeline to
    # identify unique sources, the 'from_source_id' column has the django
    # model id (in db), the 'to_source_id' has the pipeline index

    related_df = (
        srcs_df.loc[srcs_df["related_list"] != -1, ["id", "related_list"]]
        .explode("related_list")
        .rename(columns={"id": "from_source_id", "related_list": "to_source_id"})
    )

    # for the column 'from_source_id', replace relation source ids with db id
    related_df["to_source_id"] = related_df["to_source_id"].map(srcs_df["id"].to_dict())
    # drop relationships with the same source
    related_df = related_df[related_df["from_source_id"] != related_df["to_source_id"]]

    # write symmetrical relations to parquet
    related_df.to_parquet(
        os.path.join(p_run.path, 'relations.parquet'),
        index=False
    )

    # upload the relations to DB
    # check for add_mode first
    if add_mode:
        # Load old relations so the already uploaded ones can be removed
        old_relations = (
            pd.read_parquet(previous_parquets['relations'])
        )

        related_df = (
            related_df.append(old_relations, ignore_index=True)
            .drop_duplicates(keep=False)
        )
        logger.debug(f'Add mode: #{related_df.shape[0]} relations to upload.')

    make_upload_related_sources(related_df)

    del related_df

    # write sources to parquet file
    srcs_df = srcs_df.drop(["related_list", "img_list"], axis=1)
    (
        srcs_df.set_index('id')  # set the index to db ids, dropping the source idx
        .to_parquet(os.path.join(p_run.path, 'sources.parquet'))
    )

    # update measurments with sources to get associations
    sources_df = (
        sources_df.drop('related', axis=1)
        .merge(srcs_df.rename(columns={'id': 'source_id'}), on='source')
    )

    if add_mode:
        # Load old associations so the already uploaded ones can be removed
        old_assoications = (
            pd.read_parquet(previous_parquets['associations'])
            .rename(columns={'meas_id': 'id'})
        )
        sources_df_upload = sources_df.append(
            old_assoications, ignore_index=True)
        sources_df_upload = sources_df_upload.drop_duplicates(
            ['source_id', 'id', 'd2d', 'dr'], keep=False
        )
        logger.debug(
            f'Add mode: #{sources_df_upload.shape[0]} associations to upload.')
    else:
        sources_df_upload = sources_df

    # upload associations into DB
    make_upload_associations(sources_df_upload)

    # write associations to parquet file
    sources_df.rename(columns={'id': 'meas_id'})[
        ['source_id', 'meas_id', 'd2d', 'dr']
    ].to_parquet(os.path.join(p_run.path, 'associations.parquet'))

    # get the Source object primary keys for the measurement pairs
    measurement_pairs_df = measurement_pairs_df.join(
        srcs_df.id.rename("source_id"), on="source"
    )

    if add_mode:
        # Load old associations so the already uploaded ones can be removed
        old_measurement_pairs = (
            pd.read_parquet(previous_parquets['measurement_pairs'])
        ).rename(columns={'meas_id_a': 'id_a', 'meas_id_b': 'id_b'})

        measurement_pairs_df = old_measurement_pairs.append(
            measurement_pairs_df
        ).drop_duplicates(["id_a", "id_b", "source_id"])

    # optimize measurement pair DataFrame and save to parquet file
    measurement_pairs_df = optimize_ints(
        optimize_floats(
            measurement_pairs_df.drop(columns=["source"]).rename(
                columns={"id_a": "meas_id_a", "id_b": "meas_id_b"}
            )
        )
    )
    measurement_pairs_df.to_parquet(
        os.path.join(p_run.path, "measurement_pairs.parquet"), index=False
    )

    logger.info("Total final operations time: %.2f seconds", timer.reset_init())

    # calculate and return total number of extracted sources
    return srcs_df["id"].count()
