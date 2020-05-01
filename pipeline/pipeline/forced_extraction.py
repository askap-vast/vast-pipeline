import logging
import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from django.db import transaction

from pipeline.models import Image, Measurement
from pipeline.image.utils import on_sky_sep

from .forced_phot import ForcedPhot
from .utils import (
    cross_join, get_measurement_models, parallel_groupby_coord
)
from ..utils.utils import StopWatch


logger = logging.getLogger(__name__)


def get_image_list_diff(row):
    out = []
    for image in row['skyrg_img_list']:
        if image not in row['img_list']:
            out.append(image)

    # set empty list to -1
    if not out:
        out = -1

    return out


def extract_from_image(df, images_df):
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
        cluster_threshold=3,
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
    df['bmaj'] = images_df.at[img_name, 'beam_bmaj']
    df['bmin'] = images_df.at[img_name, 'beam_bmin']
    df['pa'] = images_df.at[img_name, 'beam_bpa']
    # add image id
    df['image_id'] = images_df.at[img_name, 'id']

    return df


def forced_extraction(
        sources_df, cfg_err_ra, cfg_err_dec, p_run, meas_dj_obj
    ):
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
    timer = StopWatch()

    # get all the skyregions and related images
    cols = [
        'id', 'name', 'measurements_path', 'path', 'noise_path',
        'beam_bmaj', 'beam_bmin', 'beam_bpa', 'background_path',
        'skyreg__centre_ra', 'skyreg__centre_dec', 'skyreg__xtr_radius'
    ]
    skyreg_df = pd.DataFrame(list(
        Image.objects.select_related('skyreg').values(*tuple(cols))
    ))
    # grab images df to use later
    images_df = (
        skyreg_df.copy()
        .drop([x for x in skyreg_df.columns if 'skyreg' in x], axis=1)
        # not necessary now but here for future when many images might
        # belong to same sky region
        .drop_duplicates()
        # assume each image name is unique
        .set_index('name')
    )
    skyreg_df = (
        skyreg_df.groupby(skyreg_df.columns.drop('name').values.tolist())
        .agg(lambda group: group.values.ravel().tolist())
        .reset_index()
        .rename(columns={'name':'skyrg_img_list'})
        .rename(
            columns={
                x:x.replace('skyreg__', '') for x in
                skyreg_df.columns.values
            }
        )
    )

    # calculate some metrics on sources
    # compute only some necessary metrics in the groupby
    timer.reset()
    srcs_df = parallel_groupby_coord(sources_df)
    logger.info('Groupby-apply time: %.2f seconds', timer.reset())

    # create dataframe with all skyregions and sources combinations
    src_skyrg_df = cross_join(srcs_df.reset_index(), skyreg_df)
    src_skyrg_df['sep'] = np.rad2deg(
        on_sky_sep(
            np.deg2rad(src_skyrg_df['wavg_ra'].values),
            np.deg2rad(src_skyrg_df['centre_ra'].values),
            np.deg2rad(src_skyrg_df['wavg_dec'].values),
            np.deg2rad(src_skyrg_df['centre_dec'].values),
        )
    )

    # select rows where separation is less than sky region radius
    # drop not more useful columns and groupby source id
    # compute list of images
    src_skyrg_df = (
        src_skyrg_df.loc[
            src_skyrg_df['sep'] < src_skyrg_df['xtr_radius'],
            ['source', 'skyrg_img_list']
        ]
        .groupby('source')
        .agg(lambda group: list(
            set(sum(group.values.ravel().tolist(), []))
        ))
    )

    # merge into main df and compare the images
    srcs_df = srcs_df.merge(
        src_skyrg_df, left_index=True, right_index=True
    )
    del src_skyrg_df

    srcs_df['img_diff'] = srcs_df[['img_list', 'skyrg_img_list']].apply(
        get_image_list_diff, axis=1
    )

    # prepare df to groupby image and apply force extraction function
    extr_df = srcs_df.loc[
        srcs_df['img_diff'] != -1,
        ['wavg_ra', 'wavg_dec', 'img_diff']
    ]

    timer.reset()
    extr_df = (
        extr_df.explode('img_diff')
        .reset_index()
        .rename(columns={'img_diff':'image', 'source':'source_tmp_id'})
        .groupby('image')
        .apply(extract_from_image, images_df=images_df)
        .rename(columns={'wavg_ra':'ra', 'wavg_dec':'dec'})
        .dropna(subset=['flux_int'])
    )
    logger.info(
        'Force extraction step time: %.2f seconds', timer.reset()
    )

    # select sensible flux values and set the columns with fix values
    extr_df = extr_df.loc[extr_df['flux_int'].fillna(0) != 0, :]
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
    extr_df['interim_ew'] = (
        extr_df['ra'].values * extr_df['weight_ew'].values
    )
    extr_df['interim_ns'] = (
        extr_df['dec'].values * extr_df['weight_ns'].values
    )

    extr_df['flux_peak'] = extr_df['flux_int']
    extr_df['flux_peak_err'] = extr_df['flux_int_err']
    extr_df['local_rms'] = extr_df['flux_int_err']
    extr_df['spectral_index'] = 0.
    extr_df['dr'] = 0.
    extr_df['d2d'] = 0.
    extr_df['forced'] = True

    # Create measurement Django objects
    extr_df['meas_dj'] = extr_df.apply(
        get_measurement_models, axis=1
    )
    # Delete previous forced measurements and update new forced
    # measurements in the db
    with transaction.atomic():
        obj_to_delete = Measurement.objects.filter(
            image__run=p_run, forced=True
        )
        if obj_to_delete.exists():
            n_del, detail_del = obj_to_delete.delete()
            logger.info(
                ('Deleting all previous forced measurement objects for '
                 'this run. Total objects deleted: %i'),
                n_del,
            )
            logger.debug('(type, #deleted): %s', detail_del)

        batch_size = 10_000
        for idx in range(0, extr_df['meas_dj'].size, batch_size):
            out_bulk = Measurement.objects.bulk_create(
                extr_df['meas_dj'].iloc[
                    idx : idx + batch_size
                ].values.tolist(),
                batch_size
            )
            logger.info('Bulk uploaded #%i measurements', len(out_bulk))

    # make the measurement id column and rename to source
    extr_df['id'] = extr_df['meas_dj'].apply(getattr, args=('id',))
    extr_df = extr_df.rename(columns={'source_tmp_id':'source'})

    # write forced measurements to specific parquet
    logger.info(
        'Saving forced measurements to specific parquet file...'
    )
    for grp_name, grp_df in extr_df.groupby('image'):
        fname = (
            images_df.at[grp_name, 'measurements_path']
            .replace('.parquet', f'_forced_{p_run.name}.parquet')
        )
        (
            grp_df.drop(
                ['source', 'meas_dj', 'image'],
                axis=1
            )
            .to_parquet(
                fname,
                index=False
            )
        )

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
