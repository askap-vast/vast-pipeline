import os
import logging

import pandas as pd

from ..image.main import SelavyImage
from ..models import Band, Image, Source, SurveySource


logger = logging.getLogger(__name__)


def get_source_models(row):
    src = Source()
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


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

    def process_pipeline(self, dataset_id=None):
        for path in self.image_paths:
            # STEP #1: Load image and sources
            image = SelavyImage(path, self.image_paths[path])
            logger.info(f'read image {image.name}')

            # 1.1 get/create the frequency band
            band_id = self.get_create_img_band(image)

            # 1.2 create image entry in DB
            img = self.get_create_img(dataset_id, band_id, image)

            # 1.3 get the image sources and save them in DB
            sources = image.read_selavy()

            # do checks and fill in missing field for uploading sources
            # in DB (see fields in models.py -> Source model)
            if sources.name.duplicated().any():
                raise Exception('Found duplicated names in sources')

            sources['image_id'] = img.id
            # append img prefix to source name
            img_prefix = image.name.split('.i.', 1)[-1].split('.', 1)[0] + '_'
            sources['name'] = img_prefix + sources['name']
            logger.info(f'Processed sources dataframe of shape: {sources.shape}')

            # do DB bulk create
            sources['dj_models'] = sources.apply(get_source_models, axis=1)
            # do a upload without evaluate the objects, that should be faster
            # see https://docs.djangoproject.com/en/2.2/ref/models/querysets/

            # TODO: remove development operations
            if Source.objects.filter(image_id=img.id).exists():
                del_out = Source.objects.filter(image_id=img.id).delete()
                logger.info(f'deleting all sources for this image: {del_out}')

            batch_size = 1_000
            for idx in range(0, sources.dj_models.size, batch_size):
                batch = sources.dj_models.iloc[idx : idx + batch_size].values.tolist()
                out_bulk = Source.objects.bulk_create(batch, batch_size)
                logger.info(f'bulk uploaded #{len(out_bulk)} sources')

            # # save sources to parquet file in dataset folder
            parq_folder = os.path.join(self.config.DATASET_PATH, img_prefix.strip('_'))
            if not os.path.exists(parq_folder):
                os.mkdir(parq_folder)
            f_parquet = os.path.join(parq_folder, 'sources.parquet')
            sources.drop('dj_models', axis=1).to_parquet(f_parquet, index=False)

        # STEP #2: source association
        if SurveySource.objects.exists():
            pass
        # 2.1 Associate Sources with reference catalogues

        # 2.2 Associate with other sources

        # STEP #3: ...
        pass

    @staticmethod
    def get_create_img_band(image):
        '''
        Return the existing Band row for the given FitsImage.
        An image is considered to belong to a band if its frequency is within some
        tolerance of the band's frequency.
        Returns a Band row or None if no matching band.
        '''
        # For now we match bands using the central frequency.
        # This assumes that every band has a unique frequency,
        # which is true for the datasets we've used so far.
        freq = int(image.freq_eff * 1.e-6)
        freq_band = int(image.freq_bw * 1.e-6)
        # TODO: refine the band query
        for band in Band.objects.all():
            diff = abs(freq - band.frequency) / float(band.frequency)
            if diff < 0.02:
                return band.id

        # no band has been found so create it
        band = Band(name=str(freq), frequency=freq, bandwidth=freq_band)
        logger.info(f'Adding new frequency band: {band}')
        band.save()

        return band.id

    @staticmethod
    def get_create_img(dataset_id, band_id, image):
        img = Image.objects.filter(name__exact=image.name)
        if img:
            return img.get()

        img = Image(dataset_id=dataset_id, band_id=band_id)
        # set the attributes and save the image,
        # by selecting only valid (not hidden) attributes
        # FYI attributs and/or method starting with _ are hidden
        # and with __ can't be modified/called
        for fld in img._meta.get_fields():
            if getattr(fld, 'attname', None) and getattr(image, fld.attname, None):
                setattr(img, fld.attname, getattr(image, fld.attname))
        img.save()

        return img
