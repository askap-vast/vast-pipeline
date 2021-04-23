import os
from typing import Any, Dict
import uuid

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, override_settings
import strictyaml as yaml

from vast_pipeline.management.commands.initpiperun import make_config_template
from vast_pipeline.pipeline.config import PipelineConfig
from vast_pipeline.pipeline.errors import PipelineConfigError
from vast_pipeline.utils.utils import dict_merge


TEST_ROOT = os.path.join(settings.BASE_DIR, "vast_pipeline", "tests")


@override_settings(
    PIPELINE_WORKING_DIR=os.path.join(TEST_ROOT, "pipeline-runs"),
    MAX_PIPERUN_IMAGES=10,
)
class CheckRunConfigValidationTest(SimpleTestCase):
    def setUp(self):
        # load a base run configuration file
        self.config_path = os.path.join(
            settings.PIPELINE_WORKING_DIR, "basic-association", "config.yaml"
        )
        with open(self.config_path) as fh:
            config_text = fh.read()
        config_dict: Dict[str, Any] = yaml.load(config_text).data
        config_dict["run"]["path"] = os.path.dirname(self.config_path)

        # make a template config based on defaults
        config_defaults_str = make_config_template(
            PipelineConfig.TEMPLATE_PATH, **settings.PIPE_RUN_CONFIG_DEFAULTS
        )
        config_defaults_dict: Dict[str, Any] = yaml.load(config_defaults_str).data

        # merge configs
        self.config_dict = dict_merge(config_defaults_dict, config_dict)

    def test_valid_config(self):
        config_yaml = yaml.as_document(self.config_dict)
        pipeline_config = PipelineConfig(config_yaml)
        pipeline_config.validate()

    def test_duplicated_files(self):
        for input_type in PipelineConfig._REQUIRED_INPUT_TYPES:
            with self.subTest(input_type=input_type):
                # duplicate the first input file
                input_file_list = self.config_dict["inputs"][input_type]
                input_file_list[1] = input_file_list[0]
                config_yaml = yaml.as_document(self.config_dict)
                with self.assertRaises(PipelineConfigError):
                    pipeline_config = PipelineConfig(config_yaml)
                    pipeline_config.validate()

    def test_nr_files_differs(self):
        for input_type in PipelineConfig._REQUIRED_INPUT_TYPES:
            with self.subTest(input_type=input_type):
                # add a new unique input file
                input_file_list = self.config_dict["inputs"][input_type]
                input_file_list.append(input_file_list[0].replace("01", "0x"))
                config_yaml = yaml.as_document(self.config_dict)
                with self.assertRaises(PipelineConfigError):
                    pipeline_config = PipelineConfig(config_yaml)
                    pipeline_config.validate()

    def test_source_finder_value(self):
        self.config_dict["measurements"]["source_finder"] = "foo"
        config_yaml = yaml.as_document(self.config_dict)
        with self.assertRaises(PipelineConfigError):
            pipeline_config = PipelineConfig(config_yaml)
            pipeline_config.validate()

    def test_association_method_value(self):
        # test valid options
        for method in PipelineConfig._VALID_ASSOC_METHODS:
            with self.subTest(method=method):
                self.config_dict["source_association"]["method"] = method
                config_yaml = yaml.as_document(self.config_dict)
                pipeline_config = PipelineConfig(config_yaml)
                pipeline_config.validate()
        # test invalid option
        method = "foo"
        with self.subTest(method=method):
            self.config_dict["source_association"]["method"] = method
            config_yaml = yaml.as_document(self.config_dict)
            with self.assertRaises(PipelineConfigError):
                pipeline_config = PipelineConfig(config_yaml)
                pipeline_config.validate()

    def test_background_optional(self):
        """Background inputs are optional if source monitoring is false."""
        self.config_dict["source_monitoring"]["monitor"] = False
        del self.config_dict["inputs"]["background"]
        config_yaml = yaml.as_document(self.config_dict)
        pipeline_config = PipelineConfig(config_yaml)
        pipeline_config.validate()

    def test_background_for_source_monitoring(self):
        """Background input images must be provided if source monitoring is true."""
        self.config_dict["source_monitoring"]["monitor"] = True
        del self.config_dict["inputs"]["background"]
        config_yaml = yaml.as_document(self.config_dict)
        with self.assertRaises(PipelineConfigError):
            pipeline_config = PipelineConfig(config_yaml)
            pipeline_config.validate()

    def test_maximum_input_images(self):
        max_files = settings.MAX_PIPERUN_IMAGES
        user = AnonymousUser()
        n_files_to_add = max_files - len(self.config_dict["inputs"]["image"]) + 1
        for input_type in PipelineConfig._REQUIRED_INPUT_TYPES:
            input_file_list = self.config_dict["inputs"][input_type]
            input_file_list.extend([str(uuid.uuid4()) for _ in range(n_files_to_add)])
        config_yaml = yaml.as_document(self.config_dict)
        with self.assertRaises(PipelineConfigError):
            pipeline_config = PipelineConfig(config_yaml)
            pipeline_config.validate(user=user)  # type: ignore[arg-type]

    def test_minimum_two_inputs(self):
        for input_type in PipelineConfig._REQUIRED_INPUT_TYPES:
            self.config_dict["inputs"][input_type] = [
                self.config_dict["inputs"][input_type][0],
            ]
        config_yaml = yaml.as_document(self.config_dict)
        with self.assertRaises(PipelineConfigError):
            pipeline_config = PipelineConfig(config_yaml)
            pipeline_config.validate()

    def test_input_files_exist(self):
        # add a fake input file to each input list
        for input_type in PipelineConfig._REQUIRED_INPUT_TYPES:
            input_file_list = self.config_dict["inputs"][input_type]
            input_file_list.append(input_file_list[0].replace("01", "0x"))
        config_yaml = yaml.as_document(self.config_dict)
        with self.assertRaises(PipelineConfigError):
            pipeline_config = PipelineConfig(config_yaml)
            pipeline_config.validate()
