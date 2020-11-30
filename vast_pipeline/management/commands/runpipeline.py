import os
import glob
import logging
import traceback
import warnings

from django.db import transaction
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from vast_pipeline.pipeline.forced_extraction import remove_forced_meas
from vast_pipeline.pipeline.main import Pipeline
from vast_pipeline.pipeline.utils import (
    get_create_p_run, create_measurements_arrow_file,
    create_measurement_pairs_arrow_file
)
from vast_pipeline.utils.utils import StopWatch
from ..helpers import get_p_run_name
from astropy.utils.exceptions import AstropyWarning
from vast_pipeline.pipeline.errors import PipelineError, PipelineConfigError


logger = logging.getLogger(__name__)


def run_pipe(
    name, path_name=None, run_dj_obj=None, cmd=True, debug=False, user=None
):
    '''
    Main function to run the pipeline.

    Parameters
    ----------
    name : str
        The name of the pipeline run (p_run.name).
    path_name : str, optional
        The path of the directory of the pipeline run (p_run.path), defaults to
        None.
    run_dj_obj : Run, optional
        The Run object of the pipeline run, defaults to None.
    cmd : bool, optional
        Flag to signify whether the pipeline run has been run via the UI
        (False), or the command line (True). Defaults to True.
    debug : bool, optional
        Flag to signify whether to enable debug verbosity to the logging
        output. Defaults to False.
    user : User, optional
        The User of the request if made through the UI. Defaults to None.

    Returns
    -------
    bool : bool OR CommandError : CommandError
        Boolean equal to `True` on a successful completion, or in cases of
        failures a CommandError is returned.
    '''
    path = run_dj_obj.path if run_dj_obj else path_name
    pipeline = Pipeline(
        name=run_dj_obj.name if run_dj_obj else name,
        config_path=os.path.join(path, 'config.py')
    )
    # set up logging for running pipeline from UI
    if not cmd:
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

    # Create the pipeline run in DB
    p_run, flag_exist = get_create_p_run(
        pipeline.name,
        pipeline.config.PIPE_RUN_PATH
    )

    # load and validate run configs
    try:
        pipeline.validate_cfg(user=user)
    except Exception as e:
        if debug:
            traceback.print_exc()
        logger.exception('Config error:\n%s', e)
        msg = f'Config error:\n{e}'
        # If the run is already created (e.g. through UI) then set status to
        # error
        pipeline.set_status(p_run, 'ERR')
        raise CommandError(msg) if cmd else PipelineConfigError(msg)

    if pipeline.config.CREATE_MEASUREMENTS_ARROW_FILES and cmd is False:
        logger.warning(
            'The creation of arrow files is currently unavailable when running'
            ' through the UI. Please ask an admin to complete this step for'
            ' you upon a successful completion.'
        )
        logger.warning("Setting 'CREATE_MEASUREMENTS_ARROW_FILES' to 'False'.")
        pipeline.config.CREATE_MEASUREMENTS_ARROW_FILES = False

    if pipeline.config.SUPPRESS_ASTROPY_WARNINGS:
        warnings.simplefilter("ignore", category=AstropyWarning)

    # clean up pipeline images and forced measurements for re-runs
    if flag_exist:
        logger.info('Cleaning up pipeline run before re-process data')
        p_run.image_set.clear()

        logger.info(
            'Cleaning up forced measurements before re-process data'
        )
        remove_forced_meas(p_run.path)

        parquets = (
            glob.glob(os.path.join(p_run.path, "*.parquet"))
            + glob.glob(os.path.join(p_run.path, "*.arrow"))
            # TODO Remove arrow when vaex support is dropped.
        )
        for parquet in parquets:
            os.remove(parquet)

    logger.info("Source finder: %s", pipeline.config.SOURCE_FINDER)
    logger.info("Using pipeline run '%s'", pipeline.name)
    logger.info("Source monitoring: %s", pipeline.config.MONITOR)

    stopwatch = StopWatch()

    # run the pipeline operations
    try:
        # check if max runs number is reached
        pipeline.check_current_runs()
        # run the pipeline
        pipeline.set_status(p_run, 'RUN')
        pipeline.process_pipeline(p_run)
        # Create arrow file after success if selected.
        if pipeline.config.CREATE_MEASUREMENTS_ARROW_FILES:
            create_measurements_arrow_file(p_run)
            create_measurement_pairs_arrow_file(p_run)
    except Exception as e:
        # set the pipeline status as error
        pipeline.set_status(p_run, 'ERR')
        logger.exception('Processing error:\n%s', e)
        raise CommandError(f'Processing error:\n{e}')

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

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument(
            'piperun',
            type=str,
            help='Path or name of the pipeline run.'
        )

    def handle(self, *args, **options):
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

        done = run_pipe(p_run_name, path_name=run_folder, debug=debug_flag)

        self.stdout.write(self.style.SUCCESS('Finished'))
