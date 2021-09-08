"""
The main command to launch the processing of a pipeline run.

Usage: ./manage.py runpipeline pipeline_run_name
"""

import os
import glob
import shutil
import logging
import traceback
import warnings

from argparse import ArgumentParser
from typing import Optional
from django.db import transaction
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from vast_pipeline._version import __version__ as pipeline_version
from vast_pipeline.pipeline.forced_extraction import remove_forced_meas
from vast_pipeline.pipeline.main import Pipeline
from vast_pipeline.pipeline.utils import (
    get_create_p_run, create_measurements_arrow_file,
    create_measurement_pairs_arrow_file, backup_parquets
)
from vast_pipeline.utils.utils import StopWatch
from vast_pipeline.models import Run
from ..helpers import get_p_run_name
from astropy.utils.exceptions import AstropyWarning
from vast_pipeline.pipeline.errors import PipelineConfigError


logger = logging.getLogger(__name__)


def run_pipe(
    name: str, path_name: Optional[str] = None,
    run_dj_obj: Optional[Run] = None, cli: bool = True,
    debug: bool = False, user: Optional[User] = None, full_rerun: bool = False,
    prev_ui_status: str = 'END'
) -> bool:
    '''
    Main function to run the pipeline.

    Args:
        name:
            The name of the pipeline run (p_run.name).
        path_name:
            The path of the directory of the pipeline run (p_run.path),
            defaults to None.
        run_dj_obj:
            The Run object of the pipeline run, defaults to None.
        cli:
            Flag to signify whether the pipeline run has been run via the UI
            (False), or the command line (True). Defaults to True.
        debug:
            Flag to signify whether to enable debug verbosity to the logging
            output. Defaults to False.
        user:
            The User of the request if made through the UI. Defaults to None.
        full_rerun:
            If the run already exists, a complete rerun will be performed which
            will remove and replace all the previous results.
        prev_ui_status:
            The previous status through the UI. Defaults to 'END'.

    Returns:
        Boolean equal to `True` on a successful completion, or in cases of
        failures a CommandError is returned.
    '''
    path = run_dj_obj.path if run_dj_obj else path_name
    # set up logging for running pipeline from UI
    if not cli:
        # set up the logger for the UI job
        root_logger = logging.getLogger('')
        if debug:
            root_logger.setLevel(logging.DEBUG)
        f_handler = logging.FileHandler(
            os.path.join(path, 'log.txt'),
            mode='w'
        )
        f_handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.addHandler(f_handler)

    pipeline = Pipeline(
        name=run_dj_obj.name if run_dj_obj else name,
        config_path=os.path.join(path, 'config.yaml'),
        validate_config=False,  # delay validation
    )

    # Create the pipeline run in DB
    p_run, flag_exist = get_create_p_run(
        pipeline.name,
        pipeline.config["run"]["path"],
    )

    # copy across config file at the start
    logger.debug("Copying temp config file.")
    shutil.copyfile(
        os.path.join(p_run.path, 'config.yaml'),
        os.path.join(p_run.path, 'config_temp.yaml')
    )

    # backup the last successful outputs.
    # if the run is being run again and the last status is END then the
    # user is highly likely to be attempting to add images. Making the backups
    # now from a guaranteed successful run is safer in case of problems
    # with the config file below that causes an error.
    if flag_exist:
        if cli and p_run.status == 'END':
            backup_parquets(p_run.path)
        elif not cli and prev_ui_status == 'END':
            backup_parquets(p_run.path)

    # validate run configuration
    try:
        pipeline.config.validate(user=user)
    except PipelineConfigError as e:
        if debug:
            traceback.print_exc()
        logger.exception('Config error:\n%s', e)
        msg = f'Config error:\n{e}'
        # If the run is already created (e.g. through UI) then set status to
        # error
        pipeline.set_status(p_run, 'ERR')
        raise CommandError(msg) if cli else PipelineConfigError(msg)

    # clean up pipeline images and forced measurements for re-runs
    # Scenarios:
    # A. Complete Re-run: If the job is marked as successful then backup
    # old parquets and proceed to remove parquets along with forced
    # extractions from the database.
    # B. Additional Run on successful run: Backup parquets, remove current
    # parquets and proceed.
    # C. Additional Run on errored run: Do not backup parquets, just delete
    # current.
    # D. Running on initialised run that errored and is still the init run.

    # Flag on the pipeline object on whether the addition mode is on or off.
    pipeline.add_mode = False
    pipeline.previous_parquets = {}
    prev_config_exists = False

    try:
        if not flag_exist:
            # check for and remove any present .parquet (and .arrow) files
            parquets = (
                glob.glob(os.path.join(p_run.path, "*.parquet"))
                # TODO Remove arrow when arrow files are no longer needed.
                + glob.glob(os.path.join(p_run.path, "*.arrow"))
                + glob.glob(os.path.join(p_run.path, "*.bak"))
            )
            for parquet in parquets:
                os.remove(parquet)
        else:
            # Check if the status is already running or queued. Exit if this is
            # the case.
            if p_run.status in ['RUN', 'RES']:
                logger.error(
                    "The pipeline run requested to process already has a "
                    "running or restoring status! Performing no actions. "
                    "Exiting."
                )
                return True

            # Check if there is a previous run config and back up if so
            if os.path.isfile(
                os.path.join(p_run.path, 'config_prev.yaml')
            ):
                prev_config_exists = True
                shutil.copy(
                    os.path.join(p_run.path, 'config_prev.yaml'),
                    os.path.join(p_run.path, 'config.yaml.bak')
                )
            logger.debug(f'config_prev.yaml exists: {prev_config_exists}')

            # Check for an error status and whether any previous config file
            # exists - if it doesn't exist it means the run has failed during
            # the first run. In this case we want to clear anything that has
            # gone on before so to do that `complete-rerun` mode is activated.
            if not prev_config_exists:
                if cli and p_run.status == "ERR":
                    full_rerun = True
                elif not cli and prev_ui_status == "ERR":
                    full_rerun = True
            logger.debug(f'Full re-run: {full_rerun}')

            # Check if the run has only been initialised, if so we don't want
            # to do any previous run checks or cleaning.
            if p_run.status == 'INI':
                initial_run = True
            # check if coming from UI
            elif cli is False and prev_ui_status == 'INI':
                initial_run = True
            else:
                initial_run = False

            if initial_run is False:
                parquets = (
                    glob.glob(os.path.join(p_run.path, "*.parquet"))
                    # TODO Remove arrow when arrow files are no longer needed.
                    + glob.glob(os.path.join(p_run.path, "*.arrow"))
                )

                if full_rerun:
                    logger.info(
                        'Cleaning up pipeline run before re-process data'
                    )
                    p_run.image_set.clear()

                    logger.info(
                        'Cleaning up forced measurements before re-process data'
                    )
                    remove_forced_meas(p_run.path)

                    for parquet in parquets:
                        os.remove(parquet)

                    # remove bak files
                    bak_files = glob.glob(os.path.join(p_run.path, "*.bak"))
                    if bak_files:
                        for bf in bak_files:
                            os.remove(bf)

                    # remove previous config if it exists
                    if prev_config_exists:
                        os.remove(os.path.join(p_run.path, 'config_prev.yaml'))

                    # reset epoch_based flag
                    with transaction.atomic():
                        p_run.epoch_based = False
                        p_run.save()
                else:
                    # Before parquets are started to be copied and backed up, a
                    # check is run to see if anything has actually changed in
                    # the config
                    config_diff = pipeline.config.check_prev_config_diff()
                    if config_diff:
                        logger.info(
                            "The config file has either not changed since the"
                            " previous run or other settings have changed such"
                            " that a new or complete re-run should be performed"
                            " instead. Performing no actions. Exiting."
                        )
                        os.remove(os.path.join(p_run.path, 'config_temp.yaml'))
                        pipeline.set_status(p_run, 'END')

                        return True

                    if pipeline.config.epoch_based != p_run.epoch_based:
                        logger.info(
                            "The 'epoch based' setting has changed since the"
                            " previous run. A complete re-run is required if"
                            " changing to epoch based mode or vice versa."
                        )
                        os.remove(os.path.join(p_run.path, 'config_temp.yaml'))
                        pipeline.set_status(p_run, 'END')
                        return True

                    pipeline.add_mode = True

                    for i in [
                        'images', 'associations', 'sources', 'relations',
                        'measurement_pairs'
                    ]:
                        pipeline.previous_parquets[i] = os.path.join(
                            p_run.path, f'{i}.parquet.bak')
    except Exception as e:
        logger.error('Unexpected error occurred in pre-run steps!')
        pipeline.set_status(p_run, 'ERR')
        logger.exception('Processing error:\n%s', e)
        raise CommandError(f'Processing error:\n{e}')

    if pipeline.config["run"]["suppress_astropy_warnings"]:
        warnings.simplefilter("ignore", category=AstropyWarning)

    logger.info("VAST Pipeline version: %s", pipeline_version)
    logger.info(
        "Source finder: %s",
        pipeline.config["measurements"]["source_finder"]
    )
    logger.info("Using pipeline run '%s'", pipeline.name)
    logger.info(
        "Source monitoring: %s",
        pipeline.config["source_monitoring"]["monitor"]
    )

    # log the list of input data files for posterity
    input_image_list = [
        image
        for image_list in pipeline.config["inputs"]["image"].values()
        for image in image_list
    ]
    input_selavy_list = [
        selavy
        for selavy_list in pipeline.config["inputs"]["selavy"].values()
        for selavy in selavy_list
    ]
    input_noise_list = [
        noise
        for noise_list in pipeline.config["inputs"]["noise"].values()
        for noise in noise_list
    ]
    if "background" in pipeline.config["inputs"].keys():
        input_background_list = [
            background
            for background_list in pipeline.config["inputs"]["background"].values()
            for background in background_list
        ]
    else:
        input_background_list = ["N/A", ] * len(input_image_list)
    for image, selavy, noise, background in zip(
        input_image_list, input_selavy_list, input_noise_list, input_background_list
    ):
        logger.info(
            "Matched inputs - image: %s, selavy: %s, noise: %s, background: %s",
            image,
            selavy,
            noise,
            background,
        )

    stopwatch = StopWatch()

    # run the pipeline operations
    try:
        # check if max runs number is reached
        pipeline.check_current_runs()
        # run the pipeline
        pipeline.set_status(p_run, 'RUN')
        pipeline.process_pipeline(p_run)
        # Create arrow file after success if selected.
        if pipeline.config["measurements"]["write_arrow_files"]:
            create_measurements_arrow_file(p_run)
            create_measurement_pairs_arrow_file(p_run)
    except Exception as e:
        # set the pipeline status as error
        pipeline.set_status(p_run, 'ERR')
        logger.exception('Processing error:\n%s', e)
        raise CommandError(f'Processing error:\n{e}')

    # copy across config file now that it is successful
    logger.debug("Copying and cleaning temp config file.")
    shutil.copyfile(
        os.path.join(p_run.path, 'config_temp.yaml'),
        os.path.join(p_run.path, 'config_prev.yaml'))
    os.remove(os.path.join(p_run.path, 'config_temp.yaml'))

    # set the pipeline status as completed
    pipeline.set_status(p_run, 'END')

    logger.info(
        'Total pipeline processing time %.2f sec',
        stopwatch.reset()
    )

    return True


class Command(BaseCommand):
    """
    This script is used to process images with the ASKAP transient pipeline.
    Use --help for usage, and refer README.
    """
    help = 'Process the pipeline for a list of images and Selavy catalogs'

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
        # positional arguments
        parser.add_argument(
            'piperun',
            type=str,
            help='Path or name of the pipeline run.'
        )

        parser.add_argument(
            '--full-rerun',
            required=False,
            default=False,
            action='store_true',
            help=(
                'Flag to signify that a full re-run is requested.'
                ' Old data is completely removed and replaced.')
        )

    def handle(self, *args, **options) -> None:
        """
        Handle function of the command.

        Args:
            *args: Variable length argument list.
            **options: Variable length options.

        Returns:
            None
        """
        p_run_name, run_folder = get_p_run_name(
            options['piperun'],
            return_folder=True
        )
        # configure logging
        root_logger = logging.getLogger('')
        f_handler = logging.FileHandler(
            os.path.join(run_folder, 'log.txt'),
            mode='w'
        )
        f_handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.addHandler(f_handler)

        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        # p_run_name = p_run_path
        # remove ending / if present
        if p_run_name[-1] == '/':
            p_run_name = p_run_name[:-1]
        # grab only the name from the path
        p_run_name = p_run_name.split(os.path.sep)[-1]

        debug_flag = True if options['verbosity'] > 1 else False

        _ = run_pipe(
            p_run_name,
            path_name=run_folder,
            debug=debug_flag,
            full_rerun=options["full_rerun"],
        )

        self.stdout.write(self.style.SUCCESS('Finished'))
