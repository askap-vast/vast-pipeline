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
        self.all_image_run = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-regression')
        self.add_image_run = os.path.join(s.PIPELINE_WORKING_DIR, 'add-image')
        self.config_base = os.path.join(self.add_image_run, 'config_base.py')
        self.config_add = os.path.join(self.add_image_run, 'config_add.py')
        self.config = os.path.join(self.add_image_run, 'config.py')

    def setUp(self):
        '''
        Run the pipeline and read in files
        '''
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
        Test that the number of associations increased with added images.
        '''

        self.assertTrue(len(self.ass_add) > len(self.ass_backup))

    def test_update_source(self):
        '''
        Test that the sources are correctly updated in the database.
        '''
        # check source database and file is the same after original run
        for ind in self.sources_backup.index:
            n_meas_db = self.sources_backup_db.loc[ind, 'n_meas']
            n_meas_pd = self.sources_backup.loc[ind, 'n_meas']
            self.assertTrue(n_meas_db == n_meas_pd)

        # check source database and file is the same after adding an image
        for ind in self.sources_add.index:
            n_meas_db = self.sources_add_db.loc[ind, 'n_meas']
            n_meas_pd = self.sources_add.loc[ind, 'n_meas']
            self.assertTrue(n_meas_db == n_meas_pd)

    def test_sources(self):
        '''
        Test that the sources and total relations from one run with all images 
        and another with added image returns the same results.
        '''
        sources_all = self.sources_all.sort_values(by=['wavg_ra', 'wavg_dec']).reset_index(drop=True)
        sources_add = self.sources_add.sort_values(by=['wavg_ra', 'wavg_dec']).reset_index(drop=True)

        pd.testing.assert_frame_equal(
            sources_all, 
            sources_add, 
            check_less_precise=4
        )

    def test_relations(self):
        '''
        Test that the number relations are the same from one run with all 
        images and another with added image returns the same results.
        '''
        # compare number of relations per source
        relations_all = (
            self.relations_all.pivot_table(index=['from_source_id'], aggfunc='size')
            .to_frame('relations')
            .sort_index()
        )
        relations_add = (
            self.relations_add.pivot_table(index=['from_source_id'], aggfunc='size')
            .to_frame('relations')
            .sort_index()
        )

        self.assertTrue(len(relations_all) == len(relations_add))