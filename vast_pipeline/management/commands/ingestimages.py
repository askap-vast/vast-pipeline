import logging

from argparse import ArgumentParser
from django.core.management.base import BaseCommand, CommandError
from vast_pipeline.pipeline.config import ImageIngestConfig
from vast_pipeline.pipeline.errors import PipelineConfigError
from vast_pipeline.pipeline.main import Pipeline
from vast_pipeline.pipeline.loading import make_upload_images
from typing import Dict

logger = logging.getLogger(__name__)


class _DummyPipeline(object):
    """
    A stripped down 'dummy' version of the Pipeline class, which
    provides the right methods and attributes for interfacing with
    the `make_upload_images()` function.

    Its main purpose is to correctly set the attribute: `img_paths`
    """
    make_img_paths = Pipeline.match_images_to_data

    def __init__(self,config: ImageIngestConfig) -> None:
        self.config = config
        self.img_paths: Dict[str, Dict[str, str]] = {
            'selavy': {},
            'noise': {},
            'background': {},
        }  # maps input image paths to their selavy/noise/background counterpart path
        self.img_epochs: Dict[str, str] = {}  # maps image names to their provided epoch
        self.make_img_paths()


class Command(BaseCommand):
    """
    This script runs the first part of the pipeline only. It ingests a set of
    images into the database along with their measurements.
    """
    help = (
        'Ingest/add a set of images to the database'
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
            'image_ingest_config',
            nargs=1,
            type=str,
            help=('Image ingestion configuration filename/path.')
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

        # Create image ingestion configuration object from input file
        image_config = ImageIngestConfig.from_file(
            options['image_ingest_config'][0], validate=False
        )

        # Validate the config
        try:
            image_config.validate()
        except PipelineConfigError as e:
            raise CommandError(e)

        # Create a dummy Pipeline instance using the given image ingestion configuration options
        d = _DummyPipeline(image_config)

        # Read, measure and upload the images listed in the image ingestion config
        make_upload_images(d.img_paths,image_config.image_opts())
