import logging

import pipeline.config as base_cfg

import numpy as np


logger = logging.getLogger(__name__)


def on_sky_sep(ra_1, ra_2, dec_1, dec_2):
    separation = np.arccos(
        (np.sin(dec_1) * np.sin(dec_2)) +
        (np.cos(dec_1) * np.cos(dec_2) * np.cos(ra_1 - ra_2))
    )

    return separation

def calculate_error_radius(ra, ra_err, dec, dec_err):

    ra_1 = np.deg2rad(ra)
    # ra_2 = np.deg2rad(ra + ra_err)

    dec_1 = np.deg2rad(dec)
    # dec_2 = np.deg2rad(dec + dec_err)

    ra_offsets = [
        (ra + ra_err),
        (ra + ra_err),
        (ra - ra_err),
        (ra - ra_err)
    ]

    dec_offsets = [
        (dec + dec_err),
        (dec - dec_err),
        (dec + dec_err),
        (dec - dec_err)
    ]

    seps = [np.rad2deg(on_sky_sep(
        ra_1,
        np.deg2rad(i),
        dec_1,
        np.deg2rad(j)
    )) for i,j in zip(ra_offsets, dec_offsets)]

    seps = np.column_stack(seps)

    return np.amax(seps, 1)

