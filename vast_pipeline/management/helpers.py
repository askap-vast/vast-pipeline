"""
Helper functions for the commands.
"""

import logging

from typing import Tuple
from django.conf import settings as sett
from pathlib import Path


logger = logging.getLogger(__name__)


def get_p_run_name(name: str, return_folder: bool = False) -> Tuple[str, str]:
    """
    Determines the name of the pipeline run. Can also return the output folder
    if selected.

    Args:
        name: The user entered name of the pipeline run.
        return_folder: When `True` the pipeline directory is also returned.

    Returns:
        The name of the pipeline run (always returned).
        The run directory (if `return_folder` is set to `True`).
    """
    if '/' in name:
        folder = Path(name).resolve()
        run_name = folder.parent[0]
        return (run_name, folder) if return_folder else run_name

    working_dir = Path(sett.PIPELINE_WORKING_DIR).resolve()
    folder = working_dir/name

    return (name, folder) if return_folder else name
