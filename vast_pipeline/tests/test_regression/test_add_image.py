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
    'The regression test data is missing, skipping add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicAddImageTest(TestCase):
    '''
    Test pipeline runs when adding an image for basic association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read the files.
        '''
        self.all_image_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-basic'
        )
        self.add_image_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-basic'
        )
        self.config_base = os.path.join(self.add_image_run, 'config_base.py')
        self.config_add = os.path.join(self.add_image_run, 'config_add.py')
        self.config = os.path.join(self.add_image_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.all_image_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.all_image_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.all_image_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.add_image_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )
        self.sources_backup = pd.read_parquet(
            os.path.join(self.add_image_run, 'sources.parquet')
        )
        index = self.sources_backup.index
        self.sources_backup_db = pd.DataFrame(
            [Source.objects.get(id=ind).n_meas for ind in index], 
            index=index, 
            columns = ['n_meas']
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.add_image_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.add_image_run, 'sources.parquet')
        )
        index = self.sources_add.index
        self.sources_add_db = pd.DataFrame(
            [Source.objects.get(id=ind).n_meas for ind in index], 
            index=index, 
            columns = ['n_meas']
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.add_image_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_associ in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_add, self.ass_backup)

    def test_update_source(self):
        '''
        See documentation for test_update_sources in compare_runs.
        '''
        compare_runs.test_update_source(
            self, 
            self.sources_backup, self.sources_backup_db, 
            self.sources_add, self.sources_add_db
        )

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_all, self.sources_add)

    def test_relations(self):
        '''
        See documentation for test_relations in comapre_runs.
        '''
        compare_runs.test_relations(self, self.relations_all, self.relations_add)


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedAddImageTest(TestCase):
    '''
    Test pipeline runs when adding an image for advanced association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read files.
        '''
        self.all_image_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced'
        )
        self.add_image_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-advanced'
        )
        self.config_base = os.path.join(self.add_image_run, 'config_base.py')
        self.config_add = os.path.join(self.add_image_run, 'config_add.py')
        self.config = os.path.join(self.add_image_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.all_image_run)
        self.sources_all = pd.read_parquet(
            os.path.join(self.all_image_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
            os.path.join(self.all_image_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.add_image_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.add_image_run)
        self.ass_add = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.add_image_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.add_image_run, 'relations.parquet')
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
        compare_runs.test_relations(self, self.relations_all, self.relations_add)
