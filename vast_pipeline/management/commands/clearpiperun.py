"""
This module defines the command for clearing a run from the database.
"""

import os
import logging
import shutil

from argparse import ArgumentParser
from glob import glob
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from vast_pipeline.models import Run
from vast_pipeline.pipeline.forced_extraction import remove_forced_meas
from ..helpers import get_p_run_name
from vast_pipeline.pipeline.utils import delete_file_or_dir


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script is used to clean the data for pipeline run(s).
    Use --help for usage.
    """

    help = (
        'Delete a pipeline run and all related images, sources, etc.'
        ' Will not delete objects if they are also related to another '
        'pipeline run.'
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
        # positional arguments (required)
        parser.add_argument(
            'piperuns',
            nargs='+',
            type=str,
            default=None,
            help=(
                'Name or path of pipeline run(s) to delete. Pass "clearall" to'
                ' delete all the runs.'
            )
        )
        # keyword arguments (optional)
        parser.add_argument(
            '--keep-parquet',
            required=False,
            default=False,
            action='store_true',
            help=(
                'Flag to keep the pipeline run(s) parquet files. '
                'Will also apply to arrow files if present.'
            )
        )
        parser.add_argument(
            '--remove-all',
            required=False,
            default=False,
            action='store_true',
            help='Flag to remove all the content of the pipeline run(s) folder.'
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

        if options['keep_parquet'] and options['remove_all']:
            raise CommandError(
                '"--keep-parquets" flag is incompatible with "--remove-all" flag'
            )

        piperuns = options['piperuns']
        flag_all_runs = True if 'clearall' in piperuns else False
        if flag_all_runs:
            logger.info('clearing all pipeline run in the database')
            piperuns = list(Run.objects.values_list('name', flat=True))

        for piperun in piperuns:
            p_run_name = get_p_run_name(piperun)
            try:
                p_run = Run.objects.get(name=p_run_name)
            except Run.DoesNotExist:
                raise CommandError(f'Pipeline run {p_run_name} does not exist')

            logger.info("Deleting pipeline '%s' from database", p_run_name)
            with transaction.atomic():
                p_run.status = 'DEL'
                p_run.save()
            p_run.delete()

            # remove forced measurements in db if presents
            forced_parquets = remove_forced_meas(p_run.path)

            # Delete parquet or folder eventually
            if not options['keep_parquet'] and not options['remove_all']:
                logger.info('Deleting pipeline "%s" parquets', p_run_name)
                parquets = (
                    glob(os.path.join(p_run.path, '*.parquet'))
                    + glob(os.path.join(p_run.path, '*.arrow'))
                )
                for parquet in parquets:
                    try:
                        delete_file_or_dir(parquet)
                    except OSError as e:
                        self.stdout.write(self.style.WARNING(
                            f'Parquet file "{os.path.basename(parquet)}" not existent'
                        ))
                        pass

            if options['remove_all']:
                logger.info('Deleting pipeline folder')
                try:
                    shutil.rmtree(p_run.path)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'Issues in removing run folder: {e}'
                    ))
                    pass
