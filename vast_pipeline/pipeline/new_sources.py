import logging
import pandas as pd
import numpy as np
import dask.bag as db
import dask.dataframe as dd

from typing import Dict, Union

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import (
    proj_plane_pixel_scales
)

from vast_pipeline.models import Image, Run
from vast_pipeline.utils.utils import StopWatch
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


def extract_rms_data_from_img(
        image: str
) -> Dict[str, Union[np.ndarray, WCS, fits.Header]]:
    """Extracts the data, wcs and header from a fits image.

    Args:
        image: The path to the fits image.

    Returns:
        Dictionary containing the data, wcs and header of the image.
    """
    with open_fits(image) as hdul:
        header = hdul[0].header
        wcs = WCS(header, naxis=2)
        data = hdul[0].data.squeeze()

    return {'data': data, 'wcs': wcs, 'header': header}


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


def finalise_rms_calcs(
    rms: Dict[str, Union[np.ndarray, WCS, fits.Header]],
    coords: SkyCoord,
    df: pd.DataFrame,
    nbeam: int = 3,
    edge_buffer: float = 1.0
) -> pd.DataFrame:
    """Obtains the rms values from the image at the given coordinates.

    Checks are made prior to the extraction:
        - The coordinates are not within 3 half BMAJ widths of the image.
        - The coordinates are not within the user specified edge buffer.
        - The coordinates are not within the NaN region of the image.

    Args:
        rms: The dictionary containing the image data, wcs and header.
        coords: The SkyCoord object containing the coordinates.
        df: The dataframe containing the source information.
        nbeam: The number of beams to use for the edge buffer.
        edge_buffer: The multiplicative factor to use for the edge buffer.

    Returns:
        Dataframe containing the 'img_diff_true_rms' column and the source_id
            as the index.
    """
    # Here we mimic the forced fits behaviour,
    # sources within 3 half BMAJ widths of the image
    # edges are ignored. The user buffer is also
    # applied for consistency.
    pixelscale = (
        proj_plane_pixel_scales(rms["wcs"])[1] * u.deg
    ).to(u.arcsec)

    bmaj = rms["header"]["BMAJ"] * u.deg

    npix = round(
        (nbeam / 2. * bmaj.to('arcsec') /
         pixelscale).value
    )

    npix = int(round(npix * edge_buffer))

    array_coords = rms['wcs'].world_to_array_index(coords)
    array_coords = np.array([
        np.array(array_coords[0]),
        np.array(array_coords[1]),
    ])

    # check for pixel wrapping
    x_valid = np.logical_or(
        array_coords[0] >= (rms['data'].shape[0] - npix),
        array_coords[0] < npix
    )

    y_valid = np.logical_or(
        array_coords[1] >= (rms['data'].shape[1] - npix),
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
        if np.any(np.isnan(rms["data"][sl])):
            nan_valid.append(False)
        else:
            nan_valid.append(True)

    valid[valid] = nan_valid

    # create the column data, not matched ones will be NaN.
    rms_values = np.full(valid.shape, np.NaN)
    logger.debug(f"Df shape: {df.shape}")
    logger.debug(f"Valid shape: {valid.shape}")
    logger.debug(f"Array coords shape: {array_coords.shape}")
    if np.any(valid):
        rms_values[valid] = rms['data'][
            array_coords[0][valid],
            array_coords[1][valid]
        ].astype(np.float64) * 1.e3

    # copy the df and create the rms column
    df_out = df.copy()  # dask doesn't like to modify inputs in place
    df_out['img_diff_true_rms'] = rms_values

    return df_out


def parallel_get_rms_measurements(
        df: dd.core.DataFrame,
        nbeam: int = 3,
        edge_buffer: float = 1.0
    ) -> dd.core.DataFrame:
    """
    Wrapper function to use 'get_image_rms_measurements'
    in parallel with Dask.
    """
    # Use the Dask bag backend to work on different image files
    # calculate first the unique image_diff then create the bag
    uniq_img_diff = (
        df['img_diff_rms_path'].unique()
        .compute()
        .tolist()
    )
    nr_uniq_img = len(uniq_img_diff)
    # map the extract function to the bag to get data from images
    img_data_bags = (
        db.from_sequence(uniq_img_diff, npartitions=nr_uniq_img)
        .map(extract_rms_data_from_img)
    )

    # generate bags with dataframes for each unique image_diff
    cols = ['img_diff_rms_path', 'source', 'wavg_ra', 'wavg_dec']
    df_bags = []
    for elem in uniq_img_diff:
        df_bags.append(df.loc[df['img_diff_rms_path'] == elem, cols])
    df_bags = dd.compute(*df_bags)
    df_bags = db.from_sequence(df_bags, npartitions=nr_uniq_img)

    # map the get_coord_array and column selection function
    arr_coords_bags = df_bags.map(get_coord_array)
    col_sel_bags = df_bags.map(lambda onedf: onedf[['source']])

    # combine the bags and apply final operations, this will create a list
    # of pandas dataframes
    out = (
        db.zip(img_data_bags, arr_coords_bags, col_sel_bags)
        .map(lambda tup: finalise_rms_calcs(
            *tup,
            edge_buffer=edge_buffer,
            nbeam=nbeam
        ))
        # tranform dfs to list of dicts
        .map(lambda onedf: onedf.to_dict(orient='records'))
        .flatten()
        .to_dataframe()
    )

    df = df.merge(
        out[['source', 'img_diff_true_rms']],
        left_on='source', right_on='source',
        how='left'
    )

    return df.persist()


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
    new_sources_df = (
        new_sources_df.set_index('true_sigma')
        .map_partitions(lambda x: x.sort_index())
        .drop_duplicates('source')
        .reset_index()
        .rename(columns={'true_sigma': 'new_high_sigma'})
        .set_index('source')
     )

    # moving forward only the new_high_sigma columns is needed, drop all
    # others.
    new_sources_df = new_sources_df[['new_high_sigma']]

    logger.info(
        'Total new source analysis time: %.2f seconds', timer.reset_init()
    )

    return new_sources_df.persist()
