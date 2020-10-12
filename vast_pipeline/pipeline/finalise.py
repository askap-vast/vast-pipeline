import os
import logging
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord

from vast_pipeline.models import Association, RelatedSource, Run
from vast_pipeline.utils.utils import StopWatch
from vast_pipeline.pipeline.generators import (
    source_models_generator,
    related_models_generator,
    association_models_generator
)

from .loading import (
    upload_associations, upload_sources, upload_related_sources
)
from .utils import parallel_groupby


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
        measurements and the association information.
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

    # add the separation distance in degrees
    srcs_df['n_neighbour_dist'] = d2d.deg

    # upload sources to DB using the source_models generator
    src_dj_ids = upload_sources(
        p_run, source_models_generator(srcs_df, pipeline_run=p_run)
    )

    # attach the DB IDs just obtained to the source dataframe
    srcs_df['id'] = src_dj_ids

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
        srcs_df.loc[srcs_df['related_list'] != -1, ['id', 'related_list']]
        .explode('related_list')
        .rename(
            columns={'id': 'from_source_id', 'related_list': 'to_source_id'}
        )
    )
    # for the column 'from_source_id', replace relation source ids with db id
    related_df['to_source_id'] = related_df['to_source_id'].map(
        srcs_df['id'].to_dict()
    )
    # drop relationships with the same source
    related_df = related_df[
        related_df['from_source_id'] != related_df['to_source_id']
    ]
    # write symmetrical relations to parquet
    related_df.to_parquet(
        os.path.join(p_run.path, 'relations.parquet'),
        index=False
    )

    # upload the relations using the related generator.
    upload_related_sources(
        related_models_generator(related_df)
    )

    del related_df

    # write sources to parquet file
    srcs_df = srcs_df.drop(['related_list', 'img_list'], axis=1)
    (
        srcs_df.set_index('id')# set the index to db ids, dropping the source idx
        .to_parquet(os.path.join(p_run.path, 'sources.parquet'))
    )

    # calculate total number of extracted sources
    nr_sources = srcs_df['id'].count()

    # update measurments with sources to get associations
    sources_df = (
        sources_df.drop('related', axis=1)
        .merge(srcs_df.rename(columns={'id': 'source_id'}), on='source')
    )

    # upload associations in DB using the generator
    upload_associations(
        association_models_generator(sources_df)
    )

    # write associations to parquet file
    sources_df.rename(columns={'id': 'meas_id'})[
        ['source_id', 'meas_id', 'd2d', 'dr']
    ].to_parquet(os.path.join(p_run.path, 'associations.parquet'))

    logger.info(
        'Total final operations time: %.2f seconds', timer.reset_init()
    )

    return nr_sources
