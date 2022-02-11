from django.test import SimpleTestCase

from astropy.coordinates import Longitude, Latitude

from vast_pipeline.utils.utils import deg2hms, deg2dms


class ExternalQueryTest(SimpleTestCase):
    def setUp(self):
        self.precision_test_inputs = [
            {
                "input": {
                    "class": Longitude,
                    "value": "23:16:09.951",
                    "unit": "hourangle",
                },
                "tests": [
                    {
                        "params": {"truncate": False, "precision": 2},
                        "output": "23:16:09.95",
                    },
                    {
                        "params": {"truncate": False, "precision": 1},
                        "output": "23:16:10.0",
                    },
                    {
                        "params": {"truncate": False, "precision": 0},
                        "output": "23:16:10",
                    },
                    {
                        "params": {"truncate": True, "precision": 2},
                        "output": "23:16:09.95",
                    },
                    {
                        "params": {"truncate": True, "precision": 1},
                        "output": "23:16:09.9",
                    },
                    {
                        "params": {"truncate": True, "precision": 0},
                        "output": "23:16:09",
                    },
                ],
            },
            {
                "input": {
                    "class": Longitude,
                    "value": "02:01:59.999",
                    "unit": "hourangle",
                },
                "tests": [
                    {
                        "params": {"truncate": False, "precision": 2},
                        "output": "02:02:00.00",
                    },
                    {
                        "params": {"truncate": False, "precision": 1},
                        "output": "02:02:00.0",
                    },
                    {
                        "params": {"truncate": False, "precision": 0},
                        "output": "02:02:00",
                    },
                    {
                        "params": {"truncate": True, "precision": 2},
                        "output": "02:01:59.99",
                    },
                    {
                        "params": {"truncate": True, "precision": 1},
                        "output": "02:01:59.9",
                    },
                    {
                        "params": {"truncate": True, "precision": 0},
                        "output": "02:01:59",
                    },
                ],
            },
            {
                "input": {
                    "class": Latitude,
                    "value": "-22:57:28.8905",
                    "unit": "deg",
                },
                "tests": [
                    {
                        "params": {"truncate": False, "precision": 3},
                        "output": "-22:57:28.891",
                    },
                    {
                        "params": {"truncate": False, "precision": 2},
                        "output": "-22:57:28.89",
                    },
                    {
                        "params": {"truncate": False, "precision": 1},
                        "output": "-22:57:28.9",
                    },
                    {
                        "params": {"truncate": False, "precision": 0},
                        "output": "-22:57:29",
                    },
                    {
                        "params": {"truncate": True, "precision": 3},
                        "output": "-22:57:28.890",
                    },
                    {
                        "params": {"truncate": True, "precision": 2},
                        "output": "-22:57:28.89",
                    },
                    {
                        "params": {"truncate": True, "precision": 1},
                        "output": "-22:57:28.8",
                    },
                    {
                        "params": {"truncate": True, "precision": 0},
                        "output": "-22:57:28",
                    },
                ],
            },
            {
                "input": {
                    "class": Latitude,
                    "value": "75:32:28.9994",
                    "unit": "deg",
                },
                "tests": [
                    {
                        "params": {"truncate": False, "precision": 3},
                        "output": "+75:32:28.999",
                    },
                    {
                        "params": {"truncate": False, "precision": 2},
                        "output": "+75:32:29.00",
                    },
                    {
                        "params": {"truncate": False, "precision": 1},
                        "output": "+75:32:29.0",
                    },
                    {
                        "params": {"truncate": False, "precision": 0},
                        "output": "+75:32:29",
                    },
                    {
                        "params": {"truncate": True, "precision": 3},
                        "output": "+75:32:28.999",
                    },
                    {
                        "params": {"truncate": True, "precision": 2},
                        "output": "+75:32:28.99",
                    },
                    {
                        "params": {"truncate": True, "precision": 1},
                        "output": "+75:32:28.9",
                    },
                    {
                        "params": {"truncate": True, "precision": 0},
                        "output": "+75:32:28",
                    },
                ],
            },
            {
                "input": {
                    "class": Latitude,
                    "value": "75:32:28.5",
                    "unit": "deg",
                },
                "tests": [
                    {
                        "params": {"truncate": False, "precision": 3},
                        "output": "+75:32:28.500",
                    },
                    {
                        "params": {"truncate": False, "precision": 2},
                        "output": "+75:32:28.50",
                    },
                    {
                        "params": {"truncate": False, "precision": 1},
                        "output": "+75:32:28.5",
                    },
                    {
                        "params": {"truncate": False, "precision": 0},
                        "output": "+75:32:29",
                    },
                    {
                        "params": {"truncate": True, "precision": 3},
                        "output": "+75:32:28.500",
                    },
                    {
                        "params": {"truncate": True, "precision": 2},
                        "output": "+75:32:28.50",
                    },
                    {
                        "params": {"truncate": True, "precision": 1},
                        "output": "+75:32:28.5",
                    },
                    {
                        "params": {"truncate": True, "precision": 0},
                        "output": "+75:32:28",
                    },
                ],
            },
            {
                "input": {
                    "class": Latitude,
                    "value": "75:32:28",
                    "unit": "deg",
                },
                "tests": [
                    {
                        "params": {"truncate": False, "precision": 3},
                        "output": "+75:32:28.000",
                    },
                    {
                        "params": {"truncate": False, "precision": 2},
                        "output": "+75:32:28.00",
                    },
                    {
                        "params": {"truncate": False, "precision": 1},
                        "output": "+75:32:28.0",
                    },
                    {
                        "params": {"truncate": False, "precision": 0},
                        "output": "+75:32:28",
                    },
                    {
                        "params": {"truncate": True, "precision": 3},
                        "output": "+75:32:28.000",
                    },
                    {
                        "params": {"truncate": True, "precision": 2},
                        "output": "+75:32:28.00",
                    },
                    {
                        "params": {"truncate": True, "precision": 1},
                        "output": "+75:32:28.0",
                    },
                    {
                        "params": {"truncate": True, "precision": 0},
                        "output": "+75:32:28",
                    },
                ],
            },
        ]

    def test_string_precision(self):
        """Test various precision roundings."""
        for test_input in self.precision_test_inputs:
            test_func = (
                deg2hms if test_input["input"]["class"] == Longitude else deg2dms
            )
            for test in test_input["tests"]:
                with self.subTest(
                    input=test_input["input"]["value"],
                    angle_class=test_input["input"]["class"],
                    precision=test["params"]["precision"],
                    truncate=test["params"]["truncate"],
                ):
                    test_input_obj = test_input["input"]["class"](
                        test_input["input"]["value"], unit=test_input["input"]["unit"]
                    )
                    test_output = test_func(test_input_obj.deg, **test["params"])
                    self.assertEqual(test_output, test["output"])

    def test_ra_string_separators(self):
        longitude = Longitude("23:16:09.951", unit="hourangle")
        hms_string = deg2hms(
            longitude.deg, hms_format=False, precision=2, truncate=False
        )
        self.assertEqual(hms_string, "23:16:09.95")
        hms_string = deg2hms(
            longitude.deg, hms_format=True, precision=2, truncate=False
        )
        self.assertEqual(hms_string, "23h16m09.95s")

    def test_dec_string_separators(self):
        latitude = Latitude("-22:57:28.8905", unit="deg")
        dms_string = deg2dms(
            latitude.deg, dms_format=False, precision=2, truncate=False
        )
        self.assertEqual(dms_string, "-22:57:28.89")
        dms_string = deg2dms(latitude.deg, dms_format=True, precision=2, truncate=False)
        self.assertEqual(dms_string, "-22d57m28.89s")
