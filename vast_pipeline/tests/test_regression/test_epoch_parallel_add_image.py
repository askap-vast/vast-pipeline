import os
import pandas as pd
import unittest
import glob

from vast_pipeline.tests.test_regression import compare_runs, property_check

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command

from vast_pipeline.models import Source


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not glob.glob(os.path.join(TEST_ROOT, 'regression-data','EPOCH*'))
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
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-basic'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-add-image-parallel-basic'
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
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-advanced'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-add-image-parallel-advanced'
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
class DeruiterEpochParallelAddImageTest(TestCase):
    '''
    Test pipeline runs when in epoch based parallel and adding an image for 
    deruiter association method. This is a property check and not a comparison
    because deruiter uses the largest beam size in present images, which gives
    slightly different results compared to the normal epoch based run.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-add-image-parallel-deruiter'
        )
        self.config_base = os.path.join(self.base_run, 'config_base.py')
        self.config_add = os.path.join(self.base_run, 'config_add.py')
        self.config = os.path.join(self.base_run, 'config.py')

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.base_run)

        self.ass_backup = pd.read_parquet(
            os.path.join(self.base_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.base_run)

        self.sources = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )
        self.ass = pd.read_parquet(
            os.path.join(self.base_run, 'associations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass, self.ass_backup)

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
            [[322.752092, -3.981232, 3],
             [322.752646, -3.982859, 3],
             [322.752777, -3.983257, 3],
             [322.752791, -3.982937, 3]],
            columns=['wavg_ra', 'wavg_dec', 'relations']
        )

        property_check.test_most_relations(
            self.relations, self.sources, 4, expected
        )

    def test_known_source(self):
        '''
        See documentation for test_known_source in property_check.
        '''
        property_check.test_known_source(self, self.sources, 12.369)
