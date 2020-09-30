import os
import logging
import traceback
import warnings

from django.core.management.base import BaseCommand, CommandError
from vast_pipeline.pipeline.utils import create_measurements_arrow_file
from vast_pipeline.models import Run
from ..helpers import get_p_run_name


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This command creates a measurements arrow file for a completed pipeline
    run.
    """
    help = (
        'Create a `measurements.arrow` file for a completed pipeline run.'
    )

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument(
            'piperun',
            type=str,
            help='Path or name of the pipeline run.'
        )

        parser.add_argument(
            '--overwrite',
            action='store_true',
            required=False,
            default=False,
            help="Overwrite previous 'measurements.arrow' file.",
        )

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

        measurements_arrow = os.path.join(run_folder, 'measurements.arrow')

        if os.path.isfile(measurements_arrow):
            if options['overwrite']:
                logger.info("Removing previous 'measurements.arrow' file.")
                os.remove(measurements_arrow)
            else:
                raise CommandError(
                    f'Measurements arrow file already exists for {p_run_name}'
                    ' and `--overwrite` has not been selected.'
                )

        logger.info("Creating measurements arrow file for '%s'.", p_run_name)

        create_measurements_arrow_file(p_run)
