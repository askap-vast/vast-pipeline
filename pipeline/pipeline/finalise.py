import logging

from pipeline.models import Association
from pipeline.utils.utils import StopWatch

from .loading import upload_associations, upload_sources
from .utils import get_source_models, parallel_groupby

logger = logging.getLogger(__name__)


def final_operations(sources_df, first_img, p_run, meas_dj_obj):
    timer = StopWatch()

    # calculate source fields
    logger.info(
        'Calculating statistics for %i sources...',
        sources_df.source.unique().shape[0]
    )
    timer.reset()
    srcs_df = parallel_groupby(sources_df, first_img)
    logger.info('Groupby-apply time: %.2f seconds', timer.reset())
    # fill NaNs as resulted from calculated metrics with 0
    srcs_df = srcs_df.fillna(0.)

    # generate the source models
    srcs_df['src_dj'] = srcs_df.apply(
        get_source_models,
        pipeline_run=p_run,
        axis=1
    )
    # upload sources and related to DB
    upload_sources(p_run, srcs_df)

    sources_df = (
        sources_df.drop('related', axis=1)
        .merge(srcs_df.drop('related_list', axis=1), on='source')
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

    logger.info(
        'Total final operations time: %.2f seconds', timer.reset_init()
    )
