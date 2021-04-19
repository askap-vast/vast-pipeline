import logging
import os
from typing import Any, Dict, List

from django.contrib.auth.models import User
from django.conf import settings
from jinja2 import Environment
import strictyaml as yaml

from vast_pipeline.utils.utils import dict_merge
from vast_pipeline.pipeline.errors import PipelineConfigError


logger = logging.getLogger(__name__)


def make_config_template(template_path: str, **kwargs) -> str:
    """Generate the contents of a run configuration file from on a Jinja2 template.

    Args:
        template_path: Path to a Jinja2 template.
        **kwargs: keyword arguments passed to the template renderer to fill in template
            variables.

    Returns:
        Filled in template string.
    """
    with open(template_path, "r") as fp:
        template_str = fp.read()
    env = Environment(trim_blocks=True, lstrip_blocks=True)
    template = env.from_string(template_str)
    return template.render(**kwargs)


class PipelineConfig:
    """Pipeline run configuration.

    Attributes:
        SCHEMA: class attribute containing the YAML schema for the run config.
        TEMPLATE_PATH: class attribute containing the path to the default Jinja2 run
            config template file.
        epoch_based: boolean indicating if the original run config inputs were provided
            with user-defined epochs.

    Raises:
        PipelineConfigError: the input YAML config violates the schema.
    """
    # key: config input type, value: boolean indicating if it is required
    _REQUIRED_INPUT_TYPES: Dict[str, bool] = {
        "image": True,
        "selavy": True,
        "noise": True,
        "background": False,
    }
    # inputs may be optional, all inputs will be either a unique list or a mapping to a unique list
    _SCHEMA_INPUTS = {
        (k if v else yaml.Optional(k)): yaml.MapPattern(
            yaml.Str(), yaml.UniqueSeq(yaml.Str())
        )
        | yaml.UniqueSeq(yaml.Str())
        for k, v in _REQUIRED_INPUT_TYPES.items()
    }
    _VALID_ASSOC_METHODS: List[str] = ["basic", "advanced", "deruiter"]
    SCHEMA = yaml.Map(
        {
            "run": yaml.Map(
                {
                    "path": yaml.Str(),
                    "default_survey": yaml.Str(),
                    "suppress_astropy_warnings": yaml.Bool(),
                }
            ),
            "inputs": yaml.Map(_SCHEMA_INPUTS),
            "source_monitoring": yaml.Map(
                {
                    "monitor": yaml.Bool(),
                    "min_sigma": yaml.Float(),
                    "edge_buffer_scale": yaml.Float(),
                    "cluster_threshold": yaml.Float(),
                    "allow_nan": yaml.Bool(),
                }
            ),
            "source_association": yaml.Map(
                {
                    "method": yaml.Enum(_VALID_ASSOC_METHODS),
                    "radius": yaml.Float(),
                    "deruiter_radius": yaml.Float(),
                    "deruiter_beamwidth_limit": yaml.Float(),
                    "parallel": yaml.Bool(),
                    "epoch_duplicate_radius": yaml.Float(),
                }
            ),
            "new_sources": yaml.Map(
                {
                    "min_sigma": yaml.Float(),
                }
            ),
            "measurements": yaml.Map(
                {
                    "source_finder": yaml.Enum(["selavy"]),
                    "flux_fractional_error": yaml.Float(),
                    "condon_errors": yaml.Bool(),
                    "selavy_local_rms_fill_value": yaml.Float(),
                    "write_arrow_files": yaml.Bool(),
                    "ra_uncertainty": yaml.Float(),
                    "dec_uncertainty": yaml.Float(),
                }
            ),
            "variability": yaml.Map(
                {
                    "source_aggregate_pair_metrics_min_abs_vs": yaml.Float(),
                }
            ),
        }
    )
    # path to default run config template
    TEMPLATE_PATH: str = os.path.join(
        settings.BASE_DIR, "vast_pipeline", "config_template.yaml.j2"
    )

    def __init__(self, config_yaml: yaml.YAML):
        """Initialises PipelineConfig with parsed (but not necessarily validated) YAML.

        Args:
            config_yaml (yaml.YAML): Input YAML, usually the output of `strictyaml.load`.

        Raises:
            PipelineConfigError: The input YAML config violates the schema.
        """
        self._yaml: yaml.YAML = config_yaml
        # The epoch_based parameter below is for if the user has entered just lists we
        # don't have access to the dates until the Image instances are created. So we
        # flag this as true so that we can reorder the epochs once the date information
        # is available. It is also recorded in the database such that there is a record
        # of the fact that the run was processed in an epoch based mode.
        self.epoch_based: bool

        # Determine if epoch-based association should be used based on input files.
        # If inputs have been parsed to dicts, then the user has defined their own epochs.
        # If inputs have been parsed to lists, we must convert to dicts and auto-fill
        # the epochs.

        # ensure the inputs are valid in case .from_file(..., validate=False) was used
        try:
            self._yaml["inputs"].revalidate(yaml.Map(self._SCHEMA_INPUTS))
        except yaml.YAMLValidationError as e:
            raise PipelineConfigError(e)
        for input_file_type in self._REQUIRED_INPUT_TYPES:
            if (
                not self._REQUIRED_INPUT_TYPES[input_file_type]
                and input_file_type not in self["inputs"]
            ):
                # skip missing optional input types, e.g. background
                continue
            input_files = self["inputs"][input_file_type]
            if isinstance(input_files, list):
                # Epoch-based association not requested. Replace input lists with dicts
                # where each input file has it's own epoch.
                self.epoch_based = False
                pad_width = len(str(len(input_files)))
                input_files_dict = {
                    f"{i + 1:0{pad_width}}": [val] for i, val in enumerate(input_files)
                }
                self._yaml["inputs"][input_file_type] = input_files_dict
            else:
                # must be a dict
                self.epoch_based = True

    def __getitem__(self, name: str):
        """Retrieves the requested YAML chunk as a native Python object.
        """
        return self._yaml[name].data

    @classmethod
    def from_file(
        cls,
        yaml_path: str,
        label: str = "run config",
        validate: bool = True,
        add_defaults: bool = True,
    ) -> "PipelineConfig":
        """Create a PipelineConfig object from a run configuration YAML file.

        Args:
            yaml_path: Path to the run config YAML file.
        label: A label for the config object that will be used in error messages.
            Default is "run config".
        validate: Perform config schema validation immediately after loading the config
            file. If set to False, the full schema validation will not be performed
            until PipelineConfig.validate() is explicitly called. The inputs are always
            validated regardless. Defaults to True.
        add_defaults: Add missing configuration parameters using configured defaults.
            The defaults are read from the Django settings file. Defaults to True.

        Raises:
            PipelineConfigError: The run config YAML file fails schema validation.

        """
        schema = PipelineConfig.SCHEMA if validate else yaml.Any()
        with open(yaml_path) as fh:
            config_str = fh.read()
        try:
            config_yaml = yaml.load(config_str, schema=schema, label=label)
        except yaml.YAMLValidationError as e:
            raise PipelineConfigError(e)

        if add_defaults:
            # make a template config based on defaults
            config_defaults_str = make_config_template(
                cls.TEMPLATE_PATH,
                **settings.PIPE_RUN_CONFIG_DEFAULTS,
            )
            config_defaults_dict: Dict[str, Any] = yaml.load(config_defaults_str).data

            # merge configs
            config_dict = dict_merge(config_defaults_dict, config_yaml.data)
            config_yaml = yaml.as_document(config_dict, schema=schema, label=label)
        return cls(config_yaml)

    def validate(self, user: User = None):
        """Perform extra validation steps not covered by the default schema validation.
        The following checks are performed in order. If a check fails, an exception is
        raised and no further checks are performed.

        1. All input files have the same number of epochs and the same number of files
            per epoch.
        2. The number of input files does not exceed the configured pipeline maximum.
            This is only enforced if a regular user (not staff/admin) created the run.
        3. There are at least two input images.
        4. Background input images are required is source monitoring is turned on.
        5. All input files exist.

        Args:
            user: Optional. The User of the request if made through the UI. Defaults to
                None.

        Raises:
            PipelineConfigError: a validation check failed.
        """
        # run standard base schema validation
        try:
            self._yaml.revalidate(self.SCHEMA)
        except yaml.YAMLValidationError as e:
            raise PipelineConfigError(e)

        epochs = self["inputs"]["image"].keys()
        epoch_n_files = {
            epoch: len(files) for epoch, files in self["inputs"]["image"].items()
        }
        n_files = sum([n for n in epoch_n_files.values()])

        # Ensure all input file types have the same number of epochs and the same number
        # of files per epoch. Note by this point the input files have been converted to
        # a mapping regardless of the user's input format.
        try:
            for input_type in self["inputs"].keys():
                self._yaml["inputs"][input_type].revalidate(
                    yaml.Map(
                        {
                            epoch: yaml.FixedSeq(
                                [yaml.Str() for _ in range(epoch_n_files[epoch])]
                            )
                            for epoch in epochs
                        }
                    )
                )
        except yaml.YAMLValidationError as e:
            raise PipelineConfigError(e)

        # ensure the number of input files is less than the user limit
        if user and n_files > settings.MAX_PIPERUN_IMAGES:
            if user.is_staff:
                logger.warning(
                    "Maximum number of images"
                    f" ({settings.MAX_PIPERUN_IMAGES}) rule bypassed with"
                    " admin status."
                )
            else:
                raise PipelineConfigError(
                    f"The number of images entered ({n_files})"
                    " exceeds the maximum number of images currently"
                    f" allowed ({settings.MAX_PIPERUN_IMAGES}). Please ask"
                    " an administrator for advice on processing your run."
                )

        # ensure at least two inputs are provided
        if n_files < 2:
            raise PipelineConfigError(
                "Number of image files needs to be larger than 1!"
            )

        # ensure background files are provided if source monitoring is requested
        if self["source_monitoring"]["monitor"]:
            inputs_schema = yaml.Map(
                {
                    k: yaml.UniqueSeq(yaml.Str())
                    | yaml.MapPattern(yaml.Str(), yaml.UniqueSeq(yaml.Str()))
                    for k in self._REQUIRED_INPUT_TYPES
                }
            )
            try:
                self._yaml["inputs"].revalidate(inputs_schema)
            except yaml.YAMLValidationError as e:
                raise PipelineConfigError(e)

        # ensure the input files all exist
        for input_type in self["inputs"].keys():
            for file_list in self["inputs"][input_type].values():
                for file in file_list:
                    if not os.path.exists(file):
                        raise PipelineConfigError(f"{file} does not exist.")

    def check_prev_config_diff(self) -> bool:
        """
        Checks if the previous config file differs from the current config file. Used in
        add mode. Only returns true if the images are different and the other general
        settings are the same (the requirement for add mode). Otherwise False is returned.

        Returns:
            True if images are different but general settings are the same, otherwise
            False is returned.
        """
        prev_config = PipelineConfig.from_file(
            os.path.join(self["run"]["path"], "config_prev.yaml"),
            label="previous run config",
        )
        if self._yaml == prev_config._yaml:
            return True

        # are the input image files different?
        images_changed = self["inputs"]["image"] != prev_config["inputs"]["image"]

        # are all the non-input file configs the same?
        config_dict = self._yaml.data
        prev_config_dict = prev_config._yaml.data
        _ = config_dict.pop("inputs")
        _ = prev_config_dict.pop("inputs")
        settings_check = config_dict == prev_config_dict

        if images_changed and settings_check:
            return False
        return True
