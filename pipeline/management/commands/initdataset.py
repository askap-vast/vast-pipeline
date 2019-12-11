import os
import logging
from shutil import copyfile

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as cfg
from pipeline.models import Dataset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script initialise the Dataset folder and related config for the pipeline.
    """
    help = 'Create the dataset folder structure to run a pipeline instance'

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument(
            'dataset folder name',
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

        name = options['dataset folder name'][0]
        # check for duplicated dataset name
        ds = Dataset.objects.filter(name__exact=name)
        if ds:
            raise CommandError('Dataset name already used. Change name')

        # create the dataset folder
        ds_path = os.path.join(cfg.PROJECT_WORKING_DIR, name)

        if os.path.exists(ds_path):
            raise CommandError('Dataset path already present!')
        else:
            logger.info('creating dataset folder')
            os.mkdir(ds_path)

        # copy default config into the Dataset folder
        logger.info('copying default config in dataset folder')
        copyfile(
            os.path.join(cfg.BASE_DIR, 'pipeline', 'config.py'),
            os.path.join(ds_path, 'config.py')
        )

        logger.info(
            'Dataset initialisation successful! Please modify the "config.py"'
        )
