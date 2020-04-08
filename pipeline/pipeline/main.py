import os
import operator
import logging

from astropy import units as u
from astropy.coordinates import Angle

from ..models import SurveySource
from .association import association
from .forced_extraction import forced_extraction
from .loading import upload_images


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
        self.img_paths = {}
        self.img_paths['selavy'] = {
            x:y for x,y in zip(config.IMAGE_FILES, config.SELAVY_FILES)
        }
        if config.MONITOR:
            self.img_paths['noise'] = {
                x:y for x,y in zip(
                    config.IMAGE_FILES,
                    config.NOISE_FILES
                )
            }
            self.img_paths['background'] = {
                x:y for x,y in zip(
                    config.IMAGE_FILES,
                    config.BACKGROUND_FILES
                )
            }

    def process_pipeline(self, p_run):
        img_skyreg_df, meas_dj_obj = upload_images(
            self.img_paths,
            self.config,
            p_run
        )

        # STEP #2: measurements association
        # 2.1 Associate Measurements with reference survey sources
        if SurveySource.objects.exists():
            pass

        # 2.2 Associate with other measurements
        limit = Angle(self.config.ASSOCIATION_RADIUS * u.arcsec)
        dr_limit = self.config.ASSOCIATION_DE_RUITER_RADIUS
        bw_limit = self.config.ASSOCIATION_BEAMWIDTH_LIMIT

        srcs_df, sources_df = association(
            p_run,
            img_skyreg_df,
            meas_dj_obj,
            limit,
            dr_limit,
            bw_limit,
            self.config,
        )

        # STEP #3: Run forced extraction/photometry
        if self.config.MONITOR:
            forced_extraction(srcs_df, sources_df, img_skyreg_df)

        pass
