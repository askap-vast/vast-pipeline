import os
import logging
import shutil
import time
import psutil  # Import the psutil module

from argparse import ArgumentParser
from glob import glob
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from vast_pipeline.models import Run
from vast_pipeline.pipeline.forced_extraction import remove_forced_meas
from ..helpers import get_p_run_name

from ...utils.delete_run import delete_pipeline_run_raw_sql
#from memory_profiler import profile

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

    #@profile
    def handle(self, *args, **options) -> None:
        """
        Handle function of the command.

        Args:
            *args: Variable length argument list.
            **options: Variable length options.

        Returns:
            None
        """
        process = psutil.Process(os.getpid())  # Get the current process
        start_time = time.time()  # Record the start time
        start_memory = process.memory_info().rss  # Record the start memory usage

        segment_times = {}  # Dictionary to store segment times
        segment_memory = {}  # Dictionary to store segment memory usage

        #def record_segment(name):
        #    """ Helper function to record time and memory usage for segments. """
        #    current_time = time.time()
        #    current_memory = process.memory_info().rss
        #    segment_times[name] = current_time - segment_start
        #    segment_memory[name] = current_memory - segment_memory_start
        #    return current_time, current_memory

        # configure logging
        segment_start = time.time()
        segment_memory_start = process.memory_info().rss
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True
        #record_segment('configure_logging')

        segment_start = time.time()
        segment_memory_start = process.memory_info().rss
        if options['keep_parquet'] and options['remove_all']:
            raise CommandError(
                '"--keep-parquets" flag is incompatible with "--remove-all" flag'
            )
        #record_segment('flag_check')

        piperuns = options['piperuns']
        flag_all_runs = True if 'clearall' in piperuns else False

        segment_start = time.time()
        segment_memory_start = process.memory_info().rss
        if flag_all_runs:
            logger.info('clearing all pipeline run in the database')
            piperuns = list(Run.objects.values_list('name', flat=True))
        #record_segment('run_list')

        for piperun in piperuns:
            segment_start = time.time()
            segment_memory_start = process.memory_info().rss
            p_run_name = get_p_run_name(piperun)
            try:
                p_run = Run.objects.get(name=p_run_name)
            except Run.DoesNotExist:
                raise CommandError(f'Pipeline run {p_run_name} does not exist')
            #record_segment('get_run')

            segment_start = time.time()
            segment_memory_start = process.memory_info().rss
            logger.info("Deleting pipeline '%s' from database", p_run_name)
            with transaction.atomic():
                p_run.status = 'DEL'
                p_run.save()
            delete_pipeline_run_raw_sql(p_run)
            #record_segment('delete_db')

            segment_start = time.time()
            segment_memory_start = process.memory_info().rss
            # remove forced measurements in db if presents
            forced_parquets = remove_forced_meas(p_run.path)
            #record_segment('remove_forced')

            segment_start = time.time()
            segment_memory_start = process.memory_info().rss
            # Delete parquet or folder eventually
            if not options['keep_parquet'] and not options['remove_all']:
                logger.info('Deleting pipeline "%s" parquets', p_run_name)
                parquets = (
                    glob(os.path.join(p_run.path, '*.parquet'))
                    + glob(os.path.join(p_run.path, '*.arrow'))
                )
                for parquet in parquets:
                    try:
                        os.remove(parquet)
                    except OSError as e:
                        self.stdout.write(self.style.WARNING(
                            f'Parquet file "{os.path.basename(parquet)}" not existent'
                        ))
                        pass
            #record_segment('delete_files')

            segment_start = time.time()
            segment_memory_start = process.memory_info().rss
            if options['remove_all']:
                logger.info('Deleting pipeline folder')
                try:
                    shutil.rmtree(p_run.path)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'Issues in removing run folder: {e}'
                    ))
                    pass
            #record_segment('remove_folder')

        end_time = time.time()  # Record the end time
        end_memory = process.memory_info().rss  # Record the end memory usage
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        memory_used = end_memory - start_memory  # Calculate the memory used
        logger.info(f"Time taken to execute the command: {elapsed_time:.2f} seconds")
        logger.info(f"Memory used to execute the command: {memory_used / (1024 * 1024):.2f} MB")

        # Log the time taken for each segment
        for segment, duration in segment_times.items():
            logger.info(f"Time taken for {segment}: {duration:.2f} seconds")
            print(f"Time taken for {segment}: {duration:.2f} seconds")

        # Log the memory used for each segment
        for segment, memory in segment_memory.items():
            logger.info(f"Memory used for {segment}: {memory / (1024 * 1024):.2f} MB")
            print(f"Memory used for {segment}: {memory / (1024 * 1024):.2f} MB")
