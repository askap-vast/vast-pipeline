import os
import logging
import traceback
import warnings

from django.core.management.base import BaseCommand, CommandError

from pipeline.pipeline.forced_extraction import remove_forced_meas
from pipeline.pipeline.main import Pipeline
from pipeline.pipeline.utils import (
    get_create_p_run, create_measurements_arrow_file
)
from pipeline.utils.utils import StopWatch
from ..helpers import get_p_run_name
from astropy.utils.exceptions import AstropyWarning


logger = logging.getLogger(__name__)


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

        # intitialise the pipeline with the configuration
        pipeline = Pipeline(
            name=p_run_name,
            config_path=os.path.join(run_folder, 'config.py')
        )

        # load and validate run configs
        try:
            pipeline.validate_cfg()
        except Exception as e:
            if options['verbosity'] > 1:
                traceback.print_exc()
            logger.exception('Config error:\n%s', e)
            raise CommandError(f'Config error:\n{e}')

        if pipeline.config.SUPPRESS_ASTROPY_WARNINGS:
            warnings.simplefilter("ignore", category=AstropyWarning)

        # Create the pipeline run in DB
        p_run, flag_exist = get_create_p_run(
            pipeline.name,
            pipeline.config.PIPE_RUN_PATH
        )
        # clean up pipeline images and forced measurements for re-runs
        if flag_exist:
            logger.info('Cleaning up pipeline run before re-process data')
            p_run.image_set.clear()

            if not pipeline.config.MONITOR:
                logger.info(
                    'Cleaning up forced measurements before re-process data'
                )
                forced_parquets = remove_forced_meas(p_run.path)
                for parquet in forced_parquets:
                    os.remove(parquet)

        logger.info('Source finder: %s', pipeline.config.SOURCE_FINDER)
        logger.info('Using pipeline run "%s"', pipeline.name)
        logger.info('Source monitoring: %s', pipeline.config.MONITOR)

        stopwatch = StopWatch()

        # run the pipeline operations
        try:
            # check if max runs number is reached
            pipeline.check_current_runs()
            # run the pipeline
            pipeline.set_status(p_run, 'RUN')
            pipeline.process_pipeline(p_run)
        except Exception as e:
            # set the pipeline status as error
            pipeline.set_status(p_run, 'ERR')

            if options['verbosity'] > 1:
                traceback.print_exc()
            logger.exception('Processing error:\n%s', e)
            raise CommandError(f'Processing error:\n{e}')

        # Create arrow file after success if selected.
        if pipeline.config.CREATE_MEASUREMENTS_ARROW_FILE:
            create_measurements_arrow_file(p_run)

        # set the pipeline status as completed
        pipeline.set_status(p_run, 'END')

        logger.info(
            'Total pipeline processing time %.2f sec',
            stopwatch.reset()
        )
