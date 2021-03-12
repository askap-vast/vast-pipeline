import os
import logging

from django.core.management.base import BaseCommand, CommandError

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
            'imgpath',
            type=str,
            help='Path of the image.'
        )

    def handle(self, *args, **options):
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True
