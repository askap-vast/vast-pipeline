import os
import operator
import logging
import pandas as pd

from types import ModuleType
from typing import List, Tuple
from astropy import units as u
from astropy.coordinates import Angle
from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import User
from importlib.util import spec_from_file_location, module_from_spec

from vast_pipeline.models import Run, SurveySource
from vast_pipeline.utils.utils import convert_list_to_dict

from .association import association, parallel_association
from .errors import MaxPipelineRunsError, PipelineConfigError
from .forced_extraction import forced_extraction
from .finalise import final_operations
from .loading import make_upload_images
from .new_sources import new_sources
from .utils import (
    get_src_skyregion_merged_df,
    group_skyregions,
    get_parallel_assoc_image_df
)


logger = logging.getLogger(__name__)


class Pipeline():
    '''
    Instance of a pipeline. All the methods runs the pipeline opearations,
    such as association
    '''

    def __init__(self, name: str, config_path: str):
        '''
        Initialise the pipeline with attributed such as configuration file
        path, name, and list of images and related files (e.g. selavy).
        Load the configuration file as a Python module. Transform list
        of images to dictionary if not defined as such in the configuration.

        Parameters
        ----------
        name : str
            A string with the name of the pipeline
        config_path : str
            A sring with the path of the pipeline configuration file
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
        self.config, self.epoch_based = self.check_for_epoch_based(self.config)

    @staticmethod
    def load_cfg(cfg: str) -> ModuleType:
        """
        Check the given Config path. Throw exception if any problems
        return the config object as module/class

        Parameters
        ----------
        cfg : str
            A string with the path of the pipeline configuration file

        Returns
        -------
        ModuleType
            The pipeline configuration as a python module (e.g. can
            access the attribute using .myattr)

        Raises
        ------
        PipelineConfigError
            Error if pipeline configuration file does not exist
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

    @staticmethod
    def _get_valid_keys(upper: bool = False) -> List[str]:
        """
        Obtains the valid config keys from the template config.

        Parameters
        ----------
        upper : bool
            Return all the keys in upper formatt.

        Returns
        -------
        valid_keys : List[str]
            List of valid keys.
        """
        valid_keys = settings.PIPE_RUN_CONFIG_DEFAULTS.keys()
        if upper:
            valid_keys = [i.upper() for i in valid_keys]

        return valid_keys

    @staticmethod
    def check_for_epoch_based(cfg: ModuleType) -> Tuple['config', bool]:
        # Config typing above is unknown what to put.
        """
        Checks whether the images have been provided in a Dictionary format
        which means that epoch_based has been requested. If they have been
        provided with just lists then the inputs are converted to dictionaries
        with an epoch defined for each individual image.

        Parameters
        ----------
        cfg : ModuleType
            The config object.

        Returns
        -------
        cfg, epoch_based : self.config, bool.
            The config (with converted List -> Dict inputs if required) and
            epoch_based boolean flag.
        """
        epoch_based = False

        for cfg_key in [
            'IMAGE_FILES', 'SELAVY_FILES',
            'BACKGROUND_FILES', 'NOISE_FILES'
        ]:
            if isinstance(getattr(cfg, cfg_key), list):
                setattr(
                    cfg,
                    cfg_key,
                    convert_list_to_dict(getattr(cfg, cfg_key))
                )
            elif isinstance(getattr(cfg, cfg_key), dict):
                # Set to True if dictionaries are passed.
                epoch_based = True
            else:
                raise PipelineConfigError((
                    'Unknown images entry format!'
                    f' Must be a list or dictionary.'
                ))

        return cfg, epoch_based

    def check_prev_config_diff(self, p_run_path: str) -> bool:
        """
        Checks if the previous config file differs from the current config
        file. Used in add mode. Only returns true if the images are different
        and the other general settings are the same (the requirement for add
        mode). Otherwise False is returned.

        Parameters
        ----------
        p_run_path : str
            The path of the pipeline run where the parquets are stored.

        Returns
        -------
        bool : bool
            True if images are different but general settings are the same.
            Otherwise False is returned.
        """
        valid_keys = self._get_valid_keys(upper=True)

        prev_config, _ = self.check_for_epoch_based(
            self.load_cfg(os.path.join(p_run_path, 'config_prev.py')))
        prev_config_dict = {k: getattr(prev_config, k) for k in valid_keys}

        current_config_dict = {k: getattr(self.config, k) for k in valid_keys}

        if prev_config_dict == current_config_dict:
            return True

        image_check = (
            prev_config_dict['IMAGE_FILES']
            == current_config_dict['IMAGE_FILES']
        )

        for i in [
            'IMAGE_FILES', 'SELAVY_FILES', 'NOISE_FILES', 'BACKGROUND_FILES'
        ]:
            prev_config_dict.pop(i)
            current_config_dict.pop(i)

        settings_check = prev_config_dict == current_config_dict

        if not image_check and settings_check:
            return False

        return True


    def validate_cfg(self, user: User = None) -> None:
        """
        validate a pipeline run configuration against default parameters and
        for different settings (e.g. force extraction)

        Parameters
        ----------
        user : User, optional
            The User of the request if made through the UI. Defaults to None.

        Returns
        -------
        None
        """
        # validate every config from the config template
        config_keys = [k for k in dir(self.config) if k.isupper()]
        valid_keys = self._get_valid_keys()

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
        if (
            getattr(self.config, 'IMAGE_FILES') and
            getattr(self.config, 'SELAVY_FILES') and
            getattr(self.config, 'NOISE_FILES')
        ):
            img_f_list = getattr(self.config, 'IMAGE_FILES')
            img_f_list = [
                item for sublist in img_f_list.values() for item in sublist
            ] # creates a flat list of all the dictionary value lists
            len_img_f_list = len(img_f_list)
            # maximum number of images check. If the user is `None` then it
            # means the run was initiated through the command line hence no
            # check is performed.
            if (
                user is not None
                and len_img_f_list > settings.MAX_PIPERUN_IMAGES
            ):
                if user.is_staff:
                    logger.warning(
                        'Maximum number of images'
                        f' ({settings.MAX_PIPERUN_IMAGES}) rule bypassed with'
                        ' admin status.'
                    )
                else:
                    raise PipelineConfigError(
                        f'The number of images entered ({len_img_f_list})'
                        ' exceeds the maximum number of images currently'
                        f' allowed ({settings.MAX_PIPERUN_IMAGES}). Please ask'
                        ' an administrator for advice on processing your run'
                    )
            for lst in ['IMAGE_FILES', 'SELAVY_FILES', 'NOISE_FILES']:
                cfg_list = getattr(self.config, lst)
                cfg_list = [
                    item for sublist in cfg_list.values() for item in sublist
                ]

                # checks for duplicates in each list
                if len(set(cfg_list)) != len(cfg_list):
                    raise PipelineConfigError(f'Duplicated files in: \n{lst}')

                # check if nr of files match nr of images
                if len(cfg_list) != len_img_f_list:
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

        # need more than 1 image file to generate a lightcurve
        if len(getattr(self.config, 'IMAGE_FILES')) < 2:
            raise PipelineConfigError(
                'Number of image files needs to be larger than 1!'
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
            if len(backgrd_f_list) != len_img_f_list:
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
        if self.add_mode:
            logger.info('Running in image add mode.')

        # Update epoch based flag to not cause user confusion when running
        # the pipeline (i.e. if it was only updated at the end). It is not
        # updated if the pipeline is being run in add mode.
        if self.epoch_based and not self.add_mode:
            with transaction.atomic():
                p_run.epoch_based = self.epoch_based
                p_run.save()

        # Match the image files to the respective selavy, noise and bkg files.
        # Do this after validation is successful.
        self.match_images_to_data()

        # upload/retrieve image data
        images, skyregs_df = make_upload_images(
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

        # Get already done images if in add mode
        if self.add_mode:
            done_images_df = pd.read_parquet(
                self.previous_parquets['images'], columns=['id', 'name']
            )
            done_source_ids = pd.read_parquet(
                self.previous_parquets['sources'],
                columns=['wavg_ra']
            ).index.tolist()
        else:
            done_images_df = None
            done_source_ids = None

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
                self.add_mode,
                self.previous_parquets,
                done_images_df,
                done_source_ids
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

            images_df['image_name'] = images_df['image_dj'].apply(
                lambda x: x.name
            )

            sources_df = association(
                images_df,
                limit,
                dr_limit,
                bw_limit,
                duplicate_limit,
                self.config,
                self.add_mode,
                self.previous_parquets,
                done_images_df
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
        # need to make sure no forced measurments are being passed which
        # could happen in add mode, otherwise the wrong detection image is
        # assigned.
        missing_sources_df = get_src_skyregion_merged_df(
            sources_df.loc[sources_df['forced'] == False, missing_source_cols],
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
                self.config.MONITOR_ALLOW_NAN,
                self.add_mode,
                done_images_df,
                done_source_ids
            )

        del missing_sources_df

        # STEP #6: finalise the df getting unique sources, calculating
        # metrics and upload data to database
        nr_sources = final_operations(
            sources_df,
            p_run,
            new_sources_df,
            self.config.SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS,
            self.add_mode,
            done_source_ids,
            self.previous_parquets
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
        """
        Check if the current pipeline runs/jobs are higher than maximum

        Raises
        ------
        MaxPipelineRunsError
            Error: maximum limit of simultaneous pipeline runs/jobs reached
        """
        if Run.objects.check_max_runs(settings.MAX_PIPELINE_RUNS):
            raise MaxPipelineRunsError

    @staticmethod
    def set_status(pipe_run: Run, status: str = None):
        """
        Set the status of a pipeline instance (a "run" or "job") in the
        database.

        Parameters
        ----------
        pipe_run : Run
            The Django model of a pipeline instance
        status : str, optional
            A string with the pipeline status to set
        """
        choices = [x[0] for x in Run._meta.get_field('status').choices]
        if status and status in choices and pipe_run.status != status:
            with transaction.atomic():
                pipe_run.status = status
                pipe_run.save()
