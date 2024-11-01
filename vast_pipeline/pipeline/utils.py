"""
This module contains utility functions that are used by the pipeline during
the processing of a run.
"""

import os
import logging
import glob
import shutil
import numpy as np
import pandas as pd
import pyarrow as pa
import astropy.units as u
import dask
import dask.dataframe as dd
import psutil

from typing import Any, List, Optional, Dict, Tuple, Union
from astropy.coordinates import SkyCoord, Angle
from django.conf import settings
from django.contrib.auth.models import User
from psutil import cpu_count
from itertools import chain

from vast_pipeline.image.main import FitsImage, SelavyImage
from vast_pipeline.image.utils import open_fits
from vast_pipeline.utils.utils import (
    eq_to_cart, StopWatch, optimize_ints, optimize_floats,
    calculate_workers_and_partitions
)
from vast_pipeline.models import (
    Band, Image, Run, SkyRegion
)


logger = logging.getLogger(__name__)
dask.config.set({"multiprocessing.context": "fork"})


def get_create_skyreg(image: Image) -> SkyRegion:
    '''
    This creates a Sky Region object in Django ORM given the related
    image object.

    Args:
        image: The image Django ORM object.

    Returns:
        The sky region Django ORM object.
    '''
    # In the calculations below, it is assumed the image has square
    # pixels (this pipeline has been designed for ASKAP images, so it
    # should always be square). It will likely give wrong results if not
    skyregions = SkyRegion.objects.filter(
        centre_ra=image.ra,
        centre_dec=image.dec,
        xtr_radius=image.fov_bmin
    )
    if skyregions:
        skyr = skyregions.get()
        logger.info('Found sky region %s', skyr)
    else:
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

    return skyr


def get_create_img_band(image: FitsImage) -> Band:
    '''
    Return the existing Band row for the given FitsImage.
    An image is considered to belong to a band if its frequency is within some
    tolerance of the band's frequency.
    Returns a Band row or None if no matching band.

    Args:
        image: The image Django ORM object.

    Returns:
        The band Django ORM object.
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


def get_create_img(band_id: int, image: SelavyImage) -> Tuple[Image, bool]:
    """
    Function to fetch or create the Image and Sky Region objects for an image.

    Args:
        band_id: The integer database id value of the frequency band of the
            image.
        image: The image object.

    Returns:
        The resulting image django ORM object.
        `True` the image already existed in the database, `False` if not.
    """
    images = Image.objects.filter(name__exact=image.name)
    exists = images.exists()
    if exists:
        img: Image = images.get()
        # Add background path if not originally provided
        if image.background_path and not img.background_path:
            img.background_path = image.background_path
            img.save()
    else:
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
                    getattr(image, fld.attname, None) is not None):
                setattr(img, fld.attname, getattr(image, fld.attname))

        img.rms_median, img.rms_min, img.rms_max = get_rms_noise_image_values(
            img.noise_path)

        # get create the sky region and associate with image
        img.skyreg = get_create_skyreg(img)
        img.save()

    return (img, exists)


def get_create_p_run(
    name: str, path: str, description: str = None, user: User = None
) -> Tuple[Run, bool]:
    '''
    Get or create a pipeline run in db, return the run django object and
    a flag True/False if has been created or already exists.

    Args:
        name: The name of the pipeline run.
        path: The system path to the pipeline run folder which contains the
            configuration file and where outputs will be saved.
        description: An optional description of the pipeline run.
        user: The Django user that launched the pipeline run.

    Returns:
        The pipeline run object.
        Whether the pipeline run already existed ('True') or not ('False').
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


def add_run_to_img(pipeline_run: Run, img: Image) -> None:
    """
    Add a pipeline run to an Image (and corresponding SkyRegion) in the db

    Args:
        pipeline_run:
            Pipeline run object you want to add.
        img:
            Image object you want to add to.

    Returns:
        None
    """
    skyreg = img.skyreg
    # check and add the many to many if not existent
    if not Image.objects.filter(id=img.id, run__id=pipeline_run.id).exists():
        logger.info('Adding %s to image %s', pipeline_run, img.name)
        img.run.add(pipeline_run)

    if pipeline_run not in skyreg.run.all():
        logger.info('Adding %s to sky region %s', pipeline_run, skyreg)
        skyreg.run.add(pipeline_run)


def remove_duplicate_measurements(
    sources_df: pd.DataFrame,
    dup_lim: Optional[Angle] = None,
    ini_df: bool = False
) -> pd.DataFrame:
    """
    Remove perceived duplicate sources from a dataframe of loaded
    measurements. Duplicates are determined by their separation and whether
    this distances is within the 'dup_lim'.

    Args:
        sources_df:
            The loaded measurements from two or more images.
        dup_lim:
            The separation limit of when a source is considered a duplicate.
            Defaults to None in which case 2.5 arcsec is used (usual ASKAP
            pixel size).
        ini_df:
            Boolean to indicate whether these sources are part of the initial
            source list creation for association. If 'True' the source ids are
            reset ready for the first iteration. Defaults to 'False'.

    Returns:
        The input sources_df with duplicate sources removed.
    """
    logger.debug('Cleaning duplicate sources from epoch...')

    if dup_lim is None:
        dup_lim = Angle(2.5 * u.arcsec)

    logger.debug(
        'Using duplicate crossmatch radius of %.2f arcsec.', dup_lim.arcsec
    )

    # sort by the distance from the image centre so we know
    # that the first source is always the one to keep
    sources_df = sources_df.sort_values(by='dist_from_centre')

    sources_sc = SkyCoord(
        sources_df['ra'],
        sources_df['dec'],
        unit=(u.deg, u.deg)
    )

    # perform search around sky to get all self matches
    idxc, idxcatalog, *_ = sources_sc.search_around_sky(
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

    Args:
        image:
            The object representing the image for which to load the
            measurements.
        cols:
            The columns to load.
        start_id:
            The number to start from when setting the source ids (when
            'ini_df' is 'True'). Defaults to 0.
        ini_df:
            Boolean to indicate whether these sources are part of the initial
            source list creation for association. If 'True' the source ids are
            reset ready for the first iteration. Defaults to 'False'.

    Returns:
        The measurements of the image with some extra values set ready for
            association.
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
) -> pd.DataFrame:
    '''
    Initialise the source dataframe to use in association logic by
    reading the measurement parquet file and creating columns. When epoch
    based association is used it will also remove duplicate measurements from
    the list of sources.

    Args:
        images:
            A list holding the Image objects of the images to load measurements
            for.
        perc_error:
            A percentage flux error to apply to the flux errors of the
            measurements. Defaults to 0.
        duplicate_limit:
            The separation limit of when a source is considered a duplicate.
            Defaults to None in which case 2.5 arcsec is used in the
            'remove_duplicate_measurements' function (usual ASKAP pixel size).
        ini_df:
            Boolean to indicate whether these sources are part of the initial
            source list creation for association. If 'True' the source ids are
            reset ready for the first iteration. Defaults to 'False'.

    Returns:
        The measurements of the image(s) with some extra values set ready for
            association and duplicates removed if necessary.
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
            df = pd.concat(
                [
                    df,
                    _load_measurements(
                        img, cols, df.source.max(), ini_df=ini_df
                    )
                ],
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

    Args:
        row:
            The relation information Series from the association dataframe.
            Only the columns ['related_skyc1', 'source_skyc1'] are required
            for advanced, these are instead called ['related', 'source']
            for basic.
        advanced:
            Whether advanced association is being used which changes the names
            of the columns involved.
        source_ids:
            A dataframe that contains the other ids to append to related for
            each original source.
            +----------------+--------+
            |   source_skyc1 | 0      |
            |----------------+--------|
            |            122 | [5542] |
            |            254 | [5543] |
            |            262 | [5544] |
            |            405 | [5545] |
            |            656 | [5546] |
            +----------------+--------+

    Returns:
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
            out = [row[source_col], ]

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

    Args:
        row:
            The relation information Series from the association dataframe.
            Only the columns ['related_skyc1', 'new_relations'] are required.

    Returns:
        The new related field for the source in question, containing the
            appended ids.
    """
    out = row['new_relations'].copy()

    if isinstance(row['related_skyc1'], list):
        out += row['related_skyc1'].copy()

    return out


def cross_join(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """
    A convenience function to merge two dataframes.

    Args:
        left: The base pandas DataFrame to merge.
        right: The pandas DataFrame to merge to the left.

    Returns:
        The resultant merged DataFrame.
    """
    return (
        left.assign(key=1)
        .merge(right.assign(key=1), on='key')
        .drop('key', axis=1)
    )


def get_eta_metric(
    row: Dict[str, float], df: pd.DataFrame, peak: bool = False
) -> float:
    '''
    Calculates the eta variability metric of a source.
    Works on the grouped by dataframe using the fluxes
    of the associated measurements.

    Args:
        row: Dictionary containing statistics for the current source.
        df: The grouped by sources dataframe of the measurements containing all
            the flux and flux error information,
        peak: Whether to use peak_flux for the calculation. If False then the
            integrated flux is used.

    Returns:
        The calculated eta value.
    '''
    if row['n_meas'] == 1:
        return 0.

    suffix = 'peak' if peak else 'int'
    weights = 1. / df[f'flux_{suffix}_err'].values**2
    fluxes = df[f'flux_{suffix}'].values
    eta = (row['n_meas'] / (row['n_meas'] - 1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta


def groupby_funcs(df: pd.DataFrame) -> pd.Series:
    '''
    Performs calculations on the unique sources to get the
    lightcurve properties. Works on the grouped by source
    dataframe.

    Args:
        df: The current iteration dataframe of the grouped by sources
            dataframe.

    Returns:
        Pandas series containing the calculated metrics of the source.
    '''
    # calculated average ra, dec, fluxes and metrics
    d = {}
    d['img_list'] = df['image'].values.tolist()
    d['n_meas_forced'] = df['forced'].sum()
    d['n_meas'] = df['id'].count()
    d['n_meas_sel'] = d['n_meas'] - d['n_meas_forced']
    d['n_sibl'] = df['has_siblings'].sum()
    if d['n_meas_forced'] > 0:
        non_forced_sel = ~df['forced']
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


def parallel_groupby(df: pd.DataFrame, n_cpu: int = 0, max_partition_mb: int = 15) -> pd.DataFrame:
    """
    Performs the parallel source dataframe operations to calculate the source
    metrics using Dask and returns the resulting dataframe.

    Args:
        df: The sources dataframe produced by the previous pipeline stages.
        n_cpu: The desired number of workers for Dask
        max_partition_mb: The desired maximum size (in MB) of the partitions for Dask.

    Returns:
        The source dataframe with the calculated metric columns.
    """
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
    n_workers, n_partitions = calculate_workers_and_partitions(
        df,
        n_cpu=n_cpu,
        max_partition_mb=max_partition_mb)
    logger.debug(f"Running association with {n_workers} CPUs")
    out = dd.from_pandas(df.set_index('source'), npartitions=n_partitions)
    out = (
        out.groupby('source')
        .apply(
            groupby_funcs,
            meta=col_dtype
        )
        .compute(num_workers=n_workers, scheduler='processes')
    )

    out['n_rel'] = out['related_list'].apply(
        lambda x: 0 if x == -1 else len(x))

    return out


def calc_ave_coord(grp: pd.DataFrame) -> pd.Series:
    """
    Calculates the average coordinate of the grouped by sources dataframe for
    each unique group, along with defining the image and epoch list for each
    unique source (group).

    Args:
        grp: The current group dataframe (unique source) of the grouped by
            dataframe being acted upon.

    Returns:
        A pandas series containing the average coordinate along with the
            image and epoch lists.
    """
    d = {}
    grp = grp.sort_values(by='datetime')
    d['img_list'] = grp['image'].values.tolist()
    d['epoch_list'] = grp['epoch'].values.tolist()
    d['wavg_ra'] = grp['interim_ew'].sum() / grp['weight_ew'].sum()
    d['wavg_dec'] = grp['interim_ns'].sum() / grp['weight_ns'].sum()

    return pd.Series(d)


def parallel_groupby_coord(df: pd.DataFrame, n_cpu: int = 0, max_partition_mb: int = 15) -> pd.DataFrame:
    """
    This function uses Dask to perform the average coordinate and unique image
    and epoch lists calculation. The result from the Dask compute is returned
    which is a dataframe containing the results for each source.

    Args:
        df: The sources dataframe produced by the pipeline.
        n_cpu: The desired number of workers for Dask
        max_partition_mb: The desired maximum size (in MB) of the partitions for Dask.

    Returns:
        The resulting average coordinate values and unique image and epoch
            lists for each unique source (group).
    """
    col_dtype = {
        'img_list': 'O',
        'epoch_list': 'O',
        'wavg_ra': 'f',
        'wavg_dec': 'f',
    }
    n_workers, n_partitions = calculate_workers_and_partitions(
        df,
        n_cpu=n_cpu,
        max_partition_mb=max_partition_mb)
    logger.debug(f"Running association with {n_workers} CPUs")

    out = dd.from_pandas(df.set_index('source'), npartitions=n_partitions)
    out = (
        out.groupby('source')
        .apply(calc_ave_coord, meta=col_dtype)
        .compute(num_workers=n_workers, scheduler='processes')
    )

    return out


def get_rms_noise_image_values(rms_path: str) -> Tuple[float, float, float]:
    '''
    Open the RMS noise FITS file and compute the median, max and min
    rms values to be added to the image model and then used in the
    calculations.

    Args:
        rms_path: The system path to the RMS FITS image.

    Returns:
        The median value of the RMS image.
        The minimum value of the RMS image.
        The maximum value of the RMS image.

    Raises:
        IOError: Raised when the RMS FITS file cannot be found.
    '''
    logger.debug('Extracting Image RMS values from Noise file...')
    med_val = min_val = max_val = 0.
    try:
        with open_fits(rms_path) as f:
            data = f[0].data
            data = data[np.isfinite(data) & (data > 0.)]
            med_val = np.median(data) * 1e+3
            min_val = np.min(data) * 1e+3
            max_val = np.max(data) * 1e+3
            del data
    except Exception:
        raise IOError(f'Could not read this RMS FITS file: {rms_path}')
    logger.debug('Image RMS Min: %.3g Max: %.3g Median: %.3g', min_val, max_val, med_val)

    return med_val, min_val, max_val


def get_image_list_diff(row: pd.Series) -> Union[List[str], int]:
    """
    Calculate the difference between the ideal coverage image list of a source
    and the actual observed image list. Also checks whether an epoch does in
    fact contain a detection but is not in the expected 'ideal' image for that
    epoch.

    Args:
        row: The row from the sources dataframe that is being iterated over.

    Returns:
        A list of the images missing from the observed image list.
        A '-1' integer value if there are no missing images.
    """
    out = list(
        filter(lambda arg: arg not in row['img_list'], row['skyreg_img_list'])
    )

    # set empty list to -1
    if not out:
        return -1

    # Check that an epoch has not already been seen (just not in the 'ideal'
    # image)
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
        return -1

    return out


def get_names_and_epochs(grp: pd.DataFrame) -> pd.Series:
    """
    Convenience function to group together the image names, epochs and
    datetimes into one list object which is then returned as a pandas series.
    This is necessary for easier processing in the ideal coverage analysis.

    Args:
        grp: A group from the grouped by sources DataFrame.

    Returns:
        Pandas series containing the list object that contains the lists of the
            image names, epochs and datetimes.
    """
    d = {}
    d['skyreg_img_epoch_list'] = [[[x, ], y, z] for x, y, z in zip(
        grp['name'].values.tolist(),
        grp['epoch'].values.tolist(),
        grp['datetime'].values.tolist()
    )]

    return pd.Series(d)


def check_primary_image(row: pd.Series) -> bool:
    """
    Checks whether the primary image of the ideal source
    dataframe is in the image list for the source.

    Args:
        row:
            Input dataframe row, with columns ['primary'] and ['img_list'].

    Returns:
        True if primary in image list else False.
    """
    return row['primary'] in row['img_list']


def get_src_skyregion_merged_df(
    sources_df: pd.DataFrame, images_df: pd.DataFrame, skyreg_df: pd.DataFrame,
    n_cpu: int = 0, max_partition_mb: int = 15
) -> pd.DataFrame:
    """
    Analyses the current sources_df to determine what the 'ideal coverage'
    for each source should be. In other words, what images is the source
    missing in when it should have been seen.

    Args:
        sources_df:
            The output of the association  step containing the
            measurements associated into sources.
        images_df:
            Contains the images of the pipeline run. I.e. all image
            objects for the run loaded into a dataframe.
        skyreg_df:
            Contains the sky regions of the pipeline run. I.e. all
            sky region objects for the run loaded into a dataframe.
        n_cpu:
            The desired number of workers for Dask
        max_partition_mb:
            The desired maximum size (in MB) of the partitions for Dask.

    Returns:
        DataFrame containing missing image information (see source code for
            dataframe format).
    """
    # Output format:
    # +----------+----------------------------------+-----------+------------+
    # |   source | img_list                         |   wavg_ra |   wavg_dec |
    # |----------+----------------------------------+-----------+------------+
    # |      278 | ['VAST_0127-73A.EPOCH01.I.fits'] |  22.2929  |   -71.8717 |
    # |      702 | ['VAST_0127-73A.EPOCH01.I.fits'] |  28.8125  |   -69.3547 |
    # |      844 | ['VAST_0127-73A.EPOCH01.I.fits'] |  17.3152  |   -72.346  |
    # |      934 | ['VAST_0127-73A.EPOCH01.I.fits'] |   9.75754 |   -72.9629 |
    # |     1290 | ['VAST_0127-73A.EPOCH01.I.fits'] |  20.8455  |   -76.8269 |
    # +----------+----------------------------------+-----------+------------+
    # ------------------------------------------------------------------+
    #  skyreg_img_list                                                  |
    # ------------------------------------------------------------------+
    #  ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH01.I.fits', 'VAST_0127-73A.EPOCH08.I.fits'] |
    # ------------------------------------------------------------------+
    # ----------------------------------+------------------------------+
    #  img_diff                         | primary                      |
    # ----------------------------------+------------------------------+
    #  ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] | VAST_0127-73A.EPOCH01.I.fits |
    # ----------------------------------+------------------------------+
    # ------------------------------+--------------+
    #  detection                    | in_primary   |
    # ------------------------------+--------------|
    #  VAST_0127-73A.EPOCH01.I.fits | True         |
    #  VAST_0127-73A.EPOCH01.I.fits | True         |
    #  VAST_0127-73A.EPOCH01.I.fits | True         |
    #  VAST_0127-73A.EPOCH01.I.fits | True         |
    #  VAST_0127-73A.EPOCH01.I.fits | True         |
    # ------------------------------+--------------+
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
    srcs_df = parallel_groupby_coord(sources_df,
                                     n_cpu=n_cpu,
                                     max_partition_mb=max_partition_mb)
    logger.debug('Groupby-apply time: %.2f seconds', timer.reset())

    del sources_df

    # crossmatch sources with sky regions up to the max sky region radius
    skyreg_coords = SkyCoord(
        ra=skyreg_df.centre_ra, dec=skyreg_df.centre_dec, unit="deg"
    )
    srcs_coords = SkyCoord(
        ra=srcs_df.wavg_ra,
        dec=srcs_df.wavg_dec,
        unit="deg")
    skyreg_idx, srcs_idx, sep, _ = srcs_coords.search_around_sky(
        skyreg_coords, skyreg_df.xtr_radius.max() * u.deg
    )
    skyreg_df = skyreg_df.drop(
        columns=[
            "centre_ra",
            "centre_dec"]).set_index("id")

    # select rows where separation is less than sky region radius
    # drop not more useful columns and groupby source id
    # compute list of images
    src_skyrg_df = (
        pd.DataFrame(
            {
                "source": srcs_df.iloc[srcs_idx].index,
                "id": skyreg_df.iloc[skyreg_idx].index,
                "sep": sep.to("deg").value,
            }
        )
        .merge(skyreg_df, left_on="id", right_index=True)
        .query("sep < xtr_radius")
        .drop(columns=["id", "xtr_radius"])
        .explode("skyreg_img_epoch_list")
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
        lambda x: [x, ]
    )

    src_skyrg_df = (
        src_skyrg_df.groupby('source')
        .sum(numeric_only=False)  # sum because we need to preserve order
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

    Args:
        row:
            A row from the dataframe containing all the sky regions of the run.
            Contains the 'id', 'centre_ra', 'centre_dec' and 'xtr_radius'
            columns.
        coords: A SkyCoord holding the coordinates of all sky regions.
        ids: The sky regions ids that match the coords.

    Returns:
        A list of other sky regions (including self) that are within the
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

    Args:
        df:
            A dataframe containing all the sky regions of the run. Only the
            'id', 'centre_ra', 'centre_dec' and 'xtr_radius' columns are
            required.
            +------+-------------+--------------+--------------+
            |   id |   centre_ra |   centre_dec |   xtr_radius |
            |------+-------------+--------------+--------------|
            |    2 |    319.652  |    0.0030765 |      6.72488 |
            |    3 |    319.652  |   -6.2989    |      6.7401  |
            |    1 |     21.8361 |  -73.121     |      7.24662 |
            +------+-------------+--------------+--------------+

    Returns:
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

    skyreg_groups: Dict[int, List[Any]] = {}

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
            skyreg_group_ids[j] = i

    skyreg_group_ids = pd.DataFrame.from_dict(
        skyreg_group_ids, orient='index'
    ).rename(columns={0: 'skyreg_group'})

    return skyreg_group_ids


def get_parallel_assoc_image_df(
    images: List[Image], skyregion_groups: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge the sky region groups with the images and skyreg_ids.

    Args:
        images:
            A list of the Image objects.
        skyregion_groups:
            The sky region group of each skyregion id.
            +----+----------------+
            |    |   skyreg_group |
            |----+----------------|
            |  2 |              1 |
            |  3 |              1 |
            |  1 |              2 |
            +----+----------------+

    Returns:
        Dataframe containing the merged images and skyreg_id and skyreg_group
            (see source code for output format).
    """
    # Output format
    # +----+-------------------------------+-------------+----------------+
    # |    | image                         |   skyreg_id |   skyreg_group |
    # |----+-------------------------------+-------------+----------------|
    # |  0 | VAST_2118+00A.EPOCH01.I.fits  |           2 |              1 |
    # |  1 | VAST_2118-06A.EPOCH01.I.fits  |           3 |              1 |
    # |  2 | VAST_0127-73A.EPOCH01.I.fits  |           1 |              2 |
    # |  3 | VAST_2118-06A.EPOCH03x.I.fits |           3 |              1 |
    # |  4 | VAST_2118-06A.EPOCH02.I.fits  |           3 |              1 |
    # |  5 | VAST_2118-06A.EPOCH05x.I.fits |           3 |              1 |
    # |  6 | VAST_2118-06A.EPOCH06x.I.fits |           3 |              1 |
    # |  7 | VAST_0127-73A.EPOCH08.I.fits  |           1 |              2 |
    # +----+-------------------------------+-------------+----------------+
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

    images_df['image_datetime'] = images_df['image_dj'].apply(
        lambda x: x.datetime
    )

    return images_df


def create_measurements_arrow_file(p_run: Run) -> None:
    """
    Creates a measurements.arrow file using the parquet outputs
    of a pipeline run.

    Args:
        p_run:
            Pipeline model instance.

    Returns:
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

    # drop timezone from datetime for vaex compatibility
    # TODO: Look to keep the timezone if/when vaex is compatible.
    measurements['time'] = measurements['time'].dt.tz_localize(None)

    logger.debug('Optimising dataframes.')
    measurements = optimize_ints(optimize_floats(measurements))

    logger.debug("Loading to pyarrow table.")
    measurements = pa.Table.from_pandas(measurements)

    logger.debug("Exporting to arrow file.")
    outname = os.path.join(p_run.path, 'measurements.arrow')

    local = pa.fs.LocalFileSystem()

    with local.open_output_stream(outname) as file:
        with pa.RecordBatchFileWriter(file, measurements.schema) as writer:
            writer.write_table(measurements)


def create_measurement_pairs_arrow_file(p_run: Run) -> None:
    """
    Creates a measurement_pairs.arrow file using the parquet outputs
    of a pipeline run.

    Args:
        p_run:
            Pipeline model instance.

    Returns:
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

    logger.debug("Loading to pyarrow table.")
    measurement_pairs_df = pa.Table.from_pandas(measurement_pairs_df)

    logger.debug("Exporting to arrow file.")
    outname = os.path.join(p_run.path, 'measurement_pairs.arrow')

    local = pa.fs.LocalFileSystem()

    with local.open_output_stream(outname) as file:
        with pa.RecordBatchFileWriter(file, measurement_pairs_df.schema) as writer:
            writer.write_table(measurement_pairs_df)


def backup_parquets(p_run_path: str) -> None:
    """
    Backups up all the existing parquet files in a pipeline run directory.
    Backups are named with a '.bak' suffix in the pipeline run directory.

    Args:
        p_run_path:
            The path of the pipeline run where the parquets are stored.

    Returns:
        None
    """
    parquets = (
        glob.glob(os.path.join(p_run_path, "*.parquet"))
        # TODO Remove arrow when arrow files are no longer required.
        + glob.glob(os.path.join(p_run_path, "*.arrow")))

    for i in parquets:
        backup_name = i + '.bak'
        if os.path.isfile(backup_name):
            logger.debug(f'Removing old backup file: {backup_name}.')
            os.remove(backup_name)
        shutil.copyfile(i, backup_name)


def create_temp_config_file(p_run_path: str) -> None:
    """
    Creates the temp config file which is saved at the beginning of each run.

    It is to avoid issues created by users changing the config while the run
    is running.

    Args:
        p_run_path:
            The path of the pipeline run of the config to be copied.

    Returns:
        None
    """
    config_name = 'config.yaml'
    temp_config_name = 'config_temp.yaml'

    shutil.copyfile(
        os.path.join(p_run_path, config_name),
        os.path.join(p_run_path, temp_config_name)
    )


def reconstruct_associtaion_dfs(
    images_df_done: pd.DataFrame,
    previous_parquet_paths: Dict[str, str]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    This function is used with add image mode and performs the necessary
    manipulations to reconstruct the sources_df and skyc1_srcs required by
    association.

    Args:
        images_df_done:
            The images_df output from the existing run (from the parquet).
        previous_parquet_paths:
            Dictionary that contains the paths for the previous run parquet
            files. Keys are 'images', 'associations', 'sources', 'relations'
            and 'measurement_pairs'.

    Returns:
        The reconstructed `sources_df` dataframe.
        The reconstructed `skyc1_srs` dataframes.
    """
    prev_associations = pd.read_parquet(previous_parquet_paths['associations'])

    logger.debug(images_df_done)
    logger.debug(images_df_done['image_dj'])

    # Get the parquet paths from the image objects
    img_meas_paths = (
        images_df_done['image_dj'].apply(lambda x: x.measurements_path)
        .to_list()
    )
    logger.debug(img_meas_paths)

    # Obtain the pipeline run path in order to fetch forced measurements.
    run_path = previous_parquet_paths['sources'].replace(
        'sources.parquet.bak', ''
    )

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

    # Open all the parquets
    logger.debug(
        "Opening all measurement parquet files to use in reconstruction..."
    )
    measurements = pd.concat(
        [pd.read_parquet(f, columns=cols) for f in img_meas_paths]
    )

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
            left_on='image_id', right_index=True
        )
        .rename(columns={'image_name': 'image'})
    )

    # Drop any associations that are not used in this sky region group.
    associations_mask = prev_associations['meas_id'].isin(
        measurements.index.values)

    prev_associations = prev_associations.loc[associations_mask]

    # Merge measurements into the associations to form the sources_df.
    sources_df = (
        prev_associations.merge(
            measurements, left_on='meas_id', right_index=True
        )
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
            'wavg_uncertainty_ew', 'wavg_uncertainty_ns',
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
        sources_df[~sources_df['forced']]
        .sort_values(by='id')
        .drop('related', axis=1)
        .drop_duplicates('source')
    ).copy(deep=True)

    # Get relations into the skyc1_srcs (as we only keep the first instance
    # which does not have the relation information)
    skyc1_srcs = skyc1_srcs.merge(
        prev_relations, how='left', left_on='source', right_index=True
    )

    # Need to break the pointer relationship between the related sources (
    # deep=True copy does not truly copy mutable type objects)
    relation_mask = skyc1_srcs.related.notna()
    relation_vals = skyc1_srcs.loc[relation_mask, 'related'].to_list()
    new_relation_vals = [x.copy() for x in relation_vals]
    skyc1_srcs.loc[relation_mask, 'related'] = new_relation_vals

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


def write_parquets(
    images: List[Image],
    skyregions: List[SkyRegion],
    bands: List[Band],
    run_path: str
) -> pd.DataFrame:
    """
    This function saves images, skyregions and bands to parquet files.
    It also returns a DataFrame containing containing the information
    of the sky regions associated with the current run.

    Args:
        images: list of image Django ORM objects.
        skyregions: list sky region Django ORM objects.
        bands: list of band Django ORM objects.
        run_path: directory to save parquets to.

    Returns:
        Sky regions as pandas DataFrame.
    """
    # write images parquet file under pipeline run folder
    images_df = pd.DataFrame(map(lambda x: x.__dict__, images))
    images_df = images_df.drop('_state', axis=1)
    images_df.to_parquet(
        os.path.join(run_path, 'images.parquet'),
        index=False
    )
    # write skyregions parquet file under pipeline run folder
    skyregs_df = pd.DataFrame(map(lambda x: x.__dict__, skyregions))
    skyregs_df = skyregs_df.drop('_state', axis=1)
    skyregs_df.to_parquet(
        os.path.join(run_path, 'skyregions.parquet'),
        index=False
    )
    # write skyregions parquet file under pipeline run folder
    bands_df = pd.DataFrame(map(lambda x: x.__dict__, bands))
    bands_df = bands_df.drop('_state', axis=1)
    bands_df.to_parquet(
        os.path.join(run_path, 'bands.parquet'),
        index=False
    )

    return skyregs_df


def get_total_memory_usage():
    """
    This function gets the current memory usage and returns a string.

    Returns:
        A float containing the current resource usage.
    """
    mem = psutil.virtual_memory()[3]  # resource usage in bytes
    mem = mem / 1024**3  # resource usage in GB

    return mem


def log_total_memory_usage():
    """
    This function gets the current memory usage and logs it.

    Returns:
        None
    """
    mem = get_total_memory_usage()

    logger.debug(f"Current memory usage: {mem:.3f}GB")


def get_df_memory_usage(df):
    """
    This function calculates the memory usage of a pandas dataframe and
    logs it.

    Args:
        df: The pandas dataframe to calculate the memory usage of.

    Returns:
        The pandas dataframe memory usage in MB
    """
    mem = df.memory_usage(deep=True).sum() / 1e6

    return mem
