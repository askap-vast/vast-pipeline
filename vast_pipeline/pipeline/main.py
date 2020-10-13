import os
import operator
import logging

from astropy import units as u
from astropy.coordinates import Angle

import pandas as pd

from django.conf import settings
from django.db import transaction

from importlib.util import spec_from_file_location, module_from_spec

from vast_pipeline.models import Run, SurveySource
from .association import association, parallel_association
from .new_sources import new_sources
from .forced_extraction import forced_extraction
from .finalise import final_operations
from .loading import upload_images
from .utils import (
    get_src_skyregion_merged_df,
    group_skyregions,
    get_parallel_assoc_image_df
)
from vast_pipeline.utils.utils import convert_list_to_dict

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
        # The epoch_based parameter below is for
        # if the user has entered just lists we don't have
        # access to the dates until the Image instances are
        # created. So we flag this as true so that we can
        # reorder the epochs once the date information is available.
        # It is also recorded in the database such that there is a record
        # of the fact that the run was processed in an epoch based mode.
        self.epoch_based = False

        # Check if provided files are lists and convert to
        # dictionaries if so
        for cfg_key in [
            'IMAGE_FILES', 'SELAVY_FILES',
            'BACKGROUND_FILES', 'NOISE_FILES'
        ]:
            if isinstance(getattr(self.config, cfg_key), list):
                setattr(
                    self.config,
                    cfg_key,
                    convert_list_to_dict(
                        getattr(self.config, cfg_key)
                    )
                )
            elif isinstance(getattr(self.config, cfg_key), dict):
                # Set to True if dictionaries are passed.
                self.epoch_based = True
            else:
                raise PipelineConfigError((
                    'Unknown images entry format!'
                    f' Must be a list or dictionary.'
                ))

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
        # validate every config from the config template
        config_keys = [k for k in dir(self.config) if k.isupper()]
        valid_keys = settings.PIPE_RUN_CONFIG_DEFAULTS.keys()

        # Check that there are no 'unknown' options given by the user
        for key in config_keys:
            if key.lower() not in valid_keys:
                raise PipelineConfigError(
                    f'Configuration not valid, unknown option: {key}!'
                )
        # Check that all options are provided by the user
        for key in settings.PIPE_RUN_CONFIG_DEFAULTS.keys():
            if key.upper() not in config_keys:
                raise PipelineConfigError(
                    f'Configuration not valid, missing option: {key.upper()}!'
                )

        # do sanity checks
        if (getattr(self.config, 'IMAGE_FILES') and
            getattr(self.config, 'SELAVY_FILES') and
            getattr(self.config, 'NOISE_FILES')):
            img_f_list = getattr(self.config, 'IMAGE_FILES')
            img_f_list = [
                item for sublist in img_f_list.values() for item in sublist
            ] # creates a flat list of all the dictionary value lists
            for lst in ['IMAGE_FILES', 'SELAVY_FILES', 'NOISE_FILES']:
                cfg_list = getattr(self.config, lst)
                cfg_list = [
                    item for sublist in cfg_list.values() for item in sublist
                ]

                # checks for duplicates in each list
                if len(set(cfg_list)) != len(cfg_list):
                    raise PipelineConfigError(f'Duplicated files in: \n{lst}')

                # check if nr of files match nr of images
                if len(cfg_list) != len(img_f_list):
                    raise PipelineConfigError(
                        f'Number of {lst} files not matching number of images'
                    )

                for key in getattr(self.config, lst):
                    for file in getattr(self.config, lst)[key]:
                        if not os.path.exists(file):
                            raise PipelineConfigError(
                                f'file:\n{file}\ndoes not exists!'
                            )
        else:
            raise PipelineConfigError(
                'No image and/or Selavy and/or noise file paths passed!'
            )

        source_finder_names = settings.SOURCE_FINDERS
        if getattr(self.config, 'SOURCE_FINDER') not in source_finder_names:
            raise PipelineConfigError((
                f"Invalid source finder {getattr(self.config, 'SOURCE_FINDER')}."
                f' Choices are {source_finder_names}'
            ))

        association_methods = settings.DEFAULT_ASSOCIATION_METHODS
        if getattr(self.config, 'ASSOCIATION_METHOD') not in association_methods:
            raise PipelineConfigError((
                'ASSOCIATION_METHOD is not valid!'
                f' Must be a value contained in: {association_methods}.'
            ))

        # validate Forced extraction settings
        if getattr(self.config, 'MONITOR'):
            if not getattr(self.config, 'BACKGROUND_FILES'):
                raise PipelineConfigError(
                    'Expecting list of background MAP files!'
                )

        # if defined, check background files regardless of monitor
        if getattr(self.config, 'BACKGROUND_FILES'):
            # check for duplicated values
            backgrd_f_list = getattr(self.config, 'BACKGROUND_FILES')
            backgrd_f_list = [
                item for sublist in backgrd_f_list.values() for item in sublist
            ]
            if len(set(backgrd_f_list)) != len(backgrd_f_list):
                raise PipelineConfigError(
                    'Duplicated files in: BACKGROUND_FILES list'
                )
            # check if provided more background files than images
            if len(backgrd_f_list) != len(img_f_list):
                raise PipelineConfigError((
                    'Number of BACKGROUND_FILES different from number of'
                    ' IMAGE_FILES files'
                ))

            for key in getattr(self.config, 'BACKGROUND_FILES'):
                for file in getattr(self.config, 'BACKGROUND_FILES')[key]:
                    if not os.path.exists(file):
                        raise PipelineConfigError(
                            f'file:\n{file}\ndoes not exists!'
                        )
        pass

    def match_images_to_data(self):
        """
        Loops through images and matches the selavy, noise and bkg images.
        Assumes that user has enteted images and other data in the same order.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.img_paths = {
            'selavy': {},
            'noise': {},
            'background': {}
        }
        self.img_epochs = {}

        for key in sorted(self.config.IMAGE_FILES.keys()):
            for x,y in zip(
                self.config.IMAGE_FILES[key],
                self.config.SELAVY_FILES[key]
            ):
                self.img_paths['selavy'][x] = y

            for x,y in zip(
                self.config.IMAGE_FILES[key],
                self.config.NOISE_FILES[key]
            ):
                self.img_paths['noise'][x] = y

            # check if backgound files have been given before
            # attempting to match
            if key in self.config.BACKGROUND_FILES:
                for x,y in zip(
                    self.config.IMAGE_FILES[key],
                    self.config.BACKGROUND_FILES[key]
                ):
                    self.img_paths['background'][x] = y

            for x in self.config.IMAGE_FILES[key]:
                self.img_epochs[os.path.basename(x)] = key

    def process_pipeline(self, p_run):
        logger.info(f'Epoch based association: {self.epoch_based}')

        # Update epoch based flag to not cause user confusion when running
        # the pipeline (i.e. if it was only updated at the end).
        if self.epoch_based:
            with transaction.atomic():
                p_run.epoch_based = self.epoch_based
                p_run.save()

        # Match the image files to the respective selavy, noise and bkg files.
        # Do this after validation is successful.
        self.match_images_to_data()

        # upload/retrieve image data
        images, skyregs_df = upload_images(
            self.img_paths,
            self.config,
            p_run
        )

        # STEP #2: measurements association
        # order images by time
        images.sort(key=operator.attrgetter('datetime'))

        # If the user has given lists we need to reorder the
        # image epochs such that they are in date order.
        if self.epoch_based is False:
            self.img_epochs = {}
            for i, img in enumerate(images):
                self.img_epochs[img.name] = i + 1

        image_epochs = [
            self.img_epochs[img.name] for img in images
        ]
        limit = Angle(self.config.ASSOCIATION_RADIUS * u.arcsec)
        dr_limit = self.config.ASSOCIATION_DE_RUITER_RADIUS
        bw_limit = self.config.ASSOCIATION_BEAMWIDTH_LIMIT
        duplicate_limit = Angle(
            self.config.ASSOCIATION_EPOCH_DUPLICATE_RADIUS * u.arcsec
        )

        # 2.1 Check if sky regions to be associated can be
        # split into connected point groups
        skyregion_groups = group_skyregions(
            skyregs_df[['id', 'centre_ra', 'centre_dec', 'xtr_radius']]
        )
        n_skyregion_groups = skyregion_groups[
            'skyreg_group'
        ].unique().shape[0]

        # 2.2 Associate with other measurements
        if self.config.ASSOCIATION_PARALLEL and n_skyregion_groups > 1:
            images_df = get_parallel_assoc_image_df(
                images, skyregion_groups
            )
            images_df['epoch'] = image_epochs

            sources_df = parallel_association(
                images_df,
                limit,
                dr_limit,
                bw_limit,
                duplicate_limit,
                self.config,
                n_skyregion_groups,
            )
        else:
            images_df = pd.DataFrame.from_dict(
                {
                    'image_dj': images,
                    'epoch': image_epochs
                }
            )

            images_df['skyreg_id'] = images_df['image_dj'].apply(
                lambda x: x.skyreg_id
            )

            sources_df = association(
                images_df,
                limit,
                dr_limit,
                bw_limit,
                duplicate_limit,
                self.config,
            )

        # 2.3 Associate Measurements with reference survey sources
        if SurveySource.objects.exists():
            pass

        # Obtain the number of selavy measurements for the run
        # n_selavy_measurements = sources_df.
        nr_selavy_measurements = sources_df['id'].unique().shape[0]

        # STEP #3: Merge sky regions and sources ready for
        # steps 4 and 5 below.
        missing_source_cols = [
            'source', 'datetime', 'image', 'epoch',
            'interim_ew', 'weight_ew', 'interim_ns', 'weight_ns'
        ]
        missing_sources_df = get_src_skyregion_merged_df(
            sources_df[missing_source_cols],
            images_df,
            skyregs_df,
        )

        # STEP #4 New source analysis
        new_sources_df = new_sources(
            sources_df,
            missing_sources_df,
            self.config.NEW_SOURCE_MIN_SIGMA,
            self.config.MONITOR_EDGE_BUFFER_SCALE,
            p_run
        )

        # Drop column no longer required in missing_sources_df.
        missing_sources_df = (
            missing_sources_df.drop(['in_primary'], axis=1)
        )

        # STEP #5: Run forced extraction/photometry if asked
        if self.config.MONITOR:
            (
                sources_df,
                nr_forced_measurements
            ) = forced_extraction(
                sources_df,
                self.config.ASTROMETRIC_UNCERTAINTY_RA / 3600.,
                self.config.ASTROMETRIC_UNCERTAINTY_DEC / 3600.,
                p_run,
                missing_sources_df,
                self.config.MONITOR_MIN_SIGMA,
                self.config.MONITOR_EDGE_BUFFER_SCALE,
                self.config.MONITOR_CLUSTER_THRESHOLD,
                self.config.MONITOR_ALLOW_NAN
            )

        del missing_sources_df

        # STEP #6: finalise the df getting unique sources, calculating
        # metrics and upload data to database
        nr_sources = final_operations(
            sources_df,
            p_run,
            new_sources_df
        )

        # calculate number processed images
        nr_img_processed = len(images)

        # update pipeline run with the nr images and sources
        with transaction.atomic():
            p_run.n_images = nr_img_processed
            p_run.n_sources = nr_sources
            p_run.n_selavy_measurements = nr_selavy_measurements
            p_run.n_forced_measurements = (
                nr_forced_measurements if self.config.MONITOR else 0
            )
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
