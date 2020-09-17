# original VAST file: PATH/vast-pipeline/vast/import_survey_catalogue.py

import os
import numpy as np
import logging

import pandas as pd
from astropy.table import Table
from astropy.io.votable import parse_single_table

from pipeline.utils.utils import StopWatch
from .translators import translators


logger = logging.getLogger(__name__)


def get_survey(filename, survey_name, survey_id, tr=translators['DEFAULT']):
    """
    read a table and extract the columns of interest
    :param filename:
    :param survey_name:
    :return:
    """
    # moving to Pandas (in future to Dask)
    watch = StopWatch()
    ext = os.path.splitext(filename)[-1]
    if ext.upper() in ['VOT', 'VO', 'XML']:
        tab = (
            parse_single_table(filename)
            .to_table(use_names_over_ids=True)
        )
    else:
        tab = Table.read(filename)

    logger.info('total time to load catalogue: %f s', watch.reset())

    # grab the columns names and dtypes
    col_dtype_map = {col: tab[col].dtype.name for col in tab.colnames}
    tab = tab.to_pandas()

    # remove not used columns
    for col in list(col_dtype_map.keys()):
        if col not in tr.values():
            col_dtype_map.pop(col)

    tab = tab.loc[:, col_dtype_map.keys()]

    # fix data types for bytes and convert float32 to float64
    for col in tab.columns:
        if 'bytes' in col_dtype_map[col]:
            tab[col] = tab.loc[:, col].astype(str).str.strip("'b")

        if tab.loc[:, col].dtype == np.float32:
            tab[col] = tab.loc[:, col].astype(np.float64)

    # calculate extra columns
    tab['survey_id'] = survey_id
    tab['name'] =  f"{tr['prefix']}_" + tab.index.map(lambda x: f'{x:06}').values

    tab = tab.rename(
        columns={tr['ra']: 'ra', tr['dec']:'dec', tr['pa']:'pa'},
        copy=False
    )

    tab['err_ra'] = tab.loc[:, tr['err_ra']] * tr['pos_err_ang_scale']
    tab['err_dec'] = tab.loc[:, tr['err_dec']] * tr['pos_err_ang_scale']
    tab['peak_flux'] = tab.loc[:, tr['peak_flux']] * tr['flux_scale']
    tab['err_peak_flux'] = tab.loc[:, tr['err_peak_flux']] * tr['flux_scale']
    tab['total_flux'] = tab.loc[:, tr['total_flux']] * tr['flux_scale']
    tab['err_total_flux'] = tab.loc[:, tr['err_total_flux']] * tr['flux_scale']
    tab['bmaj'] = tab.loc[:, tr['bmaj']] * tr['ang_scale']
    tab['bmin'] = tab.loc[:, tr['bmin']] * tr['ang_scale']
    tab['image_name'] = 'None'

    if 'alpha' in tr:
        tab = tab.rename(columns={tr['alpha']:'alpha'}, copy=False)
    else:
        tab['alpha'] = 0

    # drop not used columns
    cols = [
        'survey_id', 'name', 'ra', 'err_ra', 'dec', 'err_dec',
        'peak_flux', 'err_peak_flux', 'total_flux', 'err_total_flux', 'bmaj',
        'bmin', 'pa', 'alpha', 'image_name'
    ]
    tab = tab.loc[:, cols]

    # fix NaNs in numeric types
    for col in cols:
        if tab[col].isnull().any():
            if tab[col].dtype == float:
                tab[col] = tab[col].fillna(0.)
            elif tab[col].dtype == int:
                tab[col] = tab[col].fillna(0)

    logger.info('total time to process catalogue: %f s', watch.reset())
    return tab
