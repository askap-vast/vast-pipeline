"""
This module contains general pipeline utility functions.
"""

import collections
from datetime import datetime
import os
import logging
import math as m
from typing import Any, Dict, Tuple

from astropy import units as u
from astropy.coordinates import SkyCoord, Longitude, Latitude
import numpy as np
import pandas as pd
from psutil import cpu_count


logger = logging.getLogger(__name__)


class StopWatch:
    """
    A simple stopwatch to simplify timing code.
    """

    def __init__(self) -> None:
        """
        Initialise the StopWatch

        Returns:
            None.
        """
        self._init = datetime.now()
        self._last = self._init

    def reset(self) -> float:
        """
        Reset the stopwatch and return the time since last reset (seconds).

        Returns:
            The time in seconds since the last reset.
        """
        now = datetime.now()
        diff = (now - self._last).total_seconds()
        self._last = now

        return diff

    def reset_init(self) -> float:
        """
        Reset the stopwatch and return the total time since initialisation.

        Returns:
            The time in seconds since the initialisation.
        """
        now = datetime.now()
        diff = (now - self._init).total_seconds()
        self._last = self._init = now

        return diff


def check_read_write_perm(path: str, perm: str = "W") -> None:
    """
    Assess the file permission on a path.

    Args:
        path: The system path to assess.
        perm: The permission to check for.

    Returns:
        None

    Raises:
        IOError: The permission is not valid on the checked directory.
    """
    assert perm in ("R", "W", "X"), "permission not supported"

    perm_map = {"R": os.R_OK, "W": os.W_OK, "X": os.X_OK}
    if not os.access(path, perm_map[perm]):
        msg = f"permission not valid on folder: {path}"
        logger.error(msg)
        raise IOError(msg)

    pass


def deg2dms(
    deg: float,
    dms_format: bool = False,
    precision: int = 2,
    truncate: bool = False,
    latitude: bool = True,
) -> str:
    """Convert angle in degrees into a DMS formatted string.

    Args:
        deg: The angle to convert in degrees.
        dms_format (optional): If `True`, use "d", "m", and "s" as the coorindate
            separator, otherwise use ":". Defaults to False.
        precision (optional): Floating point precision of the arcseconds component.
            Can be 0 or a positive integer. Negative values will be interpreted as 0.
            Defaults to 2.
        truncate (optional): Truncate values after the decimal point instead of rounding.
            Defaults to False (rounding).
        latitude (optional): The input `deg` value should be intrepreted as a latitude.
            Otherwise, it will be interpreted as a longitude.
            Defaults to True (latitude).

    Returns:
        `deg` formatted as a DMS string.

    Example:
        >>> deg2dms(12.582438888888889)
        '+12:34:56.78'
        >>> deg2dms(2.582438888888889, dms_format=True)
        '+02d34m56.78s'
        >>> deg2dms(-12.582438888888889, precision=1)
        '-12:34:56.8'
        >>> deg2dms(-12.582438888888889, precision=1, truncate=True)
        '-12:34:56.7'
    """
    AngleClass = Latitude if latitude else Longitude
    angle = AngleClass(deg, unit="deg")
    precision = precision if precision >= 0 else 0

    output_str: str = angle.to_string(
        unit="deg",
        sep="fromunit" if dms_format else ":",
        precision=precision if not truncate else None,
        alwayssign=True,
        pad=True,
    )
    if truncate:
        # find the decimal point char position and the number of decimal places in the
        # rendered input coordinate (in DMS format, not decimal deg)
        dp_pos = output_str.find(".")
        n_dp = len(output_str[dp_pos + 1:]) if dp_pos >= 0 else 0

        # if the input coordinate precision is less than the requsted output precision,
        # pad the end with zeroes
        if n_dp < precision:
            seconds_str = ""
            # account for rendered input coord having precision = 0
            if dp_pos < 0:
                seconds_str += "."
            seconds_str += "0" * (precision - n_dp)
            output_str += seconds_str
        # otherwise, cut off the excess decimal places
        elif n_dp > precision:
            if precision > 0:
                # account for the decimal point char
                precision += 1
            output_str = output_str[: dp_pos + precision]
        # in the n_dp == precision case, do nothing
    return output_str


def deg2hms(
    deg: float,
    hms_format: bool = False,
    precision: int = 2,
    truncate: bool = False,
    longitude: bool = True,
) -> str:
    """Convert angle in degrees into a HMS formatted string.

    Args:
        deg: The angle to convert in degrees.
        hms_format (optional): If `True`, use "h", "m", and "s" as the coorindate
            separator, otherwise use ":". Defaults to False.
        precision (optional): Floating point precision of the seconds component.
            Can be 0 or a positive integer. Negative values will be interpreted as 0.
            Defaults to 2.
        truncate (optional): Truncate values after the decimal point instead of rounding.
            Defaults to False (rounding).
        longitude (optional): The input `deg` value should be intrepreted as a longitude.
            Otherwise, it will be interpreted as a latitude.
            Defaults to True (longitude).

    Returns:
        `deg` formatted as an HMS string.

    Example:
        >>> deg2hms(188.73658333333333)
        '12:34:56.78'
        >>> deg2hms(-188.73658333333333, hms_format=True)
        '12h34m56.78s'
        >>> deg2hms(188.73658333333333, precision=1)
        '12:34:56.8'
        >>> deg2hms(188.73658333333333, precision=1, truncate=True)
        '12:34:56.7'
    """
    # use the deg2dms formatter, replace d with h, and cut off the leading ±
    # sign
    return deg2dms(
        deg / 15.0,
        dms_format=hms_format,
        precision=precision,
        truncate=truncate,
        latitude=not longitude,
    ).replace("d", "h")[1:]


def eq_to_cart(ra: float, dec: float) -> Tuple[float, float, float]:
    """
    Find the cartesian co-ordinates on the unit sphere given the eq.
    co-ords. ra, dec should be in degrees.

    Args:
        ra: The right ascension coordinate, in degrees, to convert.
        dec: The declination coordinate, in degrees, to convert.

    Returns:
        The cartesian x coordinate.
        The cartesian y coordinate.
        The cartesian z coordinate.
    """
    # TODO: This part of the code can probably be removed along with the
    # storage of these coodinates on the image.
    return (
        m.cos(m.radians(dec)) * m.cos(m.radians(ra)),  # Cartesian x
        m.cos(m.radians(dec)) * m.sin(m.radians(ra)),  # Cartesian y
        m.sin(m.radians(dec)),  # Cartesian z
    )


def equ2gal(ra: float, dec: float) -> Tuple[float, float]:
    """
    Convert equatorial coordinates to galactic

    Args:
        ra (float): Right ascension in units of degrees.
        dec (float): Declination in units of degrees.

    Returns:
        Galactic longitude in degrees.
        Galactic latitude in degrees.
    """
    c = SkyCoord(
        np.float(ra),
        np.float(dec),
        unit=(
            u.deg,
            u.deg),
        frame="icrs")
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
        Right ascension in degrees.
        Declination in degrees.
    """
    c = SkyCoord(
        l=np.float(l) * u.deg,
        b=np.float(b) * u.deg,
        frame="galactic")
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
        The SkyCoord object.
    """
    # if both coord components are decimals, assume they're in degrees, otherwise assume
    # hourangles and degrees. Note that the unit parameter is ignored if the units are
    # not ambiguous i.e. if coord_string contains the units (e.g. 18.4d,
    # 5h35m, etc)
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

    Args:
        df:
            input dataframe, no specific columns.

    Returns:
        The input dataframe with the `float64` type columns downcasted.
    """
    floats = df.select_dtypes(include=["float64"]).columns.tolist()
    df[floats] = df[floats].apply(pd.to_numeric, downcast="float")

    return df


def optimize_ints(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast integer columns in a pd.DataFrame to the smallest
    data type without losing any information.

    Credit to Robbert van der Gugten.

    Args:
        df:
            Input dataframe, no specific columns.

    Returns:
        The input dataframe with the `int64` type columns downcasted.
    """
    ints = df.select_dtypes(include=["int64"]).columns.tolist()
    df[ints] = df[ints].apply(pd.to_numeric, downcast="integer")

    return df


def dict_merge(
    dct: Dict[Any, Any], merge_dct: Dict[Any, Any], add_keys=True
) -> Dict[Any, Any]:
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
        dct (dict): onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Returns:
        Updated dict.
    """
    dct = dct.copy()
    if not add_keys:
        merge_dct = {k: merge_dct[k]
                     for k in set(dct).intersection(set(merge_dct))}

    for k, v in merge_dct.items():
        if (
            k in dct
            and isinstance(dct[k], dict)
            and isinstance(merge_dct[k], collections.abc.Mapping)
        ):
            dct[k] = dict_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct


def timeStamped(fname, fmt="%Y-%m-%d-%H-%M-%S_{fname}"):
    return datetime.now().strftime(fmt).format(fname=fname)


def calculate_n_partitions(df, n_cpu, partition_size_mb=100):
    """
    This function will calculate how many partitions a dataframe should be
    split into.

    Args:
        df: The pandas dataframe to be partitionined.
        n_cpu: The number of available CPUs.
        partition_size: The optimal partition size in MB.
    Returns:
        The optimal number of partitions.
    """
    mem_usage_mb = df.memory_usage(deep=True).sum() / 1e6
    n_partitions = int(np.ceil(mem_usage_mb / partition_size_mb))

    # n_partitions should be >= n_cpu for optimal parallel processing
    if n_partitions < n_cpu:
        n_partitions = n_cpu

    partition_size_mb = int(np.ceil(mem_usage_mb / n_partitions))

    logger.debug("Using %d partions of %dMB", n_partitions, partition_size_mb)

    return n_partitions


def calculate_workers_and_partitions(df, num_cpu_max=0, partition_size_mb=15):
    """
    Return number of workers and the number of partitions for Dask

    Args:
        df: The pandas dataframe to be partitionined.
        num_cpu_max: The maximum number of workers to allocate.
                     The default of 0 means use one less than all available cores
        partition_size: The optimal partition size in MB.
    Returns:
        (num_workers, n_partitions): Calculated workers and partitions.
    """
    num_cpu = cpu_count() - 1
    num_workers = num_cpu if num_cpu_max == 0 else num_cpu_max
    if num_workers > num_cpu:
        logger.debug("%d desired workers is greater than available cores. Limiting to %s.",
                     num_workers, num_cpu)
        num_workers = num_cpu
    n_partitions = calculate_n_partitions(df, num_workers, partition_size_mb)

    return num_workers, n_partitions