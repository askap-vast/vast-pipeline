import logging
import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from django.db import transaction

from pipeline.models import Image
from pipeline.image.utils import on_sky_sep
from pipeline.pipeline.utils import get_measurement_models

from .forced_phot import ForcedPhot
from .loading import upload_associations
from .utils import cross_join
from ..models import Association, Measurement, Source


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


def get_eta_metric(df, peak=False):
    '''
    Calculates the eta variability metric of a source.
    Works on the grouped by dataframe using the fluxes
    of the assoicated measurements.
    '''
    suffix = 'peak' if peak else 'int'
    Nsrc = df['source'].count()
    if (Nsrc == 1) or (df[f'flux_{suffix}_err'] == 0.).any():
        return 0.

    weights = 1. / df[f'flux_{suffix}_err'].values**2
    fluxes = df[f'flux_{suffix}'].values
    eta = (Nsrc / (Nsrc - 1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta


def update_source_models(row):
    '''
    Fetches the source model (for DB injecting).
    '''
    src = row['src_dj']
    for fld in row.index:
        setattr(src, fld, row[fld])
    return src


def forced_extraction(srcs_df, sources_df, sys_err):
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
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
    )
    skyreg_df.columns = [
        x.replace('skyreg__', '') for x in skyreg_df.columns.values
    ]


    # create dataframe with all skyregions and sources combinations
    cols = [
        'wavg_uncertainty_ew', 'wavg_uncertainty_ns', 'avg_flux_int',
        'avg_flux_peak', 'max_flux_peak', 'v_int', 'v_peak', 'eta_int',
        'eta_peak', 'new', 'related_list', 'src_dj'
    ]
    src_skyrg_df = cross_join(
        (
            srcs_df.drop(cols, axis=1)
            .reset_index()
        ),
        skyreg_df
    )
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
    ].copy()
    extr_df = (
        extr_df.explode('img_diff')
        .reset_index()
        .rename(columns={'img_diff':'image', 'source':'source_tmp_id'})
        .groupby('image')
        .apply(extract_from_image, images_df=images_df)
        .rename(columns={'wavg_ra':'ra', 'wavg_dec':'dec'})
        .dropna(subset=['flux_int'])
    )

    extr_df = extr_df.loc[extr_df['flux_int'] > 0, :]
    # set the columns with fix values
    extr_df['ra_err'] = settings.POS_DEFAULT_MIN_ERROR
    extr_df['dec_err'] = settings.POS_DEFAULT_MIN_ERROR
    extr_df['err_bmaj'] = sys_err
    extr_df['err_bmin'] = sys_err
    extr_df['err_pa'] = sys_err
    extr_df['ew_sys_err'] = sys_err
    extr_df['ns_sys_err'] = sys_err
    extr_df['error_radius'] = 0.

    extr_df['uncertainty_ew'] = sys_err
    extr_df['weight_ew'] = 1. / extr_df['uncertainty_ew'].values**2
    extr_df['uncertainty_ns'] = sys_err
    extr_df['weight_ns'] = 1. / extr_df['uncertainty_ns'].values**2

    extr_df['flux_peak'] = extr_df['flux_int']
    extr_df['flux_peak_err'] = extr_df['flux_int_err']
    extr_df['spectral_index'] = 0.
    extr_df['forced'] = True

    # Create measurement Django objects
    extr_df['meas_dj'] = extr_df.apply(
        get_measurement_models, axis=1
    )
    # Update new sources in the db and update the parquet files
    with transaction.atomic():
        batch_size = 10_000
        for idx in range(0, extr_df['meas_dj'].size, batch_size):
            out_bulk = Measurement.objects.bulk_create(
                extr_df['meas_dj'].iloc[
                    idx : idx + batch_size
                ].values.tolist(),
                batch_size
            )
            logger.info('Bulk uploaded #%i measurements', len(out_bulk))

    # make the measurement id column
    extr_df['id'] = extr_df['meas_dj'].apply(getattr, args=('id',))

    # TODO: parallelise with Dask
    # Update the parquet files appending the new measurements
    for grp_name, grp_df in extr_df.groupby('image'):
        logger.info('Updating the image %s parquet ...', grp_name)
        fname = images_df.at[grp_name, 'measurements_path']
        df = (
            pd.read_parquet(fname)
            .append(grp_df.drop(
                ['source_tmp_id', 'meas_dj', 'image'],
                axis=1
            ))
        )
        df.to_parquet(
            fname,
            index=False
        )

    # create the associations objects
    extr_df = (
        extr_df.rename(columns={'source_tmp_id':'source'})
        .merge(
            srcs_df['src_dj'].reset_index(),
            on='source'
        )
    )
    extr_df['assoc_dj'] = extr_df.apply(lambda row: Association(
            meas=row['meas_dj'], source=row['src_dj']
        ),
        axis=1
    )
    # upload associations in DB
    upload_associations(extr_df['assoc_dj'])

    # Update source variability metrics and fluxes
    # select only sources to be updated and used columns
    cols = [
        'source', 'src_dj', 'flux_int', 'flux_int_err', 'flux_peak',
        'flux_peak_err'
    ]
    sources_df = (
        sources_df.loc[
            sources_df['source'].isin(extr_df['source']),
            cols
        ]
        .append(extr_df[cols], ignore_index=True)
    )

    grouped = sources_df.groupby('source')
    new_srcs_df = grouped.agg(
        avg_flux_int=pd.NamedAgg(column='flux_int', aggfunc='mean'),
        avg_flux_peak=pd.NamedAgg(column='flux_peak', aggfunc='mean'),
        max_flux_peak=pd.NamedAgg(column='flux_peak', aggfunc='max'),
    )
    new_srcs_df['v_int'] = (
        grouped['flux_int'].std() / grouped['flux_int'].mean()
    )
    new_srcs_df['v_peak'] = (
        grouped['flux_peak'].std() / grouped['flux_peak'].mean()
    )
    new_srcs_df['eta_int'] = grouped.apply(get_eta_metric)
    new_srcs_df['eta_peak'] = grouped.apply(get_eta_metric, peak=True)
    # add and update Django objects with new values
    new_srcs_df['src_dj'] = srcs_df.loc[new_srcs_df.index, 'src_dj']
    new_srcs_df['src_dj'] = new_srcs_df.apply(
        update_source_models,
        axis=1
    )
    # bulk update the source new variability metrics and fluxes
    with transaction.atomic():
        batch_size = 10_000
        for idx in range(0, new_srcs_df['src_dj'].size, batch_size):
            out_bulk = Source.objects.bulk_update(
                new_srcs_df['src_dj'].iloc[
                    idx : idx + batch_size
                ].values.tolist(),
                new_srcs_df.columns.drop('src_dj').values.tolist(),
                batch_size
            )
            logger.info('Bulk updated #%i sources', len(out_bulk))

    pass
