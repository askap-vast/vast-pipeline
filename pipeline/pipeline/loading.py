import os
import logging
import pandas as pd

from django.db import transaction

from ..image.main import SelavyImage
from ..models import Measurement
from .utils import (
    get_create_img, get_create_img_band, get_measurement_models
)


logger = logging.getLogger(__name__)


@transaction.atomic
def upload_images(selavy_paths, config, pipeline_run):
    '''
    carry the first part of the pipeline, by uploading all the images
    to the image table and populated band and skyregion objects
    '''
    images = []
    meas_dj_obj = pd.DataFrame()

    for path in selavy_paths:
        # STEP #1: Load image and measurements
        image = SelavyImage(
            path,
            selavy_paths[path],
            config=config
        )
        logger.info('read image %s', image.name)

        # 1.1 get/create the frequency band
        band_id = get_create_img_band(image)

        # 1.2 create image and skyregion entry in DB
        img, exists_f = get_create_img(pipeline_run, band_id, image)
        # add image to list
        images.append(img)
        if exists_f:
            logger.info(
                'image %s already processed, grab measurements',
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
        logger.info("Uploading to DB...")
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
            logger.info('bulk uploaded #%i measurements', len(out_bulk))

        # make a columns with the measurement id
        measurements['id'] = measurements.meas_dj.apply(
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
