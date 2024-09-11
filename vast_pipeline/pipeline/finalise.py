import os
import logging
import numpy as np
import pandas as pd
import dask
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster
import webbrowser
from distributed.diagnostics import MemorySampler
from dask.distributed import performance_report
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
import shutil
import warnings
import pyarrow as pa

from astropy import units as u
from astropy.coordinates import SkyCoord
from typing import List, Dict, Tuple

from vast_pipeline.models import Run
from vast_pipeline.utils.utils import StopWatch, optimize_floats, optimize_ints
from vast_pipeline.pipeline.loading import (
    make_upload_associations, make_upload_sources, make_upload_related_sources,
    update_sources
)
from vast_pipeline.pipeline.pairs import calculate_measurement_pair_metrics
from vast_pipeline.pipeline.utils import parallel_groupby

dask.config.set({'distributed.worker.multiprocessing-method': 'fork'})

logger = logging.getLogger(__name__)
ms = MemorySampler()

def calculate_measurement_pair_aggregate_metrics(
    pairs_parquet_dir: str,
    min_vs: float,
    flux_type: str = "peak",
) -> dd.DataFrame:
    """
    Calculate the aggregate maximum measurement pair variability metrics
    to be stored in `Source` objects. Only measurement pairs with
    abs(Vs metric) >= `min_vs` are considered.
    The measurement pairs are filtered on abs(Vs metric) >= `min_vs`,
    grouped by the source ID column `source`, then the row index of the
    maximum abs(m) metric is found. The absolute Vs and m metric values from
    this row are returned for each source.

    Args:
        measurement_pairs_parquet_dir:
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
    # ingest parquet files
    columns = ["source", f"vs_abs_significant_max_{flux_type}", f"m_abs_significant_max_{flux_type}"]
    filters = [(f"vs_abs_significant_max_{flux_type}", ">=", min_vs)]

    pair_filtered = dd.read_parquet(pairs_parquet_dir, columns=columns, filters=filters)

    def _get_max_flux(partition):
        inds = []
        for _, group in partition.groupby("source"):
            idx = group[f"m_abs_significant_max_{flux_type}"].idxmax()
            inds.append(idx)
        return partition.loc[inds]
    

    pair_agg_metrics = pair_filtered.map_partitions(_get_max_flux)

    return pair_agg_metrics

def final_operations(
    sources_df: pd.DataFrame,
    p_run: Run,
    new_sources_df: pd.DataFrame,
    calculate_pairs: bool,
    source_aggregate_pair_metrics_min_abs_vs: float,
    add_mode: bool,
    done_source_ids: List[int],
    previous_parquets: Dict[str, str]
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
            Whether to calculate the measurement pairs and their 2-epoch metrics, Vs and
            m.
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
        The number of sources contained in the pipeline run (used in the next steps
            of main.py).
        The number of new sources contained in the pipeline run (used in the next steps
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
    if calculate_pairs:
        # setup dask client
        cluster = LocalCluster()
        # cluster = LocalCluster(n_workers=4, memory_limit="2GiB")
        client = Client(cluster)
        print(client)
        url = client.dashboard_link
        webbrowser.open_new_tab(url)
        timer.reset()
        pairs_dir = os.path.join(p_run.path, 'measurement_pair_metrics')
        pairs_dir_tmp = os.path.join(pairs_dir, "tmp")

        # create a folder to store dask profing files
        dask_profile_dir = os.path.join(p_run.path, 'dask-profile')
        if not os.path.exists(dask_profile_dir):
            os.makedirs(dask_profile_dir)
            
        n_partitions, source_divisions = calculate_measurement_pair_metrics(sources_df, pairs_dir_tmp, dask_profile_dir)
        logger.info('Measurement pair metrics time: %.2f seconds', timer.reset())
        
        # get maximum measurement pair metrics
        max_peak_pairs = calculate_measurement_pair_aggregate_metrics(pairs_dir_tmp, source_aggregate_pair_metrics_min_abs_vs, flux_type="peak")
        max_int_pairs = calculate_measurement_pair_aggregate_metrics(pairs_dir_tmp, source_aggregate_pair_metrics_min_abs_vs, flux_type="int")


        if max_peak_pairs.npartitions == max_int_pairs.npartitions == n_partitions:
            pair_agg_metrics = dd.map_partitions(dd.merge, max_peak_pairs, max_int_pairs, on="source", how="outer", enforce_metadata=False, align_dataframes=False)
            pair_agg_metrics = pair_agg_metrics.set_index("source")
            
            with ms.sample("agg_metrics"), performance_report(filename=dask_profile_dir+"/dask-agg-metrics.html"):
                pair_agg_metrics = pair_agg_metrics.compute()
            
        else:
            with ms.sample("agg_metrics_peak"), performance_report(filename=dask_profile_dir+"/dask-agg-metrics-peak.html"):
                max_peak_pairs = max_peak_pairs.compute()
            with ms.sample("agg_metrics_int"), performance_report(filename=dask_profile_dir+"/dask-agg-metrics-int.html"):
                max_int_pairs = max_int_pairs.compute()
            pair_agg_metrics = max_peak_pairs.merge(max_int_pairs, on="source", how="outer")
            pair_agg_metrics = pair_agg_metrics.set_index("source")
        
       
        # join with sources and replace agg metrics NaNs with 0 as the DataTables API JSON
        # serialization doesn't like them
        srcs_df = srcs_df.join(pair_agg_metrics).fillna(value={
            "vs_abs_significant_max_peak": 0.0,
            "m_abs_significant_max_peak": 0.0,
            "vs_abs_significant_max_int": 0.0,
            "m_abs_significant_max_int": 0.0,
        })
        logger.info("Measurement pair aggregate metrics time: %.2f seconds", timer.reset())
    else:
        logger.info(
            "Skipping measurement pair metric calculation as specified in the run configuration."
        )
    
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
            srcs_df = pd.concat([srcs_df, srcs_df_upload])
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
            pd.concat([related_df, old_relations], ignore_index=True)
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
        sources_df_upload = pd.concat(
            [sources_df, old_assoications],
            ignore_index=True
        )
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

    if calculate_pairs:
        timer.reset()
        # ingest to dask data frames
        srcs_df_id = dd.from_pandas(srcs_df.id.rename("source_id"), npartitions=n_partitions)
        srcs_df_id = srcs_df_id.repartition(divisions=source_divisions)

        columns = ['source', 'id_a', 'id_b', 'flux_int_a', 'flux_int_err_a', 'flux_peak_a',
       'flux_peak_err_a', 'image_name_a', 'flux_int_b', 'flux_int_err_b',
       'flux_peak_b', 'flux_peak_err_b', 'image_name_b', 'vs_peak', 'vs_int',
       'm_peak', 'm_int']

        measurement_pairs_df = dd.read_parquet(pairs_dir_tmp, columns=columns)
        
        if srcs_df_id.npartitions == measurement_pairs_df.npartitions:
            measurement_pairs_df = measurement_pairs_df.map_partitions(dd.merge, srcs_df_id, how="left", on="source", align_dataframes=False, enforce_metadata=False)
        else:
            measurement_pairs_df = measurement_pairs_df.merge(srcs_df_id, how="left", on="source")

        measurement_pairs_df = measurement_pairs_df.drop("source", axis=1).rename(columns={"id_a": "meas_id_a", "id_b": "meas_id_b"})
        
        # try to optimize measurement pair DataFrame and save to parquet file  
        # fall back to original dtypes if downcasting fails due to inconsistent issue
        
        # get the schema before downcasting
        measurement_pairs_df._meta[['image_name_a', 'image_name_b']] = measurement_pairs_df._meta[['image_name_a', 'image_name_b']].astype("string")
        o_schema = pa.Schema.from_pandas(measurement_pairs_df._meta, preserve_index=False)
        
        try:
            measurement_pairs_df = measurement_pairs_df.map_partitions(optimize_floats, enforce_metadata=False)
            measurement_pairs_df = measurement_pairs_df.map_partitions(optimize_ints, enforce_metadata=False)

            with ms.sample("save_pairs"), performance_report(filename=dask_profile_dir+"/dask-save-pairs.html"):
                measurement_pairs_df.to_parquet(pairs_dir, write_index=False)
        except Exception as e:
            warnings.warn(f"str{e}; skip downcast int/float")
            with ms.sample("save_pairs"), performance_report(filename=dask_profile_dir+"/dask-save-pairs.html"):
                measurement_pairs_df.to_parquet(pairs_dir, write_index=False, schema=o_schema)


        client.close()
        ms.plot()
        plt.savefig(dask_profile_dir+"/pair_agg_save_memory.png")
        # clear the temporary folder
        try:
            shutil.rmtree(pairs_dir_tmp)
        except Exception as e:
            warnings.warn(f"Warning: Issues in removing pair calculation tmp folder: {e}")
            pass

        logger.info("Write the final version of measurement pair dataframe into files time: %.2f seconds", timer.reset())
    logger.info("Total final operations time: %.2f seconds", timer.reset_init())

    nr_sources = srcs_df["id"].count()
    nr_new_sources = srcs_df['new'].sum()
    # ms.plot()
    # plt.savefig("overall_memory.png")
    # breakpoint()
    # calculate and return total number of extracted sources
    logger.info("The total number of extracted sources: {}".format(nr_sources))
    logger.info("The total number of new extracted source: {}".format(nr_new_sources))
    return (nr_sources, nr_new_sources)
