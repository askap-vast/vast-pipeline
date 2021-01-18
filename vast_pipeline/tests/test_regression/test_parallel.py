import os
import pandas as pd
import unittest
import glob
import shutil

from vast_pipeline.tests.test_regression import compare_runs, gen_config
from vast_pipeline.tests.test_regression.make_testdir import make_testdir

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command

from vast_pipeline.models import Source


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not glob.glob(os.path.join(TEST_ROOT, 'regression-data','EPOCH*'))
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
        base_path = 'normal-basic'
        compare_path = 'parallel-basic'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # normal run
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # parallel run
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
        call_command('runpipeline', self.compare_run)
        self.sources_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

    def test_sources(self):
        '''
        See documentation for test_sources in comapre_runs.
        '''
        compare_runs.test_sources(self.sources_base, self.sources_compare)

    def test_relations(self):
        '''
        See documentation for test_relations under compare_runs.
        '''
        compare_runs.test_relations(self, self.relations_base, self.relations_compare)


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
        base_path = 'normal-advanced'
        compare_path = 'parallel-advanced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with normal
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with parallel
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.compare_run)
        self.sources_compare = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

        # remove directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_base, self.sources_compare)

    def test_relations(self):
        '''
        See documentation for test_relations in compare_runs.
        '''
        compare_runs.test_relations(self, self.relations_base, self.relations_compare)


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class DeruiterParallelTest(TestCase):
    '''
    Test pipeline runs in parallel for deruiter association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        base_path = 'normal-deruiter'
        compare_path = 'parallel-deruiter'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with normal
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with parallel
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.compare_run)
        self.sources_compare = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_base, self.sources_compare)

    def test_relations(self):
        '''
        See documentation for test_relations in compare_runs.
        '''
        compare_runs.test_relations(
            self, self.relations_base, self.relations_compare)
