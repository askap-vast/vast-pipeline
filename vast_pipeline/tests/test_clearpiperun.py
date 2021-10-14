import os
from typing import Dict

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.management import call_command

from vast_pipeline.models import Run, Image, Band, SkyRegion


TEST_ROOT = os.path.join(s.BASE_DIR, "vast_pipeline", "tests")


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, "pipeline-runs"),
)
class ClearPipelineRunTest(TestCase):
    band: Band
    run_1: Run
    run_2: Run
    skyregs: Dict[str, SkyRegion]
    images: Dict[str, Image]

    @classmethod
    def setUpTestData(cls):
        default_image_kwargs = dict(
            measurements_path="",
            polarisation="I",
            path="",
            datetime=timezone.now(),
            jd=0.0,
            ra=0.0,
            dec=0.0,
            fov_bmaj=0.0,
            fov_bmin=0.0,
            physical_bmaj=0.0,
            physical_bmin=0.0,
            radius_pixels=0.0,
            beam_bmaj=0.0,
            beam_bmin=0.0,
            beam_bpa=0.0,
            rms_median=0.0,
            rms_min=0.0,
            rms_max=0.0,
        )
        default_skyreg_kwargs = dict(
            centre_ra=0.0,
            centre_dec=0.0,
            width_ra=0.0,
            width_dec=0.0,
            xtr_radius=0.0,
            x=0.0,
            y=0.0,
            z=0.0,
        )
        # Create test objects:
        #   - 2 Runs
        #   - 3 SkyRegions
        #   - 4 Images
        # run_1 contains 3 images: image_a1, image_b1, image_a2.
        # run_2 contains 2 images: image_b1, image_c1.
        # The letter suffix indicates the sky region, e.g. image_a1 is in sky region a.

        # create a band
        cls.band = Band.objects.create(name="band", frequency=887, bandwidth=128)
        # create runs
        cls.run_1 = Run.objects.create(name="run_1", path="run_1")
        cls.run_2 = Run.objects.create(name="run_2", path="run_2")
        # create sky regions
        cls.skyregs = {
            k: SkyRegion.objects.create(**default_skyreg_kwargs)
            for k in ("a", "b", "c")
        }
        # create some images
        cls.images = {
            f"{k}1": Image.objects.create(
                band=cls.band,
                skyreg=skyreg,
                name=f"image_{k}1",
                **default_image_kwargs,
            )
            for k, skyreg in cls.skyregs.items()
        }
        cls.images["a2"] = Image.objects.create(
            band=cls.band,
            skyreg=cls.skyregs["a"],
            name="image_a2",
            **default_image_kwargs,
        )
        cls.images["a1"].run.add(cls.run_1)
        cls.images["a2"].run.add(cls.run_1)
        cls.images["b1"].run.add(cls.run_1)
        cls.images["b1"].run.add(cls.run_2)
        cls.images["c1"].run.add(cls.run_2)

        cls.skyregs["a"].run.add(cls.run_1)
        cls.skyregs["b"].run.add(cls.run_1)
        cls.skyregs["b"].run.add(cls.run_2)
        cls.skyregs["c"].run.add(cls.run_2)

    def test_data(self):
        """Check that the object relationships exist as expected.
        """
        self.assertEqual(Image.objects.filter(run=self.run_1).count(), 3)
        self.assertEqual(Image.objects.filter(run=self.run_2).count(), 2)

        self.assertEqual(SkyRegion.objects.filter(run=self.run_1).count(), 2)
        self.assertEqual(SkyRegion.objects.filter(run=self.run_2).count(), 2)

    def test_clearpiperun(self):
        """Delete a run and check that the appropriate objects are also deleted.
        """
        # delete run_1
        call_command("clearpiperun", self.run_1.name)

        # ensure the images and sky regions that were only used in run_1 are deleted
        with self.assertRaises(Image.DoesNotExist):
            _ = Image.objects.get(name="image_a1")
        with self.assertRaises(Image.DoesNotExist):
            _ = Image.objects.get(name="image_a2")
        with self.assertRaises(SkyRegion.DoesNotExist):
            _ = SkyRegion.objects.get(pk=self.skyregs["a"].pk)
        # ensure the images and sky regions that were used in both run_1 and run_2 remain
        _ = Image.objects.get(name="image_b1")
        _ = SkyRegion.objects.get(pk=self.skyregs["b"].pk)

        # delete run_2
        call_command("clearpiperun", self.run_2.name)
        # ensure no images nor sky regions remain
        self.assertEqual(Image.objects.count(), 0)
        self.assertEqual(SkyRegion.objects.count(), 0)
