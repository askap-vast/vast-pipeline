import collections
from datetime import datetime
import math as m
import logging
import os
from typing import Any, Dict, Tuple

from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np
import pandas as pd


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


def equ2gal(ra: float, dec: float) -> Tuple[float, float]:
    """
    Convert equatorial coordinates to galactic

    Args:
        ra (float): Right ascension in units of degrees.
        dec (float): Declination in units of degrees.

    Returns:
        Tuple (float, float): Galactic longitude and latitude in degrees.
    """
    c = SkyCoord(np.float(ra), np.float(dec), unit=(u.deg, u.deg), frame='icrs')
    l = c.galactic.l.deg
    b = c.galactic.b.deg

    return l, b


def gal2equ(l: float, b: float) -> Tuple[float, float]:
    """
    Convert galactic coordinates to equatorial.

    Args:
        l (float): Galactic longitude in degrees.
        b (float): Galactic latitude in degrees.

    Returns:
        Tuple (float, float): Right ascension and declination in units of degrees.
    """
    c = SkyCoord(l=np.float(l) * u.deg, b=np.float(b) * u.deg, frame='galactic')
    ra = c.icrs.ra.deg
    dec = c.icrs.dec.deg

    return ra, dec


def parse_coord(coord_string: str, coord_frame: str = "icrs") -> SkyCoord:
    """Parse a coordinate string and return a SkyCoord. The units may be expressed within
    `coord_string` e.g. "21h52m03.1s -62d08m19.7s", "18.4d +43.1d". If no units are given,
    the following assumptions are made:
        - if both coordinate components are decimals, they are assumed to be in degrees.
        - if a sexagesimal coordinate is given and the frame is galactic, both components
            are assumed to be in degrees. For any other frame, the first component is
            assumed to be in hourangles and the second in degrees.
    Will raise a ValueError if SkyCoord is unable to parse `coord_string`.

    Args:
        coord_string (str): The coordinate string to parse.
        coord_frame (str, optional): The frame of `coord_string`. Defaults to "icrs".

    Returns:
        SkyCoord
    """
    # if both coord components are decimals, assume they're in degrees, otherwise assume
    # hourangles and degrees. Note that the unit parameter is ignored if the units are
    # not ambiguous i.e. if coord_string contains the units (e.g. 18.4d, 5h35m, etc)
    try:
        _ = [float(x) for x in coord_string.split()]
        unit = "deg"
    except ValueError:
        if coord_frame == "galactic":
            unit = "deg"
        else:
            unit = "hourangle,deg"

    coord = SkyCoord(coord_string, unit=unit, frame=coord_frame)

    return coord


def optimize_floats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast float columns in a pd.DataFrame to the smallest
    data type without losing any information.

    Credit to Robbert van der Gugten.

    Parameters
    ----------
    df : pd.DataFrame
        input dataframe, no specific columns.

    Returns
    -------
    df : pd.DataFrame
        the input dataframe with the `float64` type
        columns downcasted.
    """
    floats = df.select_dtypes(include=['float64']).columns.tolist()
    df[floats] = df[floats].apply(pd.to_numeric, downcast='float')

    return df


def optimize_ints(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast integer columns in a pd.DataFrame to the smallest
    data type without losing any information.

    Credit to Robbert van der Gugten.

    Parameters
    ----------
    df : pd.DataFrame
        input dataframe, no specific columns.

    Returns
    -------
    df : pd.DataFrame
        the input dataframe with the `int64` type
        columns downcasted.
    """
    ints = df.select_dtypes(include=['int64']).columns.tolist()
    df[ints] = df[ints].apply(pd.to_numeric, downcast='integer')

    return df


def dict_merge(dct: Dict[Any, Any], merge_dct: Dict[Any, Any], add_keys=True) -> Dict[Any, Any]:
    """Recursive dict merge. Inspired by dict.update(), instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The `merge_dct` is merged into
    `dct`.

    This version will return a copy of the dictionary and leave the original
    arguments untouched.

    The optional argument `add_keys`, determines whether keys which are
    present in `merge_dict` but not `dct` should be included in the
    new dict.

    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Returns:
        dict: updated dict
    """
    dct = dct.copy()
    if not add_keys:
        merge_dct = {k: merge_dct[k] for k in set(dct).intersection(set(merge_dct))}

    for k, v in merge_dct.items():
        if (
            k in dct
            and isinstance(dct[k], dict)
            and isinstance(merge_dct[k], collections.Mapping)
        ):
            dct[k] = dict_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct
