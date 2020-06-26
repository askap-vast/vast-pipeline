import os
import operator
import logging

from astropy import units as u
from astropy.coordinates import Angle

from ..models import SurveySource
from .association import association
from .new_sources import new_sources
from .forced_extraction import forced_extraction
from .finalise import final_operations
from .loading import upload_images
from .utils import get_src_skyregion_merged_df


logger = logging.getLogger(__name__)


class Pipeline():
    '''
    Holds all the state associated with a pipeline instance (usually
    just one is used)
    '''

    def __init__(self, config=None):
        '''
        We limit the size of the cube cache so we don't hit the max
        files open limit or use too much RAM
        '''
        self.config = config

        # A dictionary of path to Fits images, eg
        # "/data/images/I1233234.FITS" and selavy catalogues
        # Used as a cache to avoid reloading cubes all the time.
        self.img_paths = {}
        self.img_paths['selavy'] = {
            x:y for x,y in zip(config.IMAGE_FILES, config.SELAVY_FILES)
        }
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
        images, meas_dj_obj = upload_images(
            self.img_paths,
            self.config,
            p_run
        )

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

        sources_df = association(
            p_run,
            images,
            meas_dj_obj,
            limit,
            dr_limit,
            bw_limit,
            self.config,
        )

        # STEP #3: Merge sky regions and sources ready for
        # steps 4 and 5 below.
        missing_sources_df = get_src_skyregion_merged_df(
            sources_df,
            p_run
        )

        # STEP #4 New source analysis
        new_sources_df = new_sources(
            sources_df,
            missing_sources_df,
            p_run
        )

        # STEP #5: Run forced extraction/photometry if asked
        if self.config.MONITOR:
            sources_df, meas_dj_obj = forced_extraction(
                sources_df,
                self.config.ASTROMETRIC_UNCERTAINTY_RA / 3600.,
                self.config.ASTROMETRIC_UNCERTAINTY_DEC / 3600.,
                p_run,
                meas_dj_obj,
                missing_sources_df
            )

        # STEP #6: finalise the df getting unique sources, calculating
        # metrics and upload data to database
        final_operations(
            sources_df,
            images[0].name,
            p_run,
            meas_dj_obj,
            new_sources_df
        )

        pass
