import os
import logging
import numpy as np
import pandas as pd
import dask.dataframe as dd
import dask.bag as db
from psutil import cpu_count
from glob import glob

from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from django.db import transaction
from pyarrow.parquet import read_schema

from pipeline.models import Image, Measurement
from pipeline.image.utils import on_sky_sep

from .loading import bulk_upload_model
from .forced_phot import ForcedPhot
from .utils import (
    cross_join, get_measurement_models, parallel_groupby_coord
)
from ..utils.utils import StopWatch


logger = logging.getLogger(__name__)


def remove_forced_meas(run_path):
    '''
    remove forced measurements from the database if forced parquet files
    are found
    '''
    path_glob = glob(
        os.path.join(run_path, 'forced_measurements_*.parquet')
    )
    if path_glob:
        ids = (
            dd.read_parquet(path_glob, columns='id')
            .values
            .compute()
            .tolist()
        )
        obj_to_delete = Measurement.objects.filter(id__in=ids)
        del ids
        if obj_to_delete.exists():
            with transaction.atomic():
                n_del, detail_del = obj_to_delete.delete()
                logger.info(
                    ('Deleting all previous forced measurement and association'
                     ' objects for this run. Total objects deleted: %i'),
                    n_del,
                )
                logger.debug('(type, #deleted): %s', detail_del)

    return path_glob


def extract_from_image(
    df, images_df, edge_buffer, cluster_threshold, allow_nan
):
    P_islands = SkyCoord(
        df['wavg_ra'].values * u.deg,
        df['wavg_dec'].values * u.deg
    )

    img_name = df['image'].iloc[0]
    image, noise, background = images_df.loc[
        img_name,
        ['path', 'noise_path', 'background_path']
    ]

    FP = ForcedPhot(image, background, noise)
    flux, flux_err, chisq, DOF = FP.measure(
        P_islands,
        cluster_threshold=cluster_threshold,
        allow_nan=allow_nan,
        edge_buffer=edge_buffer
    )

    # make up the measurements name from the image
    # get max component id from parquet file
    max_id = (
        pd.read_parquet(
            images_df.at[img_name, 'measurements_path'],
            columns=['island_id']
        )['island_id']
    )
    prefix = max_id.iloc[0].rsplit('_', maxsplit=1)[0] + '_'
    max_id = (
        max_id.str.rsplit('_', n=1)
        .str.get(-1)
        .astype(int)
        .values.max() + 1
    )

    # generate the name columns
    df['island_id'] = np.char.add(
        prefix,
        np.arange(max_id, max_id + df.shape[0]).astype(str)
    )
    df['component_id'] = df['island_id'].str.replace(
        'island', 'component'
    ) + 'a'
    prefix = img_name.split('.')[0] + '_'
    df['name'] = prefix + df['component_id']
    # assign all the other columns
    # convert fluxes to mJy
    df['flux_int'] = flux * 1.e3
    df['flux_int_err'] = flux_err * 1.e3
    df['chi_squared_fit'] = chisq
    # store source bmaj and bmin in arcsec
    df['bmaj'] = images_df.at[img_name, 'beam_bmaj'] * 3600.
    df['bmin'] = images_df.at[img_name, 'beam_bmin'] * 3600.
    df['pa'] = images_df.at[img_name, 'beam_bpa']
    # add image id and time
    df['image_id'] = images_df.at[img_name, 'id']
    df['time'] = images_df.at[img_name, 'datetime']

    return df


def parallel_extraction(
    df, df_images, df_sources, min_sigma, edge_buffer,
    cluster_threshold, allow_nan
):
    '''
    parallelize forced extraction with Dask
    '''
    col_dtype = {
        'source_tmp_id': 'i',
        'wavg_ra': 'f',
        'wavg_dec': 'f',
        'image': 'U',
        'flux_peak': 'f',
        'island_id': 'U',
        'component_id': 'U',
        'name': 'U',
        'flux_int': 'f',
        'flux_int_err': 'f',
        'chi_squared_fit': 'f',
        'bmaj': 'f',
        'bmin': 'f',
        'pa': 'f',
        'image_id': 'i',
        'time': 'datetime64[ns]'
    }
    out = (
        df.explode('img_diff')
        .reset_index()
        .rename(columns={'img_diff':'image', 'source':'source_tmp_id'})
    )

    out = out.merge(
        df_images[[
            'rms_min'
        ]],
        left_on='image',
        right_on='name',
        how='left'
    ).rename(columns={
        'rms_min': 'image_rms_min',
    })

    out = pd.merge(
        out, df_sources[['source', 'image', 'flux_peak']],
        left_on=['source_tmp_id', 'detection'], right_on=['source', 'image'],
        how='left'
    ).drop(columns=['image_y', 'source']).rename(columns={'image_x': 'image'})

    # drop the source for which we would have no hope of detecting
    predrop_shape = out.shape[0]
    out['max_snr'] = out['flux_peak'].values / out['image_rms_min'].values
    out = out[out['max_snr'] > min_sigma].reset_index(drop=True)
    postdrop_shape = out.shape[0]
    logger.debug("Min forced sigma dropped %i sources", (
        predrop_shape - postdrop_shape
    ))

    out = out.drop(['max_snr', 'image_rms_min', 'detection'], axis=1)

    n_cpu = cpu_count() - 1
    out = (
        dd.from_pandas(out, n_cpu)
        .groupby('image')
        .apply(
            extract_from_image,
            images_df=df_images,
            edge_buffer=edge_buffer,
            cluster_threshold=cluster_threshold,
            allow_nan=allow_nan,
            meta=col_dtype)
        .dropna(subset=['flux_int'])
        .compute(num_workers=n_cpu, scheduler='processes')
        .rename(columns={'wavg_ra':'ra', 'wavg_dec':'dec'})
    )

    return out


def write_group_to_parquet(df, fname):
    '''
    write a dataframe correpondent to a single group/image
    to a parquet file
    '''
    (
        df.drop(['d2d', 'dr', 'source', 'meas_dj', 'image'], axis=1)
        .to_parquet(fname, index=False)
    )

    pass


def parallel_write_parquet(df, run_path):
    '''
    parallelize writing parquet files for forced measurments
    '''
    images = df['image'].unique().tolist()
    get_fname = lambda n: os.path.join(
        run_path,
        'forced_measurements_' + n.replace('.','_') + '.parquet'
    )
    dfs = list(map(lambda x: (df[df['image'] == x], get_fname(x)), images))
    n_cpu = cpu_count() - 1

    # writing parquets using Dask bag
    bags = db.from_sequence(dfs)
    bags = bags.starmap(lambda df, fname: write_group_to_parquet(df, fname))
    bags.compute(num_workers=n_cpu)

    pass


def forced_extraction(
        sources_df, cfg_err_ra, cfg_err_dec, p_run,
        meas_dj_obj, extr_df, min_sigma, edge_buffer,
        cluster_threshold, allow_nan
    ):
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
    logger.info(
        'Starting force extraction step.'
    )

    timer = StopWatch()

    # get all the skyregions and related images
    cols = [
        'id', 'name', 'measurements_path', 'path', 'noise_path',
        'beam_bmaj', 'beam_bmin', 'beam_bpa', 'background_path',
        'rms_min', 'datetime', 'skyreg__centre_ra',
        'skyreg__centre_dec', 'skyreg__xtr_radius'
    ]

    images_df = pd.DataFrame(list(
        Image.objects.filter(
            run=p_run
        ).select_related('skyreg').order_by('datetime').values(*tuple(cols))
    )).set_index('name')

    # prepare df to groupby image and apply force extraction function
    extr_df = extr_df[['wavg_ra', 'wavg_dec', 'img_diff', 'detection']]

    timer.reset()
    extr_df = parallel_extraction(
        extr_df, images_df, sources_df, min_sigma, edge_buffer,
        cluster_threshold, allow_nan
    )
    logger.info(
        'Force extraction step time: %.2f seconds', timer.reset()
    )

    # make measurement names unique for db constraint
    now = pd.Timestamp('now').strftime('%Y%m%dT%H%M')
    extr_df['name'] = extr_df['name'] + f'_f{now}'

    # select sensible flux values and set the columns with fix values
    values = {
        'flux_int': 0,
        'flux_int_err': 0
    }
    extr_df = extr_df.fillna(value=values)

    extr_df = extr_df[
        (extr_df['flux_int'] != 0)
        & (extr_df['flux_int_err'] != 0)
        & (extr_df['chi_squared_fit'] != np.inf)
        & (extr_df['chi_squared_fit'] != np.nan)
    ]

    default_pos_err = settings.POS_DEFAULT_MIN_ERROR / 3600.
    extr_df['ra_err'] = default_pos_err
    extr_df['dec_err'] = default_pos_err
    extr_df['err_bmaj'] = 0.
    extr_df['err_bmin'] = 0.
    extr_df['err_pa'] = 0.
    extr_df['ew_sys_err'] = cfg_err_ra
    extr_df['ns_sys_err'] = cfg_err_dec
    extr_df['error_radius'] = 0.

    extr_df['uncertainty_ew'] = np.hypot(
        cfg_err_ra,
        default_pos_err
    )
    extr_df['weight_ew'] = 1. / extr_df['uncertainty_ew'].values**2
    extr_df['uncertainty_ns'] = np.hypot(
        cfg_err_dec,
        default_pos_err
    )
    extr_df['weight_ns'] = 1. / extr_df['uncertainty_ns'].values**2

    extr_df['flux_peak'] = extr_df['flux_int']
    extr_df['flux_peak_err'] = extr_df['flux_int_err']
    extr_df['local_rms'] = extr_df['flux_int_err']
    extr_df['snr'] = (
        extr_df['flux_peak'].values
        / extr_df['local_rms'].values
    )
    extr_df['spectral_index'] = 0.
    extr_df['dr'] = 0.
    extr_df['d2d'] = 0.
    extr_df['forced'] = True
    extr_df['compactness'] = 1.
    extr_df['psf_bmaj'] = extr_df['bmaj']
    extr_df['psf_bmin'] = extr_df['bmin']
    extr_df['psf_pa'] = extr_df['pa']
    extr_df['flag_c4'] = False
    extr_df['spectral_index_from_TT'] = False
    extr_df['has_siblings'] = False

    col_order = read_schema(
        images_df.iloc[0]['measurements_path']
    ).names
    col_order.remove('id')

    remaining = list(set(extr_df.columns) - set(col_order))

    extr_df = extr_df[col_order + remaining]

    # Create measurement Django objects
    extr_df['meas_dj'] = extr_df.apply(get_measurement_models, axis=1)

    # Delete previous forced measurements and update new forced
    # measurements in the db
    # get the forced measurements ids for the current pipeline run
    forced_parquets = remove_forced_meas(p_run.path)

    # delete parquet files
    logger.debug('Removing forced measurements parquet files')
    for parquet in forced_parquets:
        os.remove(parquet)

    bulk_upload_model(extr_df['meas_dj'], Measurement)

    # make the measurement id column and rename to source
    extr_df['id'] = extr_df['meas_dj'].apply(lambda x: x.id)
    extr_df = extr_df.rename(columns={'source_tmp_id':'source'})

    # write forced measurements to specific parquet
    logger.info(
        'Saving forced measurements to specific parquet file...'
    )
    parallel_write_parquet(extr_df, p_run.path)

    # append new measurements to prev meas df
    meas_dj_obj = meas_dj_obj.append(
        extr_df[['meas_dj', 'id']],
        ignore_index=True
    )

    # append new meas into main df and proceed with source groupby etc
    sources_df = sources_df.append(
        extr_df.loc[:, extr_df.columns.isin(sources_df.columns)],
        ignore_index=True
    )

    logger.info(
        'Total forced extraction time: %.2f seconds', timer.reset_init()
    )
    return sources_df, meas_dj_obj
