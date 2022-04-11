import glob
import os

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError

from vast_pipeline.models import Image


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
    RAW_IMAGE_DIR=os.path.join(TEST_ROOT, 'data'),
)
class RunPipelineTest(TestCase):
    run_dir: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.run_dir = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association')

    def setUp(self):
        # TODO: replace with a load images function and call 'runpipeline'
        # from each tests (e.g. test_basic_assoc, text_advanced_assoc, etc.)
        call_command('runpipeline', self.run_dir)
        self.run_logs = glob.glob(os.path.join(self.run_dir, '*_log.txt'))

    def tearDown(self):
        """Clean up the run directory after the test by removing the backup config and
        all run logs.
        """
        call_command('clearpiperun', self.run_dir)
        os.remove(os.path.join(self.run_dir, "config_prev.yaml"))
        for run_log in self.run_logs:
            os.remove(run_log)

    def test_check_run(self):
        self.assertEqual(len(self.run_logs), 1)


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
    RAW_IMAGE_DIR=os.path.join(TEST_ROOT, 'data'),
)
class RunPipelineInvalidCatalogTest(TestCase):
    def test_invalid_catalog(self):
        run_dir = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association-invalid-catalog')
        with self.assertRaises(CommandError) as context:
            call_command('runpipeline', run_dir)
        # check the original exception raised during runpipeline command is a KeyError
        # (caused by attempting to read the invalid catalog)
        original_exception = context.exception.__context__
        self.assertIsInstance(original_exception, KeyError)
        # check that only the image for the invalid catalog was not saved
        for epoch in range(1, 5):
            image = Image.objects.get(name=f"epoch{epoch:02d}.fits")
            self.assertIsInstance(image, Image)
        with self.assertRaises(Image.DoesNotExist):
            Image.objects.get(name="epoch05.fits")
