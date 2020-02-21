import os
import operator
import logging

import pandas as pd
from astropy import units as u
from astropy.coordinates import Angle

from ..image.main import SelavyImage
from ..models import Band, Image, SkyRegion, Source, SurveySource
from ..utils.utils import eq_to_cart
from .association import association


logger = logging.getLogger(__name__)


def get_source_models(row):
    src = Source()
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


def get_create_skyreg(dataset, image):
    skyr = SkyRegion.objects.filter(
        centre_ra=image.ra,
        centre_dec=image.dec,
        xtr_radius=image.radius_pixels
    )
    if skyr:
        skyr = skyr.get()
        logger.info('Found sky region %s', skyr)
        if dataset not in skyr.dataset.all():
            logger.info('Adding %s to sky region %s', dataset, skyr)
            skyr.dataset.add(dataset)
        return skyr

    x, y, z = eq_to_cart(image.ra, image.dec)
    skyr = SkyRegion(
        centre_ra=image.ra,
        centre_dec=image.dec,
        xtr_radius=image.radius_pixels,
        x=x,
        y=y,
        z=z,
    )
    skyr.save()
    logger.info('Created sky region %s', skyr)
    skyr.dataset.add(dataset)
    logger.info('Adding %s to sky region %s', dataset, skyr)
    return skyr


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
        self.img_selavy_paths = {
            x:y for x,y in zip(config.IMAGE_FILES, config.SELAVY_FILES)
        }

    def process_pipeline(self, dataset):
        images = []
        src_dj_obj = pd.DataFrame()
        for path in self.img_selavy_paths:
            # STEP #1: Load image and sources
            image = SelavyImage(path, self.img_selavy_paths[path])
            logger.info('read image %s', image.name)

            # 1.1 get/create the frequency band
            band_id = self.get_create_img_band(image)

            # 1.2 create image and skyregion entry in DB
            img, exists_f = self.get_create_img(dataset, band_id, image)
            # add image to list
            images.append(img)
            if exists_f:
                logger.info(
                    'image %s already processed, grab sources', img.name
                )
                # grab the sources and skip to process next image
                sources = (
                    pd.Series(
                        Source.objects.filter(image__id=img.id),
                        name='src_dj'
                    )
                    .to_frame()
                )
                sources['id'] = sources.src_dj.apply(getattr, args=('id',))
                src_dj_obj = src_dj_obj.append(sources)
                continue

            # 1.3 get the image sources and save them in DB
            sources = image.read_selavy(img)
            logger.info(
                'Processed sources dataframe of shape: (%i, %i)', sources.shape[0], sources.shape[1]
            )

            # do DB bulk create
            sources['src_dj'] = sources.apply(get_source_models, axis=1)
            # do a upload without evaluate the objects, that should be faster
            # see https://docs.djangoproject.com/en/2.2/ref/models/querysets/
            batch_size = 10_000
            for idx in range(0, sources.src_dj.size, batch_size):
                out_bulk = Source.objects.bulk_create(
                    sources.src_dj.iloc[idx : idx + batch_size].values.tolist(),
                    batch_size
                )
                logger.info('bulk uploaded #%i sources', len(out_bulk))

            # make a columns with the source id
            sources['id'] = sources.src_dj.apply(getattr, args=('id',))
            src_dj_obj = src_dj_obj.append(sources.loc[:, ['id','src_dj']])

            # save sources to parquet file in dataset folder
            if not os.path.exists(os.path.dirname(img.sources_path)):
                os.mkdir(os.path.dirname(img.sources_path))

            sources.drop('src_dj', axis=1).to_parquet(
                img.sources_path,
                index=False
            )
            del sources, image, band_id, img, out_bulk

        # STEP #2: source association
        # 2.1 Associate Sources with reference catalogs
        if SurveySource.objects.exists():
            pass

        # 2.2 Associate with other sources
        # order images by time
        images.sort(key=operator.attrgetter('datetime'))
        limit = Angle(self.config.ASSOCIATION_RADIUS * u.arcsec)

        association(dataset, images, src_dj_obj, limit)

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
        logger.info('Adding new frequency band: %s', band)
        band.save()

        return band.id

    @staticmethod
    def get_create_img(dataset, band_id, image):
        img = Image.objects.filter(name__exact=image.name)
        if img.exists():
            img = img.get()
            skyreg = get_create_skyreg(dataset, img)
            # check and add the many to many if not existent
            if not Image.objects.filter(
                id=img.id, dataset__id=dataset.id
            ).exists():
                img.dataset.add(dataset)

            return (img, True)

        # at this stage source parquet file not created but assume location
        sources_path = os.path.join(
            dataset.path,
            image.name.split('.i.', 1)[-1].split('.', 1)[0],
            'sources.parquet'
            )
        img = Image(
            band_id=band_id,
            sources_path=sources_path
        )
        # set the attributes and save the image,
        # by selecting only valid (not hidden) attributes
        # FYI attributs and/or method starting with _ are hidden
        # and with __ can't be modified/called
        for fld in img._meta.get_fields():
            if getattr(fld, 'attname', None) and getattr(image, fld.attname, None):
                setattr(img, fld.attname, getattr(image, fld.attname))

        # get create the sky region and associate with image
        skyreg = get_create_skyreg(dataset, img)
        img.skyreg = skyreg

        img.save()
        img.dataset.add(dataset)

        return (img, False)
