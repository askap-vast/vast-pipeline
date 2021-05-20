"""
This module contains the main pipeline class used for processing a pipeline
run.
"""

import os
import operator
import logging
from typing import Dict

from astropy import units as u
from astropy.coordinates import Angle

import pandas as pd

from django.conf import settings
from django.db import transaction

from vast_pipeline.models import Run, SurveySource
from .association import association, parallel_association
from .config import PipelineConfig
from .new_sources import new_sources
from .forced_extraction import forced_extraction
from .finalise import final_operations
from .loading import make_upload_images
from .utils import (
    get_src_skyregion_merged_df,
    group_skyregions,
    get_parallel_assoc_image_df,
    write_parquets
)

from .errors import MaxPipelineRunsError


logger = logging.getLogger(__name__)


class Pipeline():
    """Instance of a pipeline. All the methods runs the pipeline opearations, such as
    association.

    Attributes:
        name (str): The name of the pipeline run.
        config (PipelineConfig): The pipeline run configuration.
        img_paths: A dict mapping input image paths to their selavy/noise/background
            counterpart path. e.g. `img_paths["selavy"][<image_path>]` contains the
            selavy catalogue file path for `<image_path>`.
        img_epochs: A dict mapping input image names to their provided epoch.
        add_mode: A boolean indicating if this run is adding new images to a previously
            executed pipeline run.
        previous_parquets: A dict mapping that provides the paths to parquet files for
            previous executions of this pipeline run.
    """
    def __init__(self, name: str, config_path: str, validate_config: bool = True):
        """Initialise an instance of Pipeline with a name and configuration file path.

        Args:
            name (str): The name of the pipeline run.
            config_path (str): The path to a YAML run configuration file.
            validate_config (bool, optional): Validate the run configuration immediately.
                Defaults to True.
        """
        self.name: str = name
        self.config: PipelineConfig = PipelineConfig.from_file(
            config_path, validate=validate_config
        )
        self.img_paths: Dict[str, Dict[str, str]] = {
            'selavy': {},
            'noise': {},
            'background': {},
        }  # maps input image paths to their selavy/noise/background counterpart path
        self.img_epochs: Dict[str, str] = {}  # maps image names to their provided epoch
        self.add_mode: bool = False
        self.previous_parquets: Dict[str, str]

    def match_images_to_data(self) -> None:
        """
        Loops through images and matches the selavy, noise and bkg images.
        Assumes that user has enteted images and other data in the same order.

        Returns:
            None
        """
        for key in sorted(self.config["inputs"]["image"].keys()):
            for x, y in zip(
                self.config["inputs"]["image"][key],
                self.config["inputs"]["selavy"][key],
            ):
                self.img_paths["selavy"][x] = y
                self.img_epochs[os.path.basename(x)] = key
            for x, y in zip(
                self.config["inputs"]["image"][key], self.config["inputs"]["noise"][key]
            ):
                self.img_paths["noise"][x] = y
            if "background" in self.config["inputs"]:
                for x, y in zip(
                    self.config["inputs"]["image"][key],
                    self.config["inputs"]["background"][key],
                ):
                    self.img_paths["background"][x] = y

    def process_pipeline(self, p_run: Run) -> None:
        """
        The function that performs the processing operations of the pipeline
        run.

        Args:
            p_run: The pipeline run model object.

        Returns:
            None
        """
        logger.info(f'Epoch based association: {self.config.epoch_based}')
        if self.add_mode:
            logger.info('Running in image add mode.')

        # Update epoch based flag to not cause user confusion when running
        # the pipeline (i.e. if it was only updated at the end). It is not
        # updated if the pipeline is being run in add mode.
        if self.config.epoch_based and not self.add_mode:
            with transaction.atomic():
                p_run.epoch_based = self.config.epoch_based
                p_run.save()

        # Match the image files to the respective selavy, noise and bkg files.
        # Do this after validation is successful.
        self.match_images_to_data()

        # upload/retrieve image data
        images, skyregions, bands = make_upload_images(
            self.img_paths,
            self.config.image_config(),
            p_run
        )

        # write parquet files and retrieve skyregions as a dataframe
        skyregs_df = write_parquets(images, skyregions, bands, self.config["run"]["path"])

        # STEP #2: measurements association
        # order images by time
        images.sort(key=operator.attrgetter('datetime'))

        # If the user has given lists we need to reorder the
        # image epochs such that they are in date order.
        if self.config.epoch_based is False:
            self.img_epochs = {}
            for i, img in enumerate(images):
                self.img_epochs[img.name] = i + 1

        image_epochs = [
            self.img_epochs[img.name] for img in images
        ]
        limit = Angle(self.config["source_association"]["radius"] * u.arcsec)
        dr_limit = self.config["source_association"]["deruiter_radius"]
        bw_limit = self.config["source_association"]["deruiter_beamwidth_limit"]
        duplicate_limit = Angle(
            self.config["source_association"]["epoch_duplicate_radius"] * u.arcsec
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
        if self.config["source_association"]["parallel"] and n_skyregion_groups > 1:
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
            self.config["new_sources"]["min_sigma"],
            self.config["source_monitoring"]["edge_buffer_scale"],
            p_run
        )

        # Drop column no longer required in missing_sources_df.
        missing_sources_df = (
            missing_sources_df.drop(['in_primary'], axis=1)
        )

        # STEP #5: Run forced extraction/photometry if asked
        if self.config["source_monitoring"]["monitor"]:
            (
                sources_df,
                nr_forced_measurements
            ) = forced_extraction(
                sources_df,
                self.config["measurements"]["ra_uncertainty"] / 3600.,
                self.config["measurements"]["dec_uncertainty"] / 3600.,
                p_run,
                missing_sources_df,
                self.config["source_monitoring"]["min_sigma"],
                self.config["source_monitoring"]["edge_buffer_scale"],
                self.config["source_monitoring"]["cluster_threshold"],
                self.config["source_monitoring"]["allow_nan"],
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
            self.config["variability"]["source_aggregate_pair_metrics_min_abs_vs"],
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
                nr_forced_measurements if self.config["source_monitoring"]["monitor"] else 0
            )
            p_run.save()

        pass

    @staticmethod
    def check_current_runs() -> None:
        """
        Checks the number of pipeline runs currently being processed.

        Returns:
            None

        Raises:
            MaxPipelineRunsError: Raised if the number of pipeline runs
                currently being processed is larger than the allowed
                maximum.
        """
        if Run.objects.check_max_runs(settings.MAX_PIPELINE_RUNS):
            raise MaxPipelineRunsError

    @staticmethod
    def set_status(pipe_run: Run, status: str=None) -> None:
        """
        Function to change the status of a pipeline run model object and save
        to the database.

        Args:
            pipe_run: The pipeline run model object.
            status: The status to set.

        Returns:
            None
        """
        #TODO: This function gives no feedback if the status is not accepted?
        choices = [x[0] for x in Run._meta.get_field('status').choices]
        if status and status in choices and pipe_run.status != status:
            with transaction.atomic():
                pipe_run.status = status
                pipe_run.save()
