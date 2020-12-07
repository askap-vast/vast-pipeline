import ast
import os
import pandas as pd
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle

from django.test import SimpleTestCase

from vast_pipeline.pipeline.association import (
    one_to_many_basic, 
    one_to_many_advanced,
    many_to_many_advanced,
    many_to_one_advanced,
    basic_association,
    advanced_association,
    _correct_parallel_source_ids
)


BASE_PATH = Path(__file__).parent
DATA_PATH = os.path.join(BASE_PATH, 'data')

# Used for reading in lists from csv into pandas DataFrame.
def parse_or_nan(x):
    '''
    Attempt to parse a string as a python literal, returning NaN if it couldn't be parsed.

    Calls ast.literal_eval internally.

    Parameters
    ----------
    s : str
        String to parse.
    
    Returns
    -------
    The parsed string, or NaN if it couldn't be parsed.
    '''
    try:
        return ast.literal_eval(x)
    except:
        return float('NaN')


class OneToManyBasicTest(SimpleTestCase):
    '''
    Tests for one_to_many_basic in association.py 
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.skyc2_srcs_nodup = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_nodup.csv'), 
            header=0
        )
        self.skyc2_srcs_out = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_out.csv'), 
            header=0,
            converters={'related': parse_or_nan}
        )
        self.sources_df_in = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )
        self.sources_df_out = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out.csv'), 
            header=0
        )

    def test_duplicated_skyc2_empty(self):
        '''
        Test if one_to_many_basic will return the input dataframes unchanged 
        when there are no duplicate sources in skyc2_srcs. Repeated values in
        source are duplicates, ignoring -1 values. 
        '''
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_nodup.csv'), 
            header=0
        )
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )

        skyc2_srcs, sources_df = one_to_many_basic(skyc2_srcs, sources_df)

        self.assertTrue(skyc2_srcs.equals(self.skyc2_srcs_nodup))
        self.assertTrue(sources_df.equals(self.sources_df_in))

    def test_duplicated_skyc2_nonempty(self):
        '''
        Test if one_to_many_basic correctly identifies duplicate sources and 
        relates them.

        skyc2_srcs: all duplicate sources should have new unique source ids, 
        the new ids are assigned in order of d2d - min d2d retains original id,
        duplicate sources should have related sources listed using new source 
        ids, if >2 duplicates of 1 source then the sources with new ids will 
        be related to the old id whilst the old id will be related to all new
        ids, and other columns should remain unchanged.
        sources_df: must contain at least all source ids present in skyc2_src,
        rows with same id as duplicates in skyc2_srcs will be duplicated and
        assigned to the new id.
        '''
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_dup.csv'),
            header=0
        )
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )

        skyc2_srcs, sources_df = one_to_many_basic(skyc2_srcs, sources_df)

        self.assertTrue(skyc2_srcs.equals(self.skyc2_srcs_out))
        self.assertTrue(sources_df.equals(self.sources_df_out))


class OneToManyAdvancedTest(SimpleTestCase):
    '''
    Tests for one_to_many_advanced in association.py
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.temp_srcs_nodup = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'),
            header=0
        )
        self.temp_srcs_advanced_out = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_advanced_out.csv'), 
            header=0,
            converters={'related_skyc1': parse_or_nan}
        )
        self.temp_srcs_deruiter_out = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_deruiter_out.csv'), 
            header=0,
            converters={'related_skyc1': parse_or_nan}
        )
        self.sources_df_in = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )
        self.sources_df_out = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out.csv'), 
            header=0
        )

    def test_duplicated_skyc1_empty(self):
        '''
        Test if one_to_many_advanced will return the input dataframes unchanged
        when there are no duplicate sources in temp_srcs. Repeated values in 
        source_skyc1 are duplicates. 
        '''

        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'),
            header=0
        )
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )

        temp_srcs, sources_df = one_to_many_advanced(
            temp_srcs, 
            sources_df, 
            method='advanced'
        )

        # if no duplicates, return inputs
        self.assertTrue(temp_srcs.equals(self.temp_srcs_nodup))
        self.assertTrue(sources_df.equals(self.sources_df_in))

    def test_method_advanced(self):
        '''
        Test if one_to_many_advanced correctly identifies duplicate sources and
        relates them for method=advanced. 

        temp_srcs: all duplicate sources should have new unique source ids, 
        the new ids are assigned in order of d2d_skyc2 - min d2d_skyc2 retains
        original id, duplicate sources should have related sources listed using 
        new source ids, if >2 duplicates of 1 source then the sources with new 
        ids will be related to the old id whilst the old id will be related to
        all new ids, and other columns should remain unchanged.
        sources_df: must contain at least all source ids present in temp_src,
        rows with same id as duplicates in temp_srcs will be duplicated and
        assigned to the new id.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'), 
            header=0
        )
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )

        temp_srcs, sources_df = one_to_many_advanced(
            temp_srcs, 
            sources_df, 
            method='advanced'
        )

        self.assertTrue(temp_srcs.equals(self.temp_srcs_advanced_out))
        self.assertTrue(sources_df.equals(self.sources_df_out))

    def test_method_deruiter(self):
        '''
        Test if one_to_many_advanced correctly identifies duplicate sources and
        relates them for method=deruiter. 

        temp_srcs: all duplicate sources should have new unique source ids, 
        the new ids are assigned in order of dr - min dr retains original id, 
        duplicate sources should have related sources listed using new source 
        ids, if >2 duplicates of 1 source then the sources with new ids will be 
        related to the old id whilst the old id will be related to all new ids, 
        and other columns should remain unchanged.
        sources_df: must contain at least all source ids present in temp_src,
        rows with same id as duplicates in temp_srcs will be duplicated and
        assigned to the new id.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'), 
            header=0
        )
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )

        temp_srcs, sources_df = one_to_many_advanced(
            temp_srcs, 
            sources_df, 
            method='deruiter'
        )

        self.assertTrue(temp_srcs.equals(self.temp_srcs_deruiter_out))
        self.assertTrue(sources_df.equals(self.sources_df_out))


class ManyToManyAdvancedTest(SimpleTestCase):
    '''
    Tests for many_to_many_advanced in association.py
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.temp_srcs_nodup = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'), 
            header=0
        )
        self.temp_srcs_advanced_drop = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_advanced_drop.csv'),
            header=0
        )
        self.temp_srcs_deruiter_drop = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_deruiter_drop.csv'), 
            header=0
        )
    
    def test_m_to_m_empty(self):
        '''
        Test if many_to_many_advanced will return the input dataframe unchanged
        when there are no duplicate sources in temp_srcs. Both index_old_skyc2
        and souce_skyc1 need to be repeated for it to be a duplicate source.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'), 
            header=0
        )

        temp_srcs = many_to_many_advanced(temp_srcs, method='advanced')

        self.assertTrue(temp_srcs.equals(self.temp_srcs_nodup))

    def test_method_advanced(self):
        '''
        Testing if many_to_many_advanced drops the correct rows for duplicate
        sources when method=advanced. Duplicates are when both index_old_skyc2 
        and souce_skyc1 are repeated. The duplicate rows with 
        d2d_skyc2 > min(d2d_skyc2) will be dropped.

        This test assumes that the index of the dataframe doesn't matter. 
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'),
            header=0
        ) 

        temp_srcs = many_to_many_advanced(temp_srcs, method='advanced')
        temp_srcs.reset_index(drop=True, inplace=True)

        self.assertTrue(temp_srcs.equals(self.temp_srcs_advanced_drop))

    def test_method_deruiter(self):
        '''
        Testing if many_to_many_advanced drops the correct rows for duplicate
        sources when method=deruiter. Duplicates are when both index_old_skyc2 
        and souce_skyc1 are repeated. The duplicate rows with dr > min(dr) will 
        be dropped.

        This test assumes that the index of the dataframe doesn't matter.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'),
            header=0
        ) 

        temp_srcs = many_to_many_advanced(temp_srcs, method='deruiter')
        temp_srcs.reset_index(drop=True, inplace=True)

        self.assertTrue(temp_srcs.equals(self.temp_srcs_deruiter_drop))


class ManyToOneAdvancedTest(SimpleTestCase):
    '''
    Tests for many_to_one_advanced in association.py
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.temp_srcs_nodup = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'),
            header=0
        ) 
        self.temp_srcs_ind_rel = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_ind_rel.csv'),
            header=0,
            converters={'related_skyc1': parse_or_nan}
        )

    def test_duplicated_skyc2_empty(self):
        '''
        Test if many_to_one_advanced will return the input dataframe unchanged
        when there are no duplicate sources in temp_srcs. Repeated values in
        index_old_skyc2 are duplicate sources.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'),
            header=0
        ) 

        temp_srcs = many_to_one_advanced(temp_srcs)

        self.assertTrue(temp_srcs.equals(self.temp_srcs_nodup))

    def test_many_to_one_advanced(self):
        '''
        Testing if many_to_one_advanced relates the correct sources. Repeated 
        values in index_old_skyc2 are identified, these rows take the 
        source_skyc1 value without itself as related_skyc1 values. If there are 
        no source_skyc1 values except itself, then related_skyc1 is []. If 
        index_old_skyc2 is unique, then the previous related_skyc1 is retained. 
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'),
            header=0
        ) 

        temp_srcs_out = many_to_one_advanced(temp_srcs)

        self.assertTrue(temp_srcs_out.equals(self.temp_srcs_ind_rel))


class TestHelpers(SimpleTestCase):
    '''
    Class which has some helper functions for testing. 
    '''

    def check_col(self, df1, df2, columns=['ra', 'dec', 'source', 'epoch']):
        '''
        Function which checks that certain columns of two DataFrames are
        equal for BasicAssociationTest and AdvancedAssociationTest.
        
        Not testing related column, it is used in one_to_many_basic, which is 
        already tested. Not testing d2d column, it is output from Astropy.

        Parameters
        ----------
        df1 : pd.DataFrame
            Dataframe to be compared.
        df2 : pd.DataFrame
            Dataframe to be compared.
        columns : List[str]
            Column header of the dataframes to be compared.

        Returns
        -------
        None
        '''
        for col in columns:
            self.assertTrue(df1[col].equals(df2[col]))


class BasicAssociationTest(TestHelpers):
    '''
    Tests for basic_association in association.py
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.sources_df_basic_out = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_basic_out.csv')
        ) 
        self.sources_df_no_new = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_no_new.csv')
        ) 
        self.sources_df_all = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_all.csv')
        ) 
        self.skyc1_srcs_in = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        self.skyc1_srcs_out = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_out.csv'),
            header=0
        )
        self.skyc1_srcs_all = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_all.csv'),
            header=0
        )

    def test_no_new_skyc2_srcs(self):
        '''
        Test basic_association returns skyc1_srcs unchanged and sources_df with
        new same sources under new epoch when given skyc2_srcs with no new 
        sources. 
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_no_new.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        limit = Angle(10, unit='arcsec')

        sources_df, skyc1_srcs = basic_association(
            sources_df, skyc1_srcs, skyc1, skyc2_srcs, skyc2, limit
        )

        self.check_col(sources_df, self.sources_df_no_new)
        self.check_col(skyc1_srcs, self.skyc1_srcs_in)

    def test_zero_limit(self):
        '''
        Test basic_association returns all sources in skyc2_srcs as new sources
        when the limit is zero. 
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_in.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        limit = Angle(0, unit='arcsec')

        sources_df, skyc1_srcs = basic_association(
            sources_df, skyc1_srcs, skyc1, skyc2_srcs, skyc2, limit
        )

        self.check_col(sources_df, self.sources_df_all)
        self.check_col(skyc1_srcs, self.skyc1_srcs_all)

    def test_basic_association(self):
        '''
        Test basic_association correctly appends the sources in skyc2_srcs into
        skyc1_srcs and sources_df.
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_in.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        limit = Angle(10, unit='arcsec')

        sources_df, skyc1_srcs = basic_association(
            sources_df, skyc1_srcs, skyc1, skyc2_srcs, skyc2, limit
        )

        self.check_col(sources_df, self.sources_df_basic_out)
        self.check_col(skyc1_srcs, self.skyc1_srcs_out)


class AdvancedAssociationTest(TestHelpers):
    '''
    Tests for advanced_association in association.py
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.sources_df_advanced_out = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_advanced_out.csv')
        ) 
        self.sources_df_no_new = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_no_new.csv')
        ) 
        self.sources_df_all = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_all.csv')
        ) 
        self.skyc1_srcs_in = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        self.skyc1_srcs_out = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_out.csv'),
            header=0
        )
        self.skyc1_srcs_all = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_all.csv'),
            header=0
        )

    def test_no_new_skyc2_srcs(self):
        '''
        Test advanced_association returns skyc1_srcs unchanged and sources_df 
        with new same sources under new epoch when given skyc2_srcs with no new 
        sources. 
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_no_new.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        dr_limit = 5.68
        bw_max = Angle(10, unit='arcsec')

        sources_df, skyc1_srcs = advanced_association(
            'advanced', sources_df, skyc1_srcs, skyc1, 
            skyc2_srcs, skyc2, dr_limit, bw_max
        )

        self.check_col(sources_df, self.sources_df_no_new)
        self.check_col(skyc1_srcs, self.skyc1_srcs_in)

    def test_zero_bw_max(self):
        '''
        Test advanced_association returns all sources in skyc2_srcs as new 
        sources when the limit is zero. 
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_in.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        dr_limit = 5.68
        bw_max = Angle(0, unit='arcsec')

        sources_df, skyc1_srcs = advanced_association(
            'advanced', sources_df, skyc1_srcs, skyc1, 
            skyc2_srcs, skyc2, dr_limit, bw_max
        )

        self.check_col(sources_df, self.sources_df_all)
        self.check_col(skyc1_srcs, self.skyc1_srcs_all)

    def test_advanced(self):
        '''
        Test advanced_association correctly appends the sources in skyc2_srcs 
        into skyc1_srcs and sources_df for method=advanced.
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_in.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        dr_limit = 5.68
        bw_max = Angle(10, unit='arcsec')

        sources_df, skyc1_srcs = advanced_association(
            'advanced', sources_df, skyc1_srcs, skyc1, 
            skyc2_srcs, skyc2, dr_limit, bw_max
        ) 

        self.check_col(sources_df, self.sources_df_advanced_out)
        self.check_col(skyc1_srcs, self.skyc1_srcs_out)

    def test_deruiter(self):
        '''
        Test advanced_association correctly appends the sources in skyc2_srcs 
        into skyc1_srcs and sources_df for method=deruiter.

        Note: this test is redundant, method is already tested in other 
        functions. Better test would be if dr_limit gives different result.
        '''
        sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_ass_in.csv'), 
            header=0
        )
        skyc1_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc1_srcs_in.csv'), 
            header=0
        )
        skyc1 = SkyCoord(
            skyc1_srcs['ra'].tolist(), 
            skyc1_srcs['dec'].tolist(), 
            unit='deg'
        )
        skyc2_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_in.csv'), 
            header=0
        )
        skyc2 = SkyCoord(
            skyc2_srcs['ra'].tolist(), 
            skyc2_srcs['dec'].tolist(), 
            unit='deg'
        )
        dr_limit = 5.68
        bw_max = Angle(10, unit='arcsec')

        sources_df, skyc1_srcs = advanced_association(
            'deruiter', sources_df, skyc1_srcs, skyc1, skyc2_srcs, skyc2, dr_limit, bw_max
        )

        self.check_col(sources_df, self.sources_df_advanced_out)
        self.check_col(skyc1_srcs, self.skyc1_srcs_out)


class CorrectParallelSourceIdsTest(SimpleTestCase):
    '''
    Tests for _correct_parallel_souce_ids in association.py
    '''

    @classmethod
    def setUpClass(self):
        '''
        Load in correct outputs so inplace operations are tested.
        '''
        super().setUpClass()
        self.sources_df_in = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'),
            header=0,
            converters={'related': parse_or_nan}
        ) 
        self.sources_df_out_2 = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out_2.csv'),
            header=0,
            converters={'related': parse_or_nan}
        ) 

    def test_zero(self):
        '''
        Test _correct_parallel_source_ids doesn't change the input df when 
        correction=0.
        '''
        df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0,
            converters={'related': parse_or_nan}
        )

        df = _correct_parallel_source_ids(df, 0)

        self.assertTrue(df.equals(self.sources_df_in))

    def test_correct_parllel_source_ids(self):
        '''
        Test _correct_parallel_source_ids increases the numbers in the source
        and relate column by the correction amount.
        '''
        df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0, 
            converters={'related': parse_or_nan}
        )

        df = _correct_parallel_source_ids(df, 2)

        self.assertTrue(df.equals(self.sources_df_out_2))
