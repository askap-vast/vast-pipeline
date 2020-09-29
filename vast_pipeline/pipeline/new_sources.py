import os
import logging
import pandas as pd
import numpy as np
import dask.dataframe as dd
import dask.bag as db

from psutil import cpu_count
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel
from typing import Dict

from vast_pipeline.models import Image, Run
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


def check_primary_image(row: pd.Series) -> bool:
    return row['primary'] in row['img_list']


def extract_rms_data_from_img(image: str) -> Dict:
    with fits.open(image) as hdul:
            wcs = WCS(hdul[0].header, naxis=2)
            try:
                # ASKAP tile images
                data = hdul[0].data[0, 0, :, :]
            except Exception as e:
                # ASKAP SWarp images
                data = hdul[0].data

    return {'data': data, 'wcs': wcs}


def get_coord_array(df: pd.DataFrame) -> SkyCoord:
    coords = SkyCoord(
        df['wavg_ra'].values,
        df['wavg_dec'].values,
        unit=(u.deg, u.deg)
    )

    return coords


def finalise_rms_calcs(rms: Dict, coords: np.array,
    df: pd.DataFrame) -> pd.DataFrame:
    """
    Take the coordinates provided from the group
    and measure the array value in the provided image.
    """
    array_coords = rms['wcs'].world_to_array_index(coords)
    array_coords = np.array([
        np.array(array_coords[0]),
        np.array(array_coords[1]),
    ])

    # check for pixel wrapping
    x_valid = np.logical_or(
        array_coords[0] >= rms['data'].shape[0],
        array_coords[0] < 0
    )

    y_valid = np.logical_or(
        array_coords[1] >= rms['data'].shape[1],
        array_coords[1] < 0
    )

    # calculated the mask for indexes
    valid = ~np.logical_or(x_valid, y_valid)

    # create the column data, not matched ones will be NaN.
    rms_values = np.full(valid.shape, np.NaN)
    rms_values[valid] = rms['data'][
        array_coords[0][valid],
        array_coords[1][valid]
    ].astype(np.float64) * 1.e3

    # copy the df and create the rms column
    df_out = df.copy()# dask doesn't like to modify inputs in place
    df_out['img_diff_true_rms'] = rms_values

    return df_out


def parallel_get_rms_measurements(df: dd.core.DataFrame) -> dd.core.DataFrame:
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
        .map(lambda tup: finalise_rms_calcs(*tup))
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


def new_sources(sources_df: dd.core.DataFrame,
    missing_sources_df: dd.core.DataFrame, min_sigma: float, p_run: Run
    ) -> dd.core.DataFrame:
    """
    Process the new sources detected to see if they are
    valid.
    """

    # timer = StopWatch()

    logger.info('Starting new source analysis.')

    cols = [
        'name', 'noise_path', 'datetime',
        'rms_median', 'rms_min', 'rms_max'
    ]

    images_df = pd.DataFrame(list(
        Image.objects.filter(run=p_run)
        .values(*tuple(cols))
    )).set_index('name')

    # Get rid of sources that are not 'new', i.e. sources which the
    # first sky region image is not in the image list

    missing_sources_df['primary'] = missing_sources_df[
        'skyreg_img_list'
    ].apply(lambda x: x[0], meta=str)

    missing_sources_df['detection'] = missing_sources_df[
        'img_list'
    ].apply(lambda x: x[0], meta=str)

    missing_sources_df['in_primary'] = missing_sources_df[
        ['primary', 'img_list']
    ].apply(check_primary_image, axis=1, meta=bool)

    new_sources_df = missing_sources_df[
        missing_sources_df['in_primary'] == False
    ].drop(columns=['in_primary'])
    del missing_sources_df

    # Check if the previous sources would have actually been seen
    # i.e. are the previous images sensitive enough

    # save the index and explode now to avoid two loops below
    # Merge the respective image information to the df
    new_sources_df = (
        new_sources_df.reset_index()
        .explode('img_diff')
        .merge(
            images_df[['datetime']],
            left_on='detection',
            right_on='name',
            how='left'
        )
        .rename(columns={'datetime': 'detection_time'})
    # )
    # new_sources_df = (
        # new_sources_df.merge(
        .merge(
            images_df,
            left_on='img_diff',
            right_on='name',
            how='left'
        )
        .rename(columns={
            'datetime': 'img_diff_time',
            'rms_min': 'img_diff_rms_min',
            'rms_median': 'img_diff_rms_median',
            'noise_path': 'img_diff_rms_path'
        })
    )

    # Select only those images that come before the detection image
    # in time.
    new_sources_df = new_sources_df[
        new_sources_df.img_diff_time < new_sources_df.detection_time
    ]

    # merge the detection fluxes in
    new_sources_df = (
        new_sources_df.merge(
            sources_df,
            left_on=['source', 'detection'],
            right_on=['source', 'image'],
            how='left'
        )
        .drop(columns=['image'])
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
    # the source location.
    new_sources_df = parallel_get_rms_measurements(new_sources_df)

    # this removes those that are out of range
    new_sources_df['img_diff_true_rms'] = new_sources_df['img_diff_true_rms'].fillna(0.)
    new_sources_df = new_sources_df[
        new_sources_df['img_diff_true_rms'] != 0
    ]

    # calculate the true sigma
    new_sources_df['true_sigma'] = (
        new_sources_df['flux_peak'].values
        / new_sources_df['img_diff_true_rms'].values
    )

    # We only care about the highest true sigma: once way of selecting the rows
    # with the highest sigma is to set 'true_sigma' as the index column and sort
    # the partitions then drop duplicated based on the 'source' column, rename
    # column and set the index to be 'source'
    new_sources_df = (
        new_sources_df.set_index('true_sigma')
        .map_partitions(lambda x: x.sort_index())
        .drop_duplicates('source')
        .reset_index()
        .rename(columns={'true_sigma': 'new_high_sigma'})
        .set_index('source')
    )

    # # keep only the highest for each source, rename for the daatabase
    # new_sources_df = new_sources_df.drop_duplicates('source').rename(
    #     columns={'true_sigma':'new_high_sigma'}
    # )

    # logger.info(
    #     'Total new source analysis time: %.2f seconds', timer.reset_init()
    # )

    return new_sources_df.persist()
