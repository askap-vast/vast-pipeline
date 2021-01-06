import os
import pandas as pd
import unittest

from vast_pipeline.tests.test_regression import compare_runs

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command

from vast_pipeline.models import Source


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping parallel tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicParallelTest(TestCase):
    '''
    Test pipeline runs in parallel for basic association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read the files.
        '''
        self.normal_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-basic'
        )
        self.parallel_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'parallel-basic'
        )

        # normal run
        call_command('runpipeline', self.normal_run)
        self.sources_norm = pd.read_parquet(
            os.path.join(self.normal_run, 'sources.parquet')
        )
        self.relations_norm = pd.read_parquet(
            os.path.join(self.normal_run, 'relations.parquet')
        )

        # parallel run
        call_command('runpipeline', self.parallel_run)
        self.sources_parallel = pd.read_parquet(
            os.path.join(self.parallel_run, 'sources.parquet')
        )
        self.relations_parallel = pd.read_parquet(
            os.path.join(self.parallel_run, 'relations.parquet')
        )

    def test_sources(self):
        '''
        See documentation for test_sources in comapre_runs.
        '''
        compare_runs.test_sources(self.sources_norm, self.sources_parallel)

    def test_relations(self):
        '''
        See documentation for test_relations under compare_runs.
        '''
        compare_runs.test_relations(self, self.relations_norm, self.relations_parallel)


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedParallelTest(TestCase):
    '''
    Test pipeline runs in parallel for advanced association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        self.normal_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced'
        )
        self.parallel_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'parallel-advanced'
        )

        # run with normal
        call_command('runpipeline', self.normal_run)
        self.sources_norm = pd.read_parquet(
            os.path.join(self.normal_run, 'sources.parquet')
        )
        self.relations_norm = pd.read_parquet(
            os.path.join(self.normal_run, 'relations.parquet')
        )

        # run with parallel
        call_command('runpipeline', self.parallel_run)
        self.sources_parallel = pd.read_parquet(
            os.path.join(self.normal_run, 'sources.parquet')
        )
        self.relations_parallel = pd.read_parquet(
            os.path.join(self.parallel_run, 'relations.parquet')
        )

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_norm, self.sources_parallel)

    def test_relations(self):
        '''
        See documentation for test_relations in compare_runs.
        '''
        compare_runs.test_relations(self, self.relations_norm, self.relations_parallel)
