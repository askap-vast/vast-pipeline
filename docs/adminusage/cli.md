# Command Line Interface (CLI)

This section describes the commands available to the administrators of the pipelines.

## Pipeline Usage

All the pipeline commands are run using the Django global `./manage.py <command>` interface. Therefore you need to activate the `Python` environment. You can have a look at the available commands for the pipeline app:

```terminal
(pipeline_env)$ ./manage.py help
```

Output:

```terminal
 ...

[vast_pipeline]
  clearpiperun
  createmeasarrow
  debugrun
  initpiperun
  restorepiperun
  runpipeline

 ...
```

There are 6 commands, described in detail below.

### clearpiperun

Resetting a pipeline run can be done using the `clearpiperun` command. This will delete all images and related objects such as sources associated with that pipeline run. Images that have been used in other pipeline runs will not be deleted.

```terminal
./manage.py clearpiperun --help
usage: manage.py clearpiperun [-h] [--keep-parquet] [--remove-all] [--version]
                              [-v {0,1,2,3}] [--settings SETTINGS]
                              [--pythonpath PYTHONPATH] [--traceback]
                              [--no-color] [--force-color] [--skip-checks]
                              piperuns [piperuns ...]

Delete a pipeline run and all related images, sources, etc. Will not delete
objects if they are also related to another pipeline run.

positional arguments:
  piperuns              Name or path of pipeline run(s) to delete. Pass
                        "clearall" to delete all the runs.

optional arguments:
  -h, --help            show this help message and exit
  --keep-parquet        Flag to keep the pipeline run(s) parquet files. Will
                        also apply to arrow files if present.
  --remove-all          Flag to remove all the content of the pipeline run(s)
                        folder.
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

Example usage:

```terminal
(pipeline_env)$ ./manage.py clearpiperun path/to/my_pipe_run
# or
(pipeline_env)$ ./manage.py clearpiperun my_pipe_run
```

!!!tip
    Further information on clearing a specific run, or resetting the database, can be found in the [Contributing and Developing](../developing/localdevenv.md#removingclearing-data) section.

### createmeasarrow

This command allows for the creation of the `measurements.arrow` and `measurement_pairs.arrow` files after a run has been successfully completed. See [Arrow Files](../outputs/outputs.md#arrow-files) for more information.

```terminal
./manage.py createmeasarrow --help
usage: manage.py createmeasarrow [-h] [--overwrite] [--version] [-v {0,1,2,3}]
                                 [--settings SETTINGS]
                                 [--pythonpath PYTHONPATH] [--traceback]
                                 [--no-color] [--force-color] [--skip-checks]
                                 piperun

Create `measurements.arrow` and `measurement_pairs.arrow` files for a
completed pipeline run.

positional arguments:
  piperun               Path or name of the pipeline run.

optional arguments:
  -h, --help            show this help message and exit
  --overwrite           Overwrite previous 'measurements.arrow' file.
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
  --force-color         Force colorization of the co
```

Example usage:

```terminal
./manage.py createmeasarrow docs_example_run
2021-03-30 10:48:40,952 createmeasarrow INFO Creating measurements arrow file for 'docs_example_run'.
2021-03-30 10:48:40,952 utils INFO Creating measurements.arrow for run docs_example_run.
2021-03-30 10:48:41,829 createmeasarrow INFO Creating measurement pairs arrow file for 'docs_example_run'.
2021-03-30 10:48:41,829 utils INFO Creating measurement_pairs.arrow for run docs_example_run.
```

### debugrun

The `debugrun` command is used to print out a summary of the pipeline run to the terminal. A single pipeline run can be entered as an argument or `all` can be
entered to print the statistics of all the pipeline runs in the database.

```terminal
./manage.py debugrun --help
usage: manage.py debugrun [-h] [--version] [-v {0,1,2,3}]
                          [--settings SETTINGS] [--pythonpath PYTHONPATH]
                          [--traceback] [--no-color] [--force-color]
                          [--skip-checks]
                          piperuns [piperuns ...]

Print out total metrics such as nr of measurements for runs

positional arguments:
  piperuns              Name or path of pipeline run(s) to debug.Pass "all" to
                        print summary data of all the runs.

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

Example usage:

```terminal
./manage.py debugrun docs_example_run
* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
Printing summary data of pipeline run "docs_example_run"
Nr of images: 14
Nr of measurements: 4312
Nr of forced measurements: 2156
Nr of sources: 557
Nr of association: 3276
* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
```

### initpiperun

In order to process the images in the pipeline, you must create/initialise a pipeline run first.

The pipeline run creation is done using the `initpiperun` django command, which requires a pipeline run folder. The command creates a folder with the pipeline run name under the settings `PROJECT_WORKING_DIR` defined in [settings](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/settings.template.py){:target="_blank"}.

```terminal
(pipeline_env)$ ./manage.py initpiperun --help
```

Output:

```terminal
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

```terminal
(pipeline_env)$ ./manage.py initpiperun my_pipe_run
```

Output:

```terminal
2020-02-27 23:04:33,344 initpiperun INFO creating pipeline run folder
2020-02-27 23:04:33,344 initpiperun INFO copying default config in pipeline run folder
2020-02-27 23:04:33,344 initpiperun INFO pipeline run initialisation successful! Please modify the "config.yaml"
```

### restorepiperun

Details on the add images feature can be found [here](../using/addtorun.md).

It allows for a pipeline run that has had an image added to the run to be restored to the state it was in before the image addition was made. By default the command will ask for confirmation that the run is to be restored (the option `--no-confirm` skips this).

```terminal
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

```terminal
(pipeline_env)$ ./manage.py restorepiperun path/to/my_pipe_run
# or
(pipeline_env)$ ./manage.py restorepiperun my_pipe_run
```

Example usage:

```console
(pipeline_env)$ ./manage.py restorepiperun docs_example_run
2021-04-02 21:24:20,497 restorepiperun INFO Will restore the run to the following config:
run:
  path: /Users/obrienan/sandbox/vast-pipeline-dirs/pipeline-runs/docs_example_run
  suppress_astropy_warnings: yes
inputs:
  image:
    1:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout.fits
    2:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout.fits
    3:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout.fits
    4:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout.fits
    5:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout.fits
    6:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout.fits
    7:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout.fits
  selavy:
    1:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout.components.txt
    2:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout.components.txt
    3:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout.components.txt
    4:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout.components.txt
    5:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout.components.txt
    6:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout.components.txt
    7:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout.components.txt
  noise:
    1:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_0127-73A.EPOCH01.I.cutout_rms.fits
    2:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_2118+00A.EPOCH01.I.cutout_rms.fits
    3:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH01/VAST_2118-06A.EPOCH01.I.cutout_rms.fits
    4:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH02/VAST_2118+00A.EPOCH02.I.cutout_rms.fits
    5:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH02/VAST_2118-06A.EPOCH02.I.cutout_rms.fits
    6:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH03x/VAST_2118+00A.EPOCH03x.I.cutout_rms.fits
    7:
    - /Users/obrienan/sandbox/vast-pipeline-dirs/raw-images/regression-data/EPOCH03x/VAST_2118-06A.EPOCH03x.I.cutout_rms.fits
source_monitoring:
  monitor: no
  min_sigma: 3.0
  edge_buffer_scale: 1.2
  cluster_threshold: 3.0
  allow_nan: no
source_association:
  method: basic
  radius: 10.0
  deruiter_radius: 5.68
  deruiter_beamwidth_limit: 1.5
  parallel: no
  epoch_duplicate_radius: 2.5
new_sources:
  min_sigma: 5.0
measurements:
  source_finder: selavy
  flux_fractional_error: 0.0
  condon_errors: yes
  selavy_local_rms_fill_value: 0.2
  write_arrow_files: no
  ra_uncertainty: 1.0
  dec_uncertainty: 1.0
variability:
  source_aggregate_pair_metrics_min_abs_vs: 4.3

Would you like to restore the run ? (y/n): y
2021-04-02 21:24:28,685 restorepiperun INFO Restoring 'docs_example_run' from backup parquet files.
2021-04-02 21:24:29,602 restorepiperun INFO Deleting new sources and associated objects to restore run Total objects deleted: 433
2021-04-02 21:24:29,624 restorepiperun INFO Restoring metrics for 461 sources.
2021-04-02 21:24:29,663 restorepiperun INFO Removing 7 images from the run.
2021-04-02 21:24:29,754 restorepiperun INFO Deleting associations to restore run. Total objects deleted: 846
2021-04-02 21:24:29,979 restorepiperun INFO Deleting measurement pairs to restore run. Total objects deleted: 4212
2021-04-02 21:24:29,981 restorepiperun INFO Restoring run metrics.
2021-04-02 21:24:29,990 restorepiperun INFO Restoring parquet files and removing .bak files.
2021-04-02 21:24:29,995 restorepiperun INFO Restore complete.
```

### runpipeline

The pipeline is run using `runpipeline` django command.

```terminal
(pipeline_env)$ ./manage.py runpipeline --help
```

Output:

```terminal
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

```terminal
(pipeline_env)$ ./manage.py runpipeline path/to/my_pipe_run
```
