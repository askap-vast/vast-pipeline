import os
import logging
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
import dask.dataframe as dd
from django.conf import settings

from psutil import cpu_count
from itertools import chain

from pipeline.utils.utils import deg2hms, deg2dms, eq_to_cart, StopWatch
from ..models import Band, Image, Measurement, Run, Source, SkyRegion
from pipeline.image.utils import on_sky_sep


logger = logging.getLogger(__name__)


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
    img_folder_name = '_'.join([
        image.name.replace('.', '_'),
        image.datetime.strftime('%Y-%m-%dT%H_%M_%S%z')
    ])
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
    p_run = Run.objects.filter(name__exact=name)
    if p_run:
        return p_run.get(), True

    p_run = Run(name=name, comment=comment, path=path)
    if user:
        p_run.user = user
    p_run.save()

    return p_run, False


def remove_duplicate_measurements(
    sources_df, dup_lim=Angle(2.5 * u.arcsec), ini_df=False
):
    """
    Remove duplicate sources from dataframe
    """
    logger.debug('Cleaning duplicate sources from epoch...')
    logger.debug('Using crossmatch radius of %.2f arcsec.', dup_lim.arcsec)
    min_source = sources_df['source'].min()

    # sort by the distance from the image centre so we know
    # that the first source is always the one to keep
    sources_df = sources_df.sort_values(by='dist_from_centre')

    sources_sc = SkyCoord(
        sources_df['ra'],
        sources_df['dec'],
        unit=(u.deg, u.deg)
    )

    # perform search around sky to get all self matches
    idxc, idxcatalog, d2d_around, _ = sources_sc.search_around_sky(
        sources_sc, dup_lim
    )

    # create df from results
    results = pd.DataFrame(data={'source_id': idxc, 'match_id': idxcatalog})
    # create a pair column defining each pair ith index
    results['pair'] = results.apply(tuple, 1).apply(sorted).apply(tuple)
    # Drop the duplicate pairs (pairs are sorted so this works)
    results = results.drop_duplicates('pair')
    # No longer need pair
    results = results.drop('pair', axis=1)
    # We're only interested in the sources which have matches.
    results = results.loc[
        results.duplicated('source_id', keep=False)
    ].sort_values(by='source_id')
    # Drop all self matches and we are left with those to drop
    # in the match id column.
    to_drop = results.loc[
        results['source_id'] != results['match_id']
    ]['match_id']
    # Get the index values from the ith values
    to_drop_indexes = sources_df.iloc[to_drop].index.values
    logger.debug(
        "Dropping %i duplicate measurements.", to_drop_indexes.shape[0]
    )
    # Drop them from sources
    sources_df = sources_df.drop(to_drop_indexes).sort_values(
        by='ra'
    )

    # reset the source_df index
    sources_df = sources_df.reset_index(drop=True)

    # Reset the source number
    if ini_df:
        sources_df['source'] = sources_df.index + 1

    del results

    return sources_df


def _load_measurements(image, cols, start_id=0, ini_df=False):
    image_centre = SkyCoord(
        image.ra,
        image.dec,
        unit=(u.deg, u.deg)
    )

    df = pd.read_parquet(image.measurements_path, columns=cols)
    df['image'] = image.name
    df['datetime'] = image.datetime
    # these are the first 'sources'
    df['source'] = df.index + start_id + 1 if ini_df else -1
    df['ra_source'] = df['ra']
    df['dec_source'] = df['dec']
    df['d2d'] = 0.
    df['dr'] = 0.
    df['related'] = None

    sources_sc = SkyCoord(
        df['ra'],
        df['dec'],
        unit=(u.deg, u.deg)
    )

    seps = sources_sc.separation(image_centre).degree
    df['dist_from_centre'] = seps

    del sources_sc
    del seps

    return df


def prep_skysrc_df(images, perc_error, duplicate_limit, ini_df=False):
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

    df = _load_measurements(images[0], cols, ini_df=ini_df)

    if len(images) > 1:
        for img in images[1:]:
            df = df.append(
                _load_measurements(img, cols, df.source.max(), ini_df=ini_df),
                ignore_index=True
            )

        df = remove_duplicate_measurements(
            df, dup_lim=duplicate_limit, ini_df=ini_df
        )

    df = df.drop('dist_from_centre', axis=1)

    if perc_error != 0.0:
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


def get_eta_metric(row, df, peak=False):
    '''
    Calculates the eta variability metric of a source.
    Works on the grouped by dataframe using the fluxes
    of the assoicated measurements.
    '''
    if row['n_meas'] == 1:
        return 0.

    suffix = 'peak' if peak else 'int'
    weights = 1. / df[f'flux_{suffix}_err'].values**2
    fluxes = df[f'flux_{suffix}'].values
    eta = (row['n_meas'] / (row['n_meas']-1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta


def groupby_funcs(df):
    '''
    Performs calculations on the unique sources to get the
    lightcurve properties. Works on the grouped by source
    dataframe.
    '''
    # calculated average ra, dec, fluxes and metrics
    d = {}
    d['img_list'] = df['image'].values.tolist()
    d['n_meas_forced'] = df['forced'].sum()
    d['n_meas'] = df['id'].count()
    d['n_meas_sel'] = d['n_meas'] - d['n_meas_forced']
    d['n_sibl'] = df['has_siblings'].sum()
    if d['n_meas_forced'] > 0:
        non_forced_sel = df['forced'] != True
        d['wavg_ra'] = (
            df.loc[non_forced_sel, 'interim_ew'].sum() /
            df.loc[non_forced_sel, 'weight_ew'].sum()
        )
        d['wavg_dec'] = (
            df.loc[non_forced_sel, 'interim_ns'].sum() /
            df.loc[non_forced_sel, 'weight_ns'].sum()
        )
        d['avg_compactness'] = df.loc[
            non_forced_sel, 'compactness'
        ].mean()
        d['min_snr'] = df.loc[
            non_forced_sel, 'snr'
        ].min()
        d['max_snr'] = df.loc[
            non_forced_sel, 'snr'
        ].max()

    else:
        d['wavg_ra'] = df['interim_ew'].sum() / df['weight_ew'].sum()
        d['wavg_dec'] = df['interim_ns'].sum() / df['weight_ns'].sum()
        d['avg_compactness'] = df['compactness'].mean()
        d['min_snr'] = df['snr'].min()
        d['max_snr'] = df['snr'].max()

    d['wavg_uncertainty_ew'] = 1. / np.sqrt(df['weight_ew'].sum())
    d['wavg_uncertainty_ns'] = 1. / np.sqrt(df['weight_ns'].sum())
    for col in ['avg_flux_int', 'avg_flux_peak']:
        d[col] = df[col.split('_', 1)[1]].mean()
    d['max_flux_peak'] = df['flux_peak'].values.max()

    for col in ['flux_int', 'flux_peak']:
        d[f'{col}_sq'] = (df[col]**2).mean()
    d['v_int'] = df['flux_int'].std() / df['flux_int'].mean()
    d['v_peak'] = df['flux_peak'].std() / df['flux_peak'].mean()
    d['eta_int'] = get_eta_metric(d, df)
    d['eta_peak'] = get_eta_metric(d, df, peak=True)
    # remove not used cols
    for col in ['flux_int_sq', 'flux_peak_sq']:
        d.pop(col)

    # get unique related sources
    list_uniq_related = list(set(
        chain.from_iterable(
            lst for lst in df['related'] if isinstance(lst, list)
        )
    ))
    d['related_list'] = list_uniq_related if list_uniq_related else -1

    return pd.Series(d)


def parallel_groupby(df):
    col_dtype = {
        'img_list': 'O',
        'n_meas_forced': 'i',
        'n_meas': 'i',
        'n_meas_sel': 'i',
        'n_sibl': 'i',
        'wavg_ra': 'f',
        'wavg_dec': 'f',
        'avg_compactness': 'f',
        'min_snr': 'f',
        'max_snr': 'f',
        'wavg_uncertainty_ew': 'f',
        'wavg_uncertainty_ns': 'f',
        'avg_flux_int': 'f',
        'avg_flux_peak': 'f',
        'max_flux_peak': 'f',
        'v_int': 'f',
        'v_peak': 'f',
        'eta_int': 'f',
        'eta_peak': 'f',
        'related_list': 'O'
    }
    n_cpu = cpu_count() - 1
    out = dd.from_pandas(df, n_cpu)
    out = (
        out.groupby('source')
        .apply(
            groupby_funcs,
            meta=col_dtype
        )
        .compute(num_workers=n_cpu, scheduler='processes')
    )
    out['n_rel'] = out['related_list'].apply(lambda x: 0 if x == -1 else len(x))
    return out


def calc_ave_coord(grp):
    d = {}
    d['img_list'] = grp['image'].values.tolist()
    d['epoch_list'] = grp['epoch'].values.tolist()
    d['wavg_ra'] = grp['interim_ew'].sum() / grp['weight_ew'].sum()
    d['wavg_dec'] = grp['interim_ns'].sum() / grp['weight_ns'].sum()
    return pd.Series(d)


def parallel_groupby_coord(df):
    col_dtype = {
        'img_list': 'O',
        'epoch_list': 'O',
        'wavg_ra': 'f',
        'wavg_dec': 'f',
    }
    n_cpu = cpu_count() - 1
    out = dd.from_pandas(df, n_cpu)
    out = (
        out.groupby('source')
        .apply(calc_ave_coord, meta=col_dtype)
        .compute(num_workers=n_cpu, scheduler='processes')
    )
    return out


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
    out = list(filter(lambda arg: arg not in row['img_list'], row['skyreg_img_list']))

    # set empty list to -1
    if not out:
        out = -1

    return out


def get_names_and_epochs(grp):
    d = {}
    d['skyreg_img_epoch_list'] = [[[x,],y] for x,y in zip(
        grp['name'].values.tolist(),
        grp['epoch'].values.tolist(),
    )]

    return pd.Series(d)


def get_src_skyregion_merged_df(sources_df, images_df, skyreg_df, p_run):
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
    logger.info("Creating ideal source coverage df...")

    merged_timer = StopWatch()

    skyreg_df = skyreg_df.drop(
        ['x', 'y', 'z', 'width_ra', 'width_dec'], axis=1
    )

    images_df['name'] = images_df['image'].apply(
        lambda x: x.name
    )

    skyreg_df = skyreg_df.join(
        pd.DataFrame(
            images_df.groupby('skyreg_id').apply(
                get_names_and_epochs
            )
        ),
        on='id'
    )

    sources_df = sources_df.sort_values(by='datetime')
    # calculate some metrics on sources
    # compute only some necessary metrics in the groupby
    timer = StopWatch()
    srcs_df = parallel_groupby_coord(sources_df)
    logger.debug('Groupby-apply time: %.2f seconds', timer.reset())

    del sources_df

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
    src_skyrg_df = src_skyrg_df.loc[
        src_skyrg_df.sep < src_skyrg_df.xtr_radius,
        ['source', 'skyreg_img_epoch_list', 'sep']
    ].explode('skyreg_img_epoch_list')

    src_skyrg_df[
        ['skyreg_img_list', 'skyreg_epoch']
    ] = pd.DataFrame(
        src_skyrg_df['skyreg_img_epoch_list'].tolist(),
        index=src_skyrg_df.index
    )

    src_skyrg_df = src_skyrg_df.drop('skyreg_img_epoch_list', axis=1)

    src_skyrg_df = (
        src_skyrg_df.sort_values(
            ['source', 'skyreg_epoch', 'sep']
        )
        .drop_duplicates(['source', 'skyreg_epoch'])
        .drop(
            ['sep', 'skyreg_epoch'],
            axis=1
        )
        .groupby('source')
        .agg('sum') # sum because we need to preserve order
    )

    # merge into main df and compare the images
    srcs_df = srcs_df.merge(
        src_skyrg_df, left_index=True, right_index=True
    )

    del src_skyrg_df

    srcs_df['img_diff'] = srcs_df[['img_list', 'skyreg_img_list']].apply(
        get_image_list_diff, axis=1
    )

    srcs_df = srcs_df.loc[
        srcs_df['img_diff'] != -1
    ]

    logger.info(
        'Ideal source coverage time: %.2f seconds', merged_timer.reset()
    )

    return srcs_df


def _get_skyregion_relations(row, coords, ids):
    '''
    For each sky region row a list is returned that
    contains the ids of other sky regions that overlap
    with the row sky region (including itself).
    '''
    target = SkyCoord(
        row['centre_ra'],
        row['centre_dec'],
        unit=(u.deg, u.deg)
    )

    seps = target.separation(coords)

    # place a slight buffer on the radius to make sure
    # any neighbouring fields are caught
    mask = seps <= row['xtr_radius'] * 1.1 * u.deg

    related_ids = ids[mask].to_list()

    return related_ids


def group_skyregions(df):
    '''
    Logic to group sky regions into overlapping groups.
    Returns a dataframe containing the sky region id as
    the index and a column containing a list of the
    sky region group number it belongs to.
    '''
    sr_coords = SkyCoord(
        df['centre_ra'],
        df['centre_dec'],
        unit=(u.deg, u.deg)
    )

    df = df.set_index('id')

    results = df.apply(
        _get_skyregion_relations,
        args=(sr_coords, df.index),
        axis=1
    )

    skyreg_groups = {}
    # keep track of all checked ids
    master_done = []

    for skyreg_id, neighbours in results.iteritems():

        if skyreg_id not in master_done:
            # define a local done list for the sky region group
            sr_done = []
            master_done.append(skyreg_id)
            sr_done.append(skyreg_id)
            skyreg_group = len(skyreg_groups) + 1
            skyreg_groups[skyreg_group] = list(neighbours)

            while sorted(sr_done) != sorted(skyreg_groups[skyreg_group]):
                for other_skyreg_id in skyreg_groups[skyreg_group]:
                    if other_skyreg_id not in sr_done:
                        sr_done.append(other_skyreg_id)
                        new_vals = results.loc[other_skyreg_id]
                        for k in new_vals:
                            if k not in skyreg_groups[skyreg_group]:
                                skyreg_groups[skyreg_group].append(k)

            # Reached the end of the group so append all to the master
            # done list
            for j in skyreg_groups[skyreg_group]:
                master_done.append(j)
        else:
            # continue if already placed in group
            continue

    # flip the dictionary around
    skyreg_group_ids = {}
    for i in skyreg_groups:
        for j in skyreg_groups[i]:
            skyreg_group_ids[j]=i

    skyreg_group_ids = pd.DataFrame.from_dict(
        skyreg_group_ids, orient='index'
    ).rename(columns={0: 'skyreg_group'})

    return skyreg_group_ids


def get_parallel_assoc_image_df(images, skyregion_groups):

    skyreg_ids = [i.skyreg_id for i in images]

    images_df = pd.DataFrame({
        'image': images,
        'skyreg_id': skyreg_ids,
    })

    images_df = images_df.merge(
        skyregion_groups,
        how='left',
        left_on='skyreg_id',
        right_index=True
    )

    return images_df
