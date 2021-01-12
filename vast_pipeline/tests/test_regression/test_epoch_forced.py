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
class BasicEpochForcedTest(TestCase):
    '''
    Test pipeline under epoch based forced basic association method returns
    expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-basic-forced'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR,
            'regression',
            'epoch-add-image-parallel-basic-forced'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # normal run
        call_command('runpipeline', self.base_run)

        self.forced_files = {}
        for f in os.listdir(self.base_run):
            if f[:6] == 'forced':
                self.forced_files[f] = pd.read_parquet(
                    os.path.join(self.base_run, f)
                )
        self.sources_base = pd.read_parquet(
            os.path.join(
                self.base_run, 'sources.parquet'
            )
        )
        self.ass_base = pd.read_parquet(
            os.path.join(
                self.base_run, 'associations.parquet'
            )
        )

        # add image run
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)

        self.forced_compare = {}
        for f in os.listdir(self.compare_run):
            if f[:6] == 'forced' and f[-3:] != 'bak':
                self.forced_compare[f] = pd.read_parquet(
                    os.path.join(self.compare_run, f)
                )
        self.sources_compare = pd.read_parquet(
            os.path.join(
                self.compare_run, 'sources.parquet'
            )
        )
        self.ass_compare = pd.read_parquet(
            os.path.join(
                self.compare_run, 'associations.parquet'
            )
        )

    def test_forced_num(self):
        '''
        See documentation for test_forced_num in compare_runs.
        '''
        compare_runs.test_forced_num(
            self, self.forced_files, self.forced_compare
        )

    def test_known_in_forced(self):
        '''
        See documentation for test_known_in_forced in propery_check.
        '''
        # the expected forced extractions for PSR J2129-04
        exp_forced = {
            '2118-06A_EPOCH01', '2118-06A_EPOCH12','2118-06A_EPOCH02',
            '2118-06A_EPOCH03x'
        }

        for forced, sources, ass in zip(
            [self.forced_files, self.forced_compare],
            [self.sources_base, self.sources_compare],
            [self.ass_base, self.ass_compare]
        ):
            property_check.test_known_in_forced(
                self, forced, sources, ass, 6, exp_forced
            )


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class AdvancedEpochForcedTest(TestCase):
    '''
    Test pipeline under epoch based forced advanced association method returns
    expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, 'regression', 'epoch-advanced-forced'
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR,
            'regression',
            'epoch-add-image-parallel-advanced-forced'
        )
        self.config_base = os.path.join(self.compare_run, 'config_base.py')
        self.config_add = os.path.join(self.compare_run, 'config_add.py')
        self.config = os.path.join(self.compare_run, 'config.py')

        # normal run
        call_command('runpipeline', self.base_run)

        self.forced_files = {}
        for f in os.listdir(self.base_run):
            if f[:6] == 'forced':
                self.forced_files[f] = pd.read_parquet(
                    os.path.join(self.base_run, f)
                )
        self.sources_base = pd.read_parquet(
            os.path.join(
                self.base_run, 'sources.parquet'
            )
        )
        self.ass_base = pd.read_parquet(
            os.path.join(
                self.base_run, 'associations.parquet'
            )
        )

        # add image run
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.compare_run)
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.compare_run)

        self.forced_compare = {}
        for f in os.listdir(self.compare_run):
            if f[:6] == 'forced' and f[-3:] != 'bak':
                self.forced_compare[f] = pd.read_parquet(
                    os.path.join(self.compare_run, f)
                )
        self.sources_compare = pd.read_parquet(
            os.path.join(
                self.compare_run, 'sources.parquet'
            )
        )
        self.ass_compare = pd.read_parquet(
            os.path.join(
                self.compare_run, 'associations.parquet'
            )
        )

    def test_forced_num(self):
        '''
        See documentation for test_forced_num in compare_runs.
        '''
        compare_runs.test_forced_num(
            self, self.forced_files, self.forced_compare
        )


@unittest.skipIf(
    no_data,
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class DeruiterEpochForcedTest(TestCase):
    '''
    Test pipeline under epoch based forced advanced association method returns
    expected results. This is a property check and not a comparison because
    deruiter uses the largest beam size in present images, which gives slightly
    different results compared to the normal epoch based run.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data and run the pipeline.
        '''
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR,
            'regression',
            'epoch-add-image-parallel-deruiter-forced'
        )
        self.config_base = os.path.join(self.base_run, 'config_base.py')
        self.config_add = os.path.join(self.base_run, 'config_add.py')
        self.config = os.path.join(self.base_run, 'config.py')

        # add image run
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.base_run)
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.base_run)

        self.forced = {}
        for f in os.listdir(self.base_run):
            if f[:6] == 'forced' and f[-3:] != 'bak':
                self.forced[f] = pd.read_parquet(
                    os.path.join(self.base_run, f)
                )

    def test_forced_num(self):
        '''
        See documentation for test_forced_num in property_check.
        '''
        property_check.test_forced_num(
            self, self.forced, 982)
