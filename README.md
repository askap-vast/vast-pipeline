# VAST Pipeline
This repository holds the code of the Radio Transient detection pipeline for the VAST project.

Installation instructions are described in [`INSTALL.md`](./INSTALL.md).

If you intend to contribute to/develop the code base please read and follow the guidelines in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Table of Contents

- [Pipeline Configuration](#pipeline-configuration)
- [Pipeline Login](#pipeline-login)
- [Pipeline Usage](#pipeline-usage)
	- [Initialise a Pipeline Run](#initialise-a-pipeline-run)
	- [Run a Pipeline Instance](#run-a-pipeline-instance)
	- [Resetting a Pipeline Run](#resetting-a-pipeline-run)
	- [Import survey data (TBC)](#import-survey-data)
- [Data Exploration via Django Web Server](#data-exploration-via-django-web-server)
- [Production Deployment](#production-deployment)

## Pipeline Configuration
The following instructions, will get you started in setting up the database and pipeline configuration
1. Copy the setting configuration file template, and fill it with your settings (see [defaults](./webinterface/.env.template))

```bash
cp webinterface/.env.template webinterface/.env
```

2. Choose a database name and user with password (e.g. database name: `vastdb`; user: `vast`, psw: `vastpsw`), and add the connection details in `.env` (for URL syntax see [this link](https://django-environ.readthedocs.io/en/latest/#tips))

```cmake
DATABASE_URL=psql://FILLMYUSER:FILLMYPASSWORD@FILLMYHOST:FILLMYPORT/FILLMYDBNAME
```

NOTE: the connection details (host and port) are the same that you setup in [`INSTALL.md`](./INSTALL.md). The database/user names must not contain any spaces or dashes, so use the underscore if you want, e.g. `this_is_my_db_name`.

3. Create the database user and database name, by running:

```bash
$ ./init-tools/init-db.sh localhost 5432 postgres postgres vast vastpsw vastdb
```

  For help on the command run it without arguments

```bash
$ ./init-tools/init-db.sh
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
(pipeline_env)$ ./manage.py migrate
```

5. Create the directories listed at the bottom of `settings.py` and update the details on your setting configuration file `.env` (single name, e.g. `pipeline-runs` means path relative to `BASE_DIR`, so the main folder where you cloned the repo).

```Python
# reference surveys default folder
PIPELINE_WORKING_DIR = env('PIPELINE_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'pipeline-runs'))

# reference surveys default folder
SURVEYS_WORKING_DIR = env('SURVEYS_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'reference-surveys'))
```

The defaults values of the folders are pre-filled in your [`.env`](./webinterface/.env.template) file, and even if that variables are not present in such file, the settings assumed the default values, which are relative to the main repo folder. So create the folders with (Note: make sure you change BASE_DIR to `vast-pipeline`):

```bash
cd BASE_DIR && mkdir pipeline-runs && mkdir reference-surveys
```

After creating the folders with the defaults values your directory tree should look like this:

```bash
vast-pipeline/
├── init-tools
├── pipeline
├── pipeline-runs
├── reference-surveys
├── requirements
├── static
├── templates
├── webinterface
├── CONTRIBUTING.md
├── INSTALL.md
├── manage.py
└── README.md
```

## Pipeline Login
Currently the pipeline support only login via GitHub Team and/or as Django administrator.

Please make sure to fill the `SOCIAL_AUTH_GITHUB_KEY, SOCIAL_AUTH_GITHUB_SECRET, SOCIAL_AUTH_GITHUB_TEAM_ID, SOCIAL_AUTH_GITHUB_TEAM_ADMIN` in your [`.env`](./webinterface/.env.template) file. Also be sure to be part of the GitHub team, if not ask @srggrs, @ajstewart or @marxide to be added.

You can also login on your __local__ version for doing some develpment by creating an admin user:

```bash
$ ./manage.py createsuperuser
```

Fill in your details and then login with the created credentials at `localhost:8000/pipe-admin` (change ip and port if needed). That will log you in the Django admin site. Go to `localhost:8000` or click "site" on the right top corner to enter the vast pipeline website.

## Pipeline Usage
All the pipeline commands are run using the Django global `./manage.py <command>` interface. Therefore you need to activate the `Python` environment. You can have a look at the available commands for the pipeline app:

```bash
(pipeline_env)$ ./manage.py help
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

Detailed commands for resetting the database can be found in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

Resetting a pipeline run can be done using the `clearpiperun` command: it will delete all images (and related objects such as sources) associated with that pipeline run, if that images does not belong to another pipeline run. It will deleted all the sources associated with that pipeline run.
```bash
(pipeline_env)$ ./manage.py clearpiperun path/to/my_pipe_run
# or
(pipeline_env)$ ./manage.py clearpiperun my_pipe_run
```

More details on the `clearpiperun` command can be found in the [Contributing guidelines](./CONTRIBUTING.md#clearing-run-data).

### Import survey data

This functionality is still not developed


## Data Exploration via Django Web Server

Make sure you installed and compiled correctly the frontend assets see [guide](./INSTALL.md#pipeline-front-end-assets-quickstart)

1. Start the Django development web server:

```bash
(pipeline_env)$ ./manage.py runserver
```

2. Test the webserver by pointing your browser at http://127.0.0.1:8000 or http://localhost:8000

The webserver is independent of `runpipeline` and you can use the website while the pipeline commands are running.

## Production Deployment
This section describes a simple deployment without using Docker containers, assuming the use of [WhiteNoise](http://whitenoise.evans.io/en/stable/) to serve the static files. It is possible to serve the static files using other methods (e.g. Nginx). And in the future it is possible to upgrade the deployment stack using Docker container and Docker compose (we foresee 3 main containers: Django, Dask and Traefik). We recommend in any case reading [Django deployment documentation](https://docs.djangoproject.com/en/3.1/howto/deployment/) for general knowledge.

We assume deployment to a __UNIX server__.

The following steps describes how to set up the Django side of the production deployment, and can be of reference for a future Dockerization. They assumed you have `SSH` access to your remote server and have `sudo` priviledges.

1. Clone the repo in a suitable path, e.g. `/opt/`.

  ```bash
  $ cd /opt && sudo git clone https://github.com/askap-vast/vast-pipeline
  ```

2. Follow the installation instructions in [`INSTALL.md`](./INSTALL.md). We recommend installing the Python virtual environment under the pipeline folder.

  ```bash
  $ cd /opt/vast-pipeline && virtualenv -p python3 pipeline_env
  ```

3. Configure your `.env` files with all the right settings.

4. Check that your server is running fine by changing `DEBUG = True` in the `.env` file.

5. Run Django deployment checklist command to see what are you missing. It is possible that some options are turned off, as implemented in the reverse proxy or load balancer of your server (e.g. `SECURE_SSL_REDIRECT = False` or not set, assumes your reverse proxy redirect HTTP to HTTPS).

  ```bash
  (pipeline_env)$ ./manage.py check --deploy
  ```

6. Build up the static and fix url in JS9:

  ```bash
  (pipeline_env)$ cd /opt/vast-pipeline && npm ci && npm start && npm run js9staticprod && ./manage.py collectstatic -c --noinput
  ```

7. Set up a unit/systemd file as recommended in [Gunicorn docs](https://docs.gunicorn.org/en/latest/deploy.html#systemd) (feel free to use the socket or an IP and port). An example of command to write in the file is (assuming a virtual environment is installed in `venv` under the main pipeline folder):

  ```bash
  ExecStart=/opt/vast-pipeline/venv/bin/gunicorn -w 3 -k gevent --worker-connections=1000 --timeout 120 --limit-request-line 6000 -b 127.0.0.1:8000 webinterface.wsgi
  ```

8. Finalise the installation of the unit file. Some good instructions on where to put, link and install the unit file are described in the [Jupyter Hub docs](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html#setup-systemd-service)

### Security

By default the settings file has some security parameters that are set when you run the web app in production (`DEBUG = False`), but you can read more in the Django documentation or in this [blog post](https://adamj.eu/tech/2019/04/10/how-to-score-a+-for-security-headers-on-your-django-website/) in which they explain how to get an A+ rating for your web site.
