import os
import pandas as pd
import unittest
import glob
import shutil

from vast_pipeline.tests.test_regression import compare_runs, property_check, gen_config
from vast_pipeline.tests.test_regression.make_testdir import make_testdir

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command



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
        base_path = 'epoch-basic'
        compare_path = 'epoch-add-parallel-basic'
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
        self.sources_all = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
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
        self.ass_add = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
        base_path = 'epoch-advanced'
        compare_path = 'epoch-add-parallel-advanced'
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
        self.sources_all = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
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
        self.ass_add = pd.read_parquet(
            os.path.join(self.compare_run, 'associations.parquet')
        )
        self.sources_add = pd.read_parquet(
            os.path.join(self.compare_run, 'sources.parquet')
        )
        self.relations_add = pd.read_parquet(
            os.path.join(self.compare_run, 'relations.parquet')
        )

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
        base_path = 'epoch-add-parallel-deruiter'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )

        # run with add image
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.base_run)

        self.ass_backup = pd.read_parquet(
            os.path.join(self.base_run, 'associations.parquet')
        )

        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x']
        )
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

        # remove test directory
        shutil.rmtree(self.base_run)

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(self, self.ass, self.ass_backup)

    def test_num_sources(self):
        '''
        See documentation for test_num_sources in property_check.
        '''
        property_check.test_num_sources(self, self.sources, 610)

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


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping parallel add image tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicEpochParallelAddTwoImageTest(TestCase):
    '''
    Test pipeline runs when in epoch based parallel and adding two images for
    basic association method.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directories to test data, run the pipeline, and read the files.
        '''
        base_path = 'epoch-basic'
        compare_path = 'epoch-add-add-parallel-basic'
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
        self.sources_all = pd.read_parquet(
            os.path.join(self.base_run, 'sources.parquet')
        )
        self.relations_all = pd.read_parquet(
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

        # remove test directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

    def test_inc_assoc(self):
        '''
        See documentation for test_inc_assoc in compare_runs.
        '''
        compare_runs.test_inc_assoc(
            self, self.ass_compare, self.ass_backup_mid
        )
        compare_runs.test_inc_assoc(
            self, self.ass_backup_mid, self.ass_backup
        )
