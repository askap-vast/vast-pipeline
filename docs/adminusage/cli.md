# Command Line Interface (CLI)

This section describes the commands available to the administrators of the pipelines.

## Pipeline Usage
All the pipeline commands are run using the Django global `./manage.py <command>` interface. Therefore you need to activate the `Python` environment. You can have a look at the available commands for the pipeline app:

```bash
(pipeline_env)$ ./manage.py help
```

Output:

```bash
 ...

[vast_pipeline]
  clearpiperun
  createmeasarrow
  debugrun
  importsurvey
  initpiperun
  restorepiperun
  runpipeline

 ...
```

There are 5 commands, described in detail below.

### Initialise a Pipeline Run
In order to process the images in the pipeline, you must create/initialise a pipeline run first.

The pipeline run creation is done using the `initpiperun` django command, which requires a pipeline run folder. The command creates a folder with the pipeline run name under the settings `PROJECT_WORKING_DIR` defined in [settings](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/settings.template.py){:target="_blank"}.

```bash
(pipeline_env)$ ./manage.py initpiperun --help
```

Output:

```bash
usage: manage.py initpiperun [-h] [--version] [-v {0,1,2,3}]
                             [--settings SETTINGS] [--pythonpath PYTHONPATH]
                             [--traceback] [--no-color] [--force-color]
                             runname

Create the pipeline run folder structure to run a pipeline instance

positional arguments:
  runname       Name of the pipeline run.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --force-color         Force colorization of the command output.
```

The command yields the following folder structure:

```bash
(pipeline_env)$ ./manage.py initpiperun my_pipe_run
```

Output:

```bash
2020-02-27 23:04:33,344 initpiperun INFO creating pipeline run folder
2020-02-27 23:04:33,344 initpiperun INFO copying default config in pipeline run folder
2020-02-27 23:04:33,344 initpiperun INFO pipeline run initialisation successful! Please modify the "config.py"
```

### Run a Pipeline Instance
The pipeline is run using `runpipeline` django command.

```bash
(pipeline_env)$ ./manage.py runpipeline --help
```

Output:
```bash
usage: manage.py runpipeline [-h] [--version] [-v {0,1,2,3}]
                             [--settings SETTINGS] [--pythonpath PYTHONPATH]
                             [--traceback] [--no-color] [--force-color]
                             [--skip-checks]
                             piperun

Process the pipeline for a list of images and Selavy catalogs

positional arguments:
  piperun       Path or name of the pipeline run.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --force-color         Force colorization of the command output.
  --skip-checks         Skip system checks.
```

General usage:
```bash
(pipeline_env)$ ./manage.py runpipeline path/to/my_pipe_run
```

### Resetting a Pipeline Run

Detailed commands for resetting the database can be found in [Contributing and Developing Guidelines](../developing/localdevenv.md#reset-the-database).

Resetting a pipeline run can be done using the `clearpiperun` command: it will delete all images (and related objects such as sources) associated with that pipeline run, if that images does not belong to another pipeline run. It will deleted all the sources associated with that pipeline run.
```bash
(pipeline_env)$ ./manage.py clearpiperun path/to/my_pipe_run
# or
(pipeline_env)$ ./manage.py clearpiperun my_pipe_run
```

More details on the `clearpiperun` command can be found in the [Contributing and Developing Guidelines](../developing/localdevenv.md#clearing-run-data).

### Restoring a Pipeline Run

Details on the add images feature can be found [here](../using/addtorun.md).

It allows for a pipeline run that has had an image added to the run to be restored to the state it was in before the image addition was made. By default the command will ask for confirmation that the run is to be restored (the option `--no-confirm` skips this).

```bash
./manage.py restorepiperun --help
usage: manage.py restorepiperun [-h] [--no-confirm] [--version] [-v {0,1,2,3}]
                                [--settings SETTINGS]
                                [--pythonpath PYTHONPATH] [--traceback]
                                [--no-color] [--force-color] [--skip-checks]
                                piperuns [piperuns ...]

Restore a pipeline run to the previous person after image add mode has been
used.

positional arguments:
  piperuns              Name or path of pipeline run(s) to restore.

optional arguments:
  -h, --help            show this help message and exit
  --no-confirm          Flag to skip the confirmation stage and proceed to
                        restore the pipeline run.
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --force-color         Force colorization of the command output.
  --skip-checks         Skip system checks.
```

```bash
(pipeline_env)$ ./manage.py restorepiperun path/to/my_pipe_run
# or
(pipeline_env)$ ./manage.py restorepiperun my_pipe_run
```

Example usage:
```bash
./manage.py restorepiperun docs_example_run
2021-01-31 12:45:31,039 restorepiperun INFO Will restore the run to the following config:
PIPE_RUN_PATH...................................../Users/adam/GitHub/vast-pipeline/pipeline-runs/docs_example_run
IMAGE_FILES.......................................['/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout.fits', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout.fits', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout.fits', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout.fits', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout.fits', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout.fits', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout.fits']
SELAVY_FILES......................................['/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout.components.txt', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout.components.txt', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout.components.txt', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout.components.txt', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout.components.txt', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout.components.txt', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout.components.txt']
BACKGROUND_FILES..................................['/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout_bkg.fits', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout_bkg.fits', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout_bkg.fits', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout_bkg.fits', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout_bkg.fits', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout_bkg.fits', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout_bkg.fits']
NOISE_FILES.......................................['/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout_rms.fits', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout_rms.fits', '/Users/adam/askap/pipeline-test-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout_rms.fits', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout_rms.fits', '/Users/adam/askap/pipeline-test-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout_rms.fits', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout_rms.fits', '/Users/adam/askap/pipeline-test-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout_rms.fits']
SOURCE_FINDER.....................................selavy
MONITOR...........................................True
MONITOR_MIN_SIGMA.................................3.0
MONITOR_EDGE_BUFFER_SCALE.........................1.2
MONITOR_CLUSTER_THRESHOLD.........................3.0
MONITOR_ALLOW_NAN.................................False
ASTROMETRIC_UNCERTAINTY_RA........................1
ASTROMETRIC_UNCERTAINTY_DEC.......................1
ASSOCIATION_PARALLEL..............................True
ASSOCIATION_EPOCH_DUPLICATE_RADIUS................2.5
ASSOCIATION_METHOD................................basic
ASSOCIATION_RADIUS................................15.0
ASSOCIATION_DE_RUITER_RADIUS......................5.68
ASSOCIATION_BEAMWIDTH_LIMIT.......................1.5
NEW_SOURCE_MIN_SIGMA..............................5.0
DEFAULT_SURVEY....................................None
FLUX_PERC_ERROR...................................0
USE_CONDON_ERRORS.................................True
SELAVY_LOCAL_RMS_ZERO_FILL_VALUE..................0.2
CREATE_MEASUREMENTS_ARROW_FILES...................False
SUPPRESS_ASTROPY_WARNINGS.........................True
SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS..........4.3
Would you like to restore the run ? (y/n): y
2021-01-31 12:45:38,567 restorepiperun INFO Restoring 'docs_example_run' from backup parquet files.
2021-01-31 12:45:39,216 restorepiperun INFO Deleting new sources and associated objects to restore run Total objects deleted: 2475
2021-01-31 12:45:39,532 restorepiperun INFO Deleting forced measurement and associated objects to restore run. Total objects deleted: 3769
2021-01-31 12:45:39,576 restorepiperun INFO Restoring metrics for 459 sources.
2021-01-31 12:45:39,631 restorepiperun INFO Removing 7 images from the run.
2021-01-31 12:45:39,826 restorepiperun INFO Deleting associations to restore run. Total objects deleted: 3239
2021-01-31 12:45:40,651 restorepiperun INFO Deleting measurement pairs to restore run. Total objects deleted: 14692
2021-01-31 12:45:40,653 restorepiperun INFO Restoring run metrics.
2021-01-31 12:45:40,662 restorepiperun INFO Restoring parquet files and removing .bak files.
2021-01-31 12:45:40,669 restorepiperun INFO Restore complete.
```

### Import survey data

This functionality is still not developed
