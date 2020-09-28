import os
import logging
import numpy as np
import pandas as pd
import dask.dataframe as dd

from astropy.io import fits
from django.conf import settings

from psutil import cpu_count
from itertools import chain

from vast_pipeline.utils.utils import deg2hms, deg2dms, eq_to_cart, StopWatch
from vast_pipeline.models import (
    Band, Image, Measurement, Run, Source, SkyRegion
)
from vast_pipeline.image.utils import on_sky_sep
from vast_pipeline.daskmanager.manager import DaskManager


logger = logging.getLogger(__name__)


# Dask custom aggregations
# from https://docs.dask.org/en/latest/dataframe-groupby.html#aggregate
collect_list = dd.Aggregation(
    name='collect_list',
    chunk=lambda s: s.apply(list),
    agg=lambda s0: s0.apply(
        lambda chunks: list(chain.from_iterable(chunks))
    ),
)


def get_measurement_models(row):
    one_m = Measurement()
    for fld in one_m._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(one_m, fld.attname, row[fld.attname])
    return one_m


def get_create_skyreg(p_run, image):
    '''
    This create a Sky Region object in Django ORM given the related
    image object.
    '''
    # In the calculations below, it is assumed the image has square
    # pixels (this pipeline has been designed for ASKAP images, so it
    # should always be square). It will likely give wrong results if not
    skyr = SkyRegion.objects.filter(
        centre_ra=image.ra,
        centre_dec=image.dec,
        xtr_radius=image.fov_bmin
    )
    if skyr:
        skyr = skyr.get()
        logger.info('Found sky region %s', skyr)
        if p_run not in skyr.run.all():
            logger.info('Adding %s to sky region %s', p_run, skyr)
            skyr.run.add(p_run)
        return skyr

    x, y, z = eq_to_cart(image.ra, image.dec)
    skyr = SkyRegion(
        centre_ra=image.ra,
        centre_dec=image.dec,
        width_ra=image.physical_bmin,
        width_dec=image.physical_bmaj,
        xtr_radius=image.fov_bmin,
        x=x,
        y=y,
        z=z,
    )
    skyr.save()
    logger.info('Created sky region %s', skyr)
    skyr.run.add(p_run)
    logger.info('Adding %s to sky region %s', p_run, skyr)
    return skyr


def get_create_img_band(image):
    '''
    Return the existing Band row for the given FitsImage.
    An image is considered to belong to a band if its frequency is within some
    tolerance of the band's frequency.
    Returns a Band row or None if no matching band.
    '''
    # For now we match bands using the central frequency.
    # This assumes that every band has a unique frequency,
    # which is true for the data we've used so far.
    freq = int(image.freq_eff * 1.e-6)
    freq_band = int(image.freq_bw * 1.e-6)
    # TODO: refine the band query
    for band in Band.objects.all():
        diff = abs(freq - band.frequency) / float(band.frequency)
        if diff < 0.02:
            return band

    # no band has been found so create it
    band = Band(name=str(freq), frequency=freq, bandwidth=freq_band)
    logger.info('Adding new frequency band: %s', band)
    band.save()

    return band


def get_create_img(p_run, band_id, image):
    img = Image.objects.filter(name__exact=image.name)
    if img.exists():
        img = img.get()
        skyreg = get_create_skyreg(p_run, img)
        # check and add the many to many if not existent
        if not Image.objects.filter(
            id=img.id, run__id=p_run.id
        ).exists():
            img.run.add(p_run)

        return (img, skyreg, True)

    # at this stage, measurement parquet file is not created but
    # assume location
    img_folder_name = image.name.replace('.', '_')
    measurements_path = os.path.join(
        settings.PIPELINE_WORKING_DIR,
        'images',
        img_folder_name,
        'measurements.parquet'
        )
    img = Image(
        band_id=band_id,
        measurements_path=measurements_path
    )
    # set the attributes and save the image,
    # by selecting only valid (not hidden) attributes
    # FYI attributs and/or method starting with _ are hidden
    # and with __ can't be modified/called
    for fld in img._meta.get_fields():
        if getattr(fld, 'attname', None) and (
            getattr(image, fld.attname, None) is not None
        ):
            setattr(img, fld.attname, getattr(image, fld.attname))

    # get create the sky region and associate with image
    skyreg = get_create_skyreg(p_run, img)
    img.skyreg = skyreg

    img.rms_median, img.rms_min, img.rms_max = get_rms_noise_image_values(
        img.noise_path
    )

    img.save()
    img.run.add(p_run)

    return (img, skyreg, False)


def get_create_p_run(name, path, comment='', user=None):
    '''
    get or create a pipeline run in db, return the run django object and
    a flag True/False if has been created or already exists
    '''
    p_run = Run.objects.filter(name__exact=name)
    if p_run:
        return p_run.get(), True

    p_run = Run(name=name, comment=comment, path=path)
    if user:
        p_run.user = user
    p_run.save()

    return p_run, False


def prep_skysrc_df(image, perc_error, ini_df=False):
    '''
    initiliase the source dataframe to use in association logic by
    reading the measurement parquet file and creating columns
    inputs
    image: django image model
    ini_df: flag to initialise source id depending if inital df or not
    '''
    cols = [
    'id',
    'ra',
    'uncertainty_ew',
    'weight_ew',
    'dec',
    'uncertainty_ns',
    'weight_ns',
    'flux_int',
    'flux_int_err',
    'flux_peak',
    'flux_peak_err',
    'forced',
    'compactness',
    'has_siblings',
    'snr'
    ]

    df = pd.read_parquet(image.measurements_path, columns=cols)
    df['image'] = image.name
    df['datetime'] = image.datetime
    # these are the first 'sources'
    df['source'] = df.index + 1 if ini_df else -1
    df['ra_source'] = df['ra']
    df['dec_source'] = df['dec']
    df['d2d'] = 0.
    df['dr'] = 0.
    df['related'] = None
    logger.info('Correcting flux errors with config error setting...')
    for col in ['flux_int', 'flux_peak']:
        df[f'{col}_err'] = np.hypot(
            df[f'{col}_err'].values, perc_error * df[col].values
        )

    return df


def get_or_append_list(obj_in, elem):
    '''
    return a list with elem in it, if obj_in is list append to it
    '''
    if isinstance(obj_in, list):
        out = obj_in
        out.append(elem)
        return out

    return [elem]


def cross_join(left, right):
    return (
        left.assign(key=1)
        .merge(right.assign(key=1), on='key')
        .drop('key', axis=1)
    )


def get_eta_metric(grp: pd.DataFrame) -> pd.Series:
    '''
    Calculates the eta variability metric of a source.
    Works on the grouped by dataframe using the fluxes
    of the associated measurements.
    '''
    n_meas = grp['id'].count()
    if n_meas == 1:
        return pd.Series({'eta_int': 0., 'eta_peak': 0.})

    d = {}
    for suffix in ['int', 'peak']:
        weights = 1. / grp[f'flux_{suffix}_err'].values**2
        fluxes = grp[f'flux_{suffix}'].values
        d[f'eta_{suffix}'] = n_meas / (n_meas - 1) * (
            (weights * fluxes**2).mean() - (
                (weights * fluxes).mean()**2 / weights.mean()
            )
        )
    return pd.Series(d)


def aggr_based_on_selection(grp: pd.DataFrame) -> pd.Series:
    '''
    Performs aggreagtion based on the result of a selection
    '''
    n_meas_forced = grp['forced'].sum()
    d = {}
    if n_meas_forced > 0:
        non_forced_sel = grp['forced'] != True
        d['wavg_ra'] = (
            grp.loc[non_forced_sel, 'interim_ew'].sum() /
            grp.loc[non_forced_sel, 'weight_ew'].sum()
        )
        d['wavg_dec'] = (
            grp.loc[non_forced_sel, 'interim_ns'].sum() /
            grp.loc[non_forced_sel, 'weight_ns'].sum()
        )
        d['avg_compactness'] = grp.loc[
            non_forced_sel, 'compactness'
        ].mean()
        d['min_snr'] = grp.loc[
            non_forced_sel, 'snr'
        ].min()
        d['max_snr'] = grp.loc[
            non_forced_sel, 'snr'
        ].max()
    else:
        d['wavg_ra'] = grp['interim_ew'].sum() / grp['weight_ew'].sum()
        d['wavg_dec'] = grp['interim_ns'].sum() / grp['weight_ns'].sum()
        d['avg_compactness'] = grp['compactness'].mean()
        d['min_snr'] = grp['snr'].min()
        d['max_snr'] = grp['snr'].max()
    return pd.Series(d)


def parallel_groupby(df: dd.DataFrame) -> dd.DataFrame:
    '''
    Performs calculations on the unique sources to get the
    lightcurve properties. Works on the grouped by source
    dataframe.
    '''
    # create list of output columnd and dicts with aggregations and rename maps
    collect_set = dd.Aggregation(
        name='collect_set',
        chunk=lambda s: s.apply(lambda x: x if isinstance(x, list) else []),
        agg=lambda s0: s0.apply(
            lambda chunks: list(set(chain.from_iterable(chunks)))
        )
    )
    aggregations = {
        'image': collect_list,
        'forced': 'sum',
        'id': 'count',
        'has_siblings': 'sum',
        'weight_ew': 'sum',
        'weight_ns': 'sum',
        'flux_int': ['mean', 'std'],
        'flux_peak': ['mean', 'std', 'max'],
        'related': collect_set
    }
    renaming = {
        'image_collect_list': 'img_list',
        'forced_sum': 'n_meas_forced',
        'id_count': 'n_meas',
        'has_siblings_sum': 'n_sibl',
        'flux_int_mean': 'avg_flux_int',
        'flux_peak_mean': 'avg_flux_peak',
        'flux_peak_max': 'max_flux_peak',
        'related_collect_set': 'related_list'
    }

    groupby = df.groupby('source')
    out = groupby.agg(aggregations)
    # collapse columns Multindex
    out.columns = ['_'.join(col) for col in out.columns.to_flat_index()]
    # do some other column calcs
    out['wavg_uncertainty_ew'] = 1. / np.sqrt(out['weight_ew_sum'])
    out['wavg_uncertainty_ns'] = 1. / np.sqrt(out['weight_ns_sum'])
    out['v_int'] = out['flux_int_std'] / out['flux_int_mean']
    out['v_peak'] = out['flux_peak_std'] / out['flux_peak_mean']

    # do complex aggregations using groupby-apply
    col_dtype = {
        'wavg_ra': 'f',
        'wavg_dec': 'f',
        'avg_compactness': 'f',
        'min_snr': 'f',
        'max_snr': 'f'
    }
    out = (
        out.merge(
            groupby.apply(aggr_based_on_selection, meta=col_dtype),
            left_index=True,
            right_index=True
        )
        .merge(
            groupby.apply(
                get_eta_metric,
                meta={'eta_int': 'f', 'eta_peak': 'f'}
            ),
            left_index=True,
            right_index=True
        )
    )

    out = out.rename(columns=renaming)
    out['n_meas_sel'] = out['n_meas'] - out['n_meas_forced']
    out['n_rel'] = out['related_list'].apply(len, meta=int)

    # select only columns we need
    out_cols = [
        'img_list', 'n_meas_forced', 'n_meas', 'n_meas_sel', 'n_sibl',
        'wavg_ra', 'wavg_dec', 'avg_compactness', 'min_snr', 'max_snr',
        'wavg_uncertainty_ew', 'wavg_uncertainty_ns', 'avg_flux_int',
        'avg_flux_peak', 'max_flux_peak', 'v_int', 'v_peak', 'eta_int',
        'eta_peak', 'related_list', 'n_rel'
    ]
    out = out[out_cols]

    return out.persist()


def parallel_groupby_coord(df: dd.core.DataFrame) -> dd.core.DataFrame:
    cols = [
        'source', 'image', 'interim_ew', 'weight_ew', 'interim_ns', 'weight_ns'
    ]
    cols_to_sum = ['interim_ew', 'weight_ew', 'interim_ns', 'weight_ns']

    groups = df[cols].groupby('source')
    out = groups[cols_to_sum].agg('sum')
    out['wavg_ra'] = out['interim_ew'] / out['weight_ew']
    out['wavg_dec'] = out['interim_ns'] / out['weight_ns']
    out = out.drop(cols_to_sum, axis=1)
    out['img_list'] = groups['image'].agg(collect_list)

    return out.persist()


def get_source_models(row, pipeline_run=None):
    '''
    Fetches the source model (for DB injecting).
    '''
    name = f"src_{deg2hms(row['wavg_ra'])}{deg2dms(row['wavg_dec'])}"
    src = Source()
    src.run = pipeline_run
    src.name = name
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


def get_rms_noise_image_values(rms_path):
    '''
    open the RMS noise FITS file and compute the median, max and min
    rms values to be added to the image model and then used in the
    calculations
    '''
    logger.debug('Extracting Image RMS values from Noise file...')
    med_val = min_val = max_val = 0.
    try:
        with fits.open(rms_path) as f:
            data = f[0].data
            data = data[np.logical_not(np.isnan(data))]
            data = data[data != 0]
            med_val = np.median(data) * 1e+3
            min_val = np.min(data) * 1e+3
            max_val = np.max(data) * 1e+3
            del data
    except Exception:
        raise IOError(f'Could not read this RMS FITS file: {rms_path}')

    return med_val, min_val, max_val


def get_image_list_diff(row):
    out = list(filter(
        lambda arg: arg not in row['img_list'], row['skyreg_img_list']
    ))

    # set empty list to -1
    if not out:
        out = -1

    return out


def get_src_skyregion_merged_df(sources_df: dd.core.DataFrame,
    p_run: Run) -> dd.core.DataFrame:
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
    # get all the skyregions and related images
    cols = [
        'id', 'name', 'measurements_path', 'path', 'noise_path',
        'beam_bmaj', 'beam_bmin', 'beam_bpa', 'background_path',
        'datetime', 'skyreg__id'
    ]

    skyreg_cols = [
        'id', 'centre_ra', 'centre_dec', 'xtr_radius'
    ]

    images_df = pd.DataFrame(list(
        Image.objects.filter(run=p_run)
        .select_related('skyreg')
        .order_by('datetime')
        .values(*tuple(cols))
    )).explode('skyreg__id')

    skyreg_df = pd.DataFrame(list(
        SkyRegion.objects.filter(run=p_run)
        .values(*tuple(skyreg_cols))
    ))

    skyreg_df = skyreg_df.join(
        pd.DataFrame(
            images_df.groupby('skyreg__id')
            .apply(lambda x: x['name'].values.tolist())
        ).rename(columns={0:'skyreg_img_list'}),
        on='id'
    )

    # calculate some metrics on sources
    # compute only some necessary metrics in the groupby
    srcs_df = parallel_groupby_coord(sources_df)

    # create dataframe with all skyregions and sources combinations
    src_skyrg_df = cross_join(srcs_df.reset_index(), skyreg_df)
    src_skyrg_df['sep'] = np.rad2deg(
        on_sky_sep(
            np.deg2rad(src_skyrg_df['wavg_ra'].values),
            np.deg2rad(src_skyrg_df['centre_ra'].values),
            np.deg2rad(src_skyrg_df['wavg_dec'].values),
            np.deg2rad(src_skyrg_df['centre_dec'].values),
        )
    )

    # select rows where separation is less than sky region radius
    # drop not more useful columns and groupby source id
    # compute list of images
    src_skyrg_df = (
        src_skyrg_df.loc[
            src_skyrg_df['sep'] < src_skyrg_df['xtr_radius'],
            ['source', 'skyreg_img_list']
        ]
        .groupby('source')
        .agg('sum') # sum because we need to preserve order
    )

    # merge into main df and compare the images
    srcs_df = srcs_df.merge(
        src_skyrg_df, left_index=True, right_index=True
    )
    del src_skyrg_df

    srcs_df['img_diff'] = srcs_df[['img_list', 'skyreg_img_list']].apply(
        get_image_list_diff, axis=1, meta=object
    )

    srcs_df = srcs_df.loc[
        srcs_df['img_diff'] != -1
    ]
    return srcs_df.persist()
