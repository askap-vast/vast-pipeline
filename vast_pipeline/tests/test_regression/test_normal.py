import os
import pandas as pd
import unittest
import glob
import shutil

from vast_pipeline.tests.test_regression import property_check, gen_config
from vast_pipeline.tests.test_regression.make_testdir import make_testdir

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
        base_path = 'normal-basic'
        self.base_run = os.path.join(s.PIPELINE_WORKING_DIR, base_path)

        # setup test directory
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
        call_command('runpipeline', self.base_run)

        # read output
        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # remove test directory
        shutil.rmtree(self.base_run)

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
            [[21.033440, -73.151102, 1],
             [21.034743, -73.151590, 1],
             [23.061181, -73.651803, 1],
             [23.063016, -73.650433, 1],
             [23.425656, -73.296978, 1],
             [23.431615, -73.297481, 1],
             [322.517655, -4.050478, 1],
             [322.517889, -4.050864, 1],
             [322.822385, -5.092387, 1],
             [322.825015, -5.091084, 1],
             [322.875278, -4.231607, 1],
             [322.875398, -4.231754, 1],
             [322.927902, -5.030378, 1],
             [322.930210, -5.031081, 1]],
             columns = ['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 14, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 13.943)


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
        base_path = 'normal-advanced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )

        # setup test directory
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.base_run)

        # read output
        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # remove test directory
        shutil.rmtree(self.base_run)

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 620)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [
                [321.900237, -04.201482, 4],
                [321.898668, -04.202589, 3],
                [321.900885, -04.200907, 3],
                [20.649051, -73.638252, 2],
                [321.899747, -04.201875, 2],
                [321.901242, -04.200643, 2],
                [322.517744, -04.050434, 2],
                [322.578566, -04.318185, 2],
                [322.578833, -04.317944, 2],
                [322.578973, -04.317444, 2],
                [20.649074, -73.636792, 1],
                [20.649549, -73.640345, 1],
                [21.033440, -73.151102, 1]],
            columns=['wavg_ra', 'wavg_dec', 'relations'],
        )

        property_check.test_most_relations(
            self.relations, self.sources, 13, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 13.943)


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
        base_path = 'normal-deruiter'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )

        # setup test directory
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.base_run)

        # read output
        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # remove test directory
        shutil.rmtree(self.base_run)

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 614)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [
                [323.076226, -4.516496, 3],
                [322.517682, -4.050535, 2],
                [322.578728, -4.318062, 2],
                [323.073098, -4.517475, 2],
                [323.073534, -4.517318, 2],
                [323.079258, -4.514705, 2],
                [21.033440, -73.151102, 1],
                [21.034743, -73.151590, 1],
                [22.839231, -72.878832, 1],
                [22.840613, -72.879889, 1],
            ],
            columns=['wavg_ra', 'wavg_dec', 'relations'],
        )

        property_check.test_most_relations(
            self.relations, self.sources, 10, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 13.943)
