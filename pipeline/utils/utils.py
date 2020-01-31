import os
import logging
import datetime
from math import floor
from importlib.util import spec_from_file_location, module_from_spec

from django.conf import settings

import pipeline.config as base_cfg


logger = logging.getLogger(__name__)


class StopWatch():
    """A simple stopwatch to simplify timing code"""

    def __init__(self):
        self._init = datetime.datetime.now()
        self._last = self._init

    def reset(self):
        """
        Reset the stopwatch and return the time since last reset (seconds)
        """
        now = datetime.datetime.now()
        diff = (now - self._last).total_seconds()
        self._last = now
        return diff

    def reset_init(self):
        """
        Reset the stopwatch and return the total time since initialisation
        """
        now = datetime.datetime.now()
        diff = (now - self._init).total_seconds()
        self._last = now
        self._init = now
        return diff


class RunStats():
    """Statistics for a pipeline run"""
    fluxes_added = 0           # total Flux rows added
    sources_added = 0          # total Source rows added
    detected_count = 0         # total blind detections (Flux.blind_detection==True)


def load_validate_cfg(cfg):
    """
    Check the given Config path. Throw exception if any problems
    return the config object as module/class
    """
    if not os.path.exists(cfg):
        raise Exception('dataset config file not existent')

    # load the dataset config as a Python module
    spec = spec_from_file_location('dataset_config', cfg)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    # do sanity checks
    if not (getattr(mod, 'IMAGE_FILES') or getattr(mod, 'SELAVY_FILES')):
        raise Exception(
            'no image file paths passed or Selavy file paths!'
        )

    source_finder_names = settings.SOURCE_FINDERS
    if getattr(mod, 'SOURCE_FINDER') not in source_finder_names:
        raise Exception((
            f"Invalid source finder {getattr(mod, 'SOURCE_FINDER')}."
            f' Choices are {source_finder_names}'
        ))

    if getattr(mod, 'PRIMARY_IMAGE_MODE') and not hasattr(mod, 'PRIMARY_IMAGE_FREQUENCY'):
        raise Exception((
            'PRIMARY_IMAGE_FREQUENCY must be specified if'
            ' PRIMARY_IMAGE_MODE is True'
        ))

    # validate every config from the config template
    for key in [k for k in dir(mod) if k.isupper()]:
        if key not in dir(base_cfg):
            raise Exception('configuration not valid, missing keys!')

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
    degf = floor(adeg)
    mins = (adeg - degf) * 60.
    minsf = int(floor(mins))
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
