import pickle
from os import path
from unittest import skipIf

from astropy.coordinates import SkyCoord, Angle
from django.conf import settings
from django.test import SimpleTestCase

from vast_pipeline.utils import external_query

class ExternalQueryTest(SimpleTestCase):
    def setUp(self):
        # coordinates for SN 2018cow
        self.coord = SkyCoord(
            ra="16:16:00.220", dec="22:16:04.91", unit="hourangle,deg"
        )
        self.radius = Angle("1arcmin")
        self.data_dir = path.join("vast_pipeline", "tests", "data")

    def test_simbad(self):
        raw_simbad_results = pickle.load(open(path.join(self.data_dir, "simbad_results.pickle"), "rb"))
        simbad_results = external_query.simbad(self.coord, self.radius, input=raw_simbad_results)
        required_keys = {'object_name', 'separation_arcsec', 'otype',
                         'ra_hms', 'dec_dms', 'otype_long', 'database'}
        self.assertIsInstance(simbad_results, list)
        self.assertGreaterEqual(len(simbad_results), 2)
        for result in simbad_results:
            self.assertIsInstance(result, dict)
            self.assertTrue(required_keys <= set(result.keys()))
            self.assertIsInstance(result['ra_hms'], str)
            self.assertIsInstance(result['dec_dms'], str)
            self.assertIsInstance(result['separation_arcsec'], float)
            self.assertEqual(result['database'], 'SIMBAD')
        self.assertEqual(simbad_results[0]["object_name"], "SN 2018cow")

    def test_ned(self):
        raw_ned_results = pickle.load(open(path.join(self.data_dir, "ned_results.pickle"), "rb"))
        ned_results = external_query.ned(self.coord, self.radius, input=raw_ned_results)
        # Make sure we have a list of 39 dicts with required_keys and correct types/values
        required_keys = {'object_name', 'separation_arcsec', 'otype',
                         'ra_hms', 'dec_dms', 'otype_long', 'database'}
        self.assertIsInstance(ned_results, list)
        self.assertGreaterEqual(len(ned_results), 39)
        for result in ned_results:
            self.assertIsInstance(result, dict)
            self.assertTrue(required_keys <= set(result.keys()))
            self.assertIsInstance(result['ra_hms'], str)
            self.assertIsInstance(result['dec_dms'], str)
            self.assertIsInstance(result['separation_arcsec'], float)
            self.assertEqual(result['database'], 'NED')
            self.assertIn(result['otype'], external_query.NED_OTYPES)
        self.assertEqual(ned_results[0]["object_name"], "SN 2018cow")
        # Check arcsec conversion is correct for the first result
        self.assertAlmostEqual(ned_results[0]["separation_arcsec"], 0.12, places=2)

    @skipIf(
        settings.TNS_API_KEY is None or settings.TNS_USER_AGENT is None,
        "TNS_API_KEY or TNS_USER_AGENT not defined in settings.",
    )
    def test_tns(self):
        tns_results = external_query.tns(self.coord, self.radius)
        self.assertGreaterEqual(len(tns_results), 1)
        self.assertEqual(tns_results[0]["object_name"], "2018cow")
