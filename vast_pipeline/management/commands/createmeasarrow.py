"""
This module defines the command for creating an arrow output file for a
previously completed pipeline run.
"""

import os
import logging
import traceback
import warnings

from argparse import ArgumentParser
from django.core.management.base import BaseCommand, CommandError
from vast_pipeline.pipeline.utils import (
    create_measurements_arrow_file,
    create_measurement_pairs_arrow_file
)
from vast_pipeline.models import Run
from ..helpers import get_p_run_name


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This command creates measurements and measurement_pairs arrow files for a
    completed pipeline run.
    """
    help = (
        'Create `measurements.arrow` and `measurement_pairs.arrow` files for a'
        ' completed pipeline run.'
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
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

    def handle(self, *args, **options) -> None:
        """
        Handle function of the command.

        Args:
            *args: Variable length argument list.
            **options: Variable length options.

        Returns:
            None
        """
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
        measurement_pairs_arrow = os.path.join(
            run_folder, 'measurement_pairs.arrow'
        )

        if os.path.isfile(measurements_arrow):
            if options['overwrite']:
                logger.info("Removing previous 'measurements.arrow' file.")
                os.remove(measurements_arrow)
            else:
                raise CommandError(
                    f'Measurements arrow file already exists for {p_run_name}'
                    ' and `--overwrite` has not been selected.'
                )

        if os.path.isfile(measurement_pairs_arrow):
            if options['overwrite']:
                logger.info(
                    "Removing previous 'measurement_pairs.arrow' file."
                )
                os.remove(measurement_pairs_arrow)
            else:
                raise CommandError(
                    'Measurement pairs arrow file already exists for'
                    f' {p_run_name} and `--overwrite` has not been selected.'
                )

        logger.info("Creating measurements arrow file for '%s'.", p_run_name)

        create_measurements_arrow_file(p_run)

        logger.info(
            "Creating measurement pairs arrow file for '%s'.", p_run_name
        )

        create_measurement_pairs_arrow_file(p_run)
