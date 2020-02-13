import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pipeline.models import Dataset


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script is used to clean the data for the current dataset. Use --help for usage.
    """

    help = (
        "Delete a dataset and all related images, sources, etc. Will not delete "
        "objects if they are also related to another dataset."
    )

    def add_arguments(self, parser):
        parser.add_argument("dataset", help="Name of dataset to delete.")

    def handle(self, *args, **options):
        # configure logging
        if options["verbosity"] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger("")
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options["traceback"] = True

        dataset_name = options["dataset"]
        try:
            dataset = Dataset.objects.get(name=dataset_name)
        except Dataset.DoesNotExist:
            raise CommandError("Dataset %s does not exist" % dataset_name)

        logger.info("Database: {0}".format(settings.DATABASES["default"]["NAME"]))
        logger.info("Using dataset '{0}'".format(dataset_name))

        dataset.delete()
