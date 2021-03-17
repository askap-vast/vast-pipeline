import os
import logging

from django.core.management.base import BaseCommand, CommandError
from vast_pipeline.pipeline.loading import make_upload_images

from vast_pipeline.models import Run
from vast_pipeline.pipeline.main import Pipeline
from ..helpers import get_p_run_name

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script injects an image into the database along with extracting,
    correcting and saving the measurements and obtaining estimates of the rms.
    """
    help = (
        'Injects an image into the database'
    )

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument(
            'piperun',
            type=str,
            help='Path or name of the pipeline run.'
        )

        # parser.add_argument(
        #     'imgpath',
        #     type=str,
        #     help='Path of the image.'
        # )

    def handle(self, *args, **options):
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        piperun = options['piperun']

        p_run_name, run_folder = get_p_run_name(
            piperun,
            return_folder=True
        )
        try:
            p_run = Run.objects.get(name=p_run_name)
        except Run.DoesNotExist:
            raise CommandError(f'Pipeline run {p_run_name} does not exist')

        if p_run.status != 'END':
            raise CommandError(f'Pipeline run {p_run_name} has not completed.')

        path = p_run.path
        pipeline = Pipeline(
            name=p_run.name,
            config_path=os.path.join(path, 'config.py')
        )

        pipeline.validate_cfg()

        pipeline.match_images_to_data()

        images, skyregs_df = make_upload_images(
            pipeline.img_paths,
            pipeline.config,
            p_run
        )
