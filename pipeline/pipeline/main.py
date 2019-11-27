import logging

import pandas as pd

from ..image.main import SelavyImage
from ..models import Image, Source


logger = logging.getLogger(__name__)


class Pipeline():
    '''Holds all the state associated with a pipeline instance (usually just one is used)'''

    def __init__(self, max_img=10, config=None):
        '''
        We limit the size of the cube cache so we don't hit the max files open limit
        or use too much RAM
        '''
        self.max_img = max_img
        self.config = config
        if self.config.MAX_BACKWARDS_MONITOR_IMAGES:
            self.max_img=self.config.MAX_BACKWARDS_MONITOR_IMAGES + 1

        # A dictionary of path to Fits images, eg "/data/images/I1233234.FITS" and
        # selavy catalogues
        # Used as a cache to avoid reloading cubes all the time.
        self.image_paths = {
            x:y for x,y in zip(config.IMAGE_FILES, config.SELAVY_FILES)
        }

    def read_img(self):
        for path in self.image_paths:
            image = SelavyImage(path)
            logger.info(f'reading image {image.name}')

            # get the image data
            # sources = image.read_selavy()
            import ipdb; ipdb.set_trace()  # breakpoint 9f3f4f91 //
        pass
