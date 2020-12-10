import os
import glob
import shutil
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
    create_measurement_pairs_arrow_file, backup_parquets
)
from vast_pipeline.utils.utils import StopWatch
from ..helpers import get_p_run_name
from astropy.utils.exceptions import AstropyWarning
from vast_pipeline.pipeline.errors import PipelineError, PipelineConfigError


logger = logging.getLogger(__name__)


def run_pipe(
    name, path_name=None, run_dj_obj=None, cmd=True, debug=False, user=None,
    complete_rerun=False
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
    complete_rerun : bool, optional
        If the run already exists, a complete rerun will be performed which
        will remove and replace all the previous results.

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

    # copy across config file now that it is successful
    logger.debug("Copying temp config file.")
    shutil.copyfile(
        os.path.join(p_run.path, 'config.py'),
        os.path.join(p_run.path, 'config_temp.py'))

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

    # clean up pipeline images and forced measurements for re-runs
    # Scenarios:
    # A. Complete Re-run: If the job is marked as successful then backup
    # old parquets and proceed to remove parquets along with forced
    # extractions from the database.
    # B. Additional Run on successful run: Backup parquets, remove current
    # parquets and proceed.
    # C. Additional Run on errored run: Do not backup parquets, just delete
    # current.

    # Flag on the pipeline object on whether the addition mode is on or off.
    pipeline.add_mode = False
    pipeline.previous_parquets = {}

    if flag_exist:
        p_run_status = p_run.status
        parquets = (
            glob.glob(os.path.join(p_run.path, "*.parquet"))
            # TODO Remove arrow when vaex support is dropped.
            + glob.glob(os.path.join(p_run.path, "*.arrow"))
        )

        if complete_rerun:
            if p_run_status == 'END':
                backup_parquets(p_run.path)
            logger.info('Cleaning up pipeline run before re-process data')
            p_run.image_set.clear()

            logger.info(
                'Cleaning up forced measurements before re-process data'
            )
            remove_forced_meas(p_run.path)

            for parquet in parquets:
                os.remove(parquet)
        else:
            # Before parquets are started to be copied and backed up, a check
            # is run to see if anything has actually changed in the config
            config_diff = pipeline.check_prev_config_diff(p_run.path)
            if config_diff:
                logger.info(
                    "The config file has either not changed since the"
                    " previous run or other settings have changed such that a"
                    " new or complete re-run should be performed instead. "
                    "Performing no actions. Exiting.")
                os.remove(os.path.join(p_run.path, 'config_temp.py'))
                return True

            if pipeline.epoch_based != p_run.epoch_based:
                logger.info(
                    "The 'epoch based' setting has changed since the previous"
                    " run. A complete re-run is required if changing to"
                    " epoch based mode or vice versa.")
                os.remove(os.path.join(p_run.path, 'config_temp.py'))
                return True

            if p_run_status == 'END':
                backup_parquets(p_run.path)

            pipeline.add_mode = True
            pipeline.previous_parquets['images'] = os.path.join(
                p_run.path, 'images.parquet.backup')
            pipeline.previous_parquets['associations'] = os.path.join(
                p_run.path, 'associations.parquet.backup')
            pipeline.previous_parquets['sources'] = os.path.join(
                p_run.path, 'sources.parquet.backup')
            pipeline.previous_parquets['relations'] = os.path.join(
                p_run.path, 'relations.parquet.backup')
            pipeline.previous_parquets['measurement_pairs'] = os.path.join(
                p_run.path, 'measurement_pairs.parquet.backup')

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

    # copy across config file now that it is successful
    logger.debug("Copying and cleaning temp config file.")
    shutil.copyfile(
        os.path.join(p_run.path, 'config_temp.py'),
        os.path.join(p_run.path, 'config_prev.py'))
    os.remove(os.path.join(p_run.path, 'config_temp.py'))

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

        parser.add_argument(
            '--complete-rerun',
            required=False,
            default=False,
            action='store_true',
            help=(
                'Flag to signify that a full re-run is requested.'
                ' Old data is completely removed and replaced.')
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

        done = run_pipe(p_run_name, path_name=run_folder,
            debug=debug_flag, complete_rerun=options['complete_rerun'])

        self.stdout.write(self.style.SUCCESS('Finished'))
