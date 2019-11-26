"""
Import a survey catalogue into the VAST pipeline database (SurveySource table).

Usage: ./manage.py importsurvey survey_name file
Eg   : ./manage.py importsurvey NVSS /data/nvss.fits
"""

import os
import logging

from django.db import connection, transaction
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sqlalchemy import create_engine

from pipeline.models import Survey, SurveySource
from pipeline.survey.catalogue import get_survey
from pipeline.survey.translators import translators
from pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script is used to clean the data for the current dataset

    Use --help for usage, and refer README.
    """
    help = (
        'Import a survey catalogue into the VAST pipeline database '
        '(SurveySource table).'
    )

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        watch = StopWatch()
        survey_name = options.get('survey_name')[0]

        tr = translators['DEFAULT']
        if survey_name.upper() in translators.keys():
            tr = translators[survey_name.upper()]
            logger.info("Using translator {0}".format(survey_name.upper()))
        else:
            logger.info("Using translator DEFAULT")

        # check if the survey exists and eventually delete it
        surveys_matches = Survey.objects.filter(name__exact=survey_name)
        if surveys_matches:
            logger.info('found previous survey with same name, deleting them')
            for survey in surveys_matches:
                watch.reset()
                survey.delete()
                logger.info(f'total time survey deletion {watch.reset()}s')

        # create the survey
        survey = Survey(name=survey_name,frequency_mhz=tr['freq'])
        survey.save()

        # get the sources
        path = os.path.realpath(options.get('path_to_survey_file')[0])
        if not os.path.exists(path):
            raise CommandError('passed survey file do not exists!')

        sources = get_survey(path, survey.name, survey.id, tr)

        # upload the sources
        config = settings.DATABASES['default']
        eng = create_engine(
            (
                f"{config['ENGINE'].split('.')[-1]}://"
                f"{config['USER']}:{config['PASSWORD']}@"
                f"{config['HOST']}:{config['PORT']}/{config['NAME']}"
            )
        )

        logger.info(f'Inserting #{sources.shape[0]} records in db')
        sources.to_sql(
            SurveySource._meta.db_table,
            eng,
            if_exists='append',
            index=False,
            chunksize=100_000,
            method='multi',
        )
        logger.info(f'Inserted #{SurveySource.objects.count()} records')
        logger.info(f'Upload successful! Duration: {watch.reset_init()}s')
