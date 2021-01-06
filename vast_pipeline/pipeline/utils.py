import os
import logging
import glob
import vaex
import shutil
import numpy as np
import pandas as pd
import astropy.units as u
import dask.dataframe as dd

from typing import List, Optional, Dict
from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle
from astropy.io import fits
from django.conf import settings
from psutil import cpu_count
from itertools import chain, combinations

from vast_pipeline.utils.utils import (
    deg2hms, deg2dms, eq_to_cart, StopWatch,
    optimize_ints, optimize_floats
)
from vast_pipeline.models import (
    Band, Image, Measurement, Run, Source, SkyRegion
)
from vast_pipeline.image.utils import on_sky_sep


logger = logging.getLogger(__name__)


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
        # Add background path if not originally provided
        if image.background_path and not img.background_path:
            img.background_path = image.background_path
            img.save()
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


def get_create_p_run(name, path, description=None, user=None):
    '''
    get or create a pipeline run in db, return the run django object and
    a flag True/False if has been created or already exists
    '''
    p_run = Run.objects.filter(name__exact=name)
    if p_run:
        return p_run.get(), True

    description = "" if description is None else description
    p_run = Run(name=name, description=description, path=path)
    if user:
        p_run.user = user
    p_run.save()

    return p_run, False


def remove_duplicate_measurements(
    sources_df: pd.DataFrame,
    dup_lim: Optional[Angle] = None,
    ini_df: bool = False
) -> pd.DataFrame:
    """
    Remove perceived duplicate sources from a dataframe of loaded
    measurements. Duplicates are determined by their separation and whether
    this distances is within the 'dup_lim'.

    Parameters
    ----------
    source_df : pd.DataFrame
        The loaded measurements from two or more images.
    dup_lim : Angle, optional
        The separation limit of when a source is considered a duplicate.
        Defaults to None in which case 2.5 arcsec is used (usual ASKAP
        pixel size).
    ini_df : bool, optional
        Boolean to indicate whether these sources are part of the initial
        source list creation for association. If 'True' the source ids are
        reset ready for the first iteration. Defaults to 'False'.

    Returns
    -------
    sources_df : pd.DataFrame
        The input sources_df with duplicate sources removed.
    """
    logger.debug('Cleaning duplicate sources from epoch...')

    if dup_lim is None:
        dup_lim = Angle(2.5 * u.arcsec)

    logger.debug(
        'Using duplicate crossmatch radius of %.2f arcsec.', dup_lim.arcsec
    )

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
    results = pd.DataFrame(
        data={
            'source_id': idxc,
            'match_id': idxcatalog,
            'source_image': sources_df.iloc[idxc]['image'].tolist(),
            'match_image': sources_df.iloc[idxcatalog]['image'].tolist()
        }
    )

    # Drop those that are matched from the same image
    matching_image_mask = (
        results['source_image'] != results['match_image']
    )

    results = (
        results.loc[matching_image_mask]
        .drop(['source_image', 'match_image'], axis=1)
    )

    # create a pair column defining each pair ith index
    results['pair'] = results.apply(tuple, 1).apply(sorted).apply(tuple)
    # Drop the duplicate pairs (pairs are sorted so this works)
    results = results.drop_duplicates('pair')
    # No longer need pair
    results = results.drop('pair', axis=1)
    # Drop all self matches and we are left with those to drop
    # in the match id column.
    to_drop = results.loc[
        results['source_id'] != results['match_id'],
        'match_id'
    ]
    # Get the index values from the ith values
    to_drop_indexes = sources_df.iloc[to_drop].index.values
    logger.debug(
        "Dropping %i duplicate measurements.", to_drop_indexes.shape[0]
    )
    # Drop them from sources
    sources_df = sources_df.drop(to_drop_indexes).sort_values(by='ra')

    # reset the source_df index
    sources_df = sources_df.reset_index(drop=True)

    # Reset the source number
    if ini_df:
        sources_df['source'] = sources_df.index + 1

    del results

    return sources_df


def _load_measurements(
    image: Image,
    cols: List[str],
    start_id: int = 0,
    ini_df: bool = False
) -> pd.DataFrame:
    """
    Load the measurements for an image from the parquet file.

    Parameters
    ----------
    image : Image
        The object representing the image for which to load the measurements.
    cols : List[str]
        The columns to load.
    start_id : int, optional
        The number to start from when setting the source ids (when 'ini_df' is
        'True'). Defaults to 0.
    ini_df : bool, optional
        Boolean to indicate whether these sources are part of the initial
        source list creation for association. If 'True' the source ids are
        reset ready for the first iteration. Defaults to 'False'.

    Returns
    -------
    df : pd.DataFrame
        The measurements of the image with some extra values set ready for
        assoication.
    """
    image_centre = SkyCoord(
        image.ra,
        image.dec,
        unit=(u.deg, u.deg)
    )

    df = pd.read_parquet(image.measurements_path, columns=cols)
    df['image'] = image.name
    df['datetime'] = image.datetime
    # these are the first 'sources' if ini_df is True.
    df['source'] = df.index + start_id + 1 if ini_df else -1
    df['ra_source'] = df['ra']
    df['dec_source'] = df['dec']
    df['d2d'] = 0.
    df['dr'] = 0.
    df['related'] = None

    sources_sc = SkyCoord(df['ra'], df['dec'], unit=(u.deg, u.deg))

    seps = sources_sc.separation(image_centre).degree
    df['dist_from_centre'] = seps

    del sources_sc
    del seps

    return df


def prep_skysrc_df(
    images: List[Image],
    perc_error: float = 0.,
    duplicate_limit: Optional[Angle] = None,
    ini_df: bool = False
):
    '''
    Initiliase the source dataframe to use in association logic by
    reading the measurement parquet file and creating columns. When epoch
    based assoication is used it will also remove duplicate measurements from
    the list of sources.

    Parameters
    ----------
    images : List[Image]
        A list holding the Image objects of the images to load measurements for.
    perc_error : float, optional
        A percentage flux error to apply to the flux errors of the
        measurements. Defaults to 0.
    duplicate_limit : Angle, optional
        The separation limit of when a source is considered a duplicate.
        Defaults to None in which case 2.5 arcsec is used in the
        'remove_duplicate_measurements' function (usual ASKAP pixel size).
    ini_df : bool, optional
        Boolean to indicate whether these sources are part of the initial
        source list creation for association. If 'True' the source ids are
        reset ready for the first iteration. Defaults to 'False'.

    Returns
    -------
    df : pd.DataFrame
        The measurements of the image(s) with some extra values set ready for
        assoication and duplicates removed if necessary.
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
        'flux_int_isl_ratio',
        'flux_peak',
        'flux_peak_err',
        'flux_peak_isl_ratio',
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


def add_new_one_to_many_relations(
    row: pd.Series, advanced: bool = False,
    source_ids: Optional[pd.DataFrame] = None
) -> List[int]:
    """
    This handles the relation information being created from the
    one_to_many functions in association.

    Parameters
    ----------
    row : pd.Series
        The relation information Series from the assoication dataframe. Only
        the columns ['related_skyc1', 'source_skyc1'] are required for advanced
        , these are instead called ['related', 'source'] for basic.
    advanced : bool, optional
        Whether advanced association is being used which changes the names
        of the columns involved.
    source_ids : int, optional
        A dataframe that contains the other ids to append to related for each
        original source.
        +----------------+--------+
        |   source_skyc1 | 0      |
        |----------------+--------|
        |            122 | [5542] |
        |            254 | [5543] |
        |            262 | [5544] |
        |            405 | [5545] |
        |            656 | [5546] |
        +----------------+--------+

    Returns
    -------
    out : List[int]
        The new related field for the source in question, containing the
        appended ids.
    """
    if source_ids is None:
        source_ids = pd.DataFrame()

    related_col = 'related_skyc1' if advanced else 'related'
    source_col = 'source_skyc1' if advanced else 'source'

    # this is the not_original case where the original source id is appended.
    if source_ids.empty:
        if isinstance(row[related_col], list):
            out = row[related_col]
            out.append(row[source_col])
        else:
            out = [row[source_col],]

    else:  # the original case to append all the new ids.
        source_ids = source_ids.loc[row[source_col]].iloc[0]
        if isinstance(row[related_col], list):
            out = row[related_col] + source_ids
        else:
            out = source_ids

    return out


def add_new_many_to_one_relations(row: pd.Series) -> List[int]:
    """
    This handles the relation information being created from the
    many_to_one function in advanced association.
    It is a lot simpler than the one_to_many case as it purely just adds
    the new relations to the relation column, taking into account if it is
    already a list of relations or not (i.e. no previous relations).

    Parameters
    ----------
    row : pd.Series
        The relation information Series from the assoication dataframe. Only
        the columns ['related_skyc1', 'new_relations'] are required.

    Returns
    -------
    out : List[int]
        The new related field for the source in question, containing the
        appended ids.
    """
    if isinstance(row['related_skyc1'], list):
        out = row['related_skyc1'].copy() + row['new_relations']
    else:
        out = row['new_relations'].copy()

    return out


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
    for col in ['max_flux_peak', 'max_flux_int']:
        d[col] = df[col.split('_', 1)[1]].max()
    for col in ['min_flux_peak', 'min_flux_int']:
        d[col] = df[col.split('_', 1)[1]].min()
    for col in ['min_flux_peak_isl_ratio', 'min_flux_int_isl_ratio']:
        d[col] = df[col.split('_', 1)[1]].min()

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

    return pd.Series(d).fillna(value={"v_int": 0.0, "v_peak": 0.0})


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
        'max_flux_int': 'f',
        'min_flux_peak': 'f',
        'min_flux_int': 'f',
        'min_flux_peak_isl_ratio': 'f',
        'min_flux_int_isl_ratio': 'f',
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
    grp = grp.sort_values(by='datetime')
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
    out = list(
        filter(lambda arg: arg not in row['img_list'], row['skyreg_img_list'])
    )

    # set empty list to -1
    if not out:
        return -1

    # Check that an epoch has not already been seen (just not in the 'ideal' image)
    out_epochs = [
        row['skyreg_epoch'][pair[0]] for pair in enumerate(
            row['skyreg_img_list']
        ) if pair[1] in out
    ]

    out = [
        out[pair[0]] for pair in enumerate(
            out_epochs
        ) if pair[1] not in row['epoch_list']
    ]

    if not out:
        out = -1

    return out


def get_names_and_epochs(grp):
    d = {}
    d['skyreg_img_epoch_list'] = [[[x,], y, z] for x,y,z in zip(
        grp['name'].values.tolist(),
        grp['epoch'].values.tolist(),
        grp['datetime'].values.tolist()
    )]

    return pd.Series(d)


def check_primary_image(row: pd.Series) -> bool:
    """
    Checks whether the primary image of the ideal source
    dataframe is in the image list for the source.

    Parameters
    ----------
    row : pd.Series
        input dataframe row, with columns ['primary']
        and ['img_list'].

    Returns
    -------
    bool : bool
        True if primary in image list else False.
    """
    return row['primary'] in row['img_list']


def get_src_skyregion_merged_df(
    sources_df: pd.DataFrame, images_df: pd.DataFrame, skyreg_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Analyses the current sources_df to determine what the 'ideal coverage'
    for each source should be. In other words, what images is the source
    missing in when it should have been seen.

    Parameters
    ----------
    sources_df : pd.DataFrame
        The output of the assoication step containing the
        measurements assoicated into sources.
    images_df : pd.DataFrame
        Contains the images of the pipeline run. I.e. all image
        objects for the run loaded into a dataframe.
    skyreg_df : pd.DataFrame
        Contains the sky regions of the pipeline run. I.e. all
        sky region objects for the run loaded into a dataframe.

    Returns
    -------
    srcs_df : pd.DataFrame
        DataFrame containing missing image information. Output format:
        +----------+----------------------------------+-----------+------------+
        |   source | img_list                         |   wavg_ra |   wavg_dec |
        |----------+----------------------------------+-----------+------------+
        |      278 | ['VAST_0127-73A.EPOCH01.I.fits'] |  22.2929  |   -71.8717 |
        |      702 | ['VAST_0127-73A.EPOCH01.I.fits'] |  28.8125  |   -69.3547 |
        |      844 | ['VAST_0127-73A.EPOCH01.I.fits'] |  17.3152  |   -72.346  |
        |      934 | ['VAST_0127-73A.EPOCH01.I.fits'] |   9.75754 |   -72.9629 |
        |     1290 | ['VAST_0127-73A.EPOCH01.I.fits'] |  20.8455  |   -76.8269 |
        +----------+----------------------------------+-----------+------------+
        ------------------------------------------------------------------+
         skyreg_img_list                                                  |
        ------------------------------------------------------------------+
         ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
         ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
         ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
         ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
         ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
        ------------------------------------------------------------------+
        ----------------------------------+------------------------------+
         img_diff                         | primary                      |
        ----------------------------------+------------------------------+
         ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
         ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
         ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
         ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
         ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
        ----------------------------------+------------------------------+
        ------------------------------+--------------+
         detection                    | in_primary   |
        ------------------------------+--------------|
         VAST_0127-73A.EPOCH01.I.fits | True         |
         VAST_0127-73A.EPOCH01.I.fits | True         |
         VAST_0127-73A.EPOCH01.I.fits | True         |
         VAST_0127-73A.EPOCH01.I.fits | True         |
         VAST_0127-73A.EPOCH01.I.fits | True         |
        ------------------------------+--------------+
    """
    logger.info("Creating ideal source coverage df...")

    merged_timer = StopWatch()

    skyreg_df = skyreg_df.drop(
        ['x', 'y', 'z', 'width_ra', 'width_dec'], axis=1
    )

    images_df['name'] = images_df['image_dj'].apply(
        lambda x: x.name
    )
    images_df['datetime'] = images_df['image_dj'].apply(
        lambda x: x.datetime
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
    src_skyrg_df = cross_join(
        srcs_df.drop(['epoch_list', 'img_list'], axis=1).reset_index(),
        skyreg_df.drop('skyreg_img_epoch_list', axis=1)
    )

    skyreg_df = skyreg_df.drop(
        ['centre_ra', 'centre_dec', 'xtr_radius'],
        axis=1
    ).set_index('id')

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
            src_skyrg_df.sep < src_skyrg_df.xtr_radius,
            ['source', 'id', 'sep']
        ].merge(skyreg_df, left_on='id', right_index=True)
        .drop('id', axis=1)
        .explode('skyreg_img_epoch_list')
    )

    del skyreg_df

    src_skyrg_df[
        ['skyreg_img_list', 'skyreg_epoch', 'skyreg_datetime']
    ] = pd.DataFrame(
        src_skyrg_df['skyreg_img_epoch_list'].tolist(),
        index=src_skyrg_df.index
    )

    src_skyrg_df = src_skyrg_df.drop('skyreg_img_epoch_list', axis=1)

    src_skyrg_df = (
        src_skyrg_df.sort_values(
            ['source', 'sep']
        )
        .drop_duplicates(['source', 'skyreg_epoch'])
        .sort_values(by='skyreg_datetime')
        .drop(
            ['sep', 'skyreg_datetime'],
            axis=1
        )
    )
    # annoyingly epoch needs to be not a list to drop duplicates
    # but then we need to sum the epochs into a list
    src_skyrg_df['skyreg_epoch'] = src_skyrg_df['skyreg_epoch'].apply(
        lambda x: [x,]
    )

    src_skyrg_df = (
        src_skyrg_df.groupby('source')
        .agg('sum') # sum because we need to preserve order
    )

    # merge into main df and compare the images
    srcs_df = srcs_df.merge(
        src_skyrg_df, left_index=True, right_index=True
    )

    del src_skyrg_df

    srcs_df['img_diff'] = srcs_df[
        ['img_list', 'skyreg_img_list', 'epoch_list', 'skyreg_epoch']
    ].apply(
        get_image_list_diff, axis=1
    )

    srcs_df = srcs_df.loc[
        srcs_df['img_diff'] != -1
    ]

    srcs_df = srcs_df.drop(
        ['epoch_list', 'skyreg_epoch'],
        axis=1
    )

    srcs_df['primary'] = srcs_df[
        'skyreg_img_list'
    ].apply(lambda x: x[0])

    srcs_df['detection'] = srcs_df[
        'img_list'
    ].apply(lambda x: x[0])

    srcs_df['in_primary'] = srcs_df[
        ['primary', 'img_list']
    ].apply(
        check_primary_image,
        axis=1
    )

    srcs_df = srcs_df.drop(['img_list', 'skyreg_img_list', 'primary'], axis=1)

    logger.info(
        'Ideal source coverage time: %.2f seconds', merged_timer.reset()
    )

    return srcs_df


def _get_skyregion_relations(
    row: pd.Series,
    coords: SkyCoord,
    ids: pd.core.indexes.numeric.Int64Index
) -> List[int]:
    '''
    For each sky region row a list is returned that
    contains the ids of other sky regions that overlap
    with the row sky region (including itself).

    Parameters
    ----------
    row : pd.Series
        A row from the dataframe containing all the sky regions of the run.
        Contains the 'id', 'centre_ra', 'centre_dec' and 'xtr_radius' columns.
    coords : SkyCoord
        A SkyCoord holding the coordinates of all sky regions.
    ids : The sky regions ids that match the coords.

    Returns
    -------
    related_ids : List[int]
        A list of other sky regions (including self) that are withing the
        'xtr_radius' of the sky region in the row.
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


def group_skyregions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Logic to group sky regions into overlapping groups.
    Returns a dataframe containing the sky region id as
    the index and a column containing a list of the
    sky region group number it belongs to.

    Parameters
    ----------
    df : pd.DataFrame
        A dataframe containing all the sky regions of the run. Only the
        'id', 'centre_ra', 'centre_dec' and 'xtr_radius' columns are required.
        +------+-------------+--------------+--------------+
        |   id |   centre_ra |   centre_dec |   xtr_radius |
        |------+-------------+--------------+--------------|
        |    2 |    319.652  |    0.0030765 |      6.72488 |
        |    3 |    319.652  |   -6.2989    |      6.7401  |
        |    1 |     21.8361 |  -73.121     |      7.24662 |
        +------+-------------+--------------+--------------+

    Returns
    -------
    skyreg_group_ids : pd.DataFrame
        The sky region group of each skyregion id.
        +----+----------------+
        |    |   skyreg_group |
        |----+----------------|
        |  2 |              1 |
        |  3 |              1 |
        |  1 |              2 |
        +----+----------------+
    """
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

    master_done = []  # keep track of all checked ids in master done

    for skyreg_id, neighbours in results.iteritems():

        if skyreg_id not in master_done:
            local_done = []   # a local done list for the sky region group.
            # add the current skyreg_id to both master and local done.
            master_done.append(skyreg_id)
            local_done.append(skyreg_id)
            # Define the new group number based on the existing ones.
            skyreg_group = len(skyreg_groups) + 1
            # Add all the ones that we know are neighbours that were obtained
            # from _get_skyregion_relations.
            skyreg_groups[skyreg_group] = list(neighbours)

            # Now the sky region group is extended out to include all those sky
            # regions that overlap with the neighbours.
            # Each neighbour is checked and added to the local done list.
            # Checked means that for each neighbour, it's own neighbours are
            # added to the current group if not in already.
            # When the local done is equal to the skyreg group we know that
            # we have exhausted all possible neighbours and that results in a
            # sky region group.
            while sorted(local_done) != sorted(skyreg_groups[skyreg_group]):
                # Loop over each neighbour
                for other_skyreg_id in skyreg_groups[skyreg_group]:
                    # If we haven't checked this neighbour locally proceed.
                    if other_skyreg_id not in local_done:
                        # Add it to the local checked.
                        local_done.append(other_skyreg_id)
                        # Get the neighbours neighbour and add these.
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


def get_parallel_assoc_image_df(
    images: List[Image], skyregion_groups: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge the sky region groups with the images and skyreg_ids.

    Parameters
    ----------
    images : List
        A list of the Image objects.
    skyregion_groups: pd.DataFrame
        The sky region group of each skyregion id.
        +----+----------------+
        |    |   skyreg_group |
        |----+----------------|
        |  2 |              1 |
        |  3 |              1 |
        |  1 |              2 |
        +----+----------------+

    Returns
    -------
    results : pd.DataFrame
        Dataframe containing the merged images and skyreg_id and skyreg_group.
        +----+-------------------------------+-------------+----------------+
        |    | image                         |   skyreg_id |   skyreg_group |
        |----+-------------------------------+-------------+----------------|
        |  0 | VAST_2118+00A.EPOCH01.I.fits  |           2 |              1 |
        |  1 | VAST_2118-06A.EPOCH01.I.fits  |           3 |              1 |
        |  2 | VAST_0127-73A.EPOCH01.I.fits  |           1 |              2 |
        |  3 | VAST_2118-06A.EPOCH03x.I.fits |           3 |              1 |
        |  4 | VAST_2118-06A.EPOCH02.I.fits  |           3 |              1 |
        |  5 | VAST_2118-06A.EPOCH05x.I.fits |           3 |              1 |
        |  6 | VAST_2118-06A.EPOCH06x.I.fits |           3 |              1 |
        |  7 | VAST_0127-73A.EPOCH08.I.fits  |           1 |              2 |
        +----+-------------------------------+-------------+----------------+
    """
    skyreg_ids = [i.skyreg_id for i in images]

    images_df = pd.DataFrame({
        'image_dj': images,
        'skyreg_id': skyreg_ids,
    })

    images_df = images_df.merge(
        skyregion_groups,
        how='left',
        left_on='skyreg_id',
        right_index=True
    )

    images_df['image_name'] = images_df['image_dj'].apply(
        lambda x: x.name
    )

    return images_df


def create_measurements_arrow_file(p_run: Run) -> None:
    """
    Creates a measurements.arrow file using the parquet outputs
    of a pipeline run. Vaex is used to do the exporting to arrow to
    ensure compatibility with Vaex.

    Parameters
    ----------
    p_run: Run
        Pipeline model instance.

    Returns
    -------
    None
    """
    logger.info('Creating measurements.arrow for run %s.', p_run.name)

    associations = pd.read_parquet(
        os.path.join(
            p_run.path,
            'associations.parquet'
        )
    )
    images = pd.read_parquet(
        os.path.join(
            p_run.path,
            'images.parquet'
        )
    )

    m_files = images['measurements_path'].tolist()

    m_files += glob.glob(os.path.join(
        p_run.path,
        'forced*.parquet'
    ))

    logger.debug('Loading %i files...', len(m_files))
    measurements = dd.read_parquet(m_files, engine='pyarrow').compute()

    measurements = measurements.loc[
        measurements['id'].isin(associations['meas_id'].values)
    ]

    measurements = (
        associations.loc[:, ['meas_id', 'source_id']]
        .set_index('meas_id')
        .merge(
            measurements,
            left_index=True,
            right_on='id'
        )
        .rename(columns={'source_id': 'source'})
    )

    logger.debug('Optimising dataframes.')
    measurements = optimize_ints(optimize_floats(measurements))

    # use vaex to export to arrow
    logger.debug("Loading to vaex.")
    measurements = vaex.from_pandas(measurements)

    logger.debug("Exporting to arrow.")
    outname = os.path.join(p_run.path, 'measurements.arrow')

    measurements.export_arrow(outname)


def create_measurement_pairs_arrow_file(p_run: Run) -> None:
    """
    Creates a measurement_pairs.arrow file using the parquet outputs
    of a pipeline run. Vaex is used to do the exporting to arrow to
    ensure compatibility with Vaex.

    Parameters
    ----------
    p_run: Run
        Pipeline model instance.

    Returns
    -------
    None
    """
    logger.info('Creating measurement_pairs.arrow for run %s.', p_run.name)

    measurement_pairs_df = pd.read_parquet(
        os.path.join(
            p_run.path,
            'measurement_pairs.parquet'
        )
    )

    logger.debug('Optimising dataframe.')
    measurement_pairs_df = optimize_ints(optimize_floats(measurement_pairs_df))

    # use vaex to export to arrow
    logger.debug("Loading to vaex.")
    measurement_pairs_df = vaex.from_pandas(measurement_pairs_df)

    logger.debug("Exporting to arrow.")
    outname = os.path.join(p_run.path, 'measurement_pairs.arrow')

    measurement_pairs_df.export_arrow(outname)


def calculate_vs_metric(
    flux_a: float, flux_b: float, flux_err_a: float, flux_err_b: float
) -> float:
    """Calculate the Vs variability metric which is the t-statistic that the provided
    fluxes are variable. See Section 5 of Mooley et al. (2016) for details,
    DOI: 10.3847/0004-637X/818/2/105.

    Args:
        flux_a (float): flux value "A".
        flux_b (float): flux value "B".
        flux_err_a (float): error of `flux_a`.
        flux_err_b (float): error of `flux_b`.

    Returns:
        float: the Vs metric for flux values "A" and "B".
    """
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)


def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """Calculate the m variability metric which is the modulation index between two fluxes.
    This is proportional to the fractional variability.
    See Section 5 of Mooley et al. (2016) for details, DOI: 10.3847/0004-637X/818/2/105.

    Args:
        flux_a (float): flux value "A".
        flux_b (float): flux value "B".

    Returns:
        float: the m metric for flux values "A" and "B".
    """
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))


def calculate_measurement_pair_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a DataFrame of measurement pairs and their 2-epoch variability metrics
    from a DataFrame of measurements. For more information on the variability metrics, see
    Section 5 of Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105.

    Args:
        df (pd.DataFrame): Input measurements. Must contain columns: id, source, flux_int,
            flux_int_err, flux_peak, flux_peak_err, has_siblings.

    Returns:
        pd.DataFrame: Measurement pairs and 2-epoch metrics. Will contain columns:
            source - the source ID
            id_a, id_b - the measurement IDs
            flux_int_a, flux_int_b - measurement integrated fluxes in mJy
            flux_int_err_a, flux_int_err_b - measurement integrated flux errors in mJy
            flux_peak_a, flux_peak_b - measurement peak fluxes in mJy/beam
            flux_peak_err_a, flux_peak_err_b - measurement peak flux errors in mJy/beam
            vs_peak, vs_int - variability t-statistic
            m_peak, m_int - variability modulation index
    """
    n_cpu = cpu_count() - 1

    """Create a DataFrame containing all measurement ID combinations per source.
    Resultant DataFrame will have a MultiIndex(["source", RangeIndex]) where "source" is
    the source ID and RangeIndex is an unnamed temporary ID for each measurement pair,
    unique only together with source.
    DataFrame will have columns [0, 1], each containing a measurement ID. e.g.
                       0      1
        source
        1       0      1   9284
                1      1  17597
                2      1  26984
                3   9284  17597
                4   9284  26984
        ...          ...    ...
        11105   2  11845  19961
        11124   0   3573  12929
                1   3573  21994
                2  12929  21994
        11128   0   6216  23534
    """
    measurement_combinations = (
        dd.from_pandas(df, n_cpu)
        .groupby("source")["id"]
        .apply(
            lambda x: pd.DataFrame(list(combinations(x, 2))
        ), meta={0: "i", 1: "i"},)
        .compute(num_workers=n_cpu, scheduler="processes")
    )

    """Drop the RangeIndex from the MultiIndex as it isn't required and rename the columns.
    Example resultant DataFrame:
               source   id_a   id_b
        0           1      1   9284
        1           1      1  17597
        2           1      1  26984
        3           1   9284  17597
        4           1   9284  26984
        ...       ...    ...    ...
        33640   11105  11845  19961
        33641   11124   3573  12929
        33642   11124   3573  21994
        33643   11124  12929  21994
        33644   11128   6216  23534
    Where source is the source ID, id_a and id_b are measurement IDs.
    """
    measurement_combinations = measurement_combinations.reset_index(
        level=1, drop=True
    ).rename(columns={0: "id_a", 1: "id_b"}).astype(int).reset_index()

    # Dask has a tendency to swap which order the measurement pairs are
    # defined in, even if the dataframe is pre-sorted. We want the pairs to be
    # in date order (a < b) so the code below corrects any that are not.
    measurement_combinations = measurement_combinations.join(
        df[['source', 'id', 'datetime']].set_index(['source', 'id']),
        on=['source', 'id_a'],
    )

    measurement_combinations = measurement_combinations.join(
        df[['source', 'id', 'datetime']].set_index(['source', 'id']),
        on=['source', 'id_b'], lsuffix='_a', rsuffix='_b'
    )

    to_correct_mask = (
        measurement_combinations['datetime_a']
        > measurement_combinations['datetime_b']
    )

    if np.any(to_correct_mask):
        logger.debug('Correcting measurement pairs order')
        (
            measurement_combinations.loc[to_correct_mask, 'id_a'],
            measurement_combinations.loc[to_correct_mask, 'id_b']
        ) = np.array([
            measurement_combinations.loc[to_correct_mask, 'id_b'].values,
            measurement_combinations.loc[to_correct_mask, 'id_a'].values
        ])

    measurement_combinations = measurement_combinations.drop(
        ['datetime_a', 'datetime_b'], axis=1
    )

    # add the measurement fluxes and errors
    association_fluxes = df.set_index(["source", "id"])[
        ["flux_int", "flux_int_err", "flux_peak", "flux_peak_err", "image"]
    ].rename(columns={"image": "image_name"})
    measurement_combinations = measurement_combinations.join(
        association_fluxes,
        on=["source", "id_a"],
    ).join(
        association_fluxes,
        on=["source", "id_b"],
        lsuffix="_a",
        rsuffix="_b",
    )

    # calculate 2-epoch metrics
    measurement_combinations["vs_peak"] = calculate_vs_metric(
        measurement_combinations.flux_peak_a,
        measurement_combinations.flux_peak_b,
        measurement_combinations.flux_peak_err_a,
        measurement_combinations.flux_peak_err_b,
    )
    measurement_combinations["vs_int"] = calculate_vs_metric(
        measurement_combinations.flux_int_a,
        measurement_combinations.flux_int_b,
        measurement_combinations.flux_int_err_a,
        measurement_combinations.flux_int_err_b,
    )
    measurement_combinations["m_peak"] = calculate_m_metric(
        measurement_combinations.flux_peak_a,
        measurement_combinations.flux_peak_b,
    )
    measurement_combinations["m_int"] = calculate_m_metric(
        measurement_combinations.flux_int_a,
        measurement_combinations.flux_int_b,
    )

    return measurement_combinations


def backup_parquets(p_run_path: str) -> None:
    """
    Backups up all the existing parquet files in a pipeline run directory.
    Backups are named with a '.backup' suffix in the pipeline run directory.

    Parameters
    ----------
    p_run_path : str
        The path of the pipeline run where the parquets are stored.

    Returns
    -------
    None
    """
    parquets = (
        glob.glob(os.path.join(p_run_path, "*.parquet"))
        # TODO Remove arrow when vaex support is dropped.
        + glob.glob(os.path.join(p_run_path, "*.arrow")))

    for i in parquets:
        backup_name = i + '.backup'
        if os.path.isfile(backup_name):
            logger.debug(f'Removing old backup file: {backup_name}.')
            os.remove(backup_name)
        shutil.copyfile(i, backup_name)


def reconstruct_associtaion_dfs(
    images_df_done: pd.DataFrame,
    previous_parquet_paths: Dict[str, str]) -> (pd.DataFrame, pd.DataFrame):
    """
    This function is used with add mode and performs the necessary
    manipulations to reconstruct the sources_df and skyc1_srcs required by
    association.

    Parameters
    ----------
    images_df_done : pd.DataFrame
        The images_df output from the existing run (from the parquet).
    previous_parquet_paths : Dict[str, str]
        Dictionary that contains the paths for the previous run parquet files.
        Keys are 'images', 'associations', 'sources', 'relations' and
        'measurement_pairs'.

    Returns
    -------
    sources_df, skyc1_srcs : pd.DataFrame, pd.DataFrame.
        The reconstructed sources_df and skyc1_srs dataframes.
    """
    prev_associations = pd.read_parquet(previous_parquet_paths['associations'])

    # Get the parquet paths from the image objects
    img_meas_paths = (
        images_df_done['image_dj'].apply(lambda x: x.measurements_path)
        .to_list()
    )

    # Obtain the pipeline run path in order to fetch forced measurements.
    run_path = previous_parquet_paths['sources'].replace(
        'sources.parquet.backup', "")

    # Get the forced measurement paths.
    img_fmeas_paths = []

    for i in images_df_done.image_name.values:
        forced_parquet = os.path.join(
            run_path, "forced_measurements_{}.parquet".format(
                i.replace(".", "_")
            )
        )
        if os.path.isfile(forced_parquet):
            img_fmeas_paths.append(forced_parquet)

    # Create union of paths.
    img_meas_paths += img_fmeas_paths

    # Define the columns that are required
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
        'flux_int_isl_ratio',
        'flux_peak',
        'flux_peak_err',
        'flux_peak_isl_ratio',
        'forced',
        'compactness',
        'has_siblings',
        'snr',
        'image_id',
        'time',
    ]

    # Open all the parquets using dask.
    measurements = dd.read_parquet(img_meas_paths, columns=cols).compute()

    # Create mask to drop measurements for epoch mode (epoch based mode).
    measurements_mask = measurements['id'].isin(
        prev_associations['meas_id'])
    measurements = measurements.loc[measurements_mask].set_index('id')

    # Set the index on images_df for faster merging.
    images_df_done['image_id'] = images_df_done['image_dj'].apply(
        lambda x: x.id).values
    images_df_done = images_df_done.set_index('image_id')

    # Merge image information to measurements
    measurements = (
        measurements.merge(
            images_df_done[['image_name', 'epoch']],
            left_on='image_id', right_index=True)
        .rename(columns={'image_name': 'image'})
    )

    # Drop any associations that are not used in this sky region group.
    associations_mask = prev_associations['meas_id'].isin(
        measurements.index.values)

    prev_associations = prev_associations.loc[associations_mask]

    # Merge measurements into the associations to form the sources_df.
    sources_df = (
        prev_associations.merge(
            measurements, left_on='meas_id', right_index=True)
        .rename(columns={
            'source_id': 'source', 'time': 'datetime', 'meas_id': 'id',
            'ra': 'ra_source', 'dec': 'dec_source',
            'uncertainty_ew': 'uncertainty_ew_source',
            'uncertainty_ns': 'uncertainty_ns_source',

        })
    )

    # Load up the previous unique sources.
    prev_sources = pd.read_parquet(
        previous_parquet_paths['sources'], columns=[
            'wavg_ra', 'wavg_dec',
            'wavg_uncertainty_ew', 'wavg_uncertainty_ns'
        ]
    )

    # Merge the wavg ra and dec to the sources_df - this is required to
    # create the skyc1_srcs below (but MUST be converted back to the source
    # ra and dec)
    sources_df = (
        sources_df.merge(
            prev_sources, left_on='source', right_index=True)
        .rename(columns={
            'wavg_ra': 'ra', 'wavg_dec': 'dec',
            'wavg_uncertainty_ew': 'uncertainty_ew',
            'wavg_uncertainty_ns': 'uncertainty_ns',
        })
    )

    # Load the previous relations
    prev_relations = pd.read_parquet(previous_parquet_paths['relations'])

    # Form relation lists to merge in.
    prev_relations = pd.DataFrame(
        prev_relations
        .groupby('from_source_id')['to_source_id']
        .apply(lambda x: x.values.tolist())
        .replace({np.nan: None})
    ).rename(columns={'to_source_id': 'related'})

    # Append the relations to only the last instance of each source
    # First get the ids of the sources
    relation_ids = sources_df[
        sources_df.source.isin(prev_relations.index.values)].drop_duplicates(
            'source', keep='last'
        ).index.values
    # Make sure we attach the correct source id
    source_ids = sources_df.loc[relation_ids].source.values
    sources_df['related'] = np.nan
    relations_to_update = prev_relations.loc[source_ids].to_numpy().copy()
    relations_to_update = np.reshape(
        relations_to_update, relations_to_update.shape[0])
    sources_df.loc[relation_ids, 'related'] = relations_to_update

    # Reorder so we don't mess up the dask metas.
    sources_df = sources_df[[
        'id', 'uncertainty_ew', 'weight_ew', 'uncertainty_ns', 'weight_ns',
        'flux_int', 'flux_int_err', 'flux_int_isl_ratio', 'flux_peak',
        'flux_peak_err', 'flux_peak_isl_ratio', 'forced', 'compactness',
        'has_siblings', 'snr', 'image', 'datetime', 'source', 'ra', 'dec',
        'ra_source', 'dec_source', 'd2d', 'dr', 'related', 'epoch',
        'uncertainty_ew_source', 'uncertainty_ns_source'
    ]]

    # Create the unique skyc1_srcs dataframe.
    skyc1_srcs = (
        sources_df.sort_values(by='id')
        .drop('related', axis=1)
        .drop_duplicates('source')
    ).copy(deep=True)


    # Get relations into the skyc1_srcs (as we only keep the first instance
    # which does not have the relation information)
    skyc1_srcs = skyc1_srcs.merge(
        prev_relations, how='left', left_on='source', right_index=True)

    # Need to break the pointer relationship between the related sources (
    # deep=True copy does not truly copy mutable type objects)
    relation_mask = skyc1_srcs.related.isna()
    relation_vals = skyc1_srcs.loc[~relation_mask]['related'].to_list()
    new_relation_vals = [x.copy() for x in relation_vals]
    skyc1_srcs.loc[~relation_mask, 'related'] = new_relation_vals

    # Reorder so we don't mess up the dask metas.
    skyc1_srcs = skyc1_srcs[[
        'id', 'ra', 'uncertainty_ew', 'weight_ew', 'dec', 'uncertainty_ns',
        'weight_ns', 'flux_int', 'flux_int_err', 'flux_int_isl_ratio',
        'flux_peak', 'flux_peak_err', 'flux_peak_isl_ratio', 'forced',
        'compactness', 'has_siblings', 'snr', 'image', 'datetime', 'source',
        'ra_source', 'dec_source', 'd2d', 'dr', 'related', 'epoch'
    ]].reset_index(drop=True)

    # Finally move the source ra and dec back to the sources_df ra and dec
    # columns
    sources_df['ra'] = sources_df['ra_source']
    sources_df['dec'] = sources_df['dec_source']
    sources_df['uncertainty_ew'] = sources_df['uncertainty_ew_source']
    sources_df['uncertainty_ns'] = sources_df['uncertainty_ns_source']

    # Drop not needed columns for the sources_df.
    sources_df = sources_df.drop([
        'uncertainty_ew_source', 'uncertainty_ns_source'
    ], axis=1).reset_index(drop=True)

    return sources_df, skyc1_srcs
