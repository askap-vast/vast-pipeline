import os
from typing import Dict

from django.conf import settings as s
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from django.core.management import call_command

from vast_pipeline.models import Run, Image, Band, SkyRegion


TEST_ROOT = os.path.join(s.BASE_DIR, "vast_pipeline", "tests")


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, "pipeline-runs"),
)
class ClearPipelineRunTest(TransactionTestCase):
    band: Band
    run_1: Run
    run_2: Run
    skyregs: Dict[str, SkyRegion]
    images: Dict[str, Image]

    #@classmethod
    def setUp(self):
        print("setUpTestData running")
        try:
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
            self.band = Band.objects.create(name="band", frequency=887, bandwidth=128)
            # create runs
            self.run_1 = Run.objects.create(name="run_1", path="run_1")
            self.run_2 = Run.objects.create(name="run_2", path="run_2")
            # create sky regions
            self.skyregs = {
                k: SkyRegion.objects.create(**default_skyreg_kwargs)
                for k in ("a", "b", "c")
            }
            # create some images
            self.images = {
                f"{k}1": Image.objects.create(
                    band=self.band,
                    skyreg=skyreg,
                    name=f"image_{k}1",
                    **default_image_kwargs,
                )
                for k, skyreg in self.skyregs.items()
            }
            self.images["a2"] = Image.objects.create(
                band=self.band,
                skyreg=self.skyregs["a"],
                name="image_a2",
                **default_image_kwargs,
            )
            self.images["a1"].run.add(self.run_1)
            self.images["a2"].run.add(self.run_1)
            self.images["b1"].run.add(self.run_1)
            self.images["b1"].run.add(self.run_2)
            self.images["c1"].run.add(self.run_2)

            self.skyregs["a"].run.add(self.run_1)
            self.skyregs["b"].run.add(self.run_1)
            self.skyregs["b"].run.add(self.run_2)
            self.skyregs["c"].run.add(self.run_2)
        except Exception as e:
            print("Error in setUpTestData:", e)
            import traceback
            traceback.print_exc()
            raise

    """def setUp(self):
        print("setUp running")
        self.run_1 = self.__class__.run_1
        self.run_2 = self.__class__.run_2
        self.skyregs = self.__class__.skyregs
        self.images = self.__class__.images
    """

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
        call_command("clearpiperun", self.run_1.name, delete_images=True)

        # ensure the images and sky regions that were only used in run_1 are deleted
        with self.assertRaises(Image.DoesNotExist):
            _ = Image.objects.get(name="image_a1")
            print(_)
        with self.assertRaises(Image.DoesNotExist):
            _ = Image.objects.get(name="image_a2")
        with self.assertRaises(SkyRegion.DoesNotExist):
            _ = SkyRegion.objects.get(pk=self.skyregs["a"].pk)
        # ensure the images and sky regions that were used in both run_1 and run_2 remain
        _ = Image.objects.get(name="image_b1")
        _ = SkyRegion.objects.get(pk=self.skyregs["b"].pk)

        # delete run_2
        call_command("clearpiperun", self.run_2.name, delete_images=True)
        # ensure no images nor sky regions remain
        self.assertEqual(Image.objects.count(), 0)
        self.assertEqual(SkyRegion.objects.count(), 0)
