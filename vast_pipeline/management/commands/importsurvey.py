"""
Import a survey catalogue into the VAST pipeline database (SurveySource table).

Usage: ./manage.py importsurvey survey_name file
Eg   : ./manage.py importsurvey NVSS /data/nvss.fits
"""

import os
import logging

from argparse import ArgumentParser
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sqlalchemy import create_engine

from vast_pipeline.models import Survey, SurveySource
from vast_pipeline.survey.catalogue import get_survey
from vast_pipeline.survey.translators import translators
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script is used to import data for a survey

    Use --help for usage, and refer README.
    """
    help = (
        'Import a survey catalogue into the VAST pipeline database '
        '(SurveySource table).'
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
        # positional arguments
        parser.add_argument(
            'survey_name', nargs=1, type=str, help='the name of the survey'
        )
        parser.add_argument(
            'path_to_survey_file',
            nargs=1,
            type=str,
            help='the path to the survey file'
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
        # check/create survey folder
        if not os.path.exists(settings.SURVEYS_WORKING_DIR):
            os.mkdir(settings.SURVEYS_WORKING_DIR)

        watch = StopWatch()
        survey_name = options.get('survey_name')[0]

        tr = translators['DEFAULT']
        if survey_name.upper() in translators.keys():
            tr = translators[survey_name.upper()]
            logger.info("Using translator %s", survey_name.upper())
        else:
            logger.info("Using translator DEFAULT")

        # check if the survey exists and eventually delete it
        survey = Survey.objects.filter(name__exact=survey_name)
        if survey:
            logger.info('found previous survey with same name, deleting them')
            watch.reset()
            survey.delete()
            logger.info('total time survey deletion %f s', watch.reset())

        # create the survey
        survey = Survey(name=survey_name, frequency=tr['freq'])
        survey.save()

        # get the sources
        path = os.path.realpath(options.get('path_to_survey_file')[0])
        if not os.path.exists(path):
            raise CommandError('passed survey file does not exist!')

        sources = get_survey(path, survey.name, survey.id, tr)

        # dump sources to parquet
        watch.reset()
        parq_folder = os.path.join(settings.SURVEYS_WORKING_DIR, survey_name)
        if not os.path.exists(parq_folder):
            os.mkdir(parq_folder)
        f_parquet = os.path.join(parq_folder, 'sources.parquet')
        sources.to_parquet(f_parquet, index=False)
        logger.info('dumping sources to parquet, time: %f s', watch.reset())

        # upload the sources
        config = settings.DATABASES['default']
        eng = create_engine(
            (
                f"{config['ENGINE'].split('.')[-1]}://"
                f"{config['USER']}:{config['PASSWORD']}@"
                f"{config['HOST']}:{config['PORT']}/{config['NAME']}"
            )
        )

        logger.info('Inserting #%i records in db', sources.shape[0])
        sources.to_sql(
            SurveySource._meta.db_table,
            eng,
            if_exists='append',
            index=False,
            chunksize=100_000,
            method='multi',
        )
        logger.info('Inserted #%i records', SurveySource.objects.filter(survey_id=survey.id).count())
        logger.info('Upload successful! Duration: %s', watch.reset_init())
