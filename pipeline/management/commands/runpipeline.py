import os
import logging
import traceback

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from pipeline.pipeline.main import Pipeline
from pipeline.pipeline.utils import get_create_p_run
from pipeline.utils.utils import StopWatch
from pipeline.pipeline.errors import PipelineError, PipelineConfigError


logger = logging.getLogger(__name__)


def run_pipe(name, path_name=None, run_dj_obj=None, cmd=True, debug=False):
    # intitialise the pipeline with the configuration
    path = run_dj_obj.path if run_dj_obj else path_name
    pipeline = Pipeline(
        name=run_dj_obj.name if run_dj_obj else name,
        config_path=os.path.join(path, 'config.py')
    )

    # set up logging for running pipeline from UI
    if not cmd:
        # set up the logger for the UI job
        root_logger = logging.getLogger('')
        if debug:
            root_logger.setLevel(logging.DEBUG)
        f_handler = logging.FileHandler(
            os.path.join(path, 'log.txt'),
            mode='w'
        )
        f_handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.addHandler(f_handler)

    # load and validate run configs
    try:
        pipeline.validate_cfg()
    except Exception as e:
        if debug:
            traceback.print_exc()
        logger.exception('Config error:\n%s', e)
        msg = f'Config error:\n{e}'
        raise CommandError(msg) if cmd else PipelineConfigError(msg)

    # Create the pipeline run in DB
    p_run = get_create_p_run(
        pipeline.name,
        pipeline.config.PIPE_RUN_PATH
    ) if not run_dj_obj else run_dj_obj

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

        if debug:
            traceback.print_exc()
        logger.exception('Processing error:\n%s', e)
        msg = f'Processing error:\n{e}'
        raise CommandError(msg) if cmd else PipelineError(msg)

    # set the pipeline status as comple
    pipeline.set_status(p_run, 'END')

    logger.info(
        'total pipeline processing time %.2f sec',
        stopwatch.reset()
    )

    return True


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

        debug_flag = True if options['verbosity'] > 1 else False

        done = run_pipe(p_run_name, path_name=run_folder, debug=debug_flag)

        self.stdout.write(self.style.SUCCESS('Finished'))
