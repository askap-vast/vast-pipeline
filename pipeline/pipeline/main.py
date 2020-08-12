import os
import operator
import logging

from astropy import units as u
from astropy.coordinates import Angle

from django.conf import settings
from django.db import transaction

from importlib.util import spec_from_file_location, module_from_spec

from ..models import Run, SurveySource
from .association import association
from .new_sources import new_sources
from .forced_extraction import forced_extraction
from .finalise import final_operations
from .loading import upload_images
from .utils import get_src_skyregion_merged_df
from .errors import MaxPipelineRunsError, PipelineConfigError


logger = logging.getLogger(__name__)


class Pipeline():
    '''
    Instance of a pipeline. All the methods runs the pipeline opearations,
    such as association
    '''

    def __init__(self, name, config_path):
        '''
        Initialise the pipeline with attributed such as configuration file
        path, name, and list of images and related files (e.g. selavy)
        '''
        self.name = name
        self.config = self.load_cfg(config_path)

        # A dictionary of path to Fits images, eg
        # "/data/images/I1233234.FITS" and selavy catalogues
        # Used as a cache to avoid reloading cubes all the time.
        self.img_paths = {}
        self.img_paths['selavy'] = {
            x:y for x,y in zip(
                self.config.IMAGE_FILES,
                self.config.SELAVY_FILES
            )
        }
        self.img_paths['noise'] = {
            x:y for x,y in zip(
                self.config.IMAGE_FILES,
                self.config.NOISE_FILES
            )
        }
        self.img_paths['background'] = {
            x:y for x,y in zip(
                self.config.IMAGE_FILES,
                self.config.BACKGROUND_FILES
            )
        }

    @staticmethod
    def load_cfg(cfg):
        """
        Check the given Config path. Throw exception if any problems
        return the config object as module/class
        """
        if not os.path.exists(cfg):
            raise PipelineConfigError(
                'pipeline run config file not existent'
            )

        # load the run config as a Python module
        spec = spec_from_file_location('run_config', cfg)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)

        return mod


    def validate_cfg(self):
        """
        validate a pipeline run configuration against default parameters and
        for different settings (e.g. force extraction)
        """
        # do sanity checks
        if (getattr(self.config, 'IMAGE_FILES') and
            getattr(self.config, 'SELAVY_FILES')):
            for lst in ['IMAGE_FILES', 'SELAVY_FILES']:
                for file in getattr(self.config, lst):
                    if not os.path.exists(file):
                        raise PipelineConfigError(
                            f'file:\n{file}\ndoes not exists!'
                        )
        else:
            raise PipelineConfigError(
                'no image file paths passed or Selavy file paths!'
            )

        source_finder_names = settings.SOURCE_FINDERS
        if getattr(self.config, 'SOURCE_FINDER') not in source_finder_names:
            raise PipelineConfigError((
                f"Invalid source finder {getattr(self.config, 'SOURCE_FINDER')}."
                f' Choices are {source_finder_names}'
            ))

        association_methods = ['basic', 'advanced', 'deruiter']
        if getattr(self.config, 'ASSOCIATION_METHOD') not in association_methods:
            raise PipelineConfigError((
                'ASSOCIATION_METHOD is not valid!'
                " Must be a value contained in: {}.".format(association_methods)
            ))

        # validate min_new_source_sigma value
        if 'NEW_SOURCE_MIN_SIGMA' not in dir(self.config):
            raise PipelineConfigError('NEW_SOURCE_MIN_SIGMA must be defined!')

        # validate Forced extraction settings
        if getattr(self.config, 'MONITOR') and not(
            getattr(self.config, 'BACKGROUND_FILES') and getattr(self.config, 'NOISE_FILES')
            ):
            raise PipelineConfigError(
                'Expecting list of background MAP and RMS files!'
            )
        else:
            if 'MONITOR_MIN_SIGMA' not in dir(self.config):
                raise PipelineConfigError('MONITOR_MIN_SIGMA must be defined!')
            if 'MONITOR_EDGE_BUFFER_SCALE' not in dir(self.config):
                raise PipelineConfigError(
                    'MONITOR_EDGE_BUFFER_SCALE must be defined!'
                )
            for lst in ['BACKGROUND_FILES', 'NOISE_FILES']:
                for file in getattr(self.config, lst):
                    if not os.path.exists(file):
                        raise PipelineConfigError(
                            f'file:\n{file}\ndoes not exists!'
                        )

        # validate every config from the config template
        for key in [k for k in dir(self.config) if k.isupper()]:
            if key.lower() not in settings.PIPE_RUN_CONFIG_DEFAULTS.keys():
                raise PipelineConfigError(
                    f'configuration not valid, missing key: {key}!'
                )

        pass

    def process_pipeline(self, p_run):
        # upload/retrieve image data
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
            self.config.NEW_SOURCE_MIN_SIGMA,
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
                missing_sources_df,
                self.config.MONITOR_MIN_SIGMA,
                self.config.MONITOR_EDGE_BUFFER_SCALE,
            )

        # STEP #6: finalise the df getting unique sources, calculating
        # metrics and upload data to database
        nr_sources = final_operations(
            sources_df,
            images[0].name,
            p_run,
            meas_dj_obj,
            new_sources_df
        )

        # calculate number processed images
        nr_img_processed = len(images)

        # update pipeline run with the nr images and sources
        with transaction.atomic():
            p_run.n_images = nr_img_processed
            p_run.n_sources = nr_sources
            p_run.save()

        pass

    @staticmethod
    def check_current_runs():
        if Run.objects.check_max_runs(settings.MAX_PIPELINE_RUNS):
            raise MaxPipelineRunsError

    @staticmethod
    def set_status(pipe_run, status=None):
        choices = [x[0] for x in Run._meta.get_field('status').choices]
        if status and status in choices and pipe_run.status != status:
            with transaction.atomic():
                pipe_run.status = status
                pipe_run.save()
