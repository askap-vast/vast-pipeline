import logging
import pandas as pd
import numpy as np
import dask.dataframe as dd

from typing import Dict, Union

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import (
    proj_plane_pixel_scales
)
from dask.delayed import delayed
from dask.distributed import wait

from vast_pipeline.models import Image, Run

from vast_pipeline.utils.utils import StopWatch
from vast_pipeline.pipeline.utils import get_df_memory_usage
from vast_pipeline.image.utils import open_fits
from vast_pipeline.daskmanager.manager import get_io_semaphore


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
    array_coords = np.array(wcs.world_to_array_index(coords), dtype=np.int32)

    return array_coords


def get_coord_array(df: pd.DataFrame) -> SkyCoord:
    """Get the skycoords from a given dataframe.

    Expects the dataframe to have the columns 'wavg_ra' and 'wavg_dec'.

    Args:
        df: The dataframe containing the coordinates.

    Returns:
        The SkyCoord object containing the coordinates.
    """
    coords = SkyCoord(
        df['wavg_ra'].values,
        df['wavg_dec'].values,
        unit=(u.deg, u.deg)
    )

    return coords


def extract_data_from_img(image: str) -> Dict[str, Union[np.ndarray, WCS, fits.Header]]:
    """Extracts the data, wcs and header from a fits image.

    Args:
        image: The path to the fits image.

    Returns:
        Dictionary containing the data, wcs and header of the image.
    """

    with get_io_semaphore():
        with open_fits(image) as hdul:
            header = hdul[0].header
            bmaj = header['bmaj']
            wcs = WCS(header, naxis=2)
            data = hdul[0].data.squeeze().astype(np.float32)

    return {'data': data, 'wcs': wcs, 'bmaj': bmaj}


def get_image_rms_measurements(
    df: pd.DataFrame, nbeam: int = 3, edge_buffer: float = 1.0
) -> pd.DataFrame:
    """
    Take the coordinates provided in df and measure the array
    cell values in the provided image.

    Args:
        df:
            The group of sources to measure in the image, requiring the
            columns: 'source', 'wavg_ra', 'wavg_dec' and 'img_diff_rms_path'.
        nbeam:
            The number of half beamwidths (BMAJ) away from the edge of the
            image or a NaN value that is acceptable.
        edge_buffer:
            Multiplicative factor applied to nbeam to act as a buffer.

    Returns:
        A dataframe containing 'source' and 'true_rms' columns.
        'true_rms' will contain 'NaN' entires for sources that fail.
    """

    if len(df) == 0:
        # input dataframe is empty, nothing to do
        logger.debug(f"No image RMS measurements to get, returning")
        return pd.DataFrame({'source': [], 'true_sigma': []})

    # Ensure there is only one image in the df
    image = df['img_diff_rms_path'].unique()
    assert len(image) == 1
    image = image[0]

    logger.debug("%s - num. meas. to get: %d", image, len(df))
    partition_mem = get_df_memory_usage(df)
    logger.debug("%s - partition memory usage: %.3fMB", image, partition_mem)

    get_rms_timer = StopWatch()
    # Get image data from df
    image_data = extract_data_from_img(image)
    logger.debug("%s - Time to load fits: %.3fs", image, get_rms_timer.reset())

    # Get coordinates from df
    coords = get_coord_array(df)

    # Here we mimic the forced fits behaviour,
    # sources within 3 half BMAJ widths of the image
    # edges are ignored. The user buffer is also
    # applied for consistency.
    pixelscale = (
        proj_plane_pixel_scales(image_data["wcs"])[1] * u.deg
    ).to(u.arcsec)

    bmaj = image_data["bmaj"] * u.deg

    npix = round(
        (nbeam / 2. * bmaj.to('arcsec') /
         pixelscale).value
    )

    npix = int(round(npix * edge_buffer))
    array_coords = gen_array_coords_from_wcs(coords, image_data['wcs'])

    # check for pixel wrapping
    x_valid = np.logical_or(
        array_coords[0] >= (image_data['data'].shape[0] - npix),
        array_coords[0] < npix
    )

    y_valid = np.logical_or(
        array_coords[1] >= (image_data['data'].shape[1] - npix),
        array_coords[1] < npix
    )

    valid = ~np.logical_or(
        x_valid, y_valid
    )

    # Now we also need to check proximity to NaN values
    # as forced fits may also drop these values
    acceptable_no_nan_dist = int(
        round(bmaj.to('arcsec').value / 2. / pixelscale.value)
    )

    nan_valid = []

    # Get slices of each source and check NaN is not included.
    for i,j in zip(array_coords[0][valid], array_coords[1][valid]):
        sl = tuple((
            slice(i - acceptable_no_nan_dist, i + acceptable_no_nan_dist),
            slice(j - acceptable_no_nan_dist, j + acceptable_no_nan_dist)
        ))
        if np.any(np.isnan(image_data["data"][sl])):
            nan_valid.append(False)
        else:
            nan_valid.append(True)

    valid[valid] = nan_valid

    # Create the column data, not matched ones will be NaN.
    rms_values = np.zeros_like(valid, dtype=np.float32)

    if np.any(valid):
        rms_values[valid] = image_data['data'][
            array_coords[0][valid],
            array_coords[1][valid]
        ].astype(np.float32) * 1.e3

    # Get the columns of returned DataFrame
    rms_mask = rms_values > 0.
    source = df['source'].values[rms_mask]
    true_sigma = df['flux_peak'].values[rms_mask]/rms_values[rms_mask]

    return pd.DataFrame({'source': source, 'true_sigma': true_sigma})


def parallel_get_new_high_sigma(
    df: dd.DataFrame, edge_buffer: float = 1.0,
) -> pd.DataFrame:
    """
    Wrapper function to use 'get_image_rms_measurements' in parallel with Dask
    and calculate the new high sigma. nbeam is not an option here as that
    parameter is fixed in forced extraction and so is made sure to be fixed
    here too. This may change in the future.

    Args:
        df:
            The group of sources to measure in the images.
        edge_buffer:
            Multiplicative factor to be passed to the
            'get_image_rms_measurements' function.

    Returns:
        A DataFrame indexed by source id and containing a single 'new_high_sigma' column.
        The column will contain 'NaN' entires for sources that fail.
    """

    # Get a list of input images.
    uniq_img_diff = (
        df['img_diff_rms_path'].unique()
        .compute()
        .to_list()
    )

    cols = ['img_diff_rms_path', 'flux_peak', 'source', 'wavg_ra', 'wavg_dec']
    
    # Generate a delayed dataframe of sources for each image in uniq_img_diff
    df_generator = lambda element, df: df[df['img_diff_rms_path'] == element]
    df_per_img_rms = [delayed(df_generator)(elem, df[cols]) for elem in uniq_img_diff]

    # Do the rms calculations per rms image only using the subset of workers for IO
    out = [delayed(get_image_rms_measurements)(rms_df, edge_buffer=edge_buffer) for rms_df in df_per_img_rms]
    out = dd.from_delayed(out).persist()

    # Remove duplicate sources and only keep high sigma
    out = out.sort_values('true_sigma', ascending=True) \
             .drop_duplicates('source', keep='last') \
             .rename(columns={'true_sigma': 'new_high_sigma'}) \
             .set_index('source') \
             .persist()

    # Wait for delayed computations to finish.
    wait(out)
    del df_per_img_rms

    return out


def new_sources(
    sources_df: dd.DataFrame,
    missing_sources_df: dd.DataFrame,
    min_sigma: float,
    edge_buffer: float,
    p_run: Run,
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
        A DataFrame indexed by source id and containing a single 'new_high_sigma' column.
        The column will contain 'NaN' entires for sources that fail.
    """
    # Missing sources df layout
    # +----------------+----------------------------------+-----------+------------+
    # |   source       | img_list                         |   wavg_ra |   wavg_dec |
    # |----------------+----------------------------------+-----------+------------+
    # | wWafAHKP2QdGFg | ['VAST_0127-73A.EPOCH01.I.fits'] |  22.2929  |   -71.8717 |
    # | gCWGDZvMarcEoW | ['VAST_0127-73A.EPOCH01.I.fits'] |  28.8125  |   -69.3547 |
    # | Nbz4XwjpwX7gXa | ['VAST_0127-73A.EPOCH01.I.fits'] |  31.8223  |   -70.4674 |
    # | RV9KsSoiumCMU3 | ['VAST_0127-73A.EPOCH01.I.fits'] |  17.3152  |   -72.346  |
    # | PwEnpyALZXGHk8 | ['VAST_0127-73A.EPOCH01.I.fits'] |   9.75754 |   -72.9629 |
    # +----------------+----------------------------------+-----------+------------+
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

    # Select only those images that come before the detection image
    # in time.
    new_sources_df = new_sources_df[
        new_sources_df.img_diff_time < new_sources_df.detection_time
    ]

    # merge the detection fluxes in
    new_sources_df = new_sources_df.merge(
        sources_df[['source', 'image', 'flux_peak']],
        left_on=['source', 'detection'], right_on=['source', 'image'],
        how='left'
    ).drop(columns=['image'])

    # NOTE: Need to persist here since dask loses futures after all the previous
    # merges. Ideally this should be removed and we only persist at the end of
    # new_sources.
    new_sources_df = new_sources_df.persist()
    wait(new_sources_df)

    logger.debug("Time to reset and merge image info and merge detection "
                 "fluxes into new_sources_df: "
                 f"{debug_timer.reset()}s"
                 )

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
    # the source location and calculate the corresponding S/N

    logger.debug("Getting new_high_sigma measurements...")
    new_sources_df = parallel_get_new_high_sigma(
        new_sources_df, edge_buffer=edge_buffer
    )

    logger.debug(f"Time to get rms measurements: {debug_timer.reset()}s")

    logger.info(
        'Total new source analysis time: %.2f seconds', timer.reset_init()
    )

    return new_sources_df
