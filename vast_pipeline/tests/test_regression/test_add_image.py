import os
import pandas as pd
import unittest
import glob

from vast_pipeline.tests.test_regression import compare_runs

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command

from vast_pipeline.models import Source


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not glob.glob(os.path.join(TEST_ROOT, 'regression-data','EPOCH*'))
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
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-basic'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-basic'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        index = self.sources_backup.index
        self.sources_backup_db = pd.DataFrame(
            [Source.objects.get(id=ind).n_meas for ind in index],
            index=index,
            columns = ['n_meas']
        )

        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        index = self.sources_compare.index
        self.sources_compare_db = pd.DataFrame(
            [Source.objects.get(id=ind).n_meas for ind in index],
            index=index,
            columns = ['n_meas']
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_compare, self.ass_backup)

    def test_update_source(self):
        '''
        See documentation for test_update_sources in compare_runs.
        '''
        compare_runs.test_update_source(
            self,
            self.sources_backup, self.sources_backup_db,
            self.sources_compare, self.sources_compare_db
        )

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_base, self.sources_compare)

    def test_relations(self):
        '''
        See documentation for test_relations in comapre_runs.
        '''
        compare_runs.test_relations(self, self.relations_base, self.relations_compare)


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
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-advanced'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
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
        self.ass_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_compare, self.ass_backup)

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
class DeruiterAddImageTest(TestCase):
    '''
    Test pipeline runs when adding an image for deruiter association method.
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
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-deruiter'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
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
        self.ass_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_compare, self.ass_backup)

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


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicAddTwoImageTest(TestCase):
    '''
    Test pipeline runs when adding two images for basic association method.
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
            s.PIPELINE_WORKING_DIR, 'regression', 'add-add-image-basic'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config_add2 = os.path.join(self.compare_run, 'config_add2.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # run with all images
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )

        # run with add image
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        # run with epoch 05 06
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_backup_mid = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        # run with epoch 12
        os.system(f'cp {self.config_add2} {self.config}')
        call_command('runpipeline', self.compare_run)
        self.ass_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_compare = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass_compare, self.ass_backup_mid)
        compare_runs.test_inc_assoc(self, self.ass_backup_mid, self.ass_backup)

    def test_sources(self):
        '''
        See documentation for test_sources in compare_runs.
        '''
        compare_runs.test_sources(self.sources_base, self.sources_compare)

    def test_relations(self):
        '''
        See documentation for test_relations in comapre_runs.
        '''
        compare_runs.test_relations(
            self, self.relations_base, self.relations_compare)
