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
    # set new source
    d['new'] = False if first_img in row['img'].values else True
    return pd.Series(d)


def get_source_models(row, pipeline_run=None):
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
        'ra_err',
        'dec',
        'dec_err',
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
    # these are the first 'sources'
    skyc1_srcs['source'] = skyc1_srcs.index + 1
    skyc1_srcs['ra_source'] = skyc1_srcs.ra
    skyc1_srcs['ra_err_source'] = skyc1_srcs.ra_err
    skyc1_srcs['dec_source'] = skyc1_srcs.dec
    skyc1_srcs['dec_err_source'] = skyc1_srcs.dec_err
    skyc1_srcs['d2d'] = 0.0
    # create base catalogue
    skyc1 = SkyCoord(
        ra=skyc1_srcs.ra * u.degree,
        dec=skyc1_srcs.dec * u.degree
    )
    # initialise the sources dataframe using first image as base
    sources_df = skyc1_srcs.copy()
    for it, image in enumerate(images[1:]):
        logger.info('Association iteration: #%i', (it + 1))
        # load skyc2 source measurements and create SkyCoord
        skyc2_srcs = pd.read_parquet(
            image.measurements_path,
            columns=cols
        )
        skyc2_srcs['img'] = image.name
        skyc2_srcs['source'] = -1
        skyc2_srcs['ra_source'] = skyc2_srcs.ra
        skyc2_srcs['ra_err_source'] = skyc2_srcs.ra_err
        skyc2_srcs['dec_source'] = skyc2_srcs.dec
        skyc2_srcs['dec_err_source'] = skyc2_srcs.dec_err
        skyc2_srcs['d2d'] = 0.0
        skyc2 = SkyCoord(
            ra=skyc2_srcs.ra * u.degree,
            dec=skyc2_srcs.dec * u.degree
        )
        # match the new sources to the base
        # idx gives the index of the closest match in the base for skyc2
        idx, d2d, d3d = skyc2.match_to_catalog_sky(skyc1)
        # acceptable selection
        sel = d2d <= limit

        # The good matches can be assinged the cat id from base
        skyc2_srcs.loc[sel, 'cat'] = skyc1_srcs.loc[idx[sel], 'cat'].values.astype(int)
        # Need the d2d to make analysing doubles easier.
        skyc2_srcs.loc[sel, 'd2d'] = d2d[sel].arcsec

        # must check for double matches in the acceptable matches just made
        # this would mean that multiple sources in skyc2 have been matched to the same base source
        # we want to keep closest match and move the other match(es) back to having a NaN cat
        temp_matched_skyc2 = skyc2_srcs.dropna()
        if len(temp_matched_skyc2.cat.unique()) != len(temp_matched_skyc2.cat):
            logger.info("Double matches detected, cleaning...")
            # get the value counts
            cnts = temp_matched_skyc2.cat.value_counts()
            # and the cat ids that are doubled
            multi_cats = cnts[cnts > 1].index.values

            # now we have the cat values which are doubled.
            # make the nearest match have the original cat id
            # give the other matched source a new cat id
            for i, mcat in enumerate(multi_cats):
                # obtain the current start cat elem
                start_elem = sources_df.cat.max() + 1.
                skyc2_srcs_cut = skyc2_srcs[skyc2_srcs.cat == mcat]
                min_d2d_idx = skyc2_srcs_cut.d2d.idxmin()
                # set the other indexes to new cats
                # need to add copies of skyc1 source into the source_df
                # get the index of the skyc1 source
                skyc1_source_index =  skyc1_srcs[skyc1_srcs.cat == mcat].index.values[0]
                num_to_add = len(skyc2_srcs_cut.index) - 1
                # copy it n times needed
                skyc1_srcs_toadd = skyc1_srcs.loc[[skyc1_source_index for i in range(num_to_add)]]
                # Appy new cat ids to copies
                skyc1_srcs_toadd.cat = np.arange(start_elem, start_elem + num_to_add)
                # Change skyc2 sources to new cat ids
                idx_to_change = skyc2_srcs_cut.index.values[
                    skyc2_srcs_cut.index.values != min_d2d_idx
                ]
                skyc2_srcs.loc[idx_to_change, 'cat'] = skyc1_srcs_toadd.cat.values
                # append copies to source_df
                sources_df = sources_df.append(skyc1_srcs_toadd, ignore_index=True)
            logger.info("Cleaned {} double matches.".format(i + 1))

        del temp_matched_skyc2

        logger.info(
            "Updating sources catalogue with new sources..."
        )
        # update the cat numbers for those sources in skyc2 with no match
        # using the max current cat as the start and incrementing by one
        start_elem = sources_df.cat.max() + 1.
        nan_sel = skyc2_srcs.cat.isna().values
        skyc2_srcs.loc[nan_sel, 'cat'] = (
            np.arange(start_elem, start_elem+len(skyc2_srcs.loc[nan_sel].index))
        )

        # and skyc2 is now ready to be appended to new sources
        sources_df = sources_df.append(
            skyc2_srcs, ignore_index=True
        ).reset_index(drop=True)


        # update skyc1 and df for next association iteration
        # calculate average angles for skyc1
        skyc1_srcs = (
            skyc1_srcs.append(skyc2_srcs, ignore_index=True)
            .reset_index(drop=True)
        )

        logger.info(
            "Calculating weighted average RA and Dec for sources..."
        )
        #calculate weighted mean of ra and dec
        wm_ra = lambda x: np.average(x, weights=sources_df.loc[x.index, "ra_err"]/3600.)
        wm_dec = lambda x: np.average(x, weights=sources_df.loc[x.index, "dec_err"]/3600.)

        f = {'ra': wm_ra, 'dec': wm_dec }

        tmp_srcs_df = (
            sources_df.loc[sources_df.cat.notnull(), ['ra','dec','cat']]
            .groupby('cat')
            .agg(f)
            .reset_index()
        )

        logger.info(
            "Finalising base sources catalogue ready for next iteration..."
        )
        # merge the weighted ra and dec and replace the values
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

        #generate new sky coord ready for next iteration
        skyc1 = SkyCoord(
            ra=skyc1_srcs.ra * u.degree,
            dec=skyc1_srcs.dec * u.degree
        )
        logger.info('Association iteration: #%i complete.', (it + 1))

    # ra and dec columns are actually the average over each iteration
    # so remove ave ra and ave dec used for calculation and use
    # ra_source and dec_source columns
    sources_df = (
        sources_df.drop(['ra', 'dec'], axis=1)
        .rename(columns={'ra_source':'ra', 'dec_source':'dec'})
    )

    # calculate source fields
    logger.info(
        "Calculating statistics for {} sources...".format(
            len(sources_df.cat.unique())
        )
    )
    srcs_df = sources_df.groupby('cat').apply(
        groupby_funcs, first_img=images[0].name
    )
    # fill NaNs as resulted from calculated metrics with 0
    srcs_df =srcs_df.fillna(0.)

    # generate the source models
    srcs_df['src_dj'] = srcs_df.apply(
        get_source_models,
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
