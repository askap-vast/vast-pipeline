import logging
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

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs=1,
            type=str,
            help=('Filename to write template ingest configuration to.')
        )

    def handle(self, *args, **options):
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

        fname = options['file'][0]
        print("Writing template to: ", fname)
        with open(fname, 'w') as f:
            f.write(template_str+"\n")
