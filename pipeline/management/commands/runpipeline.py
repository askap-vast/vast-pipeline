import os
import logging
import traceback

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from pipeline.pipeline.main import Pipeline
from pipeline.pipeline.utils import get_create_p_run
from pipeline.utils.utils import load_validate_cfg, StopWatch


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

        cfg_path = os.path.join(run_folder, 'config.py')

        # load and validate run configs
        try:
            cfg = load_validate_cfg(cfg_path)
        except Exception as e:
            if options['verbosity'] > 1:
                traceback.print_exc()
            raise CommandError(f'Config error:\n{e}')

        # Create the pipeline run in DB
        p_run = get_create_p_run(p_run_name, cfg.PIPE_RUN_PATH)

        logger.info("Source finder: %s", cfg.SOURCE_FINDER)
        logger.info("Using pipeline run '%s'", p_run_name)
        logger.info("Source monitoring: %s", cfg.MONITOR)

        stopwatch = StopWatch()

        # intitialise the pipeline with the configuration
        pipeline = Pipeline(config=cfg)

        # run the pipeline operations
        try:
            pipeline.process_pipeline(p_run)
        except Exception as e:
            if options['verbosity'] > 1:
                traceback.print_exc()
            raise CommandError(f'Processing error:\n{e}')
        logger.info(
            'total pipeline processing time %.2f sec',
            stopwatch.reset()
        )
