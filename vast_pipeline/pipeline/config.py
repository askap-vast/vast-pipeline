from glob import glob
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
    # Inputs may be optional. All inputs will be either a unique list or a mapping (epoch
    # mode and/or glob expressions). These possibilities cannot be validated at once, so
    # it will accept Any and then revalidate later.
    _SCHEMA_INPUTS = {
        (k if v else yaml.Optional(k)): yaml.MapPattern(yaml.Str(), yaml.Any())
        | yaml.UniqueSeq(yaml.Str())
        for k, v in _REQUIRED_INPUT_TYPES.items()
    }
    _SCHEMA_GLOB_INPUTS = {"glob": yaml.Str() | yaml.Seq(yaml.Str())}
    _VALID_ASSOC_METHODS: List[str] = ["basic", "advanced", "deruiter"]
    SCHEMA = yaml.Map(
        {
            "run": yaml.Map(
                {
                    "path": yaml.Str(),
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
                    "pair_metrics": yaml.Bool(),
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
            self._validate_inputs()
        except yaml.YAMLValidationError as e:
            raise PipelineConfigError(e)

        # detect simple list inputs and convert them to epoch-mode inputs
        for input_file_type in self._REQUIRED_INPUT_TYPES:
            # skip missing optional input types, e.g. background
            if (
                not self._REQUIRED_INPUT_TYPES[input_file_type]
                and input_file_type not in self["inputs"]
            ):
                continue

            input_files = self["inputs"][input_file_type]

            # resolve glob expressions if present
            if isinstance(input_files, dict):
                # must be either a glob expression, list of glob expressions, or epoch-mode
                if "glob" in input_files:
                    # resolve the glob expressions
                    self.epoch_based = False
                    file_list = self._resolve_glob_expressions(
                        self._yaml["inputs"][input_file_type]
                    )
                    self._yaml["inputs"][input_file_type] = self._create_input_epochs(
                        file_list
                    )
                else:
                    # epoch-mode with either a list of files or glob expressions
                    self.epoch_based = True
                    for epoch in input_files:
                        if "glob" in input_files[epoch]:
                            # resolve the glob expressions
                            file_list = self._resolve_glob_expressions(
                                self._yaml["inputs"][input_file_type][epoch]
                            )
                            self._yaml["inputs"][input_file_type][epoch] = file_list
            else:
                # Epoch-based association not requested and no globs present. Replace
                # input lists with dicts where each input file has it's own epoch.
                self.epoch_based = False
                self._yaml["inputs"][input_file_type] = self._create_input_epochs(
                    input_files
                )

    def __getitem__(self, name: str):
        """Retrieves the requested YAML chunk as a native Python object."""
        return self._yaml[name].data

    @staticmethod
    def _create_input_epochs(input_files: List[str]) -> Dict[str, List[str]]:
        """Convert a list of input files into a dict where each list element is placed
        into its own list of length 1 and mapped to by a unique key, a string that is a
        0-padded integer. For example, ["A", "B", "C", ..., "Z"] would be converted to
        {
            "01": ["A"],
            "02": ["B"],
            "03": ["C"],
            ...
            "26": ["Z"],
        }
        The keys are 0-padded to ensure the strings are sortable regardless of the
        length of `input_files`.
        This conversion is required for run configs that are not defined in "epoch mode"
        as after config validation, the pipeline assumes that there will be defined
        epochs.

        Args:
            input_files: the list of input file paths.

        Returns:
            The input file paths mapped to by unique epoch keys.
        """
        pad_width = len(str(len(input_files)))
        input_files_dict = {
            f"{i + 1:0{pad_width}}": [val] for i, val in enumerate(input_files)
        }
        return input_files_dict

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
            validate: Perform config schema validation immediately after loading
                the config file. If set to False, the full schema validation
                will not be performed until PipelineConfig.validate() is
                explicitly called. The inputs are always validated regardless.
                Defaults to True.
            add_defaults: Add missing configuration parameters using configured
                defaults. The defaults are read from the Django settings file.
                Defaults to True.

        Raises:
            PipelineConfigError: The run config YAML file fails schema validation.

        """
        schema = cls.SCHEMA if validate else yaml.Any()
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

    @staticmethod
    def _resolve_glob_expressions(input_files: yaml.YAML) -> List[str]:
        """Resolve glob expressions in a YAML chunk, returning a list of sorted file
        paths.

        Args:
            input_files (yaml.YAML): A validated YAML chunk of input files that is a
                mapping of "glob" to either a single glob expression or a sequence of
                glob expressions. e.g.
                ---
                glob: /foo/*.fits
                ---
                or
                ---
                glob:
                - /foo/A/*.fits
                - /foo/B/*.fits
                ---

        Returns:
            The resolved file paths in lexicographical order.
        """
        file_list: List[str] = []
        if input_files["glob"].is_sequence():
            for glob_expr in input_files["glob"]:
                file_list.extend(sorted(list(glob(glob_expr.data))))
        else:
            file_list.extend(sorted(list(glob(input_files["glob"].data))))
        return file_list

    def _validate_inputs(self):
        """Validate the input files. Each input type (i.e. image, selavy, noise,
        background) may be given as one of the following:
            1. A list of files.
            2. A glob expression.
            3. A list of glob expressions.
            4. A mapping of epochs to any of the above.
        Each input type is validated individually. Extra input validation steps, e.g. to
        ensure each input type has the same number of files, are performed in
        `validate()`.

        Raises:
            PipelineConfigError: The run config inputs fail schema validation.
        """
        try:
            # first pass validation
            self._yaml["inputs"].revalidate(yaml.Map(self._SCHEMA_INPUTS))

            for input_type in self._yaml["inputs"]:
                input_yaml = self._yaml["inputs"][input_type]
                if input_yaml.is_mapping():
                    # inputs are either epoch-mode, glob expressions, or both
                    if "glob" in input_yaml:
                        # validate globs
                        input_yaml.revalidate(yaml.Map(self._SCHEMA_GLOB_INPUTS))
                    else:
                        # validate epoch mode which may also contain glob expressions
                        input_yaml.revalidate(
                            yaml.MapPattern(
                                yaml.Str(),
                                yaml.UniqueSeq(yaml.Str())
                                | yaml.Map(self._SCHEMA_GLOB_INPUTS),
                            )
                        )
        except yaml.YAMLValidationError as e:
            raise PipelineConfigError(e)

    def validate(self, user: User = None):
        """Perform extra validation steps not covered by the default schema validation.
        The following checks are performed in order. If a check fails, an exception is
        raised and no further checks are performed.

        1. All input files have the same number of epochs and the same number of files
            per epoch.
        2. The number of input files does not exceed the configured pipeline maximum.
            This is only enforced if a regular user (not staff/admin) created the run.
        3. There are at least two input images.
        4. Background input images are required if source monitoring is turned on.
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

        # epochs defined for images only, used as the reference list of epochs
        epochs_image = self["inputs"]["image"].keys()
        # map input type to a set of epochs
        epochs_by_input_type = {
            input_type: set(self["inputs"][input_type].keys())
            for input_type in self["inputs"].keys()
        }
        # map input type to total number of files from all epochs
        n_files_by_input_type = {}
        for input_type, epochs_set in epochs_by_input_type.items():
            n_files_by_input_type[input_type] = 0
            for epoch in epochs_set:
                n_files_by_input_type[input_type] += len(self["inputs"][input_type][epoch])
        n_files = 0  # total number of input files
        # map input type to a mapping of epoch to file count
        epoch_n_files: Dict[str, Dict[str, int]] = {}
        for input_type in self["inputs"].keys():
            epoch_n_files[input_type] = {}
            for epoch in self["inputs"][input_type].keys():
                n = len(self["inputs"][input_type][epoch])
                epoch_n_files[input_type][epoch] = n
                n_files += n

        # Note by this point the input files have been converted to a mapping regardless
        # of the user's input format.
        # Ensure all input file types have the same epochs.
        try:
            for input_type in self["inputs"].keys():
                self._yaml["inputs"][input_type].revalidate(
                    yaml.Map({epoch: yaml.Seq(yaml.Str()) for epoch in epochs_image})
                )
        except yaml.YAMLValidationError:
            # number of epochs could be different or the name of the epochs may not match
            # find out which by counting the number of unique epochs per input type
            n_epochs_per_input_type = [
                len(epochs_set) for epochs_set in epochs_by_input_type.values()
            ]
            if len(set(n_epochs_per_input_type)) > 1:
                if self.epoch_based:
                    error_msg = "The number of epochs must match for all input types.\n"
                else:
                    error_msg = "The number of files must match for all input types.\n"
            else:
                error_msg = "The name of the epochs must match for all input types.\n"
            counts_str = ""
            if self.epoch_based:
                for input_type in epoch_n_files.keys():
                    n = len(epoch_n_files[input_type])
                    counts_str += (
                        f"{input_type} has {n} epoch{'s' if n > 1 else ''}:"
                        f" {', '.join(epoch_n_files[input_type].keys())}\n"
                    )
            else:
                for input_type, n in n_files_by_input_type.items():
                    counts_str += f"{input_type} has {n} file{'s' if n > 1 else ''}\n"

            counts_str = counts_str[:-1]
            raise PipelineConfigError(error_msg + counts_str)

        # Ensure all input file type epochs have the same number of files per epoch.
        # This could be combined with the number of epochs validation above, but we want
        # to give specific feedback to the user on failure.
        try:
            for input_type in self["inputs"].keys():
                self._yaml["inputs"][input_type].revalidate(
                    yaml.Map(
                        {
                            epoch: yaml.FixedSeq(
                                [
                                    yaml.Str()
                                    for _ in range(epoch_n_files["image"][epoch])
                                ]
                            )
                            for epoch in epochs_image
                        }
                    )
                )
        except yaml.YAMLValidationError:
            # map input type to a mapping of epoch to file count
            file_counts_str = ""
            for input_type in self["inputs"].keys():
                file_counts_str += f"{input_type}:\n"
                for epoch in sorted(self["inputs"][input_type].keys()):
                    file_counts_str += (
                        f"  {epoch}: {len(self['inputs'][input_type][epoch])}\n"
                    )
            file_counts_str = file_counts_str[:-1]
            raise PipelineConfigError(
                "The number of files per epoch does not match between input types.\n"
                + file_counts_str
            )

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
        check = [n_files_by_input_type[input_type] < 2 for input_type in self["inputs"].keys()]
        if any(check):
            raise PipelineConfigError(
                "Number of image files must to be larger than 1"
            )

        # ensure background files are provided if source monitoring is requested
        try:
            monitor = self["source_monitoring"]["monitor"]
        except KeyError:
            monitor = False

        if monitor:
            inputs_schema = yaml.Map(
                {
                    k: yaml.UniqueSeq(yaml.Str())
                    | yaml.MapPattern(yaml.Str(), yaml.UniqueSeq(yaml.Str()))
                    for k in self._REQUIRED_INPUT_TYPES
                }
            )
            try:
                self._yaml["inputs"].revalidate(inputs_schema)
            except yaml.YAMLValidationError:
                raise PipelineConfigError(
                    "Background files must be provided if source monitoring is enabled."
                )

        # ensure the input files all exist
        for input_type in self["inputs"].keys():
            for epoch, file_list in self["inputs"][input_type].items():
                for file in file_list:
                    if not os.path.exists(file):
                        raise PipelineConfigError(f"{file} does not exist.")

    def check_prev_config_diff(self) -> bool:
        """
        Checks if the previous config file differs from the current config file. Used in
        add mode. Only returns true if the images are different and the other general
        settings are the same (the requirement for add mode). Otherwise False is returned.

        Returns:
            `True` if images are different but general settings are the same,
                otherwise `False` is returned.
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

    def image_opts(self) -> Dict[str, Any]:
        """
        Get the config options required for image ingestion only.
        Namely:
            - selavy_local_rms_fill_value
            - condon_errors
            - ra_uncertainty
            - dec_uncertainty

        Returns:
            The relevant key value pairs
        """
        keys = [
            "selavy_local_rms_fill_value",
            "condon_errors",
            "ra_uncertainty",
            "dec_uncertainty"
        ]
        return {key: self["measurements"][key] for key in keys}


class ImageIngestConfig(PipelineConfig):
    """Image ingest configuration derived from PipelineConfig.

    Attributes:
        SCHEMA: class attribute containing the YAML schema for the image ingest config.
        TEMPLATE_PATH: class attribute containing the path to the default Jinja2 image ingest
            config template file.

    Raises:
        PipelineConfigError: the input YAML config violates the schema.
    """
    # path to default image ingest config template
    TEMPLATE_PATH: str = os.path.join(
        settings.BASE_DIR, "vast_pipeline", "ingest_config_template.yaml.j2"
    )
    _VALID_ASSOC_METHODS = None
    SCHEMA = yaml.Map(
        {
            "inputs": yaml.Map(PipelineConfig._SCHEMA_INPUTS),
            "measurements": yaml.Map(
                {
                    "condon_errors": yaml.Bool(),
                    "selavy_local_rms_fill_value": yaml.Float(),
                    "ra_uncertainty": yaml.Float(),
                    "dec_uncertainty": yaml.Float(),
                }
            ),
        }
    )
