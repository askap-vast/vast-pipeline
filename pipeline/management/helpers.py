import os
import logging

from django.conf import settings as sett


logger = logging.getLogger(__name__)


def get_p_run_name(name, return_folder=False):
    if '/' in name:
        folder = os.path.realpath(name)
        run_name = os.path.basename(folder)
        return (run_name, folder) if return_folder else run_name

    folder = os.path.join(os.path.realpath(sett.PIPELINE_WORKING_DIR), name)
    return (name, folder) if return_folder else name
