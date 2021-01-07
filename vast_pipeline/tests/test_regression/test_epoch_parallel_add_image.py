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
    'The regression test data is missing, skipping parallel add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicEpochParallelAddImageTest(TestCase):
    '''
    Test pipeline runs when in epoch based parallel and adding an image for 
    basic association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read the files.
        '''
        self.normal_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-basic'
        )
        self.para_add_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-add-image-parallel-basic'
        )
        self.config_base = os.path.join(self.para_add_run, 'config_base.py')
        self.config_add = os.path.join(self.para_add_run, 'config_add.py')
        self.config = os.path.join(self.para_add_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.normal_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.normal_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.normal_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.para_add_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.para_add_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.para_add_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.para_add_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.para_add_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.para_add_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_associ in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_add, self.ass_backup)

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_all, self.sources_add)

    def test_relations(self):
        '''
        See documentation for test_relations in comapre_runs.
        '''
        compare_runs.test_relations(
            self, self.relations_all, self.relations_add
        )


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping parallel add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedEpochParallelAddImageTest(TestCase):
    '''
    Test pipeline runs when in epoch based parallel and adding an image for 
    advanced association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        self.normal_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-advanced'
        )
        self.para_add_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-add-image-parallel-advanced'
        )
        self.config_base = os.path.join(self.para_add_run, 'config_base.py')
        self.config_add = os.path.join(self.para_add_run, 'config_add.py')
        self.config = os.path.join(self.para_add_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.normal_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.normal_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.normal_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.para_add_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.para_add_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.para_add_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.para_add_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.para_add_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.para_add_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_add, self.ass_backup)

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_all, self.sources_add)

    def test_relations(self):
        '''
        See documentation for test_relations in compare_runs.
        '''
        compare_runs.test_relations(
            self, self.relations_all, self.relations_add
        )
