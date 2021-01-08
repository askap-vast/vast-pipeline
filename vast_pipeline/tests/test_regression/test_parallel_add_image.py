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
class BasicParallelAddImageTest(TestCase):
    '''
    Test pipeline runs when in parallel and adding an image for basic 
    association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read the files.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-basic'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-parallel-basic'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
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


@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping parallel add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedParallelAddImageTest(TestCase):
    '''
    Test pipeline runs when in parallel and adding an image for advanced 
    association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-parallel-advanced'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
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


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping parallel add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class DeruiterParallelAddImageTest(TestCase):
    '''
    Test pipeline runs when in parallel and adding an image for deruiter 
    association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-deruiter'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-parallel-deruiter'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
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