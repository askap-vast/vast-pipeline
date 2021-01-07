import numpy as np
import pandas as pd


def test_inc_assoc(testcase, ass_add, ass_backup):
    '''
    Test that the number of associations increased or equal with added 
    images.

    Parameters
    ----------
    testcase : class
        Test class.
    ass_add : pd.DataFrame
        Associations after images were added.
    ass_backup : pd.DataFrame
        Associations before images were added.
    '''

    testcase.assertTrue(len(ass_add) >= len(ass_backup))

def test_update_source(
    testcase, sources_backup, sources_backup_db, sources_add, sources_add_db
    ):
    '''
    Test that the sources are correctly updated in the database.

    Parameters
    ----------
    testcase : class
        Test class.
    sources_backup : pd.DataFrame
        The sources before adding images in the output.
    sources_backup_db : pd.DataFrame
        The sources before adding images in the database.
    sources_add : pd.DataFrame
        The sources after adding images in the output.
    sources_add_db : pd.DataFrame
        The sources after adding images in the database.
    '''
    # check source database and file is the same after original run
    for ind in sources_backup.index:
        n_meas_db = sources_backup_db.loc[ind, 'n_meas']
        n_meas_pd = sources_backup.loc[ind, 'n_meas']
        testcase.assertEqual(n_meas_db, n_meas_pd)

    # check source database and file is the same after adding an image
    for ind in sources_add.index:
        n_meas_db = sources_add_db.loc[ind, 'n_meas']
        n_meas_pd = sources_add.loc[ind, 'n_meas']
        testcase.assertEqual(n_meas_db, n_meas_pd)

def test_sources(sources_1, sources_2):
    '''
    Test that the sources are the same between two different runs. 

    Parameters
    ----------
    sources_1 : pd.DataFrame
        The sources found in one run. 
    sources_2 : pd.DataFrame
        The sources found in a different run.
    '''
    sources_1 = (
        sources_1  
        .sort_values(by=['wavg_ra', 'wavg_dec'])
        .reset_index(drop=True)
    )
    sources_2 = (
        sources_2  
        .sort_values(by=['wavg_ra', 'wavg_dec'])
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        sources_1,
        sources_2,
        check_less_precise=4
    )

def test_relations(testcase, relations_1, relations_2):
    '''
    Test that the number relations are the same between two different runs.

    Parameters
    ----------
    testcase : class
        Test class.
    relations_1 : pd.DataFrame
        The relations found in one run. 
    relations_2 : pd.DataFrame
        The relations found in a different run.
    '''
    # compare number of relations per source
    relations_1 = (
        relations_1.pivot_table(
            index=['from_source_id'], aggfunc='size'
        )
        .to_frame('relations')
        .sort_index()
    )
    relations_2 = (
        relations_2.pivot_table(
            index=['from_source_id'], aggfunc='size'
        )
        .to_frame('relations')
        .sort_index()
    )

    testcase.assertEqual(len(relations_1), len(relations_2))

def test_forced_num(testcase, forced_1, forced_2):
    '''
    Test the number of forced extractions are correct.

    Parameters
    ----------
    testcase : class
        Test class.
    forced1 : dict
        The forced files in one run.
    forced_2 : dict
        The forced files in a different run.
    '''
    count = lambda x: np.sum([len(f.index) for f in x.values()])
    testcase.assertEqual(count(forced_1), count(forced_2))
