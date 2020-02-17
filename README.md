# VAST Pipeline Prototype
This repository holds the code of the Radio Transient detection pipeline for the VAST project.

Installation instructions are described in [`INSTALL.md`](./INSTALL.md).

If you intend to contribute to the code base please read and follow the guidelines in [`DEVELOPING.md`](./DEVELOPING.md).

## Table of Contents

- [Pipeline Configuration](##pipeline-configuration)
- [Pipeline Usage](##pipeline-usage)
	- [Initialise a Dataset](###initialise-a-dataset)
	- [Run the Pipeline](###run-the-pipeline)
	- [Resetting a Dataset](###resetting-a-dataset)
	- [Import survey data](###import-survey-data)
- [Data Exploration via Django Web Server](##data-exploration-via-django-web-server)

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

3. Create the database user, database name and enabling the `Q3C` extension, by running:

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
creating db 'vastdb', enable Q3C plugin
CREATE EXTENSION
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
  cleardataset
  importsurvey
  initdataset
  runpipeline

 ...
```

There are 4 commands, described in detail below.

### Initialise a dataset
In order to process the images in the pipeline, you must create/initialise a dataset first.

The dataset creation is run using `initdataset` django command, which requires a dataset folder. The command creates a folder with the dataset name under the settings
`PROJECT_WORKING_DIR` defined in [settings](./webinterface/settings.template.py).

```bash
(pipeline_env)$: ./manage.py initdataset --help
```

Output:

```bash
usage: manage.py initdataset [-h] [--version] [-v {0,1,2,3}]
                             [--settings SETTINGS] [--pythonpath PYTHONPATH]
                             [--traceback] [--no-color] [--force-color]
                             dataset_folder_path

Create the dataset folder structure to run a pipeline instance

positional arguments:
  dataset_folder_path   path to the dataset folder

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
(pipeline_env)$: ./manage.py initdataset my_dataset
```

Output:

```bash
2020-02-17 00:56:50,818 initdataset INFO creating dataset folder
2020-02-17 00:56:50,818 initdataset INFO copying default config in dataset folder
2020-02-17 00:56:50,819 initdataset INFO Dataset initialisation successful! Please modify the "config.py"

```

### Run the Pipeline
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
(pipeline_env)$: ./manage.py runpipeline path/to/my_dataset
```

### Resetting a Dataset

Detailed commands for resetting the database can be found in [`DEVELOPING.md`](./DEVELOPING.md).

Resetting a dataset (i.e. a pipeline run) can be done using the `cleardataset` command: it will delete all images (and related objects such as sources) associated with that dataset, if that images does not belong to another dataset. It will deleted all the catalogs associated with that dataset.
```bash
(pipeline_env)$: ./manage.py cleardataset my_dataset
```

### Import survey data

This command is optional but recommended. TBC


## Data Exploration via Django Web Server

1. Start the Django development web server:

```bash
(pipeline_env)$: ./manage.py runserver
```

2. Test the webserver by pointing your browser at http://127.0.0.1:8000

The webserver is independent of `runpipeline` and you can use the website while the pipeline commands are running.
