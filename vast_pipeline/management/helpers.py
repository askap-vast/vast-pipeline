"""
Helper functions for the commands.
"""

import os
import logging

from typing import Tuple
from django.conf import settings as sett


logger = logging.getLogger(__name__)


def get_p_run_name(name: str, return_folder: bool=False) -> Tuple[str, str]:
    """
    Determines the name of the pipeline run. Can also return the output folder
    if selected.

    Args:
        name: The user entered name of the pipeline run.
        return_folder: When `True` the pipeline directory is also returned.

    Returns:
        The name of the pipeline run. If return_folder is `True` then both
        the name and directory are returned.
    """
    if '/' in name:
        folder = os.path.realpath(name)
        run_name = os.path.basename(folder)
        return (run_name, folder) if return_folder else run_name

    folder = os.path.join(os.path.realpath(sett.PIPELINE_WORKING_DIR), name)

    return (name, folder) if return_folder else name
