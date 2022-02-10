from django.test import SimpleTestCase

from astropy.coordinates import SkyCoord

from vast_pipeline.utils.utils import deg2hms, deg2dms


class ExternalQueryTest(SimpleTestCase):
    def setUp(self):
        self.coord = SkyCoord(
            ra="23:16:09.951", dec="-22:57:28.8905", unit="hourangle,deg"
        )

    def test_ra_string_precision_rounding(self):
        """Test various precision roundings."""
        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=True, precision=2, truncate=False
        )
        self.assertEqual(hms_string, "23h16m09.95s")

        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=True, precision=1, truncate=False
        )
        self.assertEqual(hms_string, "23h16m10.0s")

        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=True, precision=0, truncate=False
        )
        self.assertEqual(hms_string, "23h16m10s")

    def test_ra_string_precision_truncating(self):
        """Test various precision truncatings."""
        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=True, precision=2, truncate=True
        )
        self.assertEqual(hms_string, "23h16m09.95s")

        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=True, precision=1, truncate=True
        )
        self.assertEqual(hms_string, "23h16m09.9s")

        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=True, precision=0, truncate=True
        )
        self.assertEqual(hms_string, "23h16m09s")

    def test_ra_string_colon_separator(self):
        hms_string = deg2hms(
            self.coord.ra.deg, hms_format=False, precision=2, truncate=False
        )
        self.assertEqual(hms_string, "23:16:09.95")

    def test_dec_string_precision_rounding(self):
        """Test various precision roundings."""
        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=3, truncate=False
        )
        self.assertEqual(dms_string, "-22d57m28.891s")

        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=2, truncate=False
        )
        self.assertEqual(dms_string, "-22d57m28.89s")

        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=1, truncate=False
        )
        self.assertEqual(dms_string, "-22d57m28.9s")

        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=0, truncate=False
        )
        self.assertEqual(dms_string, "-22d57m29s")

    def test_dec_string_precision_truncating(self):
        """Test various precision truncatings."""
        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=3, truncate=True
        )
        self.assertEqual(dms_string, "-22d57m28.890s")

        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=2, truncate=True
        )
        self.assertEqual(dms_string, "-22d57m28.89s")

        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=1, truncate=True
        )
        self.assertEqual(dms_string, "-22d57m28.8s")

        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=True, precision=0, truncate=True
        )
        self.assertEqual(dms_string, "-22d57m28s")

    def test_dec_string_colon_separator(self):
        dms_string = deg2dms(
            self.coord.dec.deg, dms_format=False, precision=3, truncate=False
        )
        self.assertEqual(dms_string, "-22:57:28.891")
