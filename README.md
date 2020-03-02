# VAST Pipeline Prototype
This repository holds the code of the Radio Transient detection pipeline for the VAST project.

Installation instructions are described in [`INSTALL.md`](./INSTALL.md).

If you intend to contribute to the code base please read and follow the guidelines in [`DEVELOPING.md`](./DEVELOPING.md).

## Table of Contents

- [Pipeline Configuration](#pipeline-configuration)
- [Pipeline Usage](#pipeline-usage)
	- [Initialise a Pipeline Run](#initialise-a-pipeline-run)
	- [Run a Pipeline Instance](#run-the-pipeline)
	- [Resetting a Pipeline Run](#resetting-a-pipeline-run)
	- [Import survey data](#import-survey-data)
- [Data Exploration via Django Web Server](#data-exploration-via-django-web-server)

## Pipeline Configuration
The following instructions, will get you started in setting up the database and pipeline configuration
1. Copy the settings template

```bash
cp webinterface/settings.template.py webinterface/settings.py
```

2. Choose a database name and user with password (e.g. database name: `vastdb`; user: `vast`, psw: `vastpsw`), and add the connection details in `settings.py`

```Python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'vastdb',
        'USER': 'vast',
        'PASSWORD': 'vastpsw',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

NOTE: the connection details (host and port) are the same that you setup in [`INSTALL.md`](./INSTALL.md). The database/user names must not contain any spaces or dashes, so use the underscore if you want, e.g. `this_is_my_db_name`.

3. Create the database user and database name, by running:

```bash
$:./init-tools/init-db.sh localhost 5432 postgres postgres vast vastpsw vastdb
```

  For help on the command run it without arguments

```bash
$:./init-tools/init-db.sh
Usage: init-db.sh HOST PORT ADMINUSER ADMINPSW USER USERPSW DBNAME
Eg:    init-db.sh localhost 5432 postgres postgres vast vastpsw vastdb

Help: This will create a postgresql user 'vast' with login password 'vastpsw'
      and a database 'vastdb' and grant to 'vast' user all the privileges to 'vastdb'
```

  If everything went well the output is:

```bash
connecting to PostgreSQL on 'localhost:5433' as admin 'postgres'
creating user 'vast' with login password 'vastpsw' and give it createdb privileges
CREATE ROLE
************************************
creating db 'vastdb'
```

4. Create the database tables. Remember first to activate the Python environment as described in [`INSTALL.md`](./INSTALL.md).

```bash
(pipeline_env)$:./manage.py migrate
```

5. Create the directories listed at the bottom of `settings.py`

```Python
# reference surveys default folder
PROJECT_WORKING_DIR = os.path.join(BASE_DIR, 'pipeline-projects')

# reference surveys default folder
SURVEYS_WORKING_DIR = os.path.join(BASE_DIR, 'reference-surveys')
```

Create the folders with (Note: make sure you change BASE_DIR to vast-pipeline or whatever folder you clone the repo in):

```bash
cd BASE_DIR && mkdir pipeline-projects && mkdir reference-surveys
```

After creating the folders your directory tree should look like this:

```bash
vast-pipeline/
├── init-tools
├── pipeline
├── reference-surveys
├── requirements
├── static
├── templates
├── pipeline-projects
├── webinterface
├── DEVELOPING.md
├── INSTALL.md
├── manage.py
└── README.md
```

## Pipeline Usage
All the pipeline commands are run using the Django global `./manage.py <command>` interface. Therefore you need to activate the `Python` environment. You can have a look at the available commands for the pipeline app:

```bash
(pipeline_env)$: ./manage.py help
```

Output:

```bash
 ...

[pipeline]
  clearpiperun
  importsurvey
  initpiperun
  runpipeline

 ...
```

There are 4 commands, described in detail below.

### Initialise a Pipeline Run
In order to process the images in the pipeline, you must create/initialise a pipeline run first.

The pipeline run creation is done using the `initpiperun` django command, which requires a pipeline run folder. The command creates a folder with the pipeline run name under the settings `PROJECT_WORKING_DIR` defined in [settings](./webinterface/settings.template.py).

```bash
(pipeline_env)$: ./manage.py initpiperun --help
```

Output:

```bash
usage: manage.py initpiperun [-h] [--version] [-v {0,1,2,3}]
                             [--settings SETTINGS] [--pythonpath PYTHONPATH]
                             [--traceback] [--no-color] [--force-color]
                             run_folder_path

Create the pipeline run folder structure to run a pipeline instance

positional arguments:
  run_folder_path       path to the pipeline run folder

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
(pipeline_env)$: ./manage.py initpiperun my_pipe_run
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
(pipeline_env)$: ./manage.py runpipeline --help
```

Output:
```bash
TBC
```

General usage:
```bash
(pipeline_env)$: ./manage.py runpipeline path/to/my_pipe_run
```

### Resetting a Pipeline Run

Detailed commands for resetting the database can be found in [`DEVELOPING.md`](./DEVELOPING.md).

Resetting a pipeline run can be done using the `clearpiperun` command: it will delete all images (and related objects such as sources) associated with that pipeline run, if that images does not belong to another pipeline run. It will deleted all the sources associated with that pipeline run.
```bash
(pipeline_env)$: ./manage.py clearpiperun my_pipe_run
```

### Import survey data

TBC


## Data Exploration via Django Web Server

1. Start the Django development web server:

```bash
(pipeline_env)$: ./manage.py runserver
```

2. Test the webserver by pointing your browser at http://127.0.0.1:8000

The webserver is independent of `runpipeline` and you can use the website while the pipeline commands are running.
