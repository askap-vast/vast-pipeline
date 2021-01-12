import os
import types
import pandas as pd
import unittest
import glob

from vast_pipeline.tests.test_regression import property_check

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not glob.glob(os.path.join(TEST_ROOT, 'regression-data','EPOCH*'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicRegressionTest(TestCase):
    '''
    Test pipeline under basic association method returns expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-basic'
        )
        call_command('runpipeline', self.base_run)

        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 622)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[21.033441, -73.151101, 1],
             [21.035019, -73.151512, 1],
             [23.061180, -73.651803, 1],
             [23.063015, -73.650433, 1],
             [23.425469, -73.296979, 1],
             [23.429945, -73.297484, 1],
             [322.517743, -4.050352, 1],
             [322.517923, -4.050832, 1],
             [322.822412, -5.092524, 1],
             [322.824837, -5.090852, 1],
             [322.875277, -4.231576, 1],
             [322.875429, -4.231719, 1],
             [322.927896, -5.030347, 1],
             [322.930182, -5.031106, 1]], 
             columns = ['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 14, expected
        ) 

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 12.369)


@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedRegressionTest(TestCase):
    '''
    Test pipeline under advanced association method returns expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced'
        )
        call_command('runpipeline', self.base_run)

        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 621)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[321.899747,  -4.201875, 4],
             [321.900237,  -4.201482, 4],
             [321.898668,  -4.202589, 3],
             [321.900885,  -4.200907, 3],
             [20.649051, -73.638252, 2],
             [321.901242,  -4.200643, 2],
             [322.517744,  -4.050434, 2],
             [322.578566,  -4.318185, 2],
             [322.578833,  -4.317944, 2],
             [322.578973,  -4.317444, 2],
             [322.822594,  -5.092404, 2],
             [322.823466,  -5.091993, 2],
             [322.824837,  -5.090852, 2]], 
             columns = ['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 13, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 12.369)


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class DeruiterRegressionTest(TestCase):
    '''
    Test pipeline under deruiter association method returns expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced'
        )
        call_command('runpipeline', self.base_run)

        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 621)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[321.899747,  -4.201875, 4],
             [321.900237,  -4.201482, 4],
             [321.898668,  -4.202589, 3],
             [321.900885,  -4.200907, 3],
             [20.649051, -73.638252, 2],
             [321.901242,  -4.200643, 2],
             [322.517744,  -4.050434, 2],
             [322.578566,  -4.318185, 2],
             [322.578833,  -4.317944, 2],
             [322.578973,  -4.317444, 2],
             [322.822594,  -5.092404, 2],
             [322.823466,  -5.091993, 2],
             [322.824837,  -5.090852, 2]],
            columns=['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 13, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 12.369)
