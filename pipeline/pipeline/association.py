import logging
import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord

from ..models import Association, Source
from ..utils.utils import deg2hms, deg2dms


logger = logging.getLogger(__name__)


def get_eta_metric(row, df, peak=False):
    if row['Nsrc'] == 1 :
        return 0.
    suffix = 'peak' if peak else 'int'
    weights = df[f'flux_{suffix}_err']**-2
    fluxes = df[f"flux_{suffix}"]
    eta = (row['Nsrc'] / (row['Nsrc']-1)) * (
        (weights*fluxes**2).mean() - ((weights*fluxes).mean()**2 / weights.mean())
    )
    return eta


def groupby_funcs(row, first_img):
    # calculated average ra, dec, fluxes and metrics
    d = {}
    for col in ['ave_ra','ave_dec','ave_flux_int','ave_flux_peak']:
        d[col] = row[col.split('_',1)[1]].mean()
    d['max_flux_peak'] = row['flux_peak'].max()

    for col in ['flux_int','flux_peak']:
        d[f'{col}_sq'] = (row[col]**2).mean()
    d['Nsrc'] = row['id'].count()
    d['v_int'] = row["flux_int"].std() / row["flux_int"].mean()
    d['v_peak'] = row["flux_peak"].std() / row["flux_peak"].mean()
    d['eta_int'] = get_eta_metric(d, row)
    d['eta_peak'] = get_eta_metric(d, row, peak=True)
    # remove not used cols
    for col in ['flux_int_sq','flux_peak_sq']:
        d.pop(col)
    d.pop('Nsrc')
    # set new catalog/source
    d['new'] = True if first_img in row['img'] else False
    return pd.Series(d)


def get_catalog_models(row, pipeline_run=None):
    name = f"src_{deg2hms(row['ave_ra'])}{deg2dms(row['ave_dec'])}"
    src = Source()
    src.run = pipeline_run
    src.name = name
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


def association(p_run, images, meas_dj_obj, limit):
    # read the needed sources fields
    cols = [
        'id',
        'ra',
        'dec',
        'flux_int',
        'flux_int_err',
        'flux_peak',
        'flux_peak_err'
    ]
    skyc1_srcs = pd.read_parquet(
        images[0].measurements_path,
        columns=cols
    )
    skyc1_srcs['img'] = images[0].name
    skyc1_srcs['cat'] = pd.np.NaN
    skyc1_srcs['ra_source'] = skyc1_srcs.ra
    skyc1_srcs['dec_source'] = skyc1_srcs.dec
    # create base catalog
    skyc1 = SkyCoord(
        ra=skyc1_srcs.ra * u.degree,
        dec=skyc1_srcs.dec * u.degree
    )
    # initialise the df of catalogs with the base one
    sources_df = pd.DataFrame()
    for it, image in enumerate(images[1:]):
        logger.info('Association iteration: #%i', (it + 1))
        # load skyc2 sources and create SkyCoord/sky catalog(skyc)
        skyc2_srcs = pd.read_parquet(
            image.measurements_path,
            columns=cols
        )
        skyc2_srcs['img'] = image.name
        skyc2_srcs['cat'] = pd.np.NaN
        skyc2_srcs['ra_source'] = skyc2_srcs.ra
        skyc2_srcs['dec_source'] = skyc2_srcs.dec
        skyc2 = SkyCoord(
            ra=skyc2_srcs.ra * u.degree,
            dec=skyc2_srcs.dec * u.degree
        )
        idx, d2d, d3d = skyc1.match_to_catalog_sky(skyc2)
        # selection
        sel = d2d <= limit

        # assign catalog temp id in skyc1 sorces df if not previously defined
        start_elem = 0. if skyc1_srcs.cat.max() is pd.np.NaN else skyc1_srcs.cat.max()
        nan_sel = skyc1_srcs.cat.isna().values
        skyc1_srcs.loc[ sel & nan_sel, 'cat'] = (
            skyc1_srcs.index[ sel & nan_sel].values + start_elem + 1.
        )
        # append skyc1 selection to catalog df
        sources_df = sources_df.append(skyc1_srcs)

        # assign catalog temp id to skyc2 sorces from skyc1
        skyc2_srcs.loc[idx[sel], 'cat'] = skyc1_srcs.loc[sel, 'cat'].values
        # append skyc2 selection to catalog df
        sources_df = sources_df.append(skyc2_srcs.loc[idx[sel]])
        # remove eventual duplicated values
        sources_df = sources_df.drop_duplicates(subset=['id','cat'])

        # update skyc1 and df for next association iteration
        # calculate average angles for skyc1
        skyc1_srcs = (
            skyc1_srcs.append(skyc2_srcs.loc[idx[~sel]])
            .reset_index(drop=True)
        )
        tmp_srcs_df = (
            sources_df.loc[sources_df.cat.notnull(), ['ra','dec','cat']]
            .groupby('cat')
            .mean()
            .reset_index()
        )
        skyc1_srcs = skyc1_srcs.merge(
            tmp_srcs_df,
            on='cat',
            how='left',
            suffixes=('', '_y')
        )
        del tmp_srcs_df
        skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'ra'] = skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'ra_y']
        skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'dec'] = skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'dec_y']
        skyc1_srcs = skyc1_srcs.drop(['ra_y', 'dec_y'], axis=1)
        skyc1 = SkyCoord(
            ra=skyc1_srcs.ra * u.degree,
            dec=skyc1_srcs.dec * u.degree
        )

    # add leftover souces from skyc2
    sources_df = (
        sources_df.append(skyc2_srcs.loc[idx[~sel]])
        .reset_index(drop=True)
    )
    start_elem = sources_df.cat.max() + 1.
    nan_sel = sources_df.cat.isna().values
    sources_df.loc[nan_sel, 'cat'] = (
        sources_df.index[nan_sel].values + start_elem
    )

    # tidy the df of catalogs to drop duplicated entries
    # to have unique rows of c_name and src_id
    sources_df = sources_df.drop_duplicates(subset=['id','cat'])

    # ra and dec columns are actually the average over each iteration
    # so remove ave ra and ave dec used for calculation and use
    # ra_source and dec_source columns
    sources_df = (
        sources_df.drop(['ra', 'dec'], axis=1)
        .rename(columns={'ra_source':'ra', 'dec_source':'dec'})
    )

    # calculate catalog fields
    srcs_df = sources_df.groupby('cat').apply(
        groupby_funcs, first_img=(images[0].name,)
    )
    # fill NaNs as resulted from calculated metrics with 0
    srcs_df =srcs_df.fillna(0.)

    # generate the catalog models
    srcs_df['src_dj'] = srcs_df.apply(
        get_catalog_models,
        axis=1,
        pipeline_run=p_run
    )
    # create sources in DB
    # TODO remove deleting existing sources
    if Source.objects.filter(run=p_run).exists():
        logger.info('removing objects from previous pipeline run')
        n_del, detail_del  = Source.objects.filter(run=p_run).delete()
        logger.info((
            'deleting all sources and related objects for this run. '
            'Total objects deleted: %i'
            ),
            n_del,
        )
        logger.debug('(type, #deleted): %s', detail_del)

    logger.info('uploading associations to db')
    batch_size = 10_000
    for idx in range(0, srcs_df.src_dj.size, batch_size):
        out_bulk = Source.objects.bulk_create(
            srcs_df.src_dj.iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('bulk created #%i sources', len(out_bulk))

    sources_df = (
        sources_df.merge(srcs_df, on='cat')
        .merge(meas_dj_obj, on='id')
    )
    del srcs_df

    # Create Associan objects (linking measurements into single sources)
    # and insert in DB
    sources_df['assoc_dj'] = sources_df.apply(
        lambda row: Association(
            meas=row['meas_dj'],
            source=row['src_dj']
        ), axis=1
    )
    batch_size = 10_000
    for idx in range(0, sources_df.assoc_dj.size, batch_size):
        out_bulk = Association.objects.bulk_create(
            sources_df.assoc_dj.iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('bulk created #%i associations', len(out_bulk))
