import os
import types
import pandas as pd
import unittest

from vast_pipeline.tests.test_regression import compare_runs, property_check

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class BasicForcedTest(TestCase):
    '''
    Test pipeline under forced basic association method returns expected 
    results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.basic_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-basic-forced'
        )
        self.add_image_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-parallel-basic-forced'
        )
        self.config_base = os.path.join(self.add_image_run, 'config_base.py')
        self.config_add = os.path.join(self.add_image_run, 'config_add.py')
        self.config = os.path.join(self.add_image_run, 'config.py')

        # normal run
        call_command('runpipeline', self.basic_run)

        self.forced_files = {}
        for f in os.listdir(self.basic_run):
            if f[:6] == 'forced':
                self.forced_files[f] = pd.read_parquet(
                    os.path.join(self.basic_run, f)
                )
        self.sources = pd.read_parquet(
            os.path.join(
                self.basic_run, 'sources.parquet'
            )
        )
        self.associations = pd.read_parquet(
            os.path.join(
                self.basic_run, 'associations.parquet'
            )
        )

        # add image run
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.add_image_run)
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.add_image_run)

        self.forced_files_add = {}
        for f in os.listdir(self.add_image_run):
            if f[:6] == 'forced' and f[-6:] != 'backup':
                self.forced_files_add[f] = pd.read_parquet(
                    os.path.join(self.add_image_run, f)
                )
        self.sources_add = pd.read_parquet(
            os.path.join(
                self.add_image_run, 'sources.parquet'
            )
        )
        self.associations_add = pd.read_parquet(
            os.path.join(
                self.add_image_run, 'associations.parquet'
            )
        )

    def test_forced_num(self):
        '''
        See documentation for test_forced_num in property check.
        '''
        compare_runs.test_forced_num(self, self.forced_files, self.forced_files_add)

    def test_known_in_forced(self):
        '''
        See documentation for test_known_in_forced in propery_check.
        '''
        # the expected forced extractions for PSR J2129-04
        exp_forced = {
            '2118-06A_EPOCH01', '2118+00A_EPOCH03x', '2118+00A_EPOCH02',
            '2118-06A_EPOCH02', '2118-06A_EPOCH03x', '2118+00A_EPOCH01'
        }

        for forced, sources, ass in zip(
            [self.forced_files, self.forced_files_add], 
            [self.sources, self.sources_add], 
            [self.associations, self.associations_add]
        ):
            property_check.test_known_in_forced(self, forced, sources, ass, 10, exp_forced)


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedForcedTest(TestCase):
    '''
    Test pipeline under forced advanced association method returns expected
    results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.advanced_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'normal-advanced-forced'
        )
        self.add_image_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'add-image-parallel-advanced-forced'
        )
        self.config_base = os.path.join(self.add_image_run, 'config_base.py')
        self.config_add = os.path.join(self.add_image_run, 'config_add.py')
        self.config = os.path.join(self.add_image_run, 'config.py')

        # normal run
        call_command('runpipeline', self.advanced_run)

        self.forced_files = {}
        for f in os.listdir(self.advanced_run):
            if f[:6] == 'forced':
                self.forced_files[f] = pd.read_parquet(
                    os.path.join(self.advanced_run, f)
                )
        self.sources = pd.read_parquet(
            os.path.join(
                self.advanced_run, 'sources.parquet'
            )
        )
        self.associations = pd.read_parquet(
            os.path.join(
                self.advanced_run, 'associations.parquet'
            )
        )

        # add image run
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.add_image_run)
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.add_image_run)

        self.forced_files_add = {}
        for f in os.listdir(self.add_image_run):
            if f[:6] == 'forced' and f[-6:] != 'backup':
                self.forced_files_add[f] = pd.read_parquet(
                    os.path.join(self.add_image_run, f)
                )
        self.sources_add = pd.read_parquet(
            os.path.join(
                self.add_image_run, 'sources.parquet'
            )
        )
        self.associations_add = pd.read_parquet(
            os.path.join(
                self.add_image_run, 'associations.parquet'
            )
        )  

    def test_forced_num(self):
        '''
        See documentation for test_forced_num in property_check.
        '''
        compare_runs.test_forced_num(self, self.forced_files, self.forced_files_add)
