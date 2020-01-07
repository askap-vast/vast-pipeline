import logging

from django.db import connection, transaction
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pipeline.models import Cube, Image, Source, Band, Dataset, CrossMatch


logger = logging.getLogger(__name__)


def clear_database(purge=False):
    """
    Delete all data from the database
      purge - if True, all rows are deleted. If False, manual edits are kept eg persistent sources
    """
    # Delete Flux rows manually as there may be many and Django's bulk delete is very
    # inefficient and uses all the RAM on your computer if the table is big.
    with transaction.atomic():
        cursor = connection.cursor()
        logger.info("deleting Fluxes")
        cursor.execute("DELETE FROM pipeline_flux")
        if purge:
            logger.info("deleting all CrossMatches")
            cursor.execute("DELETE FROM pipeline_crossmatch")
            logger.info("deleting all Sources")
            cursor.execute("DELETE FROM pipeline_source")
        else:
            logger.info("deleting CrossMatches")
            cursor.execute("DELETE FROM pipeline_crossmatch WHERE source_id NOT IN (SELECT name FROM pipeline_source WHERE persistent)")
            logger.info("deleting Sources")
            cursor.execute("DELETE FROM pipeline_source WHERE NOT persistent")

    Source.objects.update(first_image=None)
    logger.info("deleting Images")
    Image.objects.all().delete()
    logger.info("deleting Cubes")
    Cube.objects.all().delete()
    Band.objects.all().delete()
    Dataset.objects.all().delete()
    logger.info("Kept data:")
    logger.info("   Sources: {0} rows".format(Source.objects.all().count()))
    logger.info("   CrossMatches: {0} rows".format(CrossMatch.objects.all().count()))


class Command(BaseCommand):
    """
    This script is used to clean the data for the current dataset

    Use --help for usage, and refer README.
    """
    help = 'Clean up the a dataset or all data. Delete all non-persistent data from tables'

    def add_arguments(self, parser):
        # positional arguments
        parser.add_argument('dataset', nargs=1, type=str)

        # kwargs or options
        parser.add_argument(
            '--purge', action='store_true', dest='purge', default=False,
            help='delete *ALL DATA* including manual edits (requires --clear)'
        )

    def handle(self, *args, **options):
        # TODO: check daset name validity and if present
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        self.dataset_name = options['dataset'][0]

        logger.info("Database: {0}".format(settings.DATABASES['default']['NAME']))
        logger.info("Using dataset '{0}'".format(self.dataset_name))

        msg = "Deleting *all* data including manual edits" if options['purge'] else "Deleting all data except manual edits"
        logger.info(msg)
        clear_database(purge=options['purge'])
