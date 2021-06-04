"""
This module contains all the functions required to perform source association.
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, List
import dask.dataframe as dd
from psutil import cpu_count

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle

from .utils import (
    prep_skysrc_df,
    add_new_one_to_many_relations,
    add_new_many_to_one_relations,
    reconstruct_associtaion_dfs
)
from vast_pipeline.pipeline.config import PipelineConfig
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


def calc_de_ruiter(df: pd.DataFrame) -> np.ndarray:
    """
    Calculates the unitless 'de Ruiter' radius of the
    association. Works on the 'temp_df' dataframe of the
    advanced association, where the two sources associated
    with each other have been merged into one row.

    Args:
        df:
            The 'temp_df' from advanced association. It must
            contain the columns `ra_skyc1`, 'ra_skyc2', 'uncertainty_ew_skyc1',
            'uncertainty_ew_skyc2', 'dec_skyc1', 'dec_skyc2',
            'uncertainty_ns_skyc1' and 'uncertainty_ns_skyc2'.

    Returns:
        Array containing the de Ruiter radius for all rows in the df.
    """
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


def one_to_many_basic(
    skyc2_srcs: pd.DataFrame, sources_df: pd.DataFrame,
    id_incr_par_assoc: int=0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Finds and processes the one-to-many associations in the basic
    association. For each one-to-many association, the nearest
    associated source is assigned the original source id, where as
    the others are given new ids. The original source in skyc1 then
    is copied to the sources_df to provide the extra association for
    that source, i.e. it is forked.

    This is needed to be separate from the advanced version
    as the data products between the two are different.

    Args:
        skyc2_srcs: The sky catalogue 2 sources (i.e. the sources being
            associated to the base) used during basic association.
        sources_df: The sources_df produced by each step of
            association holding the current 'sources'.
        id_incr_par_assoc: An increment value to add to new source ids
            when creating them. Mainly useful for add mode with parallel
            association

    Returns:
        Tuple containging the updated 'skyc2_srcs' and 'sources_df' with
        all one_to_many relation information added.
    """
    # select duplicated in 'source' field in skyc2_srcs, excluding -1
    duplicated_skyc2 = skyc2_srcs.loc[
        (skyc2_srcs['source'] != -1) &
        skyc2_srcs['source'].duplicated(keep=False),
        ['source', 'related', 'd2d']
    ]

    # duplicated_skyc2
    # +-----+----------+-----------+---------+
    # |     |   source | related   |     d2d |
    # |-----+----------+-----------+---------|
    # | 264 |      254 |           | 2.04422 |
    # | 265 |      254 |           | 6.16881 |
    # | 327 |      262 |           | 3.20439 |
    # | 328 |      262 |           | 3.84425 |
    # | 526 |      122 |           | 3.07478 |
    # +-----+----------+-----------+---------+

    if duplicated_skyc2.empty:
        logger.debug('No one-to-many associations.')
        return skyc2_srcs, sources_df

    logger.info(
        'Detected #%i double matches, cleaning...',
        duplicated_skyc2.shape[0]
    )

    # now we have the src values which are doubled.
    # make the nearest match have the "original" src id
    # give the other matched source a new src id
    # and make sure to copy the other previously
    # matched sources.
    # Get the duplicated, sort by the distance column
    duplicated_skyc2 = duplicated_skyc2.sort_values(by=['source', 'd2d'])

    # Get those that need to be given a new ID number (i.e. not the min dist_col)
    idx_to_change = duplicated_skyc2.index.values[
        duplicated_skyc2.duplicated('source')
    ]

    # Create a new `new_source_id` column to store the 'correct' IDs
    duplicated_skyc2['new_source_id'] = duplicated_skyc2['source']

    # Define the range of new source ids
    start_new_src_id = sources_df['source'].values.max() + 1 + id_incr_par_assoc

    new_source_ids = np.arange(
        start_new_src_id,
        start_new_src_id + idx_to_change.shape[0],
        dtype=int
    )

    # Assign the new IDs
    duplicated_skyc2.loc[idx_to_change, 'new_source_id'] = new_source_ids

    # duplicated_skyc2
    # +-----+----------+-----------+---------+-----------------+
    # |     |   source | related   |     d2d |   new_source_id |
    # |-----+----------+-----------+---------+-----------------|
    # | 526 |      122 |           | 3.07478 |             122 |
    # | 528 |      122 |           | 6.41973 |            5542 |
    # | 264 |      254 |           | 2.04422 |             254 |
    # | 265 |      254 |           | 6.16881 |            5543 |
    # | 327 |      262 |           | 3.20439 |             262 |
    # +-----+----------+-----------+---------+-----------------+

    # Now we need to sort out the related, essentially here the 'original'
    # and 'non original' need to be treated differently.
    # The original source need all the assoicated new ids appended to the
    # related column.
    # The not_original ones need just the original ID appended.
    # copy() is used here to avoid chained indexing (set with copy warnings)
    not_original = duplicated_skyc2.loc[
        idx_to_change
    ].copy()

    original = duplicated_skyc2.drop_duplicates(
        'source'
    ).copy()

    new_original_related = pd.DataFrame(
        not_original[
            ['source', 'new_source_id']
        ].groupby('source').apply(
            lambda grp: grp['new_source_id'].tolist()
        )
    )

    # new_original_related
    # +----------+--------+
    # |   source | 0      |
    # |----------+--------|
    # |      122 | [5542] |
    # |      254 | [5543] |
    # |      262 | [5544] |
    # |      405 | [5545] |
    # |      656 | [5546] |
    # +----------+--------+

    # Append the relations in each case, using the above 'new_original_related'
    # for the original ones.
    # The not original only require the appending of the original index.
    original['related'] = (
        original[['related', 'source']]
        .apply(
            add_new_one_to_many_relations,
            args=(False, new_original_related),
            axis=1
        )
    )

    not_original['related'] = not_original.apply(
        add_new_one_to_many_relations,
        args=(False,),
        axis=1
    )

    duplicated_skyc2 = original.append(not_original)

    # duplicated_skyc2
    # +-----+----------+-----------+---------+-----------------+
    # |     |   source | related   |     d2d |   new_source_id |
    # |-----+----------+-----------+---------+-----------------|
    # | 526 |      122 | [5542]    | 3.07478 |             122 |
    # | 264 |      254 | [5543]    | 2.04422 |             254 |
    # | 327 |      262 | [5544]    | 3.20439 |             262 |
    # | 848 |      405 | [5545]    | 5.52865 |             405 |
    # | 695 |      656 | [5546]    | 4.69094 |             656 |
    # +-----+----------+-----------+---------+-----------------+

    del original, not_original

    # Apply the updates to the actual temp_srcs.
    skyc2_srcs.loc[idx_to_change, 'source'] = new_source_ids
    skyc2_srcs.loc[
        duplicated_skyc2.index.values,
        'related'
    ] = duplicated_skyc2.loc[
        duplicated_skyc2.index.values,
        'related'
    ].values

    # Finally we need to copy copies of the previous sources in the
    # sources_df to complete the new sources.

    # To do this we get only the non-original sources
    duplicated_skyc2 = duplicated_skyc2.loc[
        duplicated_skyc2.duplicated('source')
    ]

    # Get all the indexes required for each original
    # `source_skyc1` value
    source_df_index_to_copy = pd.DataFrame(
        duplicated_skyc2.groupby(
            'source'
        ).apply(
            lambda grp: sources_df[
                sources_df['source'] == grp.name
            ].index.values.tolist()
        )
    )

    # source_df_index_to_copy
    # +----------+-------+
    # |   source | 0     |
    # |----------+-------|
    # |      122 | [121] |
    # |      254 | [253] |
    # |      262 | [261] |
    # |      405 | [404] |
    # |      656 | [655] |
    # +----------+-------+

    # merge these so it's easy to explode and copy the index values.
    duplicated_skyc2 = (
        duplicated_skyc2[['source', 'new_source_id']]
        .merge(
            source_df_index_to_copy,
            left_on='source',
            right_index=True,
            how='left'
        )
        .rename(columns={0: 'source_index'})
        .explode('source_index')
    )

    # Get the sources - all columns from the sources_df table
    sources_to_copy = sources_df.loc[
        duplicated_skyc2['source_index'].values
    ]

    # Apply the new_source_id
    sources_to_copy['source'] = duplicated_skyc2['new_source_id'].values

    # Reset the related column to avoid rogue relations
    sources_to_copy['related'] = None

    # and finally append.
    sources_df = sources_df.append(
        sources_to_copy,
        ignore_index=True
    )

    return skyc2_srcs, sources_df


def one_to_many_advanced(
    temp_srcs: pd.DataFrame,
    sources_df: pd.DataFrame,
    method: str,
    id_incr_par_assoc: int=0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    '''
    Finds and processes the one-to-many associations in the advanced
    association. For each one-to-many association, the nearest
    associated source is assigned the original source id, where as
    the others are given new ids. The original source in skyc1 then
    is copied to the sources_df to provide the extra association for
    that source, i.e. it is forked.

    This is needed to be separate from the basic version
    as the data products between the two are different.

    Args:
        temp_srcs:
            The temporary associtation dataframe used through the advanced
            association process.
        sources_df:
            The sources_df produced by each step of association holding
            the current 'sources'.
        method:
            Can be either 'advanced' or 'deruiter' to represent the advanced
            association method being used.
        id_incr_par_assoc:
            An increment value to add to new source ids when creating them.
            Mainly useful for add mode with parallel association

    Returns:
        Updated temp_srcs and sources_df with all one_to_many relation
        information added.
    '''
    # use only these columns for easy debugging of the dataframe
    cols = [
        'index_old_skyc1', 'id_skyc1', 'source_skyc1', 'd2d_skyc1',
        'related_skyc1', 'index_old_skyc2', 'id_skyc2', 'source_skyc2',
        'd2d_skyc2', 'dr'
    ]
    duplicated_skyc1 = temp_srcs.loc[
        temp_srcs['source_skyc1'].duplicated(keep=False), cols
    ].copy()

    # duplicated_skyc1
    # +-----+-------------------+------------+----------------+-------------+
    # |     |   index_old_skyc1 |   id_skyc1 |   source_skyc1 |   d2d_skyc1 |
    # |-----+-------------------+------------+----------------+-------------+
    # | 117 |               121 |        122 |            122 |           0 |
    # | 118 |               121 |        122 |            122 |           0 |
    # | 238 |               253 |        254 |            254 |           0 |
    # | 239 |               253 |        254 |            254 |           0 |
    # | 246 |               261 |        262 |            262 |           0 |
    # +-----+-------------------+------------+----------------+-------------+
    # -----------------+-------------------+------------+----------------+
    #  related_skyc1   |   index_old_skyc2 |   id_skyc2 |   source_skyc2 |
    # -----------------+-------------------+------------+----------------+
    #                  |               526 |       6068 |             -1 |
    #                  |               528 |       6070 |             -1 |
    #                  |               264 |       5806 |             -1 |
    #                  |               265 |       5807 |             -1 |
    #                  |               327 |       5869 |             -1 |
    # -----------------+-------------------+------------+----------------+
    # -------------+------+
    #    d2d_skyc2 |   dr |
    # -------------+------|
    #      3.07478 |    0 |
    #      6.41973 |    0 |
    #      2.04422 |    0 |
    #      6.16881 |    0 |
    #      3.20439 |    0 |
    # -------------+------+

    # If no relations then no action is required
    if duplicated_skyc1.empty:
        logger.debug('No one-to-many associations.')
        return temp_srcs, sources_df

    logger.debug(
        'Detected #%i one-to-many assocations, cleaning...',
        duplicated_skyc1.shape[0]
    )

    # Get the column to check for the minimum depending on the method
    # set the column names needed for filtering the 'to-many'
    # associations depending on the method (advanced or deruiter)
    dist_col = 'd2d_skyc2' if method == 'advanced' else 'dr'

    # go through the doubles and
    # 1. Keep the closest d2d or de ruiter as the primary id
    # 2. Increment a new source id for others
    # 3. Add a copy of the previously matched
    # source into sources.
    # multi_srcs = duplicated_skyc1['source_skyc1'].unique()

    # Get the duplicated, sort by the distance column
    duplicated_skyc1 = duplicated_skyc1.sort_values(
        by=['source_skyc1', dist_col]
    )

    # Get those that need to be given a new ID number (i.e. not the min dist_col)
    idx_to_change = duplicated_skyc1.index.values[
        duplicated_skyc1.duplicated('source_skyc1')
    ]

    # Create a new `new_source_id` column to store the 'correct' IDs
    duplicated_skyc1['new_source_id'] = duplicated_skyc1['source_skyc1']

    # +-----------------+
    # |   new_source_id |
    # +-----------------|
    # |             122 |
    # |             122 |
    # |             254 |
    # |             254 |
    # |             262 |
    # +-----------------+

    # Define the range of new source ids
    start_new_src_id = sources_df['source'].values.max() + 1 + id_incr_par_assoc

    # Create an arange to use to change the ones that need to be changed.
    new_source_ids = np.arange(
        start_new_src_id,
        start_new_src_id + idx_to_change.shape[0],
        dtype=int
    )

    # Assign the new IDs to those that need to be changed.
    duplicated_skyc1.loc[idx_to_change, 'new_source_id'] = new_source_ids

    # We also need to clear the relations for these 'new' sources
    # otherwise it will inherit rogue relations from the original relation
    duplicated_skyc1.loc[idx_to_change, 'related_skyc1'] = None

    # Now we need to sort out the related, essentially here the 'original'
    # and 'non original' need to be treated differently.
    # The original source need all the assoicated new ids appended to the
    # related column.
    # The not_original ones need just the original ID appended.
    not_original = duplicated_skyc1.loc[
        idx_to_change
    ].copy()

    original = duplicated_skyc1.drop_duplicates(
        'source_skyc1'
    ).copy()

    # This gathers all the new ids that need to be appended
    # to the original related column.
    new_original_related = pd.DataFrame(
        not_original[
            ['source_skyc1', 'new_source_id']
        ].groupby('source_skyc1').apply(
            lambda grp: grp['new_source_id'].tolist()
        )
    )

    #new_original_related
    # +----------------+--------+
    # |   source_skyc1 | 0      |
    # |----------------+--------|
    # |            122 | [5542] |
    # |            254 | [5543] |
    # |            262 | [5544] |
    # |            405 | [5545] |
    # |            656 | [5546] |
    # +----------------+--------+

    # Append the relations in each case, using the above 'new_original_related'
    # for the original ones.
    # The not original only require the appending of the original index.
    original['related_skyc1'] = (
        original[['related_skyc1', 'source_skyc1']]
        .apply(
            add_new_one_to_many_relations,
            args=(True, new_original_related),
            axis=1
        )
    )

    # what the column looks like after the above
    # +-----------------+
    # | related_skyc1   |
    # +-----------------+
    # | [5542]          |
    # | [5543]          |
    # | [5544]          |
    # | [5545]          |
    # | [5546]          |
    # +-----------------+

    not_original.loc[:, 'related_skyc1'] = not_original.apply(
        add_new_one_to_many_relations,
        args=(True,),
        axis=1
    )

    # Merge them back together
    duplicated_skyc1 = original.append(not_original)

    del original, not_original

    # Apply the updates to the actual temp_srcs.
    temp_srcs.loc[idx_to_change, 'source_skyc1'] = new_source_ids
    temp_srcs.loc[
        duplicated_skyc1.index.values,
        'related_skyc1'
    ] = duplicated_skyc1.loc[
        duplicated_skyc1.index.values,
        'related_skyc1'
    ].values

    # Finally we need to create copies of the previous sources in the
    # sources_df to complete the new sources.

    # To do this we get only the non-original sources
    duplicated_skyc1 = duplicated_skyc1.loc[
        duplicated_skyc1.duplicated('source_skyc1')
    ]

    # Get all the indexes required for each original
    # `source_skyc1` value
    source_df_index_to_copy = pd.DataFrame(
        duplicated_skyc1.groupby(
            'source_skyc1'
        ).apply(
            lambda grp: sources_df[
                sources_df['source'] == grp.name
            ].index.values.tolist()
        )
    )

    # source_df_index_to_copy
    # +----------------+-------+
    # |   source_skyc1 | 0     |
    # |----------------+-------|
    # |            122 | [121] |
    # |            254 | [253] |
    # |            262 | [261] |
    # |            405 | [404] |
    # |            656 | [655] |
    # +----------------+-------+

    # merge these so it's easy to explode and copy the index values.
    duplicated_skyc1 = (
        duplicated_skyc1.loc[:,['source_skyc1', 'new_source_id']]
        .merge(
            source_df_index_to_copy,
            left_on='source_skyc1',
            right_index=True,
            how='left'
        )
        .rename(columns={0: 'source_index'})
        .explode('source_index')
    )

    # duplicated_skyc1
    # +-----+----------------+-----------------+----------------+
    # |     |   source_skyc1 |   new_source_id |   source_index |
    # |-----+----------------+-----------------+----------------|
    # | 118 |            122 |            5542 |            121 |
    # | 239 |            254 |            5543 |            253 |
    # | 247 |            262 |            5544 |            261 |
    # | 380 |            405 |            5545 |            404 |
    # | 615 |            656 |            5546 |            655 |
    # +-----+----------------+-----------------+----------------+

    # Get the sources
    sources_to_copy = sources_df.loc[
        duplicated_skyc1['source_index'].values
    ]

    # Apply the new_source_id
    sources_to_copy['source'] = duplicated_skyc1['new_source_id'].values

    # Reset the related column to avoid rogue relations
    sources_to_copy['related'] = None

    # and finally append.
    sources_df = sources_df.append(
        sources_to_copy,
        ignore_index=True
    )

    return temp_srcs, sources_df


def many_to_many_advanced(temp_srcs: pd.DataFrame, method: str) -> pd.DataFrame:
    '''
    Finds and processes the many-to-many associations in the advanced
    association. We do not want to build many-to-many associations as
    this will make the database get very large (see TraP documentation).
    The skyc2 sources which are listed more than once are found, and of
    these, those which have a skyc1 source association which is also
    listed twice in the associations are selected. The closest (by
    limit or de Ruiter radius, depending on the method) is kept where
    as the other associations are dropped.

    This follows the same logic used by the TraP (see TraP documentation).

    Args:
        temp_srcs:
            The temporary associtation dataframe used through the advanced
            association process.
        method:
            Can be either 'advanced' or 'deruiter' to represent the advanced
            association method being used.

    Returns:
        Updated temp_srcs with the many_to_many relations dropped.
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

    dist_col = 'd2d_skyc2' if method == 'advanced' else 'dr'
    min_col = 'min_' + dist_col

    # get the minimum de ruiter value for each extracted source
    m_to_m[min_col] = (
        m_to_m.groupby('index_old_skyc2')[dist_col]
        .transform('min')
    )
    # get the ids of those crossmatches that are larger than the minimum
    m_to_m_to_drop = m_to_m[m_to_m[dist_col] != m_to_m[min_col]].index.values
    # and drop these from the temp_srcs
    temp_srcs = temp_srcs.drop(m_to_m_to_drop)

    return temp_srcs


def many_to_one_advanced(temp_srcs: pd.DataFrame) -> pd.DataFrame:
    '''
    Finds and processes the many-to-one associations in the advanced
    association. In this case in the related column of the 'many' sources
    we need to append the ids of all the other 'many' (expect for itself).

    Args:
        temp_srcs:
            The temporary associtation dataframe used through the advanced
            association process.

    Returns:
        Updated temp_srcs with all many_to_one relation information added.
    '''
    # use only these columns for easy debugging of the dataframe
    cols = [
        'index_old_skyc1', 'id_skyc1', 'source_skyc1', 'd2d_skyc1',
        'related_skyc1', 'index_old_skyc2', 'id_skyc2', 'source_skyc2',
        'd2d_skyc2', 'dr'
    ]

    # select those sources which have been matched to the same measurement
    # in the sky catalogue 2.
    duplicated_skyc2 = temp_srcs.loc[
        temp_srcs['index_old_skyc2'].duplicated(keep=False),
        cols
    ]

    # duplicated_skyc2
    # +-----+-------------------+------------+----------------+-------------
    # |     |   index_old_skyc1 |   id_skyc1 |   source_skyc1 |   d2d_skyc1
    # |-----+-------------------+------------+----------------+-------------
    # | 447 |               477 |        478 |            478 |           0
    # | 448 |               478 |        479 |            479 |           0
    # | 477 |               507 |        508 |            508 |           0
    # | 478 |               508 |        509 |            509 |           0
    # | 695 |               738 |        739 |            739 |           0
    # +-----+-------------------+------------+----------------+-------------
    # +-----------------+-------------------+------------+----------------+
    # | related_skyc1   |   index_old_skyc2 |   id_skyc2 |   source_skyc2 |
    # +-----------------+-------------------+------------+----------------+
    # |                 |               305 |       5847 |             -1 |
    # |                 |               305 |       5847 |             -1 |
    # |                 |               648 |       6190 |             -1 |
    # |                 |               648 |       6190 |             -1 |
    # |                 |               561 |       6103 |             -1 |
    # +-----------------+-------------------+------------+----------------+
    # -------------+------+
    #    d2d_skyc2 |   dr |
    # -------------+------|
    #      8.63598 |    0 |
    #      8.63598 |    0 |
    #      6.5777  |    0 |
    #      6.5777  |    0 |
    #      7.76527 |    0 |
    # -------------+------+

    # if there are none no action is required.
    if duplicated_skyc2.empty:
        logger.debug('No many-to-one associations.')
        return temp_srcs

    logger.debug(
        'Detected #%i many-to-one associations',
        duplicated_skyc2.shape[0]
    )

    # The new relations become that for each 'many' source we need to append
    # the ids of the other 'many' sources that have been associationed with the
    # 'one'. Below for each 'one' group we gather all the ids of the many
    # sources.
    new_relations = pd.DataFrame(
        duplicated_skyc2
        .groupby('index_old_skyc2')
        .apply(lambda grp: grp['source_skyc1'].tolist())
    ).rename(columns={0: 'new_relations'})

    # new_relations
    # +-------------------+-----------------+
    # |   index_old_skyc2 | new_relations   |
    # |-------------------+-----------------|
    # |               305 | [478, 479]      |
    # |               561 | [739, 740]      |
    # |               648 | [508, 509]      |
    # |               764 | [841, 842]      |
    # |               816 | [1213, 1215]    |
    # +-------------------+-----------------+

    # these new relations are then added to the duplciated dataframe so
    # they can easily be used by the next function.
    duplicated_skyc2 = duplicated_skyc2.merge(
        new_relations,
        left_on='index_old_skyc2',
        right_index=True,
        how='left'
    )

    # Remove the 'self' relations. The 'x['source_skyc1']' is an integer so it
    # is placed within a list notation, [], to be able to be easily subtracted
    # from the new_relations.
    duplicated_skyc2['new_relations'] = (
        duplicated_skyc2.apply(
            lambda x: list(set(x['new_relations']) - set([x['source_skyc1']])),
            axis=1
        )
    )

    # Use the 'add_new_many_to_one_relations' method to add tthe new relatitons
    # to the actual `related_skyc1' column.
    duplicated_skyc2['related_skyc1'] = (
        duplicated_skyc2.apply(
            add_new_many_to_one_relations,
            axis=1
        )
    )

    # Transfer the new relations from the duplicated df to the temp_srcs. The
    # index is explicitly declared to avoid any mixups.
    temp_srcs.loc[
        duplicated_skyc2.index.values, 'related_skyc1'
    ] = duplicated_skyc2.loc[
        duplicated_skyc2.index.values, 'related_skyc1'
    ].values

    return temp_srcs


def basic_association(
        sources_df: pd.DataFrame, skyc1_srcs: pd.DataFrame, skyc1: SkyCoord,
        skyc2_srcs: pd.DataFrame, skyc2: SkyCoord, limit: Angle,
        id_incr_par_assoc: int=0
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    '''
    The loop for basic source association that uses the astropy
    'match_to_catalog_sky' function (i.e. only the nearest match between
    the catalogs). A direct on sky separation is used to define the association.

    Args:
        sources_df:
            The dataframe containing all current measurements along with their
            association source and relations.
        skyc1_srcs:
            The same structure as sources_df but only has one entry per
            'source' along with a weighted average sky position of the current
            assoociated sources.
        skyc1:
            A SkyCoord object with the weighted average sky positions from
            skyc1_srcs.
        skyc2_srcs:
            The same structure as sources_df containing the measurements to be
            associated.
        skyc2:
            A SkyCoord object with the sky positions from skyc2_srcs.
        limit:
            The association limit to use (applies to basic and advanced only).
        id_incr_par_assoc:
            An increment value to be applied to source numbering when adding
            new sources to the associations (applies when parallel and add
            image are being used). Defaults to 0.

    Returns:
        The output sources_df containing all input measurements along with the
        association and relation information.
        The output skyc1_srcs with updated with new sources from the
        association.
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
    # to the same base source we want to keep closest match and move
    # the other match(es) back to having a -1 src id
    skyc2_srcs, sources_df = one_to_many_basic(
        skyc2_srcs, sources_df, id_incr_par_assoc)

    logger.info('Updating sources catalogue with new sources...')
    # update the src numbers for those sources in skyc2 with no match
    # using the max current src as the start and incrementing by one
    start_elem = sources_df['source'].values.max() + 1 + id_incr_par_assoc
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

    # and update skyc1 with the sources that were created from the one
    # to many relations and any new sources.
    skyc1_srcs = skyc1_srcs.append(
        skyc2_srcs[
            ~skyc2_srcs['source'].isin(skyc1_srcs['source'])
        ],
        ignore_index=True
    ).reset_index(drop=True)

    return sources_df, skyc1_srcs


def advanced_association(
        method: str, sources_df: pd.DataFrame, skyc1_srcs: pd.DataFrame,
        skyc1: SkyCoord, skyc2_srcs: pd.DataFrame, skyc2: SkyCoord,
        dr_limit: float, bw_max: float, id_incr_par_assoc: int=0
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    '''
    The loop for advanced source association that uses the astropy
    'search_around_sky' function (i.e. all matching sources are
    found). The BMAJ of the image * the user supplied beamwidth
    limit is the base distance for association. This is followed
    by calculating the 'de Ruiter' radius.

    Args:
        method:
            The advanced association method 'advanced' or 'deruiter'.
        sources_df:
            The dataframe containing all current measurements along with their
            association source and relations.
        skyc1_srcs:
            The same structure as sources_df but only has one entry per
            'source' along with a weighted average sky position of the current
            assoociated sources.
        skyc1:
            A SkyCoord object with the weighted average sky positions from
            skyc1_srcs.
        skyc2_srcs:
            The same structure as sources_df containing the measurements to be
            associated.
        skyc2:
            A SkyCoord object with the sky positions from skyc2_srcs.
        dr_limit:
            The de Ruiter radius limit to use (applies to de ruiter only).
        bw_max:
            The beamwidth limit to use (applies to de ruiter only).
        id_incr_par_assoc:
            An increment value to be applied to source numbering when adding
            new sources to the associations (applies when parallel and add
            image are being used). Defaults to 0.

    Returns:
        The output sources_df containing all input measurements along with the
        association and relation information.
        The output skyc1_srcs with updated with new sources from the
        association.
    '''
    # read the needed sources fields
    # Step 1: get matches within semimajor axis of image.
    idx_skyc1, idx_skyc2, d2d, d3d = skyc2.search_around_sky(
        skyc1, bw_max
    )

    # Step 2: merge the candidates so the de ruiter can be calculated
    temp_skyc1_srcs = (
        skyc1_srcs.loc[idx_skyc1]
        .reset_index()
        .rename(columns={'index': 'index_old'})
    )
    temp_skyc2_srcs = (
        skyc2_srcs.loc[idx_skyc2]
        .reset_index()
        .rename(columns={'index': 'index_old'})
    )

    temp_skyc2_srcs['d2d'] = d2d.arcsec
    temp_srcs = temp_skyc1_srcs.merge(
        temp_skyc2_srcs,
        left_index=True,
        right_index=True,
        suffixes=('_skyc1', '_skyc2')
    )

    del temp_skyc1_srcs, temp_skyc2_srcs

    # Step 3: Apply the beamwidth limit
    temp_srcs = temp_srcs[d2d <= bw_max].copy()

    # Step 4: Calculate and perform De Ruiter radius cut
    if method == 'deruiter':
        temp_srcs['dr'] = calc_de_ruiter(temp_srcs)
        temp_srcs = temp_srcs[temp_srcs['dr'] <= dr_limit]
    else:
        temp_srcs['dr'] = 0.

    # Now have the 'good' matches
    # Step 5: Check for one-to-many, many-to-one and many-to-many
    # associations. First the many-to-many
    temp_srcs = many_to_many_advanced(temp_srcs, method)

    # Next one-to-many
    # Get the sources which are doubled
    temp_srcs, sources_df = one_to_many_advanced(
        temp_srcs, sources_df, method, id_incr_par_assoc
    )

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
    start_elem = sources_df['source'].values.max() + 1 + id_incr_par_assoc
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

    # also need to append any related sources that created a new
    # source, we can use the skyc2_srcs_toappend to get these
    skyc1_srcs = skyc1_srcs.append(
        skyc2_srcs_toappend.loc[
            ~skyc2_srcs_toappend.source.isin(skyc1_srcs.source)
        ]
    )

    return sources_df, skyc1_srcs


def association(images_df: pd.DataFrame, limit: Angle, dr_limit: float,
    bw_limit: float, duplicate_limit: Angle, config: PipelineConfig, add_mode: bool,
    previous_parquets: Dict[str, str], done_images_df: pd.DataFrame,
    id_incr_par_assoc: int=0, parallel: bool=False) -> pd.DataFrame:
    '''
    The main association function that does the common tasks between basic
    and advanced modes.

    Args:
        images_df:
            The input images to be associated.
        limit:
            The association limit to use (applies to basic and advanced only).
        dr_limit:
            The de Ruiter radius limit to use (applies to de ruiter only).
        bw_limit:
            The beamwidth limit to use (applies to de ruiter only).
        duplicate_limit:
            The limit of separation for which a measurement is considered to
            be a duplicate (epoch based association).
        config:
            The pipeline configuration object.
        add_mode:
            Whether the pipeline is currently being run in add image mode.
        previous_parquets:
            Dictionary containing the paths of the previous successful run
            parquet files (used in add image mode).
        done_images_df:
            Datafraame containing the images of the previous successful run
            (used in add image mode).
        id_incr_par_assoc:
            An increment value to be applied to source numbering when adding
            new sources to the associations (applies when parallel and add
            image are being used). Defaults to 0.
        parallel:
            Whether parallel association is being used.

    Returns:
        The output sources_df containing all input measurements along with the
        association and relation information.

    Raises:
        Exception: Raised if association method is not valid.
    '''
    timer = StopWatch()

    if parallel:
        images_df = (
            images_df.sort_values(by='image_datetime')
            .drop('image_datetime', axis=1)
        )

    if 'skyreg_group' in images_df.columns:
        skyreg_group = images_df['skyreg_group'].iloc[0]
        skyreg_tag = " (sky region group %s)" % skyreg_group
    else:
        skyreg_group = -1
        skyreg_tag = ""

    method = config["source_association"]["method"]

    logger.info('Starting association%s.', skyreg_tag)
    logger.info('Association mode selected: %s.', method)

    unique_epochs = np.sort(images_df['epoch'].unique())

    if add_mode:
        # Here the skyc1_srcs and sources_df are recreated and the done images
        # are filtered out.
        image_mask = images_df['image_name'].isin(done_images_df['name'])
        images_df_done = images_df[image_mask].copy()
        sources_df, skyc1_srcs = reconstruct_associtaion_dfs(
            images_df_done,
            previous_parquets,
        )
        images_df = images_df.loc[~image_mask]
        if images_df.empty:
            logger.info(
                'No new images found, stopping association%s.', skyreg_tag
            )
            sources_df['interim_ew'] = (
                sources_df['ra_source'].values * sources_df['weight_ew'].values
            )
            sources_df['interim_ns'] = (
                sources_df['dec_source'].values * sources_df['weight_ns'].values
            )
            return (
                sources_df
                .drop(['ra', 'dec'], axis=1)
                .rename(columns={'ra_source': 'ra', 'dec_source': 'dec'})
            )
        logger.info(
            f'Found {images_df.shape[0]} images to add to the run{skyreg_tag}.')
        # re-get the unique epochs
        unique_epochs = np.sort(images_df['epoch'].unique())
        start_epoch = 0

    else:
        # Do full set up for a new run.
        first_images = (
            images_df
            .loc[images_df['epoch'] == unique_epochs[0], 'image_dj']
            .to_list()
        )

        # initialise sky source dataframe
        skyc1_srcs = prep_skysrc_df(
            first_images,
            config["measurements"]["flux_fractional_error"],
            duplicate_limit,
            ini_df=True
        )
        skyc1_srcs['epoch'] = unique_epochs[0]
        # create base catalogue
        # initialise the sources dataframe using first image as base
        sources_df = skyc1_srcs.copy()
        start_epoch = 1

    if unique_epochs.shape[0] == 1 and not add_mode:
        # This means only one image is present - or one group of images (epoch
        # mode) - so the same approach as above in add mode where there are no
        # images to be added, the interim needs to be calculated and skyc1_srcs
        # can just be returned as sources_df. ra_source and dec_source can just
        # be dropped as the ra and dec are already the average values.
        logger.warning(
            'No images to associate with!%s.', skyreg_tag
        )
        logger.info(
            'Returning base sources only%s.', skyreg_tag
        )
        # reorder the columns to match Dask expectations (parallel)
        skyc1_srcs = skyc1_srcs[[
            'id', 'uncertainty_ew', 'weight_ew', 'uncertainty_ns', 'weight_ns',
            'flux_int', 'flux_int_err', 'flux_int_isl_ratio', 'flux_peak',
            'flux_peak_err', 'flux_peak_isl_ratio', 'forced', 'compactness',
            'has_siblings', 'snr', 'image', 'datetime', 'source', 'ra', 'dec',
            'ra_source', 'dec_source', 'd2d', 'dr', 'related', 'epoch',
        ]]
        skyc1_srcs['interim_ew'] = (
            skyc1_srcs['ra'].values * skyc1_srcs['weight_ew'].values
        )
        skyc1_srcs['interim_ns'] = (
            skyc1_srcs['dec'].values * skyc1_srcs['weight_ns'].values
        )

        return skyc1_srcs.drop(['ra_source', 'dec_source'], axis=1)

    skyc1 = SkyCoord(
        skyc1_srcs['ra'].values,
        skyc1_srcs['dec'].values,
        unit=(u.deg, u.deg)
    )

    for it, epoch in enumerate(unique_epochs[start_epoch:]):
        logger.info('Association iteration: #%i%s', it + 1, skyreg_tag)
        # load skyc2 source measurements and create SkyCoord
        images = (
            images_df.loc[images_df['epoch'] == epoch, 'image_dj'].to_list()
        )
        max_beam_maj = (
            images_df.loc[images_df['epoch'] == epoch, 'image_dj']
            .apply(lambda x: x.beam_bmaj)
            .max()
        )
        skyc2_srcs = prep_skysrc_df(
            images,
            config["measurements"]["flux_fractional_error"],
            duplicate_limit
        )

        skyc2_srcs['epoch'] = epoch
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].values,
            skyc2_srcs['dec'].values,
            unit=(u.deg, u.deg)
        )

        if method == 'basic':
            sources_df, skyc1_srcs = basic_association(
                sources_df,
                skyc1_srcs,
                skyc1,
                skyc2_srcs,
                skyc2,
                limit,
                id_incr_par_assoc
            )

        elif method in ['advanced', 'deruiter']:
            if method == 'deruiter':
                bw_max = Angle(
                    bw_limit * (max_beam_maj * 3600. / 2.) * u.arcsec
                )
            else:
                bw_max = limit
            sources_df, skyc1_srcs = advanced_association(
                method,
                sources_df,
                skyc1_srcs,
                skyc1,
                skyc2_srcs,
                skyc2,
                dr_limit,
                bw_max,
                id_incr_par_assoc
            )
        else:
            raise Exception('association method not implemented!')

        logger.info(
            'Calculating weighted average RA and Dec for sources%s...',
            skyreg_tag
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

        sources_df = sources_df.drop(['ra_wrap'], axis=1)

        tmp_srcs_df = (
            sources_df.loc[
                (sources_df['source'] != -1) & (sources_df['forced'] == False),
                [
                    'ra', 'dec', 'uncertainty_ew', 'uncertainty_ns',
                    'source', 'interim_ew', 'interim_ns', 'weight_ew',
                    'weight_ns'
                ]
            ]
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
            'Finalising base sources catalogue ready for next iteration%s...',
            skyreg_tag
        )

        # merge the weighted ra and dec and replace the values
        skyc1_srcs = skyc1_srcs.merge(
            weighted_df,
            on='source',
            how='left',
            suffixes=('', '_skyc2')
        )
        del tmp_srcs_df, weighted_df
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

        # generate new sky coord ready for next iteration
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].values,
            skyc1_srcs['dec'].values,
            unit=(u.deg, u.deg)
        )

        # and update relations in skyc1
        skyc1_srcs = skyc1_srcs.drop('related', axis=1)
        relations_unique = pd.DataFrame(
            sources_df[sources_df['related'].notna()]
            .explode('related')
            .groupby('source')['related']
            .apply(lambda x: x.unique().tolist())
        )

        skyc1_srcs = skyc1_srcs.merge(
            relations_unique, how='left', left_on='source', right_index=True
        )

        logger.info(
            'Association iteration #%i complete%s.', it + 1, skyreg_tag
        )

    # End of iteration over images, ra and dec columns are actually the
    # average over each iteration so remove ave ra and ave dec used for
    # calculation and use ra_source and dec_source columns
    sources_df = (
        sources_df.drop(['ra', 'dec'], axis=1)
        .rename(columns={'ra_source': 'ra', 'dec_source': 'dec'})
    )

    del skyc1_srcs, skyc2_srcs

    logger.info(
        'Total association time: %.2f seconds%s.',
        timer.reset_init(),
        skyreg_tag
    )

    return sources_df


def _correct_parallel_source_ids(
    df: pd.DataFrame, correction: int) -> pd.DataFrame:
    """
    This function is to correct the source ids after the combination of
    the associaiton dataframes produced by parallel association - as source
    ids will be duplicated if left.

    Args:
        df:
            Holds the measurements associated into sources. The output of
            of the association step (sources_df).
        correction:
            The value to add to the source ids.

    Returns:
        The input df with corrected source ids and relations.
    """
    df['source'] = df['source'].values + correction
    related_mask = df['related'].notna()

    new_relations = df.loc[
        related_mask, 'related'
    ].explode() + correction

    df.loc[
        df[related_mask].index.values, 'related'
    ] = new_relations.groupby(level=0).apply(
        lambda x: x.values.tolist()
    )

    return df


def _correct_parallel_source_ids_add_mode(
    df: pd.DataFrame, done_source_ids: List[int],
    start_elem: int) -> Tuple[pd.DataFrame, int]:
    """
    This function is to correct the source ids after the combination of
    the associaiton dataframes produced by parallel association - as source
    ids will be duplicated if left - specifically for add mode.

    When add mode is being used the 'old' sources require the ID to remain
    the same with only the new ones being changed. The next start elem also
    needs to be dynamically updated with every skyreg_group loop.

    Args:
        df:
            Holds the measurements associated into sources. The output of of
            the association step (sources_df).
        done_source_ids:
            A list of the 'old' source ids that need to remain the same.
        start_elem:
            The start elem number for the new source ids.

    Returns:
        The input df with corrected source ids and relations, and the new
        start elem for the next group.
    """
    # When using add_mode the correction becomes easier with the increment
    # as there's a clear difference between old and new.
    # old ones do not need to be corrected

    # get a mask of those that need to be corrected
    to_correct_mask = ~df['source'].isin(done_source_ids)

    # check that there are any to correct
    if not np.any(to_correct_mask):
        # there are no ids to correct we can just return the input
        # next start elem is just the same as the input as well
        return df[['source', 'related']], start_elem

    # create a new column for the new id
    df['new_source'] = df['source']
    # how many unique new sources
    to_correct_source_ids = df.loc[to_correct_mask, 'source'].unique()
    # create the range of new ids
    new_ids = list(
        range(start_elem, start_elem + to_correct_source_ids.shape[0]))
    # create a map of old source to new source
    source_id_map = dict(zip(to_correct_source_ids, new_ids))
    # get and apply the new ids to the new column
    df.loc[to_correct_mask, 'new_source'] = (
        df.loc[to_correct_mask, 'new_source'].map(source_id_map)
    )
    # regenrate the map
    source_id_map = dict(zip(df.source.values, df.new_source.values))
    # get mask of non-nan relations
    related_mask = df['related'].notna()
    # get the relations
    new_relations = df.loc[related_mask, 'related'].explode()
    # map the new values
    new_relations = new_relations.map(source_id_map)
    # group them back and form lists again
    new_relations = new_relations.groupby(level=0).apply(
        lambda x: x.values.tolist())
    # apply corrected relations to results
    df.loc[df[related_mask].index.values, 'related'] = new_relations
    # drop the old sources and replace
    df = df.drop('source', axis=1).rename(columns={'new_source': 'source'})
    # define what the next start elem will be
    next_start_elem = new_ids[-1] + 1

    return df[['source', 'related']], next_start_elem


def parallel_association(
    images_df: pd.DataFrame,
    limit: Angle,
    dr_limit: float,
    bw_limit: float,
    duplicate_limit: Angle,
    config: PipelineConfig,
    n_skyregion_groups: int,
    add_mode: bool,
    previous_parquets: Dict[str, str],
    done_images_df: pd.DataFrame,
    done_source_ids: List[int]
) -> pd.DataFrame:
    """
    Launches association on different sky region groups in parallel using Dask.

    Args:
        images_df: Holds the images that are being processed.
            Also contains what sky region group the image belongs to.
        limit: The association radius limit.
        dr_limit: The de Ruiter radius limit.
        bw_limit: The beamwidth limit.
        duplicate_limit: The duplicate radius detection limit.
        config (module): The pipeline config settings.
        n_skyregion_groups: The number of sky region groups.

    Returns:
        pd.DataFrame: The combined association results of the parallel
            association with corrected source ids.
    """
    logger.info(
        "Running parallel association for %i sky region groups.",
        n_skyregion_groups
    )

    timer = StopWatch()

    meta = {
        'id': 'i',
        'uncertainty_ew': 'f',
        'weight_ew': 'f',
        'uncertainty_ns': 'f',
        'weight_ns': 'f',
        'flux_int': 'f',
        'flux_int_err': 'f',
        'flux_int_isl_ratio': 'f',
        'flux_peak': 'f',
        'flux_peak_err': 'f',
        'flux_peak_isl_ratio': 'f',
        'forced': '?',
        'compactness': 'f',
        'has_siblings': '?',
        'snr': 'f',
        'image': 'U',
        'datetime': 'datetime64[ns]',
        'source': 'i',
        'ra': 'f',
        'dec': 'f',
        'd2d': 'f',
        'dr': 'f',
        'related': 'O',
        'epoch': 'i',
        'interim_ew': 'f',
        'interim_ns': 'f',
    }

    # Add an increment to any new source values when using add_mode to avoid
    # getting duplicates in the result laater
    id_incr_par_assoc = max(done_source_ids) if add_mode else 0

    n_cpu = cpu_count() - 1

    # pass each skyreg_group through the normal association process.
    results = (
        dd.from_pandas(images_df, n_cpu)
        .groupby('skyreg_group')
        .apply(
            association,
            limit=limit,
            dr_limit=dr_limit,
            bw_limit=bw_limit,
            duplicate_limit=duplicate_limit,
            config=config,
            add_mode=add_mode,
            previous_parquets=previous_parquets,
            done_images_df=done_images_df,
            id_incr_par_assoc=id_incr_par_assoc,
            parallel=True,
            meta=meta
        ).compute(n_workers=n_cpu, scheduler='processes')
    )

    # results are the normal dataframe of results with the columns:
    # 'id', 'uncertainty_ew', 'weight_ew', 'uncertainty_ns', 'weight_ns',
    # 'flux_int', 'flux_int_err', 'flux_peak', 'flux_peak_err', 'forced',
    # 'compactness', 'has_siblings', 'snr', 'image', 'datetime', 'source',
    # 'ra', 'dec', 'd2d', 'dr', 'related', 'epoch', 'interim_ew' and
    # 'interim_ns'.

    # The index however is now a multi index with the skyregion group and
    # a general result index. Hence the general result index is repeated for
    # each skyreg_group along with the source_ids. This needs to be collapsed
    # and the source id's corrected.

    # Index example:
    #                        id
    # skyreg_group
    # --------------------------
    # 2            0      15640
    #              1      15641
    #              2      15642
    #              3      15643
    #              4      15644
    # ...                   ...
    # 1            46975  53992
    #              46976  54062
    #              46977  54150
    #              46978  54161
    #              46979  54164

    # Get the indexes (skyreg_groups) to loop over for source id correction
    indexes = results.index.levels[0].values

    if add_mode:
        # Need to correct all skyreg_groups.
        # First get the starting id for new sources.
        new_id = max(done_source_ids) + 1
        for i in indexes:
            corr_df, new_id = _correct_parallel_source_ids_add_mode(
                results.loc[i, ['source', 'related']],
                done_source_ids,
                new_id
            )
            results.loc[
                (i, slice(None)), ['source', 'related']
            ] = corr_df.values
    else:
        # The first index acts as the base, so the others are looped over and
        # corrected.
        for i, val in enumerate(indexes):
            # skip first one, makes the enumerate easier to deal with
            if i == 0:
                continue
            # Get the maximum source ID from the previous group.
            max_id = results.loc[indexes[i - 1]].source.max()
            # Run through the correction function, only the 'source' and
            # 'related'
            # columns are passed and returned (corrected).
            corr_df = _correct_parallel_source_ids(
                results.loc[val, ['source', 'related']],
                max_id
            )
            # replace the values in the results with the corrected source and
            # related values
            results.loc[
                (val, slice(None)), ['source', 'related']
            ] = corr_df.values

            del corr_df

    # reset the indeex of the final corrected and collapsed result
    results = results.reset_index(drop=True)

    logger.info(
        'Total parallel association time: %.2f seconds', timer.reset_init()
    )

    return results
