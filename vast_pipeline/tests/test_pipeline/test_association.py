import os
import pandas as pd
import pytest

from pathlib import Path

from django.test import SimpleTestCase, TestCase

from vast_pipeline.pipeline.association import (
    one_to_many_basic, 
    one_to_many_advanced
)


BASE_PATH = Path(__file__).parent
DATA_PATH = os.path.join(BASE_PATH, 'data')


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
        when there are no duplicate sources in skyc2_srcs
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
        sources_df = self.sources_df
        sources_df_true = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out.csv'), 
            header=0
        )

        res = one_to_many_basic(skyc2_srcs, sources_df)
        skyc2_srcs_out, sources_df_out = res

        # verify skyc2_srcs_out
        out_source = skyc2_srcs_out.loc[:,'source']
        assert list(
            skyc2_srcs.loc[:,'d2d'].values
        ) == list(
            skyc2_srcs_out.loc[:,'d2d'].values
        ) # check values in other columns are retained
        # new source ids need to be unique
        assert len(set(out_source.values)) == 6 
        # unique sources have no related source,
        # duplicated sources have their duplicates in the related column with 
        # the reassigned id
        assert pd.isnull(
            skyc2_srcs_out.loc[
                (out_source == 1).values, 
                'related'
            ].values[0]
        )
        assert skyc2_srcs_out.loc[
            (out_source == 4).values, 
            'related'
        ].values[0] == [2]
        assert skyc2_srcs_out.loc[
            (out_source == 3).values, 
            'related'
        ].values[0] == [5,6]

        # verify sources_df_out
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
        self.temp_srcs_simple = pd.read_csv(
            os.path.join(DATA_PATH, 'temp_srcs_nodup.csv'),
            header=0
        )

        self.sources_df_simple = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_in.csv'), 
            header=0
        )

    def test_method_exception(self):
        '''
        Test that an exception is raised when a bad method is used
        '''
        self.assertRaises(
            Exception, 
            one_to_many_advanced, 
            self.temp_srcs_simple, 
            self.sources_df_simple, 
            'non-existant-method'
        )

    def test_duplicated_skyc1_empty(self):
        '''
        Test if one_to_many_advanced will return the input dataframes unchanged
        when there are no duplicate sources in temp_srcs
        '''
        temp_srcs_out, sources_df_out = one_to_many_advanced(
            self.temp_srcs_simple, 
            self.sources_df_simple, 
            'advanced'
        )

        # if no duplicates, return inputs
        assert temp_srcs_out.equals(self.temp_srcs_simple)
        assert sources_df_out.equals(self.sources_df_simple)

    def test_method_advanced(self):
        '''
        Test if one_to_many_advanced correctly identifies duplicate sources and
        relates them for method=advanced. 

        temp_srcs: all duplicate sources should have new unique source ids, 
        duplicate sources should have related sources listed using new source 
        ids, if >2 duplicates of 1 source then the sources with new ids will 
        be related to the old id whilst the old id will be related to all new
        ids, and other columns should remain unchanged.
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
        sources_df_true = pd.read_csv(
            os.path.join(DATA_PATH, 'sources_df_out.csv'), 
            header=0
        )

        res = one_to_many_advanced(temp_srcs, sources_df, 'advanced')
        temp_srcs_out, sources_df_out = res

        # verify temp_srcs_out
        out_source = temp_srcs_out.loc[:,'source_skyc1']
        unchanged_temp_srcs = temp_srcs.loc[:, 
                [
                'index_old_skyc1', 'id_skyc1', 'd2d_skyc1', 
                'index_old_skyc2', 'id_skyc2', 'source_skyc2', 
                'd2d_skyc2', 'dr'
                ]
            ]
        unchanged_temp_srcs_out = temp_srcs_out.loc[:, 
                [
                'index_old_skyc1', 'id_skyc1', 'd2d_skyc1', 
                'index_old_skyc2', 'id_skyc2', 'source_skyc2', 
                'd2d_skyc2', 'dr'
                ]
            ]
        # check values in other columns are unchanged
        assert unchanged_temp_srcs.equals(unchanged_temp_srcs_out) 
        # new source ids need to be unique
        assert len(set(out_source.values)) == 6 
        # unique sources have no related source,
        # duplicated sources have their duplicates in the related column with
        # the reassigned id
        assert pd.isnull(
            temp_srcs_out.loc[
                (out_source == 1).values, 
                'related_skyc1'
            ].values[0]
        )
        assert temp_srcs_out.loc[
            (out_source == 4).values, 
            'related_skyc1'
        ].values[0] == [2]
        assert temp_srcs_out.loc[
            (out_source == 3).values, 
            'related_skyc1'
        ].values[0] == [5,6]

        # verify sources_df_out
        assert sources_df_out.equals(sources_df_true)

    def test_method_deruiter(self):
        # TODO: tests for different method? The difference between the methods 
        # is only sorting, how to check? 
        pass

class ManyToManyAdvancedTest(SimpleTestCase):

    def test_m_to_m_empty(self):
        pass