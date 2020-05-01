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
        np.sin(dec_1) * np.sin(dec_2) +
        np.cos(dec_1) * np.cos(dec_2) * np.cos(ra_1 - ra_2)
    )

    return separation


def calc_error_radius(ra, ra_err, dec, dec_err):
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

    seps = [
        np.rad2deg(on_sky_sep(
            ra_1,
            np.deg2rad(i),
            dec_1,
            np.deg2rad(j)
        )) for i,j in zip(ra_offsets, dec_offsets)
    ]

    seps = np.column_stack(seps)

    return np.amax(seps, 1)


def calc_condon_flux_errors(row, theta_B, theta_b, alpha_maj1=2.5, alpha_min1=0.5,
                 alpha_maj2=0.5, alpha_min2=2.5, alpha_maj3=1.5, alpha_min3=1.5,
                 clean_bias=0.0, clean_bias_error=0.0, frac_flux_cal_error=0.0,):
    """
    The following code for this function taken from the TraP with a few
    modifications.

    Returns the errors on parameters from Gaussian fits according to
    the Condon (PASP 109, 166 (1997)) formulae.
    These formulae are not perfect, but we'll use them for the
    time being.  (See Refregier and Brown (astro-ph/9803279v1) for
    a more rigorous approach.) It also returns the corrected peak.
    The peak is corrected for the overestimate due to the local
    noise gradient.
    """

    major = row.bmaj / 3600.  # degrees
    minor = row.bmin / 3600.  # degrees
    theta = np.deg2rad(row.pa)
    flux_peak = row.flux_peak
    flux_int = row.flux_int
    snr = row.snr
    noise = row.local_rms

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
        rho_sq3 = ((major * minor / (4.* theta_B * theta_b)) *
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
        errorflux = np.abs(flux_int) * np.sqrt(errorpeaksq / flux_peak**2 + help3 * (help1 + help2))

        # need to return flux_peak if used.
        return errorpeak, errorflux, errormajor, errorminor, errortheta, errorra, errordec

    except exception as e:
        return 0., 0., 0., 0., 0., 0., 0.
