import ast
import os
import numpy as np
import pandas as pd
import pytest

from pathlib import Path

from django.test import SimpleTestCase, TestCase

from vast_pipeline.pipeline.association import (
    one_to_many_basic, 
    one_to_many_advanced,
    many_to_many_advanced,
    many_to_one_advanced
)


BASE_PATH = Path(__file__).parent
DATA_PATH = os.path.join(BASE_PATH, 'data')

def parse_lists(x):
    '''
    Changes a string containing a list into the list type. Needed for reading
    in lists from csv into pandas DataFrame.
    '''
    try:
        return ast.literal_eval(x)
    except:
        return np.nan


class OneToManyBasicTest(TestCase):
    '''
    Tests for one_to_many_basic in association.py 
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Read in data used in multiple tests
        '''
        self.sources_df = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
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
        sources_df = self.sources_df

        res = one_to_many_basic(skyc2_srcs, sources_df)
        skyc2_srcs_out, sources_df_out = res

        assert skyc2_srcs_out.equals(skyc2_srcs)
        assert sources_df_out.equals(sources_df)

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
        skyc2_srcs_true = pd.read_csv(
            os.path.join(DATA_PATH, 'skyc2_srcs_out.csv'), 
            header=0
        )
        sources_df = self.sources_df
        sources_df_true = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out.csv'), 
            header=0
        )

        res = one_to_many_basic(skyc2_srcs, sources_df)
        skyc2_srcs_out, sources_df_out = res

        assert skyc2_srcs_out.equals(skyc2_srcs)
        assert sources_df_out.equals(sources_df_true)


class OneToManyAdvancedTest(TestCase):
    '''
    Tests for one_to_many_advanced in association.py
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Read in data used in multiple tests
        '''
        self.temp_srcs_nodup = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'),
            header=0
        )
        self.sources_df_in = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )
        self.sources_df_out = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out.csv'), 
            header=0
        )

    def test_method_exception(self):
        '''
        Test that an exception is raised when a bad method is used
        '''
        self.assertRaises(
            Exception, 
            one_to_many_advanced, 
            self.temp_srcs_nodup, 
            self.sources_df_in, 
            method='non-existant-method'
        )

    def test_duplicated_skyc1_empty(self):
        '''
        Test if one_to_many_advanced will return the input dataframes unchanged
        when there are no duplicate sources in temp_srcs. Repeated values in 
        source_skyc1 are duplicates. 
        '''

        temp_srcs = self.temp_srcs_nodup
        sources_df = self.sources_df_in

        temp_srcs_out, sources_df_out = one_to_many_advanced(
            temp_srcs, 
            sources_df, 
            method='advanced'
        )

        # if no duplicates, return inputs
        assert temp_srcs_out.equals(temp_srcs)
        assert sources_df_out.equals(sources_df)

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
        temp_srcs_true = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_advanced_out.csv'), 
            header=0,
            converters = {'related_skyc1': parse_lists}
        )
        sources_df = self.sources_df_in
        sources_df_true = self.sources_df_out

        res = one_to_many_advanced(temp_srcs, sources_df, method='advanced')
        temp_srcs_out, sources_df_out = res

        assert temp_srcs_out.equals(temp_srcs_true)
        assert sources_df_out.equals(sources_df_true)

    def test_method_deruiter(self):
        '''
        Test if one_to_many_advanced correctly identifies duplicate sources and
        relates them for method=advanced. 

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
        temp_srcs_true = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_deruiter_out.csv'), 
            header=0,
            converters = {'related_skyc1': parse_lists}
        )
        sources_df = self.sources_df_in
        sources_df_true = self.sources_df_out

        res = one_to_many_advanced(temp_srcs, sources_df, method='deruiter')
        temp_srcs_out, sources_df_out = res

        assert temp_srcs_out.equals(temp_srcs_true)
        assert sources_df_out.equals(sources_df_true)


class ManyToManyAdvancedTest(SimpleTestCase):
    '''
    Tests for many_to_many_advanced in association.py
    '''

    # TODO: there's no check on the method, write one? 
    
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

        temp_srcs_out = many_to_many_advanced(temp_srcs, method='advanced')

        assert temp_srcs_out.equals(temp_srcs)

    def test_method_advanced(self):
        '''
        Testing if many_to_many_advanced drops the correct rows for duplicate
        sources. Duplicates are when both index_old_skyc2 and souce_skyc1 are 
        repeated. The duplicate rows with d2d_skyc2 > min(d2d_skyc2) will be
        dropped.

        This test assumes that the index of the dataframe doesn't matter. 
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'),
            header=0
        ) 
        temp_srcs_true = pd.read_csv(os.path.join(DATA_PATH, 'temp_srcs_advanced_drop.csv'), header=0)

        temp_srcs_out = many_to_many_advanced(temp_srcs, method='advanced')
        temp_srcs_out.reset_index(drop=True, inplace=True)

        assert temp_srcs_out.equals(temp_srcs_true)

    def test_method_dr(self):
        '''
        Testing if many_to_many_advanced drops the correct rows for duplicate
        sources. Duplicates are when both index_old_skyc2 and souce_skyc1 are 
        repeated. The duplicate rows with dr > min(dr) will be dropped.

        This test assumes that the index of the dataframe doesn't matter.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'),
            header=0
        ) 
        temp_srcs_true = pd.read_csv(os.path.join(DATA_PATH, 'temp_srcs_dr_drop.csv'), header=0)

        temp_srcs_out = many_to_many_advanced(temp_srcs, method='dr')
        temp_srcs_out.reset_index(drop=True, inplace=True)

        assert temp_srcs_out.equals(temp_srcs_true)


class ManyToOneAdvancedTest(SimpleTestCase):
    '''
    Tests for many_to_one_advanced in association.py
    '''

    def test_duplicated_skyc2_empty(self):
        '''
        Test if many_to_one_advanced will return the input dataframe unchanged
        when there are no duplicate sources in temp_srcs. Repeated values in
        index_old_skyc2 are duplicate sources.
        '''
        temp_srcs = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_dup.csv'),
            header=0
        ) 

        temp_srcs_out = many_to_one_advanced(temp_srcs)

        assert temp_srcs_out.equals(temp_srcs)


class BasicAssociationTest(SimpleTestCase):
    '''
    Tests for basic_association in association.py
    '''

    def test(self):
        pass


class AdvancedAssociationTest(SimpleTestCase):
    '''
    Tests for advanced_association in association.py
    '''

    def test(self):
        pass


class AssociationTest(SimpleTestCase):
    '''
    Tests for association in association.py
    '''

    def test(self):
        pass


class CorrectParallelSourceIdsTest(SimpleTestCase):
    '''
    Tests for _correct_parallel_souce_ids in association.py
    '''

    def test(self):
        pass


class ParallelAssociation(SimpleTestCase):
    '''
    Tests for parallel_association in association.py
    '''

    def test(self):
        pass

