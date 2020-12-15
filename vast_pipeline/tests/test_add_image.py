import os
import pandas as pd
import unittest

from astropy.coordinates import SkyCoord, match_coordinates_sky

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
class AddImageTest(TestCase):
    '''
    Test pipeline runs when adding an image.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data.
        '''
        self.add_image_run = os.path.join(s.PIPELINE_WORKING_DIR, 'add-image')
        self.config_base = os.path.join(self.add_image_run, 'config_base.py')
        self.config_add = os.path.join(self.add_image_run, 'config_add.py')
        self.config = os.path.join(self.add_image_run, 'config.py')

    def run_base(self):
        '''
        Run the pipeline without the additional image.
        '''
        os.system(f'cp {self.config_base} {self.config}')
        call_command('runpipeline', self.add_image_run)
        
    def run_add_image(self):
        '''
        Run the pipeline with the additional image.
        '''
        os.system(f'cp {self.config_add} {self.config}')
        call_command('runpipeline', self.add_image_run)

    def test_inc_assoc(self):
        '''
        Test that the number of associations increased with added images.
        '''
        # original run
        self.run_base()
        ass_backup = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )
        # add image run
        self.run_add_image()
        ass = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )
        self.assertTrue(len(ass) > len(ass_backup))

    def test_unique_assoc(self):
        '''
        Test that meas_id in associations are unique.
        '''
        self.run_base()
        self.run_add_image()
        
        ass = pd.read_parquet(
            os.path.join(self.add_image_run, 'associations.parquet')
        )

        self.assertTrue(ass['meas_id'].is_unique)

    def test_update_source(self):
        '''
        Test that the sources are correctly updated in the database.
        '''
        # check source database and file is the same after original run
        self.run_base()
        source_backup = pd.read_parquet(
            os.path.join(self.add_image_run, 'sources.parquet')
        )
        for ind in source_backup.index:
            n_meas_db = Source.objects.get(id=ind).n_meas
            n_meas_pd = source_backup.loc[ind, 'n_meas']
            self.assertTrue(n_meas_db == n_meas_pd)
        # check source database and file is the same after adding an image
        self.run_add_image()
        source = pd.read_parquet(
            os.path.join(self.add_image_run, 'sources.parquet')
        )
        for ind in source.index:
            n_meas_db = Source.objects.get(id=ind).n_meas
            n_meas_pd = source.loc[ind, 'n_meas']
            self.assertTrue(n_meas_db == n_meas_pd)
