import os
import logging
import pandas as pd
import numpy as np
import dask.dataframe as dd

from psutil import cpu_count
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import (
    skycoord_to_pixel,
    proj_plane_pixel_scales
)

from vast_pipeline.models import Image, Run
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


def check_primary_image(row):
    """
    Checks if the primary image is in the image list.

    Parameters
    ----------
    row : pd.Series
        Row of the missing_sources_df, need the keys 'primary' and 'img_list'.

    Returns
    -------
    bool : bool
        True if the primary image is in the image list.
    """
    return row['primary'] in row['img_list']


def gen_array_coords_from_wcs(coords: SkyCoord, wcs: WCS):
    """
    Converts SkyCoord coordinates to array coordinates given a wcs.

    Parameters
    ----------
    coords : SkyCoord
        The coordinates to convert.
    wcs : WCS
        The WCS to use for the conversion.

    Returns
    -------
    array_coords : numpy.ndarray
        Array containing the x and y array coordinates of the input sky
        coordinates.
        np.array([[x1, x2, x3], [y1, y2, y3]])
    """
    array_coords = wcs.world_to_array_index(coords)
    array_coords = np.array([
        np.array(array_coords[0]),
        np.array(array_coords[1]),
    ])

    return array_coords


def get_image_rms_measurements(
    group: pd.DataFrame, nbeam: int = 3, edge_buffer: float = 1.0
):
    """
    Take the coordinates provided from the group
    and measure the array cell value in the provided image.

    Parameters
    ----------
    group : pd.DataFrame
        The group of sources to measure in the image, requiring the columns:
        'source', 'wavg_ra', 'wavg_dec' and 'img_diff_rms_path'.
    nbeam : int
        The number of half beamwidths (BMAJ) away from the edge of the image or
        a NaN value that is acceptable.
    edge_buffer : float
        Multiplicative factor applied to nbeam to act as a buffer.

    Returns
    -------
    group : pd.DataFrame
        The group dataframe with the 'img_diff_true_rms' column added. The
        column will contain 'NaN' entires for sources that fail.
    """
    image = group.iloc[0]['img_diff_rms_path']

    with fits.open(image) as hdul:
        header = hdul[0].header
        wcs = WCS(header, naxis=2)

        try:
            # ASKAP tile images
            data = hdul[0].data[0, 0, :, :]
        except Exception as e:
            # ASKAP SWarp images
            data = hdul[0].data

    # Here we mimic the forced fits behaviour,
    # sources within 3 half BMAJ widths of the image
    # edges are ignored. The user buffer is also
    # applied for consistency.
    pixelscale = (
        proj_plane_pixel_scales(wcs)[1] * u.deg
    ).to(u.arcsec)

    bmaj = header["BMAJ"] * u.deg

    npix = round(
        (nbeam / 2. * bmaj.to('arcsec') /
        pixelscale).value
    )

    npix = int(round(npix * edge_buffer))

    coords = SkyCoord(
        group.wavg_ra, group.wavg_dec, unit=(u.deg, u.deg)
    )

    array_coords = gen_array_coords_from_wcs(coords, wcs)

    # check for pixel wrapping
    x_valid = np.logical_or(
        array_coords[0] >= (data.shape[0] - npix),
        array_coords[0] < npix
    )

    y_valid = np.logical_or(
        array_coords[1] >= (data.shape[1] - npix),
        array_coords[1] < npix
    )

    valid = ~np.logical_or(
        x_valid, y_valid
    )

    valid_indexes = group[valid].index.values

    group = group.loc[valid_indexes]

    # Now we also need to check proximity to NaN values
    # as forced fits may also drop these values
    coords = SkyCoord(
        group.wavg_ra, group.wavg_dec, unit=(u.deg, u.deg)
    )

    array_coords = gen_array_coords_from_wcs(coords, wcs)

    acceptable_no_nan_dist = int(
        round(bmaj.to('arcsec').value / 2. / pixelscale.value)
    )

    nan_valid = []

    # Get slices of each source and check NaN is not included.
    for i,j in zip(array_coords[0], array_coords[1]):
        sl = tuple((
            slice(i - acceptable_no_nan_dist, i + acceptable_no_nan_dist),
            slice(j - acceptable_no_nan_dist, j + acceptable_no_nan_dist)
        ))
        if np.any(np.isnan(data[sl])):
            nan_valid.append(False)
        else:
            nan_valid.append(True)

    valid_indexes = group[nan_valid].index.values

    rms_values = data[
        array_coords[0][nan_valid],
        array_coords[1][nan_valid]
    ]

    # not matched ones will be NaN.
    group.loc[
        valid_indexes, 'img_diff_true_rms'
    ] = rms_values.astype(np.float64) * 1.e3

    return group


def parallel_get_rms_measurements(df: pd.DataFrame, edge_buffer: float = 1.0):
    """
    Wrapper function to use 'get_image_rms_measurements'
    in parallel with Dask. nbeam is not an option here as that parameter
    is fixed in forced extraction and so is made sure to be fixed here to. This
    may change in the future.

    Parameters
    ----------
    df : pd.DataFrame
        The group of sources to measure in the images.
    edge_buffer : float
        Multiplicative factor to be passed to the 'get_image_rms_measurements'
        function.

    Returns
    -------
    df : pd.DataFrame
        The original input dataframe with the 'img_diff_true_rms' column added.
        The column will contain 'NaN' entires for sources that fail.
    """
    out = df[[
        'source', 'wavg_ra', 'wavg_dec',
        'img_diff_rms_path'
    ]]

    col_dtype = {
        'source': 'i',
        'wavg_ra': 'f',
        'wavg_dec': 'f',
        'img_diff_rms_path': 'U',
        'img_diff_true_rms': 'f',
    }

    n_cpu = cpu_count() - 1

    out = (
        dd.from_pandas(out, n_cpu)
        .groupby('img_diff_rms_path')
        .apply(
            get_image_rms_measurements,
            edge_buffer=edge_buffer,
            meta=col_dtype
        ).compute(num_workers=n_cpu, scheduler='processes')
    )

    df = df.merge(
        out[['source', 'img_diff_true_rms']],
        left_on='source', right_on='source',
        how='left'
    )

    return df


def new_sources(
    sources_df: pd.DataFrame, missing_sources_df: pd.DataFrame,
    min_sigma: float, edge_buffer: float, p_run: Run
):
    """
    Processes the new sources detected to check that they are valid new sources.
    This involves checking to see that the source *should* be seen at all in
    the images where it is not detected. For valid new sources the snr
    value the source would have in non-detected images is also calculated.

    Parameters
    ----------
    source_df : pd.DataFrame
        The sources found from the association step.
    missing_sources_df : pd.DataFrame
        The dataframe containing the 'missing detections' for each source.
    +----------+----------------------------------+-----------+------------+
    |   source | img_list                         |   wavg_ra |   wavg_dec |
    |----------+----------------------------------+-----------+------------+
    |      278 | ['VAST_0127-73A.EPOCH01.I.fits'] |  22.2929  |   -71.8717 |
    |      702 | ['VAST_0127-73A.EPOCH01.I.fits'] |  28.8125  |   -69.3547 |
    |      776 | ['VAST_0127-73A.EPOCH01.I.fits'] |  31.8223  |   -70.4674 |
    |      844 | ['VAST_0127-73A.EPOCH01.I.fits'] |  17.3152  |   -72.346  |
    |      934 | ['VAST_0127-73A.EPOCH01.I.fits'] |   9.75754 |   -72.9629 |
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
    ----------------------------------+
     img_diff                         |
    ----------------------------------|
     ['VAST_0127-73A.EPOCH08.I.fits'] |
     ['VAST_0127-73A.EPOCH08.I.fits'] |
     ['VAST_0127-73A.EPOCH08.I.fits'] |
     ['VAST_0127-73A.EPOCH08.I.fits'] |
     ['VAST_0127-73A.EPOCH08.I.fits'] |
    ----------------------------------+
    min_sigma : float
        The minimum sigma value acceptable when compared to the minimum rms of
        the respective image.
    edge_buffer : float
        Multiplicative factor to be passed to the 'get_image_rms_measurements'
        function.
    p_run : Run
        The pipeline run.

    Returns
    -------
    new_sources_df : pd.DataFrame
        The original input dataframe with the 'img_diff_true_rms' column added.
        The column will contain 'NaN' entires for sources that fail.
        Columns:
            source - source id.
            img_list - list of images.
            wavg_ra - weighted average RA.
            wavg_dec - weighted average Dec.
            skyreg_img_list - list of sky regions of images in img_list.
            img_diff - The images missing from coverage.
            primary - What should be the first image.
            detection - The first detection image.
            detection_time - Datetime of detection.
            img_diff_time - Difference in times from detection and diff.
            img_diff_rms_min - Minimum rms of diff images.
            img_diff_rms_median - Median rms of diff images.
            img_diff_rms_path - rms path of diff images.
            flux_peak - Flux peak of source (detection).
            diff_sigma - SNR in differnce images (compared to minimum).
            img_diff_true_rms - The true rms value from the diff images.
            new_high_sigma - peak flux / true rms value.
    """
    timer = StopWatch()

    logger.info("Starting new source analysis.")

    cols = [
        'id', 'name', 'noise_path', 'datetime',
        'rms_median', 'rms_min', 'rms_max'
    ]

    images_df = pd.DataFrame(list(
        Image.objects.filter(
            run=p_run
        ).values(*tuple(cols))
    )).set_index('name')

    # Get rid of sources that are not 'new', i.e. sources which the
    # first sky region image is not in the image list

    missing_sources_df['primary'] = missing_sources_df[
        'skyreg_img_list'
    ].apply(lambda x: x[0])

    missing_sources_df['detection'] = missing_sources_df[
        'img_list'
    ].apply(lambda x: x[0])

    missing_sources_df['in_primary'] = missing_sources_df[
        ['primary', 'img_list']
    ].apply(
        check_primary_image,
        axis=1
    )

    new_sources_df = missing_sources_df[
        missing_sources_df['in_primary'] == False
    ].drop(
        columns=['in_primary']
    )

    # Check if the previous sources would have actually been seen
    # i.e. are the previous images sensitive enough

    # save the index before exploding
    new_sources_df = new_sources_df.reset_index()

    # Explode now to avoid two loops below
    new_sources_df = new_sources_df.explode('img_diff')

    # Merge the respective image information to the df
    new_sources_df = new_sources_df.merge(
        images_df[['datetime']],
        left_on='detection',
        right_on='name',
        how='left'
    ).rename(columns={'datetime':'detection_time'})

    new_sources_df = new_sources_df.merge(
        images_df[[
            'datetime', 'rms_min', 'rms_median',
            'noise_path'
        ]],
        left_on='img_diff',
        right_on='name',
        how='left'
    ).rename(columns={
        'datetime':'img_diff_time',
        'rms_min': 'img_diff_rms_min',
        'rms_median': 'img_diff_rms_median',
        'noise_path': 'img_diff_rms_path'
    })

    # Select only those images that come before the detection image
    # in time.
    new_sources_df = new_sources_df[
        new_sources_df.img_diff_time < new_sources_df.detection_time
    ]

    # merge the detection fluxes in
    new_sources_df = pd.merge(
        new_sources_df, sources_df[['source', 'image', 'flux_peak']],
        left_on=['source', 'detection'], right_on=['source', 'image'],
        how='left'
    ).drop(columns=['image'])

    # calculate the sigma of the source if it was placed in the
    # minimum rms region of the previous images
    new_sources_df['diff_sigma'] = (
        new_sources_df['flux_peak'].values
        / new_sources_df['img_diff_rms_min'].values
    )

    # keep those that are above the user specified threshold
    new_sources_df = new_sources_df.loc[
        new_sources_df['diff_sigma'] >= min_sigma
    ]

    # Now have list of sources that should have been seen before given
    # previous images minimum rms values.

    # Current inaccurate sky regions may mean that the source
    # was in a previous 'NaN' area of the image. This needs to be
    # checked. Currently the check is done by filtering out of range
    # pixels once the values have been obtained (below).
    # This could be done using MOCpy however this is reasonably
    # fast and the io of a MOC fits may take more time.

    # So these sources will be flagged as new sources, but we can also
    # make a guess of how signficant they are. For this the next step is
    # to measure the true rms at the source location.

    # measure the actual rms in the previous images at
    # the source location.
    new_sources_df = parallel_get_rms_measurements(
        new_sources_df, edge_buffer=edge_buffer
    )

    # this removes those that are out of range
    new_sources_df['img_diff_true_rms'] = (
        new_sources_df['img_diff_true_rms'].fillna(0.)
    )
    new_sources_df = new_sources_df[
        new_sources_df['img_diff_true_rms'] != 0
    ]

    # calculate the true sigma
    new_sources_df['true_sigma'] = (
        new_sources_df['flux_peak'].values
        / new_sources_df['img_diff_true_rms'].values
    )

    # We only care about the highest true sigma
    new_sources_df = new_sources_df.sort_values(
        by=['source', 'true_sigma']
    )

    # keep only the highest for each source, rename for the daatabase
    new_sources_df = new_sources_df.drop_duplicates('source').rename(
        columns={'true_sigma':'new_high_sigma'}
    )

    logger.info(
        'Total new source analysis time: %.2f seconds', timer.reset_init()
    )

    return new_sources_df.set_index('source')
