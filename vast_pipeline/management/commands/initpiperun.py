"""
Initialises a pipeline run and creates the relevant directories.

Usage: ./manage.py initpiperun pipeline_run_name
"""

import os
import logging
from typing import Any, Dict, Optional

from argparse import ArgumentParser
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as sett
from django.contrib.auth.models import User

from vast_pipeline.models import Run
from vast_pipeline.pipeline.errors import PipelineInitError
from vast_pipeline.pipeline.config import make_config_template, PipelineConfig
from vast_pipeline.pipeline.utils import get_create_p_run


logger = logging.getLogger(__name__)


def initialise_run(
    run_name: str,
    run_description: Optional[str] = None,
    user: Optional[User] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Run:
    """Initialise a pipeline run.

    Args:
        run_name (str): A unique name for the run.
        run_description (Optional[str], optional): Description for the run, only used if
            initialised with the web UI. Defaults to None.
        user (Optional[User], optional): User that created the run, only used if
            initialised with the web UI. Defaults to None.
        config (Optional[Dict[str, Any]], optional): Dictionary of configuration values
            to pass to the run config template, only used if initialised with the web UI.
            Defaults to None.

    Raises:
        PipelineInitError: `run_name` was not unique.
        PipelineInitError: A directory named `run_name` already exists.

    Returns:
        Run: The initialised pipeline Run Django model object.
    """
    # check for duplicated run name
    p_run = Run.objects.filter(name__exact=run_name)
    if p_run:
        msg = 'Pipeline run name already used. Change name'
        raise PipelineInitError(msg)

    # create the pipeline run folder
    run_path = os.path.join(sett.PIPELINE_WORKING_DIR, run_name)

    if os.path.exists(run_path):
        msg = 'pipeline run path already present!'
        raise PipelineInitError(msg)
    else:
        logger.info('creating pipeline run folder')
        os.mkdir(run_path)

    # copy default config into the pipeline run folder
    logger.info('copying default config in pipeline run folder')
    template_kwargs = config if config else sett.PIPE_RUN_CONFIG_DEFAULTS
    template_str = make_config_template(
        PipelineConfig.TEMPLATE_PATH, run_path=run_path, **template_kwargs
    )
    with open(os.path.join(run_path, 'config.yaml'), 'w') as fp:
        fp.write(template_str)

    # create entry in db
    p_run, _ = get_create_p_run(run_name, run_path, run_description, user)

    return p_run


class Command(BaseCommand):
    """
    This script initialise the Pipeline Run folder and related config
    for the pipeline.
    """
    help = (
        'Create the pipeline run folder structure to run a pipeline '
        'instance'
    )

    def add_arguments(self, parser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
        # positional arguments
        parser.add_argument(
            'runname',
            type=str,
            help='Name of the pipeline run.'
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

        try:
            _ = initialise_run(options['runname'])
        except Exception as e:
            raise CommandError(e)

        logger.info((
            'pipeline run initialisation successful! Please modify the '
            '"config.yaml"'
        ))
