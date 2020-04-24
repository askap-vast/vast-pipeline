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


def calc_condon_flux_errors(row, theta_n):
    """
    Calculate the parameter errors for a fitted source
    using the description of Condon'97
    All parameters are assigned errors, assuming that all params were fit.
    If some params were held fixed then these errors are overestimated.
    Parameters
    ----------
    source : :class:`AegeanTools.models.SimpleSource`
        The source which was fit.
    theta_n : float or None
        A measure of the beam sampling. (See Condon'97).
    psf : :class:`AegeanTools.wcs_helpers.Beam`
        The psf at the location of the source.
    Returns
    -------
    None
    """

    # indices for the calculation or rho
    alphas = {'amp': (3. / 2, 3. / 2),
              'major': (5. / 2, 1. / 2),
              'xo': (5. / 2, 1. / 2),
              'minor': (1. / 2, 5. / 2),
              'yo': (1. / 2, 5. / 2),
              'pa': (1. / 2, 5. / 2)}

    major = row.bmaj / 3600.  # degrees
    minor = row.bmin / 3600.  # degrees
    phi = np.radians(row.pa)  # radians
    # if psf is not None:
    #     beam = psf.get_beam(source.ra, source.dec)
    #     if beam is not None:
    #         theta_n = np.hypot(beam.a, beam.b)
    #         print(beam, theta_n)

    if theta_n is None:
        return 0., 0.

    smoothing = major * minor / (theta_n ** 2)
    factor1 = (1 + (major / theta_n))
    factor2 = (1 + (minor / theta_n))
    snr = row.snr
    # calculation of rho2 depends on the parameter being used so we lambda this into a function
    rho2 = lambda x: smoothing / 4 * factor1 ** alphas[x][0] * factor2 ** alphas[x][1] * snr ** 2

    err_peak_flux = (row.flux_peak / 1.e3) * np.sqrt(2 / rho2('amp'))
    err_a = major * np.sqrt(2 / rho2('major')) * 3600.  # arcsec
    err_b = minor * np.sqrt(2 / rho2('minor')) * 3600.  # arcsec

    err_xo2 = 2. / rho2('xo') * major ** 2 / (8 * np.log(2))  # Condon'97 eq 21
    err_yo2 = 2. / rho2('yo') * minor ** 2 / (8 * np.log(2))
    err_ra = np.sqrt(err_xo2 * np.sin(phi)**2 + err_yo2 * np.cos(phi)**2)
    err_dec = np.sqrt(err_xo2 * np.cos(phi)**2 + err_yo2 * np.sin(phi)**2)

    if (major == 0) or (minor == 0):
        source.err_pa = -1.
    # if major/minor are very similar then we should not be able to figure out what pa is.
    elif abs(2 * (major-minor) / (major+minor)) < 0.01:
        err_pa = -1.
    else:
        err_pa = np.degrees(np.sqrt(4 / rho2('pa')) * (major * minor / (major ** 2 - minor ** 2)))

    # integrated flux error
    err2 = ((err_peak_flux) / (row.flux_peak / 1.e3)) ** 2
    err2 += (theta_n ** 2 / (major * minor)) * ((err_a / (major * 3600.) ) ** 2 + (err_b / (minor * 3600.) ) ** 2)
    err_int_flux = (row.flux_int / 1.e3) * np.sqrt(err2)

    return err_peak_flux , err_int_flux

