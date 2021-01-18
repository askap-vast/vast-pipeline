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
        base_path = 'normal-basic'
        compare_path = 'add-parallel-basic'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with all images
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

        # run with add image
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
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

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
        See documentation for test_relations in comapre_runs.
        '''
        compare_runs.test_relations(
            self, self.relations_base, self.relations_compare
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
        base_path = 'normal-advanced'
        compare_path = 'add-parallel-advanced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with all images
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

        # run with add image
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
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

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
            self, self.relations_base, self.relations_compare
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
        base_path = 'normal-deruiter'
        compare_path = 'add-parallel-deruiter'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with all images
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

        # run with add image
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
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

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
            self, self.relations_base, self.relations_compare
        )


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping parallel add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicParallelAddTwoImageTest(TestCase):
    '''
    Test pipeline runs when in parallel and adding two images for basic
    association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read the files.
        '''
        base_path = 'normal-basic'
        compare_path = 'add-add-parallel-basic'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # run with all images
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

        # run with add image
        make_testdir(self.compare_run)
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.compare_run)
        self.ass_backup = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        # run with epoch 05 06
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
        call_command('runpipeline', self.compare_run)
        self.ass_backup_mid = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )

        # run with epoch 12
        gen_config.gen_config(
            compare_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
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

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
            self, self.relations_base, self.relations_compare
        )
