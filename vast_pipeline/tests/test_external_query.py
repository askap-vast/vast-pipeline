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

    def test_simbad(self):
        simbad_results = external_query.simbad(self.coord, self.radius)
        self.assertGreaterEqual(len(simbad_results), 2)
        self.assertEqual(simbad_results[0]["object_name"], "SN 2018cow")

    def test_ned(self):
        ned_results = external_query.ned(self.coord, self.radius)
        self.assertGreaterEqual(len(ned_results), 39)
        self.assertEqual(ned_results[0]["object_name"], "SN 2018cow")

    @skipIf(
        settings.TNS_API_KEY is None or settings.TNS_USER_AGENT is None,
        "TNS_API_KEY or TNS_USER_AGENT not defined in settings.",
    )
    def test_tns(self):
        tns_results = external_query.tns(self.coord, self.radius)
        self.assertGreaterEqual(len(tns_results), 1)
        self.assertEqual(tns_results[0]["object_name"], "2018cow")
