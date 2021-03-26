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
  runpipeline

 ...
```

There are 4 commands, described in detail below.

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

### Import survey data

This functionality is still not developed
