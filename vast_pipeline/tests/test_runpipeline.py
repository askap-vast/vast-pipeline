import glob
import os
from typing import List, Optional

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError

from vast_pipeline.models import Image


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


def _cleanup_test_run(run_dir: str, run_logs: Optional[List[str]] = None):
    call_command('clearpiperun', run_dir)
    prev_config_path = os.path.join(run_dir, "config_prev.yaml")
    if os.path.exists(prev_config_path):
        os.remove(prev_config_path)
    if run_logs is None:
        run_logs = glob.glob(os.path.join(run_dir, '*_log.txt'))
    for run_log in run_logs:
        os.remove(run_log)


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
    RAW_IMAGE_DIR=os.path.join(TEST_ROOT, 'data'),
)
class RunPipelineTest(TestCase):
    run_dir: str
    run_logs: Optional[List[str]] = None

    def tearDown(self):
        """Clean up the run directory after the test by removing the backup config and
        all run logs.
        """
        _cleanup_test_run(self.run_dir, run_logs=self.run_logs)

    def test_check_run(self):
        self.run_dir = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association')
        # TODO: replace with a load images function and call 'runpipeline'
        # from each tests (e.g. test_basic_assoc, text_advanced_assoc, etc.)
        call_command('runpipeline', self.run_dir)
        self.run_logs = glob.glob(os.path.join(self.run_dir, '*_log.txt'))
        self.assertEqual(len(self.run_logs), 1)

    def test_invalid_catalog(self):
        self.run_dir = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association-invalid-catalog')
        with self.assertRaises(CommandError) as context:
            call_command('runpipeline', self.run_dir)
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
        # clean up config backup
        os.remove(os.path.join(self.run_dir, "config_temp.yaml"))

    def test_pair_metrics_exist(self):
        self.run_dir = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association')
        call_command('runpipeline', self.run_dir)
        # check that the measurement pairs parquet file was written
        self.assertTrue(os.path.exists(os.path.join(self.run_dir, "measurement_pairs.parquet")))

    def test_no_pair_metrics(self):
        self.run_dir = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association-no-pairs')
        call_command('runpipeline', self.run_dir)
        # check that the measurement pairs parquet file was not written
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "measurement_pairs.parquet")))
        # check that at least one of the other parquets were written
        self.assertTrue(os.path.exists(os.path.join(self.run_dir, "sources.parquet")))
