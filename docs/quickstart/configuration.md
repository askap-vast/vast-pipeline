# Vast Pipeline Configuration

This section describe how to configure your downloaded VAST pipeline.

## Pipeline Configuration
The following instructions, will get you started in setting up the database and pipeline configuration
1. Copy the setting configuration file template, and fill it with your settings (see [defaults](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/.env.template))

```bash
cp webinterface/.env.template webinterface/.env
```

2. Choose a database name and user with password (e.g. database name: `vastdb`; user: `vast`, psw: `vastpsw`), and add the connection details in `.env` (for URL syntax see [this link](https://django-environ.readthedocs.io/en/latest/#tips))

```cmake
DATABASE_URL=psql://FILLMYUSER:FILLMYPASSWORD@FILLMYHOST:FILLMYPORT/FILLMYDBNAME
```

NOTE: the connection details (host and port) are the same that you setup during the [Installation](installation.md). The database/user names must not contain any spaces or dashes, so use the underscore if you want, e.g. `this_is_my_db_name`.

3. Create the database user and database name, by running:

```bash
$ python ./init-tools/init-db.py localhost 5432 postgres postgres vast vastpsw vastdb
```

  For help on the command run it with the option `--help`

```bash
$ python ./init-tools/init-db.py --help
usage: init-db.py [-h] host port admin-username admin-password username password database-name

Initialize a PostgreSQL database for VAST Pipeline use. Creates a new superuser and creates a new database owned by the new superuser.

positional arguments:
  host            database host
  port            database port
  admin-username  database administrator username
  admin-password  database administrator password
  username        username for the new user/role to create for the VAST Pipeline
  password        password for the new user/role to create for the VAST Pipeline
  database-name   name of the new database to create for the VAST Pipeline

optional arguments:
  -h, --help      show this help message and exit
```

  If everything went well the output is:

```bash
Creating new user/role vast ...
Creating new database vastdb ...
Done!
```

4. Create the database tables. Remember first to activate the Python environment as described in [Installation of Python Enviroment](installation.md#python-environment). The `createcachetable` command below creates the cache tables required by DjangoQ.

```bash
(pipeline_env)$ ./manage.py migrate
(pipeline_env)$ ./manage.py createcachetable
```

5. Create the directories listed at the bottom of `settings.py` and update the details on your setting configuration file `.env` (single name, e.g. `pipeline-runs` means path relative to `BASE_DIR`, so the main folder where you cloned the repo).

```Python
# reference surveys default folder
PIPELINE_WORKING_DIR = env('PIPELINE_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'pipeline-runs'))

# reference surveys default folder
SURVEYS_WORKING_DIR = env('SURVEYS_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'reference-surveys'))
```

The defaults values of the folders are pre-filled in your [`.env`](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/.env.template) file, and even if that variables are not present in such file, the settings assumed the default values, which are relative to the main repo folder. So create the folders with (Note: make sure you change BASE_DIR to `vast-pipeline`):

```bash
cd BASE_DIR && mkdir pipeline-runs && mkdir reference-surveys
```

After creating the folders with the defaults values your directory tree should look like this:

<pre><code>
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── gulpfile.js
├── <b>init-tools</b>
├── INSTALL.md
├── LICENSE.txt
├── manage.py
├── <b>node_modules</b>
├── package.json
├── package-lock.json
├── README.md
├── <b>requirements</b>
├── <b>static</b>
├── <b>templates</b>
├── <b>pipeline-runs</b>
├── <b>vast_pipeline</b>
└── <b>webinterface</b>
</code></pre>

## Pipeline Login
Currently the pipeline support only login via GitHub Team and/or as Django administrator.

Please make sure to fill the `SOCIAL_AUTH_GITHUB_KEY, SOCIAL_AUTH_GITHUB_SECRET, SOCIAL_AUTH_GITHUB_TEAM_ID, SOCIAL_AUTH_GITHUB_TEAM_ADMIN` in your [`.env`](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/.env.template) file. Also be sure to be part of the GitHub team, if not ask @srggrs, @ajstewart or @marxide to be added.

You can also login on your __local__ version for doing some develpment by creating an admin user:

```bash
$ ./manage.py createsuperuser
```

Fill in your details and then login with the created credentials at `localhost:8000/pipe-admin` (change ip and port if needed). That will log you in the Django admin site. Go to `localhost:8000` or click "site" on the right top corner to enter the vast pipeline website.

## Data Exploration via Django Web Server
You can start the web app/server via the instructions provided in XXXX.
