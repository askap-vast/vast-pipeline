<!-- markdownlint-disable MD046 -->
# Configuration

This section describe how to configure your VAST Pipeline installation.

## Pipeline Configuration

The following instructions, will get you started in setting up the database and pipeline configuration.

!!! note
    The commands given in this section, unless otherwise stated, assume that the current directory is the pipeline root and that your pipeline Python environment has been activated.

1. Create a database for the pipeline. If you followed the [installation](installation.md) process, you will have a PostgreSQL Docker container running on your system. Use the provided script `init-tools/init-db.py` script to create a new database for the pipeline. As a security precaution, this script will also create a new database user and set the pipeline database owner to this new user.

    The initialization script requires several input parameters. For usage information, run with the `--help` option:

    ```console
    python init-tools/init-db.py --help
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

    Fill in the parameters as appropriate for your configuration. If you followed the [installation](installation.md) instructions, these would be the details for your PostgreSQL Docker container. Following from the same example in the installation section:

    ```console
    python init-tools/init-db.py localhost 55002 postgres <password> vast <vast-user-password> vastdb
    ```

    !!! info
        Where `<password>` is the superuser password that was passed to `docker run`, and `<vast-user-password>` is a new password of your choice for the new `vast` database user.

        You may change the values for the username and database-name, the above is just an example.

    If everything went well the output should be:

    ```console
    Creating new user/role vast ...
    Creating new database vastdb ...
    Done!
    ```

2. Copy the setting configuration file template and modify it with your desired settings. Please refer to the [.env File](#.env-file) section on this page for further details about the settings that are set in this file along with their defaults.

    ```console
    cp webinterface/.env.template webinterface/.env
    ```

3. Set the database connection settings in the `webinterface/.env` file by modifying `DATABASE_URL` (for URL syntax see [this link](https://django-environ.readthedocs.io/en/latest/#tips){:target="_blank"}). For example:

    !!! example ".env"
        ```console
        DATABASE_URL=psql://vast:<vast-user-password>@localhost:55002/vastdb
        ```

    !!! note
        The connection details are the same that you setup during the [installation](installation.md). The database/user names must not contain any spaces or dashes, so use the underscore if you want, e.g. `this_is_my_db_name`.

4. Create the pipeline database tables. The `createcachetable` command creates the cache tables required by DjangoQ.

    ```terminal
    python manage.py migrate
    python manage.py createcachetable
    ```

5. Create the pipeline data directories. The pipeline has several directories that can be configured in `webinterface/.env`:

    * `PIPELINE_WORKING_DIR`: location to store various pipeline output files.
    * `RAW_IMAGE_DIR`: default location that the pipeline will search for input images and catalogues to ingest during a pipeline run. Data inputs can also be defined as absolute paths in a pipeline run configuration file, so this setting only affects relative paths in the pipeline run configuration.
    * `HOME_DATA_DIR`: a path relative to a user's home directory to search for additional input images and catalogues. Intended for multi-user server deployments and unlikely to be useful for local installations. See below for some examples.
    * `HOME_DATA_ROOT`: path to the location of user home directories. Used together with `HOME_DATA_DIR`. If not supplied, the pipeline will search for the user's home directory using the default OS location. See below for some examples.

    !!! example ".env – User data configuration examples"
        In the following examples, assume that the user's name is `foo`.

        ```console
        # HOME_DATA_ROOT=Uncomment to set a custom path to user data dirs
        HOME_DATA_DIR=vast-pipeline-extra-data
        ```
        Using the above settings, the pipeline will search for additional input data in the user's home directory as resolved by the OS. e.g. on an Ubuntu system, this would be `/home/foo/vast-pipeline-extra-data`.

        ```console
        HOME_DATA_ROOT=/data/home
        HOME_DATA_DIR=vast-pipeline-extra-data
        ```
        Using the above settings, the pipeline will search for additional input data in `/data/home/foo/vast-pipeline-extra-data`.

    While the default values for these settings are relative to the pipeline codebase root (i.e. within the repo), we recommend creating these directories outside of the repo and updating the `webinterface/.env` file appropriately with absolute paths. For example, assuming you wish to create these directories in `/data/vast-pipeline`:

    ```console
    mkdir -p /data/vast-pipeline
    mkdir /data/vast-pipeline/pipeline-runs
    mkdir /data/vast-pipeline/raw-images
    ```

    and update the `webinterface/.env` file with:

    !!!example ".env"
        ```console
        PIPELINE_WORKING_DIR=/data/vast-pipeline/pipeline-runs
        RAW_IMAGE_DIR=/data/vast-pipeline/raw-images
        ```

## .env File

The `.env` file contains various top-level settings that apply to Django, authentication and the running of the pipeline itself.
Shown below is the [`.env.template`](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/.env.template){:target="_blank"} file which is provided to be able to copy in step 3 above.

!!! example ".env.template"
    ```console
    # Django
    DEBUG=True
    SECRET_KEY=FillMeUPWithSomeComplicatedString
    # see https://django-environ.readthedocs.io/en/latest/#tips
    DATABASE_URL=psql://FILLMYUSER:FILLMYPASSWORD@FILLMYHOST:FILLMYPORT/FILLMYDBNAME
    # BASE_URL=this for append a base url in a production deployment
    STATIC_ROOT=./staticfiles/
    STATIC_URL=/static/
    # STATICFILES_DIRS= uncomment and fill to use
    # EXTRA_APPS= uncomment and fill to use
    # EXTRA_MIDDLEWARE= uncomment and fill to use
    ALLOWED_HOSTS=localhost

    # Github Authentication
    GITHUB_AUTH_TYPE='org'
    SOCIAL_AUTH_GITHUB_KEY=fillMeUp
    SOCIAL_AUTH_GITHUB_SECRET=fillMeUp
    SOCIAL_AUTH_GITHUB_ORG_NAME=fillMeUp
    SOCIAL_AUTH_GITHUB_ADMIN_TEAM=fillMeUp

    # External APIs
    # TNS_API_KEY= uncomment and fill to use
    # TNS_USER_AGENT= uncomment and fill to use

    # Pipeline
    PIPELINE_WORKING_DIR=pipeline-runs
    FLUX_DEFAULT_MIN_ERROR=0.001
    POS_DEFAULT_MIN_ERROR=0.01
    RAW_IMAGE_DIR=raw-images
    HOME_DATA_DIR=vast-pipeline-extra-data
    # HOME_DATA_ROOT=Uncomment to set a custom path to user data dirs
    # PIPELINE_MAINTAINANCE_MESSAGE=Uncomment and fill to show
    MAX_PIPELINE_RUNS=3
    MAX_PIPERUN_IMAGES=200
    MAX_CUTOUT_IMAGES=30

    # Q_CLUSTER_TIMEOUT=86400
    # Q_CLUSTER_RETRY=86402
    # Q_CLUSTER_MAX_ATTEMPTS=1

    ETA_V_DATASHADER_THRESHOLD=20000
    ```

The available settings are grouped into 4 distinct categories:

### Django

These settings are standard Django settings that are commonly set in the `settings.py` file of Django projects. 
Please see [this page](https://docs.djangoproject.com/en/3.2/ref/settings/){:target="_blank"} in the Django documentation for explanations on their meaning.
Multiple entries for settings such as `EXTRA_APPS` or `EXTRA_MIDDLEWARE` can be entered as comma-separated strings like the following example:

!!!example ".env"
    ```console
    EXTRA_APPS=django_extensions,debug_toolbar
    ```

### GitHub Authentication

The settings in this section control the GitHub organization authentication method. 
Please refer to the [Python Social Auth documentation](https://python-social-auth.readthedocs.io/en/latest/backends/github.html){:target="_blank"} for descriptions of the required settings.

!!! note
    By default the pipeline is set up for authentication using GitHub organizations. Note that switching to teams will require changes to `settings.py`. 
    Please refer to the instructions in the [Python Social Auth documentation](https://python-social-auth.readthedocs.io/en/latest/backends/github.html){:target="_blank"}.

### External APIs

The pipeline website interface supports querying some external APIs, e.g. SIMBAD, NED, VizieR, TNS. Some of these APIs require authentication which are described below.

#### Transient Name Server (TNS)

If you wish to enable TNS cone search results on the [source detail page](../exploringwebsite/sourcedetail.md), you must first obtain an API key for TNS.

1. Create a TNS account at https://www.wis-tns.org/user/register if you do not already have one.
2. Once logged in, create a bot by navigating to https://www.wis-tns.org/bots and clicking "Add bot" near the top of the table.
3. Fill in the create bot form. Ensure that you select "Create new API key".
4. Securely store the API key and paste it into your pipeline `webinterface/.env` file under `TNS_API_KEY`.

    !!! warning
        Do not lose the API key! It is not possible to retrieve it again past this point.

5. Navigate to your [account page on TNS](https://www.wis-tns.org/user) and copy the User-Agent specification. Paste it into your pipeline `webinterface/.env` file under `TNS_USER_AGENT`.

    !!! example "webinterface/.env"
        ```console
        TNS_USER_AGENT='tns_marker{"tns_id": 0000, "type": "user", "name": "your_username"}'
        ```

### Pipeline

These settings apply to various aspects of the VAST pipeline itself. The table below provides descriptions of each setting.

| Setting <img width=440/> | Default Value | Description |
| ------------------------ | ------- | ----------- |
| `PIPELINE_WORKING_DIR`   | pipeline-runs | The name of the working directory where pipeline run directories are created. The pipeline location acts as the root directory. |
| `FLUX_DEFAULT_MIN_ERROR` | 0.001 | In the event a measurement is ingested with a flux error of 0 from Selavy, the error is replaced with this default value (mJy). |
| `POS_DEFAULT_MIN_ERROR` | 0.01 | In the event a measurement is ingested with an positional error of 0 from Selavy, the error is replaced with this default value (arcsec). |
| `RAW_IMAGE_DIR` | raw-images | Directory where the majority of raw ASKAP FITS images are expected to be stored. This directory is scanned to provide user with an image list when configuration a job using the website interface. |
| `HOME_DATA_DIR` | vast-pipeline-extra-data | Directory relative to the user's home directory that contains additional input images and catalogues. Safe to ignore if you don't intend to use this functionality. |
| `HOME_DATA_ROOT` | Disabled | Path to directory that contains user's home directories. Enable by uncommenting and setting the desired path. If left disabled (commented), the pipeline will assume the OS default home directory location.
| `PIPELINE_MAINTAINANCE_MESSAGE` | Disabled | The message to display at the top of the webserver. See image below this table for an example. Comment out the setting to disable. |
| `MAX_PIPELINE_RUNS` | 3 | The allowed maximum number of concurrent pipeline runs. |
| `MAX_PIPERUN_IMAGES` | 200 | The allowed maximum number of images in a single pipeline run (non-admins). |
| `MAX_CUTOUT_IMAGES` | 30 | The maximum number of cutout images to display on the source detail pages. The first `MAX_CUTOUT_IMAGES` cutouts are displayed, in temporal order. |
| `Q_CLUSTER_TIMEOUT` | 86400 | Number of seconds a Django-Q cluster worker may spend on a task before it is terminated. See the [Django-Q documentation](https://django-q.readthedocs.io/en/latest/configure.html#timeout). |
| `Q_CLUSTER_RETRY` | 86402 | Number of seconds a Django-Q broker will wait for a cluster to finish a task before it's presented again. See the [Django-Q documentation](https://django-q.readthedocs.io/en/latest/configure.html#retry). |
| `Q_CLUSTER_MAX_ATTEMPTS` | 1 | Number of times a failed task is retried. See the [Django-Q documentation](https://django-q.readthedocs.io/en/latest/configure.html#max-attempts). |
| `ETA_V_DATASHADER_THRESHOLD` | 20000 | The number of datapoints above which the eta-V plot uses datashader to plot the non-threshold distribution. |

#### Maintenance Message Example

!!!example ".env"
    ```console
    PIPELINE_MAINTAINANCE_MESSAGE=This website is subject to rapid changes which may result in data loss and may go offline with minimal warning. Please be mindful of usage.
    ```

![!Maintenance message example.](../img/maintenance-message.png){: loading=lazy }

## Authentication

The pipeline supports two authentication methods: GitHub Organizations, intended to multi-user server deployments; and local Django administrator. For a single-user local installation, we recommend creating a Django superuser account.

### GitHub Organizations

Please refer to the [Python Social Auth documentation](https://python-social-auth.readthedocs.io/en/latest/backends/github.html){:target="_blank"} for a complete description on this authentication method and how to set up the GitHub app used for authentication.
All settings are entered into the `.env` file as detailed in the [above section](#.env-file).

### Django superuser

Create a Django superuser account with the following command and follow the interactive prompts.

```console
python manage.py createsuperuser
```

This account can be used to log into the Django admin panel once the webserver is running (see [Starting the Pipeline Web App](../adminusage/app.md#starting-the-pipeline-web-app)) by navigating to <https://localhost:8000/pipe-admin/>. Once logged in, you will land on the Django admin page. Navigate back to the pipeline homepage <http://localhost:8000/> and you should be authenticated.

## Data Exploration via Django Web Server

You can start the web app/server via the instructions provided in [Starting the Pipeline Web App](../adminusage/app.md#starting-the-pipeline-web-app).
