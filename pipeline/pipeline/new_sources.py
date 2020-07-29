import os
import logging

from pipeline.models import Image

import pandas as pd
import numpy as np
import dask.dataframe as dd
from psutil import cpu_count
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel

from pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


def check_primary_image(row):
    return row['primary'] in row['img_list']

def get_image_rms_measurements(group):
    """
    Take the coordinates provided from the group
    and measure the array value in the provided image.
    """
    image = group.iloc[0]['img_diff_rms_path']

    with fits.open(image) as hdul:
        wcs = WCS(hdul[0].header, naxis=2)

        try:
            # ASKAP tile images
            data = hdul[0].data[0, 0, :, :]
        except Exception as e:
            # ASKAP SWarp images
            data = hdul[0].data

    coords = SkyCoord(
        group.wavg_ra, group.wavg_dec, unit=(u.deg, u.deg)
    )

    array_coords = wcs.world_to_array_index(coords)
    array_coords = np.array([
        np.array(array_coords[0]),
        np.array(array_coords[1]),
    ])

    # check for pixel wrapping
    x_valid = np.logical_or(
        array_coords[0] >= data.shape[0],
        array_coords[0] < 0
    )

    y_valid = np.logical_or(
        array_coords[1] >= data.shape[1],
        array_coords[1] < 0
    )

    valid = ~np.logical_or(
        x_valid, y_valid
    )

    valid_indexes = group[valid].index.values

    rms_values = data[
        array_coords[0][valid],
        array_coords[1][valid]
    ]

    # not matched ones will be NaN.
    group.loc[
        valid_indexes, 'img_diff_true_rms'
    ] = rms_values.astype(np.float64) * 1.e3

    return group

def parallel_get_rms_measurements(df):
    """
    Wrapper function to use 'get_image_rms_measurements'
    in parallel with Dask.
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
            meta=col_dtype
        ).compute(num_workers=n_cpu, scheduler='processes')
    )

    df = df.merge(
        out[['source', 'img_diff_true_rms']],
        left_on='source', right_on='source',
        how='left'
    )

    return df

def new_sources(sources_df, missing_sources_df, min_sigma, p_run):
    """
    Process the new sources detected to see if they are
    valid.
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
        new_sources_df
    )

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
