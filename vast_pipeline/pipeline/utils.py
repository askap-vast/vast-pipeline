"""
This module contains utility functions that are used by the pipeline during
the processing of a run.
"""

import os
import logging
import glob
import gc
import shutil
import numpy as np
import pandas as pd
import astropy.units as u
import dask
import dask.dataframe as dd
import dask.config as dc
import psutil
import tempfile
import itertools

from typing import Any, List, Optional, Dict, Tuple, Union
from astropy.coordinates import SkyCoord, Angle
from django.conf import settings
from django.contrib.auth.models import User
from itertools import chain
from multiprocessing import Pool

from vast_pipeline.image.main import FitsImage, SelavyImage
from vast_pipeline.image.utils import open_fits
from vast_pipeline.utils.utils import (
    eq_to_cart, StopWatch, optimise_numeric, copy_file_or_dir,
    delete_file_or_dir, generate_shortuuid, UUID_LEN_SOURCE, calculate_n_partitions
)
from vast_pipeline.models import (
    Band, Image, Run, SkyRegion
)
from vast_pipeline.models import Band, Image, Run, SkyRegion


logger = logging.getLogger(__name__)
dask.config.set({"multiprocessing.context": "fork",
                 "dataframe.convert-string": False})


def get_create_skyreg(image: Image, radius: float = 10.) -> SkyRegion:
    '''
    This creates a SkyRegion object in Django ORM given the related
    image object. If a SkyRegion already exists and has an image radius
    within `radius` arcsec of the input image then use that SkyRegion.

    Args:
        image: An Image object containing attrbutes ra, dec, fov_bmin,
            physical_bmin and physical_bmaj
        radius: Search radius (in arcsec) for matching to existing SkyRegion.

    Returns:
        The sky region Django ORM object.
    '''
    # NOTE: In the calculations below, it is assumed the image has square
    # pixels (this pipeline has been designed for ASKAP images, so it
    # should always be square). It will likely give wrong results if not

    radius_deg = radius/3600.
    skyregions = SkyRegion.objects.cone_search(
        ra=float(image.ra),
        dec=float(image.dec),
        radius_deg=float(radius_deg)
    ).filter(
        xtr_radius__range=(
            image.fov_bmin - radius_deg/2.,
            image.fov_bmin + radius_deg/2.
        )
    )

    if skyregions:
        # Get the closest in case of multiple matches.
        skyr = skyregions[0]
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
        logger.info("Created sky region %s", skyr)

    return skyr


def get_create_img_band(image: FitsImage) -> Band:
    """
    Return the existing Band row for the given FitsImage.
    An image is considered to belong to a band if its frequency is within some
    tolerance of the band's frequency.
    Returns a Band row or None if no matching band.

    Args:
        image: The image Django ORM object.

    Returns:
        The band Django ORM object.
    """
    # For now we match bands using the central frequency.
    # This assumes that every band has a unique frequency,
    # which is true for the data we've used so far.
    freq = int(image.freq_eff * 1.0e-6)
    freq_band = int(image.freq_bw * 1.0e-6)
    # TODO: refine the band query
    for band in Band.objects.all():
        diff = abs(freq - band.frequency) / float(band.frequency)
        if diff < 0.02:
            return band

    # no band has been found so create it
    band = Band(name=str(freq), frequency=freq, bandwidth=freq_band)
    logger.info("Adding new frequency band: %s", band)
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
        img_folder_name = image.name.replace(".", "_")
        measurements_path = os.path.join(
            settings.PIPELINE_WORKING_DIR,
            "images",
            img_folder_name,
            "measurements.parquet",
        )
        img = Image(band_id=band_id, measurements_path=measurements_path)

        # set the attributes and save the image,
        # by selecting only valid (not hidden) attributes
        # FYI attributs and/or method starting with _ are hidden
        # and with __ can't be modified/called
        for fld in img._meta.get_fields():
            if getattr(fld, "attname", None) and (
                getattr(image, fld.attname, None) is not None
            ):
                setattr(img, fld.attname, getattr(image, fld.attname))

        img.rms_median, img.rms_min, img.rms_max = get_rms_noise_image_values(
            img.noise_path
        )

        # get create the sky region and associate with image
        img.skyreg = get_create_skyreg(img)
        img.save()

    return (img, exists)


def get_create_p_run(
    name: str, path: str, description: str = None, user: User = None
) -> Tuple[Run, bool]:
    """
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
    """
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
        logger.info("Adding %s to image %s", pipeline_run, img.name)
        img.run.add(pipeline_run)

    if pipeline_run not in skyreg.run.all():
        logger.info("Adding %s to sky region %s", pipeline_run, skyreg)
        skyreg.run.add(pipeline_run)


def remove_duplicate_measurements(
    sources_df: pd.DataFrame, dup_lim: Optional[Angle] = None, ini_df: bool = False
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
    logger.debug("Cleaning duplicate sources from epoch...")

    if dup_lim is None:
        dup_lim = Angle(2.5 * u.arcsec)

    logger.debug("Using duplicate crossmatch radius of %.2f arcsec.", dup_lim.arcsec)

    # sort by the distance from the image centre so we know
    # that the first source is always the one to keep
    sources_df = sources_df.sort_values(by="dist_from_centre")

    sources_sc = SkyCoord(sources_df["ra"], sources_df["dec"], unit=(u.deg, u.deg))

    # perform search around sky to get all self matches
    idxc, idxcatalog, *_ = sources_sc.search_around_sky(sources_sc, dup_lim)

    # create df from results
    results = pd.DataFrame(
        data={
            "source_id": idxc,
            "match_id": idxcatalog,
            "source_image": sources_df.iloc[idxc]["image"].tolist(),
            "match_image": sources_df.iloc[idxcatalog]["image"].tolist(),
        }
    )

    # Drop those that are matched from the same image
    matching_image_mask = results["source_image"] != results["match_image"]

    results = results.loc[matching_image_mask].drop(
        ["source_image", "match_image"], axis=1
    )

    # create a pair column defining each pair ith index
    results["pair"] = results.apply(tuple, 1).apply(sorted).apply(tuple)
    # Drop the duplicate pairs (pairs are sorted so this works)
    results = results.drop_duplicates("pair")
    # No longer need pair
    results = results.drop("pair", axis=1)
    # Drop all self matches and we are left with those to drop
    # in the match id column.
    to_drop = results.loc[results["source_id"] != results["match_id"], "match_id"]
    # Get the index values from the ith values
    to_drop_indexes = sources_df.iloc[to_drop].index.values
    logger.debug("Dropping %i duplicate measurements.", to_drop_indexes.shape[0])
    # Drop them from sources
    sources_df = sources_df.drop(to_drop_indexes).sort_values(by="ra")

    # reset the source_df index
    sources_df = sources_df.reset_index(drop=True)

    del results

    return sources_df


def _load_measurements(
    image: Image, cols: List[str], ini_df: bool = False
) -> pd.DataFrame:
    """
    Load the measurements for an image from the parquet file.

    Args:
        image:
            The object representing the image for which to load the
            measurements.
        cols:
            The columns to load.
        ini_df:
            Boolean to indicate whether these sources are part of the initial
            source list creation for association. If 'True' the source ids are
            reset ready for the first iteration. Defaults to 'False'.

    Returns:
        The measurements of the image with some extra values set ready for
            association.
    """
    image_centre = SkyCoord(image.ra, image.dec, unit=(u.deg, u.deg))

    df = pd.read_parquet(image.measurements_path, columns=cols)
    df["image"] = image.name
    df["datetime"] = image.datetime
    # these are the first 'sources' if ini_df is True.
    df["source"] = df["id"].apply(lambda _: generate_shortuuid(UUID_LEN_SOURCE)) if ini_df else None
    df["ra_source"] = df["ra"]
    df["dec_source"] = df["dec"]
    df["d2d"] = 0.0
    df["dr"] = 0.0
    df["related"] = None

    sources_sc = SkyCoord(df["ra"], df["dec"], unit=(u.deg, u.deg))

    seps = sources_sc.separation(image_centre).degree
    df["dist_from_centre"] = seps

    del sources_sc
    del seps

    return df


def prep_skysrc_df(
    images: List[Image],
    perc_error: float = 0.0,
    duplicate_limit: Optional[Angle] = None,
    ini_df: bool = False,
) -> pd.DataFrame:
    """
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
    """
    cols = [
        "id",
        "ra",
        "uncertainty_ew",
        "weight_ew",
        "dec",
        "uncertainty_ns",
        "weight_ns",
        "flux_int",
        "flux_int_err",
        "flux_int_isl_ratio",
        "flux_peak",
        "flux_peak_err",
        "flux_peak_isl_ratio",
        "forced",
        "compactness",
        "has_siblings",
        "snr",
    ]

    df = _load_measurements(images[0], cols, ini_df=ini_df)

    if len(images) > 1:
        for img in images[1:]:
            df = pd.concat(
                [df, _load_measurements(img, cols, ini_df=ini_df)],
                ignore_index=True,
            )

        df = remove_duplicate_measurements(df, dup_lim=duplicate_limit, ini_df=ini_df)

    df = df.drop("dist_from_centre", axis=1)

    if perc_error != 0.0:
        logger.info("Correcting flux errors with config error setting...")
        for col in ["flux_int", "flux_peak"]:
            df[f"{col}_err"] = np.hypot(
                df[f"{col}_err"].values, perc_error * df[col].values
            )

    return df


def add_new_one_to_many_relations(
    row: pd.Series, advanced: bool = False, source_ids: Optional[pd.DataFrame] = None
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

    related_col = "related_skyc1" if advanced else "related"
    source_col = "source_skyc1" if advanced else "source"

    # this is the not_original case where the original source id is appended.
    if source_ids.empty:
        if isinstance(row[related_col], list):
            out = row[related_col]
            out.append(row[source_col])
        else:
            out = [
                row[source_col],
            ]

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
    out = row["new_relations"].copy()

    if isinstance(row["related_skyc1"], list):
        out += row["related_skyc1"].copy()

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
    return left.assign(key=1).merge(right.assign(key=1), on="key").drop("key", axis=1)


def get_eta_metric(grp: pd.DataFrame, out: pd.Series) -> pd.Series:
    """
    Calculates the eta variability metric of a source.
    Works on the grouped by dataframe using the fluxes
    of the associated measurements.

    Args:
        grp: The grouped by sources dataframe of the measurements containing all
            the flux and flux error information,
        out: A Pandas Series containing statistics for the current source

    Returns:
        The series `out` updated with calculated eta values.
    """
    n_meas = grp.shape[0]
    if n_meas == 1:
        out['eta_int'] = 0.
        out['eta_peak'] = 0.
        return out

    for suffix in ['int', 'peak']:
        weights = 1. / grp[f'flux_{suffix}_err'].values**2
        fluxes = grp[f'flux_{suffix}'].values
        out[f'eta_{suffix}'] = n_meas / (n_meas - 1) * (
            (weights * fluxes**2).mean() - (
                (weights * fluxes).mean()**2 / weights.mean()
            )
        )
    return out


def get_non_forced_metric(grp: pd.DataFrame, out: pd.Series) -> pd.Series:
    """
    Get metrics that require forced measurements to be filtered first.

    Args:
        grp: The grouped by sources dataframe of the measurements containing all
            the flux and flux error information,
        out: A Pandas Series containing statistics for the current source

    Returns:
        The series `out` updated with calculated statistics.
    """

    non_forced_sel = grp['forced'] != True
    out['wavg_ra'] = (
        grp.loc[non_forced_sel, 'interim_ew'].sum() /
        grp.loc[non_forced_sel, 'weight_ew'].sum()
    )
    out['wavg_dec'] = (
        grp.loc[non_forced_sel, 'interim_ns'].sum() /
        grp.loc[non_forced_sel, 'weight_ns'].sum()
    )
    out['avg_compactness'] = grp.loc[
        non_forced_sel, 'compactness'
    ].mean()
    out['min_snr'] = grp.loc[
        non_forced_sel, 'snr'
    ].min()
    out['max_snr'] = grp.loc[
        non_forced_sel, 'snr'
    ].max()
    out['wavg_uncertainty_ew'] = 1. / np.sqrt(grp.loc[non_forced_sel, 'weight_ew'].sum())
    out['wavg_uncertainty_ns'] = 1. / np.sqrt(grp.loc[non_forced_sel, 'weight_ns'].sum())

    return out


def get_related_list(grp: pd.DataFrame) -> list[str]:
    """Collect the unique set of lists from the column.

    Args:
        grp: The dataframe to collect the lists from.

    Returns:
        The unique set of lists.
    """

    lists = [list(i) if isinstance(i, np.ndarray)
                else ["NULL",] for i in grp['related']]

    the_list = list(set(chain.from_iterable(lists)))

    # Remove 'NULL' from the list if the length is > 1
    if len(the_list) > 1 and 'NULL' in the_list:
        the_list.remove('NULL')

    return the_list


def groupby_funcs(grp: pd.DataFrame) -> pd.Series:
    """
    Performs calculations on the unique sources to get the
    lightcurve properties. Works on the grouped by source
    dataframe.

    Args:
        grp: The current iteration dataframe of the grouped by sources
            dataframe.

    Returns:
        Pandas series containing the calculated metrics of the source.
    """
    out = {}
    out['img_list'] = grp['image'].values.tolist()
    out["n_meas_forced"] = grp["forced"].sum()
    out["n_meas"] = grp["id"].count()
    out["n_meas_sel"] = out["n_meas"] - out["n_meas_forced"]
    out["n_sibl"] = grp["has_siblings"].sum()

    out = get_non_forced_metric(grp, out)

    for col in ["avg_flux_int", "avg_flux_peak"]:
        out[col] = grp[col.split("_", 1)[1]].mean()
    for col in ["max_flux_peak", "max_flux_int"]:
        out[col] = grp[col.split("_", 1)[1]].max()
    for col in ["min_flux_peak", "min_flux_int"]:
        out[col] = grp[col.split("_", 1)[1]].min()
    for col in ["min_flux_peak_isl_ratio", "min_flux_int_isl_ratio"]:
        out[col] = grp[col.split("_", 1)[1]].min()

    v_int = grp["flux_int"].std() / out["avg_flux_int"]
    v_peak = grp["flux_peak"].std() / out["avg_flux_peak"]
    out["v_int"] = v_int if np.isfinite(v_int) else 0.
    out["v_peak"] = v_peak if np.isfinite(v_peak) else 0.

    out = get_eta_metric(grp, out)

    out["related_list"] = get_related_list(grp)
    out['n_rel'] = len(out['related_list'])

    return(pd.Series(out, name=grp.index.name))


def parallel_groupby(df: dd.DataFrame) -> dd.DataFrame:
    """
    Performs the parallel source dataframe operations to calculate the source
    metrics using Dask and returns the resulting dataframe.

    Args:
        df: The sources dataframe produced by the previous pipeline stages.

    Returns:
        The source dataframe with the calculated metric columns.
    """

    columns = [
        'id',
        'image',
        'forced',
        'has_siblings',
        'interim_ns',
        'interim_ew',
        'weight_ew',
        'weight_ns',
        'flux_int',
        'flux_peak',
        'flux_int_err',
        'flux_peak_err',
        'flux_peak_isl_ratio',
        'flux_int_isl_ratio',
        'related',
        'compactness',
        'snr',
    ]
    out_col_dtype = {
        "img_list": "O",
        "n_meas_forced": "i",
        "n_meas": "i",
        "n_meas_sel": "i",
        "n_sibl": "i",
        "wavg_ra": "f",
        "wavg_dec": "f",
        "avg_compactness": "f",
        "min_snr": "f",
        "max_snr": "f",
        "wavg_uncertainty_ew": "f",
        "wavg_uncertainty_ns": "f",
        "avg_flux_int": "f",
        "avg_flux_peak": "f",
        "max_flux_peak": "f",
        "max_flux_int": "f",
        "min_flux_peak": "f",
        "min_flux_int": "f",
        "min_flux_peak_isl_ratio": "f",
        "min_flux_int_isl_ratio": "f",
        "v_int": "f",
        "v_peak": "f",
        "eta_int": "f",
        "eta_peak": "f",
        "related_list": "O",
        "n_rel": "i",
    }

    groupby_df = df[columns]

    out = groupby_df.groupby('source').apply(groupby_funcs,
                                             meta=out_col_dtype)

    # For some reason this gets lost - stupid Dask.
    out.index = out.index.rename('source')

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
    grp = grp.sort_values(by="datetime")
    d["img_list"] = grp["image"].values.tolist()
    d["epoch_list"] = grp["epoch"].values.tolist()
    d["wavg_ra"] = grp["interim_ew"].sum() / grp["weight_ew"].sum()
    d["wavg_dec"] = grp["interim_ns"].sum() / grp["weight_ns"].sum()

    return pd.Series(d)


def parallel_groupby_coord(df: dd.DataFrame,) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate the weighted average RA and Dec of the sources.

    Produces two separate per-source DataFrames in a single Dask compute pass:

    * **coords_df** — lightweight numeric frame (one float per column) used
      for the AstroPy sky crossmatch: ``wavg_ra``, ``wavg_dec``.
    * **lists_df** — heavyweight frame holding Python list columns
      ``img_list`` and ``epoch_list``, only needed for the "missing image"
      computation in ``get_src_skyregion_merged_df``.  Keeping it separate
      means the large list objects are not in memory during the crossmatch.

    NOTE: Sergio had the idea to persist the dataframe result and keep it in the
    cluster. However since then the ideal image method uses the astropy match sky
    method which relies on being able to iloc the dataframe. This would be really
    difficult to do with a persisted dataframe. So it is computed.

    Args:
        df: The sources dataframe.

    Returns:
        Tuple of (coords_df, lists_df) — both indexed by source id.
    """

    coord_cols = [
        'source', 'interim_ew', 'weight_ew', 'interim_ns', 'weight_ns',
    ]
    coord_agg = {
        'interim_ew': 'sum',
        'weight_ew': 'sum',
        'interim_ns': 'sum',
        'weight_ns': 'sum',
    }
    coord_groups = df[coord_cols].groupby('source').agg(coord_agg)

    list_cols = ['source', 'image', 'epoch']
    list_agg = {'image': list, 'epoch': list}
    list_groups = df[list_cols].groupby('source').agg(list_agg)

    coords_raw, lists_raw = dask.compute(coord_groups, list_groups)

    coords_df = coords_raw
    coords_df['wavg_ra'] = coords_df['interim_ew'] / coords_df['weight_ew']
    coords_df['wavg_dec'] = coords_df['interim_ns'] / coords_df['weight_ns']
    coords_df = coords_df.drop(
        columns=['interim_ew', 'weight_ew', 'interim_ns', 'weight_ns']
    )

    lists_df = lists_raw.rename(columns={'image': 'img_list', 'epoch': 'epoch_list'})

    return coords_df, lists_df


def get_rms_noise_image_values(rms_path: str) -> Tuple[float, float, float]:
    """
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
    """
    logger.debug("Extracting Image RMS values from Noise file...")
    med_val = min_val = max_val = 0.0
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


def _build_compact_indices(
    sources_df: dd.DataFrame, images_df: pd.DataFrame,
) -> Tuple[dd.DataFrame, np.ndarray, int, pd.DataFrame, int]:
    """
    Replaces image name strings with compact int32 codes for the rest of
    `get_src_skyregion_merged_df`, and builds the per-image ideal-coverage
    frame used by the later crossmatch.

    Args:
        sources_df: The association step output, must have an 'image'
            column holding image name strings.
        images_df: All image objects for the run, with 'name', 'skyreg_id',
            'epoch' and 'datetime' columns.

    Returns:
        sources_df: With the 'image' column replaced by int32 codes.
        image_names: Array mapping int32 image code -> original image name.
        img_mult: Multiplier for the combined (source, image) key used by
            the vectorized "missing image" membership test.
        skyreg_img_df: Per-image ideal-coverage frame indexed by
            'skyreg_id', columns 'skyreg_img_list' (int32 image code),
            'skyreg_epoch' (int32) and 'skyreg_datetime' (int64, a sort key
            only, not a real datetime).
        epoch_mult: Multiplier for the combined (source, epoch) key.
    """
    # Compact int32 image code replaces the name string from here on;
    # image_names converts back to names in get_src_skyregion_merged_df.
    image_names = images_df["name"].to_numpy()
    name_to_idx = pd.Series(np.arange(len(image_names), dtype=np.int32), index=image_names)
    images_df = images_df.assign(name=np.arange(len(image_names), dtype=np.int32))
    sources_df["image"] = sources_df["image"].map(name_to_idx, meta=("image", "int32"))
    # Multiplier for the combined (source, image) key used by
    # _compute_missing_images' vectorized membership test.
    img_mult = len(image_names)

    skyreg_img_df = images_df[["skyreg_id", "name", "epoch", "datetime"]].rename(
        columns={
            "name": "skyreg_img_list",
            "epoch": "skyreg_epoch",
            "datetime": "skyreg_datetime",
        }
    )
    # int32/int64 downcasts halve these columns' cost across the large
    # crossmatch expansion in _crossmatch_sources_to_skyregions.
    skyreg_img_df["skyreg_epoch"] = skyreg_img_df["skyreg_epoch"].astype(np.int32)
    # Multiplier for the combined (source, epoch) key used by
    # _compute_missing_images; captured now while skyreg_img_df still holds
    # the full epoch universe.
    epoch_mult = int(skyreg_img_df["skyreg_epoch"].max()) + 1
    # Avoids boxing tz-aware Timestamps in the merges/sorts that follow;
    # only used to establish sort order, then dropped.
    skyreg_img_df["skyreg_datetime"] = skyreg_img_df["skyreg_datetime"].astype(np.int64)
    skyreg_img_df = skyreg_img_df.set_index("skyreg_id")

    return sources_df, image_names, img_mult, skyreg_img_df, epoch_mult


def _crossmatch_sources_to_skyregions(
    coords_df: pd.DataFrame, skyreg_df: pd.DataFrame, skyreg_img_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Crossmatches each source with every sky region within that region's
    extraction radius, then expands each match with every image belonging
    to the sky region -- i.e. the source's "ideal coverage" images/epochs.

    Args:
        coords_df: Per-source average coordinates, indexed by int32 source
            code. Only 'wavg_ra'/'wavg_dec' are used.
        skyreg_df: Sky regions of the run, with 'id', 'centre_ra',
            'centre_dec' and 'xtr_radius' columns.
        skyreg_img_df: Per-image ideal-coverage frame indexed by
            'skyreg_id', as returned by `_build_compact_indices`.

    Returns:
        Dataframe with one row per (source, sky region, ideal image) match
        and columns 'source', 'sep', 'skyreg_img_list', 'skyreg_epoch' and
        'skyreg_datetime'.
    """
    skyreg_df = skyreg_df[["id", "centre_ra", "centre_dec", "xtr_radius"]]

    # crossmatch sources with sky regions up to the max sky region radius
    skyreg_coords = SkyCoord(
        ra=skyreg_df.centre_ra.values, dec=skyreg_df.centre_dec.values, unit="deg"
    )
    srcs_coords = SkyCoord(
        ra=coords_df["wavg_ra"],
        dec=coords_df["wavg_dec"],
        unit="deg")
    skyreg_idx, srcs_idx, sep, _ = srcs_coords.search_around_sky(
        skyreg_coords, skyreg_df.xtr_radius.values * u.deg
    )
    skyreg_df = skyreg_df.drop(
        columns=[
            "centre_ra",
            "centre_dec",
            "xtr_radius"]).set_index("id")

    # Build the per-source ideal-images frame
    src_skyrg_df = pd.DataFrame(
        {
            "source": coords_df.iloc[srcs_idx].index,
            "sep": sep.to("deg").value.astype(np.float32),
        },
        index=skyreg_df.iloc[skyreg_idx].index,
    )

    src_skyrg_df = src_skyrg_df.join(skyreg_df, how="inner")
    src_skyrg_df = src_skyrg_df.join(skyreg_img_df, how="inner")

    src_skyrg_df = src_skyrg_df.reset_index(drop=True)

    del skyreg_df, skyreg_img_df
    gc.collect()

    return src_skyrg_df


def _dedupe_closest_skyregion_per_epoch(src_skyrg_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each (source, ideal epoch) pair, keeps only the closest-matching
    sky region (smallest separation), then sorts the result ready for the
    vectorized "missing image" computation that follows.

    Args:
        src_skyrg_df: Output of `_crossmatch_sources_to_skyregions`, one
            row per (source, sky region, ideal image) match, still with
            'sep' and 'skyreg_datetime' columns.

    Returns:
        One row per (source, ideal image), sorted by 'source' (stable
        sort, so each source's rows stay in the chronological order
        established via 'skyreg_datetime'), with 'sep' and
        'skyreg_datetime' dropped.
    """
    # Sort by (source, skyreg_epoch, sep) so every row sharing a
    # (source, skyreg_epoch) pair is contiguous, smallest sep first.
    src_skyrg_df.sort_values(
        ['source', 'skyreg_epoch', 'sep'], inplace=True
    )

    # Use numpy arrays to find the first row of each (source, skyreg_epoch) group
    # and drop the rest (keeping only the closest sky region per ideal epoch).
    source_arr = src_skyrg_df["source"].to_numpy()
    epoch_arr = src_skyrg_df["skyreg_epoch"].to_numpy()
    is_first = np.empty(len(source_arr), dtype=bool)
    is_first[0] = True
    is_first[1:] = (source_arr[1:] != source_arr[:-1]) | (epoch_arr[1:] != epoch_arr[:-1])

    del source_arr, epoch_arr

    src_skyrg_df = src_skyrg_df[is_first].drop(columns=["sep"])

    # Now sort by datetime int64 value
    src_skyrg_df.sort_values(by="skyreg_datetime", inplace=True)
    src_skyrg_df.drop(columns=["skyreg_datetime"], inplace=True)

    # Stable sort to preserve the chronological order of each source's rows
    src_skyrg_df.sort_values(by="source", kind="stable", inplace=True)

    return src_skyrg_df


def _isin_sorted(keys: np.ndarray, sorted_unique_ref: np.ndarray) -> np.ndarray:
    """
    Vectorized membership test of `keys` against a sorted, unique reference
    array, via binary search.

    Args:
        keys: Array of int64 keys to test.
        sorted_unique_ref: Sorted, unique int64 reference array.

    Returns:
        Boolean array, True where the corresponding key is present in
        `sorted_unique_ref`.
    """
    idx = np.searchsorted(sorted_unique_ref, keys)
    idx = np.clip(idx, 0, len(sorted_unique_ref) - 1)
    return (idx < len(sorted_unique_ref)) & (sorted_unique_ref[idx] == keys)


def _compute_missing_images(
    src_skyrg_df: pd.DataFrame, lists_df: pd.DataFrame, img_mult: int, epoch_mult: int,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    For each source, determines which ideal images/epochs were never
    actually observed, plus the source's first ideal ("primary") and first
    observed ("detection") image. Uses vectorized lookups.

    Args:
        src_skyrg_df: Output of `_dedupe_closest_skyregion_per_epoch`, one
            row per (source, ideal image), sorted by 'source'.
        lists_df: Per-source 'img_list'/'epoch_list' columns (the actually
            observed images/epochs), indexed by int32 source code.
        img_mult: Multiplier for the combined (source, image) key.
        epoch_mult: Multiplier for the combined (source, epoch) key.

    Returns:
        img_diff_series: Per-source list of missing ideal images, indexed
            by source, name 'img_diff'. Only sources with >=1 missing
            image are present.
        per_source_df: Per-source 'detection' (first observed image) and
            'in_primary' (whether the source was detected in its first
            ideal image) columns, indexed by source.
    """
    # For each (source, ideal image)/(source, ideal epoch) pair, test
    # whether it was ever actually observed by encoding the pair as one
    # combined int64 key (source * multiplier + value) and binary-searching
    # it (np.searchsorted) against a sorted array of observed keys.
    source_arr = src_skyrg_df["source"].to_numpy()
    skyreg_img_arr = src_skyrg_df["skyreg_img_list"].to_numpy()
    skyreg_epoch_arr = src_skyrg_df["skyreg_epoch"].to_numpy()
    del src_skyrg_df

    split_points = np.flatnonzero(np.diff(source_arr)) + 1
    group_start_idx = np.concatenate(([0], split_points))
    group_source = source_arr[group_start_idx]
    # "primary" = first (chronologically earliest) ideal image per source.
    primary_arr = skyreg_img_arr[group_start_idx]
    del group_start_idx

    # Long-format "observed" (source, image)/(source, epoch) pairs, built by
    # exploding the small (one row per source) img_list/epoch_list columns.
    obs_img_long = lists_df["img_list"].explode()
    obs_epoch_long = lists_df["epoch_list"].explode()
    obs_img_keys = np.unique(
        obs_img_long.index.to_numpy().astype(np.int64) * img_mult
        + obs_img_long.to_numpy().astype(np.int64)
    )
    obs_epoch_keys = np.unique(
        obs_epoch_long.index.to_numpy().astype(np.int64) * epoch_mult
        + obs_epoch_long.to_numpy().astype(np.int64)
    )
    del obs_img_long, obs_epoch_long

    ideal_img_key = source_arr.astype(np.int64) * img_mult + skyreg_img_arr.astype(np.int64)
    in_img_list = _isin_sorted(ideal_img_key, obs_img_keys)
    del ideal_img_key

    ideal_epoch_key = source_arr.astype(np.int64) * epoch_mult + skyreg_epoch_arr.astype(np.int64)
    in_epoch_list = _isin_sorted(ideal_epoch_key, obs_epoch_keys)
    del ideal_epoch_key, skyreg_epoch_arr

    missing_mask = ~in_img_list & ~in_epoch_list
    del in_img_list, in_epoch_list

    missing_source = source_arr[missing_mask]
    missing_img = skyreg_img_arr[missing_mask]
    del skyreg_img_arr, missing_mask

    # missing_source is a subset of the already (stable-)sorted source_arr,
    # so it's still sorted — group it straight back into per-source lists
    # without needing to re-sort.
    if len(missing_source) > 0:
        m_split_points = np.flatnonzero(np.diff(missing_source)) + 1
        m_group_source = missing_source[np.concatenate(([0], m_split_points))]
        img_diff_groups = np.split(missing_img, m_split_points)
    else:
        m_group_source = np.array([], dtype=source_arr.dtype)
        img_diff_groups = []
    del missing_source, missing_img, source_arr

    img_diff_series = pd.Series(
        img_diff_groups, index=pd.Index(m_group_source, name="source"), name="img_diff",
    )
    del m_group_source, img_diff_groups

    # "detection" = first (chronologically earliest) *observed* image per source.
    detection_series = lists_df["img_list"].str[0]
    primary_key = group_source.astype(np.int64) * img_mult + primary_arr.astype(np.int64)
    in_primary_arr = _isin_sorted(primary_key, obs_img_keys)
    del primary_key, obs_img_keys, obs_epoch_keys, primary_arr

    per_source_df = pd.DataFrame(
        {
            "detection": detection_series,
            "in_primary": pd.Series(in_primary_arr, index=pd.Index(group_source, name="source")),
        }
    )
    del detection_series, in_primary_arr, group_source

    return img_diff_series, per_source_df


def _explode_missing_images_to_dask(
    srcs_df: pd.DataFrame, image_names: np.ndarray, n_cpu: Optional[int],
) -> dd.DataFrame:
    """
    Converts the assembled per-source result to a Dask DataFrame and
    explodes 'img_diff' to one row per missing image, pre-computing the
    exploded form shared by the pipeline's steps #4 and #5.

    Args:
        srcs_df: One row per source, with 'wavg_ra', 'wavg_dec',
            'detection' (image name), 'in_primary' and 'img_diff',
            indexed by source.
        image_names: Array mapping int32 image code -> original image name.
        n_cpu: Number of available CPUs/workers, used to size the returned
            Dask DataFrame's partitions (via `calculate_n_partitions`). If
            None, partitions are sized on memory alone.

    Returns:
        Dask DataFrame with one row per (source, missing image) pair, as
        described in `get_src_skyregion_merged_df`.
    """
    base_npartitions = calculate_n_partitions(srcs_df, n_cpu=n_cpu, partition_size_mb=10)
    exploded_npartitions = max(n_cpu, base_npartitions) if n_cpu else base_npartitions

    srcs_df = dd.from_pandas(srcs_df, npartitions=exploded_npartitions)

    srcs_df = srcs_df.reset_index()[
        ["source", "wavg_ra", "wavg_dec", "img_diff", "detection", "in_primary"]
    ].explode("img_diff")

    def _convert_img_diff_names(partition: pd.DataFrame) -> pd.DataFrame:
        """Vectorized int32-code -> image-name lookup for one partition"""
        partition = partition.copy()
        partition["img_diff"] = image_names[partition["img_diff"].to_numpy().astype(np.int32)]
        return partition

    srcs_df = srcs_df.map_partitions(
        _convert_img_diff_names, meta=srcs_df._meta.assign(img_diff=pd.Series(dtype=object)),
    )

    return srcs_df

def get_src_skyregion_merged_df(
    sources_df: dd.DataFrame, images_df: pd.DataFrame, skyreg_df: pd.DataFrame
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

    sources_df, image_names, img_mult, skyreg_img_df, epoch_mult = _build_compact_indices(
        sources_df, images_df
    )


    coords_df, lists_df = parallel_groupby_coord(sources_df)
    # coords_df: wavg_ra/wavg_dec, used by _crossmatch_sources_to_skyregions.
    # lists_df: img_list/epoch_list, used by _compute_missing_images.
    del sources_df

    # Use compact int32 source code instead of the ShortUUID string for the
    # rest of this function; converted back on the final index only.
    source_ids = coords_df.index.to_numpy()
    source_to_idx = pd.Series(np.arange(len(source_ids), dtype=np.int32), index=source_ids)
    coords_df.index = np.arange(len(source_ids), dtype=np.int32)
    coords_df.index.name = "source"
    lists_df.index = lists_df.index.map(source_to_idx)
    lists_df.index.name = "source"

    # crossmatch sources with sky regions up to the max sky region radius
    src_skyrg_df = _crossmatch_sources_to_skyregions(coords_df, skyreg_df, skyreg_img_df)
    del skyreg_df

    # drop duplicates of the same source and sky region for the same epoch, keeping only the closest match
    src_skyrg_df = _dedupe_closest_skyregion_per_epoch(src_skyrg_df)

    # Compute missing images. per source (img_diff_series) and per source detection image
    img_diff_series, per_source_df = _compute_missing_images(
        src_skyrg_df, lists_df, img_mult, epoch_mult
    )
    # img_diff_series: per-source list of missing ideal images.
    # per_source_df: has per-source 'detection' (first observed image) and 
    # 'in_primary' (whether the source was detected in its first ideal image) columns.
    del src_skyrg_df, lists_df

    # Join coords with detection/in_primary, then inner-join img_diff — the
    # inner join filters down to only sources with >=1 missing image.
    srcs_df = coords_df.join(per_source_df, how="inner")
    del coords_df, per_source_df
    # Join img_diff — the inner join filters down to only sources with >=1 missing image.
    srcs_df = srcs_df.join(img_diff_series, how="inner")
    del img_diff_series

    # Convert int32 image codes back to the original image name strings for the final output.
    srcs_df["detection"] = image_names[srcs_df["detection"].to_numpy()]
    srcs_df.index = source_ids[srcs_df.index.to_numpy()]
    srcs_df.index.name = "source"

    # Convert srcs_df to a Dask DataFrame and explode 'img_diff' to one row per missing image.
    srcs_df = _explode_missing_images_to_dask(srcs_df, image_names, 1)

    logger.info("Ideal source coverage time: %.2f seconds", merged_timer.reset())

    return srcs_df


def _get_skyregion_relations(row: pd.Series, coords: SkyCoord, ids: int) -> List[int]:
    """
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
    """
    target = SkyCoord(row["centre_ra"], row["centre_dec"], unit=(u.deg, u.deg))

    seps = target.separation(coords)

    # place a slight buffer on the radius to make sure
    # any neighbouring fields are caught
    mask = seps <= row["xtr_radius"] * 1.1 * u.deg

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
            +-----------+-------------+--------------+--------------+
            |   id      |   centre_ra |   centre_dec |   xtr_radius |
            |-----------+-------------+--------------+--------------|
            |  ntEvPoTZ |    319.652  |    0.0030765 |      6.72488 |
            |  py5dA25B |    319.652  |   -6.2989    |      6.7401  |
            |  kbr4Tmyw |     21.8361 |  -73.121     |      7.24662 |
            +-----------+-------------+--------------+--------------+

    Returns:
        The sky region group of each skyregion id.
            +-----------+----------------+
            |           | skyreg_group |
            |-----------+--------------|
            |  py5dA25B |            1 |
            |  kbr4Tmyw |            1 |
            |  ntEvPoTZ |            2 |
            +-----------+--------------+
    """
    sr_coords = SkyCoord(df["centre_ra"], df["centre_dec"], unit=(u.deg, u.deg))

    df = df.set_index("id")

    results = df.apply(_get_skyregion_relations, args=(sr_coords, df.index), axis=1)

    skyreg_groups: Dict[int, List[Any]] = {}

    master_done = []  # keep track of all checked ids in master done

    for skyreg_id, neighbours in results.items():
        if skyreg_id not in master_done:
            local_done = []  # a local done list for the sky region group.
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

    skyreg_group_ids = pd.DataFrame.from_dict(skyreg_group_ids, orient="index").rename(
        columns={0: "skyreg_group"}
    )

    return skyreg_group_ids


def get_parallel_assoc_image_df(
    images: List[Image], skyregion_groups: pd.DataFrame, image_epochs: List
) -> pd.DataFrame:
    """
    Merge the sky region groups with the images and skyreg_ids.

    Args:
        images:
            A list of the Image objects.
        skyregion_groups:
            The sky region group of each skyregion id.
            +-----------+----------------+
            |           |   skyreg_group |
            |-----------+----------------|
            |  py5dA25B |              1 |
            |  kbr4Tmyw |              1 |
            |  ntEvPoTZ |              2 |
            +-----------+----------------+
        image_epochs:
            The epochs associated with each image.

    Returns:
        Dataframe containing the merged images and skyreg_id and skyreg_group
            (see source code for output format).
    """
    # Output format
    # +----+-------------------------------+-------------+----------------+
    # |    | image                         |   skyreg_id |   skyreg_group |
    # |----+-------------------------------+-------------+----------------|
    # |  0 | VAST_2118+00A.EPOCH01.I.fits  |    py5dA25B |              1 |
    # |  1 | VAST_2118-06A.EPOCH01.I.fits  |    kbr4Tmyw |              1 |
    # |  2 | VAST_0127-73A.EPOCH01.I.fits  |    ntEvPoTZ |              2 |
    # |  3 | VAST_2118-06A.EPOCH03x.I.fits |    kbr4Tmyw |              1 |
    # |  4 | VAST_2118-06A.EPOCH02.I.fits  |    kbr4Tmyw |              1 |
    # |  5 | VAST_2118-06A.EPOCH05x.I.fits |    kbr4Tmyw |              1 |
    # |  6 | VAST_2118-06A.EPOCH06x.I.fits |    kbr4Tmyw |              1 |
    # |  7 | VAST_0127-73A.EPOCH08.I.fits  |    ntEvPoTZ |              2 |
    # +----+-------------------------------+-------------+----------------+
    skyreg_ids = [str(i.skyreg_id) for i in images]
    image_names = [i.name for i in images]
    image_datetimes = [i.datetime for i in images]

    images_df = pd.DataFrame(
        {
            "image_dj": images,
            "skyreg_id": skyreg_ids,
            "image_name": image_names,
            "image_datetime": image_datetimes,
            "epoch": image_epochs,
        }
    )

    images_df = images_df.merge(
        skyregion_groups, how="left", left_on="skyreg_id", right_index=True
    )

    return images_df

def _process_measurements_file(m_file: str,
                               i: int,
                               out_dir: str,
                               associations: pd.DataFrame
                               ) -> None:
    """
    Process an individual measurements file and output as a single partition
    
    Args:
        m_file: Path to measurements file.
        i: Measurements file index.
        out_dir: Path to directory containing parquet partitions
        associations: Associations dataframe
    
    Returns:
        None
    """
    measurements = pd.read_parquet(m_file, engine='pyarrow')
    
    # Memory blows up and everything is slow if we try and do a full merge.
    # Instead, pull out the indices that are in both dfs and then merge those.
    associations_merge = associations[associations.index.isin(measurements['id'])]
    measurements = measurements.loc[
        measurements['id'].isin(associations_merge.index)
    ]
    
    measurements = optimise_numeric(measurements)
    measurements = measurements.merge(associations_merge, right_index=True, left_on='id', how="inner").rename(columns={'source_id': 'source'})
    
    partition_file = os.path.join(out_dir, f'part.{i}.parquet')
    measurements.to_parquet(partition_file, index=False)

def _repartition_measurements(in_file: str, out_file: str) -> None:
    """"
    Repartition the combined measurements file to be indexed by source id
    
    Args:
        in_file: path to parquet file to be repartitioned.
        out_file: path to parquet file to be written.
    Returns:
        None
    """

    # Using large datasets, so need to do the shuffling on disk
    with dc.set({'dataframe.shuffle.method': 'disk'}):
        dask_df = dd.read_parquet(in_file).repartition(partition_size="100MB")
        dask_df = dask_df.set_index('source', drop=True)
        dask_df = dask_df.repartition(partition_size="100MB")
        dask_df.to_parquet(out_file)

def create_measurements_parquet_file(p_run: Run, max_workers: Optional[int] = 10) -> None:
    """
    Creates a measurements.parquet file using the parquet outputs
    of a pipeline run.

    Args:
        p_run:
            Pipeline model instance.
        max_workers:
            Maximum number of workers to use when processing
            individual partitions. Defaults to 10.

    Returns:
        None
    """
    logger.info('Creating measurements.parquet for run %s.', p_run.name)
    
    p_run_path = p_run.path
    parquet_file = os.path.join(p_run_path, 'measurements.parquet')
    logger.info("Will write to final parquet file to %s.", parquet_file)
    
    processed_temp = tempfile.TemporaryDirectory()
    logger.debug("Writing temporary data to %s", processed_temp.name)

    images = pd.read_parquet(
        os.path.join(
            p_run_path,
            'images.parquet'
        ),
        columns=['measurements_path']
    )
    m_files = images['measurements_path'].tolist()
    del images

    m_files += glob.glob(os.path.join(
        p_run_path,
        'forced*.parquet'
    ))

    logger.debug("Will create measurements from %i files...", len(m_files))

    associations = dd.read_parquet(
        os.path.join(
            p_run_path,
            'associations.parquet'
        ),
        columns=['source_id'],
        index='meas_id'
    ).compute()
    
    logger.debug("Processing %d partitions with %d workers", len(m_files), max_workers)

    
    with Pool(max_workers) as pool:
        iterable_arg = zip(
            m_files,
            range(len(m_files)),
            itertools.repeat(processed_temp.name),
            itertools.repeat(associations),
        )
        pool.starmap(_process_measurements_file, iterable_arg)

    logger.debug("Repartitioning dataframe and saving")
    _repartition_measurements(processed_temp.name, parquet_file)

    logger.debug("Cleaning up temporary data")
    processed_temp.cleanup()
    logger.debug("Done.")


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
    parquets = glob.glob(os.path.join(p_run_path, "*.parquet"))

    for parquet in parquets:
        backup_name = parquet + '.bak'
        if os.path.exists(backup_name):
            delete_file_or_dir(backup_name)
        copy_file_or_dir(parquet, backup_name)


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
    config_name = "config.yaml"
    temp_config_name = "config_temp.yaml"

    shutil.copyfile(
        os.path.join(p_run_path, config_name),
        os.path.join(p_run_path, temp_config_name),
    )


def reconstruct_association_dfs(
    images_df_done: pd.DataFrame, previous_parquet_paths: Dict[str, str]
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
    prev_associations = pd.read_parquet(previous_parquet_paths["associations"])

    logger.debug(images_df_done)
    logger.debug(images_df_done['image_dj'])

    # Get the parquet paths from the image objects
    img_meas_paths = (
        images_df_done["image_dj"].apply(lambda x: x.measurements_path).to_list()
    )
    logger.debug(img_meas_paths)

    # Obtain the pipeline run path in order to fetch forced measurements.
    run_path = previous_parquet_paths["sources"].replace("sources.parquet.bak", "")

    # Get the forced measurement paths.
    img_fmeas_paths = []

    for i in images_df_done.image_name.values:
        forced_parquet = os.path.join(
            run_path, "forced_measurements_{}.parquet".format(i.replace(".", "_"))
        )
        if os.path.isfile(forced_parquet) or os.path.isdir(forced_parquet):
            img_fmeas_paths.append(forced_parquet)

    # Create union of paths.
    img_meas_paths += img_fmeas_paths

    # Define the columns that are required
    cols = [
        "id",
        "ra",
        "uncertainty_ew",
        "weight_ew",
        "dec",
        "uncertainty_ns",
        "weight_ns",
        "flux_int",
        "flux_int_err",
        "flux_int_isl_ratio",
        "flux_peak",
        "flux_peak_err",
        "flux_peak_isl_ratio",
        "forced",
        "compactness",
        "has_siblings",
        "snr",
        "image_id",
        "time",
    ]

    # Open all the parquets
    logger.debug("Opening all measurement parquet files to use in reconstruction...")
    measurements = pd.concat([pd.read_parquet(f, columns=cols) for f in img_meas_paths])

    # Create mask to drop measurements for epoch mode (epoch based mode).
    measurements_mask = measurements["id"].isin(prev_associations["meas_id"])
    measurements = measurements.loc[measurements_mask].set_index("id")

    # Set the index on images_df for faster merging.
    images_df_done["image_id"] = images_df_done["image_dj"].apply(lambda x: str(x.id)).values
    images_df_done = images_df_done.set_index("image_id")

    # Merge image information to measurements
    measurements = measurements.merge(
        images_df_done[["image_name", "epoch"]], left_on="image_id", right_index=True
    ).rename(columns={"image_name": "image"})

    # Drop any associations that are not used in this sky region group.
    associations_mask = prev_associations["meas_id"].isin(measurements.index.values)

    prev_associations = prev_associations.loc[associations_mask]

    # Merge measurements into the associations to form the sources_df.
    sources_df = prev_associations.merge(
        measurements, left_on="meas_id", right_index=True
    ).rename(
        columns={
            "source_id": "source",
            "time": "datetime",
            "meas_id": "id",
            "ra": "ra_source",
            "dec": "dec_source",
            "uncertainty_ew": "uncertainty_ew_source",
            "uncertainty_ns": "uncertainty_ns_source",
        }
    ).reset_index(drop=True)

    # Load up the previous unique sources.
    prev_sources = pd.read_parquet(
        previous_parquet_paths["sources"],
        columns=[
            "wavg_ra",
            "wavg_dec",
            "wavg_uncertainty_ew",
            "wavg_uncertainty_ns",
        ],
    )

    # Merge the wavg ra and dec to the sources_df - this is required to
    # create the skyc1_srcs below (but MUST be converted back to the source
    # ra and dec)
    sources_df = sources_df.merge(
        prev_sources, left_on="source", right_index=True
    ).rename(
        columns={
            "wavg_ra": "ra",
            "wavg_dec": "dec",
            "wavg_uncertainty_ew": "uncertainty_ew",
            "wavg_uncertainty_ns": "uncertainty_ns",
        }
    ).reset_index(drop=True)

    # Load the previous relations
    prev_relations = pd.read_parquet(previous_parquet_paths["relations"])

    # Form relation lists to merge in.
    prev_relations = pd.DataFrame(
        prev_relations.groupby("from_source_id")["to_source_id"].apply(
            lambda x: x.values.tolist()
        )
    ).rename(columns={"to_source_id": "related"})

    # Append the relations to only the last instance of each source
    # First get the ids of the sources
    relation_ids = sources_df[
        sources_df.source.isin(prev_relations.index.values)].drop_duplicates(
            'source', keep='last'
    ).index.values
    # Make sure we attach the correct source id
    source_ids = sources_df.loc[relation_ids]["source"].values
    sources_df['related'] = "NULL"
    sources_df["related"] = sources_df["related"].apply(lambda x: [x,])
    relations_to_update = prev_relations.loc[source_ids].to_numpy().copy()
    relations_to_update = np.reshape(relations_to_update, relations_to_update.shape[0])
    sources_df.loc[relation_ids, "related"] = relations_to_update

    # Reorder so we don't mess up the dask metas.
    sources_df = sources_df[
        [
            "id",
            "uncertainty_ew",
            "weight_ew",
            "uncertainty_ns",
            "weight_ns",
            "flux_int",
            "flux_int_err",
            "flux_int_isl_ratio",
            "flux_peak",
            "flux_peak_err",
            "flux_peak_isl_ratio",
            "forced",
            "compactness",
            "has_siblings",
            "snr",
            "image",
            "datetime",
            "source",
            "ra",
            "dec",
            "ra_source",
            "dec_source",
            "d2d",
            "dr",
            "related",
            "epoch",
            "uncertainty_ew_source",
            "uncertainty_ns_source",
        ]
    ]

    # Create the unique skyc1_srcs dataframe.
    skyc1_srcs = (
        sources_df[~sources_df["forced"]]
        .sort_values(by=["epoch", "id"])
        .drop("related", axis=1)
        .drop_duplicates("source")
    ).copy(deep=True)

    # Get relations into the skyc1_srcs (as we only keep the first instance
    # which does not have the relation information)
    skyc1_srcs = skyc1_srcs.merge(
        prev_relations, how="left", left_on="source", right_index=True
    )

    # Need to break the pointer relationship between the related sources (
    # deep=True copy does not truly copy mutable type objects)
    relation_mask = skyc1_srcs.related.notna()
    relation_vals = skyc1_srcs.loc[relation_mask, 'related'].to_list()
    new_relation_vals = np.array([x.copy() for x in relation_vals], dtype='object')
    skyc1_srcs.loc[relation_mask, 'related'] = new_relation_vals

    # Reorder so we don't mess up the dask metas.
    skyc1_srcs = skyc1_srcs[
        [
            "id",
            "ra",
            "uncertainty_ew",
            "weight_ew",
            "dec",
            "uncertainty_ns",
            "weight_ns",
            "flux_int",
            "flux_int_err",
            "flux_int_isl_ratio",
            "flux_peak",
            "flux_peak_err",
            "flux_peak_isl_ratio",
            "forced",
            "compactness",
            "has_siblings",
            "snr",
            "image",
            "datetime",
            "source",
            "ra_source",
            "dec_source",
            "d2d",
            "dr",
            "related",
            "epoch",
        ]
    ].reset_index(drop=True)

    # Finally move the source ra and dec back to the sources_df ra and dec
    # columns
    sources_df["ra"] = sources_df["ra_source"]
    sources_df["dec"] = sources_df["dec_source"]
    sources_df["uncertainty_ew"] = sources_df["uncertainty_ew_source"]
    sources_df["uncertainty_ns"] = sources_df["uncertainty_ns_source"]

    # Drop not needed columns for the sources_df.
    sources_df = sources_df.drop(
        ["uncertainty_ew_source", "uncertainty_ns_source"], axis=1
    ).reset_index(drop=True)

    return sources_df, skyc1_srcs


def write_parquets(
    images: List[Image], skyregions: List[SkyRegion], bands: List[Band], run_path: str
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
    images_df = images_df.drop("_state", axis=1)
    images_df.to_parquet(os.path.join(run_path, "images.parquet"), index=False)

    # write skyregions parquet file under pipeline run folder
    skyregs_df = pd.DataFrame(map(lambda x: x.__dict__, skyregions))
    skyregs_df = skyregs_df.drop("_state", axis=1)
    skyregs_df.to_parquet(os.path.join(run_path, "skyregions.parquet"), index=False)

    # write skyregions parquet file under pipeline run folder
    bands_df = pd.DataFrame(map(lambda x: x.__dict__, bands))
    bands_df = bands_df.drop("_state", axis=1)
    bands_df.to_parquet(os.path.join(run_path, "bands.parquet"), index=False)

    return skyregs_df


def get_total_memory_usage() -> float:
    """
    This function gets the current memory usage and returns a string.

    Returns:
        A float containing the current resource usage.
    """
    mem = psutil.virtual_memory()[3]  # resource usage in bytes
    mem = mem / 1024**3  # resource usage in GB

    return mem


def log_total_memory_usage() -> float:
    """
    This function gets the current memory usage and logs it.

    Returns:
        None
    """
    mem = get_total_memory_usage()

    logger.debug(f"Current memory usage: {mem:.3f}GB")


def get_df_memory_usage(df: pd.DataFrame) -> float:
    """
    This function calculates the memory usage of a pandas dataframe and
    logs it.

    Args:
        df: The pandas dataframe to calculate the memory usage of.

    Returns:
        The dataframe memory usage in MB
    """

    # Check if we are a Pandas or Dask dataframe
    mem = df.memory_usage(deep=True).sum()
    if type(df) is dd.DataFrame:
        mem = mem.compute()

    mem_usage_mb = mem / 1e6

    return mem_usage_mb
