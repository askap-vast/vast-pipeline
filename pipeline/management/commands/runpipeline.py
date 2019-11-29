import os
import logging

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from pipeline.pipeline.main import Pipeline
from pipeline.utils.utils import load_validate_cfg, RunStats, StopWatch
from pipeline.models import Dataset


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
            'dataset_folder_path',
            nargs=1,
            type=str,
            help='path to the dataset folder'
        )

    def handle(self, *args, **options):
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        dataset_path = options['dataset_folder_path'][0]

        dataset_name = dataset_path
        # remove ending / if present
        if dataset_name[-1] == '/':
            dataset_name = dataset_name[:-1]
        # grab only the dataset name from the path
        dataset_name = dataset_name.split(os.path.sep)[-1]

        # Create the dataset in DB
        dataset = Dataset(name=dataset_name)
        dataset.save()
        import ipdb; ipdb.set_trace()  # breakpoint d1cb4a04 //

        cfg_path = os.path.join(os.path.realpath(dataset_path), 'config.py')

        # load and validate dataset configs
        try:
            cfg = load_validate_cfg(cfg_path)
        except Exception as e:
            raise CommandError(f'Config error:\n{e}')

        logger.info(f"Database: {settings.DATABASES['default']['NAME']}")
        logger.info(f"Source finder: {cfg.SOURCE_FINDER}")
        logger.info(f"Using dataset '{dataset_name}'")
        logger.info(f"Source monitoring: {cfg.MONITOR}")
        logger.info(f"Constant background RMS: {cfg.CONSTANT_RMS}")

        stats = RunStats()
        stopwatch = StopWatch()

        # intitialise the pipeline with the configuration
        pipeline = Pipeline(config=cfg)

        # run the pipeline operations
        pipeline.process_pipeline(dataset.id)
