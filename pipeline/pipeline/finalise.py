import os
import logging
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord

from pipeline.models import Association
from pipeline.utils.utils import StopWatch

from .loading import upload_associations, upload_sources
from .utils import get_source_models, parallel_groupby

logger = logging.getLogger(__name__)


def final_operations(
    sources_df, first_img, p_run, meas_dj_obj, new_sources_df):
    timer = StopWatch()

    # calculate source fields
    logger.info(
        'Calculating statistics for %i sources...',
        sources_df.source.unique().shape[0]
    )

    timer.reset()
    srcs_df = parallel_groupby(sources_df)
    logger.info('Groupby-apply time: %.2f seconds', timer.reset())
    # fill NaNs as resulted from calculated metrics with 0
    srcs_df = srcs_df.fillna(0.)

    # add new sources
    srcs_df['new'] = srcs_df.index.isin(new_sources_df.index)

    srcs_df = pd.merge(
        srcs_df,
        new_sources_df['new_high_sigma'],
        left_on='source', right_index=True, how='left'
    )

    srcs_df['new_high_sigma'] = srcs_df['new_high_sigma'].fillna(0.)

    # calculate nearest neighbour
    srcs_skycoord = SkyCoord(
        srcs_df['wavg_ra'],
        srcs_df['wavg_dec'],
        unit=(u.deg, u.deg)
    )

    idx, d2d, _ = srcs_skycoord.match_to_catalog_sky(
        srcs_skycoord,
        nthneighbor=2
    )

    srcs_df['n_neighbour_dist'] = d2d.deg

    # generate the source models
    srcs_df['src_dj'] = srcs_df.apply(
        get_source_models,
        pipeline_run=p_run,
        axis=1
    )
    # upload sources and related to DB
    upload_sources(p_run, srcs_df)

    # get db ids for sources
    srcs_df['id'] = srcs_df['src_dj'].apply(getattr, args=('id',))

    # write relations to parquet file
    related_df = srcs_df[['id', 'related_list']].explode(
        'related_list'
    ).rename(
        columns={'related_list': 'related_with'}
    )

    # need to replace relation source ids with db ids
    # as db ids is what's written to the association parquet
    related_indexes = related_df[related_df['related_with'] != -1].index.values

    related_df.loc[related_indexes, 'related_with'] = srcs_df.loc[
        related_df.loc[related_indexes, 'related_with'].values,
        'id'
    ].values

    related_df.to_parquet(
        os.path.join(p_run.path, 'relations.parquet')
    )

    # write sources to parquet file
    srcs_df = srcs_df.drop(['related_list', 'img_list'], axis=1)
    (
        srcs_df.drop('src_dj', axis=1)
        .to_parquet(os.path.join(p_run.path, 'sources.parquet'))
    )

    # update measurments with sources to get associations
    sources_df = (
        sources_df.drop('related', axis=1)
        .merge(srcs_df.rename(columns={'id': 'source_id'}), on='source')
        .merge(meas_dj_obj, on='id')
    )

    # Create Associan objects (linking measurements into single sources)
    # and insert in DB
    sources_df['assoc_dj'] = sources_df.apply(
        lambda row: Association(
            meas=row['meas_dj'],
            source=row['src_dj'],
            d2d=row['d2d'],
            dr=row['dr'],
        ), axis=1
    )
    # upload associations in DB
    upload_associations(sources_df['assoc_dj'])

    # write associations to parquet file
    sources_df.rename(columns={'id': 'meas_id'})[
        ['source_id', 'meas_id', 'd2d', 'dr']
    ].to_parquet(os.path.join(p_run.path, 'associations.parquet'))

    logger.info(
        'Total final operations time: %.2f seconds', timer.reset_init()
    )
