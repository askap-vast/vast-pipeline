"""
This module contains utility functions used by the image ingestion section
of the pipeline.
"""

import logging
import numpy as np
import pandas as pd

from typing import Tuple, Union, Optional
from pathlib import Path
from astropy.io import fits


logger = logging.getLogger(__name__)


def on_sky_sep(ra_1, ra_2, dec_1, dec_2) -> float:
    """
    Simple on sky distance between two RA and Dec coordinates.
    Needed for fast calculation on dataframes as astropy is
    slow. All units are radians.

    Args:
        ra_1 (float): The right ascension of coodinate 1 (radians).
        ra_2 (float): The right ascension of coodinate 2 (radians).
        dec_1 (float): The declination of coodinate 1 (radians).
        dec_2 (float): The declination of coodinate 2 (radians).

    Returns:
        The on-sky separation distance between the two coodinates (radians).
    """
    separation = (
        np.sin(dec_1) * np.sin(dec_2) +
        np.cos(dec_1) * np.cos(dec_2) * np.cos(ra_1 - ra_2)
    )
    # fix errors on separation values over 1
    separation[separation > 1.] = 1.

    return np.arccos(separation)


def calc_error_radius(ra, ra_err, dec, dec_err) -> float:
    """
    Using the fitted errors from selavy, this function
    estimates the largest on sky angular size of the
    uncertainty. The four different combinations of the
    errors are analysed and the maximum is returned.
    Logic is taken from the TraP, where this is also
    used. Function has been vectorised for pandas. All inputs are in
    degrees.

    Args:
        ra (float): The right ascension of the coordinate (degrees).
        ra_err (float): The error associated with the ra value (degrees).
        dec (float): The declination of the coordinate (degrees).
        dec_err (float): The error associated with the declination
            value (degrees).

    Returns:
        The calculated error radius (degrees).
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

    seps = [
        np.rad2deg(on_sky_sep(
            ra_1,
            np.deg2rad(i),
            dec_1,
            np.deg2rad(j)
        )) for i, j in zip(ra_offsets, dec_offsets)
    ]

    seps = np.column_stack(seps)

    return np.amax(seps, 1)


def calc_condon_flux_errors(
    row: pd.Series,
    theta_B: float,
    theta_b: float,
    alpha_maj1: float = 2.5,
    alpha_min1: float = 0.5,
    alpha_maj2: float = 0.5,
    alpha_min2: float = 2.5,
    alpha_maj3: float = 1.5,
    alpha_min3: float = 1.5,
    clean_bias: float = 0.0,
    clean_bias_error: float = 0.0,
    frac_flux_cal_error: float = 0.0
) -> Tuple[float, float, float, float, float, float, float]:
    """
    The following code for this function taken from the TraP with a few
    modifications.

    Returns the errors on parameters from Gaussian fits according to
    the Condon (PASP 109, 166 (1997)) formulae.
    These formulae are not perfect, but we'll use them for the
    time being.  (See Refregier and Brown (astro-ph/9803279v1) for
    a more rigorous approach.) It also returns the corrected peak.
    The peak can be corrected for the overestimate due to the local
    noise gradient, but this is currently not used in the function.

    Args:
        row (pd.Series):
            The row containing the component information from the Selavy
            component catalogue.
        theta_B (float):
            The major axis size of the restoring beam of the image (degrees).
        theta_b (float):
            The minor axis size of the restoring beam of the image (degrees).
        alpha_maj1 (float):
            The alpha_M exponent value for x_0.
        alpha_min1 (float):
            The alpha_m exponent value for x_0.
        alpha_maj2 (float):
            The alpha_M exponent value for y_0.
        alpha_min2 (float):
            The alpha_m exponent value for y_0.
        alpha_maj3 (float):
            The alpha_M exponent value for the amplitude error.
        alpha_min3 (float):
            The alpha_m exponent value for the amplitude error.
        clean_bias (float):
            Clean bias value used in the peak flux correction (not currently
             used).
        clean_bias_error (float):
            The error of the clean bias value used in the peak flux correction
            (not currently used).
        frac_flux_cal_error (float):
            Flux calibration error value. (Unsure of exact meaning, refer to
            TraP).

    Returns:
        Peak flux error (Jy).
        Integrated flux error (Jy).
        Major axis error (deg).
        Minor axis error (deg).
        Position angle error (deg).
        Right ascension error (deg).
        Declination error (deg).
    """

    major = row.bmaj / 3600.  # degrees
    minor = row.bmin / 3600.  # degrees
    theta = np.deg2rad(row.pa)
    flux_peak = row['flux_peak']
    flux_int = row['flux_int']
    snr = row['snr']
    noise = row['local_rms']

    variables = [
        theta_B,
        theta_b,
        major,
        minor,
        flux_peak,
        flux_int,
        snr,
        noise
    ]

    # return 0 if the source is unrealistic. Should be rare
    # given that these sources are also filtered out before hand.
    if 0.0 in variables:
        logger.debug(variables)
        return 0., 0., 0., 0., 0., 0., 0.

    try:

        rho_sq1 = ((major * minor / (4. * theta_B * theta_b)) *
                   (1. + (theta_B / major)**2)**alpha_maj1 *
                   (1. + (theta_b / minor)**2)**alpha_min1 *
                   snr**2)
        rho_sq2 = ((major * minor / (4. * theta_B * theta_b)) *
                   (1. + (theta_B / major)**2)**alpha_maj2 *
                   (1. + (theta_b / minor)**2)**alpha_min2 *
                   snr**2)
        rho_sq3 = ((major * minor / (4. * theta_B * theta_b)) *
                   (1. + (theta_B / major)**2)**alpha_maj3 *
                   (1. + (theta_b / minor)**2)**alpha_min3 *
                   snr**2)

        rho1 = np.sqrt(rho_sq1)
        rho2 = np.sqrt(rho_sq2)
        rho3 = np.sqrt(rho_sq3)

        # here we change the TraP code slightly and base it
        # purely on Condon 97 and not the NVSS paper.
        denom1 = np.sqrt(4. * np.log(2.)) * rho1
        denom2 = np.sqrt(4. * np.log(2.)) * rho2

        # these are the 'xo' and 'y0' errors from Condon
        error_par_major = major / denom1
        error_par_minor = minor / denom2

        # ra and dec errors
        errorra = np.sqrt((error_par_major * np.sin(theta))**2 +
                          (error_par_minor * np.cos(theta))**2)
        errordec = np.sqrt((error_par_major * np.cos(theta))**2 +
                           (error_par_minor * np.sin(theta))**2)

        errormajor = np.sqrt(2) * major / rho1
        errorminor = np.sqrt(2) * minor / rho2

        if major > minor:
            errortheta = 2.0 * (major * minor / (major**2 - minor**2)) / rho2
        else:
            errortheta = np.pi
        if errortheta > np.pi:
            errortheta = np.pi

        # correction to flux peak not currently used
        # but might be in the future.
        # Do not remove!
        # flux_peak += -noise**2 / flux_peak + clean_bias

        errorpeaksq = ((frac_flux_cal_error * flux_peak)**2 +
                       clean_bias_error**2 +
                       2. * flux_peak**2 / rho_sq3)

        errorpeak = np.sqrt(errorpeaksq)

        help1 = (errormajor / major)**2
        help2 = (errorminor / minor)**2
        help3 = theta_B * theta_b / (major * minor)
        help4 = np.sqrt(errorpeaksq / flux_peak**2 + help3 * (help1 + help2))
        errorflux = np.abs(flux_int) * help4

        # need to return flux_peak if used.
        return errorpeak, errorflux, errormajor, errorminor, errortheta, errorra, errordec

    except Exception as e:
        logger.debug(
            "Error in the calculation of Condon errors for a source",
            exc_info=True)
        return 0., 0., 0., 0., 0., 0., 0.


def open_fits(fits_path: Union[str, Path], memmap: Optional[bool] = True):
    """
    This function opens both compressed and uncompressed fits files.

    Args:
        fits_path: Path to the fits file
        memmap: Open the fits file with mmap.

    Returns:
        HDUList loaded from the fits file
    """

    if isinstance(fits_path, Path):
        fits_path = str(fits_path)

    hdul = fits.open(fits_path, memmap=memmap)
    if hdul[0].data is None:
        return fits.HDUList(hdul[1:])
    else:
        return hdul
