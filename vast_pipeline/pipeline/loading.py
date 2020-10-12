import os
import logging
import pandas as pd

from django.db import transaction
from itertools import islice

from vast_pipeline.image.main import SelavyImage
from vast_pipeline.pipeline.generators import measurement_models_generator
from vast_pipeline.models import Association, Measurement, Source, RelatedSource
from .utils import (
    get_create_img, get_create_img_band
)
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


@transaction.atomic
def bulk_upload_model(djmodel, generator, batch_size=10_000, return_ids=False):
    '''
    bulk upload a pandas series of django models to db
    objs: pandas.Series
    djmodel: django.model
    '''
    bulk_ids = []
    while True:
        items = list(islice(generator, batch_size))
        if not items:
            break
        out_bulk = djmodel.objects.bulk_create(items)
        logger.info('Bulk created #%i %s', len(out_bulk), djmodel.__name__)
        # save the DB ids to return
        if return_ids:
            [bulk_ids.append(i.id) for i in out_bulk]

    if return_ids:
        return bulk_ids


def upload_images(paths, config, pipeline_run):
    '''
    carry the first part of the pipeline, by uploading all the images
    to the image table and populated band and skyregion objects
    '''
    timer = StopWatch()
    images = []
    skyregions = []
    bands = []

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
                    Measurement.objects.filter(forced=False, image__id=img.id),
                    name='meas_dj'
                )
                .to_frame()
            )
            measurements['id'] = measurements['meas_dj'].apply(lambda x: x.id)
            continue

        # 1.3 get the image measurements and save them in DB
        measurements = image.read_selavy(img)
        logger.info(
            'Processed measurements dataframe of shape: (%i, %i)',
            measurements.shape[0], measurements.shape[1]
        )

        # do a upload without evaluate the objects, that should be faster
        meas_dj_ids = bulk_upload_model(
            Measurement, measurement_models_generator(measurements),
            return_ids=True
        )

        # make a columns with the measurement id
        measurements['id'] = meas_dj_ids

        # save measurements to parquet file in pipeline run folder
        base_folder = os.path.dirname(img.measurements_path)
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)

        measurements.to_parquet(
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
    return images


def upload_sources(pipeline_run, sources):
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

    src_dj_ids = bulk_upload_model(Source, sources, return_ids=True)

    return src_dj_ids


def upload_related_sources(related):
    logger.info('Populate "related" field of sources...')
    bulk_upload_model(RelatedSource, related)


def upload_associations(associations_list):
    logger.info('Upload associations...')
    bulk_upload_model(Association, associations_list)
