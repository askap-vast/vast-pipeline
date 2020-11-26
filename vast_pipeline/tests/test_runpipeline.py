import os

from django.conf import settings as s
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.management import call_command

from vast_pipeline.pipeline.main import Pipeline
from vast_pipeline.pipeline.errors import PipelineConfigError


TEST_ROOT = os.path.join(s.BASE_DIR, 'vast_pipeline', 'tests')


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs'),
    RAW_IMAGE_DIR=os.path.join(TEST_ROOT, 'data'),
)
class RunPipelineTest(TestCase):

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


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, 'pipeline-runs')
)
class CheckRunConfigValidationTest(SimpleTestCase):

    def setUp(self):
        config_path = os.path.join(
            s.PIPELINE_WORKING_DIR,
            'basic-association',
            'config.py'
        )

        self.pipe_run = Pipeline(
            name='dj_test_basic-association',
            config_path=config_path
        )
        self.config_path = config_path

    def test_duplicated_files_image_files(self):
        key = 'IMAGE_FILES'
        f_list = getattr(self.pipe_run.config, key)
        f_list.update({len(f_list): list(f_list.values())[0]})
        setattr(self.pipe_run.config, key, f_list)
        with self.assertRaises(PipelineConfigError):
            self.pipe_run.validate_cfg()

    def test_duplicated_files_selavy_files(self):
        key = 'SELAVY_FILES'
        f_list = getattr(self.pipe_run.config, key)
        f_list.update({len(f_list): list(f_list.values())[0]})
        setattr(self.pipe_run.config, key, f_list)
        with self.assertRaises(PipelineConfigError):
            self.pipe_run.validate_cfg()

    def test_duplicated_files_noise_files(self):
        key = 'NOISE_FILES'
        f_list = getattr(self.pipe_run.config, key)
        f_list.update({len(f_list): list(f_list.values())[0]})
        setattr(self.pipe_run.config, key, f_list)
        with self.assertRaises(PipelineConfigError):
            self.pipe_run.validate_cfg()

    def test_nr_files_differs_for_image_files(self):
        key = 'IMAGE_FILES'
        f_list = getattr(self.pipe_run.config, key)
        new_value = list(f_list.values())[0][0]
        new_value = new_value.replace('04', '05')
        f_list.update({len(f_list): new_value})
        setattr(self.pipe_run.config, key, f_list)
        with self.assertRaises(PipelineConfigError):
            self.pipe_run.validate_cfg()

    def test_nr_files_differs_for_selavy_files(self):
        key = 'SELAVY_FILES'
        f_list = getattr(self.pipe_run.config, key)
        new_value = list(f_list.values())[0][0]
        new_value = new_value.replace('04', '05')
        f_list.update({len(f_list): new_value})
        setattr(self.pipe_run.config, key, f_list)
        with self.assertRaises(PipelineConfigError):
            self.pipe_run.validate_cfg()

    def test_nr_files_differs_for_noise_files(self):
        key = 'NOISE_FILES'
        f_list = getattr(self.pipe_run.config, key)
        new_value = list(f_list.values())[0][0]
        new_value = new_value.replace('04', '05')
        f_list.update({len(f_list): new_value})
        setattr(self.pipe_run.config, key, f_list)
        with self.assertRaises(PipelineConfigError):
            self.pipe_run.validate_cfg()
