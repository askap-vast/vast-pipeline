import os
import logging
import math as m
from astroquery.ned import Ned
from astroquery.simbad import Simbad
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord

from datetime import datetime


logger = logging.getLogger(__name__)


class StopWatch():
    """A simple stopwatch to simplify timing code"""

    def __init__(self):
        self._init = datetime.now()
        self._last = self._init

    def reset(self):
        """
        Reset the stopwatch and return the time since last reset (seconds)
        """
        now = datetime.now()
        diff = (now - self._last).total_seconds()
        self._last = now
        return diff

    def reset_init(self):
        """
        Reset the stopwatch and return the total time since initialisation
        """
        now = datetime.now()
        diff = (now - self._init).total_seconds()
        self._last = self._init = now
        return diff


def check_read_write_perm(path, perm='W'):
    """
    assess the file permission on a path
    """
    assert perm in ('R', 'W', 'X'), 'permission not supported'

    perm_map = {'R': os.R_OK, 'W': os.W_OK, 'X': os.X_OK}
    if not os.access(path, perm_map[perm]):
        msg = f'permission not valid on folder: {path}'
        logger.error(msg)
        raise IOError(msg)

    pass


def deg2sex(deg):
    """ Converts angle in degrees to sexagesimal notation
    Returns tuple containing (sign, (degrees, minutes & seconds))
    sign is -1 or 1

    >>> deg2sex(12.582438888888889)
    (12, 34, 56.78000000000182)

    >>> deg2sex(-12.582438888888889)
    (-12, 34, 56.78000000000182)

    """

    sign = -1 if deg < 0 else 1
    adeg = abs(deg)
    degf = m.floor(adeg)
    mins = (adeg - degf) * 60.
    minsf = int(m.floor(mins))
    secs = (mins - minsf) * 60.
    return (sign, (degf, minsf, secs))


def deg2dms(deg, dms_format=False):
    """Convert angle in degrees into DMS using format. Default: '02d:02d:05.2f'

    >>> deg2dms(12.582438888888889)
    '+12:34:56.78'

    >>> deg2dms(2.582438888888889)
    '+02:34:56.78'

    >>> deg2dms(-12.582438888888889)
    '-12:34:56.78'
    """

    sign, sex = deg2sex(deg)
    signchar = "+" if sign == 1 else "-"
    if dms_format:
        return f'{signchar}{sex[0]:02d}d{sex[1]:02d}m{sex[2]:05.2f}s'
    return f'{signchar}{sex[0]:02d}:{sex[1]:02d}:{sex[2]:05.2f}'


def deg2hms(deg, hms_format=False):
    """Convert angle in degrees into HMS using format. Default: '%d:%d:%.2f'

    >>> deg2hms(188.73658333333333)
    '12:34:56.78'


    >>> deg2hms(-188.73658333333333)
    '12:34:56.78'
    """

    # TODO: why it this?
    # We only handle positive RA values
    # assert deg >= 0
    sign, sex = deg2sex(deg / 15.)
    if hms_format:
        return f'{sex[0]:02d}h{sex[1]:02d}m{sex[2]:05.2f}s'
    return f'{sex[0]:02d}:{sex[1]:02d}:{sex[2]:05.2f}'


def eq_to_cart(ra, dec):
    """
    Find the cartesian co-ordinates on the unit sphere given the eq.
    co-ords. ra, dec should be in degrees.
    """
    return (
        m.cos(m.radians(dec)) * m.cos(m.radians(ra)),# Cartesian x
        m.cos(m.radians(dec)) * m.sin(m.radians(ra)),# Cartesian y
        m.sin(m.radians(dec))# Cartesian z
    )


def gal2equ(l,b):
    """
    Convert galactic coordinates to equatorial.
    """
    c = SkyCoord(l=np.float(l) * u.deg, b=np.float(b) * u.deg, frame='galactic')
    icrs = c.icrs
    ra = icrs.ra.deg
    dec = icrs.dec.deg

    return ra, dec


def ned_search(object_name):
    """
    Find the coordinates of an object from the NED service.
    Returns RA and Dec. Will return None values if search
    returns no results.
    """
    try:
        result_table = Ned.query_object(object_name)

        ra = result_table[0]['RA']
        dec = result_table[0]['DEC']

        return ra, dec

    except Exception as e:
        logger.debug(
            "Error in performing the NED object search!", exc_info=True
        )
        return None, None


def simbad_search(object_name):
    """
    Find the coordinates of an object from the NED service.
    Returns RA and Dec. Will return None values if search
    returns no results.
    """
    try:
        result_table = Simbad.query_object(object_name)
        if result_table is None:
            return None, None

        ra = result_table[0]['RA']
        dec = result_table[0]['DEC']

        c = SkyCoord(ra + dec, unit=(u.hourangle, u.deg))

        ra = c.ra.deg
        dec = c.dec.deg

        return ra, dec

    except Exception as e:
        logger.debug(
            "Error in performing the SIMBAD object search!", exc_info=True
        )
        return None, None
