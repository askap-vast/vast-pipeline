import os
import types
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
        property_check.test_num_sources(self, self.sources, 616)

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
             [322.249559, -4.402759, 1],
             [322.249615, -4.402745, 1],
             [322.752246, -3.982728, 1],
             [322.752994, -3.982975, 1],
             [322.822412, -5.092524, 1],
             [322.825119, -5.090515, 1],
             [322.875352, -4.231587, 1],
             [322.875452, -4.231785, 1],
             [322.927896, -5.030347, 1],
             [322.930617, -5.031158, 1]],
             columns = ['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 16, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property check.
        '''
        property_check.test_known_source(self, self.sources, 12.369)


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
        property_check.test_num_sources(self, self.sources, 624)

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
        property_check.test_known_source(self, self.sources, 12.369)


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
        property_check.test_num_sources(self, self.sources, 616)

    def test_most_relations(self):
        '''
        See documentation for test_most_relations in property_check.
        '''
        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[322.752467, -3.982379, 4],
             [322.752646, -3.982859, 4],
             [322.752791, -3.982937, 4],
             [322.752859, -3.983386, 4],
             [322.753513, -3.985183, 4]],
            columns=['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 5, expected)

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 12.369)
