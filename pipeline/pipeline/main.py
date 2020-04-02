import os
import operator
import logging

import pandas as pd
from astropy import units as u
from astropy.coordinates import Angle

from ..image.main import SelavyImage
from ..models import Measurement, SurveySource
from .association import association

from .utils import (
    get_create_img, get_create_img_band, get_create_skyreg,
    get_measurement_models
)


logger = logging.getLogger(__name__)


class Pipeline():
    '''
    Holds all the state associated with a pipeline instance (usually
    just one is used)
    '''

    def __init__(self, max_img=10, config=None):
        '''
        We limit the size of the cube cache so we don't hit the max
        files open limit or use too much RAM
        '''
        self.max_img = max_img
        self.config = config
        if self.config.MAX_BACKWARDS_MONITOR_IMAGES:
            self.max_img=self.config.MAX_BACKWARDS_MONITOR_IMAGES + 1

        # A dictionary of path to Fits images, eg
        # "/data/images/I1233234.FITS" and selavy catalogues
        # Used as a cache to avoid reloading cubes all the time.
        self.img_selavy_paths = {
            x:y for x,y in zip(config.IMAGE_FILES, config.SELAVY_FILES)
        }

    def process_pipeline(self, p_run):
        images = []
        meas_dj_obj = pd.DataFrame()
        for path in self.img_selavy_paths:
            # STEP #1: Load image and measurements
            image = SelavyImage(
                path,
                self.img_selavy_paths[path],
                config=self.config
            )
            logger.info('read image %s', image.name)

            # 1.1 get/create the frequency band
            band_id = get_create_img_band(image)

            # 1.2 create image and skyregion entry in DB
            img, exists_f = get_create_img(p_run, band_id, image)
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

        # STEP #2: measurements association
        # 2.1 Associate Measurements with reference survey sources
        if SurveySource.objects.exists():
            pass

        # 2.2 Associate with other measurements
        # order images by time
        images.sort(key=operator.attrgetter('datetime'))
        limit = Angle(self.config.ASSOCIATION_RADIUS * u.arcsec)
        dr_limit = self.config.ASSOCIATION_DE_RUITER_RADIUS
        bw_limit = self.config.ASSOCIATION_BEAMWIDTH_LIMIT

        association(
            p_run,
            images,
            meas_dj_obj,
            limit,
            dr_limit,
            bw_limit,
            self.config,
        )

        # STEP #3: ...
        pass
