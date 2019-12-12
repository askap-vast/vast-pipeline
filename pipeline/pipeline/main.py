import os
import operator
import logging

import pandas as pd
from astropy import units as u
from astropy.coordinates import Angle, match_coordinates_sky, SkyCoord

from ..image.main import SelavyImage
from ..models import Band, Catalog, Image, Source, SurveySource
from ..utils.utils import deg2hms, deg2dms


logger = logging.getLogger(__name__)


def get_source_models(row):
    src = Source()
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


def get_catalog_models(row):
    name = f"catalog_{deg2hms(row['ave_ra'])}{deg2dms(row['ave_dec'])}"
    c = Catalog(name=name, ave_ra=row['ave_ra'], ave_dec=row['ave_dec'])
    return c


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

    def process_pipeline(self, dataset):
        images = []
        for path in self.image_paths:
            # STEP #1: Load image and sources
            image = SelavyImage(path, self.image_paths[path])
            logger.info(f'read image {image.name}')

            # 1.1 get/create the frequency band
            band_id = self.get_create_img_band(image)

            # 1.2 create image entry in DB
            img = self.get_create_img(dataset, band_id, image)
            # add image to list
            images.append(img)

            # 1.3 get the image sources and save them in DB
            sources = image.read_selavy(img)
            logger.info(f'Processed sources dataframe of shape: {sources.shape}')

            # do DB bulk create
            sources['dj_model'] = sources.apply(get_source_models, axis=1)
            # do a upload without evaluate the objects, that should be faster
            # see https://docs.djangoproject.com/en/2.2/ref/models/querysets/
            # TODO: remove development operations
            if Source.objects.filter(image_id=img.id).exists():
                del_out = Source.objects.filter(image_id=img.id).delete()
                logger.info(f'deleting all sources for this image: {del_out}')

            batch_size = 1_000
            for idx in range(0, sources.dj_model.size, batch_size):
                out_bulk = Source.objects.bulk_create(
                    sources.dj_model.iloc[idx : idx + batch_size].values.tolist(),
                    batch_size
                )
                logger.info(f'bulk uploaded #{len(out_bulk)} sources')

            # make a columns with the source id
            sources['id'] = sources.dj_model.apply(getattr, args=('id',))

            # save sources to parquet file in dataset folder
            if not os.path.exists(os.path.dirname(img.sources_path)):
                os.mkdir(os.path.dirname(img.sources_path))
            sources.drop('dj_model', axis=1).to_parquet(
                img.sources_path,
                index=False
            )
            del sources, image, band_id, img, out_bulk

        # STEP #2: source association
        # 2.1 Associate Sources with reference catalogues
        if SurveySource.objects.exists():
            pass

        # 2.2 Associate with other sources
        # order images by time
        images.sort(key=operator.attrgetter('time'))


        limit = Angle(self.config.ASSOCIATION_RADIUS * u.degree)

        # read the needed sources fields
        c1_srcs = pd.read_parquet(
            images[0].sources_path,
            columns=['id','ra','dec']
        )
        # create base catalog
        c1 = SkyCoord(
            ra=c1_srcs.ra * u.degree,
            dec=c1_srcs.dec * u.degree
        )
        # initialise the df of catalogues with the base one
        catalogs_df = pd.DataFrame()
        c1_df = self.create_catalog_df(c1_srcs)
        for image in images[1:]:
            c2_srcs = pd.read_parquet(
                image.sources_path,
                columns=['id','ra','dec']
            )
            c2 = SkyCoord(
                ra=c2_srcs.ra * u.degree,
                dec=c2_srcs.dec * u.degree
            )
            idx, d2d, d3d = c1.match_to_catalog_sky(c2)

            selection = d2d <= limit
            # select from c1 df and append it to catalogue df
            c1_df = c1_df.loc[selection]
            catalogs_df = catalogs_df.append(c1_df)

            # create c2 df and select from it, and append to catalogue df
            c2_df = self.create_catalog_df(c2_srcs)
            c2_df = c2_df.loc[idx[selection]]
            catalogs_df = catalogs_df.append(c2_df)

            # # calculate the new base catalogue
            # c1 = SkyCoord(
            #     ra=np.mean(
            #         [
            #             c1[selection].ra,
            #             c2[idx[selection]].ra
            #         ], axis=0) * u.degree,
            #     dec=np.mean(
            #         [
            #             c1[selection].dec,
            #             c2[idx[selection]].dec
            #         ], axis=0) * u.degree,
            # )
            # update c1 for next association iteration
            c1 = SkyCoord([c1, c2[idx[~selection]]])

        # tidy the df of catalogues to drop duplicated entries
        # to have unique rows of c_name and src_id
        catalogs_df = catalogs_df.drop_duplicates()

        # calculated average ra and dec
        cat_df = (
            catalogs_df.groupby('c_name')['ra','dec']
            .mean().reset_index()
            .rename(columns={'ra':'ave_ra', 'dec':'ave_dec'})
        )
        # generate the catalog models
        cat_df['dj_model'] = cat_df.apply(get_catalog_models, axis=1)
        catalogs_df = catalogs_df.merge(cat_df, on='c_name')
        del cat_df

        # insert association in DB
        import ipdb; ipdb.set_trace()  # breakpoint c6ac6b08 //

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
    def get_create_img(dataset, band_id, image):
        img = Image.objects.filter(name__exact=image.name)
        if img:
            return img.get()

        # at this stage source parquet file not created but assume location
        sources_path = os.path.join(
            dataset.path,
            image.name.split('.i.', 1)[-1].split('.', 1)[0],
            'sources.parquet'
            )
        img = Image(
            dataset_id=dataset.id,
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
        img.save()

        return img

    @staticmethod
    def create_catalog_df(src_df):
        df = src_df.rename(columns={'id':'src_id'})
        df['c_name'] = 'c' + df.index.astype(str)
        return df

