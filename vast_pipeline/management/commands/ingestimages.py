import os
import logging

from django.core.management.base import BaseCommand, CommandError
from vast_pipeline.pipeline.loading import make_upload_images

from vast_pipeline.models import Run
from vast_pipeline.pipeline.main import Pipeline
from ..helpers import get_p_run_name

logger = logging.getLogger(__name__)

class _DummyConfig(object):

    def __init__(self,image_files,selavy_files,noise_files,background_files):
        self.IMAGE_FILES = image_files
        self.SELAVY_FILES = selavy_files
        self.NOISE_FILES = noise_files
        self.BACKGROUND_FILES = background_files

class _DummyPipeline(object):
    make_image_paths = Pipeline.match_images_to_data

    def __init__(self,image_files,selavy_files,noise_files,background_files):
        self.config = _DummyConfig(image_files,selavy_files,noise_files,background_files)
        self.config, _ = Pipeline.check_for_epoch_based(self.config)
        self.make_image_paths()


class Command(BaseCommand):
    """
    This script injects an image into the database along with extracting,
    correcting and saving the measurements and obtaining estimates of the rms.
    """
    help = (
        'Injects an image into the database'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-i',
            '--image-files',
            nargs='+',
            type=str,
            required=True,
            help=('Paths to image files.')
        )
        parser.add_argument(
            '-s',
            '--selavy-files',
            nargs='+',
            type=str,
            required=True,
            help=('Paths to selavy files.')
        )
        parser.add_argument(
            '-n',
            '--noise-files',
            nargs='+',
            type=str,
            required=True,
            help=('Paths to noise files.')
        )
        parser.add_argument(
            '-b',
            '--background-files',
            nargs='+',
            type=str,
            required=True,
            help=('Paths to background files.')
        )

    def handle(self, *args, **options):
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        n_images = len(options['image_files'])
        n_selavy = len(options['selavy_files'])
        n_noise = len(options['noise_files'])
        n_background = len(options['background_files'])

        if not n_images == n_selavy:
            raise CommandError("Number of selavy files not equal to number of image files")

        if not n_images == n_noise:
            raise CommandError("Number of noise files not equal to number of image files")

        if not n_images == n_background:
            raise CommandError("Number of background files not equal to number of image files")

        d = _DummyPipeline(
            options['image_files'],
            options['selavy_files'],
            options['noise_files'],
            options['background_files'],
        )

        make_upload_images(d.img_paths)
