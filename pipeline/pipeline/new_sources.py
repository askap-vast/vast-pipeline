import os
import logging

from pipeline.models import Image

import pandas as pd
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel

from ..utils.utils import StopWatch


logger = logging.getLogger(__name__)


def check_primary_image(row):
    if row.primary in row.img_list:
        return True
    else:
        return False


def get_image_rms_measurements(image, group):

    with fits.open(image) as hdul:
        header = hdul[0].header
        wcs = WCS(header, naxis=2)

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
        array_coords[0] > data.shape[0],
        array_coords[0] < 0
    )

    y_valid = np.logical_or(
        array_coords[1] > data.shape[1],
        array_coords[1] < 0
    )

    valid = ~np.logical_or(
        x_valid, y_valid
    )


    valid_indexes = group[valid].index.values
    not_valid_indexes = group[~valid].index.values

    rms_values = data[
        array_coords[0][valid],
        array_coords[1][valid]
    ]

    group.loc[
        valid_indexes, 'img_diff_true_rms'
    ] = rms_values.astype(np.float64) * 1.e3

    group.loc[
        not_valid_indexes, 'img_diff_true_rms'
    ] = np.nan

    return group


def new_sources(sources_df, missing_sources_df, p_run):
    """
    Process the new sources detected to see if they are
    valid.
    """

    timer = StopWatch()

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

    missing_sources_df['primary'] = [
        i[0] for i in missing_sources_df.skyreg_img_list
    ]

    missing_sources_df['detection'] = [
        i[0] for i in missing_sources_df.img_list
    ]

    missing_sources_df['in_primary'] = missing_sources_df[
        ['primary', 'img_list']
    ].apply(
        check_primary_image,
        axis=1
    )

    new_sources_df = missing_sources_df[
        missing_sources_df['in_primary'] == False
    ]

    new_sources_df = new_sources_df.drop(
        columns=['in_primary']
    )

    # Step 2 check if the previous sources would have actually been seen
    # i.e. are the previous images sensitive enough

    # save the index before exploding
    new_sources_df['source'] = new_sources_df.index

    new_sources_df = new_sources_df.reset_index(drop=True)

    # Explode now to avoid two loops below
    new_sources_df = new_sources_df.explode('img_diff')

    new_sources_df = new_sources_df.merge(
        images_df[['datetime']],
        left_on='detection',
        right_on='name'
    ).rename(columns={'datetime':'detection_time'})

    new_sources_df = new_sources_df.merge(
        images_df[[
            'datetime', 'rms_min', 'rms_median',
            'noise_path'
        ]],
        left_on='img_diff',
        right_on='name'
    ).rename(columns={
        'datetime':'img_diff_time',
        'rms_min': 'img_diff_rms_min',
        'rms_median': 'img_diff_rms_median',
        'noise_path': 'img_diff_rms_path'
    })

    new_sources_df = new_sources_df[
        new_sources_df.img_diff_time < new_sources_df.detection_time
    ].copy()

    # merge the detection fluxes in
    new_sources_df = pd.merge(
        new_sources_df, sources_df[['source', 'img', 'flux_peak']],
        left_on=['source', 'detection'], right_on=['source', 'img']
    ).drop(columns=['img'])

    new_sources_df['diff_sigma'] = (
        new_sources_df['flux_peak']
        / new_sources_df['img_diff_rms_min']
    )

    new_sources_df = new_sources_df[
        new_sources_df['diff_sigma'] >= 5.0
    ].copy()

    # Now have list of sources that should have been seen before given
    # previous images minimum rms values.

    # Current inaccurate sky regions may mean that the source
    # was in a previous 'NaN' area of the image. This needs to be
    # checked. Currently the check is done by filtering out of range
    # pixels. This could be done using MOCpy however this is reasonably
    # fast and the io of a MOC fits may take more time.

    # So these sources will be flagged as new sources, but we can also
    # make a guess of how signficant they are. For this the next step is
    # to measure the true rms at the source location.

    new_sources_df = new_sources_df.groupby(
        'img_diff_rms_path'
    ).apply(
        lambda x: get_image_rms_measurements(x.name, x)
    )

    # this removes those that are out of range
    values = {'img_diff_true_rms': 0.0}
    new_sources_df = new_sources_df.fillna(values)
    new_sources_df = new_sources_df[
        new_sources_df['img_diff_true_rms'] != 0
    ].reset_index(drop=True)

    new_sources_df['true_sigma'] = (
        new_sources_df['flux_peak']
        / new_sources_df['img_diff_true_rms']
    )

    # We only care about the highest true sigma
    new_sources_df = new_sources_df.sort_values(
        by=['source', 'img_diff_true_rms']
    )

    new_sources_df = new_sources_df.drop_duplicates('source')

    logger.info(
        'Total new source analysis time: %.2f seconds', timer.reset_init()
    )

    return new_sources_df
