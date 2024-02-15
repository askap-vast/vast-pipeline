import numpy as np
import pandas as pd
from typing import List

from astropy.coordinates import SkyCoord, match_coordinates_sky

from django.test import TestCase


def test_num_sources(testcase: TestCase, sources: pd.DataFrame, num: int):
    '''
    Test the number of overall sources identified is correct.

    Parameters
    ----------
    testcase : class
        Test class.
    sources : pd.DataFrame
        Dataframe containing identified sources.
    num : int
        Number of identified sources.
    '''

    testcase.assertEqual(len(sources.index), num)

def test_most_relations(relations: pd.DataFrame, sources: pd.DataFrame,
    rows: int, expected: pd.DataFrame):
    '''
    Test that the highest relation source is the same, and in general the
    top sources with the most relations are correct.

    Parameters
    ----------
    relations : pd.DataFrame
        The relations of the sources.
    sources : pd.DataFrame
        The sources identified.
    rows : int
        The number of rows to take of the most relations.
    expected : pd.DataFrame
        The expected most relations sources.
    '''
    # count relations and order by number of relations and then index
    relations = (
        relations.pivot_table(index=['from_source_id'], aggfunc='size')
        .to_frame('relations')
    )

    # get sources with highest relations
    sources = sources.loc[relations.index, ['wavg_ra', 'wavg_dec']]

    highest_relations = (
        pd.merge(sources, relations, left_index=True, right_index=True)
        .sort_values(['relations', 'wavg_ra'], ascending=[False, True])
        .reset_index(drop=True)
        .iloc[:rows]
    )

    # only checks that the first 4 decimal places are equal
    pd.testing.assert_frame_equal(
        highest_relations,
        expected,
        rtol=1e-04,
    )

def known_source(sources: pd.DataFrame) -> int:
    '''
    Find the source closest to PSR J2129-04

    Parameters
    ----------
    sources : pd.DataFrame
        The sources to search through. Indicies must be reset.

    Returns
    -------
    id_match : int
        The index of the closest source.
    '''
    # from SIMBAD
    coords = SkyCoord(
        "21 29 45.29", "-04 29 11.9",
        frame='icrs',
        unit=('hourangle', 'deg')
    )

    # find PSR J2129-04 by matching coordinates in sources
    source_coords = SkyCoord(
        sources['wavg_ra'],
        sources['wavg_dec'],
        unit=('deg', 'deg')
    )
    id_match, *_ = match_coordinates_sky(coords, source_coords)

    return id_match

def test_known_source(testcase: TestCase, sources: pd.DataFrame, high_sigma: float):
    '''
    Check that PSR J2129-04 is detected as a new source and has correct
    new_high_sigma.

    Parameters
    ----------
    testcase : class
        Test class.
    sources : pd.DataFrame
        The sources to search through.
    high_sigma : float
        The expected high sigma value.
    '''
    sources = sources.reset_index()
    id_match = known_source(sources)

    # check new and has correct new_high_sigma to 3 decimal places
    testcase.assertTrue(sources.loc[id_match, 'new'])
    testcase.assertTrue(
        abs(sources.loc[id_match, 'new_high_sigma'] - high_sigma) < 1e-3
    )

def test_known_in_forced(testcase: TestCase, forced: dict, sources: pd.DataFrame,
    associations: pd.DataFrame, num: int, exp_forced: List[str]):
    '''
    Find if PSR J2129-04 appears in the correct forced files and has the
    correct number of associations.

    Parameters
    ----------
    testcase : class
        Test class.
    forced : dict
        The forced extractions.
    sources : pd.DataFrame
        The sources to search through.
    associations : pd.DataFrame
        The associations present for the sources.
    num : int
        The number of expected associations for PSR J2129-04.
    exp_forced : List[str]
        The expected force extraction files for PSR J2129-04.
    '''
    sources = sources.reset_index()
    sources
    id_match = known_source(sources)
    source_id = sources.loc[id_match, 'source']
    meas_id = associations[
        associations['source_id'] == source_id
    ]['meas_id'].values

    # check the number of measurements is correct
    testcase.assertEqual(len(meas_id), num)

    # find the forced extractions with PSR J2129-04
    images = []
    for f_key in forced.keys():
        f_df = forced[f_key]
        for m_id in meas_id:
            match = f_df[f_df['id'] == m_id]
            if not match.empty:
                testcase.assertEqual(len(match), 1) # should only appear once
                obs = '_'.join(f_key.split('_')[3:5])
                images.append(obs)

    # check that the forced extractions appear in the correct images
    testcase.assertEqual(set(images), exp_forced)

def test_forced_num(testcase: TestCase, forced: dict, num: int):
    '''
    Test the number of forced extractions is expected.

    Parameters
    ----------
    testcase : class
        Test class.
    forced : dict
        The forced measurements.
    num : int
        The number of expected forced measurements.
    '''
    count = np.sum([len(f.index) for f in forced.values()])

    testcase.assertEqual(count, num)
