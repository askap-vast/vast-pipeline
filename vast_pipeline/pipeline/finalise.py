import os
import logging
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord

from vast_pipeline.models import Run, MeasurementPair
from vast_pipeline.utils.utils import StopWatch, optimize_floats, optimize_ints
from vast_pipeline.pipeline.loading import (
    make_upload_associations, make_upload_sources, make_upload_related_sources,
    upload_measurement_pairs
)
from vast_pipeline.pipeline.utils import parallel_groupby, calculate_measurement_pair_metrics


logger = logging.getLogger(__name__)


def final_operations(
    sources_df: pd.DataFrame, p_run: Run, new_sources_df: pd.DataFrame
) -> int:
    """
    Performs the final operations of the pipeline:
    - Calculates the statistics for the final sources.
    - Uploads sources and writes parquet.
    - Uploads related sources and writes parquet.
    - Uploads associations and writes parquet.

    Parameters
    ----------
    sources_df : pd.DataFrame
        The main sources_df dataframe produced from the pipeline. Contains all
        measurements and the association information. The `id` column is the Measurement
        object primary key that has already been saved to the database.
    p_run : Run
        The pipeline Run object of which the sources are associated with.
    new_sources_df : pd.DataFrame
        The new sources dataframe, only contains the 'new_source_high_sigma'
        column (source_id is the index).

    Returns
    -------
    nr_sources : int
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
    # calculate 2-pair metric aggregates for sources
    srcs_df = srcs_df.join(
        measurement_pairs_df.groupby("source")
        .agg(
            vs_max_int=("vs_int", "max"),
            vs_max_peak=("vs_peak", "max"),
            m_abs_max_int=("m_int", lambda x: x.abs().max()),
            m_abs_max_peak=("m_peak", lambda x: x.abs().max()),
        )
        .dropna(how="all"),
    )
    logger.info("Measurement pair aggregate metrics time: %.2f seconds", timer.reset())

    # fill NaNs as resulted from calculated metrics with 0, the DataTables API doesn't like them
    srcs_df = srcs_df.fillna(0.0)

    # upload sources to DB, column 'id' with DB id is contained in return
    srcs_df = make_upload_sources(srcs_df, p_run)

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

    # upload the relations to DB.
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

    # upload associations into DB
    make_upload_associations(sources_df)

    # write associations to parquet file
    sources_df.rename(columns={'id': 'meas_id'})[
        ['source_id', 'meas_id', 'd2d', 'dr']
    ].to_parquet(os.path.join(p_run.path, 'associations.parquet'))

    # get the Source object primary keys for the measurement pairs
    measurement_pairs_df = measurement_pairs_df.join(
        srcs_df.id.rename("source_id"), on="source"
    )
    # create the measurement pair objects
    measurement_pairs_df["measurement_pair_dj"] = measurement_pairs_df.apply(
        lambda row: MeasurementPair(
            source_id=row["source_id"],  # set the source foreign key ID directly
            measurement_a_id=row["id_a"],
            measurement_b_id=row["id_b"],
            vs_peak=row["vs_peak"],
            vs_int=row["vs_int"],
            m_peak=row["m_peak"],
            m_int=row["m_int"],
        ),
        axis=1,
    )
    upload_measurement_pairs(measurement_pairs_df["measurement_pair_dj"])

    # get the MeasurementPair object primary keys
    measurement_pairs_df["id"] = measurement_pairs_df["measurement_pair_dj"].apply(
        lambda x: x.id
    )
    # optimize measurement pair DataFrame and save to parquet file
    measurement_pairs_df = optimize_ints(
        optimize_floats(
            measurement_pairs_df.drop(columns=["source", "measurement_pair_dj"]).rename(
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
