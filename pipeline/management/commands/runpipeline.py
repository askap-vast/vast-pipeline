import os
import logging
import traceback

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from pipeline.pipeline.main import Pipeline
from pipeline.pipeline.utils import get_create_p_run
from pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script is used to process images with the ASKAP transient pipeline.
    Use --help for usage, and refer README.
    """
    help = 'Process the pipeline for a list of images or a Selavy catalog'

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument(
            'run_folder_path',
            nargs=1,
            type=str,
            help='path to the pipeline run folder'
        )

    def handle(self, *args, **options):
        p_run_path = options['run_folder_path'][0]
        run_folder = os.path.realpath(p_run_path)
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

        p_run_name = p_run_path
        # remove ending / if present
        if p_run_name[-1] == '/':
            p_run_name = p_run_name[:-1]
        # grab only the name from the path
        p_run_name = p_run_name.split(os.path.sep)[-1]

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

        # Create the pipeline run in DB
        p_run = get_create_p_run(
            pipeline.name,
            pipeline.config.PIPE_RUN_PATH
        )

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
        except Exception as e:
            # set the pipeline status as error
            pipeline.set_status(p_run, 'ERR')

            if options['verbosity'] > 1:
                traceback.print_exc()
            logger.exception('Processing error:\n%s', e)
            raise CommandError(f'Processing error:\n{e}')

        # set the pipeline status as completed
        pipeline.set_status(p_run, 'END')

        logger.info(
            'total pipeline processing time %.2f sec',
            stopwatch.reset()
        )
