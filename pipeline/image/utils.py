import logging

import numpy as np


logger = logging.getLogger(__name__)


def on_sky_sep(ra_1, ra_2, dec_1, dec_2):
    """
    Simple on sky distance between two RA and Dec coordinates.
    Needed for fast calculation on dataframes as astropy is
    slow. All units are radians.
    """
    separation = np.arccos(
        (np.sin(dec_1) * np.sin(dec_2)) +
        (np.cos(dec_1) * np.cos(dec_2) * np.cos(ra_1 - ra_2))
    )

    return separation

def calculate_error_radius(ra, ra_err, dec, dec_err):
    """
    Using the fitted errors from selavy, this function
    estimates the largest on sky angular size of the
    uncertainty. The four different combinations of the
    errors are analysed and the maximum is returned.
    Logic is taken from the TraP, where this is also
    used. Function has been vectorised for pandas.
    """
    ra_1 = np.deg2rad(ra)
    dec_1 = np.deg2rad(dec)

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

