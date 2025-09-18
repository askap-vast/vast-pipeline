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
class BasicEpochTest(TestCase):
    '''
    Test pipeline under epoch based basic association method returns expected
    results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        base_path = 'epoch-basic'
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
            os.path.join(
                self.base_run, 'relations.parquet'
            )
        )

        # remove test directory
        shutil.rmtree(self.base_run)

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 617)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[322.75292, -3.982978, 2],
             [21.033440, -73.151102, 1],
             [21.034743, -73.151590, 1],
             [23.061181, -73.651803, 1],
             [23.063016, -73.650433, 1],
             [23.425656, -73.296978, 1],
             [23.431615, -73.297481, 1],
             [322.249550, -4.402741, 1],
             [322.249601, -4.402723, 1],
             [322.751992, -3.983102, 1],
             [322.752802, -3.982956, 1],
             [322.822385, -5.092387, 1],
             [322.825281, -5.090753, 1],
             [322.875345, -4.231618, 1],
             [322.875472, -4.231777, 1],
             [322.927902, -5.030378, 1]],
             columns = ['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 16, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property check.
        '''
        property_check.test_known_source(self, self.sources, 13.943)


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedEpochTest(TestCase):
    '''
    Test pipeline under epoch based advanced association method returns
    expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        base_path = 'epoch-advanced'
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
            os.path.join(
                self.base_run, 'relations.parquet'
            )
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
            [
                [321.899517, -04.201971, 3],
                [020.649051, -73.638252, 2]
            ],
            columns=["wavg_ra", "wavg_dec", "relations"],
        )

        property_check.test_most_relations(self.relations, self.sources, 2, expected)

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
class DeruiterEpochTest(TestCase):
    '''
    Test pipeline under epoch based deruiter association method returns
    expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        base_path = 'epoch-deruiter'
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
            os.path.join(
                self.base_run, 'relations.parquet'
            )
        )

        # remove test directory
        shutil.rmtree(self.base_run)

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 617)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[322.752313, -3.982144, 4],
             [322.752458, -3.982929, 4],
             [322.752811, -3.983308, 4],
             [322.752833, -3.983007, 4],
             [322.753856, -3.984780, 4]],
            columns=['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 5, expected)

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 13.943)
