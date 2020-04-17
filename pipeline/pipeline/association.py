import logging
import multiprocessing
import numpy as np
import pandas as pd
import dask.dataframe as dd

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle
from itertools import chain

from .loading import upload_associations, upload_sources
from .utils import get_or_append_list, prep_skysrc_df
from ..models import Association, Source
from ..utils.utils import deg2hms, deg2dms, StopWatch


logger = logging.getLogger(__name__)


def get_eta_metric(row, df, peak=False):
    '''
    Calculates the eta variability metric of a source.
    Works on the grouped by dataframe using the fluxes
    of the assoicated measurements.
    '''
    if row['Nsrc'] == 1:
        return 0.

    suffix = 'peak' if peak else 'int'
    weights = 1. / df[f'flux_{suffix}_err'].values**2
    fluxes = df[f'flux_{suffix}'].values
    eta = (row['Nsrc'] / (row['Nsrc']-1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta


def calc_de_ruiter(df):
    '''
    Calculates the unitless 'de Ruiter' radius of the
    association. Works on the 'temp_df' dataframe of the
    advanced association, where the two sources associated
    with each other have been merged into one row.
    '''
    ra_1 = df['ra_skyc1'].values
    ra_2 = df['ra_skyc2'].values

    # avoid wrapping issues
    ra_1[ra_1 > 270.] -= 180.
    ra_2[ra_2 > 270.] -= 180.
    ra_1[ra_1 < 90.] += 180.
    ra_2[ra_2 < 90.] += 180.

    ra_1 = np.deg2rad(ra_1)
    ra_2 = np.deg2rad(ra_2)

    ra_1_err = np.deg2rad(df['uncertainty_ew_skyc1'].values)
    ra_2_err = np.deg2rad(df['uncertainty_ew_skyc2'].values)

    dec_1 = np.deg2rad(df['dec_skyc1'].values)
    dec_2 = np.deg2rad(df['dec_skyc2'].values)

    dec_1_err = np.deg2rad(df['uncertainty_ns_skyc1'].values)
    dec_2_err = np.deg2rad(df['uncertainty_ns_skyc2'].values)

    dr1 = (ra_1 - ra_2) * (ra_1 - ra_2)
    dr1_1 = np.cos((dec_1 + dec_2) / 2.)
    dr1 *= dr1_1 * dr1_1
    dr1 /= ra_1_err * ra_1_err + ra_2_err * ra_2_err

    dr2 = (dec_1 - dec_2) * (dec_1 - dec_2)
    dr2 /= dec_1_err * dec_1_err + dec_2_err * dec_2_err

    dr = np.sqrt(dr1 + dr2)

    return dr


def groupby_funcs(row, first_img):
    '''
    Performs calculations on the unique sources to get the
    lightcurve properties. Works on the grouped by source
    dataframe.
    '''
    # calculated average ra, dec, fluxes and metrics
    d = {}
    d['wavg_ra'] = row['interim_ew'].sum() / row['weight_ew'].sum()
    d['wavg_dec'] = row['interim_ns'].sum() / row['weight_ns'].sum()
    d['wavg_uncertainty_ew'] = 1. / np.sqrt(row['weight_ew'].sum())
    d['wavg_uncertainty_ns'] = 1. / np.sqrt(row['weight_ns'].sum())
    for col in ['avg_flux_int', 'avg_flux_peak']:
        d[col] = row[col.split('_', 1)[1]].mean()
    d['max_flux_peak'] = row['flux_peak'].values.max()

    for col in ['flux_int', 'flux_peak']:
        d[f'{col}_sq'] = (row[col]**2).mean()
    d['Nsrc'] = row['id'].count()
    d['v_int'] = row['flux_int'].std() / row['flux_int'].mean()
    d['v_peak'] = row['flux_peak'].std() / row['flux_peak'].mean()
    d['eta_int'] = get_eta_metric(d, row)
    d['eta_peak'] = get_eta_metric(d, row, peak=True)
    # remove not used cols
    for col in ['flux_int_sq', 'flux_peak_sq']:
        d.pop(col)
    d.pop('Nsrc')
    # set new source
    d['new'] = False if first_img in row['img'].values else True

    # get unique related sources
    list_uniq_related = list(set(
        chain.from_iterable(
            lst for lst in row['related'] if isinstance(lst, list)
        )
    ))
    d['related_list'] = list_uniq_related if list_uniq_related else -1

    return pd.Series(d)


def get_source_models(row, pipeline_run=None):
    '''
    Fetches the source model (for DB injecting).
    '''
    name = f"src_{deg2hms(row['wavg_ra'])}{deg2dms(row['wavg_dec'])}"
    src = Source()
    src.run = pipeline_run
    src.name = name
    for fld in src._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(src, fld.attname, row[fld.attname])
    return src


def one_to_many_basic(sources_df, skyc2_srcs):
    '''
    Finds and processes the one-to-many associations in the basic
    association. For each one-to-many association, the nearest
    associated source is assigned the original source id, where as
    the others are given new ids. The original source in skyc1 then
    is copied to the sources_df to provide the extra association for
    that source, i.e. it is forked.

    This is needed to be separate from the advanced version
    as the data products between the two are different.
    '''
    # select duplicated in 'source' field in skyc2_srcs, excluding -1
    duplicated_skyc2 = skyc2_srcs.loc[
        (skyc2_srcs['source'] != -1) &
        skyc2_srcs['source'].duplicated(keep=False),
        ['source', 'd2d']
    ]
    if duplicated_skyc2.empty:
        logger.debug('No one-to-many associations.')
        return sources_df, skyc2_srcs

    logger.info(
        'Detected #%i double matches, cleaning...',
        duplicated_skyc2.shape[0]
    )
    multi_srcs = duplicated_skyc2['source'].unique()

    # now we have the src values which are doubled.
    # make the nearest match have the "original" src id
    # give the other matched source a new src id
    # and make sure to copy the other previously
    # matched sources.
    for i, msrc in enumerate(multi_srcs):
        # 1) assign new source id and
        # get the sky2_sources with this source id and
        # get the minimum d2d index
        src_selection = duplicated_skyc2['source'] == msrc
        min_d2d_idx = duplicated_skyc2.loc[
            src_selection,
            'd2d'
        ].idxmin()
        # Get the indexes of the other skyc2 sources
        # which need to be changed
        idx_to_change = duplicated_skyc2.index.values[
            (duplicated_skyc2.index.values != min_d2d_idx) &
            src_selection
        ]
        # how many new source ids we need to make?
        num_to_add = idx_to_change.shape[0]
        # obtain the current start src elem
        start_src_id = sources_df['source'].values.max() + 1
        # Set the new index range
        new_src_ids = np.arange(
            start_src_id,
            start_src_id + num_to_add,
            dtype=int
        )
        # Set the new index values in the skyc2
        skyc2_srcs.loc[idx_to_change, 'source'] = new_src_ids

        # populate the 'related' field in skyc2_srcs
        # original source with duplicated
        orig_src = skyc2_srcs.at[min_d2d_idx, 'related']
        if isinstance(orig_src, list):
            skyc2_srcs.at[min_d2d_idx, 'related'] = (
                orig_src + new_src_ids.tolist()
            )
        else:
            skyc2_srcs.at[min_d2d_idx, 'related'] = new_src_ids.tolist()
        # other sources with original
        skyc2_srcs.loc[idx_to_change, 'related'] = skyc2_srcs.loc[
            idx_to_change,
            'related'
        ].apply(get_or_append_list, elem=msrc)

        # 2) Check for generate copies of previous crossmatches in
        # 'sources_df' and match them with new source id
        # e.g. clone f1 and f2 in https://tkp.readthedocs.io/en/
        # latest/devref/database/assoc.html#one-to-many-association
        # and assign them to f3
        for new_id in new_src_ids:
            # Get all the previous crossmatches to be cloned
            sources_to_copy = sources_df.loc[
                sources_df['source'] == msrc
            ].copy()
            # change source id with new one
            sources_to_copy['source'] = new_id
            # append copies to "sources_df"
            sources_df = sources_df.append(
                sources_to_copy,
                ignore_index=True
            )
    logger.info('Cleaned %i double matches.', i + 1)

    return sources_df, skyc2_srcs


def one_to_many_advanced(temp_srcs, sources_df):
    '''
    Finds and processes the one-to-many associations in the basic
    association. The same logic is applied as in
    'one_to_many_basic.

    This is needed to be separate from the basic version
    as the data products between the two are different.
    '''
    # use only these columns for easy debugging of the dataframe
    cols = [
        'index_old_skyc1', 'id_skyc1', 'source_skyc1', 'd2d_skyc1',
        'related_skyc1', 'index_old_skyc2', 'id_skyc2', 'source_skyc2',
        'd2d_skyc2', 'related_skyc2', 'dr'
    ]
    duplicated_skyc1 = temp_srcs.loc[
        temp_srcs['source_skyc1'].duplicated(keep=False), cols
    ]
    if duplicated_skyc1.empty:
        logger.debug('No one-to-many associations.')
        return temp_srcs, sources_df

    logger.debug(
        'Detected #%i one-to-many assocations, cleaning...',
        duplicated_skyc1.shape[0]
    )
    # go through the doubles and
    # 1. Keep the closest de ruiter as the primary id
    # 2. Increment a new source id for others
    # 3. Add a copy of the previously matched
    # source into sources.
    multi_srcs = duplicated_skyc1['source_skyc1'].unique()
    for i, msrc in enumerate(multi_srcs):
        # Make the selection
        src_selection = duplicated_skyc1['source_skyc1'] == msrc
        # Get the min dr idx
        min_dr_idx = duplicated_skyc1.loc[src_selection, 'dr'].idxmin()
        # Select the others
        idx_to_change = duplicated_skyc1.index.values[
            (duplicated_skyc1.index.values != min_dr_idx) &
            src_selection
        ]
        # how many new source ids we need to make?
        num_to_add = idx_to_change.shape[0]
        # define a start src id for new forks
        start_src_id = sources_df['source'].values.max() + 1
        # Define new source ids
        new_src_ids = np.arange(
            start_src_id,
            start_src_id + num_to_add,
            dtype=int
        )
        # Apply the change to the temp sources
        temp_srcs.loc[idx_to_change, 'source_skyc1'] = new_src_ids
        # populate the 'related' field for skyc1
        # original source with duplicated
        orig_src = temp_srcs.at[min_dr_idx, 'related_skyc1']
        if isinstance(orig_src, list):
            temp_srcs.at[min_dr_idx, 'related_skyc1'] = (
                orig_src + new_src_ids.tolist()
            )
        else:
            temp_srcs.at[min_dr_idx, 'related_skyc1'] = new_src_ids.tolist()
        # other sources with original
        temp_srcs.loc[idx_to_change, 'related_skyc1'] = temp_srcs.loc[
            idx_to_change,
            'related_skyc1'
        ].apply(get_or_append_list, elem=msrc)

        # Check for generate copies of previous crossmatches and copy
        # the past source rows ready to append
        for new_id in new_src_ids:
            sources_to_copy = sources_df[
                sources_df['source'] == msrc
            ].copy()
            # change source id with new one
            sources_to_copy['source'] = new_id
            # append copies of skyc1 to source_df
            sources_df = sources_df.append(
                sources_to_copy,
                ignore_index=True
            )

    return temp_srcs, sources_df


def many_to_many_advanced(temp_srcs):
    '''
    Finds and processes the many-to-many associations in the advanced
    association. We do not want to build many-to-many associations as
    this will make the database get very large (see TraP documentation).
    The skyc2 sources which are listed more than once are found, and of
    these, those which have a skyc1 source association which is also
    listed twice in the associations are selected. The closest (by
    de Ruiter radius) is kept where as the other associations are dropped.

    This follows the same logic used by the TraP (see TraP documentation).
    '''
    # Select those where the extracted source is listed more than once
    # (e.g. index_old_skyc2 duplicated values) and of these get those that
    # have a source id that is listed more than once (e.g. source_skyc1
    # duplicated values) in the temps_srcs df
    m_to_m = temp_srcs[(
        temp_srcs['index_old_skyc2'].duplicated(keep=False) &
        temp_srcs['source_skyc1'].duplicated(keep=False)
    )].copy()
    if m_to_m.empty:
        logger.debug('No many-to-many assocations.')
        return temp_srcs

    logger.debug(
        'Detected #%i many-to-many assocations, cleaning...',
        m_to_m.shape[0]
    )
    # get the minimum de ruiter value for each extracted source
    m_to_m['min_dr'] = (
        m_to_m.groupby('index_old_skyc2')['dr']
        .transform('min')
    )
    # get the ids of those crossmatches that are larger than the minimum
    m_to_m_to_drop = m_to_m[m_to_m.dr != m_to_m.min_dr].index.values
    # and drop these from the temp_srcs
    temp_srcs = temp_srcs.drop(m_to_m_to_drop)

    return temp_srcs


def many_to_one_advanced(temp_srcs):
    '''
    Finds and processes the many-to-one associations in the advanced
    association.
    '''
    # use only these columns for easy debugging of the dataframe
    cols = [
        'index_old_skyc1', 'id_skyc1', 'source_skyc1', 'd2d_skyc1',
        'related_skyc1', 'index_old_skyc2', 'id_skyc2', 'source_skyc2',
        'd2d_skyc2', 'related_skyc2', 'dr'
    ]

    duplicated_skyc2 = temp_srcs.loc[
            temp_srcs['index_old_skyc2'].duplicated(keep=False),
            cols
    ]
    if duplicated_skyc2.empty:
        logger.debug('No many-to-one associations.')
        return temp_srcs

    logger.debug(
        'Detected #%i many-to-one associations',
        duplicated_skyc2.shape[0]
    )
    multi_srcs = duplicated_skyc2['index_old_skyc2'].unique()
    for i, msrc in enumerate(multi_srcs):
        # Make the selection
        src_sel_idx = duplicated_skyc2.loc[
            duplicated_skyc2['index_old_skyc2'] == msrc
        ].index
        # populate the 'related' field for skyc1
        for idx in src_sel_idx:
            related = temp_srcs.loc[
                src_sel_idx.drop(idx), 'source_skyc1'
            ].tolist()
            elem = temp_srcs.at[idx, 'related_skyc1']
            if isinstance(elem, list):
                temp_srcs.at[idx, 'related_skyc1'] = (
                    elem + related
                )
            else:
                temp_srcs.at[idx, 'related_skyc1'] = related

    return temp_srcs


def basic_association(
        sources_df, skyc1_srcs, skyc1, skyc2_srcs, skyc2, limit
    ):
    '''
    The loop for basic source association that uses the astropy
    'match_to_catalog_sky' function (i.e. only the nearest match between
    the catalogs). A direct on sky separation is used to define the association.
    '''
    # match the new sources to the base
    # idx gives the index of the closest match in the base for skyc2
    idx, d2d, d3d = skyc2.match_to_catalog_sky(skyc1)
    # acceptable selection
    sel = d2d <= limit

    # The good matches can be assinged the src id from base
    skyc2_srcs.loc[sel, 'source'] = skyc1_srcs.loc[idx[sel], 'source'].values
    # Need the d2d to make analysing doubles easier.
    skyc2_srcs.loc[sel, 'd2d'] = d2d[sel].arcsec

    # must check for double matches in the acceptable matches just made
    # this would mean that multiple sources in skyc2 have been matched
    #  to the same base source we want to keep closest match and move
    # the other match(es) back to having a -1 src id
    sources_df, skyc2_srcs = one_to_many_basic(sources_df, skyc2_srcs)

    logger.info('Updating sources catalogue with new sources...')
    # update the src numbers for those sources in skyc2 with no match
    # using the max current src as the start and incrementing by one
    start_elem = sources_df['source'].values.max() + 1
    nan_sel = (skyc2_srcs['source'] == -1).values
    skyc2_srcs.loc[nan_sel, 'source'] = (
        np.arange(
            start_elem,
            start_elem + skyc2_srcs.loc[nan_sel].shape[0],
            dtype=int
        )
    )

    # and skyc2 is now ready to be appended to new sources
    sources_df = sources_df.append(
        skyc2_srcs, ignore_index=True
    ).reset_index(drop=True)

    # update skyc1 and df for next association iteration
    # calculate average angles for skyc1
    skyc1_srcs = (
        skyc1_srcs.append(skyc2_srcs[nan_sel], ignore_index=True)
        .reset_index(drop=True)
    )

    return sources_df, skyc1_srcs


def advanced_association(
        sources_df, skyc1_srcs, skyc1,
        skyc2_srcs, skyc2, dr_limit, bw_max
    ):
    '''
    The loop for advanced source association that uses the astropy
    'search_around_sky' function (i.e. all matching sources are
    found). The BMAJ of the image * the user supplied beamwidth
    limit is the base distance for association. This is followed
    by calculating the 'de Ruiter' radius.
    '''
    # read the needed sources fields
    # Step 1: get matches within semimajor axis of image.
    idx_skyc1, idx_skyc2, d2d, d3d = skyc2.search_around_sky(
        skyc1, bw_max
    )
    # Step 2: Apply the beamwidth limit
    sel = d2d <= bw_max

    skyc2_srcs.loc[idx_skyc2[sel], 'd2d'] = d2d[sel].arcsec

    # Step 3: merge the candidates so the de ruiter can be calculated
    temp_skyc1_srcs = (
        skyc1_srcs.loc[idx_skyc1[sel]]
        .reset_index()
        .rename(columns={'index': 'index_old'})
    )
    temp_skyc2_srcs = (
        skyc2_srcs.loc[idx_skyc2[sel]]
        .reset_index()
        .rename(columns={'index': 'index_old'})
    )
    temp_srcs = temp_skyc1_srcs.merge(
        temp_skyc2_srcs,
        left_index=True,
        right_index=True,
        suffixes=('_skyc1', '_skyc2')
    )
    del temp_skyc1_srcs, temp_skyc2_srcs

    # Step 4: Calculate and perform De Ruiter radius cut
    temp_srcs['dr'] = calc_de_ruiter(temp_srcs)
    temp_srcs = temp_srcs[temp_srcs['dr'] <= dr_limit]

    # Now have the 'good' matches
    # Step 5: Check for one-to-many, many-to-one and many-to-many
    # associations. First the many-to-many
    temp_srcs = many_to_many_advanced(temp_srcs)

    # Next one-to-many
    # Get the sources which are doubled
    temp_srcs, sources_df = one_to_many_advanced(temp_srcs, sources_df)

    # Finally many-to-one associations, the opposite of above but we
    # don't have to create new ids for these so it's much simpler in fact
    # we don't need to do anything but lets get the number for debugging.
    temp_srcs = many_to_one_advanced(temp_srcs)

    # Now everything in place to append
    # First the skyc2 sources with a match.
    # This is created from the temp_srcs df.
    # This will take care of the extra skyc2 sources needed.
    skyc2_srcs_toappend = skyc2_srcs.loc[
        temp_srcs['index_old_skyc2'].values
    ].reset_index(drop=True)
    skyc2_srcs_toappend['source'] = temp_srcs['source_skyc1'].values
    skyc2_srcs_toappend['related'] = temp_srcs['related_skyc1'].values
    skyc2_srcs_toappend['dr'] = temp_srcs['dr'].values

    # and get the skyc2 sources with no match
    logger.info(
        'Updating sources catalogue with new sources...'
    )
    new_sources = skyc2_srcs.loc[
        skyc2_srcs.index.difference(
            temp_srcs['index_old_skyc2'].values
        )
    ].reset_index(drop=True)
    # update the src numbers for those sources in skyc2 with no match
    # using the max current src as the start and incrementing by one
    start_elem = sources_df['source'].values.max() + 1
    new_sources['source'] = np.arange(
        start_elem,
        start_elem + new_sources.shape[0],
        dtype=int
    )
    skyc2_srcs_toappend = skyc2_srcs_toappend.append(
        new_sources, ignore_index=True
    )

    # and skyc2 is now ready to be appended to source_df
    sources_df = sources_df.append(
        skyc2_srcs_toappend, ignore_index=True
    ).reset_index(drop=True)

    # update skyc1 and df for next association iteration
    # calculate average angles for skyc1
    skyc1_srcs = (
        skyc1_srcs.append(new_sources, ignore_index=True)
        .reset_index(drop=True)
    )

    return sources_df, skyc1_srcs


def association(p_run, images, meas_dj_obj, limit, dr_limit, bw_limit,
    config):
    '''
    The main association function that does the common tasks between basic
    and advanced modes.
    '''
    method = config.ASSOCIATION_METHOD
    logger.info('Association mode selected: %s.', method)

    # initialise sky source dataframe
    skyc1_srcs = prep_skysrc_df(
        images[0],
        config.FLUX_PERC_ERROR,
        ini_df=True
    )
    # create base catalogue
    skyc1 = SkyCoord(
        ra=skyc1_srcs['ra'].values * u.degree,
        dec=skyc1_srcs['dec'].values * u.degree
    )
    # initialise the sources dataframe using first image as base
    sources_df = skyc1_srcs.copy()

    for it, image in enumerate(images[1:]):
        logger.info('Association iteration: #%i', it + 1)
        # load skyc2 source measurements and create SkyCoord
        skyc2_srcs = prep_skysrc_df(image, config.FLUX_PERC_ERROR)
        skyc2 = SkyCoord(
            ra=skyc2_srcs['ra'].values * u.degree,
            dec=skyc2_srcs['dec'].values * u.degree
        )

        if method == 'basic':
            sources_df, skyc1_srcs = basic_association(
                sources_df,
                skyc1_srcs,
                skyc1,
                skyc2_srcs,
                skyc2,
                limit,
            )

        elif method == 'advanced':
            bw_max = Angle(
                bw_limit * (image.beam_bmaj * 3600. / 2.) * u.arcsec
            )
            sources_df, skyc1_srcs = advanced_association(
                sources_df,
                skyc1_srcs,
                skyc1,
                skyc2_srcs,
                skyc2,
                dr_limit,
                bw_max
            )
        else:
            raise Exception('association method not implemented!')

        logger.info(
            'Calculating weighted average RA and Dec for sources...'
        )

        # account for RA wrapping
        ra_wrap_mask = sources_df.ra <= 0.1
        sources_df['ra_wrap'] = sources_df.ra.values
        sources_df.at[
            ra_wrap_mask, 'ra_wrap'
        ] = sources_df[ra_wrap_mask].ra.values + 360.

        sources_df['interim_ew'] = (
            sources_df['ra_wrap'].values * sources_df['weight_ew'].values
        )
        sources_df['interim_ns'] = (
            sources_df['dec'].values * sources_df['weight_ns'].values
        )

        sources_df.drop(['ra_wrap'], axis=1)

        tmp_srcs_df = (
            sources_df.loc[sources_df['source'] != -1, [
                'ra', 'dec', 'uncertainty_ew', 'uncertainty_ns',
                'source', 'interim_ew', 'interim_ns', 'weight_ew',
                'weight_ns'
            ]]
            .groupby('source')
        )

        stats = StopWatch()

        wm_ra = tmp_srcs_df['interim_ew'].sum() / tmp_srcs_df['weight_ew'].sum()
        wm_uncertainty_ew = 1. / np.sqrt(tmp_srcs_df['weight_ew'].sum())

        wm_dec = tmp_srcs_df['interim_ns'].sum() / tmp_srcs_df['weight_ns'].sum()
        wm_uncertainty_ns = 1. / np.sqrt(tmp_srcs_df['weight_ns'].sum())

        weighted_df = (
            pd.concat(
                [wm_ra, wm_uncertainty_ew, wm_dec, wm_uncertainty_ns],
                axis=1,
                sort=False
            )
            .reset_index()
            .rename(
                columns={
                    0: 'ra',
                    'weight_ew': 'uncertainty_ew',
                    1: 'dec',
                    'weight_ns': 'uncertainty_ns'
            })
        )

        # correct the RA wrapping
        ra_wrap_mask = weighted_df.ra >= 360.
        weighted_df.at[
            ra_wrap_mask, 'ra'
        ] = weighted_df[ra_wrap_mask].ra.values - 360.

        logger.debug('Groupby concat time %f', stats.reset())

        logger.info(
            'Finalising base sources catalogue ready for next iteration...'
        )
        # merge the weighted ra and dec and replace the values
        skyc1_srcs = skyc1_srcs.merge(
            weighted_df,
            on='source',
            how='left',
            suffixes=('', '_skyc2')
        )
        del tmp_srcs_df
        del weighted_df
        skyc1_srcs['ra'] = skyc1_srcs['ra_skyc2']
        skyc1_srcs['dec'] = skyc1_srcs['dec_skyc2']
        skyc1_srcs['uncertainty_ew'] = skyc1_srcs['uncertainty_ew_skyc2']
        skyc1_srcs['uncertainty_ns'] = skyc1_srcs['uncertainty_ns_skyc2']
        skyc1_srcs = skyc1_srcs.drop(
            [
                'ra_skyc2',
                'dec_skyc2',
                'uncertainty_ew_skyc2',
                'uncertainty_ns_skyc2'
            ], axis=1
        )

        #generate new sky coord ready for next iteration
        skyc1 = SkyCoord(
            ra=skyc1_srcs['ra'] * u.degree,
            dec=skyc1_srcs['dec'] * u.degree
        )
        logger.info('Association iteration #%i complete.', it + 1)

    # End of iteration over images, move to stats calcs and Django
    # association model generation
    # ra and dec columns are actually the average over each iteration
    # so remove ave ra and ave dec used for calculation and use
    # ra_source and dec_source columns
    sources_df = (
        sources_df.drop(['ra', 'dec'], axis=1)
        .rename(columns={'ra_source':'ra', 'dec_source':'dec'})
    )

    # calculate source fields
    logger.info(
        'Calculating statistics for %i sources...',
        sources_df.source.unique().shape[0]
    )
    stats = StopWatch()
    n_cpu = multiprocessing.cpu_count() - 1
    srcs_df_dask = dd.from_pandas(sources_df, n_cpu)
    srcs_df = srcs_df_dask.groupby('source').apply(
        groupby_funcs, first_img=images[0].name
    ).compute(num_workers=n_cpu, scheduler='processes')
    logger.info('Groupby-apply time: %.2f', stats.reset())
    # fill NaNs as resulted from calculated metrics with 0
    srcs_df = srcs_df.fillna(0.)

    # correct the RA wrapping
    ra_wrap_mask = srcs_df.wavg_ra >= 360.
    srcs_df.at[
        ra_wrap_mask, 'wavg_ra'
    ] = srcs_df[ra_wrap_mask].wavg_ra.values - 360.

    # generate the source models
    srcs_df['src_dj'] = srcs_df.apply(
        get_source_models,
        pipeline_run=p_run,
        axis=1
    )
    # upload sources and related to DB
    upload_sources(p_run, srcs_df)

    sources_df = (
        sources_df.drop('related', axis=1)
        .merge(srcs_df.drop('related_list', axis=1), on='source')
        .merge(meas_dj_obj, on='id')
    )
    del srcs_df

    # Create Associan objects (linking measurements into single sources)
    # and insert in DB
    sources_df['assoc_dj'] = sources_df.apply(
        lambda row: Association(
            meas=row['meas_dj'],
            source=row['src_dj'],
            d2d=row['d2d'],
            dr=row['dr'],
        ), axis=1
    )
    # upload associations in DB
    upload_associations(sources_df['assoc_dj'])
