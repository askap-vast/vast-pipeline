"""
Helper functions for the commands.
"""

import os
import logging
import gc

from typing import Tuple
from django.conf import settings as sett


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
        folder = os.path.realpath(name)
        run_name = os.path.basename(folder)
        return (run_name, folder) if return_folder else run_name

    folder = os.path.join(os.path.realpath(sett.PIPELINE_WORKING_DIR), name)

    return (name, folder) if return_folder else name


def _queryset_iterator(qs, batchsize:int = 500, gc_collect:bool = True):
    """
    
    Args:
        qs: QuerySet
        batchsize: number of objects to batch together, defaults to 500.
        gc_collect: whether to garbage collect, defaults to `True`.
    
    Returns:
    
    """
    
    # Yoinked from:
    #https://www.guguweb.com/2020/03/27/optimize-django-memory-usage/
    
    iterator = qs.values_list('pk', flat=True).order_by('pk').distinct().iterator()
    eof = False
    while not eof:
        primary_key_buffer = []
        try:
            while len(primary_key_buffer) < batchsize:
                primary_key_buffer.append(iterator.next())
        except StopIteration:
            eof = True
        for obj in qs.filter(pk__in=primary_key_buffer).order_by('pk').iterator():
            yield obj
        if gc_collect:
            gc.collect()

def clean_delete(self, p_run):
    """
    Delete the pipeline run database entries without loading them all
    into memory simultaneously
    
    Args:
        p_run: 
    
    Returns:
        None
    """
    
    for obj in _queryset_iterator(p_run.objects.all()):
        obj.delete()
