import os
import logging
import pandas as pd

from django.db import transaction

from ..image.main import SelavyImage
from ..models import Association, Measurement, Source
from .utils import (
    get_create_img, get_create_img_band, get_measurement_models
)


logger = logging.getLogger(__name__)


@transaction.atomic
def upload_images(paths, config, pipeline_run):
    '''
    carry the first part of the pipeline, by uploading all the images
    to the image table and populated band and skyregion objects
    '''
    images = []
    meas_dj_obj = pd.DataFrame()

    for path in paths['selavy']:
        # STEP #1: Load image and measurements
        image = SelavyImage(
            path,
            paths['selavy'][path],
            config=config
        )
        logger.info('Reading image %s ...', image.name)

        # 1.1 get/create the frequency band
        band_id = get_create_img_band(image)

        # 1.2 create image and skyregion entry in DB
        img, exists_f = get_create_img(pipeline_run, band_id, image)
        # add noise and background paths if necessary
        if config.MONITOR and (
            img.noise_path == '' or img.background_path == ''
            ):
            img.noise_path = paths['noise'][path]
            img.background_path = paths['background'][path]
            logger.info(
                'Updating image model with noise and background paths...'
            )
            img.save(update_fields=['noise_path', 'background_path'])

        # add image to list
        images.append(img)
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
        for idx in range(0, measurements.meas_dj.size, batch_size):
            out_bulk = Measurement.objects.bulk_create(
                measurements.meas_dj.iloc[idx : idx + batch_size].values.tolist(),
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
        if not os.path.exists(os.path.dirname(img.measurements_path)):
            os.mkdir(os.path.dirname(img.measurements_path))

        measurements.drop('meas_dj', axis=1).to_parquet(
            img.measurements_path,
            index=False
        )
        del measurements, image, band_id, img, out_bulk

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

    # add source related object in DB
    logger.info('Populate "related" field of sources...')
    related_df = srcs_df.loc[
        srcs_df['related_list'] != -1, ['related_list', 'src_dj']
    ]
    for idx, row in related_df.iterrows():
        for src_id in row['related_list']:
            try:
                row['src_dj'].related.add(srcs_df.at[src_id, 'src_dj'])
            except Exception as e:
                logger.debug('Error in related update:\n%s', e)
                pass


@transaction.atomic
def upload_associations(associations_list):
    batch_size = 10_000
    for idx in range(0, associations_list.size, batch_size):
        out_bulk = Association.objects.bulk_create(
            associations_list.iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('Bulk created #%i associations', len(out_bulk))
