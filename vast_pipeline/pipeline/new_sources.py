import logging
import pandas as pd
import numpy as np
import dask.dataframe as dd

from psutil import cpu_count
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from astropy.wcs.utils import (
    proj_plane_pixel_scales
)

from vast_pipeline.models import Image, Run
from vast_pipeline.utils.utils import StopWatch
from vast_pipeline.pipeline.utils import (
    get_df_memory_usage, log_total_memory_usage
)
from vast_pipeline.image.utils import open_fits


logger = logging.getLogger(__name__)


def check_primary_image(row: pd.Series) -> bool:
    """
    Checks if the primary image is in the image list.

    Args:
        row:
            Row of the missing_sources_df, need the keys 'primary' and
            'img_list'.

    Returns:
        True if the primary image is in the image list.
    """
    return row['primary'] in row['img_list']


def gen_array_coords_from_wcs(coords: SkyCoord, wcs: WCS) -> np.ndarray:
    """
    Converts SkyCoord coordinates to array coordinates given a wcs.

    Args:
        coords:
            The coordinates to convert.
        wcs:
            The WCS to use for the conversion.

    Returns:
        Array containing the x and y array coordinates of the input sky
            coordinates, e.g.:
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
) -> pd.DataFrame:
    """
    Take the coordinates provided from the group
    and measure the array cell value in the provided image.

    Args:
        group:
            The group of sources to measure in the image, requiring the
            columns: 'source', 'wavg_ra', 'wavg_dec' and 'img_diff_rms_path'.
        nbeam:
            The number of half beamwidths (BMAJ) away from the edge of the
            image or a NaN value that is acceptable.
        edge_buffer:
            Multiplicative factor applied to nbeam to act as a buffer.

    Returns:
        The group dataframe with the 'img_diff_true_rms' column added. The
            column will contain 'NaN' entires for sources that fail.
    """
    if len(group) == 0:
        # input dataframe is empty, nothing to do
        logger.debug(f"No image RMS measurements to get, returning")
        return group
    image = group.iloc[0]['img_diff_rms_path']

    logger.debug(f"{image} - num. meas. to get: {len(group)}")
    partition_mem = get_df_memory_usage(group)
    logger.debug(f"{image} - partition memory usage: {partition_mem}MB")

    get_rms_timer = StopWatch()

    with open_fits(image) as hdul:
        header = hdul[0].header
        wcs = WCS(header, naxis=2)
        data = hdul[0].data.squeeze()

    logger.debug(f"{image} - Time to load fits: {get_rms_timer.reset()}s")

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

    if group.empty:
        # early return if all sources failed range check
        logger.debug(
            'All sources out of range in new source rms measurement'
            f' for image {image}.'
        )
        group['img_diff_true_rms'] = np.nan
        return group

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
    for i, j in zip(array_coords[0], array_coords[1]):
        sl = tuple((
            slice(i - acceptable_no_nan_dist, i + acceptable_no_nan_dist),
            slice(j - acceptable_no_nan_dist, j + acceptable_no_nan_dist)
        ))
        if np.any(np.isnan(data[sl])):
            nan_valid.append(False)
        else:
            nan_valid.append(True)

    valid_indexes = group[nan_valid].index.values

    if np.any(nan_valid):
        # only run if there are actual values to measure
        rms_values = data[
            array_coords[0][nan_valid],
            array_coords[1][nan_valid]
        ]

        # not matched ones will be NaN.
        group.loc[
            valid_indexes, 'img_diff_true_rms'
        ] = rms_values.astype(np.float64) * 1.e3

    else:
        group['img_diff_true_rms'] = np.nan

    return group


def parallel_get_rms_measurements(
    df: pd.DataFrame, edge_buffer: float = 1.0
) -> pd.DataFrame:
    """
    Wrapper function to use 'get_image_rms_measurements'
    in parallel with Dask. nbeam is not an option here as that parameter
    is fixed in forced extraction and so is made sure to be fixed here to. This
    may change in the future.

    Args:
        df:
            The group of sources to measure in the images.
        edge_buffer:
            Multiplicative factor to be passed to the
            'get_image_rms_measurements' function.

    Returns:
        The original input dataframe with the 'img_diff_true_rms' column
            added. The column will contain 'NaN' entires for sources that fail.
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
) -> pd.DataFrame:
    """
    Processes the new sources detected to check that they are valid new
    sources. This involves checking to see that the source *should* be seen at
    all in     the images where it is not detected. For valid new sources the
    snr value the source would have in non-detected images is also calculated.

    Args:
        sources_df:
            The sources found from the association step.
        missing_sources_df:
            The dataframe containing the 'missing detections' for each source.
            See the source code comments for the layout of this dataframe.
        min_sigma:
            The minimum sigma value acceptable when compared to the minimum
            rms of the respective image.
        edge_buffer:
            Multiplicative factor to be passed to the
            'get_image_rms_measurements' function.
        p_run:
            The pipeline run.

    Returns:
        The original input dataframe with the 'img_diff_true_rms' column
            added. The column will contain 'NaN' entires for sources that fail.
            Columns:
                source - source id, int.
                img_list - list of images, List.
                wavg_ra - weighted average RA, float.
                wavg_dec - weighted average Dec, float.
                skyreg_img_list - list of sky regions of images in img_list, List.
                img_diff - The images missing from coverage, List.
                primary - What should be the first image, str.
                detection - The first detection image, str.
                detection_time - Datetime of detection, datetime.datetime.
                img_diff_time - Datetime of img_diff list, datetime.datetime.
                img_diff_rms_min - Minimum rms of diff images, float.
                img_diff_rms_median - Median rms of diff images, float.
                img_diff_rms_path - rms path of diff images, str.
                flux_peak - Flux peak of source (detection), float.
                diff_sigma - SNR in differnce images (compared to minimum), float.
                img_diff_true_rms - The true rms value from the diff images, float.
                new_high_sigma - peak flux / true rms value, float.
    """
    # Missing sources df layout
    # +----------+----------------------------------+-----------+------------+
    # |   source | img_list                         |   wavg_ra |   wavg_dec |
    # |----------+----------------------------------+-----------+------------+
    # |      278 | ['VAST_0127-73A.EPOCH01.I.fits'] |  22.2929  |   -71.8717 |
    # |      702 | ['VAST_0127-73A.EPOCH01.I.fits'] |  28.8125  |   -69.3547 |
    # |      776 | ['VAST_0127-73A.EPOCH01.I.fits'] |  31.8223  |   -70.4674 |
    # |      844 | ['VAST_0127-73A.EPOCH01.I.fits'] |  17.3152  |   -72.346  |
    # |      934 | ['VAST_0127-73A.EPOCH01.I.fits'] |   9.75754 |   -72.9629 |
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
    # ----------------------------------+
    #  img_diff                         |
    # ----------------------------------|
    #  ['VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] |
    #  ['VAST_0127-73A.EPOCH08.I.fits'] |
    # ----------------------------------+
    timer = StopWatch()
    debug_timer = StopWatch()

    logger.info("Starting new source analysis.")

    cols = [
        'id', 'name', 'noise_path', 'datetime',
        'rms_median', 'rms_min', 'rms_max',
    ]

    images_df = pd.DataFrame(list(
        Image.objects.filter(
            run=p_run
        ).values(*tuple(cols))
    )).set_index('name')

    # Get rid of sources that are not 'new', i.e. sources which the
    # first sky region image is not in the image list
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
    ).rename(columns={'datetime': 'detection_time'})

    new_sources_df = new_sources_df.merge(
        images_df[[
            'datetime', 'rms_min', 'rms_median',
            'noise_path'
        ]],
        left_on='img_diff',
        right_on='name',
        how='left'
    ).rename(columns={
        'datetime': 'img_diff_time',
        'rms_min': 'img_diff_rms_min',
        'rms_median': 'img_diff_rms_median',
        'noise_path': 'img_diff_rms_path'
    })

    logger.debug(f"Time to reset & merge image info into new_sources_df: {debug_timer.reset()}s")

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

    logger.debug(f"Time to merge detection fluxes into new_sources_df: {debug_timer.reset()}s")

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

    logger.debug(f"Time to do new_sources_df threshold calcs: {debug_timer.reset()}s")

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

    logger.debug("Getting rms measurements...")
    new_sources_df = parallel_get_rms_measurements(
        new_sources_df, edge_buffer=edge_buffer
    )
    logger.debug(f"Time to get rms measurements: {debug_timer.reset()}s")

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
    new_sources_df = (
        new_sources_df
        .drop_duplicates('source')
        .set_index('source')
        .rename(columns={'true_sigma': 'new_high_sigma'})
    )

    # moving forward only the new_high_sigma columns is needed, drop all
    # others.
    new_sources_df = new_sources_df[['new_high_sigma']]

    logger.debug(f"Time to to do final cleanup steps {debug_timer.reset()}s")

    logger.info(
        'Total new source analysis time: %.2f seconds', timer.reset_init()
    )

    return new_sources_df
