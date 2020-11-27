import os
import types
import pandas as pd
import unittest

from astropy.coordinates import SkyCoord, match_coordinates_sky

from django.conf import settings as s
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.management import call_command

from vast_pipeline.pipeline.main import Pipeline
from vast_pipeline.pipeline.errors import PipelineConfigError


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


no_data = not os.path.exists(os.path.join(TEST_ROOT, 'regression-data'))
@unittest.skipIf(
    no_data, 
    'The regression test data is missing, skipping regression tests'
)
@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
)
class RegressionTest(TestCase):
    '''
    Test pipeline returns expected results.
    '''

    @classmethod
    def setUpTestData(self):
        '''
        Set up directory to test data.
        '''
        self.basic_assoc_run = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-regression')

    def setUp(self):
        '''
        Run the pipeline with the test data.
        '''
        call_command('runpipeline', self.basic_assoc_run)

    def test_num_sources(self):
        '''
        Test the number of overall sources identified is correct. 
        '''
        sources = pd.read_parquet(os.path.join(s.PIPELINE_WORKING_DIR, 'basic-regression', 'sources.parquet'))
        
        self.assertTrue(len(sources.index) == 17165)

    def test_most_relations(self):
        '''
        Test that the highest relation source is the same, and in general the 
        top 10 sources with the most relations are correct.
        '''
        # get sources with highest number of relations
        relations = pd.read_parquet(
            os.path.join(
                s.PIPELINE_WORKING_DIR, 
                'basic-regression', 
                'relations.parquet'
            )
        )
        relations = (
            relations.pivot_table(index=['from_source_id'], aggfunc='size')
            .sort_values(ascending=False)
            .iloc[:12]
            .to_frame('relations')
        )

        # get ra and dec of highest relations sources
        sources = pd.read_parquet(
            os.path.join(
                s.PIPELINE_WORKING_DIR, 
                'basic-regression', 
                'sources.parquet'
            )
        )
        sources = sources.loc[relations.index, ['wavg_ra', 'wavg_dec']]

        # merge the dataframes
        highest_relations = pd.merge(sources, relations, on='from_source_id')
        highest_relations = (
            highest_relations.sort_values(
                by=['relations', 'wavg_ra'], 
                ascending=[False, True])
            .reset_index()
            .drop('from_source_id', axis=1)
        )

        # this is the expected highest relation sources
        expected = pd.DataFrame(
            [[320.503875, -2.682186, 50],
             [320.503987, -2.681935, 49],
             [320.503995, -2.681944, 49],
             [320.504224, -2.681775, 48],
             [320.504333, -2.681529, 48],
             [320.504340, -2.681538, 48],
             [320.504448, -2.681296, 47],
             [320.503663, -2.682327, 45],
             [320.503671, -2.682336, 45],
             [320.503903, -2.682164, 45],
             [320.504016, -2.681913, 45],
             [320.504023, -2.681921, 45]], 
             columns = ['wavg_ra', 'wavg_dec', 'relations']
        )

        # only checks that the first 4 decimal places are equal
        pd.testing.assert_frame_equal(
            highest_relations, 
            expected, 
            check_less_precise=4
        ) 

    def test_known_source(self):
        '''
        Check that PSR J2129-04 is detected as a new source and has correct 
        new_high_sigma.
        '''
        # from SIMBAD
        coords = SkyCoord(
            "21 29 45.29", "-04 29 11.9", 
            frame='icrs', 
            unit=('hourangle', 'deg')
        ) 

        sources = pd.read_parquet(
            os.path.join(
                s.PIPELINE_WORKING_DIR, 
                'basic-regression', 
                'sources.parquet'
            )
        )
        sources.reset_index(inplace=True)

        # find PSR J2129-04 by matching coordinates in sources
        source_coords = SkyCoord(
            sources.loc[:, 'wavg_ra'], 
            sources.loc[:, 'wavg_dec'], 
            unit=('deg', 'deg')
        )
        id_match, *_ = match_coordinates_sky(coords, source_coords)

        # check new and has correct new_high_sigma to 2 decimal places
        self.assertTrue(sources.loc[id_match, 'new'])
        self.assertTrue(
            abs(sources.loc[id_match, 'new_high_sigma'] - 12.380) < 1e-2
        )