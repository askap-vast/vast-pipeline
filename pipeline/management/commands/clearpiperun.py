import logging

from django.core.management.base import BaseCommand, CommandError

from pipeline.models import Run


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script is used to clean the data for the current pipeline .
    Use --help for usage.
    """

    help = (
        "Delete a pipeline run and all related images, sources, etc."
        " Will not delete  objects if they are also related to another "
        "pipeline run."
    )

    def add_arguments(self, parser):
        parser.add_argument("piperun", help="Name of pipeline run to delete.")

    def handle(self, *args, **options):
        # configure logging
        if options["verbosity"] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger("")
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options["traceback"] = True

        p_run_name = options["piperun"]
        try:
            p_run = Run.objects.get(name=p_run_name)
        except Run.DoesNotExist:
            raise CommandError(f"Pipeline run {p_run_name} does not exist")

        logger.info("Using pipeline run '%s'", p_run_name)

        p_run.delete()
