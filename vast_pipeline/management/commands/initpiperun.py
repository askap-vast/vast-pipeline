"""
Initialises a pipeline run and creates the relevant directories.

Usage: ./manage.py initpiperun pipeline_run_name
"""

import os
import logging

from argparse import ArgumentParser
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as sett
from django.contrib.auth.models import User
from jinja2 import Template

from vast_pipeline.models import Run
from vast_pipeline.pipeline.errors import PipelineInitError
from vast_pipeline.pipeline.utils import get_create_p_run


logger = logging.getLogger(__name__)


def initialise_run(
    run_name: str, run_description: str=None, user: User=None, config=None
) -> Run:
    """
    Initialises a pipeline run object.

    Args:
        run_name: The string name of the run.
        run_description: The description of the run supplied by the user.
        user: The Django user that is performing the run (None if from CLI).
        config: The pipeline configuration settings.

    Returns:
        The pipeline run Django model object.
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
    template_f = os.path.join(
        sett.BASE_DIR,
        'vast_pipeline',
        'config_template.py.j2'
    )
    with open(template_f, 'r') as fp:
        template_str = fp.read()

    tm = Template(template_str)
    with open(os.path.join(run_path, 'config.py'), 'w') as fp:
        if config:
            fp.write(tm.render(**config))
        else:
            fp.write(tm.render(**sett.PIPE_RUN_CONFIG_DEFAULTS))

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
            p_run = initialise_run(options['runname'])
        except Exception as e:
            raise CommandError(e)

        logger.info((
            'pipeline run initialisation successful! Please modify the '
            '"config.py"'
        ))
