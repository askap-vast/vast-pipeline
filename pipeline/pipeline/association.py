import logging
import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord

from ..models import Association, Catalog
from ..utils.utils import deg2hms, deg2dms


logger = logging.getLogger(__name__)


def get_eta_metric(row, df, peak=False):
    if row['Nsrc'] == 1 :
        return 0.
    suffix = 'peak' if peak else 'int'
    # weights
    w = df[f'flux_{suffix}_err']**-2
    w_mean = w.mean()

    # weighted means
    w_flux_mean = (w * df[f'flux_{suffix}']).mean()
    w_flux_sq_mean = (w * row[f'flux_{suffix}_sq']).mean()

    return row['Nsrc'] / (row['Nsrc'] - 1) * (
        w_flux_sq_mean - w_flux_mean**2 / w_mean
    )


def get_var_metric(row, df, peak=False):
    if row['Nsrc'] == 1 :
        return 0.
    suffix = 'peak' if peak else 'int'
    return row[f'ave_flux_{suffix}']**-1 * np.sqrt(
        row['Nsrc'] / (row['Nsrc'] - 1) * (
            row[f'flux_{suffix}_sq'].mean() - (
                df[f'flux_{suffix}'].mean()
            )**2
        )
    )


def groupby_funcs(row, first_img):
    # calculated average ra, dec, fluxes and metrics
    d = {}
    for col in ['ave_ra','ave_dec','ave_flux_int','ave_flux_peak']:
        d[col] = row[col.split('_',1)[1]].mean()
    d['max_flux_peak'] = row['flux_peak'].max()

    for col in ['flux_int','flux_peak']:
        d[f'{col}_sq'] = (row[col]**2).mean()
    d['Nsrc'] = row['id'].count()
    d['v_int'] = get_var_metric(d, row)
    d['v_peak'] = get_var_metric(d, row, peak=True)
    d['eta_int'] = get_eta_metric(d, row)
    d['eta_peak'] = get_eta_metric(d, row, peak=True)
    # remove not used cols
    for col in ['flux_int_sq','flux_peak_sq']:
        d.pop(col)
    d.pop('Nsrc')
    # set new catalog/source
    d['new'] = True if first_img in row['img'] else False
    return pd.Series(d)


def get_catalog_models(row, dataset=None):
    name = f"catalog_{deg2hms(row['ave_ra'])}{deg2dms(row['ave_dec'])}"
    cat = Catalog()
    cat.dataset = dataset
    cat.name = name
    for fld in cat._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(cat, fld.attname, row[fld.attname])
    return cat


def association(dataset, images, src_dj_obj, limit):
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
        images[0].sources_path,
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
    catalogs_df = pd.DataFrame()
    for it, image in enumerate(images[1:]):
        logger.info('Association iteration: #%i', (it + 1))
        # load skyc2 sources and create SkyCoord/sky catalog(skyc)
        skyc2_srcs = pd.read_parquet(
            image.sources_path,
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
        catalogs_df = catalogs_df.append(skyc1_srcs)

        # assign catalog temp id to skyc2 sorces from skyc1
        skyc2_srcs.loc[idx[sel], 'cat'] = skyc1_srcs.loc[sel, 'cat'].values
        # append skyc2 selection to catalog df
        catalogs_df = catalogs_df.append(skyc2_srcs.loc[idx[sel]])
        # remove eventual duplicated values
        catalogs_df = catalogs_df.drop_duplicates(subset=['id','cat'])

        # update skyc1 and df for next association iteration
        # calculate average angles for skyc1
        skyc1_srcs = (
            skyc1_srcs.append(skyc2_srcs.loc[idx[~sel]])
            .reset_index(drop=True)
        )
        tmp_cat_df = (
            catalogs_df.loc[catalogs_df.cat.notnull(), ['ra','dec','cat']]
            .groupby('cat')
            .mean()
            .reset_index()
        )
        skyc1_srcs = skyc1_srcs.merge(
            tmp_cat_df,
            on='cat',
            how='left',
            suffixes=('', '_y')
        )
        del tmp_cat_df
        skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'ra'] = skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'ra_y']
        skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'dec'] = skyc1_srcs.loc[skyc1_srcs.cat.notnull(), 'dec_y']
        skyc1_srcs = skyc1_srcs.drop(['ra_y', 'dec_y'], axis=1)
        skyc1 = SkyCoord(
            ra=skyc1_srcs.ra * u.degree,
            dec=skyc1_srcs.dec * u.degree
        )

    # add leftover souces from skyc2
    catalogs_df = (
        catalogs_df.append(skyc2_srcs.loc[idx[~sel]])
        .reset_index(drop=True)
    )
    start_elem = catalogs_df.cat.max() + 1.
    nan_sel = catalogs_df.cat.isna().values
    catalogs_df.loc[nan_sel, 'cat'] = (
        catalogs_df.index[nan_sel].values + start_elem
    )

    # tidy the df of catalogs to drop duplicated entries
    # to have unique rows of c_name and src_id
    catalogs_df = catalogs_df.drop_duplicates(subset=['id','cat'])

    # ra and dec columns are actually the average over each iteration
    # so remove ave ra and ave dec used for calculation and use
    # ra_source and dec_source columns
    catalogs_df = (
        catalogs_df.drop(['ra', 'dec'], axis=1)
        .rename(columns={'ra_source':'ra', 'dec_source':'dec'})
    )

    # calculate catalog fields
    cat_df = catalogs_df.groupby('cat').apply(
        groupby_funcs, first_img=(images[0].name,)
    )

    # generate the catalog models
    cat_df['cat_dj'] = cat_df.apply(
        get_catalog_models,
        axis=1,
        dataset=dataset
    )
    # create catalogs in DB
    # TODO remove deleting existing catalogs
    if Catalog.objects.filter(dataset=dataset).exists():
        logger.info('removing objects from previous pipeline run')
        n_del, detail_del  = Catalog.objects.filter(dataset=dataset).delete()
        logger.info((
            'deleting all catalogs and related objects for this dataset'
            ' (type, #deleted): %s. Total objects deleted: %i'
            ),
            detail_del,
            n_del,
        )

    logger.info('uploading associations to db')
    batch_size = 10_000
    for idx in range(0, cat_df.cat_dj.size, batch_size):
        out_bulk = Catalog.objects.bulk_create(
            cat_df.cat_dj.iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('bulk created #%i catalogs', len(out_bulk))

    catalogs_df = (
        catalogs_df.merge(cat_df, on='cat')
        .merge(src_dj_obj, on='id')
    )
    del cat_df

    # Create Associan objects (linking sources and catalogs) and insert in DB
    catalogs_df['assoc_dj'] = catalogs_df.apply(
        lambda row: Association(
            source=row['src_dj'],
            catalog=row['cat_dj']
        ), axis=1
    )
    batch_size = 10_000
    for idx in range(0, catalogs_df.assoc_dj.size, batch_size):
        out_bulk = Association.objects.bulk_create(
            catalogs_df.assoc_dj.iloc[idx : idx + batch_size].tolist(),
            batch_size
        )
        logger.info('bulk created #%i associations', len(out_bulk))
