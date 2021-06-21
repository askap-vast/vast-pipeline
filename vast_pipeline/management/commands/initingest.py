import logging
from argparse import ArgumentParser
from django.conf import settings
from django.core.management.base import BaseCommand
from vast_pipeline.pipeline.config import ImageIngestConfig, make_config_template

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script creates a template image configuration file for use with image ingestion
    """
    help = (
        'Create a template image ingestion configuration file'
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
        parser.add_argument(
            'config_file_name',
            nargs=1,
            type=str,
            help=('Filename to write template ingest configuration to.')
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

        template_str = make_config_template(
            ImageIngestConfig.TEMPLATE_PATH,
            **settings.PIPE_RUN_CONFIG_DEFAULTS
            )

        fname = options['config_file_name'][0]
        print("Writing template to: ", fname)
        with open(fname, 'w') as f:
            f.write(template_str+"\n")
