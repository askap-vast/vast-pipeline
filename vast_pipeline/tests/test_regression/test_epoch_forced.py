import os
import types
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
        base_path = 'epoch-basic-forced'
        compare_path = 'epoch-add-parallel-basic-forced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # normal run
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
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

        # remove directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
        base_path = 'epoch-advanced-forced'
        compare_path = 'epoch-add-parallel-advanced-forced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )
        self.compare_run = os.path.join(
            s.PIPELINE_WORKING_DIR, compare_path
        )

        # normal run
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
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

        # remove directories
        shutil.rmtree(self.base_run)
        shutil.rmtree(self.compare_run)

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
        base_path = 'epoch-add-parallel-deruiter-forced'
        self.base_run = os.path.join(
            s.PIPELINE_WORKING_DIR, base_path
        )

        # add image run
        make_testdir(self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02']
        )
        call_command('runpipeline', self.base_run)
        gen_config.gen_config(
            base_path,
            s.PIPELINE_WORKING_DIR,
            ['01', '03x', '02', '05x', '06x', '12']
        )
        call_command('runpipeline', self.base_run)

        self.forced = {}
        for f in os.listdir(self.base_run):
            if f[:6] == 'forced' and f[-3:] != 'bak':
                self.forced[f] = pd.read_parquet(
                    os.path.join(self.base_run, f)
                )

        # remove directory
        shutil.rmtree(self.base_run)

    def test_forced_num(self):
        '''
        See documentation for test_forced_num in property_check.
        '''
        property_check.test_forced_num(
            self, self.forced, 982)
