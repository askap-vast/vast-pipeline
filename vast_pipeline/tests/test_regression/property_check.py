import pandas as pd

from astropy.coordinates import SkyCoord, match_coordinates_sky


def test_num_sources(testcase, sources, num):
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

def test_known_source(testcase, sources, high_sigma):
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

    # check new and has correct new_high_sigma to 3 decimal places
    testcase.assertTrue(sources.loc[id_match, 'new'])
    testcase.assertTrue(
        abs(sources.loc[id_match, 'new_high_sigma'] - high_sigma) < 1e-3
    )

def test_most_relations(relations, sources, rows, expected):
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
    # count relations
    relations = (
        relations.pivot_table(index=['from_source_id'],aggfunc='size')
        .sort_values(ascending=False)
        .iloc[:rows]
        .to_frame('relations')
    )

    # get sources with highest relations
    sources = sources.loc[relations.index, ['wavg_ra', 'wavg_dec']]

    # merge the dataframes
    highest_relations = pd.merge(sources, relations, on='from_source_id')
    highest_relations = (
        highest_relations.sort_values(
            by=['relations', 'wavg_ra'], 
            ascending=[False, True]
        )
        .reset_index()
        .drop('from_source_id', axis=1)
    )

    print(highest_relations)

    # only checks that the first 4 decimal places are equal
    pd.testing.assert_frame_equal(
        highest_relations, 
        expected, 
        check_less_precise=4
    )
