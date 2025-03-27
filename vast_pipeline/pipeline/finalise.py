import os
import logging
import warnings
import pandas as pd
import pyarrow as pa
import dask.dataframe as dd

from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from typing import List, Dict, Tuple

from vast_pipeline.models import Run
from vast_pipeline.utils.utils import (
    StopWatch, optimise_numeric, delete_file_or_dir, calculate_n_partitions
)
from vast_pipeline.pipeline.loading import (
    update_sources,
    copy_upload_sources,
    copy_upload_related_sources,
    copy_upload_associations,
)
from vast_pipeline.pipeline.pairs import (
    calculate_measurement_pair_metrics,
    calculate_measurement_pair_aggregate_metrics
)
from vast_pipeline.pipeline.utils import (
    parallel_groupby, get_df_memory_usage,
    log_total_memory_usage
)

# NOTE: Get testing environment status.
# See comment in forced_extraction.py
__TESTING__ = settings.TESTING

logger = logging.getLogger(__name__)

def final_operations(
    sources_df: dd.DataFrame,
    p_run: Run,
    new_sources_df: pd.DataFrame,
    calculate_pairs: bool,
    source_aggregate_pair_metrics_min_abs_vs: float,
    add_mode: bool,
    done_source_ids: List[int],
    previous_parquets: Dict[str, str],
    upload_chunk_size_mb: int,
    io_workers: List[str],
) -> Tuple[int, int]:
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
        calculate_pairs:
            Whether to calculate the measurement pairs and their 2-epoch
            metrics, Vs and m.
        source_aggregate_pair_metrics_min_abs_vs:
            Only measurement pairs where the Vs metric exceeds this value
            are selected for the aggregate pair metrics that are stored in
            `Source` objects.
        add_mode:
            Whether the pipeline is running in add mode.
        done_source_ids:
            A list containing the source ids that have already been uploaded
            in the previous run in add mode.
        upload_chunk_size_mb:
            The size in MB to repartition dataframs before uploading and
            saving to parquet.
        io_workers:
            List of dask worker addresses to use for the compute.
            This is likely the output of `DaskManager.get_n_random_workers()`.

    Returns:
        The number of sources contained in the pipeline run (used in the next
            steps of main.py).
        The number of new sources contained in the pipeline run (used in the
            next steps of main.py).
    """
    timer = StopWatch()

    # calculate source fields
    logger.info("Calculating statistics for sources...")
    log_total_memory_usage()

    npartitions = calculate_n_partitions(sources_df,
                                         partition_size_mb=upload_chunk_size_mb
                                         )
    sources_df = sources_df.set_index("source") \
                           .shuffle(npartitions=npartitions, on_index=True)

    srcs_df = parallel_groupby(sources_df)

    mem_usage = get_df_memory_usage(srcs_df)
    logger.info('Groupby-apply time: %.2f seconds', timer.reset())
    logger.debug(f"Initial srcs_df memory: {mem_usage}MB")
    log_total_memory_usage()

    # Add new high sigma
    srcs_df = dd.merge(
        srcs_df,
        new_sources_df,
        left_index=True,
        right_index=True,
        how="left",
    )
    srcs_df["new_high_sigma"] = srcs_df["new_high_sigma"].fillna(0.0)

    # NOTE: It should be possible to hold off the compute on srcs_df
    # until the associations and related parques are written.
    # This would simplify the merge with maesurement pairs below as well.
    srcs_df = srcs_df.compute()

    mem_usage = get_df_memory_usage(srcs_df)
    logger.debug(f"srcs_df memory after adding new sources: {mem_usage}MB")
    log_total_memory_usage()

    # calculate nearest neighbour
    srcs_skycoord = SkyCoord(srcs_df['wavg_ra'], srcs_df['wavg_dec'], unit=(u.deg, u.deg))
    _, d2d, _ = srcs_skycoord.match_to_catalog_sky(srcs_skycoord, nthneighbor=2)

    # add the separation distance in degrees
    srcs_df["n_neighbour_dist"] = d2d.deg

    # add new sources
    srcs_df["new"] = srcs_df.index.isin(new_sources_df.index.compute().values)

    mem_usage = get_df_memory_usage(srcs_df)
    logger.debug(f"srcs_df memory after nearest-neighbour: {mem_usage}MB")
    log_total_memory_usage()

    # create measurement pairs, aka 2-epoch metrics
    if calculate_pairs:
        timer.reset()

        pairs_dir = os.path.join(p_run.path, 'measurement_pairs.parquet')
        pairs_dir_tmp = os.path.join(pairs_dir, "tmp")

        n_partitions, source_divisions = calculate_measurement_pair_metrics(sources_df, pairs_dir_tmp)
        
        logger.info('Measurement pair metrics time: %.2f seconds', timer.reset())

        # calculate measurement pair metric aggregates for sources by finding
        # the row indices of the aggregate max of the abs(m) metric for each
        # flux type.
        max_peak_pairs = calculate_measurement_pair_aggregate_metrics(
                            pairs_dir_tmp,
                            source_aggregate_pair_metrics_min_abs_vs,
                            flux_type="peak",
                            )
        max_int_pairs = calculate_measurement_pair_aggregate_metrics(
                            pairs_dir_tmp,
                            source_aggregate_pair_metrics_min_abs_vs,
                            flux_type="int",
                            )
        if max_peak_pairs.npartitions == max_int_pairs.npartitions == n_partitions:
            pair_agg_metrics = dd.merge(max_peak_pairs, max_int_pairs, on="source", how="outer")
            pair_agg_metrics = pair_agg_metrics.set_index("source")
            pair_agg_metrics = pair_agg_metrics.compute()
        else:
            max_peak_pairs = max_peak_pairs.compute()
            max_int_pairs = max_int_pairs.compute()
            pair_agg_metrics = max_peak_pairs.merge(max_int_pairs, on="source", how="outer")
            pair_agg_metrics = pair_agg_metrics.set_index("source")

        # NOTE: this logging check can eventually be removed
        pair_metrics_dupes = pair_agg_metrics.index.duplicated(keep=False)
        logger.debug("Duplicated pair_agg_metrics:")
        logger.debug(pair_agg_metrics[pair_metrics_dupes])
        
        # join with sources and replace agg metrics NaNs with 0 as the
        # DataTables API JSON serialization doesn't like them
        srcs_df = srcs_df.join(pair_agg_metrics).fillna(value={
            "vs_abs_significant_max_peak": 0.0,
            "m_abs_significant_max_peak": 0.0,
            "vs_abs_significant_max_int": 0.0,
            "m_abs_significant_max_int": 0.0,
        })
        
        # NOTE: this logging check can eventually be removed
        srcs_df_dupes = srcs_df.index.duplicated(keep=False)
        logger.debug("Duplicated srcs_df:")
        logger.debug(srcs_df[srcs_df_dupes])

        logger.info(
            "Measurement pair aggregate metrics time: %.2f seconds",
            timer.reset())
        mem_usage = get_df_memory_usage(srcs_df)
        logger.debug(f"srcs_df memory after calculate_pairs: {mem_usage}MB")
        log_total_memory_usage()
    else:
        logger.info(
            "Skipping measurement pair metric calculation as specified in "
            "the run configuration."
        )
        logger.info("Setting source two epoch metrics to 0...")
        for col in [
            "vs_abs_significant_max_peak",
            "m_abs_significant_max_peak",
            "vs_abs_significant_max_int",
            "m_abs_significant_max_int",
        ]:
            srcs_df[col] = 0.0

    # upload sources to DB
    if add_mode:
        # if add mode is being used some sources need to updated whereas some
        # need to be newly uploaded.
        # upload new ones first
        src_done_mask = srcs_df.index.isin(done_source_ids)
        srcs_df_upload = srcs_df.loc[~src_done_mask].copy()

        mem_usage = get_df_memory_usage(srcs_df_upload)
        logger.debug(f"srcs_df_upload initial memory: {mem_usage}MB")
        log_total_memory_usage()

        copy_upload_sources(srcs_df_upload, p_run, add_mode)

        mem_usage = get_df_memory_usage(srcs_df_upload)
        logger.debug(f"srcs_df_upload memory after upload: {mem_usage}MB")
        log_total_memory_usage()

        # And now update
        srcs_df_update = srcs_df.loc[src_done_mask].copy()
        logger.info(
            f"Updating {srcs_df_update.shape[0]} sources with new metrics.")
        mem_usage = get_df_memory_usage(srcs_df_update)
        logger.debug(f"srcs_df_update memory: {mem_usage}MB")
        log_total_memory_usage()

        srcs_df = update_sources(srcs_df_update, batch_size=1000)
        mem_usage = get_df_memory_usage(srcs_df_update)
        logger.debug(f"srcs_df_update memory: {mem_usage}MB")
        log_total_memory_usage()
        # Add back together
        if not srcs_df_upload.empty:
            srcs_df = pd.concat([srcs_df, srcs_df_upload])
    else:
        copy_upload_sources(srcs_df, p_run, add_mode)

    mem_usage = get_df_memory_usage(srcs_df)
    logger.debug(f"srcs_df memory after uploading sources: {mem_usage}MB")
    log_total_memory_usage()

    # gather the related df, upload to db and save to parquet file
    # the df will look like
    #
    #         from_source_id  to_source_id
    # index
    # 0       2VZ84BkbB3Fj    k4HX2abxFFek
    # 1       2uAMTWTSvBuV    4YNpzF4UE2kn
    # 2       3XLFPgfGovEW    d6cHFu68PYeJ

    related_df = (
        srcs_df.loc[
            (srcs_df["related_list"].apply(len) > 0) & (srcs_df["related_list"].apply(lambda x: x[0] != "NULL")),
            ["related_list"]]
        .explode("related_list")
        .reset_index()
        .rename(columns={"source": "from_source_id", "related_list": "to_source_id"})
    )

    if related_df.empty:
        # Add the 'from_source_id' column to the empty dataframe
        related_df = pd.DataFrame(columns=["from_source_id", "to_source_id"])

    # drop relationships with the same source
    related_df = related_df.loc[
        related_df["from_source_id"] != related_df["to_source_id"]
    ]

    # write symmetrical relations to parquet
    related_df.to_parquet(os.path.join(p_run.path, "relations.parquet"), index=False)

    # upload the relations to DB
    # check for add_mode first
    if add_mode:
        # Load old relations so the already uploaded ones can be removed
        old_relations = pd.read_parquet(previous_parquets["relations"])

        related_df = pd.concat(
            [related_df, old_relations], ignore_index=True
        ).drop_duplicates(keep=False)
        logger.debug(f"Add mode: #{related_df.shape[0]} relations to upload.")

    copy_upload_related_sources(related_df)

    del related_df

    # write sources to parquet file
    cols_to_drop = ["related_list", "img_list"]

    if add_mode:
        cols_to_drop.append("id")

    srcs_df = srcs_df.drop(cols_to_drop, axis=1)

    (
        srcs_df.to_parquet(  # set the index to db ids, dropping the source idx
            os.path.join(p_run.path, "sources.parquet")
        )
    )

    # update measurements with sources to get associations
    associations_df = sources_df.drop("related", axis=1).reset_index()

    mem_usage = get_df_memory_usage(associations_df)
    logger.debug(f"sources_df memory after merge: {mem_usage}MB")
    log_total_memory_usage()

    # Repartition associations df to optimise upload
    associations_df = associations_df.repartition(partition_size=f'{upload_chunk_size_mb}MB')
    
    logger.info("Number of associations: %d", len(associations_df.index))

    if add_mode:
        # Load old associations so the already uploaded ones can be removed
        old_associations = dd.read_parquet(previous_parquets["associations"]).rename(
            columns={"meas_id": "id", "source_id": "source"}
        )
        associations_df_upload = dd.concat(
            [associations_df, old_associations],
            ignore_index=True
        )
        # NOTE: Annoyingly keep=False doesn't work with dask, so we have to compute
        # the drop_duplicates and then recompute the dask dataframe.
        associations_df_upload = associations_df_upload[["source", "id", "d2d", "dr"]] \
                                 .compute() \
                                 .drop_duplicates(["source", "id", "d2d", "dr"], keep=False)
        associations_df_upload = dd.from_pandas(
            associations_df_upload, npartitions=associations_df.npartitions
        )
        logger.debug(f"Add mode: #{associations_df_upload.shape[0]} associations to upload.")
    else:
        associations_df_upload = associations_df

    # upload associations into DB
    if not __TESTING__:
        assoc_df = associations_df_upload.loc[:, ["id", "source", "d2d", "dr"]]
        copy_upload_associations(assoc_df, io_workers)

    # write associations to parquet file
    associations_df[['source', 'id', 'd2d', 'dr']] \
        .rename(columns={"id": "meas_id", "source": "source_id"}) \
        .to_parquet(os.path.join(p_run.path, "associations.parquet"), overwrite=True)

    nr_sources = srcs_df.shape[0]
    nr_new_sources = srcs_df["new"].sum()

    if calculate_pairs:
        # optimize measurement pair DataFrame and save to parquet file
        timer.reset()
        # ingest to dask data frames
        srcs_df.index.name = "source_id"
        srcs_df = dd.from_pandas(srcs_df, npartitions=n_partitions)
        columns = ['id_a', 'id_b', 'flux_int_a', 'flux_int_err_a', 'flux_peak_a',
       'flux_peak_err_a', 'image_name_a', 'flux_int_b', 'flux_int_err_b',
       'flux_peak_b', 'flux_peak_err_b', 'image_name_b', 'vs_peak', 'vs_int',
       'm_peak', 'm_int']

        measurement_pairs_df = dd.read_parquet(pairs_dir_tmp, columns=columns, index='source') \
                                 .merge(srcs_df, how="left", left_index=True, right_index=True) \
                                 .rename(columns={"id_a": "meas_id_a", "id_b": "meas_id_b"}) \
                                 .reset_index()

        # try to optimize measurement pair DataFrame and save to parquet file
        # fall back to original dtypes if downcasting fails due to inconsistent issue

        # get the schema before downcasting
        measurement_pairs_df._meta[['image_name_a', 'image_name_b']] = measurement_pairs_df._meta[['image_name_a', 'image_name_b']].astype("string")
        o_schema = pa.Schema.from_pandas(measurement_pairs_df._meta, preserve_index=False)
        
        try:
            measurement_pairs_df = measurement_pairs_df.map_partitions(optimise_numeric, enforce_metadata=False)
            measurement_pairs_df.to_parquet(pairs_dir, write_index=False)
        except Exception as e:
            warnings.warn(f"str{e}; skip downcast int/float")
            measurement_pairs_df.to_parquet(pairs_dir, write_index=False, schema=o_schema)

        # clear the temporary folder

        delete_file_or_dir(pairs_dir_tmp)

        logger.info("Write the final version of measurement pair dataframe into files time: %.2f seconds", timer.reset())


    logger.info("Total final operations time: %.2f seconds", timer.reset_init())

    # calculate and return total number of extracted sources
    return (nr_sources, nr_new_sources)
