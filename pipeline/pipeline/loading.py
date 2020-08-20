import os
import logging
import pandas as pd

from django.db import transaction

from ..image.main import SelavyImage
from ..models import Association, Measurement, Source, RelatedSource
from .utils import (
    get_create_img, get_create_img_band, get_measurement_models
)
from ..utils.utils import StopWatch
from ..utils.model import bulk_upload_model


logger = logging.getLogger(__name__)


@transaction.atomic
def upload_images(paths, config, pipeline_run):
    '''
    carry the first part of the pipeline, by uploading all the images
    to the image table and populated band and skyregion objects
    '''
    timer = StopWatch()
    images = []
    skyregions = []
    bands = []
    meas_dj_obj = pd.DataFrame()

    for path in paths['selavy']:
        # STEP #1: Load image and measurements
        image = SelavyImage(
            path,
            paths,
            config=config
        )
        logger.info('Reading image %s ...', image.name)

        # 1.1 get/create the frequency band
        band = get_create_img_band(image)
        if band not in bands:
            bands.append(band)

        # 1.2 create image and skyregion entry in DB
        img, skyreg, exists_f = get_create_img(
            pipeline_run, band.id, image
        )

        # add image and skyregion to respective lists
        images.append(img)
        if skyreg not in skyregions:
            skyregions.append(skyreg)
        if exists_f:
            logger.info(
                'Image %s already processed, grab measurements',
                img.name
            )
            # grab the measurements and skip to process next image
            measurements = (
                pd.Series(
                    Measurement.objects.filter(image__id=img.id),
                    name='meas_dj'
                )
                .to_frame()
            )
            measurements['id'] = measurements.meas_dj.apply(
                getattr, args=('id',)
            )
            meas_dj_obj = meas_dj_obj.append(measurements)
            continue

        # 1.3 get the image measurements and save them in DB
        measurements = image.read_selavy(img)
        logger.info(
            'Processed measurements dataframe of shape: (%i, %i)',
            measurements.shape[0], measurements.shape[1]
        )

        # do DB bulk create
        logger.info('Uploading to DB...')
        measurements['meas_dj'] = measurements.apply(
            get_measurement_models, axis=1
        )
        # do a upload without evaluate the objects, that should be faster
        # see https://docs.djangoproject.com/en/2.2/ref/models/querysets/
        batch_size = 10_000
        for idx in range(0, measurements['meas_dj'].size, batch_size):
            out_bulk = Measurement.objects.bulk_create(
                measurements['meas_dj'].iloc[
                    idx : idx + batch_size
                ].values.tolist(),
                batch_size
            )
            logger.info('Bulk uploaded #%i measurements', len(out_bulk))

        # make a columns with the measurement id
        measurements['id'] = measurements['meas_dj'].apply(
            getattr, args=('id',)
        )
        meas_dj_obj = meas_dj_obj.append(
            measurements.loc[:, ['id','meas_dj']]
        )

        # save measurements to parquet file in pipeline run folder
        base_folder = os.path.dirname(img.measurements_path)
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)

        measurements.drop('meas_dj', axis=1).to_parquet(
            img.measurements_path,
            index=False
        )
        del measurements, image, band, img, out_bulk

    # write images parquet file under pipeline run folder
    images_df = pd.DataFrame(map(lambda x: x.__dict__, images))
    images_df = images_df.drop('_state', axis=1)
    images_df.to_parquet(
        os.path.join(config.PIPE_RUN_PATH, 'images.parquet'),
        index=False
    )
    # write skyregions parquet file under pipeline run folder
    skyregs_df = pd.DataFrame(map(lambda x: x.__dict__, skyregions))
    skyregs_df = skyregs_df.drop('_state', axis=1)
    skyregs_df.to_parquet(
        os.path.join(config.PIPE_RUN_PATH, 'skyregions.parquet'),
        index=False
    )
    # write skyregions parquet file under pipeline run folder
    bands_df = pd.DataFrame(map(lambda x: x.__dict__, bands))
    bands_df = bands_df.drop('_state', axis=1)
    bands_df.to_parquet(
        os.path.join(config.PIPE_RUN_PATH, 'bands.parquet'),
        index=False
    )

    logger.info(
        'Total images upload/loading time: %.2f seconds',
        timer.reset_init()
    )
    return images, meas_dj_obj


@transaction.atomic
def upload_sources(pipeline_run, srcs_df):
    '''
    delete previous sources for given pipeline run and bulk upload
    new found sources as well as related sources
    '''
    # create sources in DB
    # TODO remove deleting existing sources
    if Source.objects.filter(run=pipeline_run).exists():
        logger.info('Removing objects from previous pipeline run')
        n_del, detail_del = Source.objects.filter(run=pipeline_run).delete()
        logger.info(
            ('Deleting all sources and related objects for this run. '
             'Total objects deleted: %i'),
            n_del,
        )
        logger.debug('(type, #deleted): %s', detail_del)

    logger.info('Uploading associations to db...')
    batch_size = 10_000
    for idx in range(0, srcs_df['src_dj'].size, batch_size):
        out_bulk = Source.objects.bulk_create(
            srcs_df['src_dj'].iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('Bulk created #%i sources', len(out_bulk))


def upload_related_sources(related):
    logger.info('Populate "related" field of sources...')
    bulk_upload_model(related, RelatedSource)


@transaction.atomic
def upload_associations(associations_list):
    batch_size = 10_000
    for idx in range(0, associations_list.size, batch_size):
        out_bulk = Association.objects.bulk_create(
            associations_list.iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('Bulk created #%i associations', len(out_bulk))
