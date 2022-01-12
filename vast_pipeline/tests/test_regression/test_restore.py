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
        base_path = 'normal-basic-forced'
        compare_path = 'restore-basic-forced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with three epoch images
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.base_run)
        self.sources_base = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_base = pd.read_parquet(
            os.path.join(self.base_run, 'relations.parquet')
        )
        self.ass_base = pd.read_parquet(
            os.path.join(self.base_run, 'associations.parquet')
        )
        index = self.sources_base.index
        self.sources_base_db = pd.DataFrame(
            [Source.objects.get(id=ind).n_meas for ind in index],
            index=index,
            columns = ['n_meas']
        )

        # run with add image and then restore
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.compare_run)

        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
        call_command('runpipeline', self.compare_run)
        call_command('restorepiperun', self.compare_run, no_confirm=True)

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

        # remove directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(
            self, self.ass_compare, self.ass_base, must_be_equal=True
        )

    def test_update_source(self):
        '''
        See documentation for test_update_sources in compare_runs.
        '''
        compare_runs.test_update_source(
            self,
            self.sources_base, self.sources_base_db,
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
