import os
import logging
from shutil import copyfile

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as cfg

from pipeline.models import Run

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script initialise the Pipeline Run folder and related config
    for the pipeline.
    """
    help = (
        'Create the pipeline run folder structure to run a pipeline '
        'instance'
    )

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument(
            'run_folder_path',
            nargs=1,
            type=str,
            help='path to the pipeline run folder'
        )

    def handle(self, *args, **options):
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        name = options['run_folder_path'][0]
        # check for duplicated run name
        p_run = Run.objects.filter(name__exact=name)
        if p_run:
            raise CommandError('Pipeline run name already used. Change name')

        # create the pipeline run folder
        ds_path = os.path.join(cfg.PROJECT_WORKING_DIR, name)

        if os.path.exists(ds_path):
            raise CommandError('pipeline run path already present!')
        else:
            logger.info('creating pipeline run folder')
            os.mkdir(ds_path)

        # copy default config into the pipeline run folder
        logger.info('copying default config in pipeline run folder')
        copyfile(
            os.path.join(cfg.BASE_DIR, 'pipeline', 'config.template.py'),
            os.path.join(ds_path, 'config.py')
        )

        logger.info((
            'pipeline run initialisation successful! Please modify the '
            '"config.py"'
        ))
