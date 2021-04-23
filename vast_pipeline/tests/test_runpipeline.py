import os

from django.conf import settings as s
from django.test import TestCase, override_settings
from django.core.management import call_command


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
    RAW_IMAGE_DIR=os.path.join(TEST_ROOT, 'data'),
)
class RunPipelineTest(TestCase):
    basic_assoc_run: str

    @classmethod
    def setUpTestData(cls):
        cls.basic_assoc_run = os.path.join(s.PIPELINE_WORKING_DIR, 'basic-association')

    def setUp(self):
        # TODO: replace with a load images function and call 'runpipeline'
        # from each tests (e.g. test_basic_assoc, text_advanced_assoc, etc.)
        call_command('runpipeline', self.basic_assoc_run)

    def test_check_run(self):
        run_log_path = os.path.join(self.basic_assoc_run, 'log.txt')
        self.assertTrue(os.path.exists(run_log_path))
