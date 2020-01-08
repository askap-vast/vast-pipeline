import os
import operator
import logging

import pandas as pd
from astropy import units as u
from astropy.coordinates import Angle, match_coordinates_sky, SkyCoord

from ..image.main import SelavyImage
from ..models import Association, Band, Catalog, Image, Source, SurveySource
from ..utils.utils import deg2hms, deg2dms


logger = logging.getLogger(__name__)


def get_source_models(row):
    src = Source()
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


def get_catalog_models(row, dataset=None):
    name = f"catalog_{deg2hms(row['ave_ra'])}{deg2dms(row['ave_dec'])}"
    return Catalog(
        name=name,
        ave_ra=row['ave_ra'],
        ave_dec=row['ave_dec'],
        dataset=dataset
    )


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
        src_dj_obj = pd.DataFrame()
        for path in self.image_paths:
            # STEP #1: Load image and sources
            image = SelavyImage(path, self.image_paths[path])
            logger.info(f'read image {image.name}')

            # 1.1 get/create the frequency band
            band_id = self.get_create_img_band(image)

            # 1.2 create image entry in DB
            img, exists_f = self.get_create_img(dataset, band_id, image)
            # add image to list
            images.append(img)
            if exists_f:
                logger.info(f'image {img.name} already processed, grab sources')
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
            logger.info(f'Processed sources dataframe of shape: {sources.shape}')

            # do DB bulk create
            sources['src_dj'] = sources.apply(get_source_models, axis=1)
            # do a upload without evaluate the objects, that should be faster
            # see https://docs.djangoproject.com/en/2.2/ref/models/querysets/
            # # TODO: remove development operations
            # if Source.objects.filter(image_id=img.id).exists():
            #     del_out = Source.objects.filter(image_id=img.id).delete()
            #     logger.info(f'deleting all sources for this image: {del_out}')

            batch_size = 10_000
            for idx in range(0, sources.src_dj.size, batch_size):
                out_bulk = Source.objects.bulk_create(
                    sources.src_dj.iloc[idx : idx + batch_size].values.tolist(),
                    batch_size
                )
                logger.info(f'bulk uploaded #{len(out_bulk)} sources')

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
        images.sort(key=operator.attrgetter('time'))
        limit = Angle(self.config.ASSOCIATION_RADIUS * u.arcsec)

        # read the needed sources fields
        skyc1_srcs = pd.read_parquet(
            images[0].sources_path,
            columns=['id','ra','dec']
        )
        skyc1_srcs['cat'] = pd.np.NaN
        # create base catalog
        skyc1 = SkyCoord(
            ra=skyc1_srcs.ra * u.degree,
            dec=skyc1_srcs.dec * u.degree
        )
        # initialise the df of catalogs with the base one
        catalogs_df = pd.DataFrame()
        for it, image in enumerate(images[1:]):
            logger.info(f'Association iteration: #{it + 1}')
            # load skyc2 sources and create SkyCoord/sky catalog(skyc)
            skyc2_srcs = pd.read_parquet(
                image.sources_path,
                columns=['id','ra','dec']
            )
            skyc2_srcs['cat'] = pd.np.NaN
            skyc2 = SkyCoord(
                ra=skyc2_srcs.ra * u.degree,
                dec=skyc2_srcs.dec * u.degree
            )
            idx, d2d, d3d = skyc1.match_to_catalog_sky(skyc2)
            # selection
            sel = d2d <= limit

            # assign catalog temp id in skyc1 sorces df if not previously defined
            start_elem = 0. if skyc1_srcs.cat.max() is pd.np.NaN else skyc1_srcs.cat.max()
            nan_sel = skyc1_srcs.cat.isna().values
            skyc1_srcs.loc[ sel & nan_sel, 'cat'] = (
                skyc1_srcs.index[ sel & nan_sel].values + start_elem + 1.
            )
            # append skyc1 selection to catalog df
            catalogs_df = catalogs_df.append(skyc1_srcs)

            # assign catalog temp id to skyc2 sorces from skyc1
            skyc2_srcs.loc[idx[sel], 'cat'] = skyc1_srcs.loc[sel, 'cat'].values
            # append skyc2 selection to catalog df
            catalogs_df = catalogs_df.append(skyc2_srcs.loc[idx[sel]])

            # update skyc1 and df for next association iteration
            # # calculate average angle for skyc1
            # tmp_skyc1_srcs = (
            #     skyc1_srcs.loc[:, ['ra','dec']].copy()
            #     .rename(columns={'ra':'ra1','dec':'dec1'})
            # )
            # tmp_skyc1_srcs.loc[idx[sel], 'ra2'] = skyc2_srcs.loc[idx[sel], 'ra'].values
            # tmp_skyc1_srcs.loc[idx[sel], 'dec2'] = skyc2_srcs.loc[idx[sel], 'dec'].values
            # tmp_skyc1_srcs['ra'] = tmp_skyc1_srcs.loc[:,['ra1','ra2']].mean(axis=1)
            # skyc1 = SkyCoord(
            #     ra=tmp_skyc1_srcs.ra* u.degree,
            #     dec=tmp_skyc1_srcs.dec* u.degree
            #     )
            skyc1 = SkyCoord([skyc1, skyc2[idx[~sel]]])
            skyc1_srcs = (
                skyc1_srcs.append(skyc2_srcs.loc[idx[~sel]])
                .reset_index(drop=True)
            )

        # add leftover souces from skyc2
        catalogs_df = (
            catalogs_df.append(skyc2_srcs.loc[idx[~sel]])
            .reset_index(drop=True)
        )
        start_elem = catalogs_df.cat.max() + 1.
        nan_sel = catalogs_df.cat.isna().values
        catalogs_df.loc[nan_sel, 'cat'] = (
            catalogs_df.index[ nan_sel].values + start_elem
        )

        # tidy the df of catalogs to drop duplicated entries
        # to have unique rows of c_name and src_id
        catalogs_df = catalogs_df.drop_duplicates()

        # calculated average ra and dec
        cat_df = (
            catalogs_df.groupby('cat')['ra','dec']
            .mean().reset_index()
            .rename(columns={'ra':'ave_ra', 'dec':'ave_dec'})
        )
        # generate the catalog models
        cat_df['cat_dj'] = cat_df.apply(
            get_catalog_models,
            axis=1,
            dataset=dataset
        )
        # create catalogs in DB
        # TODO remove deleting existing catalogs
        if Catalog.objects.filter(dataset=dataset).exists():
            cats = Catalog.objects.filter(dataset=dataset).delete()
            logger.info(f'deleting all catalogs for this dataset: {cats}')

        batch_size = 10_000
        for idx in range(0, cat_df.cat_dj.size, batch_size):
            out_bulk = Catalog.objects.bulk_create(
                cat_df.cat_dj.iloc[idx : idx + batch_size].tolist(),
                batch_size
            )
            logger.info(f'bulk created #{len(out_bulk)} catalogs')

        catalogs_df = (
            catalogs_df.merge(cat_df, on='cat')
            .merge(src_dj_obj, on='id')
        )
        del cat_df

        # Create Associan objects (linking sources and catalogs) and insert in DB
        catalogs_df['assoc_dj'] = catalogs_df.apply(
            lambda row: Association(
                source=row['src_dj'],
                catalog=row['cat_dj']
            ), axis=1
        )
        batch_size = 10_000
        for idx in range(0, catalogs_df.assoc_dj.size, batch_size):
            out_bulk = Association.objects.bulk_create(
                catalogs_df.assoc_dj.iloc[idx : idx + batch_size].tolist(),
                batch_size
            )
            logger.info(f'bulk created #{len(out_bulk)} associations')

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
            return (img.get(), True)

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

        return (img, False)
