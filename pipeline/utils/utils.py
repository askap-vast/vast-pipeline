import os
import logging
import math as m
from importlib.util import spec_from_file_location, module_from_spec

from datetime import datetime
from django.conf import settings

import pipeline.config_template as base_cfg


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
        self._last = now
        self._init = now
        return diff


def load_validate_cfg(cfg):
    """
    Check the given Config path. Throw exception if any problems
    return the config object as module/class
    """
    if not os.path.exists(cfg):
        raise Exception('pipeline run config file not existent')

    # load the run config as a Python module
    spec = spec_from_file_location('run_config', cfg)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    # do sanity checks
    if not (getattr(mod, 'IMAGE_FILES') and getattr(mod, 'SELAVY_FILES')):
        raise Exception(
            'no image file paths passed or Selavy file paths!'
        )
    else:
        for lst in ['IMAGE_FILES', 'SELAVY_FILES']:
            for file in getattr(mod, lst):
                if not os.path.exists(file):
                    raise Exception(f'file:\n{file}\ndo not exists!')

    source_finder_names = settings.SOURCE_FINDERS
    if getattr(mod, 'SOURCE_FINDER') not in source_finder_names:
        raise Exception((
            f"Invalid source finder {getattr(mod, 'SOURCE_FINDER')}."
            f' Choices are {source_finder_names}'
        ))

    # validate Forced extraction settings
    if getattr(mod, 'MONITOR') and not(
            getattr(mod, 'BACKGROUND_MAP_FILES') and getattr(mod, 'RMS_FILES')
        ):
        raise Exception('Expecting list of background map and RMS files!')
    else:
        for lst in ['BACKGROUND_MAP_FILES', 'RMS_FILES']:
            for file in getattr(mod, lst):
                if not os.path.exists(file):
                    raise Exception(f'file:\n{file}\ndo not exists!')

    # validate every config from the config template
    for key in [k for k in dir(mod) if k.isupper()]:
        if key not in dir(base_cfg):
            raise Exception(f'configuration not valid, missing key: {key}!')


    return mod


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
