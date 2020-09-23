import os
import logging
import pandas as pd

from django.db import transaction

from vast_pipeline.image.main import SelavyImage
from vast_pipeline.models import Association, Measurement, Source, RelatedSource
from .utils import (
    get_create_img, get_create_img_band, get_measurement_models
)
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


@transaction.atomic
def bulk_upload_model(objs, djmodel, batch_size=10_000):
    '''
    bulk upload a pandas series of django models to db
    objs: pandas.Series
    djmodel: django.model
    '''
    size = objs.size
    objs = objs.values.tolist()

    for idx in range(0, size, batch_size):
        out_bulk = djmodel.objects.bulk_create(
            objs[idx : idx + batch_size],
            batch_size
        )
        logger.info('Bulk created #%i %s', len(out_bulk), djmodel.__name__)


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
        with transaction.atomic():
            band = get_create_img_band(image)
        if band not in bands:
            bands.append(band)

        # 1.2 create image and skyregion entry in DB
        with transaction.atomic():
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
            measurements['id'] = measurements['meas_dj'].apply(lambda x: x.id)
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
        bulk_upload_model(measurements['meas_dj'], Measurement)

        # make a columns with the measurement id
        measurements['id'] = measurements['meas_dj'].apply(lambda x: x.id)
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
        del measurements, image, band, img

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


def upload_sources(pipeline_run, srcs_df):
    '''
    delete previous sources for given pipeline run and bulk upload
    new found sources as well as related sources
    '''
    # create sources in DB
    with transaction.atomic():
        if Source.objects.filter(run=pipeline_run).exists():
            logger.info('Removing objects from previous pipeline run')
            n_del, detail_del = (
                Source.objects.filter(run=pipeline_run).delete()
            )
            logger.info(
                ('Deleting all sources and related objects for this run. '
                 'Total objects deleted: %i'),
                n_del,
            )
            logger.debug('(type, #deleted): %s', detail_del)

    bulk_upload_model(srcs_df['src_dj'], Source)


def upload_related_sources(related):
    logger.info('Populate "related" field of sources...')
    bulk_upload_model(related, RelatedSource)


def upload_associations(associations_list):
    bulk_upload_model(associations_list, Association)
